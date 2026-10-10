"""Phase 2: Streaming IDS Equivalence Test"""

import pytest
import pandas as pd
import time
from config.scenarios import get_scenario_by_id
from config.parameters import PARAMS
from simulator.process_simulator import ProcessSimulator
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.common.packets import TelemetryPacket
from dataclasses import replace

# Import engines directly for the batch reference
from engines.physics_engine import PhysicsEngine
from engines.policy_engine import PolicyEngine
from engines.availability_engine import AvailabilityEngine
from engines.temporal_engine import TemporalEngine
from engines.fusion_engine import FusionEngine
from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import DataPreprocessor
import pickle
import torch
import os

SCENARIOS = ['N_001', 'A1_001', 'A2_001', 'A3_001', 'A4_001']

def dict_to_packet(r, scenario_id):
    return TelemetryPacket(
        seq=r['sequence_id'],
        run_id=scenario_id,
        ts=r['simulation_time_s'],
        src_t=r['source_time_s'],
        received=bool(r['packet_received']),
        level_m=r['tank_level_observed'],
        q_in=r['q_in'],
        q_out=r['q_out'],
        pump_on=bool(r['pump_state'] == 1),
        pump_cmd=int(r['pump_command']),
        valve_pct=float(r['valve_state']),
        valve_cmd=float(r['valve_command'])
    )

