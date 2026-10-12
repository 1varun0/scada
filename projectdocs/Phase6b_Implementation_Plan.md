# Phase 6b Implementation Plan: Authorization Misuse Detection, Command Filtering & Actuator Consistency

> **Status:** Draft / Pending User Approval — STOPPED FOR REVIEW.  
> **Scope:** Architecture and design specification for Phase 6b (Command filtering, authorization misuse mitigation, channel vs tamper variants, continuous enforcement, actuator-feedback consistency). **NO Phase 6b implementation code is written in this step.**

---

## 1. Overview & Objectives

In Phase 6a, we verified physical protection against sensor-spoofing attacks (FDI ramps, DoS gaps, stealthy drift) via Digital Twin takeover.
In Phase 6b, we address **actuator-level command attacks (Authorization Misuse / Rogue Commands)**:

1. **Ingress Filtering vs Bus Tampering vs Continuous Hold Enforcement:**
   - **"Channel" Ingress Misuse (AM-1, AM-2):** Malicious commands arrive at the Gateway ingress API (`POST /api/command`). The Gateway evaluates them against process safety constraints via a dedicated gateway-side function (`evaluate_command_with_live_setpoint`) and **blocks** them before plant dispatch in Prevention mode.
     - **AM-1 (High-Level Pump Latch):** Starts at $H = 1.30\text{ m}$ (above the $1.25\text{ m}$ boundary $[1.0 + 0.20 + 0.05]$) with `pump_cmd = 1, valve_cmd = 50%`. The plant reaches $1.30\text{ m}$ either via scenario initial condition configuration ($H_0 = 1.30\text{ m}$) or an unmitigated transient filling step above $1.20\text{ m}$. Ingress filter blocks it immediately ($1.30\text{ m} > 1.25\text{ m}$).
     - **AM-2 (Low-Level Drainage):** Starts at $H \approx 0.90\text{ m}$ with `pump_cmd = 0, valve_cmd = 90%`. Ingress filter blocks it immediately (valve $90\% \ne 50\%$ and $\ne 0\%$).
   - **"Wire / Fieldbus Tamper" (AM-3):** Commands are altered downstream on the physical wire/fieldbus (injector reply override). The Gateway **cannot prevent or mitigate a bus-level override** because downstream plant hardware executes the wire signal directly; AM-3 is strictly **DETECT-ONLY**. Success is defined by detection delay ($\le 3\text{ ticks}$) and attribution, with identical physical harm across both Monitor and Prevention modes    - **"In-Deadband Toggle" (AM-4):** An attacker toggles the pump within the operational deadband ($0.8\text{ m} \le H \le 1.2\text{ m}$, e.g. at $1.0\text{ m}$). This represents a documented blind spot for policy and physics engines. Evaluated empirically without unverified claims.
    - **"In-Band Malicious Hold - Filling" (AM-5):** Attacker issues a superficially valid command at nominal level ($H \approx 1.0\text{ m}$, `pump_cmd = 1`, `hold_ticks = 1500`). The authenticated A/B attacker uses the cryptographic shared secret (A4 threat model: rogue authenticated insider), bypassing the 60-tick hold cap; therefore, **Continuous Enforcement is the vital defense**. Ingress filtering allows it initially because $H = 1.0\text{ m}$ is within the valid envelope. At $1.0\text{ m}$, net fill rate is $\frac{0.005 - 0.002\sqrt{1.0}}{2.0} = 0.0015\text{ m/s} = 1.5\text{ mm/s}$. Analytical time to reach the upper boundary $1.25\text{ m}$ ($setpoint + deadband + \epsilon$) is $t \approx 174\text{ s}$ ($\int_{1.0}^{1.25} \frac{dh}{0.0025 - 0.001\sqrt{h}} \approx 173.8\text{ s}$). Time to tank crest ($2.50\text{ m}$) is $\approx 1288\text{ s}$. In Monitor mode, overflow occurs at $t \approx 1288\text{ s}$ producing $\approx 210$ overflow ticks. In Prevention mode, Continuous Enforcement re-evaluates the hold on every simulation tick against the live level estimate $h_{est}$ and drops the hold when level crosses $H > 1.25\text{ m}$ ($t \approx 174\text{ s}$), de-energizing the pump and preventing tank overflow (0 overflow ticks).
    - **"In-Band Malicious Hold - Draining" (AM-6):** Authenticated attacker (A4 threat model using secret) issues `pump_cmd = 0, valve_cmd = 50%, hold_ticks = 1800` at nominal level ($H \approx 1.0\text{ m}$). Ingress filtering allows it initially because $H = 1.0\text{ m} \ge 0.75\text{ m}$. Initial drain rate at $1.0\text{ m}$ is $-0.001\sqrt{1.0} = -1.0\text{ mm/s}$. Analytical gravity drain time to reach the lower boundary $0.75\text{ m}$ is $t = 2000(1.0 - \sqrt{0.75}) \approx 268\text{ s}$ ($267.95\text{ s}$). Drain time to dry-run ($0.05\text{ m}$) is $t = 2000(1.0 - \sqrt{0.05}) \approx 1553\text{ s}$. In Monitor mode, dry-run begins at $t \approx 1553\text{ s}$, producing $\approx 247$ dry-run ticks. In Prevention mode, Continuous Enforcement drops the hold when $h_{est} < 0.75\text{ m}$ ($t \approx 268\text{ s}$), reverting to autonomous controller which energizes pump, preventing dry-run (0 dry-run ticks).
    - **"Unauthenticated Hold Cap" (AM-7):** Unauthenticated caller attempts a long hold (`pump_cmd = 1, hold_ticks = 1500`) without the shared secret. Ingress validation caps hold duration at $\min(1500, 60) = 60\text{ ticks}$. The hold expires after $60\text{ s}$ (well before reaching $1.25\text{ m}$ at $174\text{ s}$ or overflow at $1288\text{ s}$), safely resuming autonomous control with 0 overflows.
