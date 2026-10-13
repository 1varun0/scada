# Source File Note: `simulator/pump.py`

## Purpose
Simulates a fixed-displacement ON/OFF pump with fixed maximum flow rate $Q_{\text{max}}$ and discrete response delay modeling mechanical inertia.

## Public Classes and Functions
- `class Pump(initial_state: int = 0, q_max_m3s: float | None = None, response_delay_s: float | None = None, dt_s: float | None = None)`
  - `@property command -> int`: Returns current commanded state (1=ON, 0=OFF).
  - `@property state -> int`: Returns current actual state (1=ON, 0=OFF).
  - `@property flow -> float`: Returns delivered flow rate: `q_max` if `state == 1` else `0.0`.
  - `set_command(command: int) -> None`: Sets commanded target; resets `_steps_since_command = 0` if command changed.
  - `step() -> int`: Advances simulation by one step, increments `_steps_since_command`, updates `state = command` if `_steps_since_command >= delay_steps`, and returns `state`.
  - `reset(state: int = 0) -> None`: Resets pump command, state, and timer to settled state.

## Inputs and Outputs
- `set_command()`: Input integer `0` or `1`.
- `step()`: Output integer `0` or `1` (actual pump state).
- `flow`: Output float in m³/s.

## Config Keys and Constants Read
- `PARAMS.pump.q_max_m3s` [CODE simulator/pump.py:29] (0.005 m³/s)
- `PARAMS.pump.response_delay_s` [CODE simulator/pump.py:30] (1.0 s)
- `PARAMS.simulation.dt_s` [CODE simulator/pump.py:31] (1.0 s)

## Who Calls It
- `simulator.process_simulator.ProcessSimulator` (`self._pump`)
- `tests/test_pump.py`

## Side Effects
- In-memory state tracking only.

## Tests Covering It
- `tests/test_pump.py`:
  - `test_initial_off`
  - `test_initial_on`
  - `test_flow_rate_on`
  - `test_flow_rate_off`
  - `test_response_delay`
  - `test_immediate_if_no_change`
  - `test_reset`
  - `test_rapid_command_toggle`

## Surprising / Notable Observations
- Discrete delay: `_delay_steps = max(1, math.ceil(response_delay_s / dt_s))`. With default parameters (`response_delay_s = 1.0`, `dt_s = 1.0`), `_delay_steps = 1`. If `set_command(1)` is called immediately before `step()` in the same cycle, `_steps_since_command` becomes 1 on that step, triggering transition to state 1 on that very cycle. If `response_delay_s = 2.0`, it requires 2 calls to `step()` before transitioning.
