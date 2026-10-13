# Source File Note: `scripts/run_evaluation.py`

## Purpose
Main pipeline evaluation driver. Loads all 90 attack scenarios and 9 held-out test normal scenarios from SQLite, runs the 4 detection engines in sequence, applies max-vote hybrid fusion ($\tau_{\text{fusion}}=0.95$), saves per-tick records to `data/evaluation_results.csv`, and generates summary metrics.

## Public Classes and Functions
- `load_test_data(db_path="data/scada_ids.db", test_normal_ids=None) -> pd.DataFrame`: Reads all rows where `scenario_id LIKE 'A%'` (90,000 rows) plus rows for `test_normal_ids` (9,000 rows). Total: 99,000 rows.
- `get_initial_level_for_scenario(scenario_id: str) -> float`: Looks up nominal deterministic initial level from `config/scenarios.py` (e.g. 0.4m or 2.1m for A4, 1.0m for steady state, 0.5m for recovery).
- `main()`:
  - Initializes `PhysicsEngine(tau_p=0.035)`, `PolicyEngine(epsilon_m=0.05)`, `AvailabilityEngine(tau_a_ms=1500.0, tau_a_max_ms=5000.0)`.
  - Loads PyTorch LSTM Autoencoder from `checkpoints/lstm_ae_v1.pt` and `MinMaxScaler` from `checkpoints/scaler_v1.pkl`.
  - Configures `FusionEngine(w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25, tau_fusion=0.95, strategy="max_vote")`.
  - Steps through each of the 99 scenarios, writing per-tick results into pre-allocated NumPy arrays.
  - Exports DataFrame to `data/evaluation_results.csv`.
  - Computes and prints classification metrics and latencies; plots ROC curve to `reports/roc_curve.png`.

## Inputs and Outputs
- Inputs:
  - `data/scada_ids.db` (`scada_telemetry` table).
  - `checkpoints/data_split_v1.json` (`test_normal_ids`).
  - `checkpoints/lstm_ae_v1.pt`.
  - `checkpoints/scaler_v1.pkl`.
- Outputs:
  - Writes `data/evaluation_results.csv` (99,001 lines: header + 99,000 rows).
  - Writes `reports/roc_curve.png`.

## Config Keys and Constants Read
- `PARAMS.simulation.dt_s` [CODE scripts/run_evaluation.py:132] (1.0 s)
- Hardcoded detection parameters: `tau_p = 0.035`, `tau_l = 0.0085`, `tau_a_ms = 1500.0`, `tau_a_max_ms = 5000.0`, `tau_fusion = 0.95`.

## Who Calls It
- Executed via CLI: `python scripts/run_evaluation.py`.

## Side Effects
- Overwrites `data/evaluation_results.csv` and `reports/roc_curve.png`.

## Tests Covering It
- Core evaluation driver; outputs verified by `experiments/*`.

## Surprising / Notable Observations
- Policy engine version: Line 135 invokes `policy_engine.evaluate(...)` (Policy v1), rather than `evaluate_v2(...)`. This explains why the batch results stored in `data/evaluation_results.csv` exhibit zero policy detections for A4 scenarios.
- Window buffer warmup: For the first 9 steps of each scenario (`sequence_id` 0 to 8), `len(window_buffer) < 10`, so `s_l` is fixed at `0.0`. The LSTM-AE only begins inference starting at step index 9.
- Initial level selection: Uses `get_initial_level_for_scenario` to re-seed the physics twin at the true nominal initial level rather than the noisy `tank_level_observed` at $t=0$.
