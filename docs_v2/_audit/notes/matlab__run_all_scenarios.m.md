# Source File Note: `matlab/run_all_scenarios.m`

## Purpose
Master MATLAB batch dataset generation script. Coordinates execution of all 60 normal scenarios and 90 attack scenarios, applying attack overlays, exporting 150 scenario CSV files, and compiling `matlab/data/attack_scenarios.csv`.

## Public Classes and Functions
- `run_all_scenarios` (Script):
  - Normal loops:
    - `N_001`–`N_020` (20): Steady State ($H_{\text{sp}}=1.0\text{m}$, $H_0=1.0\text{m}$).
    - `N_021`–`N_035` (15): Setpoint Step ($1.0 \to 1.5\text{m}$ at $t=400\text{s}$, $H_0=1.0\text{m}$).
    - `N_036`–`N_050` (15): Variable Load ramp ($0.8 \to 1.4\text{m}$ from $t=200\text{s}$, $H_0=1.0\text{m}$).
    - `N_051`–`N_060` (10): Recovery ($H_0=0.5\text{m}$, $H_{\text{sp}}=1.0\text{m}$).
  - Attack loops:
    - `A1_001`–`A1_045` (45 FDI): 10 small bias (+0.05m), 10 med bias (+0.10m), 10 large bias (+0.20m), 10 scale ($\times 1.10$), 5 intermittent (+0.15m).
    - `A2_001`–`A2_015` (15 Replay): buffer sweep 30–100s.
    - `A3_001`–`A3_015` (15 DoS): duration sweep 20–120s.
    - `A4_001`–`A4_015` (15 Auth Misuse): 11 valve open ($H_0=0.4\text{m}$), 4 pump on ($H_0=2.1\text{m}$).
  - Exports:
    - Writes each table to `matlab/data/{scenario_id}.csv`.
    - Concatenates metadata into `matlab/data/attack_scenarios.csv`.
- Helper functions:
  - `make_normal_cfg(...)`
  - `make_attack_cfg(...)`
  - `make_attack_meta(...)`
  - `export_csv(telemetry, output_dir, scenario_id)`

## Inputs and Outputs
- Inputs: Simulation parameters from `scada_params()`.
- Outputs: 151 CSV files written to `matlab/data/` (150 scenario files $\times$ 1,000 rows + 1 metadata file with 90 rows).

## Config Keys and Constants Read
- Reads `scada_params()` configuration structs.

## Who Calls It
- Executed in MATLAB to create the baseline dataset.

## Side Effects
- Creates directory `matlab/data/` and writes all CSV data files.

## Tests Covering It
- Cross-validation script `scripts/validate_matlab_vs_python.py` and SQLite import.

## Surprising / Notable Observations
- Comment vs Reality Discrepancy (170 vs 150 scenarios):
  Line 3 comments state `% Generates ALL 170 scenarios (60 normal + 110 attack)` and line 224 prints `Total scenarios: 170`. However, the loop constructs generate exactly 60 normal scenarios and 90 attack scenarios (45 A1 + 15 A2 + 15 A3 + 15 A4 = 90). The actual total is 150 scenarios (150,000 telemetry rows), not 170!
- Conclusive Proof of Post-Hoc Overlay:
  In lines 94-96, 162-164, 177-179, and 206-208, the workflow is:
  ```matlab
  [telemetry, true_lvls] = run_single_scenario(params, cfg);
  telemetry = apply_<attack>(telemetry, ...);
  export_csv(telemetry, output_dir, cfg.scenario_id);
  ```
  `run_single_scenario` completes a full 1,000-second unattacked normal run first; then `apply_*` modifies the finished table post-hoc.
