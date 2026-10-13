# 16 — Glossary & Mathematical Notations

- **Audience**: All project contributors, researchers, auditors, and system operators
- **Scope**: Comprehensive lexicon of terminology, physical dimensions, SI units, mathematical symbols, operational states, attack taxonomies, and architectural abbreviations across the batch and live systems
- **Status**: Complete & Code-Audited
- **Evidence Tags**: `[CODE]`, `[MEASURED]`, `[EXISTING-DOC]`, `[DESIGN-INTENT]`

---

## 1. Physical Process Variables & Units

All continuous plant equations and discrete simulation steps strictly observe SI units unless explicitly noted:

| Symbol | Variable Name | SI Unit | Canonical Value in Code | Code Definition / Reference |
| :---: | :--- | :---: | :---: | :--- |
| $H$ | Tank Fluid Level | $\text{m}$ (meters) | Operating in $[0.0, 2.5]\text{ m}$ | `tank.level` [CODE simulator/tank.py:46] |
| $H_0$ | Initial Fluid Level | $\text{m}$ (meters) | $1.00\text{ m}$ (nominal); $0.4\text{ m}, 2.1\text{ m}$ in A4 | `initial_level_m` [CODE config/parameters.py:31] |
| $H_{\text{set}}$ | Target Setpoint Level | $\text{m}$ (meters) | $1.00\text{ m}$ (nominal); profiles in $[0.8, 1.5]$ | `setpoint_profile` [CODE config/scenarios.py:31-56] |
| $A$ | Tank Cross-Sectional Area | $\text{m}^2$ | $2.00\text{ m}^2$ | `tank.area` [CODE config/parameters.py:30] |
| $H_{\text{max}}$ | Physical Tank Height Crest | $\text{m}$ (meters) | $2.50\text{ m}$ | `tank.max_height` [CODE config/parameters.py:29] |
| $H_{\text{overflow}}$ | Structural Overflow Threshold | $\text{m}$ (meters) | $2.20\text{ m}$ (live), $2.50\text{ m}$ (crest) | `metrics.overflow_threshold_m` [CODE scada_live/config.yaml:75] |
| $H_{\text{dry}}$ | Pump Cavitation / Dry Limit | $\text{m}$ (meters) | $0.30\text{ m}$ | `metrics.dry_run_threshold_m` [CODE scada_live/config.yaml:76] |
| $Q_{\text{in}}$ | Volumetric Inflow Rate | $\text{m}^3/\text{s}$ | Operating in $[0.0, 0.005]\text{ m}^3/\text{s}$ | `pump.flow` [CODE simulator/pump.py:35] |
| $Q_{\text{max}}$ | Maximum Pump Flow Capacity | $\text{m}^3/\text{s}$ | $0.005\text{ m}^3/\text{s}$ ($5.0\text{ L/s}$) | `pump.q_max` [CODE config/parameters.py:37] |
| $Q_{\text{out}}$ | Volumetric Outflow Discharge | $\text{m}^3/\text{s}$ | Calculated via Torricelli orifice | `valve.compute_outflow()` [CODE simulator/valve.py:36] |
| $C_v$ | Valve Flow Coefficient | $\text{m}^3/\text{s}$ | $0.004\text{ m}^3/\text{s}$ ($4.0\text{ L/s}$) | `valve.cv` [CODE config/parameters.py:44] |
| $V\%$ | Valve Aperture Percentage | $\%$ | $0.0\%\text{ to } 100.0\%$ ($50\%$ nominal) | `valve.position` [CODE simulator/valve.py:25] |
| $g$ | Standard Acceleration of Gravity | $\text{m/s}^2$ | $9.81\text{ m/s}^2$ | Torricelli discharge formulation [CODE docs_v2/03_FORMULAS_REFERENCE_V2.md] |
| $\Delta t$ ($dt$) | Simulation Timestep / Sample Period | $\text{s}$ (seconds) | $1.0\text{ s}$ ($1.0\text{ Hz}$ polling rate) | `simulation.dt` [CODE config/parameters.py:22] |
| $\sigma_{\text{sensor}}$ | Level Sensor Noise Std Dev | $\text{m}$ (meters) | $0.005\text{ m}$ ($5\text{ mm}$, $3\sigma = 1.5\text{ cm}$) | `simulation.noise_level` [CODE config/parameters.py:24] |
| $\sigma_{\text{flow}}$ | Flow Sensor Noise Std Dev | $\text{m}^3/\text{s}$ | $0.0001\text{ m}^3/\text{s}$ ($0.1\text{ L/s}$) | `simulation.noise_flow` [CODE config/parameters.py:25] |

