# SCADA Hybrid IDS — Comprehensive Codebase Map (v2)

**Title:** SCADA Hybrid IDS — Comprehensive Codebase Map (v2)  
**Purpose:** Detailed file-by-file directory map, public symbol inventory, architectural roles, call hierarchies, and covering test suites  
**Audience:** Software engineers, code reviewers, and system maintainers  
**Generated from commit:** `b7a6c999dd0b333475349fb33c3272ea434b447c`  
**Date:** 2026-10-13  
**Status:** Audited & Verified  

---

## 1. Architectural Directory Overview

The codebase is structured into cohesive domains separating physics simulation, machine learning detection, data persistence, and real-time network defense:

```
C:\projects\p1\New folder\
├── simulator/          # Physical components (Tank, Pump, Valve, Controller, Noise)
├── config/             # Parameter sheets (parameters.py, scenarios.py)
├── digital_twin/       # Digital Twin physics model (PhysicsTwin)
├── engines/            # 4 specialized detection engines and multi-evidence fusion
├── models/             # PyTorch LSTM-Autoencoder and DataPreprocessor
├── evaluation/         # Performance metrics, confusion matrix, and reporting
├── storage/            # SQLite client for scada_telemetry table
├── scripts/            # Training, dataset import, and validation CLI scripts
├── matlab/             # MATLAB generation scripts and attack overlays
├── dashboard/          # Legacy batch inspection dashboard (Flask port 5000)
├── scada_live/         # Real-time closed-loop simulation and defender gateway
│   ├── common/         # Dataclasses (TelemetryPacket, CommandPacket), config loader
│   ├── plant_sim/      # LivePlant real-time physics and GatewayClient
│   ├── attacker_wire/  # In-flight Injector proxy
│   └── scada_ids/      # GatewayCore, StreamingIDS, AlertManager, Defender UI
├── experiments/        # Benchmark scripts, sweeps, and committed results
├── tests/              # Batch unit tests (66 passed)
└── scada_live/tests/   # Live simulation and gateway tests (116 passed)
```

---

## 2. Master Codebase Reference Table

The table below compiles every active source, configuration, and test file across the project:

