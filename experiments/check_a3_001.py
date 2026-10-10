import sqlite3
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engines.physics_engine import PhysicsEngine
from config.parameters import PARAMS

conn = sqlite3.connect('c:/projects/p1/New folder/data/scada_ids.db')
run_id = 'A3_001'

df = pd.read_sql_query(f"SELECT * FROM scada_telemetry WHERE scenario_id='{run_id}' AND sequence_id >= 195 AND sequence_id <= 210", conn)

if df.empty:
    print(f"No data for scenario_id {run_id}")
else:
    print("Raw DB rows:")
    cols = ['sequence_id', 'packet_received', 'simulation_time_s', 'tank_level_observed', 'q_in', 'q_out', 'pump_command', 'valve_command']
    print(df[cols].to_string())
    
    print("\nRunning through PhysicsEngine...")
    pe = PhysicsEngine(tau_p=0.035)
    # The initial level at t=0 is needed. Let's just run from t=0.
    df_all = pd.read_sql_query(f"SELECT * FROM scada_telemetry WHERE scenario_id='{run_id}' ORDER BY sequence_id", conn)
    pe.reset(df_all.iloc[0]['tank_level_observed'])
    
    results = []
    # simulate GatewayCore reusing last packet
    last_pkt = None
    
    for _, row in df_all.iterrows():
        received = row['packet_received'] == 1
        
        if received:
            last_pkt = {
                'q_in': row['q_in'],
                'q_out': row['q_out'],
                'level_m': row['tank_level_observed']
            }
            h_twin, residual, s_p = pe.step(row['q_in'], row['q_out'], row['tank_level_observed'], dt=1.0)
        else:
            # GatewayCore re-evaluates using last packet
            if last_pkt is not None:
                h_twin, residual, s_p = pe.step(last_pkt['q_in'], last_pkt['q_out'], last_pkt['level_m'], dt=1.0)
            else:
                h_twin, s_p = 0.0, 0.0
            
        if 350 <= row['sequence_id'] <= 449:
            results.append({
                'seq': row['sequence_id'],
                'received': row['packet_received'],
                'q_in': row['q_in'],
                'q_out': row['q_out'],
                'level_m': row['tank_level_observed'],
                'twin_level': h_twin,
                'physics_score': s_p
            })
            
    res_df = pd.DataFrame(results)
    print("\nResults for seq=350 to 449:")
    print(res_df.head(10).to_string())
    print("...")
    print(res_df.tail(10).to_string())
