"""
Parses reproduced ablation results and generates table T07.
Usage:
    python results_v2/scripts/parse_ablation_results.py
"""
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SANDBOX_REPORT = Path("C:/Users/varun/AppData/Local/Temp/p1_sandbox/reports/ablation_results.md")
RAW_REPORT = REPO_ROOT / "results_v2" / "raw" / "reproduced_ablation_results.md"
TABLES_DIR = REPO_ROOT / "results_v2" / "tables"


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    if SANDBOX_REPORT.exists():
        shutil.copy2(SANDBOX_REPORT, RAW_REPORT)

    content = RAW_REPORT.read_text(encoding="utf-8")
    
    header = [
        "# Table T07: Component Ablation Study Results (C1 - C7)",
        "",
        "> Source: Executed `scripts.run_ablation` in isolated sandbox copy.",
        "> Generated from `results_v2/raw/reproduced_ablation_results.md` (Raw runner log `results_v2/raw/d2_run_ablation.log`).",
        "",
        "## Multi-Engine Configuration Performance Matrix",
        ""
    ]
    
    # Strip existing title and prepend our formatted header
    lines = content.splitlines()
    table_lines = [l for l in lines if l.startswith("|")]
    
    out_file = TABLES_DIR / "t07_ablation_study_results.md"
    out_file.write_text("\n".join(header + table_lines) + "\n", encoding="utf-8")
    print(f"Generated {out_file} successfully.")


if __name__ == "__main__":
    main()
