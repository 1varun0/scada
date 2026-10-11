import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('data/scada_ids.db')

from config.scenarios import get_scenario_by_id
from engines.physics_engine import PhysicsEngine

tau_p = 0.035
dt = 1.0

held_out_ids = {'N_001', 'N_006', 'N_013', 'N_014', 'N_034', 'N_037', 'N_046', 'N_049', 'N_055'}

all_60_residuals = []
held_out_residuals = []
train_val_51_residuals = []

for i in range(1, 61):
    sc_id = f"N_{i:03d}"
    df = pd.read_sql_query(f"SELECT * FROM scada_telemetry WHERE scenario_id='{sc_id}' ORDER BY sequence_id", conn)
    if df.empty:
        continue
    sc = get_scenario_by_id(sc_id)
    pe = PhysicsEngine(tau_p=tau_p)
    pe.reset(sc.initial_level_m)
    
    for _, row in df.iterrows():
        _, res, _ = pe.step(row['q_in'], row['q_out'], row['tank_level_observed'], dt)
        abs_r = abs(res)
        all_60_residuals.append(abs_r)
        if sc_id in held_out_ids:
            held_out_residuals.append(abs_r)
        else:
            train_val_51_residuals.append(abs_r)

conn.close()

all_60 = np.array(all_60_residuals)
held_out = np.array(held_out_residuals)
train_51 = np.array(train_val_51_residuals)

print("=== Batch Physics Absolute Residual Statistics ===")
print(f"All 60 Normals ({len(all_60):,} ticks):")
print(f"  Max Absolute Residual: {np.max(all_60):.6f} m")
print(f"  P99 Absolute Residual: {np.percentile(all_60, 99):.6f} m")
print(f"  P95 Absolute Residual: {np.percentile(all_60, 95):.6f} m")
print(f"  MAE:                   {np.mean(all_60):.6f} m")
print(f"  Ticks > tau_p ({tau_p}m): {np.sum(all_60 > tau_p)}")

print(f"\n9 Held-Out Normals ({len(held_out):,} ticks):")
print(f"  Max Absolute Residual: {np.max(held_out):.6f} m")
print(f"  P99 Absolute Residual: {np.percentile(held_out, 99):.6f} m")
print(f"  MAE:                   {np.mean(held_out):.6f} m")
print(f"  Ticks > tau_p ({tau_p}m): {np.sum(held_out > tau_p)}")

print(f"\n51 Train/Val Normals ({len(train_51):,} ticks):")
print(f"  Max Absolute Residual: {np.max(train_51):.6f} m")
print(f"  P99 Absolute Residual: {np.percentile(train_51, 99):.6f} m")
print(f"  MAE:                   {np.mean(train_51):.6f} m")
print(f"  Ticks > tau_p ({tau_p}m): {np.sum(train_51 > tau_p)}")
