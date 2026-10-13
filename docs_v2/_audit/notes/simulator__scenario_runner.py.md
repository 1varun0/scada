# Source File Note: `simulator/scenario_runner.py`

## Purpose
Batch execution coordinator for running collections of `ScenarioConfig` instances through `ProcessSimulator` and persisting the resulting telemetry records and attack metadata into a SQLite database instance.

## Public Classes and Functions
- `class ScenarioRunner(db: SCADADatabase)`
  - `__init__(db: SCADADatabase)`: Stores reference to `SCADADatabase` client.
  - `run_scenarios(scenarios: List[ScenarioConfig], show_progress: bool = True) -> int`: Loops over scenarios, executes `ProcessSimulator(scenario).run()`, strips internal `_` fields, inserts batches into SQLite via `self._db.insert_telemetry_batch()`, and optionally inserts attack metadata via `self._db.insert_attack_scenario()`. Returns total records created.
  - `run_normal(show_progress: bool = True) -> int`: Runs all scenarios produced by `config.scenarios.generate_normal_scenarios()`.
  - `run_attacks(show_progress: bool = True) -> int`: Runs base simulations for `config.scenarios.generate_attack_scenarios()`.

## Inputs and Outputs
- `run_scenarios`:
  - Inputs: `scenarios: List[ScenarioConfig]`, `show_progress: bool`.
  - Output: integer count of total inserted records.

## Config Keys and Constants Read
- Does not directly read `PARAMS`; imports `generate_normal_scenarios` and `generate_attack_scenarios` from `config.scenarios`.

## Who Calls It
- Available as Python batch generation utility. Note: The repository's committed dataset was generated using MATLAB scripts and imported using `scripts/import_matlab_csv.py`.

## Side Effects
- Database write operations: Calls `self._db.insert_telemetry_batch()` and `self._db.insert_attack_scenario()`.
- Standard output: Prints progress via `tqdm`.

## Tests Covering It
- Integration-level simulation tests.

## Surprising / Notable Observations
- Private fields stripped: Lines 44-47 iterate over records and exclude any key starting with `_` (`_true_level`, `_q_in_true`, `_q_out_true`). Consequently, the true noiseless physics values are not saved to SQLite.
- Attack post-processing discrepancy: In line 78-80 docstring, `run_attacks()` only generates unattacked base telemetry; the Python codebase relies on external post-processing for attacks, which in practice was executed via MATLAB scripts (`apply_fdi.m`, `apply_replay.m`, `apply_dos.m`, `apply_auth_misuse.m`).
