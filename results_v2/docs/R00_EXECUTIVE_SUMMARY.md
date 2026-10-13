# R00: Executive Summary — SCADA Hybrid IDS Empirical Audit & Measurement Report

## 1. Audit & Measurement Mandate

This report documents the exhaustive, code-grounded measurement and reproduction of the **SCADA Hybrid Intrusion Detection and Prevention System (IDS/IPS)**. The audit was conducted strictly under cleanroom isolation protocols:
- **Zero Modifications**: No existing code, config, database, test, or documentation file outside `results_v2/` was modified, moved, renamed, or deleted.
- **External Execution Sandbox**: All computational experiments, test suites, batch benchmarks, and live simulations were executed exclusively within an isolated sandbox environment located at `C:\Users\varun\AppData\Local\Temp\p1_sandbox`.
- **Zero Hallucination Standard**: Every figure, metric, and percentage cited across this document set originates directly from executed processes whose raw outputs are captured verbatim in [`results_v2/raw/`](file:///c:/projects/p1/New%20folder/results_v2/raw/) and tabulated via automated scripts in [`results_v2/tables/`](file:///c:/projects/p1/New%20folder/results_v2/tables/).

---

## 2. Key Empirical Findings & Verdicts

### A. Batch Pipeline Reproduction (Bit-for-Bit Exact)
Execution of the offline 99-scenario evaluation pipeline ([`scripts/run_evaluation.py`](file:///c:/projects/p1/New%20folder/scripts/run_evaluation.py)) produced a dataset of 99,000 timesteps whose raw CSV output matches the repository's committed benchmark ([`data/evaluation_results.csv`](file:///c:/projects/p1/New%20folder/data/evaluation_results.csv)) **bit-for-bit**:
- **Committed SHA-256**: `6bd6b6a1e556afcca920d2b936a723ed88f7326da14d6234c5e077dd3c4c5ac0`
- **Reproduced SHA-256**: `6bd6b6a1e556afcca920d2b936a723ed88f7326da14d6234c5e077dd3c4c5ac0`
- **Discrepancy Delta**: Exactly `0.000000` across all floating-point engine scores ($S_p, S_l, S_c, S_a, S_{\text{hybrid}}$) and categorical predictions across all 99,000 evaluated records.

### B. Test Suite Determinism (100% Item-Level Parity)
Two consecutive executions of the complete test battery (66 unit/batch tests + 116 live streaming & gateway tests = 182 total tests) demonstrated **100% determinism**:
- **Batch Suite (`tests/`)**: 66 passed in 4.04s (Run 1) and 2.79s (Run 2).
- **Live Suite (`scada_live/tests/`)**: 116 passed in 257.28s (Run 1) and 257.71s (Run 2).
- **Determinism Check**: All 182 individual test items yielded bit-for-bit identical outcomes across runs ([`results_v2/_audit/determinism.md`](file:///c:/projects/p1/New%20folder/results_v2/_audit/determinism.md)).

### C. Dataset Integrity & Partitioning
Direct queries against the SQLite database ([`data/scada_ids.db`](file:///c:/projects/p1/New%20folder/data/scada_ids.db)) and partition manifest ([`checkpoints/data_split_v1.json`](file:///c:/projects/p1/New%20folder/checkpoints/data_split_v1.json)) confirm:
- **Total Records**: 150,000 rows across 150 scenarios (60 normal, 90 attack).
- **Zero Partition Leakage**: Exactly 0 training normal scenarios and 0 validation normal scenarios appear in the 99-scenario test evaluation set.
- **Ingress Regularity**: Exactly 1,000 ticks per scenario; 1,035 dropped packets strictly confined to DoS attack windows.

### D. Multi-Threat Classification Performance
The frozen hybrid ensemble evaluates incoming SCADA telemetry using physics-based mass balance ($S_p$), LSTM autoencoder reconstruction ($S_l$), state-boundary policy ($S_c$), and availability timing ($S_a$):
- **Overall Metrics**: Precision = **38.91%**, Recall = **99.82%**, F1 = **56.00%**, ROC-AUC = **0.8946**, PR-AUC = **0.3905**.
- **Low Precision Mechanism**: Driven by background false positive ticks during normal operating phases ($FP = 18,468$ ticks out of 87,215 negative ground truth ticks, $FPR = 21.18\%$).
- **Per-Attack Precision**: When sliced within specific attack scenario runs, attack-class detection achieves **Precision = 1.000, Recall = 0.997–1.000, F1 = 0.999–1.000**.
- **Detection Latency**: Fresh detection delay at attack onset across all 90 attacks is **0.00s**, with **0 pre-attack false alarms** in the 10 ticks prior to attack onset.

### E. Live Active Defense & Prevention Stability
The live closed-loop streaming pipeline ([`scada_live/`](file:///c:/projects/p1/New%20folder/scada_live/)) demonstrates proven active defense capabilities:
- **Digital Twin Takeover**: During False Data Injection (FDI), the gateway replaces corrupted sensor telemetry with Digital Twin state estimation within $\le 3$ ticks, maintaining tank water level safely inside $[0.89\text{ m}, 1.00\text{ m}]$.
- **Zero Physical Harm**: In Phase 6b A/B testing across 10 evaluation seeds, Prevention Mode eliminated all physical overflows ($121.0\text{t} \rightarrow 0.0\text{t}$) and dry-runs ($151.0\text{t} \rightarrow 0.0\text{t}$) seen in Monitor Mode.
- **Physical Invariance of Wire Tampering**: Downstream wire tampering post-gateway was detected in 0 ticks with 17 consistency alerts, while physical harm remained identical in both modes, validating the theoretical constraint that network ingress filtering cannot alter downstream physical wire modifications.
- **Plant-Model Mismatch Tolerance**: Across 8 mismatch cases (area $\pm 5\%$, flowmeter bias $\pm 5\%$, unmeasured leak $+2\%$, actuator variations) spanning 160 runs over a 2400-second horizon, the physical safety envelope $[0.3\text{ m}, 2.5\text{ m}]$ was **never breached (0/160 runs)**.

---

## 3. High-Level Master Results Scorecard

| Evaluation Domain | Metric / Property | Committed Reference | Newly Measured Value | Verification Status | Primary Evidence Citation |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Test Suites** | Total Passing Tests | 182 | **182 / 182 (100%)** | ✅ Identical | [`t01_test_suites_summary.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t01_test_suites_summary.md) |
| **Determinism** | Run 1 vs Run 2 Item Match | 182 | **182 / 182 (100%)** | ✅ Identical | [`determinism.md`](file:///c:/projects/p1/New%20folder/results_v2/_audit/determinism.md) |
| **Dataset Size** | Total Records & Scenarios | 150k / 150 | **150,000 / 150** | ✅ Identical | [`t02_database_schema_and_counts.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t02_database_schema_and_counts.md) |
| **Test Partition** | Evaluated Scenarios | 99 | **99 (9 Norm + 90 Atk)** | ✅ Identical | [`t04_dataset_split_and_coverage.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t04_dataset_split_and_coverage.md) |
| **Batch Eval Hash** | SHA-256 of `evaluation_results.csv` | `6bd6b6a1...` | `6bd6b6a1...` | ✅ Bit-for-bit Exact | [`t06_batch_evaluation_reproduction_comparison.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t06_batch_evaluation_reproduction_comparison.md) |
| **Batch Metrics** | Overall F1 / Recall / Precision | 0.5600 / 0.9982 / 0.3891 | **0.5600 / 0.9982 / 0.3891** | ✅ Exact ($\Delta = 0$) | [`t06_batch_evaluation_reproduction_comparison.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t06_batch_evaluation_reproduction_comparison.md) |
| **ROC-AUC** | Area Under ROC Curve | 0.8946 | **0.8946** | ✅ Exact ($\Delta = 0$) | [`d1_run_evaluation.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/d1_run_evaluation.log) |
| **Sensor Bias Sweep** | $P(\text{CRITICAL})$ at $\ge 4\text{ cm}$ bias | 100% | **100.0% (10/10 seeds)** | ✅ Verified | [`t09_constant_bias_sweep.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t09_constant_bias_sweep.md) |
| **Safety Rule** | False alarms on 60 Normals | 0 | **0 / 60,000 ticks (0%)** | ✅ Verified | [`t08_gateway_safety_rule_evaluation.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t08_gateway_safety_rule_evaluation.md) |
| **Prevention A/B** | Mitigation Rate (AM-1 to AM-7) | 100% | **100% (All 10 seeds)** | ✅ Verified | [`t10_auth_misuse_prevention_ab.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t10_auth_misuse_prevention_ab.md) |
| **Model Mismatch** | Safety Boundary Violations | 0 | **0 / 160 runs (0%)** | ✅ Verified | [`t12_plant_model_mismatch_sensitivity.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t12_plant_model_mismatch_sensitivity.md) |
| **Fresh Latency** | Detection Delay at $t_{\text{start}}$ | 0.0s | **0.00s across 90 attacks** | ✅ Verified | [`t13_fresh_detection_latency.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t13_fresh_detection_latency.md) |
| **Live Demo** | Overflows / Dry-Runs in Live Demo | 0 / 0 | **0 / 0 (Level: 0.89-1.00m)**| ✅ Verified | [`t14_live_demo_execution_summary.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t14_live_demo_execution_summary.md) |

---

## 4. Document Map for `results_v2/docs/`

The subsequent documentation chapters provide exhaustive deep dives into each functional domain:
- **[R01: Environment & Provenance](file:///c:/projects/p1/New%20folder/results_v2/docs/R01_ENVIRONMENT_AND_PROVENANCE.md)**: Hardware, OS, runtime libraries, git commit hash, and clean scaler check.
- **[R02: Test Suite Verification](file:///c:/projects/p1/New%20folder/results_v2/docs/R02_TEST_SUITE_VERIFICATION.md)**: Detailed breakdown of all 182 test cases across batch and live suites.
- **[R03: Dataset Truth & Coverage](file:///c:/projects/p1/New%20folder/results_v2/docs/R03_DATASET_TRUTH_AND_COVERAGE.md)**: Schema inspection, row counts, threat windows, and zero-leakage split verification.
- **[R04: Batch Evaluation Reproduction](file:///c:/projects/p1/New%20folder/results_v2/docs/R04_BATCH_EVALUATION_REPRODUCTION.md)**: Hash verification, row-level deltas, and confusion matrices.
- **[R05: Model Architecture & Inference](file:///c:/projects/p1/New%20folder/results_v2/docs/R05_MODEL_ARCHITECTURE_AND_INFERENCE.md)**: PyTorch LSTM Autoencoder architecture, preprocessor scaling, and GPU inference.
- **[R06: Threshold Ablations & Sensitivity](file:///c:/projects/p1/New%20folder/results_v2/docs/R06_THRESHOLD_ABLATIONS_AND_SENSITIVITY.md)**: Single-engine vs hybrid configurations (C1–C7) and optimal thresholds.
- **[R07: Physical Simulation Fidelity](file:///c:/projects/p1/New%20folder/results_v2/docs/R07_PHYSICAL_SIMULATION_FIDELITY.md)**: Mass balance, Torricelli outflow, noise models, and plant-twin equivalence.
- **[R08: Live Streaming Pipeline](file:///c:/projects/p1/New%20folder/results_v2/docs/R08_LIVE_STREAMING_PIPELINE.md)**: Architecture of the Flask API, SSE event hub, watchdog, and gateway client.
- **[R09: Prevention Mechanisms Evaluation](file:///c:/projects/p1/New%20folder/results_v2/docs/R09_PREVENTION_MECHANISMS_EVALUATION.md)**: Digital Twin takeover, handback gating, command filtering, and wire tamper checking.
- **[R10: Attack Detection Latency](file:///c:/projects/p1/New%20folder/results_v2/docs/R10_ATTACK_DETECTION_LATENCY.md)**: Pre-alarm analysis, fresh detection delays, and sliding window dynamics.
- **[R11: Edge Cases & Safety Limits](file:///c:/projects/p1/New%20folder/results_v2/docs/R11_EDGE_CASES_AND_SAFETY_LIMITS.md)**: Sensor bias sweeps, plant-model parameter mismatch, and 30-minute soak stability.
- **[R12: Resource Consumption & Benchmarks](file:///c:/projects/p1/New%20folder/results_v2/docs/R12_RESOURCE_CONSUMPTION_AND_BENCHMARKS.md)**: Wall-clock execution durations, GPU/CPU throughput, and memory profiles.
- **[R13: Reproducibility Audit Trail](file:///c:/projects/p1/New%20folder/results_v2/docs/R13_REPRODUCIBILITY_AUDIT_TRAIL.md)**: Sandbox replication steps, sidecar JSON metadata, and git commit history.
- **[R14: Discrepancy & Limitations Register](file:///c:/projects/p1/New%20folder/results_v2/docs/R14_DISCREPANCY_AND_LIMITATIONS_REGISTER.md)**: Unbiased analysis of background false alarm rates, Policy v1 dormancy, and wire tamper bounds.
