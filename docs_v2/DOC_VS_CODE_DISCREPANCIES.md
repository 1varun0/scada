# Discrepancies Between Existing Documentation, Stored Data, and Active Code

## Purpose
This document audits and records every discrepancy, outdated claim, or contradiction between the legacy documentation set (`projectdocs/`, root markdown files) and the actual active codebase, database (`data/scada_ids.db`), result files (`experiments/results/`), and simulation scripts.

Every factual statement in this document is tagged with code or measured evidence: `[CODE path:line]`, `[MEASURED file]`, `[EXISTING-DOC file:line]`.

---

## 1. Summary of Identified Discrepancies

| ID | Topic | Existing Document Claim | Actual Code / Data Reality | Evidence Tag |
|---|---|---|---|---|
| D-01 | Dataset Scenario Count | 170 scenarios (60 normal + 110 attack) | Exactly 150 scenarios (60 normal + 90 attack: 45 A1, 15 A2, 15 A3, 15 A4) | [CODE matlab/run_all_scenarios.m:29-208], [MEASURED db_queries_output.txt] |
| D-02 | Attack Generation Mechanism | Injected during simulation with closed-loop physical reaction | Post-hoc overlay on pre-recorded finished normal runs; zero closed-loop reaction in FDI | [CODE matlab/run_all_scenarios.m:94-96], [CODE matlab/attacks/apply_fdi.m:34-45] |
| D-03 | Attack Boundaries & Discontinuities | Smooth cyber-physical progression | Instant step level jumps at attack exit ($t_{end}+1$) for DoS and Auth Misuse | [CODE matlab/attacks/apply_dos.m:45-55], [MEASURED compute_a3_mechanism_detailed.txt] |
| D-04 | Policy Engine Thresholds | "Checks pump MUST be OFF when Level > 1.2m" | v1 checks only $H > 2.45\text{m}$ (overflow) or $H < 0.3\text{m}$; v2 assigns $H_{off}=1.2\text{m}$ but leaves it unused | [CODE engines/policy_engine.py:35-58], [EXISTING-DOC projectdocs/ARCHITECTURE.md:50] |
| D-05 | Batch Evaluation Detections | Policy Engine detected attacks in batch evaluation | Zero ($S_c = 0.0$) policy detections across all 99,000 batch evaluation rows | [CODE scripts/run_evaluation.py:114], [MEASURED data/evaluation_results.csv] |
| D-06 | Evaluation Storage Location | Results stored in SQLite `evaluation_results` table | SQLite tables `evaluation_results` and `experiment_runs` have 0 rows; results reside in CSV | [CODE dashboard/app.py:41-42], [MEASURED db_queries_output.txt] |
| D-07 | Physics Threshold Origin ($\tau_p$) | Statistically derived optimal boundary | Exactly $2 \times \text{E0 P99}$ ($2 \times 0.017458 = 0.034916 \approx 0.035\text{m}$); 0.3% margin against stored normals | [CODE scripts/run_e0_validation.py:186], [MEASURED recompute_all60_residuals.txt] |
| D-08 | Live vs Stored Normal Conditions | Live plant exercises full operational dynamics | Stored normals have 4 conditions (step, ramp, recovery); live plant runs steady-state cycling only | [CODE config/scenarios.py:284-335], [CODE scada_live/plant_sim/plant.py:13-39] |
| D-09 | Sensor Flow Noise Model | Gaussian white noise $\mathcal{N}(0, \sigma^2)$ | Flow noise is clamped with $\max(0, Q + \text{noise})$ in batch, causing twin drift after 861 ticks | [CODE simulator/noise.py:53], [CODE matlab/run_single_scenario.m:134], [MEASURED run_soak_tick0.txt] |
| D-10 | A3 DoS Residual False Alarms | Physics engine robustly handles DoS | Stored DoS creates 7,561 post-attack residual false alarms unless Step 2b gap re-seed rule is applied | [MEASURED reconcile_a3_fp.txt], [CODE scada_live/scada_ids/streaming_ids.py:168-222] |
| D-11 | Separate Process Architecture | Standalone attacker server on :5001 and separate control server | `attacker_wire/server.py`, `control_server.py`, and `prevention.py` are stubs; logic is unified in `gateway_core.py` and `run_demo.py` | [CODE scada_live/attacker_wire/server.py:1], [CODE scada_live/scada_ids/control_server.py:1] |
| D-12 | UI Mode Switcher Status | Plan states mode toggle is pending or command line only | Fully implemented in Defender Dashboard UI (`btn-mode-toggle` in `defender.html` and `app.js`) | [CODE scada_live/scada_ids/static/defender.html:30], [CODE scada_live/scada_ids/static/js/app.js:17-30] |

