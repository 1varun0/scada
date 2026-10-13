# R02: Test Suite Verification & Determinism Audit

## 1. Test Suite Architecture

The repository contains two distinct, complementary automated test suites executing under `pytest`:
1. **Core Batch Suite (`tests/`)**: Focuses on isolated plant physics components, tank mass balance, valve dynamics, pump delays, PID/bang-bang controller hysteresis, and offline detection engines.
2. **Live Streaming & Prevention Suite (`scada_live/tests/`)**: Focuses on real-time closed-loop operations, two-call gateway protocol (`/api/sense`, `/api/telemetry`), SSE fanout, watchdog timer fail-safe, Digital Twin takeover & handback, command filtering, and downstream wire tampering.

---

## 2. Execution Summary (Run 1)

Tabulated from [`b1_pytest_tests_run1.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/b1_pytest_tests_run1.log) and [`b1_pytest_scada_live_tests_run1.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/b1_pytest_scada_live_tests_run1.log) into [`t01_test_suites_summary.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t01_test_suites_summary.md):

| Suite | Directory | Collected | Passed | Failed | Skipped | Exit Code | Wall Time | Raw Log Citation |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Core Batch Suite** | `tests/` | 66 | 66 | 0 | 0 | 0 | 4.04s | [`b1_pytest_tests_run1.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/b1_pytest_tests_run1.log) |
| **Live Streaming Suite** | `scada_live/tests/` | 116 | 116 | 0 | 0 | 0 | 257.28s | [`b1_pytest_scada_live_tests_run1.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/b1_pytest_scada_live_tests_run1.log) |
| **Total Test Battery** | **Combined** | **182** | **182** | **0** | **0** | **0** | **261.32s** | - |

---

## 3. Module Breakdown

### A. Core Batch Suite (`tests/` — 66 Tests)
- [`tests/test_controller.py`](file:///c:/projects/p1/New%20folder/tests/test_controller.py) (8 tests): Bang-bang hysteresis deadband ($0.8\text{ m} \le H \le 1.2\text{ m}$), setpoint adjustment, manual overrides, and failsafe behavior.
- [`tests/test_engines.py`](file:///c:/projects/p1/New%20folder/tests/test_engines.py) (4 tests): Physics residual engine, policy engine bounds, availability timeout tracking, and MinMaxScaler numerical transform parity.
- [`tests/test_fusion.py`](file:///c:/projects/p1/New%20folder/tests/test_fusion.py) (2 tests): Multi-score fusion engine weighting and threshold normalization.
- [`tests/test_pump.py`](file:///c:/projects/p1/New%20folder/tests/test_pump.py) (9 tests): Actuator inertia, startup/shutdown flow rate responses, and command tracking.
- [`tests/test_simulator.py`](file:///c:/projects/p1/New%20folder/tests/test_simulator.py) (10 tests): `ProcessSimulator` record synthesis, determinism, seed noise divergence, and telemetry structure.
- [`tests/test_tank.py`](file:///c:/projects/p1/New%20folder/tests/test_tank.py) (11 tests): Mass balance fill/drain rates, clamp upper/lower limits, and multi-step integration.
- [`tests/test_twin.py`](file:///c:/projects/p1/New%20folder/tests/test_twin.py) (11 tests): Digital Twin discrete physics estimator and residual drift.
- [`tests/test_valve.py`](file:///c:/projects/p1/New%20folder/tests/test_valve.py) (11 tests): Torricelli outflow orifice behavior and non-linear throttling.

### B. Live Streaming Suite (`scada_live/tests/` — 116 Tests)
- [`scada_live/tests/test_api_command_validation.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_api_command_validation.py) (12 tests): REST JSON schema rejection, auth tokens, and 60-tick hold caps.
- [`scada_live/tests/test_gateway_safety_rule.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_gateway_safety_rule.py) (8 tests): Upper ($1.25\text{ m}$) and lower ($0.75\text{ m}$) safety boundary enforcements.
- [`scada_live/tests/test_phase0_imports.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase0_imports.py) (10 tests): Clean module imports and truth stripping from client packets.
- [`scada_live/tests/test_phase1_plant.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase1_plant.py) (7 tests): `LivePlant` stepping, standalone vs closed-loop modes, and noise generators.
- [`scada_live/tests/test_phase2_equivalence.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase2_equivalence.py) (8 tests): Tick-for-tick numerical equivalence between batch simulator and live streaming engine.
- [`scada_live/tests/test_phase3a_gateway.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase3a_gateway.py) (11 tests): Watchdog heartbeat synthetic packet generation and concurrency.
- [`scada_live/tests/test_phase3b_alert_metrics.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase3b_alert_metrics.py) (3 tests): Alert state machine, latching, and manual operator ack.
- [`scada_live/tests/test_phase3b_metrics.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase3b_metrics.py) (1 test): Out-of-band ground truth alignment and confusion counters.
- [`scada_live/tests/test_phase4_api.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase4_api.py) (9 tests): Flask API routes (`/api/config`, `/api/state`, `/api/history`, static UI).
- [`scada_live/tests/test_phase4_injector.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase4_injector.py) (4 tests): Live threat injector (FDI, Replay, DoS, Auth Misuse).
- [`scada_live/tests/test_phase6a_prevention.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase6a_prevention.py) (13 tests): Prevention mode, digital twin substitution, 30-min physical soak, DoS gap re-seed rule.
- [`scada_live/tests/test_phase6b_command_filtering.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase6b_command_filtering.py) (16 tests): Ingress blocking, continuous hold dropping, and envelope termination.
- [`scada_live/tests/test_phase7_auto_demo.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase7_auto_demo.py) (4 tests): Headless demo orchestration and speed multiplier.
- [`scada_live/tests/test_phase7_evaluation.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase7_evaluation.py) (4 tests): Multi-threat live benchmark evaluation harness.
- [`scada_live/tests/test_tamper_consistency_check.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_tamper_consistency_check.py) (6 tests): Actuator 4-way consistency checking for wire tampering.

