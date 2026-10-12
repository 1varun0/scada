import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import numpy as np
import pandas as pd
from scipy.integrate import quad

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub

def get_attack_schedule(seed: int):
    rng = np.random.RandomState(seed)
    attack_start = int(rng.randint(200, 601))
    ramp_duration = int(rng.randint(1000, 1401))
    return attack_start, ramp_duration

def ode_overflow_time(h_start: float, h_end: float = 2.50) -> float:
    """Analytical ODE time to overflow under full inflow (pump ON, valve 50%).
    dh/dt = (Qin - Qout)/A = (0.005 - 0.002*sqrt(h))/2.0 = 0.0025 - 0.001*sqrt(h)
    """
    if h_start >= h_end:
        return 0.0
    res, _ = quad(lambda h: 1.0 / (0.0025 - 0.001 * np.sqrt(h)), h_start, h_end)
    return float(res)

def ode_dry_run_time(h_start: float, h_end: float = 0.05) -> float:
    """Analytical ODE time to dry-run under pure drainage (pump OFF, valve 50%).
    dh/dt = -0.002*sqrt(h)/2.0 = -0.001*sqrt(h)
    t = 2*(sqrt(h_start) - sqrt(h_end)) / 0.001 = 2000 * (sqrt(h_start) - sqrt(h_end))
    """
    if h_start <= h_end:
        return 0.0
    res, _ = quad(lambda h: 1.0 / (0.001 * np.sqrt(h)), h_end, h_start)
    return float(res)

