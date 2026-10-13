# Source File Note: `engines/policy_engine.py`

## Purpose
Implements Engine 3 (Policy/Safety Engine, $S_c$), targeting A4 Authenticated Misuse attacks by evaluating incoming actuator commands against current process states and deterministic domain constraints.

## Public Classes and Functions
- `class PolicyEngine(epsilon_m: float = 0.05)`
  - `__init__(epsilon_m: float = 0.05)`: Initializes boundaries from `PARAMS`: `h_crit_low` (0.3m), `h_crit_high` (2.3m), `h_max` (2.5m), `default_valve_pct` (50.0%), and `epsilon` (0.05m).
  - `evaluate(h_observed: float, pump_command: int, valve_command: float) -> float`: Evaluates policy v1 rules. Returns `1.0` on violation, `0.0` otherwise.
  - `evaluate_v2(h_observed: float, pump_command: int, valve_command: float) -> float`: Evaluates policy v2 rules (valve consistency check + fallback to v1). Returns `1.0` on violation, `0.0` otherwise.

## Inputs and Outputs
- `evaluate` and `evaluate_v2`:
  - Inputs: `h_observed: float`, `pump_command: int`, `valve_command: float`.
  - Output: float discrete score $S_c \in \{0.0, 1.0\}$.

## Config Keys and Constants Read
- `PARAMS.tank.critical_low_m` [CODE engines/policy_engine.py:12] (0.3 m)
- `PARAMS.tank.critical_high_m` [CODE engines/policy_engine.py:13] (2.3 m)
- `PARAMS.tank.max_height_m` [CODE engines/policy_engine.py:14] (2.5 m)
- `PARAMS.controller.default_valve_pct` [CODE engines/policy_engine.py:16] (50.0 %)
- `PARAMS.controller.pump_off_threshold_m` [CODE engines/policy_engine.py:53] (1.2 m, unused in logic)
- `PARAMS.controller.pump_on_threshold_m` [CODE engines/policy_engine.py:54] (0.8 m, unused in logic)
- `PARAMS.valve.safe_position_pct` [CODE engines/policy_engine.py:55] (0.0 %)

## Who Calls It
- `evaluation.ablation`
- `scripts.run_evaluation`
- `tests.test_engines`
- `scada_live.scada_ids.streaming_ids.StreamingIDS`

## Side Effects
- Pure stateless decision function; no state mutations or side effects.

## Tests Covering It
- `tests/test_engines.py`:
  - `test_policy_engine_safe`
  - `test_policy_engine_pump_at_high_overflow`
  - `test_policy_engine_valve_open_at_low`
  - `test_policy_engine_v2_valve_mismatch`

## Surprising / Notable Observations
- Unused variables in `evaluate_v2()`: Lines 53-54 extract `h_off = PARAMS.controller.pump_off_threshold_m` and `h_on = PARAMS.controller.pump_on_threshold_m`, but neither variable is referenced anywhere in executable logic. As explained in the docstring (lines 42-47), static hysteresis level checks were omitted because `PolicyEngine` does not receive current setpoint information, and static checks would trigger false positives during setpoint step transitions.
- v2 Rule Logic: `evaluate_v2` checks if `valve_command != 50.0%`. If not 50.0%, it allows only `valve_command == 0.0%` accompanied by `pump_command == 0` (the DoS fail-safe pattern). Any other valve position immediately yields $S_c = 1.0$. If valve is 50.0%, it falls back to `evaluate(h_observed, pump_command, valve_command)`.
- Critical boundary rule in v1: Pump ON is only flagged if $H_{\text{observed}} > H_{\text{max}} - \epsilon = 2.5 - 0.05 = 2.45\text{ m}$. Notice that $H_{\text{crit\_high}} = 2.3\text{ m}$ is stored in `self.h_crit_high` at line 13, but rule 1 checks `self.h_max - self.epsilon` (2.45m), leaving `self.h_crit_high` unused in `evaluate()`.
