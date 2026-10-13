# Source File Note: tests/ (Root Batch Unit Test Suite)

## 1. Purpose
Unit tests covering batch simulation, actuators, digital twin, and detection engines: `test_tank.py`, `test_pump.py`, `test_valve.py`, `test_controller.py`, `test_twin.py`, `test_engines.py`, `test_fusion.py`, `test_simulator.py` [CODE tests/test_tank.py:1-106, tests/test_pump.py:1-90, tests/test_valve.py:1-110, tests/test_controller.py:1-105, tests/test_twin.py:1-139, tests/test_engines.py:1-84, tests/test_fusion.py:1-32, tests/test_simulator.py:1-152].

## 2. Test Breakdown by File
1. `tests/test_tank.py` (11 tests):
   - Mass balance conservation: $dH/dt = (Q_{in} - Q_{out}) / A$.
   - Physical limits: ceiling clamping at 2.5m, dry-out flooring at 0.0m.
   - Initial level configuration, state reset, and error handling for negative area/height.
2. `tests/test_pump.py` (9 tests):
   - Transport delay ring buffer: 2.0s delay at $dt=1.0\text{s}$ takes 2 steps for flow to appear after command.
   - Flow capacity: $Q_{in} = 0.005\text{ m}^3/\text{s}$ when active, 0.0 when off.
   - Command queuing and state resetting.
3. `tests/test_valve.py` (11 tests):
   - Torricelli outflow: $Q_{out} = C_v \cdot (V\% / 100) \cdot \sqrt{H}$.
   - Linear slew rate limiting: $100\% / 1.5\text{s} = 66.67\%/\text{s}$.
   - Default position (50%), fail-safe position (0%), and negative level guards ($\le 0 \implies Q_{out} = 0$).
4. `tests/test_controller.py` (8 tests):
   - Bang-bang hysteresis with deadband: pump ON when $H \le 0.8\text{m}$, pump OFF when $H \ge 1.2\text{m}$, holds state within $(0.8, 1.2)\text{m}$.
   - Fail-safe safety override: critical low $H \le 0.3\text{m}$ forces valve to 0% and pump ON; critical high $H \ge 2.3\text{m}$ forces pump OFF and valve to 100%.
5. `tests/test_twin.py` (11 tests):
   - Discrete Euler forward integration: $H_{twin}[k+1] = H_{twin}[k] + (Q_{in} - Q_{out})\cdot dt / A$.
   - Tracking under ideal flows, divergence under spoofed levels, and reset behavior.
6. `tests/test_engines.py` (4 tests):
   - `PhysicsEngine`: residual calculation $|H_{obs} - H_{twin}|$, normalization by $\tau_p=0.035\text{m}$.
   - `PolicyEngine`: evaluation of physical and behavioral rules under v1.
   - `AvailabilityEngine`: latency evaluation, stale packet detection, timeout clamping.
   - `TemporalEngine`: window preprocessor, LSTM reconstruction error normalization.
7. `tests/test_fusion.py` (2 tests):
   - Max-vote fusion strategy: $S_{hybrid} = \max(S_p, S_l, S_c, S_a)$, flag if $S_{hybrid} > \tau_{fusion}$.
   - Weighted average fusion strategy.
8. `tests/test_simulator.py` (10 tests):
   - Integrated closed-loop simulation stepping, scenario generation, noise injection, and database record structure.

## 3. Execution & Measured Results
- Output file: `docs_v2/_audit/outputs/pytest_batch_output.txt`
- Result: **66 passed in 1.86s** on Python 3.12.6, pytest 9.1.1.
