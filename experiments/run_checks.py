import pandas as pd
import sqlite3
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS
from engines.policy_engine import PolicyEngine

print("--- Task B.1: Dataset Provenance ---")
conn = sqlite3.connect('data/scada_ids.db')
df_db = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'N_%'", conn)
df_eval = pd.read_csv('data/evaluation_results.csv')
df_eval_n = df_eval[df_eval['scenario_id'].str.startswith('N')]

print("Stored Normal (MATLAB/DB):")
print(f"Level range: {df_db['tank_level_observed'].min():.3f} - {df_db['tank_level_observed'].max():.3f}")
print(f"Q_in mean: {df_db['q_in'].mean():.4f}, Q_out mean: {df_db['q_out'].mean():.4f}")
print(f"LSTM Score (CSV): Max: {df_eval_n['S_l'].max():.4f}, Mean: {df_eval_n['S_l'].mean():.4f}")

cfg = load_config('scada_live/config.yaml')
plant = LivePlant(cfg, standalone_mode=True)
plant.noise._clamp_flow = False
levels, q_ins, q_outs = [], [], []
for _ in range(1800):
    pkt = plant.step()
    levels.append(pkt.level_m)
    q_ins.append(pkt.q_in)
    q_outs.append(pkt.q_out)

print("\nLive Normal (Python ProcessSimulator, Unclamped):")
print(f"Level range: {min(levels):.3f} - {max(levels):.3f}")
print(f"Q_in mean: {np.mean(q_ins):.4f}, Q_out mean: {np.mean(q_outs):.4f}")

print("\n--- Task C: Policy v2 ---")
# 1. Print A4 attack-tick hit rate before and after.
df_a4 = df_eval[df_eval['scenario_id'].str.startswith('A4')]
df_a4_attack = df_a4[df_a4['ground_truth'] == 1]
df_a4_telemetry = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'A4_%' AND simulation_time_s >= 200 AND simulation_time_s <= 300", conn)

policy = PolicyEngine()
# Before (Old logic: safe_valve allowed regardless of pump)
hits_before = 0
hits_after = 0
for _, row in df_a4_telemetry.iterrows():
    # Old logic:
    if row['valve_command'] not in [policy.default_valve_pct, 0.0]:
        hits_before += 1
    elif policy.evaluate(row['tank_level_observed'], row['pump_command'], row['valve_command']) == 1.0:
        hits_before += 1
        
    # New logic:
    if policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command']) == 1.0:
        hits_after += 1

total_a4_attack = len(df_a4_telemetry)
print(f"A4 attack ticks hit BEFORE: {hits_before}/{total_a4_attack} ({(hits_before/total_a4_attack)*100:.1f}%)")
print(f"A4 attack ticks hit AFTER:  {hits_after}/{total_a4_attack} ({(hits_after/total_a4_attack)*100:.1f}%)")

# 2. Print policy v2 fire counts on: 9 test normals, 60 DB normals, pre-attack ticks of A1 to A4.
df_db_n = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'N_%'", conn)
df_db_pre = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id NOT LIKE 'N_%' AND simulation_time_s < 200", conn)

def count_v2_fires(df_in):
    return sum(policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command']) == 1.0 for _, row in df_in.iterrows())

print("\nPolicy v2 fires on:")
print(f"9 test normals (CSV): {count_v2_fires(pd.merge(df_eval_n, df_db, on=['scenario_id', 'simulation_time_s']))}")
print(f"60 DB normals: {count_v2_fires(df_db_n)}")
print(f"Pre-attack ticks A1-A4: {count_v2_fires(df_db_pre)}")

# 3. Print distinct (pump, valve) counts for A4 ticks that are still missed.
print("\nMissed A4 attack ticks distinct (pump, valve):")
missed = []
for _, row in df_a4_telemetry.iterrows():
    if policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command']) == 0.0:
        missed.append((row['pump_command'], row['valve_command']))
from collections import Counter
for (p, v), count in Counter(missed).items():
    print(f"Pump: {p}, Valve: {v} => {count} ticks")
