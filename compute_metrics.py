import pandas as pd
import sqlite3
import json

print("=== Per-Tick vs Event-Level Metrics per Attack Type ===")
print(f"{'Type':<12} | {'Tick-Recall':<12} | {'Tick-Precision':<15} | {'Tick-F1':<10} | {'Event-Recall':<15}")

df = pd.read_csv("data/evaluation_results.csv")

for attack_type in ['FDI', 'Replay', 'DoS', 'Auth_Misuse']:
    df_attack = df[df['attack_type'] == attack_type]
    if len(df_attack) == 0: continue
        
    tp = len(df_attack[(df_attack['ground_truth'] == 1) & (df_attack['predicted_anomaly'] == 1)])
    fp = len(df_attack[(df_attack['ground_truth'] == 0) & (df_attack['predicted_anomaly'] == 1)])
    fn = len(df_attack[(df_attack['ground_truth'] == 1) & (df_attack['predicted_anomaly'] == 0)])
    
    tick_rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    tick_prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    tick_f1 = 2 * tick_prec * tick_rec / (tick_prec + tick_rec) if (tick_prec + tick_rec) > 0 else 0
    
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

print("\n=== LSTM Score on A4 Scenarios ===")
df_a4 = df[df['scenario_id'].str.startswith('A4')]
for scenario_id, group in df_a4.groupby('scenario_id'):
    settled = group[(group['simulation_time_s'] >= 120) & (group['simulation_time_s'] <= 199)]
    attack = group[(group['simulation_time_s'] >= 200) & (group['simulation_time_s'] <= 300)]
    print(f"{scenario_id} | Settled Max Sl: {settled['S_l'].max():.3f} | Attack Max Sl: {attack['S_l'].max():.3f}")

print("\n=== LSTM Flags across N scenarios ===")
df_normals = df[df['scenario_id'].str.startswith('N_')]
flags = len(df_normals[df_normals['S_l'] > 0.95])
print(f"Total LSTM flags in N scenarios: {flags}")

print("\n=== Pre- and Post-Attack FP Counts (A1-A4) ===")
# Pre/post attack are ticks in A1-A4 where ground_truth == 0
df_attacks = df[df['scenario_id'].str.startswith('A')]
pre_post = df_attacks[df_attacks['ground_truth'] == 0]
lstm_fps = len(pre_post[pre_post['S_l'] > 0.95])
policy_fps = len(pre_post[pre_post['S_c'] > 0.95])
physics_fps = len(pre_post[pre_post['S_p'] > 0.95])
print(f"Pre/Post attack ticks: {len(pre_post)}")
print(f"LSTM false positives: {lstm_fps}")
print(f"Policy false positives: {policy_fps}")
print(f"Physics false positives: {physics_fps}")

print("\n=== Policy Engine A4 Breakdown ===")
from engines.policy_engine import PolicyEngine
policy = PolicyEngine(epsilon_m=0.05)
conn = sqlite3.connect("data/scada_ids.db")
df_db = pd.read_sql_query("SELECT * FROM scada_telemetry", conn)

a4_attack_ticks = df_db[(df_db['scenario_id'].str.startswith('A4')) & (df_db['ground_truth'] == 1)]
missed_types = {'pump_on_in_deadband': 0, 'pump_off_in_deadband': 0, 'valve_in_range': 0, 'other': 0}

fired = 0
for _, row in a4_attack_ticks.iterrows():
    s_c = policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command'])
    if s_c > 0.95:
        fired += 1
    else:
        lvl = row['tank_level_observed']
        if row['pump_command'] == 1 and 0.1 <= lvl <= 0.8:
            missed_types['pump_on_in_deadband'] += 1
        elif row['pump_command'] == 0 and 0.2 <= lvl <= 0.9:
            missed_types['pump_off_in_deadband'] += 1
        elif 0 <= row['valve_command'] <= 100 and row['pump_command'] in [0,1]:
            missed_types['valve_in_range'] += 1
        else:
            missed_types['other'] += 1

print(f"A4 attack ticks: {len(a4_attack_ticks)}")
print(f"Policy caught: {fired} ({fired/len(a4_attack_ticks)*100:.1f}%)")
print("Missed logic breakdown:")
for k, v in missed_types.items():
    print(f"  - {k}: {v}")

conn.close()
