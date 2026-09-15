import sqlite3
import pandas as pd
import numpy as np
import torch
import os
import pickle
import json

from config.parameters import PARAMS
from config.scenarios import get_scenario_by_id
from engines.physics_engine import PhysicsEngine
from engines.policy_engine import PolicyEngine
from engines.availability_engine import AvailabilityEngine
from engines.temporal_engine import TemporalEngine
from engines.fusion_engine import FusionEngine
from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import DataPreprocessor
from evaluation.metrics import calculate_classification_metrics, calculate_detection_latency
from evaluation.reporter import Reporter

def load_test_data(db_path="data/scada_ids.db", test_normal_ids=None):
    """Load test scenarios: all attacks + only held-out normal scenarios."""
    conn = sqlite3.connect(db_path)
    
    # Always load all attack scenarios
    query_attacks = "SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'A%'"
    df_attacks = pd.read_sql_query(query_attacks, conn)
    
    # Only load held-out normal scenarios (never seen during training)
    df_normals = pd.DataFrame()
    if test_normal_ids:
        placeholders = ','.join(['?'] * len(test_normal_ids))
        query_normals = f"SELECT * FROM scada_telemetry WHERE scenario_id IN ({placeholders})"
        df_normals = pd.read_sql_query(query_normals, conn, params=test_normal_ids)
    
    conn.close()
    return pd.concat([df_attacks, df_normals], ignore_index=True)

def get_initial_level_for_scenario(scenario_id: str) -> float:
    """Get the deterministic initial level from scenario config (not from noisy data)."""
    config = get_scenario_by_id(scenario_id)
    if config is not None:
        return config.initial_level_m
    return PARAMS.tank.initial_level_m  # Fallback