---

## 2. Mathematical Notations & Algorithm Symbols

### State Estimates & Observers
- $\mathbf{x}_k$: Physical plant state vector at timestep $k$, representing true physical liquid level $[H_k]$.
- $\tilde{H}_k$: Noisy sensor measurement observed from the physical tank: $\tilde{H}_k = H_k + \eta_{\text{level},k}$.
- $\hat{H}_k$ ($h_{\text{twin}}$): Analytical state estimate produced by the Digital Twin physics observer via discrete Euler integration:
  $$\hat{H}_{k+1} = \hat{H}_k + \frac{Q_{\text{in},k} - Q_{\text{out},k}}{A} \Delta t$$
- $\mathbf{X}_k \in \mathbb{R}^{W \times D}$: Sliding window tensor supplied to the LSTM Autoencoder at timestep $k$, where window size $W = 10$ and feature dimension $D = 7$:
  $$\mathbf{X}_k = [\mathbf{x}_{k-W+1}, \dots, \mathbf{x}_k]$$
- $\hat{\mathbf{X}}_k \in \mathbb{R}^{W \times D}$: Reconstructed tensor produced by the PyTorch LSTM Autoencoder:
  $$\hat{\mathbf{X}}_k = \text{Decoder}(\text{Encoder}(\mathbf{X}_k))$$

### Residuals & Error Metrics
- $r_p(k)$: Physics Engine liquid level residual ($\text{m}$):
  $$r_p(k) = |\tilde{H}_k - \hat{H}_k|$$
- $r_l(k)$: Temporal Engine reconstruction mean squared error (MSE):
  $$r_l(k) = \frac{1}{W \cdot D} \sum_{i=1}^W \sum_{j=1}^D (\mathbf{X}_{k,i,j} - \hat{\mathbf{X}}_{k,i,j})^2$$
- $r_a(k)$: Availability Engine communication latency residual ($\text{ms}$):
  $$r_a(k) = \Delta t_{\text{arrival}} = (t_{\text{recv}} - t_{\text{prev\_recv}}) \times 1000$$

### Normalized Anomaly Scores
- $S_p(k) \in [0.0, 1.0]$: Normalized Physics Engine score:
  $$S_p(k) = \min\left(1.0, \frac{r_p(k)}{\tau_p}\right)$$
- $S_l(k) \in [0.0, 1.0]$: Normalized Temporal Engine score:
  $$S_l(k) = \min\left(1.0, \frac{r_l(k)}{\tau_l}\right)$$
- $S_c(k) \in \{0.0, 1.0\}$: Discrete Policy Engine compliance violation score ($1.0$ if control logic invariant breached, else $0.0$).
- $S_a(k) \in [0.0, 1.0]$: Normalized Availability Engine communication score ($0.0$ for on-time packets, scaling to $1.0$ at timeout $\tau_{a,\text{max}}$).
- $S_{\text{hybrid}}(k) \in [0.0, 1.0]$: Overall multi-evidence hybrid anomaly score under Max-Vote Fusion:
  $$S_{\text{hybrid}}(k) = \max(S_p(k), S_l(k), S_c(k), S_a(k))$$

### Calibrated Thresholds
- $\tau_p$: Physics residual threshold.
  - Batch: $0.035\text{ m}$ [CODE config/parameters.py:89].
  - Live: $0.080\text{ m}$ [CODE scada_live/config.yaml:70].
