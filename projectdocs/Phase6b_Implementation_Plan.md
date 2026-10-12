# Phase 6b Implementation Plan: Authorization Misuse Prevention & Command Filtering

> **Status:** Draft / Pending User Approval — STOPPED for Review.  
> **Scope:** Architecture and design specification for Phase 6b (Command filtering, authorization misuse mitigation, channel vs tamper variants). **NO implementation code is written in this step.**

---

## 1. Overview & Objectives

In Phase 6a, we implemented and validated physical protection against sensor-spoofing attacks (FDI ramps and stealthy bias) using Digital Twin takeover.
In Phase 6b, we extend `GatewayCore` to handle **actuator-level command attacks (Authorization Misuse / Rogue Commands)**:
1. Expose a secure, validated `POST /api/command` endpoint.
2. Distinguish and mitigate two distinct authorization misuse variants:
   - **"Channel" Variant:** A rogue command arrives at the Gateway interface. In Prevention mode, the Gateway evaluates it against Policy Engine v2 and **blocks** it before forwarding to the plant.
   - **"Tamper" (Man-in-the-Middle) Variant:** A command is modified on the network bus between Gateway and Plant. The Gateway cannot block it in advance, but detects the divergence upon observing physical telemetry feedback and intervenes.
3. Eliminate dataset start-up artifacts by initiating attacks strictly from **nominal water levels** ($H \in [0.8, 1.2\text{ m}]$) rather than the non-physical 0.4 m or 2.1 m initial conditions present in the offline training dataset.
4. Provide a 10-seed paired A/B validation harness demonstrating 0 physical overflows or dry-runs in Prevention mode.

---

## 2. API Design & Packet Specification

### 2.1 `POST /api/command`
- **Path:** `/api/command`
- **Method:** `POST`
- **Request Headers:**
  - `Content-Type: application/json`
  - `X-Actor-Role: operator | attacker | supervisor` (for demo role attribution)
  - `X-Auth-Token: <token>` (optional demo bearer token)
- **JSON Request Payload:**
  ```json
  {
    "run_id": "test_run_001",
    "pump_cmd": 1,
    "valve_cmd": 50.0,
    "hold_ticks": 10,
    "source": "operator_console",
    "timestamp": 1712894000.123
  }
  ```

### 2.2 Schema & Validation Rules
We reuse and extend `CommandPacket` from `scada_live.common.packets`:
- `pump_cmd`: Integer $\in \{0, 1\}$. Rejects values $\notin \{0, 1\}$ with HTTP 400.
- `valve_cmd`: Float $\in [0.0, 100.0]$. Rejects values outside range with HTTP 400.
- `hold_ticks`: Integer $\ge 1$ (default 5, max 300). Defines how many control ticks this external override suppresses the automatic hysteresis controller.
- `source`: String identifier (`"operator"`, `"attacker_01"`, `"automated_script"`).

### 2.3 Who May Send & Operator Override Assumption
- **Demo Assumption:** In this single-tank SCADA testbed, the autonomous hysteresis controller is designed to manage the process without routine manual overrides. Therefore, **any manual override outside the controller's autonomous output specification is treated as an unauthorized misuse condition** unless tagged with an authenticated supervisor maintenance override token.
- **Attacker Feedback:**
  - In **Monitor Mode:** The rogue command is accepted, logged, and forwarded to the plant. Response:
    ```json
    {"status": "accepted", "executed": true, "mode": "monitor", "warning": "Policy violation logged"}
    ```
  - In **Prevention Mode (Channel Variant):** The rogue command violates Policy v2 and is blocked before dispatch. Response:
    ```json
    {"status": "blocked", "executed": false, "mode": "prevention", "reason": "Policy violation: valve position 90.0% forbidden with active pumping"}
    ```
  - In **Prevention Mode (Tamper Variant):** Forwarded command was valid at gateway, but feedback indicates plant executed altered state. Gateway activates mitigation:
    ```json
    {"status": "mitigated", "action": "twin_takeover", "mode": "prevention"}
    ```

---