2. **Monitor vs Prevention Event Invariance:**
   - In Monitor mode, GatewayCore evaluates the exact same safety rules at the exact same ticks.
   - When an ingress command violates the safety envelope, GatewayCore raises a `would_block` event to `EventHub` with the exact violation reason, records it in metrics (`commands_would_block_total`), logs it, and passes the command to the plant without blocking.
   - When continuous enforcement detects a hold violation, GatewayCore raises a `would_drop` event to `EventHub`, records it in metrics (`holds_would_drop_total`), logs it, and allows the hold to persist without dropping.
   - In Prevention mode, GatewayCore raises `command_blocked` / `hold_dropped` events, increments blocked/dropped counters, and enforces the block/drop.
   - Pass criterion: Test verifies that `would_block` and `would_drop` events are dispatched at the exact same ticks in Monitor mode as `command_blocked` and `hold_dropped` events in Prevention mode.
3. **Rigorous Physical Pass Conditions:**
   - AM-1: Starts at $1.30\text{ m}$. Hold duration $1200\text{ s}$. Analytical fill time to overflow ($2.50\text{ m}$) is $\approx 1078\text{ s}$. Monitor mode: $\ge 1$ overflow event in $\ge 9/10$ seeds ($\approx 120$ overflow ticks). Prevention mode: exactly 0 overflow ticks.
   - AM-2: Starts at $0.90\text{ m}$, valve $90\%$. Hold duration $1200\text{ s}$. Analytical drain time to dry-run ($0.05\text{ m}$) is $\approx 806\text{ s}$. Monitor mode: $\ge 1$ dry-run event in $\ge 9/10$ seeds ($\approx 390$ dry-run ticks). Prevention mode: exactly 0 dry-run ticks.
   - AM-3: Wire tamper forcing pump ON. Monitor and Prevention modes suffer identical overflow harm. Mismatch detected in $\le 3\text{ ticks}$.
   - AM-4: In-deadband toggles at $1.0\text{ m}$. Empirically record engine scores; documented blind spot.
   - AM-5: Fills at $1.5\text{ mm/s}$ at $1.0\text{ m}$, crosses $1.25\text{ m}$ at $\approx 174\text{ s}$. Pump ON held for $1500\text{ s}$. Fill time to $2.50\text{ m}$ is $\approx 1288\text{ s}$. Monitor mode: $\ge 1$ overflow event in $\ge 9/10$ seeds ($\approx 210$ overflow ticks). Prevention mode: exactly 0 overflow ticks.
   - AM-6: Crosses $0.75\text{ m}$ at $\approx 268\text{ s}$. Pump OFF held for $1800\text{ s}$. Drain time to $0.05\text{ m}$ is $\approx 1553\text{ s}$. Monitor mode: $\ge 1$ dry-run event in $\ge 9/10$ seeds ($\approx 247$ dry-run ticks). Prevention mode: exactly 0 dry-run ticks.
   - AM-7: Unauthenticated caller capped at 60 ticks. Hold expires at $60\text{ s}$ without reaching $1.25\text{ m}$; exactly 0 overflow ticks.
4. **Recorded Architectural Decisions:**
   - **Flask Framework & Existing Hub:** Server implementation uses existing Flask framework in `scada_ids/server.py` and `EventHub`/`MetricsCollector`. No FastAPI/Starlette or external Prometheus client.
   - **Shared Secret from Config & Fail-Closed Authentication:** Shared secret is loaded from `cfg.api.shared_secret`. If the secret is missing, empty, or unconfigured, the system **fails closed** (caps all callers at 60 ticks). Secret verification uses constant-time `hmac.compare_digest` against `Authorization: Bearer <secret>` or `X-API-Key: <secret>`.
   - **Role Header Must NOT Be Used in Validation:** Client-supplied `X-Actor-Role` is unverified metadata for telemetry logging only. Validation logic must never use `role` to grant privileges or bypass safety checks.
   - **Explicit Exceptions Instead of Assert:** Gateway validation and controller attribute checks raise explicit `AttributeError` or `ValueError` rather than `assert`, preventing silent failure when running with Python optimizations (`-O`).
   - **Gateway Has No Direct Plant Reference:** GatewayCore communicates with the plant over network messages and has no direct Python object reference to `plant` or `plant.pump`. Controller state resynchronization on hold drop/expiration uses the plant's echoed actuator state from the latest telemetry packet (`latest_telemetry.pump_on`).
   - **HTTP Route Error Handling:** Invalid JSON, missing required fields (`pump_cmd`, `valve_cmd`), invalid types, or out-of-envelope parameters return HTTP 400 Bad Request, NOT HTTP 500.
   - **Tamper Hook Location:** The bus-level tamper hook lives strictly in the injector/wire layer (`attacker_wire/injector.py`), never inside `LivePlant` core or `GatewayCore`.

---

## 2. Threat Scenarios & Physical Mechanics

### 2.1 Attack Scenarios Summary

| Threat ID | Threat Class | Ingress Point | Primary Detection Engine | Mitigable by Gateway? | Pass Condition (10 Seeds) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AM-1** | Channel Ingress Misuse | `POST /api/command` | Gateway Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ overflow event in $\ge 9/10$ seeds (~120 ov ticks); Prevention: 0 ov ticks. |
| **AM-2** | Channel Ingress Misuse | `POST /api/command` | Gateway Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ dry-run event in $\ge 9/10$ seeds (~390 dry ticks); Prevention: 0 dry ticks. |
| **AM-3** | Wire / Fieldbus Tamper | Downstream Wire Reply Override | 4-Way Actuator Consistency | **No** (Detect-Only) | Detection delay $\le 3$ ticks, correct attribution; physical harm identical in Monitor and Prevention. |
| **AM-4** | In-Deadband Toggle | `POST /api/command` | Empirical Engine Test | No (Within Deadband) | Policy & Physics Twin do NOT fire; record empirical engine behavior without unverified claims. |
| **AM-5** | In-Band Hold (Filling, Authenticated) | `POST /api/command` | Continuous Enforcement Filter | **Yes** (Hold Drop) | Monitor: $\ge 1$ overflow event in $\ge 9/10$ seeds (~210 ov ticks with hold 1500s); Prevention: 0 ov ticks. |
| **AM-6** | In-Band Hold (Draining, Authenticated) | `POST /api/command` | Continuous Enforcement Filter | **Yes** (Hold Drop) | Monitor: $\ge 1$ dry-run event in $\ge 9/10$ seeds (~247 dry ticks with hold 1800s); Prevention: 0 dry ticks. |
| **AM-7** | In-Band Hold (Unauthenticated Cap) | `POST /api/command` | Ingress Payload Validator | **Yes** (Hold Cap) | Capped at 60 ticks; hold expires at $t=60\text{ s}$ before reaching $1.25\text{ m}$; 0 ov ticks. |