| File Path | Domain | Primary Purpose | Key Symbols / Classes / Routes | Covering Tests |
|---|---|---|---|---|
| [`simulator/tank.py`](file:///c:/projects/p1/New%20folder/simulator/tank.py) | Physics | Liquid mass balance ODE integration | `Tank.step()`, `Tank.reset()`, `Tank.level` | `tests/test_tank.py` |
| [`simulator/pump.py`](file:///c:/projects/p1/New%20folder/simulator/pump.py) | Physics | Centrifugal pump with 2s transport delay | `Pump.step()`, `Pump.set_command()`, `Pump.flow` | `tests/test_pump.py` |
| [`simulator/valve.py`](file:///c:/projects/p1/New%20folder/simulator/valve.py) | Physics | Torricelli gravity valve with slew limiter | `Valve.step()`, `Valve.compute_outflow()` | `tests/test_valve.py` |
| [`simulator/controller.py`](file:///c:/projects/p1/New%20folder/simulator/controller.py) | Physics | Bang-bang hysteresis with deadband & fail-safe | `Controller.step()`, `Controller.reset()` | `tests/test_controller.py` |
| [`simulator/noise.py`](file:///c:/projects/p1/New%20folder/simulator/noise.py) | Physics | Gaussian perturbation with optional clamp | `NoiseGenerator.add_level_noise()`, `add_flow_noise()` | `tests/test_simulator.py` |
| [`simulator/process_simulator.py`](file:///c:/projects/p1/New%20folder/simulator/process_simulator.py) | Physics | Closed-loop integration harness | `ProcessSimulator.run_scenario()`, `step()` | `tests/test_simulator.py` |
| [`simulator/scenario_runner.py`](file:///c:/projects/p1/New%20folder/simulator/scenario_runner.py) | Physics | Multi-scenario batch runner | `ScenarioRunner.run_all()` | `tests/test_simulator.py` |
| [`config/parameters.py`](file:///c:/projects/p1/New%20folder/config/parameters.py) | Config | Frozen physical constants and thresholds | `PARAMS`, `TankParams`, `PumpParams`, `ValveParams` | All test suites |
| [`config/scenarios.py`](file:///c:/projects/p1/New%20folder/config/scenarios.py) | Config | 150 scenario definitions and profiles | `SCENARIOS`, `get_scenario_by_id()` | `tests/test_simulator.py` |
| [`digital_twin/physics_twin.py`](file:///c:/projects/p1/New%20folder/digital_twin/physics_twin.py) | Twin | Independent mass-balance estimator | `PhysicsTwin.step()`, `PhysicsTwin.reset()` | `tests/test_twin.py` |
| [`engines/physics_engine.py`](file:///c:/projects/p1/New%20folder/engines/physics_engine.py) | IDS | Residual evaluation $|H_{obs} - H_{twin}| / \tau_p$ | `PhysicsEngine.step()`, `PhysicsEngine.reset()` | `tests/test_engines.py` |
| [`engines/temporal_engine.py`](file:///c:/projects/p1/New%20folder/engines/temporal_engine.py) | IDS | LSTM reconstruction loss evaluation | `TemporalEngine.evaluate()` | `tests/test_engines.py` |
| [`engines/policy_engine.py`](file:///c:/projects/p1/New%20folder/engines/policy_engine.py) | IDS | Deterministic rule checking (v1 and v2) | `PolicyEngine.evaluate()`, `evaluate_v2()` | `tests/test_engines.py` |
| [`engines/availability_engine.py`](file:///c:/projects/p1/New%20folder/engines/availability_engine.py) | IDS | Network age and packet drop scoring | `AvailabilityEngine.evaluate()` | `tests/test_engines.py` |
| [`engines/fusion_engine.py`](file:///c:/projects/p1/New%20folder/engines/fusion_engine.py) | IDS | Multi-evidence max-vote fusion | `FusionEngine.evaluate()`, `FusionEngine.strategy` | `tests/test_fusion.py` |
| [`models/lstm_autoencoder.py`](file:///c:/projects/p1/New%20folder/models/lstm_autoencoder.py) | ML | PyTorch LSTM autoencoder (5-32-5) | `LSTMAutoencoder`, `Encoder`, `Decoder` | `scripts/train_lstm.py` |
| [`models/preprocessor.py`](file:///c:/projects/p1/New%20folder/models/preprocessor.py) | ML | MinMax scaler and window creator ($W=10$) | `DataPreprocessor.fit_transform()`, `transform()` | `tests/test_engines.py` |
| [`models/trainer.py`](file:///c:/projects/p1/New%20folder/models/trainer.py) | ML | PyTorch training harness with early stopping | `ModelTrainer.train()`, `ModelTrainer.evaluate()` | `scripts/train_lstm.py` |
| [`evaluation/metrics.py`](file:///c:/projects/p1/New%20folder/evaluation/metrics.py) | Eval | Confusion matrix and statistical rates | `compute_confusion_matrix()`, `compute_metrics()` | `tests/test_engines.py` |
| [`evaluation/ablation.py`](file:///c:/projects/p1/New%20folder/evaluation/ablation.py) | Eval | Multi-engine ablation test harness | `AblationStudy.run_study()` | `scripts/run_ablation.py` |
| [`evaluation/reporter.py`](file:///c:/projects/p1/New%20folder/evaluation/reporter.py) | Eval | Markdown and console report generator | `EvaluationReporter.generate_markdown_report()` | `scripts/run_evaluation.py` |
| [`storage/sqlite_client.py`](file:///c:/projects/p1/New%20folder/storage/sqlite_client.py) | Data | SQLite WAL-mode client for `scada_ids.db` | `SQLiteClient.init_db()`, `insert_telemetry()` | `tests/test_simulator.py` |
| [`scripts/import_matlab_csv.py`](file:///c:/projects/p1/New%20folder/scripts/import_matlab_csv.py) | Tools | Ingests 150 MATLAB CSVs into SQLite | `import_all_scenarios()` | Self-validated |
| [`scripts/run_evaluation.py`](file:///c:/projects/p1/New%20folder/scripts/run_evaluation.py) | Tools | Batch pipeline benchmark across 99 scenarios | `main()` | Self-validated |
| [`scripts/train_lstm.py`](file:///c:/projects/p1/New%20folder/scripts/train_lstm.py) | Tools | Trains PyTorch model on 42 train normals | `main()` | Self-validated |
| [`scripts/run_e0_validation.py`](file:///c:/projects/p1/New%20folder/scripts/run_e0_validation.py) | Tools | Validates physical parameters on normal run | `main()` | Output captured |
| [`scripts/validate_matlab_vs_python.py`](file:///c:/projects/p1/New%20folder/scripts/validate_matlab_vs_python.py) | Tools | Proves equivalence between MATLAB and Python | `main()` | Output captured |
| [`dashboard/app.py`](file:///c:/projects/p1/New%20folder/dashboard/app.py) | UI | Batch scenario inspection web server | `GET /`, `GET /api/scenarios`, `GET /api/telemetry/<id>` | Manual inspection |
| [`run_demo.py`](file:///c:/projects/p1/New%20folder/run_demo.py) | Runner | Unified live launcher, soak test, auto demo | `main()`, `AutoDemoCoordinator`, `run_plant_loop` | `scada_live/tests/test_phase7_auto_demo.py` |
| [`scada_live/config.yaml`](file:///c:/projects/p1/New%20folder/scada_live/config.yaml) | Config | Configuration sheet for live defense system | `tank`, `pump`, `valve`, `ids`, `prevention`, `network` | All live tests |
| [`scada_live/common/config_loader.py`](file:///c:/projects/p1/New%20folder/scada_live/common/config_loader.py) | Live | YAML loader converting dicts to SimpleNamespace | `load_config()`, `_dict_to_namespace()` | `scada_live/tests/test_phase0_imports.py` |
| [`scada_live/common/packets.py`](file:///c:/projects/p1/New%20folder/scada_live/common/packets.py) | Live | Telemetry and Command packet dataclasses | `TelemetryPacket`, `CommandPacket` | `scada_live/tests/test_phase0_imports.py` |
| [`scada_live/common/transport.py`](file:///c:/projects/p1/New%20folder/scada_live/common/transport.py) | Live | HTTP client and SSE generator wrapper | `TransportClient`, `TransportServer` | `scada_live/tests/test_phase0_imports.py` |
| [`scada_live/plant_sim/plant.py`](file:///c:/projects/p1/New%20folder/scada_live/plant_sim/plant.py) | Live | Real-time single-tank plant simulation | `LivePlant.observe()`, `advance()`, `step()` | `scada_live/tests/test_phase1_plant.py` |
| [`scada_live/plant_sim/gateway_client.py`](file:///c:/projects/p1/New%20folder/scada_live/plant_sim/gateway_client.py) | Live | Two-call client communicating with Gateway | `GatewayClient.sense()`, `send_telemetry()` | `scada_live/tests/test_phase3a_gateway.py` |
| [`scada_live/plant_sim/server.py`](file:///c:/projects/p1/New%20folder/scada_live/plant_sim/server.py) | Live | Legacy multi-process plant server (:5100) | `GET /telemetry`, `POST /command`, `GET /status` | `scada_live/tests/test_phase1_plant.py` |
| [`scada_live/attacker_wire/injector.py`](file:///c:/projects/p1/New%20folder/scada_live/attacker_wire/injector.py) | Live | Wire proxy injecting FDI, Replay, DoS, Tamper | `Injector.sense()`, `send_telemetry()`, `start_attack()` | `scada_live/tests/test_phase4_injector.py` |
| [`scada_live/scada_ids/streaming_ids.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/streaming_ids.py) | Live | Stateful streaming IDS with DoS gap re-seed | `StreamingIDS.update()`, `get_twin_estimate()` | `scada_live/tests/test_phase2_equivalence.py` |
| [`scada_live/scada_ids/alert_manager.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/alert_manager.py) | Live | Sliding window N-of-W alert latching state machine | `AlertManager.update()`, `acknowledge()` | `scada_live/tests/test_phase3b_alert_metrics.py` |
| [`scada_live/scada_ids/gateway_core.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/gateway_core.py) | Live | Central coordinator, safety rules, prevention | `GatewayCore.process_sense()`, `process_telemetry()` | `scada_live/tests/test_phase3a_gateway.py` |
| [`scada_live/scada_ids/server.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/server.py) | Live | Gateway REST & SSE server (21 routes, :5000) | `app`, `POST /api/sense`, `POST /api/command`, etc. | `scada_live/tests/test_phase4_api.py` |
| [`scada_live/scada_ids/sse_hub.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/sse_hub.py) | Live | Multi-client queue fanout with overflow drop | `EventHub.subscribe()`, `publish()`, `unsubscribe()` | `scada_live/tests/test_phase3a_gateway.py` |
| [`scada_live/scada_ids/db_writer.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/db_writer.py) | Live | Background queue worker writing to `live_run.db` | `DBWriter.write_tick()`, `write_event()` | `scada_live/tests/test_phase3a_gateway.py` |
| [`scada_live/scada_ids/metrics.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/metrics.py) | Live | In-memory truth joiner and live metrics collector | `MetricsCollector.update_truth()`, `update_verdict()` | `scada_live/tests/test_phase3b_metrics.py` |
| [`scada_live/scada_ids/static/defender.html`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/static/defender.html) | Live UI | HTML5 interface with SVG tank & Chart.js canvas | DOM elements: `#tank-svg`, `#btn-mode-toggle` | Browser verified |
| [`scada_live/scada_ids/static/js/app.js`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/static/js/app.js) | Live UI | Client SSE stream handler, charts, mode toggle | `toggleMode()`, `startSSE()`, `updateChart()` | Browser verified |

---

## 3. Test Suite Organization

The project contains two comprehensive test suites totaling **182 passing tests**:

### 3.1 Batch Unit Test Suite (`tests/`, 66 Tests, 1.86s)
Evaluates low-level physical dynamics and isolated algorithmic components [MEASURED docs_v2/_audit/outputs/pytest_batch_output.txt]:
- `test_tank.py` (11 tests): Mass balance, saturation limits, error checking.
- `test_pump.py` (9 tests): Transport delay buffer, maximum flow capacity.
- `test_valve.py` (11 tests): Torricelli outflow equation, slew-rate clamping.
- `test_controller.py` (8 tests): Hysteresis deadband switching, emergency fail-safe override.
- `test_twin.py` (11 tests): Digital twin forward integration, state resetting.
- `test_engines.py` (4 tests): Physics residual, LSTM reconstruction, policy rules, availability age.
- `test_fusion.py` (2 tests): Max-vote and weighted average fusion strategies.
- `test_simulator.py` (10 tests): Closed-loop simulation stepping, noise generation.

### 3.2 Live Simulation Test Suite (`scada_live/tests/`, 116 Tests, 314.58s)
Evaluates real-time networking, prevention state machines, and benchmark execution [MEASURED docs_v2/_audit/outputs/pytest_live_output.txt]:
- `test_api_command_validation.py` (12 tests): Ingress JSON schema, types, hold duration capping ($\le 60\text{ ticks}$), HMAC authentication.
- `test_gateway_safety_rule.py` (8 tests): Dynamic setpoint and deadband boundary checks (AM-1 through AM-6).
- `test_phase0_imports.py` (10 tests): Dataclass structure, ground-truth stripping.
- `test_phase1_plant.py` (7 tests): Live plant simulation, noise models, standalone stepping.
- `test_phase2_equivalence.py` (8 tests): Exact numerical equivalence between batch `ProcessSimulator` and streaming `LivePlant`.
- `test_phase3a_gateway.py` (11 tests): Two-call protocol, watchdog synthetic packet emission, concurrency, 1,800-tick soak test (`test_soak_30min`).
- `test_phase3b_alert_metrics.py` (3 tests): Alert manager state machine (SAFE $\to$ SUSPICIOUS $\to$ CRITICAL).
- `test_phase3b_metrics.py` (1 test): Truth joining and episode metrics compilation.
- `test_phase4_api.py` (9 tests): REST endpoints and plant control actions.
- `test_phase4_injector.py` (4 tests): In-flight attack corruption and out-of-band truth emission.
- `test_phase6a_prevention.py` (13 tests): Prevention mode switching, Digital Twin takeover, clean handback.
- `test_phase6b_command_filtering.py` (16 tests): Ingress command blocking and continuous hold enforcement.
- `test_phase7_auto_demo.py` (4 tests): Unattended 7-phase presentation coordinator.
- `test_phase7_evaluation.py` (4 tests): Scenario metadata integrity, benchmark execution smoke test.
- `test_tamper_consistency_check.py` (6 tests): 4-way actuator consistency check flagging downstream fieldbus overrides in $\le 3\text{ ticks}$.

---

## 4. Code Health & Dead Code Audit

During the line-by-line audit, several stub files and unused variables were identified:

1. **Stubs / Unimplemented Modules:**
   - [`scada_live/attacker_wire/server.py`](file:///c:/projects/p1/New%20folder/scada_live/attacker_wire/server.py): Contains only `# Phase 5: Flask server on :5001`. Attack injection is handled in-process by `Injector` wrapping `GatewayClient`.
   - [`scada_live/scada_ids/control_server.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/control_server.py): Contains `class ControlServer: pass # Phase 6`. All control logic resides in `GatewayCore`.
   - [`scada_live/scada_ids/prevention.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/prevention.py): Contains `class PreventionController: pass # Phase 6`. Prevention is integrated directly into `GatewayCore`.
   - [`scada_live/run_all.py`](file:///c:/projects/p1/New%20folder/scada_live/run_all.py): Contains `print("Phase 5: launcher not yet implemented")`. All live launching is orchestrated by root `run_demo.py`.
2. **Unused Local Variables:**
   - In [`engines/policy_engine.py:53-54`](file:///c:/projects/p1/New%20folder/engines/policy_engine.py#L53-L54) (`evaluate_v2`), variables `h_off = 1.2` and `h_on = 0.8` are initialized but never referenced in subsequent logic.
3. **Empty Database Tables:**
   - SQLite tables `evaluation_results` and `experiment_runs` in `data/scada_ids.db` contain zero rows [MEASURED docs_v2/_audit/outputs/db_queries_output.txt]. Evaluation results reside in `data/evaluation_results.csv`.

---

## 5. Verification

1. **File Existence:** Every referenced file was verified to exist on disk at the indicated path.
2. **Line Number Accuracy:** Line numbers were cross-referenced against the HEAD commit (`b7a6c999dd0b333475349fb33c3272ea434b447c`).
3. **Test Counts:** All 182 tests were executed and passed without failure [MEASURED docs_v2/_audit/outputs/pytest_batch_output.txt, docs_v2/_audit/outputs/pytest_live_output.txt].
