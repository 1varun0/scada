# Source File Note: dashboard/app.py

## 1. Purpose
Implements the legacy batch dashboard Flask web application for inspecting pre-recorded scenarios stored in SQLite (`data/scada_ids.db`) alongside evaluation scores from `data/evaluation_results.csv` [CODE dashboard/app.py:1-11, 40-71].

## 2. Public Classes / Functions / Endpoints
- `get_db_connection()` [CODE dashboard/app.py:13-17]: Opens a connection to `../data/scada_ids.db` with a 10.0-second lock timeout and `sqlite3.Row` row factory.
- Route `GET /` (`index()`) [CODE dashboard/app.py:19-21]: Renders `templates/index.html`.
- Route `GET /api/scenarios` (`api_scenarios()`) [CODE dashboard/app.py:23-34]: Queries `SELECT DISTINCT scenario_id FROM scada_telemetry ORDER BY scenario_id`, returns JSON list of string scenario IDs.
- Route `GET /api/telemetry/<scenario_id>` (`api_telemetry(scenario_id)`) [CODE dashboard/app.py:35-75]:
  - Reads telemetry columns (`sequence_id`, `simulation_time_s`, `tank_level_observed`, `pump_state`, `valve_state`, `q_in`, `q_out`, `attack_type`, `ground_truth`) from `scada_telemetry`.
  - Checks if `../data/evaluation_results.csv` exists; if so, reads and filters by `scenario_id`, then merges columns `['sequence_id', 'S_p', 'S_l', 'S_c', 'S_a', 'S_hybrid', 'predicted_anomaly']` on `sequence_id` via pandas [CODE dashboard/app.py:56-67].
  - Returns JSON dict with columnar lists (`to_dict(orient='list')`).
- Main block [CODE dashboard/app.py:76-77]: Runs Flask on port 5000 (`debug=True`).

## 3. Inputs and Outputs
- **Inputs**: HTTP requests to `/`, `/api/scenarios`, `/api/telemetry/<scenario_id>`.
- **Outputs**: HTML page, JSON array of scenario IDs, or JSON columnar telemetry and scores.

## 4. Config Keys or Constants Read
- Hardcoded relative path to `../data/scada_ids.db` [CODE dashboard/app.py:9].
- Hardcoded relative path to `../data/evaluation_results.csv` [CODE dashboard/app.py:56].
- Default port 5000 [CODE dashboard/app.py:77].

## 5. Who Calls It
- User running manual command `python dashboard/app.py` for visual inspection of batch scenarios.

## 6. Side Effects
- Opens SQLite connection to `data/scada_ids.db` for read queries (`SELECT`).
- Reads `data/evaluation_results.csv`.

## 7. Tests Covering It
- None directly in `tests/` (it is an auxiliary batch visualization UI).

## 8. Surprises, Mismatches, or Dead Code
- The code explicitly comments: `# We need to query evaluation_results from CSV or check if it exists in DB. # Wait, run_evaluation.py writes to evaluation_results.csv, not the database directly! # Let's read from CSV and merge in pandas.` [CODE dashboard/app.py:40-42]. This confirms that evaluation results are never written to the SQLite `evaluation_results` table, leaving that table empty in the committed database.
- Front-end threshold line in `app.js` is hard-coded to 0.95 (`Array(times.length).fill(0.95)`) [CODE dashboard/static/app.js:143], whereas `config/parameters.py` defines `TAU_HYBRID = 0.85` or max-vote logic.