def main():
    os.makedirs("experiments/results", exist_ok=True)
    seeds = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    
    cfg = load_config("scada_live/config.yaml")
    cfg.simulation.clamp_flow_noise = False
    cfg.ids.dos_gap_rule = True

    lines = []
    lines.append("=" * 135)
    lines.append("STRICT MEASURED LATCH AND ODE VERIFICATION ACROSS ALL 10 SEEDS (NO BACK-FITTING)")
    lines.append("=" * 135)
    lines.append("Definitions:")
    lines.append("  - Latch Tick: First tick t_latch >= t_start after which pump stays ON (state=1) continuously to t=2399 (Negative Ramp)")
    lines.append("                or stays OFF (state=0) continuously to t=2399 (Positive Ramp).")
    lines.append("  - h_latch: True plant water level measured at t = t_latch.")
    lines.append("  - t_ODE: Exact numerical integration via scipy.integrate.quad.")
    lines.append("  - Pred Tick: t_latch + t_ODE.")
    lines.append("  - Obs Tick: First tick in the simulation where true level hits threshold (>= 2.50m for overflow, <= 0.05m for dry-run).")
    lines.append("  - Ov/Dry Ticks: Total simulation ticks where true level meets the threshold (matches ab_comparison_results.csv).")
    lines.append("  - Discrepancy: Obs Tick - Pred Tick.\n")

    # 1. Negative Ramp
    lines.append("-" * 135)
    lines.append("1. NEGATIVE RAMP (OVERFLOW THREAT, TARGET H >= 2.50 M):")
    lines.append(
        f"{'Seed':<5} | {'Start':<6} | {'t_latch':<8} | {'h_latch (m)':<12} | "
        f"{'t_ODE (s)':<10} | {'Pred Tick':<11} | {'Obs Tick':<10} | {'OvTicks':<8} | {'Discrepancy (s)':<15}"
    )
    lines.append("-" * 135)

    neg_rows = []
    for s in seeds:
        t_start, ramp_dur = get_attack_schedule(s)
        gw = GatewayCore(cfg, EventHub(), dos_gap_rule=True)
        gw.set_mode("monitor")
        plant = LivePlant(cfg, standalone_mode=False, seed=s)
        
        pump_states = []
        true_levels = []
        for t in range(2400):
            obs = plant.observe()
            spoof = -1.5 * min(1.0, (t - t_start) / float(ramp_dur)) if t >= t_start else 0.0
            cmds = gw.process_sense(obs + spoof)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            pkt.level_m = obs + spoof
            gw.process_telemetry(pkt)
            pump_states.append(plant.pump.state)
            true_levels.append(plant.tank.level)
            
        # Find latch tick: first tick after which pump stays 1 continuously to 2399
        latch_tick = t_start
        for t in range(2399, t_start - 1, -1):
            if pump_states[t] != 1:
                latch_tick = t + 1
                break
                
        h_latch = true_levels[latch_tick]
        t_ode = ode_overflow_time(h_latch, 2.50)
        pred_tick = latch_tick + t_ode
        
        obs_tick = next((t for t in range(2400) if true_levels[t] >= 2.50), None)
        ov_ticks = sum(1 for lvl in true_levels if lvl >= 2.50)
        disc = (obs_tick - pred_tick) if obs_tick is not None else float("nan")
        
        neg_rows.append({
            "seed": s, "start": t_start, "latch": latch_tick, "h_latch": h_latch,
            "t_ode": t_ode, "pred": pred_tick, "obs": obs_tick, "ov_ticks": ov_ticks, "disc": disc
        })
        lines.append(
            f"{s:<5d} | {t_start:<6d} | {latch_tick:<8d} | {h_latch:<12.4f} | "
            f"{t_ode:<10.1f} | {pred_tick:<11.1f} | {obs_tick:<10d} | {ov_ticks:<8d} | {disc:<+15.2f}"
        )
    lines.append("-" * 135)
    df_neg = pd.DataFrame(neg_rows)
    lines.append(
        f"{'Mean':<5} | {df_neg['start'].mean():<6.1f} | {df_neg['latch'].mean():<8.1f} | {df_neg['h_latch'].mean():<12.4f} | "
        f"{df_neg['t_ode'].mean():<10.1f} | {df_neg['pred'].mean():<11.1f} | {df_neg['obs'].mean():<10.1f} | "
        f"{df_neg['ov_ticks'].mean():<8.1f} | {df_neg['disc'].mean():<+15.2f}\n"
    )

    # 2. Positive Ramp
    lines.append("-" * 135)
    lines.append("2. POSITIVE RAMP (DRY-RUN THREAT, TARGET H <= 0.05 M):")
    lines.append(
        f"{'Seed':<5} | {'Start':<6} | {'t_latch':<8} | {'h_latch (m)':<12} | "
        f"{'t_ODE (s)':<10} | {'Pred Tick':<11} | {'Obs Tick':<10} | {'DryTicks':<8} | {'Discrepancy (s)':<15}"
    )
    lines.append("-" * 135)

    pos_rows = []
    for s in seeds:
        t_start, ramp_dur = get_attack_schedule(s)
        gw = GatewayCore(cfg, EventHub(), dos_gap_rule=True)
        gw.set_mode("monitor")
        plant = LivePlant(cfg, standalone_mode=False, seed=s)
        
        pump_states = []
        true_levels = []
        for t in range(2400):
            obs = plant.observe()
            spoof = +1.5 * min(1.0, (t - t_start) / float(ramp_dur)) if t >= t_start else 0.0
            cmds = gw.process_sense(obs + spoof)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            pkt.level_m = obs + spoof
            gw.process_telemetry(pkt)
            pump_states.append(plant.pump.state)
            true_levels.append(plant.tank.level)
            
        # Find latch tick: first tick after which pump stays 0 continuously to 2399
        latch_tick = t_start
        for t in range(2399, t_start - 1, -1):
            if pump_states[t] != 0:
                latch_tick = t + 1
                break
                
        h_latch = true_levels[latch_tick]
        t_ode = ode_dry_run_time(h_latch, 0.05)
        pred_tick = latch_tick + t_ode
        
        obs_tick = next((t for t in range(2400) if true_levels[t] <= 0.05), None)
        dry_ticks = sum(1 for lvl in true_levels if lvl <= 0.05)
        disc = (obs_tick - pred_tick) if obs_tick is not None else float("nan")
        
        pos_rows.append({
            "seed": s, "start": t_start, "latch": latch_tick, "h_latch": h_latch,
            "t_ode": t_ode, "pred": pred_tick, "obs": obs_tick, "dry_ticks": dry_ticks, "disc": disc
        })
        lines.append(
            f"{s:<5d} | {t_start:<6d} | {latch_tick:<8d} | {h_latch:<12.4f} | "
            f"{t_ode:<10.1f} | {pred_tick:<11.1f} | {obs_tick:<10d} | {dry_ticks:<8d} | {disc:<+15.2f}"
        )
    lines.append("-" * 135)
    df_pos = pd.DataFrame(pos_rows)
    lines.append(
        f"{'Mean':<5} | {df_pos['start'].mean():<6.1f} | {df_pos['latch'].mean():<8.1f} | {df_pos['h_latch'].mean():<12.4f} | "
        f"{df_pos['t_ode'].mean():<10.1f} | {df_pos['pred'].mean():<11.1f} | {df_pos['obs'].mean():<10.1f} | "
        f"{df_pos['dry_ticks'].mean():<8.1f} | {df_pos['disc'].mean():<+15.2f}"
    )
    lines.append("=" * 135)

    output_str = "\n".join(lines)
    print(output_str)
    out_path = "experiments/results/compute_latch_output.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_str + "\n")
    print(f"\nSaved latch output to {out_path}")

if __name__ == "__main__":
    main()
