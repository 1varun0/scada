# Source File Note: `scripts/run_e0_validation.py`

## Purpose
Phase 1 verification script validating that the open-loop `PhysicsTwin` accurately predicts the physical tank level under nominal noisy conditions. Computes residual metrics against ground truth $H_{\text{true}}$ and proposes empirical threshold $\tau_p$.

## Public Classes and Functions
- `run_e0_validation(num_scenarios: int = 15, verbose: bool = True) -> dict`:
  - Runs first 15 normal scenarios (`N_001`–`N_015`).
  - Initializes `PhysicsTwin` at $H_{\text{true}}(0)$.
  - Steps twin using noisy reported flows $Q_{\text{in}}, Q_{\text{out}}$.
  - Evaluates residual $r = H_{\text{true}} - H_{\text{twin}}$.
  - Returns dict containing `mae`, `rmse`, `p95`, `p99`, `max_error`, `mean_residual`, `std_residual`, and array of all 15,000 residuals.
- `print_report(results: dict) -> bool`: Prints formatted report; evaluates pass/fail check (`mae < 0.02 m`).
- `save_plot(results: dict, output_path: str = None) -> None`: Plots residual histogram and time series, saving to `data/e0_residual_distribution.png`.

## Inputs and Outputs
- Inputs: Generated normal scenarios (`N_001` through `N_015`).
- Output metrics [MEASURED docs_v2/_audit/outputs/run_e0_validation_output.txt]:
  - MAE: 0.007062 m
  - RMSE: 0.008122 m
  - P95: 0.014363 m
  - P99: 0.017458 m (suggests $\tau_p = 0.0175\text{ m}$)
  - Max absolute error: 0.019299 m
  - Mean residual: -0.007061 m
  - Std residual: 0.004014 m

## Config Keys and Constants Read
- `PARAMS.tank.cross_section_area_m2` [CODE scripts/run_e0_validation.py:75] (2.0 m²)
- `PARAMS.tank.max_height_m` [CODE scripts/run_e0_validation.py:76] (2.5 m)
- `PARAMS.simulation.dt_s` [CODE scripts/run_e0_validation.py:86] (1.0 s)

## Who Calls It
- Executed via CLI: `python scripts/run_e0_validation.py`.

## Side Effects
- Saves diagnostic plot to `data/e0_residual_distribution.png`.

## Tests Covering It
- Core gate validation experiment.

## Surprising / Notable Observations
- Ground truth comparison: Evaluates $H_{\text{true}} - H_{\text{twin}}$ rather than $H_{\text{observed}} - H_{\text{twin}}$ to measure true model error decoupled from sensor measurement noise.
- Origin of $\tau_p$: The script suggests $\tau_p = 0.0175\text{ m}$ based directly on the 99th percentile ($0.017458\text{ m}$). However, `config/parameters.py` defines `tau_p = 0.035` [CODE config/parameters.py:73], which equals exactly $2 \times \text{P99}$ (adding a $2\times$ safety margin over the empirical 99th percentile). No formula or comment in `config/parameters.py` documents this $2\times$ derivation.
- Residual bias: Notice `mean_residual = -0.007061 m`. The residual has a negative mean, showing that $H_{\text{twin}} > H_{\text{true}}$ on average. This occurs because flow measurements are clamped non-negative (`max(0, Q + noise)`), which systematically inflates twin inflow integration.
