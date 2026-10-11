import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import pandas as pd
import numpy as np
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.common.packets import TelemetryPacket

def run_a3_gap_analysis():
    cfg = load_config('scada_live/config.yaml')
    conn = sqlite3.connect('data/scada_ids.db')

    A = cfg.tank.cross_section_area_m2
    qin_max = cfg.pump.q_max_m3s
    cv = cfg.valve.flow_coefficient_m3s
    h_max = cfg.tank.max_height_m

    v_max = max(qin_max / A, cv * (h_max**0.5) / A)
    sigma = float(cfg.simulation.sensor_noise_level_m)
    max_std = float(cfg.recalibration.max_std_m)

    print(f"Config: A={A:.1f} m2, Qin_max={qin_max:.4f} m3/s, Cv={cv:.4f} m3/s, h_max={h_max:.1f} m")
    print(f"v_max = max(Qin_max/A, Cv*sqrt(h_max)/A) = max({qin_max/A:.4f}, {cv*(h_max**0.5)/A:.5f}) = {v_max:.6f} m/s")
    print(f"sigma_sensor = {sigma:.4f} m, max_std_m = {max_std:.4f} m\n")

    header = f"{'Scenario':<8} | {'G':<3} | {'m':<7} | {'std':<7} | {'twin':<7} | {'|m - twin|':<10} | {'band':<7} | {'Decision':<8}"
    print(header)
    print("-" * len(header))

    results = []
    for i in range(1, 16):
        sid = f"A3_{i:03d}"
        df = pd.read_sql_query(
            f"SELECT * FROM scada_telemetry WHERE scenario_id='{sid}' ORDER BY sequence_id", conn
        )
        dos_rows = df[df['packet_received'] == 0]
        G = len(dos_rows)
        t_end = int(dos_rows['simulation_time_s'].max())

        # Step a fresh StreamingIDS with dos_gap_rule=False to obtain the true un-reseeded twin state
        ids = StreamingIDS(cfg, policy_version="v2", dos_gap_rule=False)
        ids.reset(df.iloc[0]['tank_level_observed'], sid)

        twin_at_eval = None
        for _, row in df.iterrows():
            t = int(row['simulation_time_s'])
            rcvd = bool(row['packet_received'] == 1)
            pkt = TelemetryPacket(
                run_id=sid, seq=int(row['sequence_id']), ts=float(t), src_t=float(t),
                received=rcvd, level_m=float(row['tank_level_observed']),
                q_in=float(row['q_in']), q_out=float(row['q_out']),
                pump_cmd=int(row['pump_command']), valve_cmd=float(row['valve_command']),
                pump_on=bool(row['pump_state'] == 1), valve_pct=float(row['valve_state'])
            )
            # Before the 5th post-DoS packet steps, capture the twin estimate
            if t == t_end + 5:
                twin_at_eval = ids.get_twin_estimate()
            ids.update(pkt)
            if t == t_end + 5:
                break

        post_5 = df[(df['simulation_time_s'] > t_end) & (df['simulation_time_s'] <= t_end + 5)]
        levels = post_5['tank_level_observed'].tolist()
        m = float(np.median(levels))
        std = float(np.std(levels, ddof=1))
        diff = abs(m - twin_at_eval)
        band = v_max * G * float(cfg.simulation.dt_s) + 3.0 * sigma

        decision = "RE-SEED" if (diff <= band and std <= max_std) else "REFUSE"
        row_str = f"{sid:<8} | {G:<3} | {m:<7.4f} | {std:<7.4f} | {twin_at_eval:<7.4f} | {diff:<10.4f} | {band:<7.4f} | {decision:<8}"
        print(row_str)
        results.append((sid, G, m, std, twin_at_eval, diff, band, decision))

    conn.close()
    return results

if __name__ == "__main__":
    run_a3_gap_analysis()
