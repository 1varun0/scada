import pandas as pd
import numpy as np

def main():
    csv_path = "experiments/results/ab_comparison_results.csv"
    df = pd.read_csv(csv_path)

    cols = [
        "scenario", "mode", "seed", "attack_start", "first_flag_tick",
        "critical_tick", "takeover_tick", "overflow_ticks", "dry_run_ticks",
        "max_dev_from_setpoint"
    ]
    sub_df = df[cols].copy()

    lines = []
    lines.append("=" * 140)
    lines.append("FULL PER-SEED TABLE FROM EXPERIMENTS/RESULTS/AB_COMPARISON_RESULTS.CSV (ALL 80 RUNS)")
    lines.append("=" * 140)
    header = (
        f"{'Scenario':<14} | {'Mode':<10} | {'Seed':<4} | {'Start':<5} | "
        f"{'1stFlag':<7} | {'Crit':<6} | {'TkOver':<6} | {'OvTicks':<7} | "
        f"{'DryTicks':<8} | {'MaxDevSP (m)':<12}"
    )
    lines.append(header)
    lines.append("-" * 140)

    for sc in ["Control_FDI", "Negative_Ramp", "Positive_Ramp", "Stealthy_Ramp"]:
        for mode in ["monitor", "prevention"]:
            part = sub_df[(sub_df["scenario"] == sc) & (sub_df["mode"] == mode)]
            for _, r in part.iterrows():
                tk = str(int(r['takeover_tick'])) if r['takeover_tick'] != -1 else "N/A"
                lines.append(
                    f"{r['scenario']:<14} | {r['mode']:<10} | {int(r['seed']):<4d} | {int(r['attack_start']):<5d} | "
                    f"{int(r['first_flag_tick']):<7d} | {int(r['critical_tick']):<6d} | {tk:<6} | {int(r['overflow_ticks']):<7d} | "
                    f"{int(r['dry_run_ticks']):<8d} | {r['max_dev_from_setpoint']:<12.4f}"
                )
            lines.append("-" * 140)

    lines.append("\n" + "=" * 140)
    lines.append("EXACT SUMMARY STATISTICS (MEAN ± STD ACROSS 10 SEEDS)")
    lines.append("=" * 140)
    sum_header = (
        f"{'Scenario':<14} | {'Mode':<10} | {'Start (s)':<16} | {'1stFlag (s)':<16} | "
        f"{'Crit (s)':<16} | {'TkOver (s)':<16} | {'OvTicks':<16} | {'DryTicks':<16} | {'MaxDevSP (m)':<16}"
    )
    lines.append(sum_header)
    lines.append("-" * 140)

    for sc in ["Control_FDI", "Negative_Ramp", "Positive_Ramp", "Stealthy_Ramp"]:
        for mode in ["monitor", "prevention"]:
            part = sub_df[(sub_df["scenario"] == sc) & (sub_df["mode"] == mode)]
            m_start = f"{part['attack_start'].mean():.1f} ± {part['attack_start'].std():.1f}"
            m_flag = f"{part['first_flag_tick'].mean():.1f} ± {part['first_flag_tick'].std():.1f}"
            m_crit = f"{part['critical_tick'].mean():.1f} ± {part['critical_tick'].std():.1f}"
            if mode == "prevention":
                m_tk = f"{part['takeover_tick'].mean():.1f} ± {part['takeover_tick'].std():.1f}"
            else:
                m_tk = "N/A"
            m_ov = f"{part['overflow_ticks'].mean():.1f} ± {part['overflow_ticks'].std():.1f}"
            m_dry = f"{part['dry_run_ticks'].mean():.1f} ± {part['dry_run_ticks'].std():.1f}"
            m_dev = f"{part['max_dev_from_setpoint'].mean():.4f} ± {part['max_dev_from_setpoint'].std():.4f}"

            lines.append(
                f"{sc:<14} | {mode:<10} | {m_start:<16} | {m_flag:<16} | "
                f"{m_crit:<16} | {m_tk:<16} | {m_ov:<16} | {m_dry:<16} | {m_dev:<16}"
            )
        lines.append("-" * 140)

    output_str = "\n".join(lines)
    print(output_str)
    with open("experiments/results/ab_per_seed_output.txt", "w", encoding="utf-8") as f:
        f.write(output_str + "\n")

if __name__ == "__main__":
    main()
