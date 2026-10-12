import sqlite3
import pandas as pd

conn = sqlite3.connect('data/scada_ids.db')
query = """
SELECT scenario_id, sequence_id, simulation_time_s, tank_level_observed, attack_type, ground_truth
FROM scada_telemetry
WHERE scenario_id LIKE 'A4_%' AND sequence_id IN (199, 200)
ORDER BY scenario_id, sequence_id
"""
df = pd.read_sql_query(query, conn)

print(f"{'Scenario':<10} | {'Seq 199 (t=199s) Level':<24} | {'Seq 200 (t=200s) Level':<24} | {'Doc H0 Claim':<20}")
print("-" * 85)

for sid in sorted(df['scenario_id'].unique()):
    sub = df[df['scenario_id'] == sid]
    row199 = sub[sub['sequence_id'] == 199]
    row200 = sub[sub['sequence_id'] == 200]
    lvl199 = row199['tank_level_observed'].values[0] if len(row199) else float('nan')
    lvl200 = row200['tank_level_observed'].values[0] if len(row200) else float('nan')
    
    # Doc claim
    if sid in ['A4_004', 'A4_007', 'A4_010', 'A4_013']:
        doc_claim = "H0 = 2.1 m"
    else:
        doc_claim = "H0 = 0.4 m"
        
    print(f"{sid:<10} | {lvl199:<24.4f} | {lvl200:<24.4f} | {doc_claim:<20}")
