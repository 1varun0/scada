import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pandas as pd
import numpy as np

df = pd.read_csv('data/evaluation_results.csv')

attack_types = {
    'A1': 'FDI',
    'A2': 'Replay',
    'A3': 'DoS',
    'A4': 'Auth_Misuse'
}

print("=== Attack Start Analysis: Active Alarms and Fresh Detection Delay ===")

fresh_delays_by_type = {'FDI': [], 'Replay': [], 'DoS': [], 'Auth_Misuse': []}
pre_active_counts = {'FDI': 0, 'Replay': 0, 'DoS': 0, 'Auth_Misuse': 0}
engine_flags_at_start = {'FDI': {'S_p': 0, 'S_l': 0, 'S_c': 0, 'S_a': 0},
                         'Replay': {'S_p': 0, 'S_l': 0, 'S_c': 0, 'S_a': 0},
                         'DoS': {'S_p': 0, 'S_l': 0, 'S_c': 0, 'S_a': 0},
                         'Auth_Misuse': {'S_p': 0, 'S_l': 0, 'S_c': 0, 'S_a': 0}}

for sc_id, group in df.groupby('scenario_id'):
    group = group.sort_values('sequence_id')
    prefix = sc_id[:2]
    if prefix not in attack_types:
        continue
    atype = attack_types[prefix]
    
    attack_mask = group['ground_truth'] == 1
    if not attack_mask.any():
        continue
    t_start = group.loc[attack_mask, 'simulation_time_s'].iloc[0]
    
    # Check 10 ticks before attack start
    pre_window = group[(group['simulation_time_s'] < t_start) & (group['simulation_time_s'] >= t_start - 10)]
    pre_active = bool((pre_window['predicted_anomaly'] == 1).any())
    if pre_active:
        pre_active_counts[atype] += 1
        
    # At attack start tick
    row_start = group[group['simulation_time_s'] == t_start].iloc[0]
    phy_flag = bool(row_start['S_p'] > 0.95)
    lstm_flag = bool(row_start['S_l'] > 0.95)
    pol_flag = bool(row_start['S_c'] > 0.95)
    av_flag = bool(row_start['S_a'] > 0.95)
    pred_flag = bool(row_start['predicted_anomaly'] == 1)
    
    if phy_flag: engine_flags_at_start[atype]['S_p'] += 1
    if lstm_flag: engine_flags_at_start[atype]['S_l'] += 1
    if pol_flag: engine_flags_at_start[atype]['S_c'] += 1
    if av_flag: engine_flags_at_start[atype]['S_a'] += 1
    
    # Fresh detection delay:
    post_attack = group[group['simulation_time_s'] >= t_start]
    
    if not pre_active:
        det_rows = post_attack[post_attack['predicted_anomaly'] == 1]
        fresh_delay = (det_rows.iloc[0]['simulation_time_s'] - t_start) if not det_rows.empty else np.nan
    else:
        if atype == 'FDI':
            det_rows = post_attack[post_attack['S_p'] > 0.95]
        elif atype in ['Replay', 'DoS']:
            det_rows = post_attack[post_attack['S_a'] > 0.95]
        elif atype == 'Auth_Misuse':
            det_rows = post_attack[post_attack['S_l'] > 0.95]
            
        fresh_delay = (det_rows.iloc[0]['simulation_time_s'] - t_start) if not det_rows.empty else np.nan
        
    fresh_delays_by_type[atype].append(fresh_delay)
    
    if sc_id in ['A1_001', 'A2_001', 'A3_001', 'A4_001', 'A4_002', 'A4_003', 'A4_004']:
        print(f"{sc_id} ({atype:<11}): t_start={t_start:.0f} | Pre-active in 10t before: {pre_active} | Start Flags: Phy={phy_flag} LSTM={lstm_flag} Pol={pol_flag} Av={av_flag} | Fresh Delay: {fresh_delay:.1f}s")

print("\n=== Per Attack Type Breakdown across all 90 attacks ===")
for atype, delays in fresh_delays_by_type.items():
    n_scen = len(delays)
    flags = engine_flags_at_start[atype]
    print(f"Attack Type: {atype} (N={n_scen} scenarios)")
    print(f"  Flags at t_start: Physics={flags['S_p']}/{n_scen}, LSTM={flags['S_l']}/{n_scen}, Policy(v1)={flags['S_c']}/{n_scen}, Availability={flags['S_a']}/{n_scen}")
    print(f"  Pre-attack alarmed in 10t before t_start: {pre_active_counts[atype]}/{n_scen} scenarios")
    valid_delays = [d for d in delays if not np.isnan(d)]
    print(f"  Fresh Detection Delay: Mean={np.mean(valid_delays):.2f}s, Median={np.median(valid_delays):.2f}s, Max={np.max(valid_delays):.2f}s")