## 3. Threat Variants: Channel vs Tamper Misuse

### 3.1 Variant 1: "Channel" Misuse (Rogue Command at Gateway)
- **Attack Vector:** Attacker sends malicious `POST /api/command` directly to the Gateway (e.g. forcing pump ON at 1.3 m, or forcing valve to 90% at 0.9 m).
- **Enforcement Point:** Ingress filter at `GatewayCore.process_external_command()`.
- **Prevention Capability:** **Active Drop / Block.**
  - `GatewayCore` intercepts the packet *before* calling `plant.advance()`.
  - In Monitor mode: logs violation, increments metrics, forwards to plant.
  - In Prevention mode: rejects packet, drops command, retains autonomous controller command, returns HTTP 403 `{"status": "blocked"}`.

### 3.2 Variant 2: "Tamper" Misuse (Man-in-the-Middle on Actuator Bus)
- **Attack Vector:** Gateway issues normal command (e.g. pump=0, valve=50%), but an attacker on the fieldbus modifies the packet in transit so the Plant receives pump=1.
- **Enforcement Point:** Egress telemetry feedback loop.
- **Prevention Capability:** **Detection & Override Re-Command (Detect Only at Ingress).**
  - Gateway cannot block the packet before arrival because the tampering occurs downstream of the Gateway interface.
  - Upon receiving the subsequent `TelemetryPacket` from the Plant (`plant.observe()` / `plant.advance()`), `GatewayCore` detects that the reported actuator state (`pump_on=True`) disagrees with the Gateway's issued command and violates Policy v2.
  - Gateway triggers CRITICAL alert, forces immediate emergency override re-commands (or engages twin takeover), preventing prolonged plant harm.

---

## 4. Control Logic & Policy v2 Evaluation

### 4.1 Forwarded External Command Override Mechanism (`hold_ticks`)
When an external command is accepted (or permitted in Monitor mode):
1. `GatewayCore` sets an internal counter `external_override_hold_ticks = hold_ticks`.
2. While `external_override_hold_ticks > 0`:
   - The autonomous hysteresis controller (`Controller.step()`) is bypassed.
   - The actuator outputs are forced to `(pump_cmd_ext, valve_cmd_ext)`.
   - `external_override_hold_ticks` decrements by 1 each plant tick.
3. The outgoing `CommandPacket` carries:
   - `pump_cmd`: external value.
   - `valve_cmd`: external value.
   - `is_external_override`: `True`.
   - `override_source`: source string.

### 4.2 Policy v2 Evaluation Against the Best Level Estimate
Policy Engine v2 determines whether an actuator command configuration is physically safe.
- **Dynamic Level Source Selection:**
  $$\hat{h} = \begin{cases} h_{twin} & \text{if } \text{twin\_takeover\_active is True} \\ h_{obs} & \text{otherwise} \end{cases}$$
- **Policy v2 Rules:**
  1. **Valve Position Invariant:** The valve must be in its nominal operating position ($50.0\% \pm 1\%$) OR legitimately in fail-safe ($0.0\%$ with pump commanded OFF). Any command with $\text{valve} \notin \{0.0\%, 50.0\%\}$ is forbidden.
  2. **High Level Protection ($h \ge 1.20\text{ m}$):** Pump MUST be OFF ($0$). A command with $\text{pump}=1$ when $\hat{h} \ge 1.20\text{ m}$ is a direct violation.
  3. **Low Level Protection ($h \le 0.80\text{ m}$):** Pump MUST be ON ($1$) and valve must NOT exceed $50\%$. A command with $\text{pump}=0$ or $\text{valve} > 50\%$ when $\hat{h} \le 0.80\text{ m}$ is a direct violation.

### 4.3 Policy Engine Blind Spots (Documented Invariant)
- **In-Deadband Pump Toggles:**
  When water level is inside the deadband ($0.80\text{ m} < \hat{h} < 1.20\text{ m}$) and the valve remains at nominal $50\%$, both $\text{pump}=1$ and $\text{pump}=0$ are physically valid controller states depending on prior hysteresis history.
  A rogue command that toggles the pump ON/OFF inside the deadband without touching the valve cannot be flagged by Policy Engine v2 alone.
  *Detection mechanism:* This blind spot is caught by the **Temporal Engine (LSTM autoencoder)**, which flags high-frequency actuator switching patterns unseen during normal smooth cycles.

