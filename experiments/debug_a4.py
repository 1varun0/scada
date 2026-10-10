import pandas as pd
import sqlite3
conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query('SELECT * FROM scada_telemetry WHERE scenario_id="A4_001"', conn)
df_eval = pd.read_csv('data/evaluation_results.csv')
a4_eval = df_eval[df_eval['scenario_id'] == 'A4_001']

merged = pd.merge(df, a4_eval, on=['scenario_id', 'simulation_time_s'])
for idx, row in merged.iterrows():
    if 298 <= row['simulation_time_s'] <= 305:
        print(f"Time: {row['simulation_time_s']}, S_p: {row['S_p']:.3f}, Obs: {row['tank_level_observed']:.3f}, q_in: {row['q_in']:.4f}, q_out: {row['q_out']:.4f}, pump: {row['pump_command']}, valve: {row['valve_command']}")
