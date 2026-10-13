# Progress Tracker: SCADA Hybrid IDS Results Reproduction (results_v2)

## Current Status
- Phase: Phase C Complete (Dataset Facts & Statistics Recorded)
- Active Task: Phase D1 (Batch Evaluation Reproduction - Stop Point 2)
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

## Active / Next Tasks
- [ ] D1. Run `python -m scripts.run_evaluation` in sandbox copy, compare output against committed `data/evaluation_results.csv`, generate table T06, and reach Stop Point 2.

## Blockers
- None. Proceeding to Phase D1.
