# Table T06: Batch Evaluation Reproduction Verification (Stop Point 2)

> Comparing freshly executed `scripts.run_evaluation` output in isolated sandbox against committed `data/evaluation_results.csv`.

## File Hash & Dimension Verification

| Attribute | Committed Benchmark | Newly Reproduced Sandbox Output | Match Status |
| :--- | :--- | :--- | :---: |
| **File Path** | `data/evaluation_results.csv` | `results_v2/raw/reproduced_evaluation_results.csv` | - |
| **SHA-256 Hash** | `6bd6b6a1e556afcc...` | `6bd6b6a1e556afcc...` | ✅ IDENTICAL |
| **Row Count** | 99,000 | 99,000 | ✅ IDENTICAL |
| **Column Count** | 11 | 11 | ✅ IDENTICAL |

## Overall Metric Parity Comparison

| Metric | Committed Score | Reproduced Score | Absolute Difference | Relative Parity |
| :--- | :---: | :---: | :---: | :---: |
| Precision | 0.3891 | 0.3891 | 0.000000 | ✅ 100% |
| Recall | 0.9982 | 0.9982 | 0.000000 | ✅ 100% |
| F1-Score | 0.5600 | 0.5600 | 0.000000 | ✅ 100% |
| Accuracy | 0.8132 | 0.8132 | 0.000000 | ✅ 100% |
| ROC-AUC | 0.8946 | 0.8946 | 0.000000 | ✅ 100% |
| PR-AUC | 0.3905 | 0.3905 | 0.000000 | ✅ 100% |
| False Positive Rate (FPR) | 0.2118 | 0.2118 | 0.000000 | ✅ 100% |
| False Negative Rate (FNR) | 0.0018 | 0.0018 | 0.000000 | ✅ 100% |
| True Positives (TP) | 11,764 | 11,764 | 0 | ✅ 100% |
| False Positives (FP) | 18,468 | 18,468 | 0 | ✅ 100% |
| True Negatives (TN) | 68,747 | 68,747 | 0 | ✅ 100% |
| False Negatives (FN) | 21 | 21 | 0 | ✅ 100% |

## Per-Attack Class Performance Parity

| Threat Class | Metric | Committed | Reproduced | Delta | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `FDI` | Precision | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `FDI` | Recall | 0.9975 | 0.9975 | 0.000000 | ✅ EXACT |
| `FDI` | F1 | 0.9987 | 0.9987 | 0.000000 | ✅ EXACT |
| `Replay` | Precision | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `Replay` | Recall | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `Replay` | F1 | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `DoS` | Precision | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `DoS` | Recall | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `DoS` | F1 | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `Auth_Misuse` | Precision | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `Auth_Misuse` | Recall | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
| `Auth_Misuse` | F1 | 1.0000 | 1.0000 | 0.000000 | ✅ EXACT |