- $\tau_l$: Temporal LSTM reconstruction threshold.
  - Batch: $0.0085\text{ MSE}$ [CODE config/parameters.py:90].
  - Live: $0.080\text{ norm}$ / $0.950\text{ alert threshold}$ [CODE scada_live/config.yaml:70].
- $\tau_a$: Availability Warning latency threshold ($1500.0\text{ ms}$).
- $\tau_{a,\text{max}}$: Availability Critical communication loss threshold ($5000.0\text{ ms}$).
- $\tau_{\text{fusion}}$ / $\tau_{\text{alert}}$: Hybrid decision threshold ($0.50$ in batch; $0.95$ in max-vote alert evaluation).

---

## 3. Operational States & Control Boundaries

```
+----------------------------------------------------------------------------------------------------+
|                                 OPERATIONAL LEVEL REGIMES & BOUNDS                                  |
+====================================================================================================+
|  2.50 m  --  Physical Tank Crest (Structural Overflow in Batch: H >= 2.50m)                        |
|  2.20 m  --  Live Benchmark Overflow Alarm Boundary (overflow_threshold_m)                        |
|  1.25 m  --  Ingress Command Safety Interlock: High Cutoff (Pump ON command rejected)               |
|  1.20 m  --  Autonomous Controller Deadband Ceiling (Pump turns OFF)                               |
|  1.00 m  --  Nominal Operating Setpoint (H_set)                                                    |
|  0.80 m  --  Autonomous Controller Deadband Floor (Pump turns ON)                                  |
|  0.75 m  --  Continuous Safety Monitor Drain Interlock (Active drain hold dropped)                 |
|  0.30 m  --  Pump Cavitation & Structural Dry-Run Boundary (dry_run_threshold_m)                     |
|  0.00 m  --  Physical Bottom of Tank Basin                                                         |
+----------------------------------------------------------------------------------------------------+
```

### Operational Modes
- `monitor`: Passive observation mode. The gateway runs all IDS detection engines, logs anomaly scores, and broadcasts SSE alerts, but executes control feedback strictly using received sensor measurements.
- `prevention`: Active mitigation mode. When an anomaly is confirmed ($S_{\text{hybrid}} \ge 0.50$ or CRITICAL alert), `GatewayCore` switches `level_source = "twin"`, decoupling actuators from compromised telemetry and commanding the plant via analytical redundancy.

### Alert States (`alert_state`)
- `NORMAL`: All engine residuals reside safely below their respective thresholds ($S_{\text{hybrid}} < 0.50$). Level source remains `sensed`.
- `WARNING`: Anomaly scores elevate into transient buffer zone ($0.50 \le S_{\text{hybrid}} < 0.80$) without meeting persistence criteria. Logged to HMI; operator alerted.
- `CRITICAL`: Confirmed active cyber or physical breach ($S_{\text{hybrid}} \ge 0.80$, sustained $S_p \ge 1.0$, or discrete policy/wire tamper violation). Triggers Digital Twin Takeover in Prevention mode.

### Feedback Level Sources (`level_source`)
- `sensed`: The deadband controller reads water level directly from field sensor telemetry (`pkt.level_m`).
- `twin`: The deadband controller reads water level from the internal Digital Twin ODE estimate ($\hat{H}$). Activated during active twin takeover in Prevention mode.

### Operational Tolerances
- `handback_tolerance_m`: Maximum allowable residual ($0.050\text{ m}$) between sensor reading and twin estimate required before relinquishing twin takeover and handing authority back to the physical sensor [CODE scada_live/config.yaml:71].
- `max_degraded_s`: Watchdog expiration timeout ($600.0\text{ s}$) governing continuous open-loop twin takeover before forcing plant shutdown [CODE scada_live/config.yaml:72].

---

## 4. Attack Scenario Taxonomy Lexicon

### Batch Dataset Attacks (90 Scenarios in `scada_ids.db`)
- **A1 (False Data Injection / FDI)**: 45 scenarios (`A1_001` – `A1_045`). Sensor telemetry spoofing modifying observed liquid level via:
  - Bias: Small ($+0.05\text{ m}$), Medium ($+0.10\text{ m}$), Large ($+0.20\text{ m}$).
  - Scaling: Constant scaling factor ($\alpha = 1.10$).
  - Intermittent: Periodic bias ($+0.15\text{ m}$) injected on steps where $(t - 300) \equiv 0 \pmod 5$.
