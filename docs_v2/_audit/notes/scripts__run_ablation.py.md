# Source File Note: `scripts/run_ablation.py`

## Purpose
Execution script for running the 8-configuration ablation study (C1 through C7). Loads precomputed per-tick evaluation metrics from `data/evaluation_results.csv`, executes `AblationRunner`, and outputs the consolidated results to `reports/ablation_results.md`.

## Public Classes and Functions
- `load_results(filepath="data/evaluation_results.csv") -> pd.DataFrame`: Reads CSV into Pandas DataFrame, verifying file existence.
- `main()`: Instantiates `AblationRunner(df_results, tau_fusion=0.5)`, executes `run_all()`, passes summary to `Reporter.generate_ablation_markdown()`, and prints key metrics (`precision`, `recall`, `f1`, `latency_median`) to stdout.

## Inputs and Outputs
- Input: Reads `data/evaluation_results.csv`.
- Output: Writes `reports/ablation_results.md`.

## Config Keys and Constants Read
- Hard-coded default `tau_fusion = 0.5` [CODE scripts/run_ablation.py:21].

## Who Calls It
- Executed via CLI: `python scripts/run_ablation.py`.

## Side Effects
- Overwrites `reports/ablation_results.md`.
- Prints summary table to stdout.

## Tests Covering It
- Integration ablation testing.

## Surprising / Notable Observations
- Decoupled from online simulation: Does not re-run simulation or model inference; operates entirely as an offline post-processing pass over `data/evaluation_results.csv`.
