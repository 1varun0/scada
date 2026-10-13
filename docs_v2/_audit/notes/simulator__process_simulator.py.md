# Source File Note: `simulator/process_simulator.py`

## Purpose
Orchestrates a complete normal simulation run for a given scenario: instantiates the physical tank, pump, valve, hysteresis controller, and noise generator, stepping them through time to produce a list of telemetry records.

## Public Classes and Functions
- `class ProcessSimulator(scenario: ScenarioConfig)`
  - `@property scenario -> ScenarioConfig`: Returns the scenario configuration.
  - `@property tank -> Tank`: Accessor for internal tank model.
  - `run() -> List[Dict[str, Any]]`: Iterates from step 0 to `total_steps - 1` and returns the complete list of telemetry dicts.
  - `_step(sequence_id: int, t: float) -> Dict[str, Any]`: Internal helper performing one timestep simulation.

## Inputs and Outputs
- `__init__(scenario: ScenarioConfig)`:
  - Input: `scenario` with duration, initial level, setpoint profile, random seed, and operating condition.
- `run()`:
  - Output: List of 1,000 dicts (for duration 1000s at dt=1.0s). Each dict contains 25 standard telemetry fields plus 3 internal keys (`_true_level`, `_q_in_true`, `_q_out_true`).

## Config Keys and Constants Read
- `PARAMS.simulation.dt_s` [CODE simulator/process_simulator.py:32] (default: 1.0 s)
- `PARAMS.controller.default_valve_pct` [CODE simulator/process_simulator.py:38] (default: 50.0%)
- Reads scenario config attributes: `duration_s`, `initial_level_m`, `setpoint_profile`, `random_seed`, `operating_condition` [CODE simulator/process_simulator.py:33, 36, 40, 42, 129]

## Who Calls It
- `simulator.scenario_runner.ScenarioRunner`
- `scripts/validate_matlab_vs_python.py`
- `scripts/run_e0_validation.py`
- `tests/test_simulator.py`

## Side Effects
- Pure computation in memory; no file, DB, or network operations.

## Tests Covering It
- `tests/test_simulator.py`:
  - `test_process_simulator_run_length`
  - `test_process_simulator_records_format`
  - `test_process_simulator_physics_consistency`
  - `test_process_simulator_noise_reproducibility`

## Surprising / Notable Observations
- The base `ProcessSimulator` only produces normal (un-attacked) data (`attack_type: 'None'`, `ground_truth: 0`, `dos_active=False`).
- Ground truth physics uses true un-noised flows for tank mass balance (`self._tank.step(q_in_true, q_out_true, self._dt)` at line 111), but controller decisions observe noisy level readings (`self._noise.add_level_noise(true_level)` at line 91).
- Total step count is `int(scenario.duration_s / self._dt)` = 1000 steps (`sequence_id` 0 to 999).