---

## 2. Detailed Technical Audit of Discrepancies

### D-01: Scenario Count Discrepancy (170 vs 150)
- **Existing Document Text:**  
  "Total scenarios: 170 (60 normal + 110 attack)" [EXISTING-DOC matlab/run_all_scenarios.m:3], "The MATLAB script (run_all_scenarios.m) is the primary data generator because it can batch-run 170 scenarios" [EXISTING-DOC matlab/scada_simulink_guide.m:84], "Attack Scenarios (110 Scenarios: A1_001 – A4_015)" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md:118].
- **Code & Data Evidence:**  
  In `matlab/run_all_scenarios.m`, the loops generate:
  - Normals: 60 scenarios (`N_001` to `N_060`) [CODE matlab/run_all_scenarios.m:29-84].
  - A1 FDI: 45 scenarios (`A1_001` to `A1_045`) [CODE matlab/run_all_scenarios.m:86-155].
  - A2 Replay: 15 scenarios (`A2_001` to `A2_015`) [CODE matlab/run_all_scenarios.m:157-170].
  - A3 DoS: 15 scenarios (`A3_001` to `A3_015`) [CODE matlab/run_all_scenarios.m:172-185].
  - A4 Auth Misuse: 15 scenarios (`A4_001` to `A4_015`) [CODE matlab/run_all_scenarios.m:187-219].
  - Total scenarios: $60 + 45 + 15 + 15 + 15 = 150$.
  - Database verification: `SELECT COUNT(DISTINCT scenario_id) FROM scada_telemetry` yields exactly 150 [MEASURED docs_v2/_audit/outputs/db_queries_output.txt]. Directory `matlab/data/` contains exactly 150 scenario CSVs plus `attack_scenarios.csv`.
- **Verdict:** Legacy documents and script comments carry an unedited draft count of 170 (which assumed 110 attacks). The true dataset size is 150 scenarios (150,000 records).

---

### D-02: Attack Generation Mechanism (Post-Hoc Overlays vs Closed-Loop Simulation)
- **Existing Document Text:**  
  "Large Additive Bias... Forces controller to prematurely cut pump, inducing progressive tank drainage" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md:131-132].
- **Code & Data Evidence:**  
  In `matlab/run_all_scenarios.m`:
  ```matlab
  % Lines 94-96:
  raw = run_single_scenario('Steady_State', 1.0, 1000, seed);
  corrupted = apply_fdi(raw, 300, 500, 'bias', 0.05);
  ```
  `run_single_scenario` runs a full 1,000-second peaceful simulation to completion. `apply_fdi.m` then modifies only the telemetry columns `tank_level_observed` in the pre-recorded output table [CODE matlab/attacks/apply_fdi.m:34-45].
  Because the controller ran during the initial peaceful run, it never received the corrupted level. Consequently, the pump commands and true water level are 100% identical to the peaceful baseline run. The tank never drained, and the controller never cut the pump early.
- **Verdict:** Stored FDI attacks are post-hoc telemetry overlays with zero closed-loop physical reaction.

---

### D-03: Attack Boundaries & Discontinuities
- **Existing Document Text:**  
  "Continuous hydrodynamic state integration... Mass balance" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md:40-42].
- **Code & Data Evidence:**  
  In `matlab/attacks/apply_dos.m` and `matlab/attacks/apply_auth_misuse.m`:
  - The attack modification loop runs strictly for $t \in [t_{start}, t_{end}]$.
  - In A3 DoS, fail-safe locks pump and valve for the duration, causing tank level to deviate from the peaceful baseline. At $t = t_{end} + 1$, the overlay loop exits, and the table immediately resumes the pre-recorded peaceful baseline values.
  - In scenario A3_010, the level jumps instantaneously from 1.022m to 1.189m in a single timestep [MEASURED experiments/results/compute_a3_mechanism_detailed.txt].
- **Verdict:** Stored datasets contain artificial step discontinuities at attack termination ($t_{end} + 1$) caused by post-hoc overlay splicing.

---