def main():
    print("Starting full pipeline evaluation...")
    
    # Thresholds
    tau_p = 0.035
    tau_l = 0.0085
    tau_a_ms = 1500.0
    tau_a_max_ms = 5000.0
    tau_fusion = 0.95
    
    # 1. Initialize deterministic engines
    physics_engine = PhysicsEngine(tau_p=tau_p)
    policy_engine = PolicyEngine(epsilon_m=0.05)
    availability_engine = AvailabilityEngine(tau_a_ms=tau_a_ms, tau_a_max_ms=tau_a_max_ms)
    
    # 2. Load LSTM & Preprocessor
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model to {device}...")
    
    preprocessor = DataPreprocessor(window_size=10)
    scaler_path = "checkpoints/scaler_v1.pkl"
    with open(scaler_path, "rb") as f:
        preprocessor.scaler = pickle.load(f)
    preprocessor.is_fitted = True
    
    model = LSTMAutoencoder(input_dim=5, hidden_dim=32, num_layers=1)
    model.load_state_dict(torch.load("checkpoints/lstm_ae_v1.pt", map_location=device, weights_only=True))
    
    temporal_engine = TemporalEngine(model, preprocessor, tau_l, device=device)
    
    # 3. Fusion Engine
    tau_fusion = 0.95
    fusion_engine = FusionEngine(w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25, tau_fusion=tau_fusion, strategy="max_vote")
    
    # 4. Load data split
    test_normal_ids = None
    split_path = "checkpoints/data_split_v1.json"
    if os.path.exists(split_path):
        with open(split_path, 'r') as f:
            split_info = json.load(f)
        test_normal_ids = split_info.get('test_normal_ids', None)
        print(f"Using held-out test normal scenarios: {test_normal_ids}")
    else:
        print("WARNING: No data split file found. Using all N_0xx as test normals (may include training data).")
    
    # 5. Load Data
    print("Loading test data...")
    df_test = load_test_data(test_normal_ids=test_normal_ids)
    print(f"Loaded {len(df_test)} test records across {df_test['scenario_id'].nunique()} scenarios.")
    
    # 6. Evaluate
    print("Evaluating...")
    
    window_size = preprocessor.window_size
    feature_cols = preprocessor.feature_cols
    
    # Pre-allocate results dictionary (Fix #7)
    n_records = len(df_test)
    results = {
        'scenario_id': [''] * n_records,
        'sequence_id': np.zeros(n_records, dtype=int),
        'simulation_time_s': np.zeros(n_records, dtype=float),
        'attack_type': [''] * n_records,
        'S_p': np.zeros(n_records, dtype=float),
        'S_l': np.zeros(n_records, dtype=float),
        'S_c': np.zeros(n_records, dtype=float),
        'S_a': np.zeros(n_records, dtype=float),
        'S_hybrid': np.zeros(n_records, dtype=float),
        'predicted_anomaly': np.zeros(n_records, dtype=int),
        'ground_truth': np.zeros(n_records, dtype=int)
    }
    
    from tqdm import tqdm
    idx = 0
    grouped = list(df_test.groupby('scenario_id'))
    for scenario_id, group in tqdm(grouped, desc="Evaluating Scenarios"):
        group = group.sort_values('sequence_id').reset_index(drop=True)
        
        # FIX #3: Use deterministic initial level, not noisy observed value
        initial_level = get_initial_level_for_scenario(scenario_id)
        physics_engine.reset(initial_level)
        
        window_buffer = []
        
        for _, row in group.iterrows():
            # Step physics
            _, _, s_p = physics_engine.step(row['q_in'], row['q_out'], row['tank_level_observed'], PARAMS.simulation.dt_s)
            
            # Step policy
            s_c = policy_engine.evaluate(row['tank_level_observed'], row['pump_command'], row['valve_command'])
            
            # Step availability
            _, s_a = availability_engine.evaluate(row['simulation_time_s'], row['source_time_s'], row['packet_received'])
            
            # Step temporal
            window_buffer.append(row[feature_cols].to_dict())
            if len(window_buffer) > window_size:
                window_buffer.pop(0)
                
            s_l = 0.0
            if len(window_buffer) == window_size:
                window_df = pd.DataFrame(window_buffer)
                _, s_l = temporal_engine.evaluate(window_df)
                
            # Fuse
            s_hybrid, predicted = fusion_engine.evaluate(s_p, s_l, s_c, s_a)
            
            # Store in pre-allocated dictionary
            results['scenario_id'][idx] = scenario_id
            results['sequence_id'][idx] = row['sequence_id']
            results['simulation_time_s'][idx] = row['simulation_time_s']
            results['attack_type'][idx] = row.get('attack_type', 'None')
            results['S_p'][idx] = s_p
            results['S_l'][idx] = s_l
            results['S_c'][idx] = s_c
            results['S_a'][idx] = s_a
            results['S_hybrid'][idx] = s_hybrid
            results['predicted_anomaly'][idx] = predicted
            results['ground_truth'][idx] = row['ground_truth']
            idx += 1
            
    df_results = pd.DataFrame(results)
    
    # Save raw results
    os.makedirs("data", exist_ok=True)
    df_results.to_csv("data/evaluation_results.csv", index=False)
    
    # 7. Report
    print("Generating report...")
    reporter = Reporter()
    metrics = calculate_classification_metrics(df_results['ground_truth'], df_results['predicted_anomaly'], df_results['S_hybrid'])
    latency = calculate_detection_latency(df_results)
    
    print("\n--- Overall Evaluation Results ---")
    for k, v in {**metrics, **latency}.items():
        print(f"  {k}: {v}")
    
    # Per-attack-type breakdown (Fix #9)
    print("\n--- Per-Attack-Type Breakdown ---")
    for attack_type in ['FDI', 'Replay', 'DoS', 'Auth_Misuse']:
        df_type = df_results[df_results['attack_type'] == attack_type]
        if len(df_type) > 0:
            m = calculate_classification_metrics(df_type['ground_truth'], df_type['predicted_anomaly'])
            print(f"  {attack_type}: Precision={m['precision']:.3f}, Recall={m['recall']:.3f}, F1={m['f1']:.3f}")
        
    filepath = reporter.plot_roc_curve(df_results['ground_truth'], df_results['S_hybrid'])
    print(f"\nROC curve saved to {filepath}")

if __name__ == "__main__":
    main()