---

## 4. Slowest Tests Profile

Top 5 slowest individual unit tests identified by `--durations=20`:
1. `scada_live/tests/test_phase6a_prevention.py::test_batch_replay_all_15_a3_scenarios` (**59.38s**): Replays all 15 DoS scenarios through full gateway stack.
2. `scada_live/tests/test_phase7_evaluation.py::test_execute_benchmark_fast_smoke` (**38.84s**): Runs complete live benchmark across threat instances.
3. `scada_live/tests/test_phase6b_command_filtering.py::test_am6_draining_monitor_dry_runs` (**34.23s**): Multi-seed draining soak test in monitor mode.
4. `scada_live/tests/test_phase6b_command_filtering.py::test_am5_filling_monitor_overflows` (**29.40s**): Multi-seed filling soak test in monitor mode.
5. `scada_live/tests/test_phase6a_prevention.py::test_gap_free_equivalence_rule_on_off` (**15.27s**): Mathematical verification of DoS gap step equivalence.

---

## 5. Determinism Verification (Run 1 vs Run 2)

Both suites were completely re-executed in Run 2 and audited via [`results_v2/scripts/compare_test_runs.py`](file:///c:/projects/p1/New%20folder/results_v2/scripts/compare_test_runs.py):
- **Batch Suite**: Run 1 = 66 passed (4.04s); Run 2 = 66 passed (2.79s).
- **Live Suite**: Run 1 = 116 passed (257.28s); Run 2 = 116 passed (257.71s).
- **Item-Level Verification**: 100% identical outcomes across all 182 test cases. Zero flaky tests, zero race conditions, and zero order dependencies detected ([`results_v2/_audit/determinism.md`](file:///c:/projects/p1/New%20folder/results_v2/_audit/determinism.md)).
