# Source File Note: `simulator/controller.py`

## Purpose
Implements `Controller`, a bang-bang (hysteresis) level controller with deadband and deterministic fail-safe behavior for the batch simulation pipeline.

## Public Classes and Functions
- `class Controller(setpoint_m: float | None = None, deadband_m: float | None = None, default_valve_pct: float | None = None)`
  - `@property setpoint -> float`: Current setpoint in meters.
  - `@property pump_command -> int`: Last pump command (1=ON, 0=OFF).
  - `@property valve_command -> float`: Current valve position command (0-100%).
  - `@property control_command_str -> str`: Text description (`INIT`, `PUMP_ON`, `PUMP_OFF`, `HOLD`, `FAILSAFE`, `OVERRIDE`).
  - `@property is_failsafe -> bool`: Flag indicating whether the controller is currently in fail-safe mode.
  - `update_setpoint(setpoint_m: float) -> None`: Updates setpoint and recalculates `_pump_on_threshold = setpoint - deadband` and `_pump_off_threshold = setpoint + deadband`.
  - `step(observed_level_m: float, dos_active: bool = False) -> dict`: Executes one control cycle. Returns `{"pump_command": int, "valve_command": float, "control_command": str}`.
  - `override_command(pump_command: int | None = None, valve_command: float | None = None, command_str: str = "OVERRIDE") -> dict`: Overrides commands directly (used during A4 attack simulation).
  - `reset(setpoint_m: float | None = None) -> None`: Resets controller internal state to initial defaults.

## Inputs and Outputs
- `step()` inputs:
  - `observed_level_m`: float (sensor reading of tank water level).
  - `dos_active`: bool (indicates active DoS condition).
- `step()` outputs:
  - Dictionary with keys:
    - `"pump_command"`: `0` (OFF) or `1` (ON)
    - `"valve_command"`: `50.0` (default) or `0.0` (fail-safe)
    - `"control_command"`: string descriptor

## Config Keys and Constants Read
- `PARAMS.controller.deadband_m` [CODE simulator/controller.py:35]
- `PARAMS.controller.default_valve_pct` [CODE simulator/controller.py:36]
- `PARAMS.controller.setpoint_m` [CODE simulator/controller.py:39]
- `PARAMS.valve.safe_position_pct` [CODE simulator/controller.py:153]

## Who Calls It
- `simulator.process_simulator.ProcessSimulator` (`self._controller`)
- `tests/test_controller.py`

## Side Effects
- None (pure in-memory state manipulation).

## Tests Covering It
- `tests/test_controller.py`:
  - `test_controller_initial_state`
  - `test_controller_pump_on_when_low`
  - `test_controller_pump_off_when_high`
  - `test_controller_deadband_hold`
  - `test_controller_failsafe_on_dos`
  - `test_controller_failsafe_recovery`
  - `test_controller_override`
  - `test_controller_setpoint_update`
  - `test_controller_reset`

## Surprising / Notable Observations
- Valve position is not proportional or PID-controlled: it is simply fixed at `default_valve_pct` (50.0%) during normal operation and clamped to `0.0%` in fail-safe mode.
- Fail-safe state completely overrides hysteresis logic regardless of water level, forcing `pump_command = 0` and `valve_command = 0.0%`.
