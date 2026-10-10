import sqlite3
import pandas as pd
from scada_live.scada_ids.streaming_ids import StreamingIDS, TelemetryPacket
from scada_live.common.config_loader import load_config

def main():
    conn = sqlite3.connect('c:/projects/p1/New folder/data/scada_ids.db')
    df = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id LIKE 'N_%' ORDER BY scenario_id, sequence_id", conn)
    
    cfg = load_config("c:/projects/p1/New folder/scada_live/config.yaml")
    cfg.ids.policy_version = "v2"
    
    ids = StreamingIDS(cfg, policy_version="v2")
    
    fps = 0
    total_ticks = 0
    scenario_scores = {}
    
    for _, row in df.iterrows():
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
            
    print(f"Normal Scenarios FPR (DB, includes 51 normals used for training/validation): {fps} FPs out of {total_ticks} ticks")
    
    print("\nHeld-out normals (N_052 to N_060):")
    for sid in [f"N_{str(i).zfill(3)}" for i in range(52, 61)]:
        if sid in scenario_scores:
            max_s = scenario_scores[sid]
            margin = 0.95 - max_s
            print(f"  {sid}: max LSTM score {max_s:.3f} (margin {margin:.3f})")

if __name__ == "__main__":
    main()
