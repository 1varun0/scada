import pandas as pd
import sqlite3
import json
# Load evaluation results
df = pd.read_csv("data/evaluation_results.csv")

# 1. Real per-attack definition / Event-level vs per-tick
print("=== Per-Tick vs Event-Level Metrics per Attack Type ===")
print(f"{'Type':<12} | {'Tick-Recall':<12} | {'Tick-Precision':<15} | {'Tick-F1':<10} | {'Event-Recall':<15}")

for attack_type in ['FDI', 'Replay', 'DoS', 'Auth_Misuse']:
    df_attack = df[df['attack_type'] == attack_type]
    if len(df_attack) == 0:
        continue
        
    # Per-tick
    tp = len(df_attack[(df_attack['ground_truth'] == 1) & (df_attack['predicted_anomaly'] == 1)])
    fp = len(df_attack[(df_attack['ground_truth'] == 0) & (df_attack['predicted_anomaly'] == 1)])
    fn = len(df_attack[(df_attack['ground_truth'] == 1) & (df_attack['predicted_anomaly'] == 0)])
    
    tick_rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    tick_prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    tick_f1 = 2 * tick_prec * tick_rec / (tick_prec + tick_rec) if (tick_prec + tick_rec) > 0 else 0
    
    # Event-level (did we catch the attack at least once per scenario?)
    total_attacks = 0
    detected_attacks = 0
    
    for scenario_id, group in df_attack.groupby('scenario_id'):
        attack_mask = group['ground_truth'] == 1
        if attack_mask.any():
            total_attacks += 1
            if (group.loc[attack_mask, 'predicted_anomaly'] == 1).any():
                detected_attacks += 1
                
    event_rec = detected_attacks / total_attacks if total_attacks > 0 else 0
    
    print(f"{attack_type:<12} | {tick_rec:<12.3f} | {tick_prec:<15.3f} | {tick_f1:<10.3f} | {event_rec:<15.3f} ({detected_attacks}/{total_attacks})")


# 2. Initial levels
print("\n=== Initial Levels ===")
conn = sqlite3.connect("data/scada_ids.db")
query = """
SELECT scenario_id, min(simulation_time_s) as start_time, tank_level_observed 
FROM scada_telemetry 
GROUP BY scenario_id 
ORDER BY scenario_id
"""
df_starts = pd.read_sql_query(query, conn)
for _, row in df_starts.iterrows():
    print(f"Scenario {row['scenario_id']}: initial_level_m = {row['tank_level_observed']}")

# 3. Settled-period LSTM on A4_001
print("\n=== LSTM Score on A4_001 ===")
df_a4 = df[df['scenario_id'] == 'A4_001']
if len(df_a4) > 0:
    settled = df_a4[(df_a4['simulation_time_s'] >= 120) & (df_a4['simulation_time_s'] <= 199)]
    attack = df_a4[(df_a4['simulation_time_s'] >= 200) & (df_a4['simulation_time_s'] <= 300)]
    print(f"Settled period (120-199s) max S_l: {settled['S_l'].max():.3f}")
    print(f"Attack period (200-300s) max S_l: {attack['S_l'].max():.3f}")


# 4. LSTM flags across all N scenarios
print("\n=== LSTM Flags across N scenarios ===")
df_normals = df[df['scenario_id'].str.startswith('N_')]
for scenario_id, group in df_normals.groupby('scenario_id'):
    flags = len(group[group['S_l'] > 0.95])
    print(f"{scenario_id}: {flags} LSTM flags")


# 5. Policy v2 over every scenario
print("\n=== Policy Engine Firing Counts ===")
from engines.policy_engine import PolicyEngine
from config.parameters import PARAMS

policy = PolicyEngine(epsilon_m=0.05)

df_db = pd.read_sql_query("SELECT * FROM scada_telemetry", conn)

a4_attack_ticks = 0
a4_attack_flags = 0
other_flags = 0

for _, row in df_db.iterrows():
    s_c = policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command'])
    
    is_a4_attack_tick = (row['scenario_id'].startswith('A4') and row['ground_truth'] == 1)
    
    if is_a4_attack_tick:
        a4_attack_ticks += 1
        if s_c > 0.95:
            a4_attack_flags += 1
    else:
        if s_c > 0.95:
            other_flags += 1

print(f"A4 attack ticks: {a4_attack_ticks}, Policy fired: {a4_attack_flags}")
print(f"All other ticks: {len(df_db) - a4_attack_ticks}, Policy fired: {other_flags}")

conn.close()
