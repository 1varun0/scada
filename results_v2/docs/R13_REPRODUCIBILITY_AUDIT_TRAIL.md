# R13: Reproducibility Audit Trail & Step-by-Step Replication Protocol

## 1. Cleanroom Replication Protocol

To replicate the entirety of results documented in this audit report on any compatible Windows/Linux host, execute the following steps in sequence:

### Step 1: Environment Inspection & Sandbox Construction
```bash
# Record environment specifications
python results_v2/scripts/record_env.py

# Record baseline cryptographic hashes of all 434 tracked files
python results_v2/scripts/hash_tree.py results_v2/_audit/hashes_before.txt

# Construct isolated sandbox copy in temp directory
python results_v2/scripts/build_sandbox.py
```

### Step 2: Test Suite Execution & Determinism Verification
```bash
# Execute Run 1
python results_v2/scripts/runner_util.py b1_pytest_tests_run1 python -m pytest tests -v --durations=20
python results_v2/scripts/runner_util.py b1_pytest_scada_live_tests_run1 python -m pytest scada_live/tests -v --durations=20
python results_v2/scripts/parse_test_results.py --run 1

# Execute Run 2 (Determinism Verification)
python results_v2/scripts/runner_util.py b2_pytest_tests_run2 python -m pytest tests -v --durations=20
python results_v2/scripts/runner_util.py b2_pytest_scada_live_tests_run2 python -m pytest scada_live/tests -v --durations=20
python results_v2/scripts/parse_test_results.py --run 2
python results_v2/scripts/compare_test_runs.py
```

### Step 3: Dataset Facts & Ingress Extraction
```bash
python results_v2/scripts/query_dataset_facts.py
```

### Step 4: Batch Evaluation Reproduction & Parity Check
```bash
python results_v2/scripts/runner_util.py d1_run_evaluation python -m scripts.run_evaluation
python -c "import shutil; shutil.copy2('C:/Users/varun/AppData/Local/Temp/p1_sandbox/data/evaluation_results.csv', 'results_v2/raw/reproduced_evaluation_results.csv')"
python results_v2/scripts/compare_evaluation_reproduction.py
```

### Step 5: Parameter Sweeps, Ablations & Live Benchmarks
```bash
# Single-Engine Ablations
python results_v2/scripts/runner_util.py d2_run_ablation python -m scripts.run_ablation
python results_v2/scripts/parse_ablation_results.py

# Gateway Safety Rule Offline Audit
python results_v2/scripts/runner_util.py e1_gateway_rule_validation python experiments/validate_gateway_rule.py
python results_v2/scripts/parse_gateway_rule_results.py

# Constant Sensor Bias Sweep
python results_v2/scripts/runner_util.py e2_constant_bias_sweep python experiments/run_constant_bias_sweep.py
python results_v2/scripts/parse_constant_bias_sweep.py

# Authorization Misuse A/B Verification
python results_v2/scripts/runner_util.py e3_auth_misuse_ab python experiments/run_auth_misuse_ab.py
python results_v2/scripts/parse_auth_misuse_ab.py

# LSTM 2x2 Factorial Grid
python results_v2/scripts/runner_util.py e4_2x2_grid python experiments/run_2x2_grid.py
python results_v2/scripts/parse_grid_results.py

# Plant-Model Mismatch Sensitivity
python results_v2/scripts/runner_util.py e5_mismatch_sensitivity python experiments/run_mismatch_sensitivity.py
python results_v2/scripts/parse_mismatch_sensitivity.py

# Fresh Detection Latency Audit
python results_v2/scripts/runner_util.py f1_fresh_latency python experiments/compute_fresh_latency.py
python results_v2/scripts/parse_fresh_latency.py

# Full Automated Live System Demonstration
python results_v2/scripts/runner_util.py g1_live_demo python run_demo.py --auto --exit-on-finish --speed 10.0
python results_v2/scripts/parse_live_demo.py
```

---

## 2. Git Commit Progression Trail

Every phase of the measurement campaign was committed sequentially with granular, descriptive commit messages:

1. **Commit [`c7dab66`](file:///c:/projects/p1/New%20folder/results_v2/_env/)**: `results_v2: A. Environment and sandbox setup`
   - Created folder hierarchy, recorded hardware and Python specs, hashed 434 base files, and initialized execution sandbox.
2. **Commit [`f22e8aa`](file:///c:/projects/p1/New%20folder/results_v2/tables/t01_test_suites_summary.md)**: `results_v2: B. Test suites execution and determinism`
   - Executed Run 1 and Run 2 for both test suites (182 tests) and verified 100% item-level determinism.
3. **Commit [`d48456e`](file:///c:/projects/p1/New%20folder/results_v2/tables/t02_database_schema_and_counts.md)**: `results_v2: C. Dataset facts and statistics`
   - Extracted table schemas, record counts, partition coverage, and physical signal statistics.
4. **Commit [`7cde4ad`](file:///c:/projects/p1/New%20folder/results_v2/tables/t06_batch_evaluation_reproduction_comparison.md)**: `results_v2: D1. Batch evaluation reproduction`
   - Re-executed 99-scenario batch pipeline and verified bit-for-bit SHA-256 hash match against committed benchmark.
5. **Commit [`04aa92a`](file:///c:/projects/p1/New%20folder/results_v2/tables/t07_ablation_study_results.md)**: `results_v2: D2 & E. Ablations, sweeps, and sensitivity analyses`
   - Component ablations C1-C7, constant bias sweeps, auth misuse A/B verification, 2x2 grid, and mismatch sensitivity.
6. **Commit [`4e8376b`](file:///c:/projects/p1/New%20folder/results_v2/tables/t13_fresh_detection_latency.md)**: `results_v2: F & G. Live latency, streaming, and automated demonstration`
   - Pre-attack alarm audit, fresh latency measurements, and automated live system demonstration.