@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_streaming_equals_batch(scenario_id):
    cfg = load_config()
    base_scenario = get_scenario_by_id(scenario_id)
    # Ensure run captures the attack (starts ~200-400s depending on attack)
    scenario = replace(base_scenario, duration_s=600.0)
    
    # Check attack start times
    if scenario.is_attack:
        assert scenario.attack.attack_start_s < 600.0, "Attack starts after simulation ends"
    
    import sqlite3
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 1. Load Batch Data from DB
    conn = sqlite3.connect(os.path.join(base_dir, "data/scada_ids.db"))
    df_batch = pd.read_sql_query(f"SELECT * FROM scada_telemetry WHERE scenario_id='{scenario_id}'", conn)
    conn.close()
    
    df_batch = df_batch[df_batch['simulation_time_s'] <= 600.0]
    batch_records = df_batch.to_dict('records')
    
    # 2. Run Batch Loop (Exactly as in run_evaluation.py)
    physics_engine = PhysicsEngine(tau_p=cfg.ids.tau_p)
    physics_engine.reset(scenario.initial_level_m)
    policy_engine = PolicyEngine(epsilon_m=cfg.ids.epsilon_m)
    availability_engine = AvailabilityEngine(tau_a_ms=cfg.ids.tau_a_ms, tau_a_max_ms=cfg.ids.tau_a_max_ms)
    
    preprocessor = DataPreprocessor(window_size=cfg.ids.lstm_window)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(base_dir, cfg.lstm.scaler_path), "rb") as f:
        preprocessor.scaler = pickle.load(f)
    preprocessor.is_fitted = True
    assert preprocessor.feature_cols == cfg.lstm.feature_cols
    assert cfg.simulation.dt_s == PARAMS.simulation.dt_s
    
    model = LSTMAutoencoder(input_dim=cfg.lstm.input_dim, hidden_dim=cfg.lstm.hidden_dim, num_layers=cfg.lstm.num_layers)
    model.load_state_dict(torch.load(os.path.join(base_dir, cfg.lstm.weights_path), map_location="cpu", weights_only=True))
    temporal_engine = TemporalEngine(model, preprocessor, cfg.ids.tau_l, device="cpu")
    
    fusion_engine = FusionEngine(w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25, tau_fusion=cfg.ids.tau_fusion, strategy="max_vote")
    
    batch_results = []
    window_buffer = []
    
    engines_fired_batch = {"physics": False, "lstm": False, "policy": False, "availability": False}
    has_missing_packet = False
    has_stale_packet = False
    
    for _, row in df_batch.iterrows():
        _, p_res, s_p = physics_engine.step(row['q_in'], row['q_out'], row['tank_level_observed'], PARAMS.simulation.dt_s)
        s_c = policy_engine.evaluate(row['tank_level_observed'], row['pump_command'], row['valve_command'])
        _, s_a = availability_engine.evaluate(row['simulation_time_s'], row['source_time_s'], row['packet_received'])
        
        if not bool(row['packet_received']):
            has_missing_packet = True
        if row['source_time_s'] < row['simulation_time_s']:
            has_stale_packet = True
            
        window_buffer.append(row[preprocessor.feature_cols].to_dict())
        if len(window_buffer) > preprocessor.window_size:
            window_buffer.pop(0)
            
        s_l = 0.0
        if len(window_buffer) == preprocessor.window_size:
            window_df = pd.DataFrame(window_buffer)
            _, s_l = temporal_engine.evaluate(window_df)
            
        s_hybrid, predicted = fusion_engine.evaluate(s_p, s_l, s_c, s_a)
        batch_results.append({
            's_p': float(s_p), 's_l': float(s_l), 's_c': float(s_c), 's_a': float(s_a), 
            's_hybrid': float(s_hybrid), 'predicted': bool(predicted)
        })
        
        if s_p > cfg.ids.tau_fusion: engines_fired_batch["physics"] = True
        if s_l > cfg.ids.tau_fusion: engines_fired_batch["lstm"] = True
        if s_c > cfg.ids.tau_fusion: engines_fired_batch["policy"] = True
        if s_a > cfg.ids.tau_fusion: engines_fired_batch["availability"] = True

    # Check Coverage
    if "A1" in scenario_id: assert engines_fired_batch["physics"], "FDI attack didn't fire physics engine"
    if "A2" in scenario_id: 
        assert engines_fired_batch["availability"], "Replay attack didn't fire availability engine"
        assert has_stale_packet, "Replay attack had no stale packets"
    if "A3" in scenario_id: 
        assert engines_fired_batch["availability"], "DoS attack didn't fire availability engine"
        assert has_missing_packet, "DoS attack had no missing packets"
    if "N_" in scenario_id:
        assert not any(engines_fired_batch.values()), "Normal scenario raised an anomaly"

    # 3. Run Streaming IDS on the SAME data
    streaming_ids = StreamingIDS(cfg, device="cpu")
    streaming_ids.reset(scenario.initial_level_m, scenario_id)
    
    streaming_results = []
    for r in batch_records:
        pkt = dict_to_packet(r, scenario_id)
        streaming_results.append(streaming_ids.update(pkt))
        
    # 4. Assert Exact Equivalence
    tol = 1e-5
    for i, (b, s) in enumerate(zip(batch_results, streaming_results)):
        assert abs(b['s_p'] - s['scores']['physics']) < tol, f"Physics mismatch at {i}"
        assert abs(b['s_c'] - s['scores']['policy']) < tol, f"Policy mismatch at {i}"
        assert abs(b['s_a'] - s['scores']['availability']) < tol, f"Availability mismatch at {i}"
        assert abs(b['s_l'] - s['scores']['lstm']) < tol, f"LSTM mismatch at {i}"
        assert abs(b['s_hybrid'] - s['hybrid']) < tol, f"Hybrid mismatch at {i}"
        assert b['predicted'] == s['is_anomaly'], f"Decision mismatch at {i}"

def test_performance_and_soak():
    """Runs a 30-minute simulation (1800 ticks) and verifies no drift and < 50ms latency."""
    cfg = load_config()
    base_scenario = get_scenario_by_id("N_001")
    scenario = replace(base_scenario, duration_s=1800.0)
    sim = ProcessSimulator(scenario)
    records = sim.run()
    
    ids = StreamingIDS(cfg)
    ids.reset(scenario.initial_level_m, "soak_run")
    
    latencies = []
    false_alarms = 0
    
    # Introduce mid-run recalibrate
    recalibrate_at = 900
    recent_levels = []
    
    for i, r in enumerate(records):
        pkt = dict_to_packet(r, "soak_run")
        recent_levels.append(pkt.level_m)
        if len(recent_levels) > 10:
            recent_levels.pop(0)
            
        if i == recalibrate_at:
            ids.recalibrate(recent_levels)
            
        start = time.perf_counter()
        v = ids.update(pkt)
        latencies.append(time.perf_counter() - start)
        
        if not v['calibrating'] and v['is_anomaly']:
            false_alarms += 1
            
    avg_ms = (sum(latencies) / len(latencies)) * 1000
    
    assert avg_ms < 50.0, f"Average tick latency too high: {avg_ms:.2f}ms"
    assert false_alarms == 0, f"False alarms during soak test: {false_alarms}"

