# Source File Note: `matlab/attacks/apply_fdi.m`

## Purpose
MATLAB post-processing function applying False Data Injection (A1) modifications to an already completed simulation telemetry table.

## Public Classes and Functions
- `function telemetry = apply_fdi(telemetry, attack_cfg)`:
  - Iterates over each row $k$ where $t(k) \in [\text{attack\_start}, \text{attack\_end}]$.
  - Supports three parameter types:
    - `'bias'`: $H_{\text{observed}}(k) \leftarrow H_{\text{observed}}(k) + b$.
    - `'scale'`: $H_{\text{observed}}(k) \leftarrow H_{\text{observed}}(k) \times \alpha$.
    - `'intermittent'`: applies bias $b$ only when $\text{step\_in\_attack} \equiv 0 \pmod 5$.
  - Sets `attack_type{k} = 'FDI'`, `attack_parameter(k) = parameter_value`, `ground_truth(k) = 1`.

## Inputs and Outputs
- Inputs:
  - `telemetry`: MATLAB table containing finished 1,000-timestep simulation run.
  - `attack_cfg`: struct with `attack_start`, `attack_end`, `parameter_type`, `parameter_value`.
- Output: Modified MATLAB table.

## Config Keys and Constants Read
- Reads fields from input struct `attack_cfg`.

## Who Calls It
- `matlab/run_all_scenarios.m`
- `matlab/run_single_scenario.m`

## Side Effects
- Mutates in-memory table.

## Tests Covering It
- Telemetry cross-validation and database queries.

## Surprising / Notable Observations
- Critical Dataset Artifact — Post-hoc overlay without closed-loop plant feedback:
  The function modifies ONLY `telemetry.tank_level_observed(k)`. Because the physical simulation and controller execution already concluded prior to calling `apply_fdi()`, the modified level does NOT feed back into the controller. Actuator states (`pump_state`, `valve_state`) and flows (`q_in`, `q_out`) remain those of the peaceful normal run.
- Intermittent attack ground truth labeling: Lines 34-39 show that if `mod(step_in_attack, 5) != 0`, line 38 executes `continue;`. Thus, intermediate ticks between the 5-step bursts are NOT marked with `ground_truth = 1` or modified, leaving them labeled normal.
