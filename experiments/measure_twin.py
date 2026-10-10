import pandas as pd
import sqlite3
import numpy as np

conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query('SELECT * FROM scada_telemetry', conn)
df_eval = pd.read_csv('data/evaluation_results.csv')

df_normals = df[df['scenario_id'].str.startswith('N_')]
eval_normals = df_eval[df_eval['scenario_id'].str.startswith('N_')]

merged = pd.merge(df_normals, eval_normals, on=['scenario_id', 'simulation_time_s'])

# S_p = min(|h_obs - h_twin| / tau_p, 1.0)
# So |h_obs - h_twin| = S_p * tau_p (if S_p < 1.0)
# Let's verify max S_p
max_s_p = merged['S_p'].max()
print(f"Max tracking error on 60 normal scenarios (meters): {max_s_p * 0.035:.5f}")
