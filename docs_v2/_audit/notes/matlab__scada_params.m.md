# Source File Note: matlab/scada_params.m

## 1. Purpose
Defines the frozen physical and simulation parameters for MATLAB simulations [CODE matlab/scada_params.m:1-6]. It is designed to mirror `config/parameters.py` exactly [CODE matlab/scada_params.m:2].

## 2. Public Classes / Functions
- `function params = scada_params()` [CODE matlab/scada_params.m:7-43]: Returns a MATLAB struct containing physical, controller, and simulation parameters.

## 3. Inputs and Outputs
- **Inputs**: None.
- **Outputs**: Struct `params` with sub-structs:
  - `params.tank`: `area=2.0`, `max_height=2.5`, `initial_level=1.0`, `critical_low=0.3`, `critical_high=2.3`, `overflow=2.5` [CODE matlab/scada_params.m:9-15]
  - `params.pump`: `q_max=0.005`, `response_delay=2.0`, `delay_steps=2` [CODE matlab/scada_params.m:17-20]
  - `params.valve`: `cv=0.004`, `response_time=1.5`, `safe_position=0.0`, `max_slew_rate=66.6667` [CODE matlab/scada_params.m:22-26]
  - `params.ctrl`: `setpoint=1.0`, `deadband=0.2`, `pump_on_thresh=0.8`, `pump_off_thresh=1.2`, `default_valve=50.0` [CODE matlab/scada_params.m:28-33]
  - `params.sim`: `dt=1.0`, `duration=1000.0`, `noise_level=0.005`, `noise_flow=0.0001`, `actuator_delay=1`, `base_seed=42000` [CODE matlab/scada_params.m:35-41]

## 4. Config Keys or Constants Read
- Hardcoded constants within the function definition.

## 5. Who Calls It
- `matlab/run_single_scenario.m:24` [CODE matlab/run_single_scenario.m:24]
- `matlab/run_all_scenarios.m:29` [CODE matlab/run_all_scenarios.m:29]
- `matlab/attacks/apply_auth_misuse.m:41` [CODE matlab/attacks/apply_auth_misuse.m:41]

## 6. Side Effects
- None (pure parameter constructor function).

## 7. Tests Covering It
- Indirectly covered by `scripts/validate_matlab_vs_python.py` (which validates numerical equivalence between Python parameters and MATLAB generated traces).

## 8. Surprises, Mismatches, or Dead Code
- Parameters match `config/parameters.py` defaults exactly [CODE config/parameters.py:17-80].
- Notice `params.sim.base_seed = 42000` [CODE matlab/scada_params.m:41] whereas `config/parameters.py` has `RANDOM_SEED: int = 42` [CODE config/parameters.py:72]. However, in `matlab/run_all_scenarios.m`, seed offsets are computed per scenario (`base_seed + scenario_num * 7`).