def test_policy_streaming_parity_synthetic():
    """Forces a policy violation by hand-editing a frame to ensure equivalence logic is tested for the policy engine."""
    cfg = load_config()
    scenario_id = "A4_001"
    base_scenario = get_scenario_by_id(scenario_id)
    scenario = replace(base_scenario, duration_s=600.0)
    import sqlite3
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    conn = sqlite3.connect(os.path.join(base_dir, "data/scada_ids.db"))
    df_batch = pd.read_sql_query(f"SELECT * FROM scada_telemetry WHERE scenario_id='{scenario_id}'", conn)
    conn.close()
    
    df_batch = df_batch[df_batch['simulation_time_s'] <= 600.0]
    
    # Inject a forced policy violation for A4 so the coverage assertion passes
    idx = df_batch.index[df_batch['simulation_time_s'] == 250.0].tolist()
    if idx:
        df_batch.at[idx[0], 'tank_level_observed'] = 0.1
        
    batch_records = df_batch.to_dict('records')
    
    policy_engine = PolicyEngine(epsilon_m=cfg.ids.epsilon_m)
    batch_results = []
    
    for _, row in df_batch.iterrows():
        s_c = policy_engine.evaluate(row['tank_level_observed'], row['pump_command'], row['valve_command'])
        batch_results.append(s_c)
        
    streaming_ids = StreamingIDS(cfg, device="cpu")
    streaming_ids.reset(scenario.initial_level_m, scenario_id)
    streaming_results = []
    for r in batch_records:
        pkt = dict_to_packet(r, scenario_id)
        streaming_results.append(streaming_ids.update(pkt)['scores']['policy'])
        
    assert any(s > cfg.ids.tau_fusion for s in batch_results), "Forced policy violation failed to trigger batch engine"
    assert batch_results == streaming_results, "Policy engine streaming parity failed on synthetic frame"

def test_run_switch():
    """Verify that resetting the same instance gives identical results to a fresh instance."""
    cfg = load_config()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    import sqlite3
    conn = sqlite3.connect(os.path.join(base_dir, "data/scada_ids.db"))
    df_a = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A1_001' AND simulation_time_s <= 300", conn)
    df_b = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A3_001' AND simulation_time_s <= 300", conn)
    conn.close()
    
    reused_ids = StreamingIDS(cfg, device="cpu")
    # Run scenario A
    reused_ids.reset(get_scenario_by_id("A1_001").initial_level_m, "A1_001")
    for r in df_a.to_dict('records'):
        reused_ids.update(dict_to_packet(r, "A1_001"))
        
    # Reset and run scenario B
    reused_ids.reset(get_scenario_by_id("A3_001").initial_level_m, "A3_001")
    reused_results = []
    for r in df_b.to_dict('records'):
        reused_results.append(reused_ids.update(dict_to_packet(r, "A3_001")))
        
    # Fresh instance running scenario B
    fresh_ids = StreamingIDS(cfg, device="cpu")
    fresh_ids.reset(get_scenario_by_id("A3_001").initial_level_m, "A3_001")
    fresh_results = []
    for r in df_b.to_dict('records'):
        fresh_results.append(fresh_ids.update(dict_to_packet(r, "A3_001")))
        
    for reused, fresh in zip(reused_results, fresh_results):
        assert reused['scores'] == fresh['scores']
        assert reused['hybrid'] == fresh['hybrid']
