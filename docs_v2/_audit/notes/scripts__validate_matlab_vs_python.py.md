# Source File Note: `scripts/validate_matlab_vs_python.py`

## Purpose
Cross-validation utility that runs scenarios through the Python `ProcessSimulator` and compares the resulting trajectories against MATLAB-generated CSV files (`matlab/data/*.csv`) to verify equivalence in physics modeling and controller dynamics.

## Public Classes and Functions
- `load_matlab_csv(csv_dir: str, scenario_id: str) -> pd.DataFrame`: Reads CSV corresponding to given scenario ID.
- `run_python_scenario(scenario_id: str) -> pd.DataFrame`: Runs Python `ProcessSimulator` for scenario ID and returns DataFrame.
- `compare_scenarios(matlab_df, python_df, scenario_id) -> dict`: Evaluates:
  1. Record count equality ($N=1,000$).
  2. Timestamp alignment ($\max|\Delta t| \le 10^{-6}\text{s}$).
  3. Pump command agreement rate (target $\ge 90\%$).
  4. Mean observed level difference (target $\le 0.05\text{ m}$).
  5. Mean flow differences (`q_in`, `q_out`).
- `main()`: CLI entry point supporting `--scenario`, `--csv-dir`, `--num` (defaults to first 5 normal scenarios `N_001`–`N_005`).

## Inputs and Outputs
- Inputs: `matlab/data/{scenario_id}.csv` and scenario definitions from `config/scenarios.py`.
- Output: Console comparison report [MEASURED docs_v2/_audit/outputs/validate_matlab_vs_python_output.txt]:
  - `N_001`: Records 1000, Status MATCH, Pump match 97.0%, Mean level diff 0.0014 m.
  - `N_002`: Records 1000, Status MATCH, Pump match 98.2%, Mean level diff 0.0006 m.
  - `N_003`: Records 1000, Status MATCH, Pump match 97.6%, Mean level diff 0.0018 m.
  - `N_004`: Records 1000, Status MATCH, Pump match 99.5%, Mean level diff 0.0036 m.
  - `N_005`: Records 1000, Status MATCH, Pump match 94.6%, Mean level diff 0.0017 m.

## Config Keys and Constants Read
- Reads scenarios via `config.scenarios.get_scenario_by_id`.

## Who Calls It
- Executed via CLI: `python scripts/validate_matlab_vs_python.py`.

## Side Effects
- Prints comparison results to stdout.

## Tests Covering It
- Cross-platform verification harness.

## Surprising / Notable Observations
- RNG divergence: Because MATLAB's Mersenne Twister/Philox implementation and NumPy's `default_rng` produce different pseudo-random sequences for Gaussian noise, exact sample-by-sample matching is impossible. The validation correctly checks statistical and physical equivalence (mean level difference $< 4\text{ mm}$, pump command agreement $> 94\%$).