### D-04 & D-05: Policy Engine Rules & Zero Evaluation Detections
- **Existing Document Text:**  
  "Policy Engine: A deterministic rule engine that encodes the standard operating procedures of the SCADA controller (e.g., 'Pump MUST be OFF when Level > 1.2m')" [EXISTING-DOC projectdocs/ARCHITECTURE.md:48-51].
- **Code & Data Evidence:**  
  - In `engines/policy_engine.py:35-43` (v1 `evaluate`):
    - Checks only $H > 2.45\text{m}$ with pump ON, or $H < 0.3\text{m}$ with valve $> 50\%$.
    - It does NOT check whether pump is ON above 1.2m or OFF below 0.8m.
  - In `engines/policy_engine.py:53-54` (v2 `evaluate_v2`):
    - Variables `h_off = 1.2` and `h_on = 0.8` are initialized on lines 53-54 but never referenced in subsequent conditions. It checks only valve consistency (`valve == 50%` or `valve == 0% and pump == 0`) and then falls back to v1.
  - In `scripts/run_evaluation.py:114`, evaluation calls v1 `self.policy_engine.evaluate(...)`. Because no scenario in the evaluation split breaches $H > 2.45\text{m}$ with pump ON or $H < 0.3\text{m}$, the score $S_c = 0.0$ for all 99,000 timesteps [MEASURED data/evaluation_results.csv].
- **Verdict:** The Policy Engine in the batch evaluation pipeline produced zero detections. Complete policy enforcement against live deadband boundaries was only achieved later via `evaluate_command_with_live_setpoint` [CODE scada_live/scada_ids/gateway_core.py:22-66].

---

### D-06: Storage of Evaluation Results
- **Existing Document Text:**  
  `projectdocs/ARCHITECTURE.md` and schema definitions list `evaluation_results` as an active database table in `data/scada_ids.db`.
- **Code & Data Evidence:**  
  - Database query: `SELECT count(*) FROM evaluation_results` returns 0 [MEASURED docs_v2/_audit/outputs/db_queries_output.txt].
  - `dashboard/app.py` lines 40-42 explicitly states:  
    `# We need to query evaluation_results from CSV or check if it exists in DB. # Wait, run_evaluation.py writes to evaluation_results.csv, not the database directly! # Let's read from CSV and merge in pandas.` [CODE dashboard/app.py:40-42].
- **Verdict:** SQLite database table `evaluation_results` is empty. The ground-truth evaluation results are stored in `data/evaluation_results.csv` (99,000 rows).

---

### D-07: Physics Threshold Origin ($\tau_p = 0.035\text{m}$)
- **Existing Document Text:**  
  "Thresholds tuned against validation split" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md].
- **Code & Data Evidence:**  
  - `scripts/run_e0_validation.py` lines 186-189 measures the 99th percentile residual of E0 normal operation as $0.017458\text{m}$ and suggests $\tau_p = 0.0175\text{m}$ [MEASURED docs_v2/_audit/outputs/run_e0_validation_output.txt].
  - Production `tau_p = 0.035\text{m}` in `config/parameters.py:65` is exactly $2 \times \text{E0 P99}$ ($2 \times 0.017458 = 0.034916 \approx 0.035\text{m}$).
  - `experiments/recompute_all60_residuals.py` shows that across all 60 stored normals, the maximum absolute residual is $0.034884\text{m}$. The margin to false alarm is only $0.035000 - 0.034884 = 0.000116\text{m}$ (0.3%) [MEASURED experiments/results/recompute_all60_residuals.txt].
- **Verdict:** $\tau_p = 0.035\text{m}$ was set as an uncalibrated $2 \times$ multiplier of E0 P99 rather than an analytically derived boundary, leaving a 0.3% margin against stored normal traces.

---

### D-08: Live vs Stored Normal Conditions
- **Existing Document Text:**  
  "Simulation exercises continuous operational variability across all operational conditions" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md:105-115].
- **Code & Data Evidence:**  
  - Stored batch normal scenarios include Setpoint Step Changes ($1.0 \to 1.5\text{m}$), Variable Load Ramps ($0.8 \to 1.4\text{m}$), and Low Level Recovery ($0.5 \to 1.0\text{m}$) [CODE config/scenarios.py:284-335].
  - The live simulation plant (`LivePlant` in `scada_live/plant_sim/plant.py:13-39`) only runs steady-state autonomous cycling between 0.8m and 1.2m around a fixed 1.0m setpoint.
- **Verdict:** Dynamic setpoint ramps and recovery profiles exist only in the batch dataset, not in the live simulation plant.

