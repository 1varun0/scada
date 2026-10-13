# Source File Note: `storage/sqlite_client.py`

## Purpose
Manages SQLite database interactions under Write-Ahead Logging (WAL) mode. Handles table creation, indexes, batch inserts, and parameterized queries for `scada_telemetry`, `attack_scenarios`, `experiment_runs`, and `evaluation_results`.

## Public Classes and Functions
- `class SCADADatabase(db_path: str | None = None)`
  - `connect() -> None`: Establishes connection, sets `PRAGMA journal_mode=WAL;`, `PRAGMA foreign_keys=ON;`, and `row_factory = sqlite3.Row`.
  - `close() -> None`: Closes SQLite connection.
  - `initialize() -> None`: Executes DDL creating tables `scada_telemetry`, `attack_scenarios`, `experiment_runs`, `evaluation_results`, and indexes `idx_telemetry_scenario`, `idx_telemetry_attack`.
  - `insert_telemetry_batch(records: List[Dict[str, Any]]) -> None`: Bulk executes `INSERT OR REPLACE INTO scada_telemetry` across 25 schema columns.
  - `query_telemetry(scenario_id: str = None, attack_type: str = None, limit: int = None) -> List[Dict[str, Any]]`: Filtered telemetry query ordered by `(scenario_id, sequence_id)`.
  - `get_scenario_ids(attack_type: str = None) -> List[str]`: Retrieves unique scenario IDs.
  - `count_records(scenario_id: str = None) -> int`: Returns record count.
  - `insert_attack_scenario(record: Dict[str, Any]) -> None`: Inserts attack metadata.
  - `insert_experiment_run(record: Dict[str, Any]) -> None`: Inserts experiment run metadata, JSON-encoding nested structures.
  - `insert_evaluation_batch(records: List[Dict[str, Any]]) -> None`: Inserts predictions into `evaluation_results`.
  - `query_evaluation(experiment_id: str, scenario_id: str = None) -> List[Dict[str, Any]]`: Queries evaluation records.
  - `clear_telemetry()`, `clear_all()`: Administrative truncate methods.
  - `get_wal_mode() -> str`: Verifies journal mode.

## Inputs and Outputs
- `insert_telemetry_batch`: Input list of telemetry dicts.
- `query_telemetry`: Output list of row dicts.

## Config Keys and Constants Read
- Default database filepath: `_DEFAULT_DB_PATH = data/scada_ids.db` [CODE storage/sqlite_client.py:22].

## Who Calls It
- `simulator.scenario_runner`
- `scripts.import_matlab_csv`
- `dashboard.app`

## Side Effects
- Modifies SQLite database file on disk (`data/scada_ids.db` and accompanying `-wal` / `-shm` files).

## Tests Covering It
- Storage and data pipeline tests.

## Surprising / Notable Observations
- Upsert behavior: Uses `INSERT OR REPLACE INTO` across all batch insert methods.
- Table population status: Although `evaluation_results` table DDL exists and `insert_evaluation_batch()` is implemented, `data/scada_ids.db` has 0 rows in `evaluation_results` because evaluation scripts write directly to `data/evaluation_results.csv`.
