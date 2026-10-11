import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import pandas as pd
from config.parameters import PARAMS
from config.scenarios import get_scenario_by_id
from engines.physics_engine import PhysicsEngine

def main():
    conn = sqlite3.connect('data/scada_ids.db')
    df = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A3_001' ORDER BY sequence_id", conn)
    conn.close()

    sc_cfg = get_scenario_by_id('A3_001')
    initial_level = sc_cfg.initial_level_m if sc_cfg else 1.0

    pe = PhysicsEngine(tau_p=0.035)
    pe.reset(initial_level)

    rows = []
    first_sp_flag = None

    for _, row in df.iterrows():
        h_twin, residual, s_p = pe.step(row['q_in'], row['q_out'], row['tank_level_observed'], PARAMS.simulation.dt_s)
        seq = int(row['sequence_id'])
        gt = int(row['ground_truth'])
        
        if gt == 0 and s_p > 0.95 and first_sp_flag is None and seq > 370:
            first_sp_flag = (seq, s_p, row['tank_level_observed'], h_twin, residual)

        if 340 <= seq <= 480:
            rows.append({
                't': seq,
                'recv': int(row['packet_received']),
                'gt': gt,
                'q_in': f"{row['q_in']:.5f}",
                'q_out': f"{row['q_out']:.5f}",
                'h_obs': f"{row['tank_level_observed']:.4f}",
                'h_twin': f"{h_twin:.4f}",
                'resid': f"{residual:.4f}",
                'S_p': f"{s_p:.4f}",
            })

    res_df = pd.DataFrame(rows)
    print("=== A3_001 REAL BATCH PHYSICS PATH (t=340 to 480) ===")
    print(res_df.to_string(index=False))

    print("\nFirst out-of-attack tick with S_p > 0.95:")
    if first_sp_flag:
        seq, s_p, obs, twin, res = first_sp_flag
        print(f"t={seq}: S_p={s_p:.4f}, h_obs={obs:.4f}, h_twin={twin:.4f}, residual={res:.4f}")
    else:
        print("None! S_p never exceeded 0.95 outside attack.")

if __name__ == '__main__':
    main()
