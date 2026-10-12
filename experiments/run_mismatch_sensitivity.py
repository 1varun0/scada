"""
Phase 6a Extension: Plant-Model Mismatch Sensitivity Analysis

Evaluates Digital Twin takeover robustness when the physical plant parameters
deviate from the Digital Twin model:
  - Pump flow: +/- 5%
  - Valve Cv:   +/- 10%
  - Tank Area:  +/- 5%
The Digital Twin in GatewayCore maintains nominal parameters.
Evaluated across 10 random seeds on Negative Ramp and Positive Ramp scenarios.
Reports:
  - Overflow ticks (H_true >= 2.5m)
  - Dry-run ticks (H_true <= 0.05m)
  - Time twin-controlled operation first exits operational deadband [0.8, 1.2m]
  - Time twin-controlled operation first exits safety boundaries [0.3, 2.5m]
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
from experiments.run_comparison import get_attack_schedule

def run_mismatch_simulation(
    scenario_name: str, 
    seed: int, 
    delta_pump_pct: float, 
    delta_cv_pct: float, 
    delta_area_pct: float,
    duration_s: int = 2400
) -> dict:
    cfg = load_config('scada_live/config.yaml')
    cfg.simulation.clamp_flow_noise = False
    cfg.ids.dos_gap_rule = True
    
    hub = EventHub()
    # Twin uses nominal parameters inside GatewayCore
    gw = GatewayCore(cfg, hub, dos_gap_rule=True)
    gw.set_mode("prevention")
    gw.set_auto_handback(True)
    
    # Plant uses perturbed parameters
    plant = LivePlant(cfg, standalone_mode=False, seed=seed)
    plant.pump._q_max = cfg.pump.q_max_m3s * (1.0 + delta_pump_pct)
    plant.valve._cv = cfg.valve.flow_coefficient_m3s * (1.0 + delta_cv_pct)
    plant.tank._area = cfg.tank.cross_section_area_m2 * (1.0 + delta_area_pct)
    
    run_id = f"mismatch_{scenario_name}_{seed}"
    gw.current_run_id = run_id
    plant.run_id = run_id
    
    attack_start, ramp_dur = get_attack_schedule(seed)
    
    true_levels = []
    first_exit_deadband_tick = None
    first_exit_safety_tick = None
    
    for t in range(duration_s):
        true_level = plant.observe()
        
        spoof_offset = 0.0
        if scenario_name == "Negative_Ramp":
            if t >= attack_start:
                frac = min(1.0, (t - attack_start) / float(ramp_dur))
                spoof_offset = -1.5 * frac
        elif scenario_name == "Positive_Ramp":
            if t >= attack_start:
                frac = min(1.0, (t - attack_start) / float(ramp_dur))
                spoof_offset = +1.5 * frac
                
        spoofed_obs = true_level + spoof_offset
        
        # Sense step
        cmds = gw.process_sense(spoofed_obs)
        
        # Plant advance
        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        pkt.level_m = spoofed_obs
        
        # Telemetry processing & IDS verdict
        gw.process_telemetry(pkt)
        
        # Check twin-controlled operation limits during takeover
        if gw.twin_takeover_active:
            cur_level = plant.tank.level
            if (cur_level < 0.8 or cur_level > 1.2) and first_exit_deadband_tick is None:
                first_exit_deadband_tick = t
            if (cur_level < 0.3 or cur_level > 2.5) and first_exit_safety_tick is None:
                first_exit_safety_tick = t
                
        true_levels.append(plant.tank.level)
        
    true_arr = np.array(true_levels)
    overflow_ticks = int(np.sum(true_arr >= 2.5))
    dry_run_ticks = int(np.sum(true_arr <= 0.05))
    
    return {
        "scenario": scenario_name,
        "seed": seed,
        "delta_pump_pct": delta_pump_pct,
        "delta_cv_pct": delta_cv_pct,
        "delta_area_pct": delta_area_pct,
        "overflow_ticks": overflow_ticks,
        "dry_run_ticks": dry_run_ticks,
        "first_exit_deadband_tick": first_exit_deadband_tick if first_exit_deadband_tick is not None else -1,
        "first_exit_safety_tick": first_exit_safety_tick if first_exit_safety_tick is not None else -1,
        "min_level": float(np.min(true_arr)),
        "max_level": float(np.max(true_arr))
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
    sys.stdout = Tee('experiments/results/mismatch_sensitivity_output.txt')
    print("=" * 115)
    print("EXTENSION STUDY: DIGITAL TWIN PARAMETER MISMATCH SENSITIVITY (10 SEEDS)")
    print("=" * 115)
    print("Parameter Perturbations Applied to Plant (Twin Retains Nominal Constants):")
    print("  - Case A (Positive Mismatch): Pump +5%, Valve Cv +10%, Tank Area +5%")
    print("  - Case B (Negative Mismatch): Pump -5%, Valve Cv -10%, Tank Area -5%")
    print("  - Case C (Opposing Stress 1): Pump +5%, Valve Cv -10%, Tank Area -5% (Max accumulation rate)")
    print("  - Case D (Opposing Stress 2): Pump -5%, Valve Cv +10%, Tank Area +5% (Max depletion rate)\n")
    
    seeds = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    cases = [
        ("Case_A (+5%, +10%, +5%)", +0.05, +0.10, +0.05),
        ("Case_B (-5%, -10%, -5%)", -0.05, -0.10, -0.05),
        ("Case_C (+5%P, -10%Cv, -5%A)", +0.05, -0.10, -0.05),
        ("Case_D (-5%P, +10%Cv, +5%A)", -0.05, +0.10, +0.05),
    ]
    
    all_results = []
    
    header = (
        f"{'Case':<28} | {'Scenario':<13} | {'Mean Ov Ticks':<14} | {'Mean Dry Ticks':<14} | "
        f"{'First Exit [0.8, 1.2]':<22} | {'First Exit [0.3, 2.5]':<22}"
    )
    print(header)
    print("-" * 115)
    
    for case_label, dp, dc, da in cases:
        for sc in ["Negative_Ramp", "Positive_Ramp"]:
            case_runs = []
            for seed in seeds:
                res = run_mismatch_simulation(sc, seed, dp, dc, da, duration_s=2400)
                case_runs.append(res)
                all_results.append({**res, "case": case_label})
                
            df_case = pd.DataFrame(case_runs)
            mean_ov = f"{df_case['overflow_ticks'].mean():.1f} ± {df_case['overflow_ticks'].std():.1f}"
            mean_dry = f"{df_case['dry_run_ticks'].mean():.1f} ± {df_case['dry_run_ticks'].std():.1f}"
            
            # Format exit ticks
            ex_db = df_case[df_case["first_exit_deadband_tick"] != -1]["first_exit_deadband_tick"]
            ex_db_str = f"t ~ {ex_db.mean():.0f} s ({len(ex_db)}/10 seeds)" if len(ex_db) > 0 else "None (0/10 seeds)"
            
            ex_sf = df_case[df_case["first_exit_safety_tick"] != -1]["first_exit_safety_tick"]
            ex_sf_str = f"t ~ {ex_sf.mean():.0f} s ({len(ex_sf)}/10 seeds)" if len(ex_sf) > 0 else "None (0/10 seeds)"
            
            print(f"{case_label:<28} | {sc:<13} | {mean_ov:<14} | {mean_dry:<14} | {ex_db_str:<22} | {ex_sf_str:<22}")
            
    print("-" * 115)
    
    os.makedirs("experiments/results", exist_ok=True)
    df_all = pd.DataFrame(all_results)
    df_all.to_csv("experiments/results/mismatch_sensitivity_results.csv", index=False)
    print("Saved complete sensitivity dataset to experiments/results/mismatch_sensitivity_results.csv\n")

if __name__ == "__main__":
    main()