---

### 2.2 Detailed Threat Mechanics

#### AM-1: Overflow Misuse (Pump Latched ON at High Level)
- **Reaching Initiation Level ($H = 1.30\text{ m}$):** The scenario reaches $H = 1.30\text{ m}$ either via configuring the scenario initial condition ($H_0 = 1.30\text{ m}$) or by allowing a preceding unmitigated filling transient to carry the tank level from nominal cycling to $1.30\text{ m}$. At $1.30\text{ m}$, the level is unambiguously above the upper boundary $setpoint + deadband + \epsilon = 1.0 + 0.20 + 0.05 = 1.25\text{ m}$.
- **Command Payload:** Rogue command forces `pump_cmd = 1, valve_cmd = 50.0%`, with `hold_ticks = 1200`.
- **Physical Dynamics & Analytical Timing:**
  - Net fill rate: $\frac{dh}{dt} = \frac{Q_{in} - Q_{out}}{A} = \frac{0.005 - 0.002\sqrt{h}}{2.0} = 0.0025 - 0.001\sqrt{h}$.
  - Analytical fill time from $h = 1.30\text{ m}$ to tank crest overflow ($h = 2.50\text{ m}$):
    $$t_{fill} = \int_{1.30}^{2.50} \frac{dh}{0.0025 - 0.001\sqrt{h}} \approx 1077.95\text{ s} \approx 1078\text{ s}$$
  - For an attack hold duration of $1200\text{ s}$, the tank hits overflow at $t \approx 1078\text{ s}$ and remains overflowing for the remaining $1200 - 1078 = 122 \approx 120\text{ ticks}$.
- **Monitor Mode:** Command is dispatched to the plant. Tank overflows for $\approx 120$ ticks, hitting $2.50\text{ m}$. Gateway dispatches `would_block` event to `EventHub`.
- **Prevention Mode:** Gateway command filter blocks the rogue command at ingress ($1.30\text{ m} > 1.25\text{ m}$). Autonomous controller commands pump OFF ($0$). Tank remains within $[0.8, 1.2\text{ m}]$ with exactly 0 overflow ticks.

#### AM-2: Dry-Run Misuse (Excessive Drainage at Low Level)
- **Initiation Point:** Initiated when the tank level drops toward the lower boundary ($H \approx 0.90\text{ m}$).
- **Command Payload:** Rogue command forces `pump_cmd = 0, valve_cmd = 90.0%` (extreme opening), with `hold_ticks = 1200`.
- **Physical Dynamics & Analytical Timing:**
  - Inflow $Q_{in} = 0$. At valve position $90\%$, outflow coefficient is $C_v \times \frac{90}{100} = 0.004 \times 0.90 = 0.0036\text{ m}^3\text{/s}$.
  - Analytical gravity drainage: $\frac{dh}{dt} = -\frac{0.0036\sqrt{h}}{2.0} = -0.0018\sqrt{h}$.
  - Analytical drain time from $h = 0.90\text{ m}$ to pump cavitation / suction dry-run ($h = 0.05\text{ m}$):
    $$t_{drain} = \frac{2}{0.0018} \left( \sqrt{0.90} - \sqrt{0.05} \right) = \frac{20000}{18} (0.94868 - 0.22361) \approx 805.6\text{ s} \approx 806\text{ s}$$
  - For an attack hold duration of $1200\text{ s}$, the tank hits dry-run at $t \approx 806\text{ s}$ and remains in dry-run for the remaining $1200 - 806 = 394 \approx 390\text{ ticks}$.
- **Monitor Mode:** Command is dispatched to the plant. Tank drains to $0.05\text{ m}$ in $\approx 806\text{ s}$, remaining in dry-run for $\approx 390$ ticks. Gateway dispatches `would_block` event to `EventHub`.
- **Prevention Mode:** Command filter blocks the rogue command at ingress (valve $90\% \ne 50\%$ and $\ne 0\%$). Autonomous controller maintains default valve position ($50\%$) and energizes pump ($1$). Tank level stays $\ge 0.78\text{ m}$ with exactly 0 dry-run ticks.