---

## 5. Attack Scenarios Starting from Nominal Levels

Unlike the offline dataset which contains unnatural $H_0 = 0.4\text{ m}$ or $2.1\text{ m}$ starts, Phase 6b evaluates attacks starting from steady-state nominal cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$):

1. **Attack Scenario AM-1: Overflow Misuse (Pump Latched ON at High Level):**
   - Condition: Tank rises to $H = 1.25\text{ m}$ (above upper setpoint).
   - Rogue Command: Attacker forces `pump_cmd = 1`, `valve_cmd = 50.0%`, `hold_ticks = 1200`.
   - Monitor mode result: Pump stays ON, water rises at $+1.16\text{ mm/s}$, tank overflows ($H \ge 2.50\text{ m}$) in ~1080 s.
   - Prevention mode result: Gateway blocks command immediately; controller switches pump OFF; 0 overflow ticks.
2. **Attack Scenario AM-2: Dry-Run Misuse (Excessive Drainage at Low Level):**
   - Condition: Tank drops to $H = 0.90\text{ m}$ (approaching lower setpoint).
   - Rogue Command: Attacker forces `pump_cmd = 0`, `valve_cmd = 90.0%`, `hold_ticks = 1200`.
   - Monitor mode result: Pump stays OFF, valve drains tank at high discharge rate, tank hits dry-run ($H \le 0.05\text{ m}$) in ~650 s.
   - Prevention mode result: Gateway blocks command immediately; controller maintains valve at 50% and turns pump ON; 0 dry-run ticks.
3. **Attack Scenario AM-3: Tamper Misuse (Bus-Level Actuator Forcing):**
   - Condition: Downstream tamper forces `pump = 1` continuously while Gateway commanded 0.
   - Monitor mode result: Unchecked accumulation to overflow.
   - Prevention mode result: Telemetry mismatch triggers CRITICAL alert in $\le 3$ ticks; Gateway intervenes with active mitigation.

---

## 6. A/B Experimental Design & Evaluation Metrics

### 6.1 Experimental Setup
- **Sample Size:** 10 random seeds (101 to 110).
- **Attack Timing:** Randomized attack start ($t_{start} \in [200, 600]\text{ s}$) and duration ($[1000, 1400]\text{ s}$), paired identically across Monitor and Prevention modes.
- **Duration:** $T = 2400\text{ s}$ (40 minutes) per run.

### 6.2 Key Metrics
1. **Physical Safety Metrics:**
   - `overflow_ticks`: Ticks with $H_{true} \ge 2.50\text{ m}$ (Target: 0 in Prevention).
   - `dry_run_ticks`: Ticks with $H_{true} \le 0.05\text{ m}$ (Target: 0 in Prevention).
   - `time_below_0.3m`: Ticks with $H_{true} < 0.30\text{ m}$.
2. **Command Enforcement Metrics:**
   - `rogue_commands_blocked`: Total unauthorized command packets dropped.
   - `legitimate_commands_blocked`: Legitimate operator actions dropped (Target: 0).
   - `false_blocks_normal_soak`: Unauthorized command blocks on a 30-minute unattacked normal run (Target: 0).

---

## 7. Test List & Pass Conditions

