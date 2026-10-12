"""
Phase 6a Step 3 Follow-up: No-Attack Prevention Soak Comparison

Evaluates GatewayCore Prevention mode on unattacked normal runs across 10 seeds:
  - Durations: 30 minutes (1800 s) and 60 minutes (3600 s)
  - Noise conditions:
      (a) clamp_flow_noise = True  (Dataset noise: asymmetric non-negative clamp)
      (b) clamp_flow_noise = False (Zero-mean symmetric Gaussian noise)
Reports:
  - False-takeover ticks per seed
  - First false takeover tick per seed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
import pandas as pd

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.common.packets import TelemetryPacket

def run_soak(seed: int, duration_s: int, clamp_flow: bool) -> dict:
    cfg = load_config('scada_live/config.yaml')
    cfg.simulation.clamp_flow_noise = clamp_flow
    cfg.ids.dos_gap_rule = True
    
    hub = EventHub()
    gw = GatewayCore(cfg, hub, dos_gap_rule=True)
    gw.set_mode("prevention")
    gw.set_auto_handback(True)
    
    plant = LivePlant(cfg, standalone_mode=False, seed=seed)
    run_id = f"soak_seed{seed}_{duration_s}s_clamp{clamp_flow}"
    gw.current_run_id = run_id
    plant.run_id = run_id
    
    false_takeover_ticks = 0
    first_false_takeover_tick = None
    
    for t in range(duration_s):
        obs = plant.observe()
        cmds = gw.process_sense(obs)
        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        pkt.level_m = obs
        verdict = gw.process_telemetry(pkt)
        
        if gw.twin_takeover_active:
            false_takeover_ticks += 1
            if first_false_takeover_tick is None:
                first_false_takeover_tick = t
                
    return {
        "seed": seed,
        "duration_s": duration_s,
        "duration_min": duration_s // 60,
        "clamp_flow_noise": clamp_flow,
        "false_takeover_ticks": false_takeover_ticks,
        "first_false_takeover_tick": first_false_takeover_tick if first_false_takeover_tick is not None else -1
    }

class Tee:
    def __init__(self, filepath):
        self.file = open(filepath, "w", encoding="utf-8")
        self.stdout = sys.stdout
    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
    def flush(self):
        self.file.flush()
        self.stdout.flush()

def main():
    os.makedirs('experiments/results', exist_ok=True)
    sys.stdout = Tee('experiments/results/soak_comparison_output.txt')
    seeds = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    durations = [1800, 3600] # 30 min, 60 min
    
    print("=" * 105)
    print("NO-ATTACK PREVENTION SOAK ANALYSIS: CLAMPED (DATASET) VS UNCLAMPED NOISE (10 SEEDS)")
    print("=" * 105)
    
    all_runs = []
    
    for dur in durations:
        for clamp in [True, False]:
            label = f"{dur//60}-Min ({'Clamped / Dataset' if clamp else 'Unclamped / Gaussian'})"
            print(f"\n--- Running {label} Soak across 10 seeds ---")
            dur_runs = []
            for s in seeds:
                res = run_soak(seed=s, duration_s=dur, clamp_flow=clamp)
                dur_runs.append(res)
                all_runs.append(res)
                
            df_sub = pd.DataFrame(dur_runs)
            mean_ft = df_sub['false_takeover_ticks'].mean()
            std_ft = df_sub['false_takeover_ticks'].std()
            first_ticks = df_sub[df_sub['first_false_takeover_tick'] != -1]['first_false_takeover_tick']
            
            first_str = f"Earliest: t={first_ticks.min()} s, Mean: t={first_ticks.mean():.0f} s ({len(first_ticks)}/10 seeds)" if len(first_ticks) > 0 else "None (0/10 seeds had false takeover)"
            print(f"Summary for {label}:")
            print(f"  False Takeover Ticks: {mean_ft:.1f} ± {std_ft:.1f} ticks (Total across seeds: {df_sub['false_takeover_ticks'].sum()})")
            print(f"  First False Takeover: {first_str}")
            print(f"  Per-seed takeover ticks: {df_sub['false_takeover_ticks'].tolist()}")
            print(f"  Per-seed first tick:     {df_sub['first_false_takeover_tick'].tolist()}")

    os.makedirs("experiments/results", exist_ok=True)
    df_all = pd.DataFrame(all_runs)
    df_all.to_csv("experiments/results/soak_comparison_results.csv", index=False)
    print("\nSaved soak comparison results to experiments/results/soak_comparison_results.csv")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    main()
