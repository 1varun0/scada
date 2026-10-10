import sqlite3
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.policy_engine import PolicyEngine

conn = sqlite3.connect('c:/projects/p1/New folder/data/scada_ids.db')

query = "SELECT scenario_id, ground_truth, tank_level_observed, pump_command, valve_command FROM scada_telemetry"
df = pd.read_sql_query(query, conn)

engine = PolicyEngine(epsilon_m=0.05)
df['v2_fire'] = df.apply(lambda row: engine.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command']), axis=1)

print("Policy v2 fires (v2_fire == 1.0) by scenario type and ground_truth:")

normal_df = df[df['scenario_id'].str.startswith('N')]
print(f"Normal scenarios: {int(normal_df['v2_fire'].sum())} fires out of {len(normal_df)} total ticks.")

a4_df = df[df['scenario_id'].str.startswith('A4')]
summary = a4_df.groupby(['scenario_id', 'ground_truth'])['v2_fire'].sum().reset_index()
print("\nA4 Scenarios:")
print(summary.to_string(index=False))

a1_df = df[df['scenario_id'].str.startswith('A1')]
print(f"A1 attack ticks: {int(a1_df[a1_df['ground_truth'] == 1]['v2_fire'].sum())}")
print(f"A1 post-attack ticks: {int(a1_df[a1_df['ground_truth'] == 0]['v2_fire'].sum())}")

a2_df = df[df['scenario_id'].str.startswith('A2')]
print(f"A2 attack ticks: {int(a2_df[a2_df['ground_truth'] == 1]['v2_fire'].sum())}")
print(f"A2 post-attack ticks: {int(a2_df[a2_df['ground_truth'] == 0]['v2_fire'].sum())}")

a3_df = df[df['scenario_id'].str.startswith('A3')]
print(f"A3 attack ticks: {int(a3_df[a3_df['ground_truth'] == 1]['v2_fire'].sum())}")
print(f"A3 post-attack ticks: {int(a3_df[a3_df['ground_truth'] == 0]['v2_fire'].sum())}")
