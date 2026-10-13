# Progress Tracker: SCADA Hybrid IDS Results Reproduction (results_v2)

## Current Status
- Phase: Stop Point 2 Reached (Phase D1 Batch Evaluation Reproduction Verified)
- Active Task: Awaiting User Approval to Proceed to Phase D2 & E (Ablations & Sweeps)
- Context Usage: Normal

## Tasks Done
- [x] Initialized `results_v2/` directory structure and `README.md`.
- [x] A1. Recorded environment specs (commit hash `27d13c2`, clean git status, Windows 11, Python 3.12.6, pip freeze, Intel i5-10300H 4C/8T, 15.84 GB RAM, GTX 1650, PyTorch 2.5.1+cu121, NumPy 2.3.3, Pandas 2.3.2, Scikit-Learn 1.7.2, and clean scaler pickle check) in `results_v2/_env/`.
- [x] A2. Computed SHA-256 baseline hashes for all 434 tracked files (plus `data/scada_ids.db` and `checkpoints/*`) outside `results_v2/` into `results_v2/_audit/hashes_before.txt`.
- [x] A2. Built isolated sandbox copy at `C:\Users\varun\AppData\Local\Temp\p1_sandbox` containing all 434 files.
- [x] A2. Verified sandbox runs `python -m pytest tests -q` before anything else (`66 passed in 2.04s`, exit code 0). Captured verbatim log and sidecar JSON in `results_v2/raw/a2_sandbox_pytest_tests_q.log` and `.json`.
- [x] Stop Point 1 reached & approved by user: Environment and Sandbox setup completed.
- [x] B1. Executed `python -m pytest tests -v --durations=20` (66 passed in 4.04s) and `python -m pytest scada_live/tests -v --durations=20` (116 passed in 257.28s) in sandbox. Raw verbatim logs and JSON sidecars saved to `results_v2/raw/b1_pytest_*`.
- [x] B1. Generated summary table `results_v2/tables/t01_test_suites_summary.md` and parsed record `results_v2/raw/parsed_test_suites_run1.json`.
- [x] B2. Re-executed both test suites for determinism (Core: 66 passed in 2.79s, Live: 116 passed in 257.71s). Generated audit comparison in `results_v2/_audit/determinism.md` confirming 100% item-level determinism (182/182 identical outcomes).
- [x] C. Executed read-only queries against sandbox DB and `data_split_v1.json` via `results_v2/scripts/query_dataset_facts.py`. Saved raw JSON dumps (`c1_database_facts.json`, `c2_split_facts.json`, `c3_signal_statistics.json`) and generated markdown tables:
  - `t02_database_schema_and_counts.md`: PRAGMA schemas and table inventory.
  - `t03_attack_scenarios_breakdown.md`: Threat profiles, windows, and telemetry ingress totals (150k rows, 1,035 dropped packets).
  - `t04_dataset_split_and_coverage.md`: Partition verification (42 train, 9 val, 9 test normal, 90 test attacks; 0 leakage).
  - `t05_signal_statistics_by_scenario_type.md`: Min/mean/max water levels, flow rates, and pump duty cycles per group.
- [x] D1. Executed `python -m scripts.run_evaluation` in sandbox (259.26s, exit code 0). Captured verbatim log `results_v2/raw/d1_run_evaluation.log` and sidecar JSON.
- [x] D1. Copied produced CSV to `results_v2/raw/reproduced_evaluation_results.csv` and ROC curve to `results_v2/figures/reproduced_roc_curve.png`.
- [x] D1. Executed `results_v2/scripts/compare_evaluation_reproduction.py` generating `results_v2/raw/d1_reproduction_diff.json` and `results_v2/tables/t06_batch_evaluation_reproduction_comparison.md`. Confirmed **100% bit-for-bit identical reproduction** (SHA-256 match `6bd6b6a1e556afcca920d2b936a723ed88f7326da14d6234c5e077dd3c4c5ac0`, 0 deltas across all 99,000 rows and all metrics).
- [x] Stop Point 2 reached: Batch Evaluation Reproduction verified bit-for-bit identical.

## Active / Next Tasks
- [ ] D2. Offline threshold ablations and single-engine ablations (`scripts.run_ablation`).
- [ ] E. Parameter sweeps and sensitivity analyses (`experiments/run_constant_bias_sweep.py`, `experiments/run_mismatch_sensitivity.py`).

## Blockers
- None. Awaiting user 'continue' at Stop Point 2.