#### AM-3: Tamper Misuse (Bus-Level Actuator Override — Detect-Only)
- **Packet `cmd` Semantics:** Telemetry packet fields `pkt.pump_cmd` and `pkt.valve_cmd` represent what the plant actuators physically received and set (what the plant echoes back in telemetry).
- **Tamper Location:** The tamper acts downstream of the Gateway on the wire (injector reply override middleware intercepting the plant's sense reply). The Gateway issues `pump_cmd = 0, valve_cmd = 50%`, but the wire tamper forces the reply to `pump_cmd = 1`. The plant receives $1$, executes it, and echoes `pkt.pump_cmd = 1, pkt.pump_on = True`.
- **Mitigation Limitation:** **The Gateway cannot mitigate a bus-level override.** Because the override occurs downstream of the gateway's network boundary, software commands cannot override the forced wire state. AM-3 is strictly **detect-only**.
- **Pump Class Delay Semantics & Historical Command Indexing:**
  - In `simulator/pump.py`, response delay is governed by `self._delay_steps = max(1, math.ceil(response_delay_s / dt)) = 2`.
  - When `set_command(cmd)` is invoked with a changed command, `self._command` updates and `self._steps_since_command` is reset to 0.
  - In `step()`, `self._steps_since_command` is incremented by 1, and only transitions `self._state = self._command` when `self._steps_since_command >= self._delay_steps`.
  - Consequently, when transitioning from ON to OFF, the physical pump remains ON (`state = 1`) during the first step after `command = 0` is received.
  - **Indexing Definition:** The Gateway maintains `gateway_issued_pump_history`:
    - `history[-1]` is the pump command issued at the current timestep $t$.
    - `history[-2]` is the pump command issued at timestep $t-1$.
  - Therefore, `gateway_pump_off_for_delay = (len(history) >= 2 and history[-1] == 0 and history[-2] == 0)`.
  - The tamper detection rule is:
    ```python
    is_wire_tampered = (
        len(gateway_issued_pump_history) >= 2
        and gateway_issued_pump_history[-1] == 0
        and gateway_issued_pump_history[-2] == 0
        and (
            telemetry.pump_command == 1
            or telemetry.pump_on == True
            or telemetry.q_in > 0.001
        )
    )
    ```
- **Return Telemetry Integrity Assumption:**
  This rule explicitly assumes that the return telemetry path from the plant to the gateway (sensor level, flow meters, actuator echo) is **NOT** tampered. The adversary tampers solely with the forward control wire from gateway to plant actuators. If the return path were also spoofed, the attack becomes a multi-point attack (addressed by the physics twin tracking unmodelled water level rise).
- **Tests & Verification:**
  1. **Legitimate Turn-off Transition Test:** Explicitly test legitimate pump turn-off transitions from autonomous cycling. During the 2-step transition window where the pump remains mechanically ON while shutting down, verify zero alerts are triggered.
  2. **30-Minute False-Alarm Soak Test:** Run a 30-minute (1800-tick) normal cycling soak test with no attacks: count the total number of legitimate pump turn-off transitions (typically 15–20 transitions across cycling) and verify that false wire-tamper alerts are exactly **0 alerts**.
  3. **Detection Delay Measurement:** Under AM-3 injection, measure the delay from wire tamper inception to alert: exactly $D_{delay} = 2\text{ ticks}$ (matching the plant actuator activation delay).
  4. **Identical Physical Harm:** Physical harm (overflow ticks) is **identical** in both Monitor and Prevention modes because downstream wire overrides bypass gateway command routing.

#### AM-4: In-Deadband Pump Toggle at Nominal Level
- **Attack Nature:** Attacker issues valid valve command ($50\%$) but rapidly toggles `pump_cmd` ($0 \leftrightarrow 1$) while the water level is nominal ($H \approx 1.0\text{ m}$, inside the $[0.8, 1.2\text{ m}]$ deadband).
- **Engine Behavior & Blind Spot:**
  - **Policy Filter / Policy v2:** Does **NOT** fire. Inside $[0.75, 1.25\text{ m}]$, both pump ON and pump OFF are legitimate controller states depending on hysteresis history.
  - **Physics Twin:** Does **NOT** fire. Telemetry faithfully echoes the toggled pump state; the twin integrates identical inflow.
  - **Temporal Engine (LSTM):** Evaluated empirically. We make no unverified claims of detection; the evaluation harness records the empirical maximum LSTM anomaly score.

#### AM-5: In-Band Malicious Hold - Filling ($H=1.0\text{ m}$, Pump ON, Hold 1500s)
- **Threat Model:** The attacker is an authenticated insider possessing the valid API shared secret (A4 threat model). Because the attacker possesses valid credentials, the 60-tick hold cap does not prevent the attack. Therefore, **Continuous Enforcement is the primary defense**.
- **Attack Nature:** Attacker issues authenticated command `pump_cmd = 1, valve_cmd = 50.0%, hold_ticks = 1500` while tank level is nominal ($H \approx 1.0\text{ m}$).
- **Analytical Timing from 1.0m to 1.25m and 2.5m:**
  - Net fill rate: $\frac{dh}{dt} = \frac{0.005 - 0.002\sqrt{h}}{2.0} = 0.0025 - 0.001\sqrt{h}$.
  - At $h = 1.0\text{ m}$: $\frac{dh}{dt} = 0.0025 - 0.001(1.0) = 0.0015\text{ m/s} = 1.5\text{ mm/s}$.
  - Analytical time to reach the upper safety boundary $1.25\text{ m}$ ($setpoint + deadband + \epsilon$):
    $$t_{1.25} = \left[ -2000u - 5000\ln(2.5 - u) \right]_{1.0}^{\sqrt{1.25}} \approx -3853.54 - (-4027.33) \approx 173.8\text{ s} \approx 174\text{ s}$$
  - Analytical fill time from $1.0\text{ m}$ to tank crest overflow ($2.50\text{ m}$):
    $$t_{fill} = \left[ -2000u - 5000\ln(2.5 - u) \right]_{1.0}^{\sqrt{2.5}} \approx -2739.2 - (-4027.3) \approx 1288.1\text{ s} \approx 1288\text{ s}$$
  - Because $1288\text{ s} > 1200\text{ s}$, a 1200 s hold produces NO overflow. Therefore, AM-5 uses `hold_ticks = 1500`.
  - Overflow ticks in Monitor mode: $1500 - 1288 = 212 \approx 210\text{ ticks}$.
- **Ingress Filter Behavior:** At $H = 1.0\text{ m}$, pump ON is valid ($1.0\text{ m} \le 1.25\text{ m}$). Ingress filter allows the command.
- **Continuous Enforcement Behavior:**
  - On every simulation tick, the active hold is re-evaluated against the live level estimate $h_{est}$.
  - Tank fills at $1.5\text{ mm/s}$ initially, crossing $1.25\text{ m}$ at $t \approx 174\text{ s}$.
  - When $h_{est} > 1.25\text{ m}$ ($t \approx 174\text{ s}$), Continuous Enforcement flags a safety violation and **drops the hold** (`hold_ticks = 0`).
  - Control reverts immediately to the autonomous controller, which de-energizes the pump.
- **Pass Conditions:**
  - **Monitor Mode:** Command hold persists for 1500 s without continuous enforcement. Tank overflows in $\ge 9$ of 10 seeds ($\approx 210$ overflow ticks). Gateway dispatches `would_drop` event at $H > 1.25\text{ m}$ ($t \approx 174\text{ s}$).
  - **Prevention Mode:** Continuous enforcement drops the hold at $H > 1.25\text{ m}$ ($t \approx 174\text{ s}$). Exactly **0 overflow ticks** across all 10 seeds.

#### AM-6: In-Band Malicious Hold - Draining ($H=1.0\text{ m}$, Pump OFF, Hold 1800s)
- **Threat Model:** Authenticated insider possessing the valid API shared secret (A4 threat model). Continuous Enforcement is the primary defense.
- **Attack Nature:** Attacker issues authenticated command `pump_cmd = 0, valve_cmd = 50.0%, hold_ticks = 1800` while tank level is nominal ($H \approx 1.0\text{ m}$).
- **Analytical Timing from 1.0m to 0.75m and 0.05m:**
  - Gravity drain rate: $\frac{dh}{dt} = -\frac{0.002\sqrt{h}}{2.0} = -0.001\sqrt{h}$. At $h = 1.0\text{ m}$, rate is $-1.0\text{ mm/s}$.
  - Analytical time to reach the lower safety boundary $0.75\text{ m}$ ($setpoint - deadband - \epsilon$):
    $$t_{0.75} = \frac{2}{0.001} \left( \sqrt{1.0} - \sqrt{0.75} \right) = 2000(1.0 - 0.866025) \approx 267.95\text{ s} \approx 268\text{ s}$$
  - Analytical drain time from $1.0\text{ m}$ to pump cavitation/dry-run ($0.05\text{ m}$):
    $$t_{drain} = \frac{2}{0.001} \left( \sqrt{1.0} - \sqrt{0.05} \right) = 2000(1.0 - 0.22361) \approx 1552.8\text{ s} \approx 1553\text{ s}$$
  - Dry-run ticks in Monitor mode: $1800 - 1553 = 247\text{ ticks}$.
- **Ingress Filter Behavior:** At $H = 1.0\text{ m}$, pump OFF is valid ($1.0\text{ m} \ge 0.75\text{ m}$). Ingress filter allows the command.
- **Continuous Enforcement Behavior:**
  - On every simulation tick, active hold is re-evaluated against live level estimate $h_{est}$.
  - When $h_{est}$ falls below $0.75\text{ m}$ ($t \approx 268\text{ s}$), Continuous Enforcement flags a safety violation and **drops the hold** (`hold_ticks = 0`).
  - Control reverts immediately to the autonomous controller, which commands pump ON ($1$), arresting tank drainage.
- **Pass Conditions:**
  - **Monitor Mode:** Command hold persists for 1800 s. Tank reaches dry-run ($0.05\text{ m}$) at $t \approx 1553\text{ s}$, remaining in dry-run for $\approx 247$ ticks. Gateway dispatches `would_drop` event at $H < 0.75\text{ m}$ ($t \approx 268\text{ s}$).
  - **Prevention Mode:** Continuous enforcement drops the hold at $H < 0.75\text{ m}$ ($t \approx 268\text{ s}$). Exactly **0 dry-run ticks** across all 10 seeds.

#### AM-7: Unauthenticated Hold Cap Test ($H=1.0\text{ m}$, Pump ON, Hold 1500s)
- **Threat Model:** Unauthenticated attacker issuing commands without credentials or with an invalid secret.
- **Attack Payload:** `POST /api/command` with `pump_cmd = 1, valve_cmd = 50.0%, hold_ticks = 1500`.
- **Validation & Cap Enforcement:**
  - Ingress validator detects unauthenticated request.
  - Applies uniform 60-tick hold cap: `hold_ticks = min(1500, 60) = 60`.
  - Ingress filter accepts the command since $H = 1.0\text{ m} \le 1.25\text{ m}$.
  - Over 60 seconds, tank level fills by $\Delta h \approx 60 \times 0.0014\text{ m/s} \approx 0.084\text{ m} = 8.4\text{ cm}$, reaching $H \approx 1.084\text{ m}$, safely inside the $[0.8, 1.2\text{ m}]$ operational deadband.
  - At $t = 60\text{ s}$, the hold expires naturally, returning authority to the autonomous controller well before reaching the $1.25\text{ m}$ limit ($t \approx 174\text{ s}$).
- **Pass Condition:** Command accepted with `hold_ticks: 60`. Exactly **0 overflow ticks** and **0 dry-run ticks** across all 10 seeds.

---

## 3. Policy Engine v2 Limitations & New Gateway-Side Safety Function

### 3.1 Policy Engine v2 Discrepancy & Docstring Reality

Inspection of `engines/policy_engine.py` reveals the following implementation of `evaluate_v2`:

```python
    def evaluate_v2(self, h_observed: float, pump_command: int, valve_command: float) -> float:
        """
        Evaluate safety rules based on Controller valve logic and critical boundaries.
        ...
        """
        h_off = PARAMS.controller.pump_off_threshold_m
        h_on = PARAMS.controller.pump_on_threshold_m
        safe_valve_pct = getattr(PARAMS.valve, "safe_position_pct", 0.0)
        
        if valve_command != self.default_valve_pct:
            if valve_command != safe_valve_pct or pump_command != 0:
                return 1.0
            
        # Fall back to v1 rules for critical bounds
        return self.evaluate(h_observed, pump_command, valve_command)
```

**Key Discrepancy:**
- Although `h_off` and `h_on` are retrieved, **they are never used in any comparison**.
- `evaluate_v2` only checks the valve invariant and then falls back to `evaluate()`, which only checks critical tank boundaries ($H > 2.45\text{ m}$ or $H < 0.30\text{ m}$).
- Consequently, **Policy Engine v2 does NOT catch AM-1 at nominal or elevated levels ($1.30\text{ m}$)**.
- Furthermore, `PolicyEngine` does not have access to the active controller's setpoint $r(t)$.

### 3.2 Gateway-Side Function: `evaluate_command_with_live_setpoint`

To preserve Phase 2 batch equivalence and avoid modifying existing IDS engine scoring, `PolicyEngine.evaluate_v2` is **not modified**. Instead, a dedicated gateway-side function is introduced in `GatewayCore`:

```python
def evaluate_command_with_live_setpoint(
    h_est: float,
    pump_cmd: int,
    valve_cmd: float,
    controller: Any,
    epsilon: float = 0.05,
    safe_valve: float = 0.0
) -> tuple[bool, str]:
    """
    Gateway-side command validation against live controller setpoint and deadband.
    Asserts exact Controller attributes exist; no silent fallback defaults.
    
    Safety Invariants:
    1. Valve must equal default_valve_pct OR (safe_position_pct with pump_cmd == 0).
    2. Pump ON is invalid if h_est > setpoint + deadband + epsilon (e.g. > 1.25m for sp=1.0).
    3. Pump OFF is invalid if h_est < setpoint - deadband - epsilon (e.g. < 0.75m for sp=1.0).
    
    Returns:
        (is_valid, rejection_reason)
    """
    # Strict attribute validation - explicit exceptions instead of assert
    if not hasattr(controller, "setpoint"):
        raise AttributeError("Controller missing 'setpoint' attribute")
    setpoint = float(controller.setpoint)
    if not hasattr(controller, "_deadband"):
        raise AttributeError("Controller missing '_deadband' attribute")
    deadband = float(controller._deadband)
    if not hasattr(controller, "_default_valve_pct"):
        raise AttributeError("Controller missing '_default_valve_pct' attribute")
    default_valve = float(controller._default_valve_pct)

    # Valve invariant
    if valve_cmd != default_valve:
        if valve_cmd != safe_valve or pump_cmd != 0:
            return False, f"Invalid valve position {valve_cmd}% (allowed: {default_valve}% or safe {safe_valve}% with pump OFF)"

    # Dynamic pump-vs-level hysteresis rules
    if pump_cmd == 1 and h_est > (setpoint + deadband + epsilon):
        return False, f"Pump ON forbidden at h_est={h_est:.3f}m > limit={setpoint + deadband + epsilon:.3f}m"

    if pump_cmd == 0 and h_est < (setpoint - deadband - epsilon):
        return False, f"Pump OFF forbidden at h_est={h_est:.3f}m < limit={setpoint - deadband - epsilon:.3f}m"

    return True, "Valid"
```

### 3.3 Offline Database Evaluation Matrix (Measured Numbers)

The function `evaluate_command_with_live_setpoint` was executed against all stored database scenarios via `experiments/validate_gateway_rule.py` (`data/scada_ids.db`):

| Scenario Corpus | Description | Inside GT Hits | Outside GT Hits | Measured Verdict | Rationale & Empirical Findings |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **All 60 Normal Scenarios (`N_001` to `N_060`)** | Full Phase 1 normal runs: Steady_State (20,000t), Setpoint_Change (15,000t), Variable_Load (15,000t), Recovery (10,000t); 60,000 ticks total | **N/A** | **0 fires** (0 / 60,000) | **PASSED (0.000 FPR)** | Normal controller commands strictly follow setpoint/deadband envelope. Exactly 0 false alarms across all operating conditions. |
| **A1 FDI (`A1_001` to `A1_045`)** | Sensor bias, scale, intermittent (45 scenarios, 45,000 ticks total) | **1818 fires** (across 35 scenarios) | **0 fires** (0 / 36,755) | **PASSED** (Matches Post-Hoc Overlay Artifact) | Post-hoc dataset artifact: In MATLAB `run_all_scenarios.m`, `run_single_scenario` ran first, then `apply_fdi` added bias post-simulation to observed level, pushing $H_{obs} > 1.25\text{ m}$ while recorded normal pump command was 1. Outside GT window: 0 fires. |
| **A2 Replay (`A2_001` to `A2_015`)** | Replay buffer attacks (15 scenarios, 15,000 ticks total) | **0 fires** (0 / 990) | **0 fires** (0 / 14,010) | **PASSED** (Expected 0, Measured 0) | Replay replays valid recorded state sequences, which stay within nominal envelope. |
| **A3 DoS (`A3_001` to `A3_015`)** | Telemetry loss (15 scenarios, 15,000 ticks total) | **0 fires** (0 / 1,035) | **0 fires** (0 / 13,965) | **PASSED** (Expected 0, Measured 0) | Plant controller fail-safe commands (`pump=0, valve=0%`) strictly satisfy the safe valve rule. |
| **A4 Authorization Misuse (`A4_001` to `A4_015`)** | Rogue actuator commands (15 scenarios, 15,000 ticks total, 1,515 attack ticks) | **1515 fires** (1,515 / 1,515) | **0 fires** (0 / 13,485) | **PASSED (100.0% Detection Rate)** | Exactly 101 hits in every single scenario (A4_001 to A4_015) catching rogue valve opening (80–100%) and forced pump ON. Outside GT window: 0 false alarms. |

---

## 4. API Design, Continuous Enforcement & Hold Semantics

### 4.1 Flask Route Specification (`POST /api/command`)
Implemented within the existing Flask server (`scada_live/scada_ids/server.py`):

```python
@app.route('/api/command', methods=['POST'])
def handle_command():
    if not request.is_json:
        return jsonify({"error": "Bad Request", "details": "Request body must be JSON"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Bad Request", "details": "Invalid JSON format"}), 400

    # 1. Schema & Field Type Validation
    if 'pump_cmd' not in data or 'valve_cmd' not in data:
        return jsonify({"error": "Bad Request", "details": "Missing required fields 'pump_cmd' or 'valve_cmd'"}), 400

    try:
        pump_cmd = int(data['pump_cmd'])
        valve_cmd = float(data['valve_cmd'])
        hold_ticks = int(data.get('hold_ticks', 1))
    except (ValueError, TypeError) as ex:
        return jsonify({"error": "Bad Request", "details": f"Field type error: {str(ex)}"}), 400

    if pump_cmd not in (0, 1):
        return jsonify({"error": "Bad Request", "details": "pump_cmd must be 0 or 1"}), 400
    if not (0.0 <= valve_cmd <= 100.0):
        return jsonify({"error": "Bad Request", "details": "valve_cmd must be between 0.0 and 100.0"}), 400
    if hold_ticks <= 0:
        return jsonify({"error": "Bad Request", "details": "hold_ticks must be positive"}), 400

    # 2. Hold Duration Cap for Non-Authenticated Callers (Fail-Closed, hmac.compare_digest)
    cfg_obj = current_app.config.get('SCADA_CONFIG')
    api_cfg = getattr(cfg_obj, 'api', None) if cfg_obj else None
    shared_secret = str(getattr(api_cfg, 'shared_secret', '') or '')
    
    is_authenticated = False
    if shared_secret:  # If secret missing or empty in config -> Fail Closed (all callers unauthenticated)
        auth_header = request.headers.get('Authorization', '')
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        api_key = request.headers.get('X-API-Key', '').strip()
        is_authenticated = (
            (bool(bearer_token) and hmac.compare_digest(bearer_token, shared_secret))
            or (bool(api_key) and hmac.compare_digest(api_key, shared_secret))
        )
    if not is_authenticated:
        hold_ticks = min(hold_ticks, 60)  # Max 60 ticks without cryptographic shared secret

    # Metadata role attribute for telemetry logging ONLY (MUST NOT be used in validation)
    role = request.headers.get('X-Actor-Role', 'unauthenticated')

    # 3. Gateway Ingress Filtering & Mode Handling
    is_valid, reason = gateway.evaluate_ingress_command(pump_cmd, valve_cmd, hold_ticks, role)
    if not is_valid:
        if gateway.mode == "monitor":
            # Monitor mode: dispatch would_block event, record metric, do NOT block
            gateway.dispatch_event("would_block", pump_cmd, valve_cmd, reason, role)
            gateway.apply_override(pump_cmd, valve_cmd, hold_ticks)
            return jsonify({"status": "accepted_monitor", "would_block": True, "reason": reason}), 200
        else:
            # Prevention mode: block command at ingress
            gateway.dispatch_event("command_blocked", pump_cmd, valve_cmd, reason, role)
            return jsonify({"status": "blocked", "reason": reason}), 403

    gateway.apply_override(pump_cmd, valve_cmd, hold_ticks)
    return jsonify({"status": "accepted", "hold_ticks": hold_ticks}), 200
```

### 4.2 Continuous Enforcement Mechanics
1. **Per-Tick Re-Validation:**
   - On every tick $t$, if `external_override_hold_ticks > 0`:
   - Obtain best level estimate $h_{est}$ (using calibrated sensor reading or digital twin level if degraded).
   - Evaluate `evaluate_command_with_live_setpoint(h_est, held_pump_cmd, held_valve_cmd, controller)`.
2. **Mode-Dependent Action:**
   - If evaluation returns `False`:
     - If `mode == "monitor"`:
       - Dispatch `would_drop` event to `EventHub` (`source: "continuous_enforcement"`).
       - Record metric `holds_would_drop_total`.
       - Allow external hold to continue uninterrupted.
     - If `mode == "prevention"`:
       - Set `external_override_hold_ticks = 0`.
       - Dispatch `hold_dropped` event to `EventHub` (`source: "continuous_enforcement"`).
       - Record metric `holds_dropped_total`.
       - Immediately invoke `controller.step(h_est)` to issue legitimate autonomous commands.
3. **Resumption State Synchronization:**
   - When hold expires or drops, the autonomous controller synchronizes its internal state (`controller._pump_command = latest_telemetry.pump_on`) to prevent erratic toggling (the Gateway has no direct plant reference; it uses the echoed `latest_telemetry.pump_on` from the incoming telemetry packet).

---

## 5. EventHub & Metrics Integration (Flask Backend)

### 5.1 EventHub Alert Dispatch
When a command is blocked/dropped or would-be blocked/dropped:
```python
event_hub.publish({
    "event_type": "Auth misuse",
    "source": "command_filter",
    "severity": "CRITICAL",
    "timestamp": time.time(),
    "details": {
        "action": action,  # "blocked", "hold_dropped", "would_block", "would_drop"
        "pump_cmd": pump_cmd,
        "valve_cmd": valve_cmd,
        "h_est": h_est,
        "role": role,
        "reason": reason
    }
})
```

### 5.2 Metrics Collection via `MetricsCollector`
Recorded in the existing `MetricsCollector` instance in `scada_ids/`:
- `commands_received_total`: Incremented on each `/api/command` request.
- `commands_blocked_total`: Incremented on each ingress block (Prevention mode).
- `commands_would_block_total`: Incremented on each would-block (Monitor mode).
- `holds_dropped_total`: Incremented on each continuous enforcement drop (Prevention mode).
- `holds_would_drop_total`: Incremented on each continuous enforcement would-drop (Monitor mode).

---

## 6. Experimental Design & Pass Conditions

### 6.1 Simulation Environment & Parameters
- **Horizon:** $T = 2400\text{ s}$ per run.
- **Seeds:** 10 random seeds (101 to 110).
- **Noise Setting:** `clamp_flow_noise = False`.
- **Nominal Cycling:** Steady-state cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$).