- **A2 (Replay Attack)**: 15 scenarios (`A2_001` – `A2_015`). History tampering substituting current telemetry with pre-attack buffer windows ($30\text{--}100\text{ s}$ duration) while preserving historical timestamps (`source_time_s`).
- **A3 (Denial of Service / DoS)**: 15 scenarios (`A3_001` – `A3_015`). Network communication disruption lasting $20\text{--}120\text{ s}$. Packets marked blocked; actuators forced to fail-safe (`pump = 0, valve = 0%`).
- **A4 (Authenticated Misuse)**: 15 scenarios (`A4_001` – `A4_015`). Process safety violations executed using valid operator credentials:
  - Valve open at low level ($60\text{--}100\%$ aperture at $H_0 = 0.4\text{ m}$).
  - Pump force on at high level ($1.0$ at $H_0 = 2.1\text{ m}$).

### Live Simulation Multi-Threat Benchmark (12 Scenarios in `run_full_evaluation.py`)
- **NORM**: Baseline unattacked operation ($600\text{ ticks}$, $H_0 = 1.00\text{ m}$).
- **FDI-1**: Step Bias injection ($+0.20\text{ m}$ at $t = 50\text{ s}$).
- **FDI-2**: Ramp Drift injection ($0.0\text{ to } +0.35\text{ m}$ over 50 ticks starting at $t = 50\text{ s}$).
- **REP**: Replay Attack ($60\text{ s}$ recorded buffer replayed starting at $t = 60\text{ s}$).
- **DOS**: Network Outage ($100\%$ packet drop over wire starting at $t = 50\text{ s}$).
- **AM-1**: Rogue Ingress High-Level Pump Latch (`pump=1, valve=50%`, hold 1200 ticks at $H_0 = 1.30\text{ m}$).
- **AM-2**: Rogue Ingress Excessive Drainage (`pump=0, valve=90%`, hold 1200 ticks at $H_0 = 0.90\text{ m}$).
- **AM-3**: Downstream Fieldbus Wire Tampering (hardware bypass forcing pump motor contactor ON at $t = 5\text{ s}$).
- **AM-4**: In-Deadband Rapid Pump Toggling (alternating pump commands every 5 ticks).
- **AM-5**: In-Band Malicious Filling Hold (`pump=1, valve=50%`, hold 1500 ticks at $H_0 = 1.00\text{ m}$).
- **AM-6**: In-Band Malicious Draining Hold (`pump=0, valve=50%`, hold 1800 ticks at $H_0 = 1.00\text{ m}$).
- **AM-7**: Unauthenticated Long Hold Cap (requested 1500-tick hold capped at 60 ticks by gateway).

---

## 5. Architectural Acronyms & Abbreviations