---

### D-09: Clamped Flow Noise and Digital Twin Drift
- **Existing Document Text:**  
  "Zero-mean Gaussian noise perturbation" [EXISTING-DOC projectdocs/DATASET_DOCUMENTATION.md:27-29].
- **Code & Data Evidence:**  
  - In `simulator/noise.py:53`, `matlab/run_single_scenario.m:134-135`, and `matlab/attacks/apply_auth_misuse.m:75-76`, flow noise is clamped:  
    `q_in_observed = max(0, q_in + noise)`.
  - When true flow is 0, clamping produces positive expectation bias $E[\tilde{Q}] = \sigma_Q / \sqrt{2\pi} \approx 3.99 \times 10^{-5}\text{ m}^3/\text{s}$.
  - Over a continuous run without recalibration, the Digital Twin integrates zero true inflow while the observed sensor carries positive bias, accumulating drift. At $t = 861\text{ s}$, the residual breaches $\tau_p = 0.035\text{m}$, triggering false alarms in 100% of 60-minute clamped soaks [MEASURED experiments/results/run_soak_tick0.txt, experiments/results/soak_comparison_results.csv].
  - In `scada_live/config.yaml:35`, `clamp_flow_noise: false` is explicitly set to prevent drift during live execution.
- **Verdict:** Flow noise clamping is present in the stored dataset and causes systematic drift after 860 ticks, but is disabled in live configuration.

---

### D-10: DoS Gap Residuals and the Step 2b Re-Seed Rule
- **Existing Document Text:**  
  "Availability Engine flags DoS instantly with zero residual impact" [EXISTING-DOC projectdocs/ARCHITECTURE.md:53-56].
- **Code & Data Evidence:**  
  - When DoS severs telemetry, the physical plant continues moving under fail-safe outflow, while the Digital Twin receives zero inflows and zero outflows.
  - When telemetry restores, the abrupt level discrepancy triggers severe physics residuals ($S_p > 0.95$), generating 7,561 false positive ticks across the 15 A3 scenarios in batch evaluation [MEASURED experiments/results/reconcile_a3_fp.txt].
  - In `scada_live/scada_ids/streaming_ids.py:168-222`, the Step 2b DoS gap re-seed rule resynchronizes the twin to the post-gap sensor median if the jump satisfies physical slew limits ($v_{max} \cdot G \cdot dt + 3\sigma$).
  - Limitation: If an adversary alters physical level during the DoS beyond the physical rate band, re-seed is refused and twin takeover is suppressed to prevent runaway actuation.
- **Verdict:** Stored DoS traces produce extensive post-attack physics false alarms unless the Step 2b gap re-seed rule is active.

---

### D-11: Multi-Process Architecture Status
- **Existing Document Text:**  
  "Attacker console runs as an independent Flask process on port 5001" [EXISTING-DOC projectdocs/SCADA_Hybrid_IDS_Plan.md].
- **Code & Data Evidence:**  
  - `scada_live/attacker_wire/server.py` contains only `# Phase 5: Flask server on :5001` [CODE scada_live/attacker_wire/server.py:1-2].
  - `scada_live/scada_ids/control_server.py` and `scada_live/scada_ids/prevention.py` are stubs with `pass` [CODE scada_live/scada_ids/control_server.py:1-2, scada_live/scada_ids/prevention.py:1-2].
  - Attacker injection runs in-process via `Injector` wrapping `GatewayClient`, coordinated by `run_demo.py` [CODE run_demo.py:349-351].
- **Verdict:** The multi-process attacker console and separate control servers are stubs; live simulation is orchestrated as a single threaded application by `run_demo.py`.

---

### D-12: UI Mode Toggle Status
- **Existing Document Text:**  
  Earlier review notes questioned whether the UI mode toggle was implemented or only controllable via CLI.
- **Code & Data Evidence:**  
  - `scada_live/scada_ids/static/defender.html:28-33` contains `<button id="btn-mode-toggle" class="btn-mode monitor">MONITOR</button>`.
  - `scada_live/scada_ids/static/js/app.js:17-30` implements `toggleMode()` calling `POST /api/mode` and updating UI classes.
  - Server route `/api/mode` [CODE scada_live/scada_ids/server.py:147-156] accepts GET and POST, dynamically switching `GatewayCore.mode` between `monitor` and `prevention`.
- **Verdict:** The UI mode toggle is fully implemented and operational in the Defender Dashboard.