### 6.2 Pass Conditions Table

| Scenario | Mode | Expected Physical Behavior | Formal Pass Condition |
| :--- | :--- | :--- | :--- |
| **AM-1 (Overflow Misuse)** | Monitor | Pump forced ON at $H = 1.30\text{ m}$; overflows in $\approx 1078\text{ s}$; overflows for $\approx 120$ ticks. | $\ge 1$ overflow event in $\ge 9$ of 10 seeds ($> 80$ mean overflow ticks). |
| | Prevention | Ingress filter blocks command at $H = 1.30\text{ m}$; pump commanded OFF; tank remains in $[0.8, 1.2\text{ m}]$. | Exactly **0 overflow ticks** across all 10 seeds. |
| **AM-2 (Dry-Run Misuse)** | Monitor | Pump OFF, valve $90\%$; drains in $\approx 806\text{ s}$; dry-run for $\approx 390$ ticks. | $\ge 1$ dry-run event in $\ge 9$ of 10 seeds ($> 200$ mean dry-run ticks). |
| | Prevention | Ingress filter blocks command; valve held at $50\%$, pump ON; tank remains $\ge 0.78\text{ m}$. | Exactly **0 dry-run ticks** across all 10 seeds. |
| **AM-3 (Tamper Misuse)** | Monitor | Downstream wire tamper forces pump ON; tank overflows. | Mismatch detected in $\le 3\text{ ticks}$; overflow harm occurs. |
| | Prevention | Gateway cannot mitigate downstream wire override; identical physical trajectory as Monitor. | Mismatch detected in $\le 3\text{ ticks}$; **identical overflow ticks to Monitor mode**. |
| **AM-4 (In-Deadband Toggle)** | Both | Rapid pump toggle at $H = 1.0\text{ m}$. | Report empirical engine behavior (Policy=0, Physics=0, record LSTM score). |
| **AM-5 (In-Band Hold - Filling)** | Monitor | Pump ON held at $H = 1.0\text{ m}$ for 1500 ticks without continuous enforcement; fills to $2.5\text{ m}$ in $\approx 1288\text{ s}$; overflows for $\approx 210$ ticks. | $\ge 1$ overflow event in $\ge 9$ of 10 seeds ($> 150$ mean overflow ticks). |
| | Prevention | Ingress allows command; Continuous Enforcement drops hold at $H > 1.25\text{ m}$; pump de-energized. | Exactly **0 overflow ticks** across all 10 seeds. |
| **AM-6 (In-Band Hold - Draining)** | Monitor | Pump OFF held at $H = 1.0\text{ m}$ for 1800 ticks without continuous enforcement; drains to $0.05\text{ m}$ in $\approx 1553\text{ s}$; dry-run for $\approx 247$ ticks. | $\ge 1$ dry-run event in $\ge 9$ of 10 seeds ($> 150$ mean dry-run ticks). |
| | Prevention | Ingress allows command; Continuous Enforcement drops hold at $H < 0.75\text{ m}$; pump energized. | Exactly **0 dry-run ticks** across all 10 seeds. |
| **AM-7 (Unauthenticated Cap)** | Both | Unauthenticated command with requested hold = 500 ticks is capped to 60 ticks. | Hold expires after exactly 60 ticks; subsequent plant state determined by autonomous controller. |
| **Normal Soak** | Prevention | 30-minute unattacked normal cycling with legitimate commands. | Exactly **0 false blocks** and **0 false takeovers**. |

