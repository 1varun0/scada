# Source File Note: `matlab/run_single_scenario.m`

## Purpose
Core MATLAB physical simulation function. Executes a single continuous 1,000-timestep scenario run modeling tank mass balance, pump delay, valve slew-rate limiting, and hysteresis control, producing a 25-column telemetry table and true noiseless water level array.

## Public Classes and Functions
- `function [telemetry, true_levels] = run_single_scenario(params, cfg)`:
  - Seeds generator: `rng(cfg.seed, 'twister')`.
  - Loops $k = 1 \dots N$ ($N=1000$ for duration 1000s, $\Delta t = 1.0\text{s}$).
  - Evaluates setpoint via `get_setpoint(cfg, t)`.
  - Adds level sensor noise: $H_{\text{obs}} = H + \sigma_H \cdot \mathcal{N}(0, 1)$.
  - Executes bang-bang hysteresis controller with pump delay queue.
  - Limits valve slew rate: $\Delta V \le \text{max\_slew\_rate} \cdot \Delta t$.
  - Computes Torricelli outflow: $Q_{\text{out}} = C_v \left(\frac{V}{100}\right) \sqrt{H}$.
  - Adds clamped flow noise: $Q_{\text{obs}} = \max(0, Q_{\text{true}} + \sigma_Q \cdot \mathcal{N}(0, 1))$.
  - Steps Euler integration: $H \leftarrow \text{clamp}(H + \frac{Q_{\text{in}} - Q_{\text{out}}}{A} \Delta t, 0, H_{\text{max}})$.
  - Packages results into MATLAB `table` with 0-indexed `sequence_id = k - 1`.
- `function sp = get_setpoint(cfg, t)`: Helper evaluating constant, step, or ramp profiles.

## Inputs and Outputs
- Inputs:
  - `params`: Struct from `scada_params()`.
  - `cfg`: Scenario struct with `duration`, `seed`, `initial_level`, `operating_condition`, setpoint profile settings.
- Outputs:
  - `telemetry`: MATLAB table with 1,000 rows and 25 schema columns.
  - `true_levels`: Array of 1,000 floats storing un-noised level $H(t)$.

## Config Keys and Constants Read
- Reads parameter struct from `scada_params()`.

## Who Calls It
- `matlab/run_all_scenarios.m`

## Side Effects
- Mutates MATLAB RNG state (`rng(..., 'twister')`).

## Tests Covering It
- `scripts/validate_matlab_vs_python.py` cross-validation.

## Surprising / Notable Observations
- Clamped flow noise: Lines 134-135 execute `q_in_obs = max(0, q_in_true + params.sim.noise_flow * randn())` and `q_out_obs = max(0, q_out_true + params.sim.noise_flow * randn())`, demonstrating that non-negative clamping is inherent to the dataset generation process.
- True level output: Returns `true_levels` (line 138 captures $H$ before Euler step), which is then passed to attack generators `apply_dos` and `apply_auth_misuse` as the baseline ground truth.
