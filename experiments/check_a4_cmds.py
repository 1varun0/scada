import pandas as pd
import sqlite3
conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query('SELECT * FROM scada_telemetry WHERE scenario_id="A4_001"', conn)
for _, row in df[df['ground_truth'] == 1].head(10).iterrows():
    print(f"t={row['simulation_time_s']}, param={row['attack_parameter']}, pump={row['pump_command']}, valve={row['valve_command']}")