---

## 7. Step-by-Step Implementation Checkpoints (Post-Approval)

When Phase 6b is approved for implementation, execution will proceed in strict order:

### Step 1: Ingress API & Command Schema (`POST /api/command`)
- Implement Flask route handler in `scada_ids/server.py` with HTTP 400 validation for invalid/missing fields.
- Attach `X-Actor-Role` header as non-authoritative metadata label (must NOT be used in validation); enforce uniform 60-tick hold cap for unauthenticated callers.
- *Test:* `test_api_command_validation.py`.

### Step 2: GatewayCore Command Pipeline, Live Validation & Continuous Enforcement
- Implement `evaluate_command_with_live_setpoint(h_est, pump_cmd, valve_cmd, controller)` in `GatewayCore` raising explicit `AttributeError` if controller attributes missing.
- Add Continuous Enforcement tick loop: re-evaluate active holds every tick; drop hold in Prevention mode, raise `would_drop` in Monitor mode.
- Validate across all 60 normal scenarios (0 fires) and offline test suite.
- Dispatch blocked command, dropped hold, would-block, and would-drop alerts to `EventHub` and `MetricsCollector`.
- *Test:* `test_phase6b_command_filtering.py`, `test_ids_verdicts_identical_between_monitor_and_prevention`.

### Step 3: Wire Tamper Hook & 4-Way Actuator Consistency
- Place bus tamper injector strictly in downstream wire/reply layer (`attacker_wire/injector.py`), never inside `LivePlant` or `GatewayCore`.
- Implement explicit boolean 4-way consistency check conditioned on Gateway pump OFF history for 2 ticks (`gateway_issued_pump_history[-2:] == [0, 0]`).
- Verify detection delay $\le 3\text{ ticks}$ and identical physical harm between Monitor and Prevention modes.
- Verify 30-minute normal soak has 0 wire tamper alerts.
- *Test:* `test_tamper_consistency_check.py`.

