# Source File Note: `simulator/valve.py`

## Purpose
Simulates a continuously adjustable discharge control valve ($0\text{--}100\%$) with linear actuator slew-rate limiting and gravity-driven Torricelli discharge dynamics ($Q_{\text{out}} = C_v \cdot \frac{V\%}{100} \cdot \sqrt{H}$).

## Public Classes and Functions
- `class Valve(initial_position_pct: float = 50.0, flow_coefficient_m3s: float | None = None, response_time_s: float | None = None, dt_s: float | None = None)`
  - `@property command -> float`: Returns commanded position ($0\text{--}100\%$).
  - `@property position -> float`: Returns actual position ($0\text{--}100\%$).
  - `set_command(position_pct: float) -> None`: Clamps target to $[0.0, 100.0]\%$.
  - `step() -> float`: Moves `_position_pct` toward `_command_pct` by at most `max_change = (100 / response_time) * dt` percentage points per step. Returns updated actual position.
  - `compute_outflow(tank_level_m: float) -> float`: Evaluates $Q_{\text{out}} = C_v \left(\frac{V\%}{100}\right) \sqrt{H}$. Returns `0.0` if `tank_level_m <= 0.0`.
  - `reset(position_pct: float = 50.0) -> None`: Resets command and position without slew lag.

## Inputs and Outputs
- `set_command(position_pct: float)`: Input float percentage.
- `step()`: Output float (current actual position).
- `compute_outflow(tank_level_m: float)`:
  - Input: float liquid level in meters.
  - Output: float volumetric outflow in m³/s.

## Config Keys and Constants Read
- `PARAMS.valve.flow_coefficient_m3s` [CODE simulator/valve.py:31] (default: 0.004 m³/s)
- `PARAMS.valve.response_time_s` [CODE simulator/valve.py:32] (default: 2.0 s)
- `PARAMS.simulation.dt_s` [CODE simulator/valve.py:33] (default: 1.0 s)

## Who Calls It
- `simulator.process_simulator.ProcessSimulator`
- `scada_live.plant_sim.plant.SimulatedPlant`
- `tests/test_valve.py`

## Side Effects
- In-memory state tracking only.

## Tests Covering It
- `tests/test_valve.py`:
  - `test_valve_initial_state`
  - `test_valve_command_bounds`
  - `test_valve_slew_rate_limiting`
  - `test_valve_reaches_target`
  - `test_valve_compute_outflow_zero_level`
  - `test_valve_compute_outflow_normal`
  - `test_valve_reset`

## Surprising / Notable Observations
- Slew rate limitation: At default `response_time_s = 2.0` and `dt_s = 1.0`, `max_change` is $50\%$ per step. A full stroke from $0\%$ to $100\%$ requires exactly 2 discrete time steps.
- Gravity discharge model: Follows Torricelli's Law ($Q \propto \sqrt{H}$). When tank level drops below zero, the function returns `0.0` to guard against `math.sqrt()` ValueError.
