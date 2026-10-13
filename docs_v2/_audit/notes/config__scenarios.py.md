# Source File Note: `config/scenarios.py`

## Purpose
Defines data structures and deterministic generator functions for all simulation scenarios (60 normal, 90 attack). Configures setpoint profiles, seeds, operating regimes, and attack parameters.

## Public Classes and Functions
- `class SetpointProfile`:
  - `profile_type: str = "constant"` (`"constant"`, `"step"`, `"ramp"`)
  - `initial_setpoint_m: float = 1.0`
  - `final_setpoint_m: float = 1.0`
  - `change_time_s: float = 400.0`
  - `get_setpoint(t: float, duration: float) -> float`: Evaluates piecewise level setpoint at time $t$.
- `class AttackConfig`:
  - Fields: `attack_type`, `attack_id`, `attack_start_s`, `attack_end_s`, `parameter_type`, `parameter_value`, `replay_buffer_s`, `unsafe_command`, `description`.
- `class ScenarioConfig`:
  - Fields: `scenario_id`, `random_seed`, `duration_s`, `initial_level_m`, `operating_condition`, `setpoint_profile`, `attack`.
  - `@property is_attack -> bool`: True if `attack_type != "None"`.
- `generate_normal_scenarios() -> List[ScenarioConfig]`: Generates 60 normal scenarios (`N_001`–`N_060`).
- `generate_attack_scenarios() -> List[ScenarioConfig]`: Generates 90 attack scenarios (`A1_001`–`A1_045`, `A2_001`–`A2_015`, `A3_001`–`A3_015`, `A4_001`–`A4_015`).
- `get_all_scenarios() -> List[ScenarioConfig]`: Concatenates normal and attack lists (150 total).
- `get_scenario_by_id(scenario_id: str) -> Optional[ScenarioConfig]`: Linear search by ID.

## Inputs and Outputs
- `SetpointProfile.get_setpoint(t: float, duration: float) -> float`.
- Generator functions return typed lists of `ScenarioConfig`.

## Config Keys and Constants Read
- `PARAMS.simulation.scenario_duration_s` [CODE config/scenarios.py:83] (1000.0 s)
- `PARAMS.tank.initial_level_m` [CODE config/scenarios.py:84] (1.0 m)
- `PARAMS.simulation.base_random_seed` [CODE config/scenarios.py:101] (42000)

## Who Calls It
- `simulator.scenario_runner`
- `scripts/validate_matlab_vs_python.py`
- `scripts/run_e0_validation.py`
- `scripts/import_matlab_csv.py`
- `tests/*`

## Side Effects
- None (pure in-memory object factories).

## Tests Covering It
- `tests/test_simulator.py`

## Surprising / Notable Observations
- Docstring mismatch: Line 170 docstring says `"""Generate all 110 attack scenarios."""`, but the function contains code for exactly 90 attack scenarios (45 A1, 15 A2, 15 A3, 15 A4). The SQLite database also holds exactly 90 attack scenarios.
- Normal scenario taxonomy (60 total):
  - `N_001`–`N_020` (20): `Steady_State`, setpoint constant 1.0m, $H_0=1.0\text{m}$.
  - `N_021`–`N_035` (15): `Setpoint_Change`, step 1.0m $\to$ 1.5m at $t=400\text{s}$, $H_0=1.0\text{m}$.
  - `N_036`–`N_050` (15): `Variable_Load`, linear ramp 0.8m $\to$ 1.4m from $t=200\text{s}$, $H_0=1.0\text{m}$.
  - `N_051`–`N_060` (10): `Recovery`, constant setpoint 1.0m, low initial level $H_0=0.5\text{m}$.
- Attack scenario taxonomy (90 total):
  - A1 (45): 10 small bias (+0.05m), 10 med bias (+0.10m), 10 large bias (+0.20m), 10 scale ($\times 1.10$), 5 intermittent (+0.15m every 5 steps). Window: $[300, 500]\text{s}$.
  - A2 (15): Replay buffer length sweep [30, 40, 50, 60, 70, 80, 90, 100, 35, 45, 55, 65, 75, 85, 95] s. Start: $t=400\text{s}$.
  - A3 (15): DoS duration sweep [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 25, 45, 75, 105] s. Start: $t=350\text{s}$.
  - A4 (15): Authenticated misuse. Initial levels are polarized: $H_0=0.4\text{m}$ for valve open commands (11 scenarios) and $H_0=2.1\text{m}$ for pump force on commands (4 scenarios). Window: $[200, 300]\text{s}$.
