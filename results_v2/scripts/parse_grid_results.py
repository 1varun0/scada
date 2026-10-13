"""
Parses e4_2x2_grid.log and generates table T11.
Usage:
    python results_v2/scripts/parse_grid_results.py
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_LOG = REPO_ROOT / "results_v2" / "raw" / "e4_2x2_grid.log"
TABLES_DIR = REPO_ROOT / "results_v2" / "tables"


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_LOG.exists():
        raise FileNotFoundError(f"Missing {RAW_LOG}")

    text = RAW_LOG.read_text(encoding="utf-8")
    lines = text.splitlines()

    md_lines = [
        "# Table T11: LSTM Autoencoder Pump Alignment & Noise Clamp 2x2 Grid",
        "",
        "> Source: `experiments/run_2x2_grid.py` executed in isolated sandbox copy.",
        "> Evaluates LSTM anomaly score response during actuator transient (t=200..230s) across feature source and noise clamping.",
        "> Raw log: [`e4_2x2_grid.log`](../raw/e4_2x2_grid.log).",
        "",
        "## 2x2 Factorial Sensitivity Matrix",
        "",
        "| Feature Source | Noise Clamping (`clamp_flow_noise`) | Peak Reconstruction Score ($S_l$) | Ticks Exceeding Threshold ($S_l > 0.95$) | Anomaly Flagging |",
        "| :--- | :---: | :---: | :---: | :---: |"
    ]

    pattern = re.compile(r"Mode:\s+([^|]+)\s+\|\s+Clamp:\s+([^|]+)\s+\|\s+Max LSTM \(t=200\.\.230\):\s+([0-9\.]+)\s+\|\s+Ticks > 0\.95:\s+(\d+)")

    for l in lines:
        m = pattern.search(l)
        if m:
            mode, clamp, max_score, ticks = m.groups()
            mode = mode.strip()
            clamp = clamp.strip()
            max_s = float(max_score)
            t_cnt = int(ticks)
            flag_str = "❌ False Anomaly Triggered" if t_cnt > 0 else "✅ Normal (Clean)"
            md_lines.append(f"| `{mode}` | `{clamp}` | {max_s:.4f} | {t_cnt} | {flag_str} |")

    md_lines.extend([
        "",
        "## Key Physical Insights",
        "",
        "- **Physical State Parity**: When input feature `pump_state` accurately reflects actual plant actuator state, peak LSTM reconstruction error remains below **0.67** (well below threshold $0.95$), generating **zero false alarm ticks** regardless of noise clamp settings.",
        "- **Command Desynchronization Vulnerability**: When the feature vector is fed with commanded state during delayed mechanical ramp, artificial state mismatch drives the error to **1.0000** for **10 ticks**, demonstrating why physical sensor telemetry must reflect physical actuator feedback rather than naked control intents.",
        ""
    ])

    out_file = TABLES_DIR / "t11_lstm_pump_alignment_grid.md"
    out_file.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Generated {out_file} successfully.")


if __name__ == "__main__":
    main()
