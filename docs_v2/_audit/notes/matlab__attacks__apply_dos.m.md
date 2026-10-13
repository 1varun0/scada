# Source File Note: `matlab/attacks/apply_dos.m`

## Purpose
MATLAB post-processing function applying Denial of Service (A3) attack modifications by marking packets as blocked, forcing fail-safe actuator states (pump OFF, valve 0%), and freezing tank level during the attack window.

## Public Classes and Functions
- `function telemetry = apply_dos(telemetry, true_levels, attack_cfg, params)`:
  - Inside attack window $[t_{\text{start}}, t_{\text{end}}]$:
    - Sets `pump_command = 0`, `pump_state = 0`.
    - Sets `valve_command = 0%`, `valve_state = 0%`.
    - Sets `control_command = 'FAILSAFE'`.
    - Sets `packet_received = 0`, `communication_status = 'BLOCKED'`.
    - Sets `q_in = 0.0`, `q_out = 0.0`.
    - Computes zero-flow mass balance $dH = 0$, holding liquid level constant.
    - Sets `attack_type = 'DoS'`, `attack_parameter = parameter_value`, `ground_truth = 1`.
  - When $t(k) > t_{\text{end}}$: sets `H = -1` and exits attack branch.

## Inputs and Outputs
- Inputs:
  - `telemetry`: Completed normal simulation table.
  - `true_levels`: Array of noiseless physical water levels from the base run.
  - `attack_cfg`: Struct with `attack_start`, `attack_end`, `parameter_value`.
  - `params`: Struct with physical parameters.
- Output: Modified MATLAB table.

## Config Keys and Constants Read
- Reads `params.sim.dt` (1.0s), `params.valve.safe_position` (0.0%), `params.tank.area` (2.0 m²), `params.tank.max_height` (2.5 m), `params.sim.noise_level` (0.005 m).

## Who Calls It
- `matlab/run_all_scenarios.m`
- `matlab/run_single_scenario.m`

## Side Effects
- In-memory table modifications.

## Tests Covering It
- Availability engine tests and database queries.

## Surprising / Notable Observations
- Critical Dataset Artifact — Post-DoS level discontinuity:
  During DoS, the fail-safe shuts the valve and pump, holding $H$ static ($dH = 0$). However, when $t(k) > t_{\text{end}}$, the loop does NOT re-simulate the remainder of the scenario. Rows for $t > t_{\text{end}}$ retain the unmodified data of the original normal run. Consequently, at $t = t_{\text{end}} + 1$, `tank_level_observed` instantly jumps from the frozen fail-safe level to whatever level the un-attacked normal simulation had reached at that timestamp, causing an artificial step discontinuity in the dataset.
