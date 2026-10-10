import pandas as pd
import sqlite3
conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query('SELECT * FROM scada_telemetry WHERE scenario_id LIKE "A4_%" AND ground_truth = 1', conn)

from engines.policy_engine import PolicyEngine
policy = PolicyEngine(epsilon_m=0.05)

missed = df[df.apply(lambda row: policy.evaluate_v2(row['tank_level_observed'], row['pump_command'], row['valve_command']) <= 0.95, axis=1)]

print("Missed scenarios:")
for scenario_id in missed['scenario_id'].unique():
    print(f"Scenario: {scenario_id}")
    sample = missed[missed['scenario_id'] == scenario_id].iloc[0]
    print(f"  param={sample['attack_parameter']}, pump={sample['pump_command']}, valve={sample['valve_command']}")
