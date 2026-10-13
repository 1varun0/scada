# Final Audit & Verification Report — SCADA Hybrid IDS (results_v2)

- **Date of Completion**: 2026-10-13
- **Auditor Role**: Measurement Engineer
- **Baseline Git Commit**: `27d13c2`
- **Execution Target**: Cleanroom Sandbox at `%TEMP%\p1_sandbox`
- **Integrity Status**: **100% BIT-FOR-BIT IDENTICAL OUTSIDE `results_v2/`**

---

## 1. Compliance with Absolute Audit Rules

1. **Rule 1 (Zero Modification Outside `results_v2/`)**:
   - Cryptographic SHA-256 verification of all 434 base tracked files (`hashes_after.txt` vs `hashes_before.txt`) confirmed **0 differences**.
   - Git working tree status confirmed **0 files touched outside `results_v2/`**.
2. **Rule 2 (Zero Hallucination / Grounded Reality)**:
   - Every metric, duration, percentage, and table row across this campaign originated from direct command execution recorded in [`results_v2/raw/`](../raw/) and tabulated via scripts in [`results_v2/scripts/`](../scripts/).
3. **Rule 3 (Stop Points Observed & Approved)**:
   - **Stop Point 1 (Environment & Sandbox Setup)**: Acknowledged and approved.
   - **Stop Point 2 (Batch Evaluation Reproduction)**: Acknowledged and approved.
   - **Stop Point 3 (Live System Results)**: Acknowledged and approved.
   - **Stop Point 4 (Final Wrap-up Presentation)**: Reached in this report.

---

## 2. Core Scientific & Empirical Results

| Verification Item | Target Artifact | Key Empirical Result | Status |
| :--- | :--- | :---: | :---: |
| **Unit Test Suite** | `tests/` | 66 passed in 4.04s (Run 1) and 2.79s (Run 2) | ✅ 100% Pass |
| **Live Test Suite** | `scada_live/tests/` | 116 passed in 257.28s (Run 1) and 257.71s (Run 2) | ✅ 100% Pass |
| **Determinism Parity** | `tests/` + `scada_live/tests/` | 182 / 182 identical outcomes between Run 1 and Run 2 | ✅ 100% Deterministic |
| **Batch Benchmark Hash** | `data/evaluation_results.csv` | SHA-256: `6bd6b6a1e556afcca920d2b936a723ed88f7326da14d6234c5e077dd3c4c5ac0` | ✅ Exact Hash Match |
| **Batch Precision / Recall / F1** | 99,000 timesteps | Precision = 0.3891, Recall = 0.9982, F1 = 0.5600 | ✅ $\Delta = 0.000000$ |
| **ROC-AUC Score** | Overall hybrid ensemble | Area Under Curve = 0.8946 | ✅ $\Delta = 0.000000$ |
| **Single-Engine Ablations** | C1 through C7 | C1 (Physics F1: 0.4720), C2 (LSTM F1: 0.4468), C3 (Physics+LSTM F1: 0.6071) | ✅ Verified (Table T07) |
| **Sensor Bias Sweep** | 0 to 5 cm (10 seeds) | Biases $\ge 4\text{ cm}$ detected in 2.1s; 0.017% false alarms at 0cm | ✅ Verified (Table T09) |
| **Active Prevention A/B** | AM-1 to AM-7 (10 seeds) | Prevention mode achieves 0.0 overflow/dry ticks on cyber threats | ✅ 100% Mitigation (T10) |
| **Parameter Mismatch** | 8 cases (160 runs) | Safety bounds $[0.3, 2.5\text{ m}]$ never left over 2400s horizon | ✅ 0 Safety Breaches (T12) |
| **Fresh Attack Latency** | 90 attack scenarios | Detection delay = 0.00s; pre-attack false alarms = 0 / 90 | ✅ 0.00s Latency (T13) |
| **Live End-to-End Demo** | `run_demo.py --auto` | 354s simulated time: 0 overflows, 0 dry-runs, 100% TPR, 0.0% FPR | ✅ Complete Parity (T14) |

---

## 3. Deliverables Summary

- **14 Generated Markdown Tables**: [`results_v2/tables/`](../tables/) (`T01` to `T14`)
- **15 Technical Audit Documents**: [`results_v2/docs/`](../docs/) (`R00` to `R14`)
- **Raw Log Archives & Sidecars**: [`results_v2/raw/`](../raw/) (`b1`, `b2`, `c1-c3`, `d1`, `d2`, `e1-e5`, `f1`, `g1`)
- **Cryptographic Provenance**: [`results_v2/_audit/hashes_before.txt`](hashes_before.txt) and [`hashes_after.txt`](hashes_after.txt) (identical).
