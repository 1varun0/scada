import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
import pandas as pd
from scada_live.scada_ids.streaming_ids import StreamingIDS, TelemetryPacket
from scada_live.common.config_loader import load_config

def main():
    conn = sqlite3.connect('c:/projects/p1/New folder/data/scada_ids.db')
    df = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'N_%' ORDER BY scenario_id, sequence_id", conn)
    
    cfg = load_config("c:/projects/p1/New folder/scada_live/config.yaml")
    cfg.ids.policy_version = "v2"
    
    fps = 0
    total_ticks = 0
    scenario_scores = {}
    
    import sys, os
    sys.path.insert(0, 'c:/projects/p1/New folder')
    from config.scenarios import get_scenario_by_id

    for sid, group in df.groupby('scenario_id'):
        ids = StreamingIDS(cfg, policy_version="v2")
        scenario_cfg = get_scenario_by_id(sid)
        if scenario_cfg:
            initial_level = scenario_cfg.initial_level_m
        else:
            # Clean start levels for normals are 1.0, 0.8, 0.5. 
            # We can round the first observed value to the nearest 0.1 to strip the noise.
            obs = group.iloc[0]['tank_level_observed']
            initial_level = round(obs * 10) / 10.0
        ids.physics_engine.reset(initial_level)
        
        for _, row in group.iterrows():
            pkt = TelemetryPacket(
                run_id=row['scenario_id'],
                ts=float(row['sequence_id']),
                seq=int(row['sequence_id']),
                src_t=float(row['sequence_id']),
                received=float(row['sequence_id']) if row['packet_received'] else 0.0,
                level_m=row['tank_level_observed'],
                q_in=row['q_in'],
                q_out=row['q_out'],
                pump_cmd=int(row['pump_command']),
                valve_cmd=float(row['valve_command']),
                pump_on=bool(row['pump_command']),
                valve_pct=float(row['valve_command'])
            )
            res = ids.update(pkt)
            is_anomaly = (res['scores']['physics'] > 0.95 or 
                          res['scores']['lstm'] > 0.95 or 
                          res['scores']['policy'] > 0.95 or 
                          res['scores']['availability'] > 0.95)
            if is_anomaly:
                fps += 1
            total_ticks += 1
            
            sid = row['scenario_id']
            lstm_score = res['scores']['lstm']
            if sid not in scenario_scores:
                scenario_scores[sid] = 0.0
            if lstm_score > scenario_scores[sid]:
                scenario_scores[sid] = lstm_score
        if lstm_score > scenario_scores[sid]:
            scenario_scores[sid] = lstm_score
            
    print(f"Normal Scenarios FPR (DB, includes 51 normals used for training/validation): {fps} FPs out of {total_ticks} ticks")
    
    # Read held-out normals dynamically from evaluation_results.csv
    eval_csv_path = "data/evaluation_results.csv"
    if os.path.exists(eval_csv_path):
        df_eval = pd.read_csv(eval_csv_path)
        held_out_ids = sorted([sid for sid in df_eval['scenario_id'].unique() if sid.startswith('N_')])
        print(f"\nHeld-out normals from {eval_csv_path} ({len(held_out_ids)} scenarios):")
        for sid in held_out_ids:
            sc_cfg = get_scenario_by_id(sid)
            op_cond = sc_cfg.operating_condition if sc_cfg else "Unknown"
            sub_eval = df_eval[df_eval['scenario_id'] == sid]
            max_s = sub_eval['S_l'].max()
            margin = 0.95 - max_s
            print(f"  {sid} ({op_cond}): max LSTM score {max_s:.3f} (margin {margin:.3f})")

if __name__ == "__main__":
    main()
