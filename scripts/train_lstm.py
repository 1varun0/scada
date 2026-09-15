import sqlite3
import pandas as pd
import numpy as np
import torch
import os
import json

from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import DataPreprocessor, SCADADataset
from models.trainer import ModelTrainer

def load_normal_data(db_path="data/scada_ids.db"):
    """Load only normal scenarios for training the autoencoder."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Run import script first.")
        
    conn = sqlite3.connect(db_path)
    # Get all normal scenarios (N_*)
    query = "SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'N_%' ORDER BY scenario_id, sequence_id"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def train_val_test_split_scenarios(df, val_ratio=0.15, test_ratio=0.15):
    """Split by entire scenarios to prevent data leakage.
    
    Produces three sets:
      - Train: for LSTM-AE learning
      - Val: for early stopping and threshold selection
      - Test: held out entirely — never used until final evaluation
    """
    scenario_ids = df['scenario_id'].unique()
    np.random.seed(42)
    np.random.shuffle(scenario_ids)
    
    n_test = int(len(scenario_ids) * test_ratio)
    n_val = int(len(scenario_ids) * val_ratio)
    
    test_ids = scenario_ids[:n_test]
    val_ids = scenario_ids[n_test:n_test + n_val]
    train_ids = scenario_ids[n_test + n_val:]
    
    df_train = df[df['scenario_id'].isin(train_ids)].copy()
    df_val = df[df['scenario_id'].isin(val_ids)].copy()
    df_test = df[df['scenario_id'].isin(test_ids)].copy()
    
    return df_train, df_val, df_test, train_ids.tolist(), val_ids.tolist(), test_ids.tolist()

def main():
    print("Loading normal training data from SQLite...")
    try:
        df_normal = load_normal_data()
    except FileNotFoundError as e:
        print(e)
        return
        
    if df_normal.empty:
        print("No normal data found in database. Make sure Phase 1/2 data is imported.")
        return
        
    print(f"Loaded {len(df_normal)} normal telemetry records.")
    
    # Split into train/val/test
    df_train, df_val, df_test, train_ids, val_ids, test_ids = train_val_test_split_scenarios(
        df_normal, val_ratio=0.15, test_ratio=0.15
    )
    print(f"Train scenarios: {df_train['scenario_id'].nunique()}, records: {len(df_train)}")
    print(f"Val scenarios: {df_val['scenario_id'].nunique()}, records: {len(df_val)}")
    print(f"Test scenarios (held out): {df_test['scenario_id'].nunique()}, records: {len(df_test)}")
    
    # Preprocess
    print("Fitting preprocessor and generating sliding windows...")
    preprocessor = DataPreprocessor(window_size=10)
    preprocessor.fit(df_train)
    
    df_train_scaled = preprocessor.transform(df_train)
    df_val_scaled = preprocessor.transform(df_val)
    
    X_train, _, _ = preprocessor.create_windows(df_train_scaled)
    X_val, _, _ = preprocessor.create_windows(df_val_scaled)
    
    print(f"Train windows shape: {X_train.shape}")
    print(f"Val windows shape: {X_val.shape}")
    
    train_dataset = SCADADataset(X_train)
    val_dataset = SCADADataset(X_val)
    
    # Initialize Model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training on device: {device}")
    
    model = LSTMAutoencoder(input_dim=5, hidden_dim=32, num_layers=1)
    trainer = ModelTrainer(model=model, device=device, learning_rate=1e-3, batch_size=128)
    
    # Train
    print("Starting training loop...")
    history = trainer.train(train_dataset, val_dataset, epochs=20, patience=3)
    
    # Save
    checkpoint_dir = "checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    model_path = os.path.join(checkpoint_dir, "lstm_ae_v1.pt")
    trainer.save_checkpoint(model_path)
    print(f"Model saved to {model_path}")
    
    # Save the preprocessor (scaler) for later evaluation
    import pickle
    scaler_path = os.path.join(checkpoint_dir, "scaler_v1.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(preprocessor.scaler, f)
    print(f"Scaler saved to {scaler_path}")
    
    # Save the data split so evaluation can respect it
    split_info = {
        'train_normal_ids': train_ids,
        'val_normal_ids': val_ids,
        'test_normal_ids': test_ids,
    }
    split_path = os.path.join(checkpoint_dir, "data_split_v1.json")
    with open(split_path, 'w') as f:
        json.dump(split_info, f, indent=2)
    print(f"Data split saved to {split_path}")

if __name__ == "__main__":
    main()
