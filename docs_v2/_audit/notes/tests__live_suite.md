# Source File Note: scada_live/tests/ (Live Simulation & Gateway Test Suite)

## 1. Purpose
Tests the live plant simulation, two-call gateway protocol, SSE fanout, watchdog timer, digital twin takeover & handback, command filtering & validation, wire tamper consistency checks, and automated presentation demo [CODE scada_live/tests/test_phase0_imports.py:1-96, scada_live/tests/test_phase1_plant.py:1-112, scada_live/tests/test_phase2_equivalence.py:1-262, scada_live/tests/test_phase3a_gateway.py:1-273, scada_live/tests/test_phase3b_alert_metrics.py:1-81, scada_live/tests/test_phase3b_metrics.py:1-57, scada_live/tests/test_phase4_api.py:1-132, scada_live/tests/test_phase4_injector.py:1-76, scada_live/tests/test_phase6a_prevention.py:1-560, scada_live/tests/test_phase6b_command_filtering.py:1-487, scada_live/tests/test_phase7_auto_demo.py:1-101, scada_live/tests/test_phase7_evaluation.py:1-70, scada_live/tests/test_api_command_validation.py:1-209, scada_live/tests/test_gateway_safety_rule.py:1-128, scada_live/tests/test_tamper_consistency_check.py:1-241].

## 2. Test Breakdown by File
1. `test_api_command_validation.py` (12 tests): Validates `/api/command` schema, types (rejecting bools), hold duration capping for unauthenticated callers ($\le 60\text{ ticks}$), HMAC secret comparison, and ingress rejection/acceptance responses.
2. `test_gateway_safety_rule.py` (8 tests): Unit tests for `evaluate_command_with_live_setpoint` against dynamic setpoint and deadband invariants (AM-1 through AM-6 synthetic attack patterns).
3. `test_phase0_imports.py` (10 tests): Verifies imports across all modules, dataclass instantiation, and ground-truth stripping.
4. `test_phase1_plant.py` (7 tests): Tests `LivePlant` physics stepping, noise injection, flow calculations, and standalone hysteresis controller mode.
5. `test_phase2_equivalence.py` (8 tests): Verifies numerical equivalence between batch `ProcessSimulator` and streaming `LivePlant` + `StreamingIDS` across normal and attack scenarios (captures attacks starting at 200-400s).
6. `test_phase3a_gateway.py` (11 tests): Tests gateway routes, concurrency under load, watchdog synthetic packet generation, time scaling, and a 1,800-tick soak test (`test_soak_30min`).
7. `test_phase3b_alert_metrics.py` (3 tests): Tests `AlertManager` state machine transitions (SAFE $\to$ SUSPICIOUS $\to$ CRITICAL) and latch clearing.
8. `test_phase3b_metrics.py` (1 test): Tests `MetricsCollector` out-of-band truth joining, episode metrics, and detection delay computation.
9. `test_phase4_api.py` (9 tests): Tests Flask API endpoints `/api/config`, `/api/state`, `/api/history`, `/api/mode`, and control actions (`pause`, `resume`, `speed`, `reset`).
10. `test_phase4_injector.py` (4 tests): Tests in-flight attack interception (`sense()` and `send_telemetry()`) for FDI, Replay, DoS, and Auth misuse.
11. `test_phase6a_prevention.py` (13 tests): Tests Monitor vs Prevention mode switching, Digital Twin takeover during CRITICAL physics alerts, and automatic handback upon sensor recovery.
12. `test_phase6b_command_filtering.py` (16 tests): Tests ingress command blocking in Prevention mode, would-block emission in Monitor mode, and continuous hold enforcement dropping rogue holds before water level leaves deadband.
13. `test_phase7_auto_demo.py` (4 tests): Tests `AutoDemoCoordinator` initialization, interruptible sleep, final metrics summary generation, and ultra-high-speed headless execution.
14: `test_phase7_evaluation.py` (4 tests): Evaluates scenario metadata integrity, single-run simulations (NORM, AM-1), and smoke execution of the full benchmark matrix.
15. `test_tamper_consistency_check.py` (6 tests): Validates the 4-way actuator consistency check (AM-3 fieldbus wire tamper) detecting actuator mismatches within $\le 3\text{ ticks}$.

## 3. Execution & Measured Results
- Output file: `docs_v2/_audit/outputs/pytest_live_output.txt`
- Result: **116 passed in 314.58s (5m 14s)** on Python 3.12.6, pytest 9.1.1.
- Slow tests identified: `test_soak_30min` (1,800 ticks in `test_phase3a_gateway.py`), `test_streaming_equals_batch` (3,000 LSTM forward passes in `test_phase2_equivalence.py`), and `test_execute_benchmark_fast_smoke` (24 multi-engine simulations in `test_phase7_evaluation.py`).