| Abbreviation | Expanded Term | Architectural Meaning & Context |
| :--- | :--- | :--- |
| **ADR** | Architectural Decision Record | Formal documentation of design choices and technical pivot rationales. |
| **API** | Application Programming Interface | REST HTTP interface exposed by `server.py` on port 5000. |
| **DoS** | Denial of Service | Cyberattack disrupting communications between plant and gateway. |
| **FDI** | False Data Injection | Cyberattack modifying numerical sensor telemetry payloads in transit. |
| **FIFO** | First-In, First-Out | Buffer structure utilized by the LSTM sliding window preprocessor. |
| **FPR** | False Positive Rate | Proportion of clean negative operational ticks incorrectly flagged as anomalous. |
| **HMI** | Human-Machine Interface | Web browser defender console (`static/js/app.js` & `defender.html`). |
| **HMAC** | Hash-based Message Authentication Code | Cryptographic signing mechanism for verifying command payload authenticity. |
| **ICS** | Industrial Control System | Generic term for automated industrial engineering facilities. |
| **IDS** | Intrusion Detection System | The multi-engine cyber-physical anomaly detection pipeline. |
| **LSTM** | Long Short-Term Memory | Recurrent neural network architecture utilized in the autoencoder. |
| **MITM** | Man-in-the-Middle | In-line attacker intercepting communications (`Injector.py`). |
| **MSE** | Mean Squared Error | Mathematical reconstruction loss metric evaluated by the Temporal Engine. |
| **ODE** | Ordinary Differential Equation | Continuous mass conservation differential equation modeling liquid level. |
| **OT** | Operational Technology | Industrial physical plant control domain (distinguished from corporate IT). |
| **PLC** | Programmable Logic Controller | Industrial edge controller executing deadband logic (`GatewayCore`). |
| **REST** | Representational State Transfer | Stateless HTTP communication protocol governing `/api/` endpoints. |
| **ROC-AUC** | Receiver Operating Characteristic Area Under Curve | Discriminative performance metric evaluating true positive vs. false positive tradeoffs. |
| **SCADA** | Supervisory Control and Data Acquisition | Industrial monitoring and supervisory control system. |
| **SLA** | Service Level Agreement | Operational timing bounds governing packet arrival latencies. |
| **SSE** | Server-Sent Events | Unidirectional streaming protocol (`GET /api/events`) broadcasting live telemetry to HMI. |
| **STRIDE** | Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation | Threat modeling methodology mapping industrial cyber threats. |
| **TPR** | True Positive Rate (Recall) | Proportion of true attack ticks or events correctly identified by the IDS. |

---

## 6. Codebase Cross-Reference Matrix

| Concept / Variable | Code Symbol in Codebase | Source File Location |
| :--- | :--- | :--- |
| **Tank Physics** | `class Tank` | `simulator/tank.py:6-60`, `scada_live/plant_sim/plant.py:15-32` |
| **Pump Actuator** | `class Pump` | `simulator/pump.py:6-45` |
| **Valve Actuator** | `class Valve` | `simulator/valve.py:6-45` |
| **Plant Process** | `class ProcessSimulator` / `LivePlant` | `simulator/process_simulator.py:16-163`, `scada_live/plant_sim/plant.py:34-135` |
| **Digital Twin** | `class PhysicsTwin` | `digital_twin/physics_twin.py:10-80` |
| **Physics Engine** | `class PhysicsEngine` | `engines/physics_engine.py:15-85` |
| **Temporal Engine** | `class TemporalEngine` | `engines/temporal_engine.py:16-95` |
| **Policy Engine** | `class PolicyEngine` | `engines/policy_engine.py:16-75` |
| **Availability Engine** | `class AvailabilityEngine` | `engines/availability_engine.py:15-85` |
| **Fusion Engine** | `class FusionEngine` | `engines/fusion_engine.py:16-120` |
| **LSTM Autoencoder** | `class LSTMAutoencoder` | `models/lstm_autoencoder.py:5-48` |
| **Live Gateway** | `class GatewayCore` | `scada_live/scada_ids/gateway_core.py:46-502` |
| **Streaming IDS** | `class StreamingIDS` | `scada_live/scada_ids/streaming_ids.py:20-195` |
| **Live Attacker** | `class Injector` | `scada_live/attacker_wire/injector.py:5-131` |
| **SSE Event Hub** | `class EventHub` | `scada_live/scada_ids/sse_hub.py:6-35` |
| **REST Server** | `app = Flask(...)` | `scada_live/scada_ids/server.py:17-310` |
| **Demo Orchestrator** | `def main()` | `run_demo.py:340-420` |

---

## 7. Verification

All terms, physical units, mathematical symbols, thresholds, and scenario classifications defined in this glossary have been cross-checked and verified against:
1. Physical equations in `digital_twin/physics_twin.py` and `simulator/tank.py`.
2. Detection thresholds and scoring logic in `engines/` and `scada_live/config.yaml`.
3. Scenario definitions in `config/scenarios.py` and `experiments/run_full_evaluation.py`.
4. Operational boundaries and safety interlocks in `scada_live/scada_ids/gateway_core.py`.
