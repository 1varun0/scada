"""
Compares the reproduced evaluation_results.csv from sandbox against the committed
data/evaluation_results.csv, computing hashes, row-level diffs, and metric comparisons.

Usage:
    python results_v2/scripts/compare_evaluation_reproduction.py
"""
import hashlib
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import (
    precision_score, recall_score, f1_score, accuracy_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMMITTED_CSV = REPO_ROOT / "data" / "evaluation_results.csv"
REPRODUCED_CSV = REPO_ROOT / "results_v2" / "raw" / "reproduced_evaluation_results.csv"

RAW_DIR = REPO_ROOT / "results_v2" / "raw"
TABLES_DIR = REPO_ROOT / "results_v2" / "tables"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_metrics(y_true, y_pred, y_score):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "fpr": float(fpr),
        "fnr": float(fnr)
    }


def main():
    if not REPRODUCED_CSV.exists():
        raise FileNotFoundError(f"Missing {REPRODUCED_CSV}")

    committed_hash = sha256_of_file(COMMITTED_CSV)
    reproduced_hash = sha256_of_file(REPRODUCED_CSV)

    df_comm = pd.read_csv(COMMITTED_CSV)
    df_repr = pd.read_csv(REPRODUCED_CSV)

    shape_match = df_comm.shape == df_repr.shape
    cols_match = list(df_comm.columns) == list(df_repr.columns)

    # Numerical difference analysis
    float_cols = ['S_p', 'S_l', 'S_c', 'S_a', 'S_hybrid']
    col_diffs = {}
    for col in float_cols:
        if col in df_comm.columns and col in df_repr.columns:
            diff = np.abs(df_comm[col].values - df_repr[col].values)
            col_diffs[col] = {
                "max_abs_diff": float(np.max(diff)),
                "mean_abs_diff": float(np.mean(diff)),
                "exact_equal_fraction": float(np.mean(diff == 0.0))
            }

    # Integer discrete columns match
    int_cols = ['predicted_anomaly', 'ground_truth', 'sequence_id']
    int_diffs = {}
    for col in int_cols:
        if col in df_comm.columns and col in df_repr.columns:
            mismatches = int(np.sum(df_comm[col].values != df_repr[col].values))
            int_diffs[col] = {
                "mismatch_count": mismatches,
                "fraction_match": float(np.mean(df_comm[col].values == df_repr[col].values))
            }

    # Classification metrics comparison
    comm_metrics = compute_metrics(df_comm['ground_truth'], df_comm['predicted_anomaly'], df_comm['S_hybrid'])
    repr_metrics = compute_metrics(df_repr['ground_truth'], df_repr['predicted_anomaly'], df_repr['S_hybrid'])

    # Per attack type comparison
    attack_breakdown = {}
    for atype in ['FDI', 'Replay', 'DoS', 'Auth_Misuse']:
        c_sub = df_comm[df_comm['attack_type'] == atype]
        r_sub = df_repr[df_repr['attack_type'] == atype]
        if len(c_sub) > 0 and len(r_sub) > 0:
            attack_breakdown[atype] = {
                "committed": compute_metrics(c_sub['ground_truth'], c_sub['predicted_anomaly'], c_sub['S_hybrid']),
                "reproduced": compute_metrics(r_sub['ground_truth'], r_sub['predicted_anomaly'], r_sub['S_hybrid'])
            }

    summary = {
        "committed_sha256": committed_hash,
        "reproduced_sha256": reproduced_hash,
        "exact_hash_match": committed_hash == reproduced_hash,
        "shape_committed": list(df_comm.shape),
        "shape_reproduced": list(df_repr.shape),
        "shape_match": shape_match,
        "columns_match": cols_match,
        "float_column_diffs": col_diffs,
        "int_column_diffs": int_diffs,
        "committed_overall_metrics": comm_metrics,
        "reproduced_overall_metrics": repr_metrics,
        "per_attack_breakdown": attack_breakdown
    }

    (RAW_DIR / "d1_reproduction_diff.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Generate markdown table
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    t06_lines = [
        "# Table T06: Batch Evaluation Reproduction Verification (Stop Point 2)",
        "",
        "> Comparing freshly executed `scripts.run_evaluation` output in isolated sandbox against committed `data/evaluation_results.csv`.",
        "",
        "## File Hash & Dimension Verification",
        "",
        "| Attribute | Committed Benchmark | Newly Reproduced Sandbox Output | Match Status |",
        "| :--- | :--- | :--- | :---: |",
        f"| **File Path** | `data/evaluation_results.csv` | `results_v2/raw/reproduced_evaluation_results.csv` | - |",
        f"| **SHA-256 Hash** | `{committed_hash[:16]}...` | `{reproduced_hash[:16]}...` | {'✅ IDENTICAL' if committed_hash == reproduced_hash else '⚠️ DIFFERENCE DETECTED'} |",
        f"| **Row Count** | {len(df_comm):,} | {len(df_repr):,} | {'✅ IDENTICAL' if len(df_comm) == len(df_repr) else '❌ MISMATCH'} |",
        f"| **Column Count** | {len(df_comm.columns)} | {len(df_repr.columns)} | {'✅ IDENTICAL' if len(df_comm.columns) == len(df_repr.columns) else '❌ MISMATCH'} |",
        "",
        "## Overall Metric Parity Comparison",
        "",
        "| Metric | Committed Score | Reproduced Score | Absolute Difference | Relative Parity |",
        "| :--- | :---: | :---: | :---: | :---: |"
    ]

    metric_names = [
        ("Precision", "precision"),
        ("Recall", "recall"),
        ("F1-Score", "f1"),
        ("Accuracy", "accuracy"),
        ("ROC-AUC", "roc_auc"),
        ("PR-AUC", "pr_auc"),
        ("False Positive Rate (FPR)", "fpr"),
        ("False Negative Rate (FNR)", "fnr"),
        ("True Positives (TP)", "tp"),
        ("False Positives (FP)", "fp"),
        ("True Negatives (TN)", "tn"),
        ("False Negatives (FN)", "fn")
    ]

    for label, key in metric_names:
        c_val = comm_metrics[key]
        r_val = repr_metrics[key]
        diff = abs(c_val - r_val)
        if isinstance(c_val, int):
            t06_lines.append(f"| {label} | {c_val:,} | {r_val:,} | {diff:,} | {'✅ 100%' if diff == 0 else f'Δ {diff}'} |")
        else:
            t06_lines.append(f"| {label} | {c_val:.4f} | {r_val:.4f} | {diff:.6f} | {'✅ 100%' if diff < 1e-6 else f'{diff:.6f}'} |")

    t06_lines.extend([
        "",
        "## Per-Attack Class Performance Parity",
        "",
        "| Threat Class | Metric | Committed | Reproduced | Delta | Status |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |"
    ])

    for atype in ['FDI', 'Replay', 'DoS', 'Auth_Misuse']:
        b = attack_breakdown[atype]
        for m in ['precision', 'recall', 'f1']:
            cv = b['committed'][m]
            rv = b['reproduced'][m]
            d = abs(cv - rv)
            status = "✅ EXACT" if d < 1e-6 else f"Δ {d:.4f}"
            t06_lines.append(f"| `{atype}` | {m.capitalize()} | {cv:.4f} | {rv:.4f} | {d:.6f} | {status} |")

    out_file = TABLES_DIR / "t06_batch_evaluation_reproduction_comparison.md"
    out_file.write_text("\n".join(t06_lines) + "\n", encoding="utf-8")
    print(f"Generated {out_file} successfully.")


if __name__ == "__main__":
    main()