| Test ID | Test Name | File | Pass Condition |
| :--- | :--- | :--- | :--- |
| **T-6B-01** | `test_post_command_endpoint_validation` | `scada_live/tests/test_api_command.py` | Valid payloads return HTTP 200/202; out-of-range pump/valve values return HTTP 400. |
| **T-6B-02** | `test_channel_rogue_command_blocked` | `scada_live/tests/test_phase6b_auth.py` | In Prevention mode, rogue command violating Policy v2 is dropped; plant actuators unchanged. |
| **T-6B-03** | `test_channel_rogue_command_monitor_forwards`| `scada_live/tests/test_phase6b_auth.py` | In Monitor mode, rogue command is logged but executed by plant; plant level deviates. |
| **T-6B-04** | `test_tamper_variant_detected_by_feedback` | `scada_live/tests/test_phase6b_auth.py` | Bus-level mismatch between gateway command and plant state flags CRITICAL in $\le 3$ ticks. |
| **T-6B-05** | `test_policy_evaluation_against_best_estimate`| `scada_live/tests/test_phase6b_auth.py` | When takeover active, policy evaluates against $h_{twin}$; when inactive, against $h_{obs}$. |
| **T-6B-06** | `test_normal_run_zero_false_blocks` | `scada_live/tests/test_phase6b_auth.py` | 30-minute unattacked normal run triggers 0 blocked commands and 0 false alarms. |
| **T-6B-07** | `test_ab_auth_misuse_prevention` | `experiments/run_auth_misuse_ab.py` | 10 seeds: Monitor has $>500$ overflow / dry-run ticks; Prevention has 0 overflow and 0 dry-run ticks. |
| **T-6B-08** | `test_regression_existing_suites` | `tests/`, `scada_live/tests/` | All 66 batch tests and 62 existing live tests continue to pass (100% regression pass). |

---

## 8. Build Order & Step Checkpoints

- **Step 1: Ingress API & Command Validation**
  - Implement `/api/command` route handler in `scada_live`.
  - Validate payloads against `CommandPacket` schema.
  - *Checkpoint:* Run `T-6B-01` (`pytest scada_live/tests/test_api_command.py`).
- **Step 2: GatewayCore Command Pipeline & Policy Filtering**
  - Implement `GatewayCore.process_external_command()`.
  - Add `hold_ticks` override scheduler in `GatewayCore`.
  - Implement dynamic best-level estimate lookup ($h_{twin}$ during takeover, $h_{obs}$ otherwise) in Policy Engine v2 evaluation.
  - Implement Channel blocking logic (Prevention: drop; Monitor: forward) and Tamper feedback detection.
  - *Checkpoint:* Run `T-6B-02` through `T-6B-06`.
- **Step 3: A/B Verification Harness & Documentation**
  - Build `experiments/run_auth_misuse_ab.py` with 10 seeds and nominal starting conditions.
  - Run 10-seed A/B verification across AM-1, AM-2, AM-3.
  - Update `PROJECT_REVIEW_CHEAT_SHEET.md`.
  - *Checkpoint:* Run full regression test suites (both batch and live).

---

## 9. Out of Scope for Phase 6b

- **Replay Shadow Estimator:** Model-based shadow simulation for replay spoofing (Phase 6c).
- **DoS Adaptive Token Bucket:** Transport-layer rate limiting and sync mechanisms (Phase 6c).
- **Web UI Dashboard Modals:** Visual frontend buttons, operator approval dialogs, or CSS animations.

---

## 10. Risks & Open Questions

### 10.1 Technical Risks
1. **Concurrency Jitter:** If external commands arrive asynchronously via HTTP while `LivePlant` advances in a background simulation loop, state race conditions could occur.  
   *Mitigation:* Use thread-safe locking (`threading.Lock`) across `GatewayCore.process_external_command()` and `GatewayCore.step()`.
2. **Actuator Inertia Delay:** Physical pump has a 2-tick response delay (`response_delay_s = 2.0 s`). Immediate command verification must account for mechanical delay steps before flagging tamper.  
   *Mitigation:* Gate tamper verification using the actuator state tracking buffer (`_steps_since_command >= delay_steps`).

### 10.2 Open Questions for User
1. **Authentication Token Format:** Should the `/api/command` endpoint enforce a mock JWT / bearer token string, or is an explicit JSON role attribute (`"source": "operator"`) sufficient for the evaluation harness?
2. **Tamper Inversion Hook:** For simulating the Tamper variant, should we insert an in-process fault injector hook directly in `LivePlant.advance()`, or pass a network tamper middleware flag in `GatewayCore`?