### Step 4: A/B Verification Harness & AM-1 to AM-7 Evaluation
- Implement `experiments/run_auth_misuse_ab.py` evaluating 10 seeds across AM-1, AM-2, AM-3, AM-4, AM-5, AM-6, AM-7.
- Verify 0 overflows/dry-runs for AM-1, AM-2, AM-5, AM-6 in Prevention mode.
- Verify unauthenticated hold cap expires at 60 ticks for AM-7.
- Record empirical engine firing measurements for AM-4.
- Update `PROJECT_REVIEW_CHEAT_SHEET.md`.

---

## 8. Summary of Explicit Constraints
1. **NO Phase 6b code written until this plan is formally reviewed and approved.**
2. **AM-3 is strictly detect-only; gateway does not claim mitigation for bus-level tampering.**
3. **No JWT parsing; role labels are non-authoritative metrics attributes; 60-tick hold cap is uniform across all unauthenticated callers.**
4. **Pass conditions accurately reflect ODE fill and drain durations (806 s drain for AM-2, ~1078 s fill for AM-1 starting at 1.3 m, 1288 s fill for AM-5 from 1.0 m, 1553 s drain for AM-6 from 1.0 m).**
5. **No modification of `PolicyEngine.evaluate_v2` or batch Phase 2 results; new function is strictly gateway-side.**
6. **No FastAPI/Starlette or external Prometheus client; built on Flask and internal `EventHub`/`MetricsCollector`.**
7. **HTTP route returns 400 Bad Request on invalid/missing fields, never 500.**
8. **Monitor mode dispatches `would_block` and `would_drop` events at the exact same ticks and takes no blocking action.**
