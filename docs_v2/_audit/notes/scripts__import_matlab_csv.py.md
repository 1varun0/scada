# Source File Note: `scripts/import_matlab_csv.py`

## Purpose
Import utility bridging MATLAB dataset generation with the Python pipeline. Reads 150 scenario CSV files (`N_*.csv`, `A1_*.csv`, etc.) and `attack_scenarios.csv` from `matlab/data/` and loads them into `data/scada_ids.db`.

## Public Classes and Functions
- `CSV_TO_DB_COLUMNS`: Mapping dictionary of 25 telemetry column names.
- `ATTACK_META_COLUMNS`: List of 11 attack scenario metadata column names.
- `import_telemetry_csvs(csv_dir: str, db: SCADADatabase, verbose: bool = True) -> int`: Globs all `*.csv` files except `attack_scenarios.csv`, reads via pandas, sanitizes NaNs to `None`, casts integer types, and executes `db.insert_telemetry_batch()`. Returns count of imported records.
- `import_attack_metadata(csv_dir: str, db: SCADADatabase, verbose: bool = True) -> int`: Reads `attack_scenarios.csv` and inserts into `attack_scenarios` table via `db.insert_attack_scenario()`.
- `main()`: CLI entry point supporting `--csv-dir`, `--db-path`, and `--clear`.

## Inputs and Outputs
- Inputs: CSV files in `matlab/data/` (150 scenario files each with 1,000 data rows + 1 metadata file with 90 rows).
- Outputs: Database rows written to `scada_telemetry` (150,000 rows) and `attack_scenarios` (90 rows) in `data/scada_ids.db`.

## Config Keys and Constants Read
- Defaults:
  - `csv_dir = matlab/data/` [CODE scripts/import_matlab_csv.py:179]
  - `db_path = data/scada_ids.db` via `SCADADatabase` default.

## Who Calls It
- Executed as initial setup command during Phase 1 database population.

## Side Effects
- Mutates SQLite database `data/scada_ids.db`.
- Can wipe existing database if run with `--clear`.

## Tests Covering It
- Data integrity verified by `docs_v2/_audit/outputs/query_db.py`.

## Surprising / Notable Observations
- Type casting rules: Lines 111-116 explicitly convert float/numeric values to `int` for integer columns (`sequence_id`, `data_age_ms`, `packet_received`, `pump_command`, `pump_state`, `ground_truth`, `is_authenticated`, `is_authorized`, `replay_source_sequence_id`) because MATLAB exports integers as numeric floats in CSVs.
- Total records: 150 files $\times$ 1,000 rows = 150,000 telemetry records; 90 attack scenario metadata rows.
