import pandas as pd
import sqlite3
conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query('SELECT * FROM scada_telemetry WHERE scenario_id="A4_001"', conn)
print("A4_001 rows around end of attack (t=300):")
for _, row in df[(df['simulation_time_s'] >= 298) & (df['simulation_time_s'] <= 303)].iterrows():
    print(f"t={row['simulation_time_s']} obs={row['tank_level_observed']:.3f} q_in={row['q_in']:.4f} q_out={row['q_out']:.4f} pump={row['pump_command']} valve={row['valve_command']}")
