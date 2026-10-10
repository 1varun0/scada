import pandas as pd
import sqlite3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.physics_engine import PhysicsEngine

conn = sqlite3.connect('c:/projects/p1/New folder/data/scada_ids.db')
df_all = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A3_001' ORDER BY sequence_id", conn)

pe = PhysicsEngine(tau_p=0.035)
pe.reset(df_all.iloc[0]['tank_level_observed'])

results = []
for _, row in df_all.iterrows():
    # Batch pipeline uses exact row values for q_in and q_out without packet_received check
    pkt = {
        'q_in': row['q_in'],
        'q_out': row['q_out'],
        'level_m': row['tank_level_observed']
    }
    h_twin, residual, s_p = pe.step(row['q_in'], row['q_out'], row['tank_level_observed'], dt=1.0)
    
    if 340 <= row['sequence_id'] <= 480:
        results.append({
            'seq': row['sequence_id'],
            'rcv': row['packet_received'],
            'q_in': row['q_in'],
            'q_out': row['q_out'],
            'obs_lvl': row['tank_level_observed'],
            'twin_lvl': h_twin,
            'S_p': s_p
        })

res_df = pd.DataFrame(results)
print("Batch pipeline exact trace for A3_001 (seq 340 to 360 and 460 to 480):")
print(res_df.head(21).to_string(index=False))
print("...")
print(res_df.tail(21).to_string(index=False))
