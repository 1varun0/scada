# Phase 6b Implementation Plan: Authorization Misuse Detection, Command Filtering & Actuator Consistency

> **Status:** Draft / Pending User Approval — STOPPED FOR REVIEW.  
> **Scope:** Architecture and design specification for Phase 6b (Command filtering, authorization misuse mitigation, channel vs tamper variants, actuator-feedback consistency). **NO Phase 6b implementation code is written in this step.**

---

## 1. Overview & Objectives

In Phase 6a, we verified physical protection against sensor-spoofing attacks (FDI ramps, DoS gaps, stealthy drift) via Digital Twin takeover.
In Phase 6b, we address **actuator-level command attacks (Authorization Misuse / Rogue Commands)**:
1. **Ingress Filtering vs Bus Tampering Distinction:**
   - **"Channel" Ingress Misuse (AM-1, AM-2):** Malicious commands arrive at the Gateway ingress API (`POST /api/command`). The Gateway evaluates them against process safety constraints and **blocks** them before plant dispatch in Prevention mode.
   - **"Tamper" Man-in-the-Middle Override (AM-3):** Commands are altered downstream on the physical wire/fieldbus. The Gateway **cannot prevent or mitigate a bus-level override** because downstream plant hardware ignores gateway commands; AM-3 is **DETECT-ONLY**. Success is defined by detection delay and attribution, with identical physical harm across both Monitor and Prevention modes.
   - **"In-Deadband Toggle" (AM-4):** An attacker toggles the pump within the operational deadband ($0.8\text{ m} \le H \le 1.2\text{ m}$). This represents a documented blind spot for policy and physics engines.
2. **Alert Manager Integration:**
   - Every blocked command raises an alert/event (`event_type: "Auth misuse"`, `source: "command_filter"`) in the alert manager and Prometheus-style metrics.
   - **IDS Verdict Invariant:** IDS verdict scoring and telemetry engine outputs are **100% identical** between Monitor and Prevention modes.
3. **Rigorous Physical Pass Conditions:**
   - Attacks start from steady-state nominal cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$).
   - With an attack hold duration of 1200 s, AM-1 overflows for $\approx 90$ ticks and AM-2 causes dry-run for $\approx 390$ ticks (analytical dry-run time is $\approx 806\text{ s}$, not 650 s).
   - Pass criterion: At least one overflow/dry-run event in at least 9 of 10 seeds in Monitor mode; 0 overflow and 0 dry-run events across all 10 seeds in Prevention mode.
4. **Recorded Architectural Decisions:**
   - **No JWT / Cryptographic Tokens:** `X-Actor-Role` is a self-declared role label used solely for telemetry attribution and metrics; it does **not** influence blocking decisions.
   - **Tamper Hook Location:** The bus-level tamper hook lives strictly in the injector/wire layer (reply override middleware / synthetic fieldbus fault), **never** inside `LivePlant` core or `GatewayCore`.

---

## 2. Threat Scenarios & Physical Mechanics

### 2.1 Attack Scenarios Summary

| Threat ID | Threat Class | Ingress Point | Primary Detection Engine | Mitigable by Gateway? | Pass Condition (10 Seeds) |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **AM-1** | Channel Ingress Misuse | `POST /api/command` | Policy Engine / Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ overflow event in $\ge 9/10$ seeds (~90 ov ticks); Prevention: 0 ov ticks. |
| **AM-2** | Channel Ingress Misuse | `POST /api/command` | Policy Engine / Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ dry-run event in $\ge 9/10$ seeds (~390 dry ticks); Prevention: 0 dry ticks. |
| **AM-3** | Wire / Fieldbus Tamper | Wire / Network Bus | Actuator-Feedback Consistency | **No** (Detect-Only) | Detection delay $\le 3$ ticks, correct attribution; physical harm identical in Monitor and Prevention. |
| **AM-4** | In-Deadband Toggle | `POST /api/command` | Empirical Engine Test | No (Within Deadband) | Policy & Physics Twin do NOT fire; record empirical engine behavior without unverified claims. |

---

### 2.2 Detailed Threat Mechanics

#### AM-1: Overflow Misuse (Pump Latched ON at High Level)
- **Initiation Point:** Initiated when the tank level rises toward the upper boundary ($H \approx 1.25\text{ m}$).
- **Command Payload:** Rogue command forces `pump_cmd = 1`, `valve_cmd = 50.0%`, with `hold_ticks = 1200`.
- **Physical Dynamics & Analytical Timing:**
  - Net fill rate: $\frac{dh}{dt} = \frac{Q_{in} - Q_{out}}{A} = \frac{0.005 - 0.002\sqrt{h}}{2.0} = 0.0025 - 0.001\sqrt{h}$.
  - Analytical fill time from $h = 1.25\text{ m}$ to tank crest overflow ($h = 2.50\text{ m}$):
    $$t_{fill} = 2000 \left[ -u - 2.5 \ln(2.5 - u) \right]_{\sqrt{1.25}}^{\sqrt{2.5}} \approx 1110\text{ s}$$
  - For an attack hold duration of $1200\text{ s}$, the tank hits overflow at $t \approx 1110\text{ s}$ and remains overflowing for the remaining $1200 - 1110 = 90\text{ ticks}$.
- **Monitor Mode:** Command is dispatched to the plant. Tank overflows for $\approx 90$ ticks, hitting $2.50\text{ m}$.
- **Prevention Mode:** Command filter blocks the rogue command at ingress. Autonomous controller commands pump OFF ($0$). Tank remains within $[0.8, 1.2\text{ m}]$ with 0 overflow ticks.

#### AM-2: Dry-Run Misuse (Excessive Drainage at Low Level)
- **Initiation Point:** Initiated when the tank level drops toward the lower boundary ($H \approx 0.90\text{ m}$).
- **Command Payload:** Rogue command forces `pump_cmd = 0`, `valve_cmd = 90.0%` (extreme opening), with `hold_ticks = 1200`.
- **Physical Dynamics & Analytical Timing:**
  - Inflow $Q_{in} = 0$. At valve position $90\%$, outflow coefficient is $C_v \times \frac{90}{100} = 0.004 \times 0.90 = 0.0036\text{ m}^3\text{/s}$.
  - Analytical gravity drainage: $\frac{dh}{dt} = -\frac{0.0036\sqrt{h}}{2.0} = -0.0018\sqrt{h}$.
  - Analytical drain time from $h = 0.90\text{ m}$ to pump cavitation / suction dry-run ($h = 0.05\text{ m}$):
    $$t_{drain} = \frac{2}{0.0018} \left( \sqrt{0.90} - \sqrt{0.05} \right) = \frac{20000}{18} (0.94868 - 0.22361) \approx 805.6\text{ s} \approx 806\text{ s}$$
  - For an attack hold duration of $1200\text{ s}$, the tank hits dry-run at $t \approx 806\text{ s}$ and remains in dry-run for the remaining $1200 - 806 = 394 \approx 390\text{ ticks}$.
- **Monitor Mode:** Command is dispatched to the plant. Tank drains to $0.05\text{ m}$ in $\approx 806\text{ s}$, remaining in dry-run for $\approx 390$ ticks.
- **Prevention Mode:** Command filter blocks the rogue command at ingress. Autonomous controller maintains default valve position ($50\%$) and energizes pump ($1$). Tank level stays $\ge 0.78\text{ m}$ with 0 dry-run ticks.

#### AM-3: Tamper Misuse (Bus-Level Actuator Override — Detect-Only)
- **Attack Nature:** The attacker intercepts actuator communications on the fieldbus downstream of the Gateway (e.g., via compromised RTU firmware or 4-20mA current loop bridge). The Gateway issues `pump_cmd = 0, valve_cmd = 50%`, but the wire tamper forces the physical pump ON (`pump_cmd = 1`).
- **Mitigation Limitation:** **The Gateway cannot mitigate a bus-level override.** Because the override occurs downstream of the gateway's control interface, re-sending commands or entering twin takeover cannot override the hardware fault on the wire.
- **Actuator-Feedback Consistency Check:**
  - Defined as a Gateway-side diagnostic check or versioned policy rule, **not a modification to scored IDS engines**.
  - Consistency conditions:
    1. **Pump Consistency:** $| \text{pump\_on}_{t} - \text{pump\_cmd}_{t - \Delta t_{pump}} | == 0$ after pump response delay ($\Delta t_{pump} = 2.0\text{ s} = 2\text{ ticks}$).
    2. **Valve Consistency:** $| \text{valve\_pct}_{t} - \text{valve\_cmd}_{t - \Delta t_{slew}} | \le \epsilon_{slew}$ after valve slew time.
    3. **Flowmeter Sanity Check (Optional):** $Q_{in,meas} > 0.001\text{ m}^3\text{/s}$ while pump has been commanded OFF for $> 3\text{ s}$.
- **Attribution & Success Criterion:**
  - Detection delay $\le 3\text{ ticks}$ from physical actuator execution.
  - Attribution alert tagged as `tamper_actuator_mismatch` (Source: `wire_tamper_monitor`).
  - **Identical Physical Harm:** Because the bus override cannot be undone from the gateway software, physical harm (overflow ticks) is **identical** in both Monitor and Prevention modes.

#### AM-4: In-Deadband Pump Toggle at Nominal Level
- **Attack Nature:** Attacker issues valid valve command ($50\%$) but rapidly toggles `pump_cmd` ($0 \leftrightarrow 1$) while the water level is nominal ($H \approx 1.0\text{ m}$, inside the $[0.8, 1.2\text{ m}]$ deadband).
- **Engine Behavior & Blind Spot:**
  - **Policy Engine v2:** Does **NOT** fire. Inside the deadband, both pump ON and pump OFF are physically legitimate controller outputs depending on prior hysteresis history.
  - **Physics Twin:** Does **NOT** fire. Because the telemetry packet faithfully reports the actual pump state, the twin integrates the corresponding inflow and closely matches the plant.
  - **Temporal Engine (LSTM):** Will be empirically evaluated. **We make no claim that the LSTM catches in-deadband toggles without a concrete measurement.** The evaluation harness will record whether LSTM prediction error crosses threshold $\tau_{temporal} = 0.95$.

---

## 3. Policy Engine v2 Source Code & Normal Operation Constraints

### 3.1 Current Policy Engine Source Code

Below is the verbatim source code of `evaluate_v2` and `evaluate` from `engines/policy_engine.py`:

```python
from config.parameters import PARAMS

class PolicyEngine:
    """
    Engine 3: Command/Policy Safety (Target: A4 Auth Misuse)
    Evaluates commands against the current physical state using deterministic safety rules.
    
    Rules target authenticated misuse scenarios where valid operators issue
    commands that violate process safety constraints.
    """
    def __init__(self, epsilon_m: float = 0.05):
        self.h_crit_low = PARAMS.tank.critical_low_m
        self.h_crit_high = PARAMS.tank.critical_high_m
        self.h_max = PARAMS.tank.max_height_m
        self.epsilon = epsilon_m
        self.default_valve_pct = PARAMS.controller.default_valve_pct

    def evaluate(self, h_observed: float, pump_command: int, valve_command: float) -> float:
        """
        Evaluate safety rules. Returns 1.0 if a violation occurs, else 0.0.
        
        Rules:
        1. Pump ON when H > H_crit_high (near overflow) => 1.0
        2. Valve opened ABOVE the controller default when H < H_crit_low => 1.0
        """
        # Rule 1: Tank nearly overflowing, but pump is commanded ON
        if h_observed > (self.h_max - self.epsilon) and pump_command == 1:
            return 1.0
            
        # Rule 2: Tank critically low and valve opened beyond normal operating point
        # This correctly targets misuse (e.g., VALVE_SET_80 when H is dangerously low)
        # without flagging the controller's normal default valve position
        if h_observed < self.h_crit_low and valve_command > self.default_valve_pct:
            return 1.0
            
        return 0.0

    def evaluate_v2(self, h_observed: float, pump_command: int, valve_command: float) -> float:
        """
        Evaluate stricter safety rules based on Controller hysteresis band and valve logic.
        
        Rules:
        1. Pump ON when H > H_off (1.2m) + epsilon => 1.0
        2. Pump OFF when H < H_on (0.8m) - epsilon => 1.0
        3. Valve is not a legitimate value (default or safe_position) => 1.0
        """
        h_off = PARAMS.controller.pump_off_threshold_m
        h_on = PARAMS.controller.pump_on_threshold_m
        safe_valve_pct = getattr(PARAMS.valve, "safe_position_pct", 0.0)
        
        # The controller only enters fail-safe (valve=0.0) when dos is active, and forces pump=0.
        # Allow safe_position only if the pump is also OFF.
        if valve_command != self.default_valve_pct:
            if valve_command != safe_valve_pct or pump_command != 0:
                return 1.0
            
        # Fall back to v1 rules for critical bounds
        return self.evaluate(h_observed, pump_command, valve_command)
```

### 3.2 Key Findings on Policy Engine Capabilities
1. **Not Setpoint-Aware:** `PolicyEngine` receives only `(h_observed, pump_command, valve_command)`. It has no knowledge of current setpoint $r(t)$.
2. **Why Fixed 0.8 / 1.2 m Thresholds Cannot Be Hardcoded:** In normal operating scenarios (e.g., setpoint profile steps where setpoint moves to $1.5\text{ m}$), the pump is legitimately commanded ON at levels between $1.3\text{ m}$ and $1.7\text{ m}$. Enforcing fixed $[0.8, 1.2\text{ m}]$ pump thresholds in `evaluate_v2` would cause severe false blocks during normal setpoint transitions.
3. **Current Active Rules in `evaluate_v2`:**
   - **Valve Invariant:** Valve must equal nominal $50.0\%$ OR fail-safe $0.0\%$ (only permitted if `pump_cmd == 0`). Any other valve position (such as $90\%$ in AM-2) triggers an immediate $1.0$ violation score.
   - **Critical Overflow Boundary:** If $H > 2.45\text{ m}$ ($H_{max} - \epsilon$) and `pump_cmd == 1`, triggers $1.0$.
   - **Critical Low Boundary:** If $H < 0.30\text{ m}$ and `valve_cmd > 50%`, triggers $1.0$.
4. **Command Filter Design for Phase 6b:**
   - The ingress command filter uses `PolicyEngine.evaluate_v2`.
   - To catch AM-1 earlier than $2.45\text{ m}$, the gateway evaluates against the active operational setpoint envelope $[H_{sp} - \Delta_{db}, H_{sp} + \Delta_{db}]$ when setpoint is known, OR enforces that external manual overrides cannot command pump ON when $H > 1.25\text{ m}$ under nominal setpoint $1.0\text{ m}$.

---

## 4. API Design, Roles, and Hold Semantics

### 4.1 `POST /api/command` Endpoint Specification
- **Path:** `/api/command`
- **Method:** `POST`
- **Headers:**
  - `Content-Type: application/json`
  - `X-Actor-Role: operator | supervisor | attacker | automated` (Telemetry label only; **does not influence blocking**)
- **Request Payload:**
  ```json
  {
    "run_id": "live_session_01",
    "pump_cmd": 1,
    "valve_cmd": 50.0,
    "hold_ticks": 1200,
    "source": "maintenance_console"
  }
  ```
- **Validation Rules:**
  - `pump_cmd`: Integer $\in \{0, 1\}$.
  - `valve_cmd`: Float $\in [0.0, 100.0]$.
  - `hold_ticks`: Integer $\ge 1$ (unconstrained up to run horizon $T = 2400$; max 300 constraint removed).
  - Out-of-bounds parameters reject with HTTP 400 Bad Request.

### 4.2 Role Label Semantics (`X-Actor-Role`)
- **Recorded Decision:** **No JWT or cryptographic token parsing.**
- `X-Actor-Role` is self-declared metadata used strictly for Prometheus metrics, alert categorization, and log attribution.
- The command filter evaluates safety purely on the physical payload and plant state, regardless of whether the header claims `"operator"`, `"supervisor"`, or `"attacker"`.

### 4.3 Definition of Legitimate Command Set (False Block Metric)
To measure the `false_block_rate` cleanly:
- **Legitimate Command Set:**
  1. Controller-identical commands: commands that match what the autonomous hysteresis controller would output at that tick.
  2. Safe operator actions: manual pump shutdown (`pump=0, valve=50%`) when $H > 1.0\text{ m}$; valve fail-safe closure (`pump=0, valve=0%`).
- **Policy Invariance:** Legitimate commands within this set must produce **0 blocked commands** across 10 unattacked seeds over a 30-minute soak run.
- **In-Deadband Ambiguity:** In-deadband toggles ($0.8 < H < 1.2\text{ m}$) cannot be differentiated by policy alone, so policy filters will neither flag nor block them.

### 4.4 Override Hold Semantics
When a valid external command is accepted:
1. `hold_ticks` sets an internal countdown timer `external_override_hold_ticks`.
2. While `external_override_hold_ticks > 0`:
   - The autonomous controller's `step()` method is **bypassed**.
   - The controller's internal hysteresis state (`self._pump_command`) is **not updated**.
   - Actuator commands are forced to `(pump_cmd_ext, valve_cmd_ext)`.
3. **Resumption State Upon Hold Expiry:**
   - When `external_override_hold_ticks` reaches 0, autonomous control resumes on the subsequent tick.
   - If observed level $H_{obs} < 0.80\text{ m}$: controller asserts `pump_command = 1`.
   - If observed level $H_{obs} > 1.20\text{ m}$: controller asserts `pump_command = 0`.
   - If observed level $H_{obs} \in [0.80, 1.20\text{ m}]$: to prevent artificial transient switching, the controller synchronizes its internal memory with the plant's actual current actuator state (`self._pump_command = plant.pump.state`).

---

## 5. Alert Manager & Metrics Integration

### 5.1 Alert Generation on Blocked Command
Whenever a command is blocked by the ingress filter in Prevention mode:
1. An event is dispatched to `EventHub`:
   - `event_type`: `"Auth misuse"`
   - `source`: `"command_filter"`
   - `severity`: `"CRITICAL"`
   - `details`: `{"blocked_command": {"pump": pump_cmd, "valve": valve_cmd}, "level": h_eval, "reason": "policy_violation"}`
2. Prometheus counters incremented:
   - `scada_commands_received_total{role=...}`
   - `scada_commands_blocked_total{role=..., reason=...}`

### 5.2 IDS Verdict Scoring Invariance
- **Critical Requirement:** **IDS verdict scoring must be identical in Monitor and Prevention modes.**
- The IDS engines (Physics Twin, Temporal LSTM, Availability, Policy Engine) operate strictly on telemetry observations received from the plant.
- Command filtering occurs at the ingress gateway interface before or alongside dispatch; it must **not** alter the internal scoring thresholds or evaluation mathematics of `StreamingIDS`.
- Unit test `test_ids_verdicts_identical_between_monitor_and_prevention` will explicitly assert that given identical telemetry streams, IDS anomaly scores and engine firing sets match tick-for-tick across both modes.

---

## 6. Experimental Design & Pass Conditions

### 6.1 Simulation Environment & Parameters
- **Horizon:** $T = 2400\text{ s}$ per run.
- **Seeds:** 10 random seeds (101 to 110).
- **Noise Setting:** `clamp_flow_noise = False` (zero-mean symmetric Gaussian noise).
- **Starting Level:** Steady-state nominal cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$).
- **Hold Duration:** `hold_ticks = 1200` (or hold to the end of the simulation run).

### 6.2 Pass Conditions

| Scenario | Mode | Expected Physical Behavior | Formal Pass Condition |
| :--- | :--- | :--- | :--- |
| **AM-1 (Overflow Misuse)** | Monitor | Pump forced ON; fills at $\approx 1.16\text{ mm/s}$; hits $2.50\text{ m}$ in $\approx 1110\text{ s}$; overflows for $\approx 90$ ticks. | $\ge 1$ overflow event in $\ge 9$ of 10 seeds ($> 50$ mean overflow ticks). |
| | Prevention | Ingress filter blocks command; pump switched OFF; tank remains in $[0.8, 1.2\text{ m}]$. | Exactly **0 overflow ticks** and **0 overflow events** across all 10 seeds. |
| **AM-2 (Dry-Run Misuse)** | Monitor | Pump OFF, valve $90\%$; drains in $\approx 806\text{ s}$; dry-run for $\approx 390$ ticks. | $\ge 1$ dry-run event in $\ge 9$ of 10 seeds ($> 200$ mean dry-run ticks). |
| | Prevention | Ingress filter blocks command; valve held at $50\%$, pump ON; tank remains $\ge 0.78\text{ m}$. | Exactly **0 dry-run ticks** and **0 dry-run events** across all 10 seeds. |
| **AM-3 (Tamper Misuse)** | Monitor | Downstream wire tamper forces pump ON; tank overflows. | Mismatch detected in $\le 3\text{ ticks}$; overflow harm occurs. |
| | Prevention | Cannot mitigate downstream bus override; identical physical trajectory as Monitor. | Mismatch detected in $\le 3\text{ ticks}$; **identical overflow ticks to Monitor mode**. |
| **AM-4 (In-Deadband Toggle)** | Both | Rapid pump toggle at $H \approx 1.0\text{ m}$. | Report which engine fires (Policy=0, Physics=0; record empirical LSTM score). |
| **Normal Soak** | Prevention | 30-minute unattacked normal cycling with legitimate commands. | Exactly **0 false blocks** and **0 false takeovers**. |

---

## 7. Step-by-Step Implementation Checkpoints (Post-Approval)

When Phase 6b is approved for implementation, execution will proceed in strict order:

### Step 1: Ingress API & Command Schema (`POST /api/command`)
- Implement FastAPI/Starlette route handler `POST /api/command`.
- Validate against `CommandPacket` schema (support arbitrary `hold_ticks`).
- Attach `X-Actor-Role` header as metadata label only.
- *Test:* `test_api_command_validation.py`.

### Step 2: GatewayCore Command Pipeline & Policy Filtering
- Implement `GatewayCore.process_external_command()`.
- Add `hold_ticks` override scheduler and clean resumption semantics.
- Evaluate against `PolicyEngine.evaluate_v2` using dynamic best-level estimate.
- In Prevention mode: block violation, emit `Auth misuse` event from `command_filter`.
- In Monitor mode: forward violation to plant, log warning.
- *Test:* `test_phase6b_command_filtering.py`, `test_ids_verdicts_identical_between_monitor_and_prevention`.

### Step 3: Wire Tamper Hook & Actuator-Feedback Consistency
- Place bus tamper injector strictly in the wire/reply layer (synthetic fieldbus fault), never in `LivePlant` or `GatewayCore`.
- Implement actuator consistency diagnostic check (`pump_on` vs `pump_cmd` after 2s delay; `valve_state` vs `valve_cmd` after slew).
- Verify AM-3 is detect-only with identical physical harm in both modes.
- *Test:* `test_tamper_consistency_check.py`.

### Step 4: A/B Verification Harness & AM-4 Empirical Study
- Implement `experiments/run_auth_misuse_ab.py` evaluating 10 seeds across AM-1, AM-2, AM-3, AM-4.
- Verify 0 overflows/dry-runs for AM-1 and AM-2 in Prevention mode.
- Record empirical engine firing measurements for AM-4.
- Update `PROJECT_REVIEW_CHEAT_SHEET.md`.

---

## 8. Summary of Explicit Constraints
1. **NO Phase 6b code written until this plan is formally reviewed and approved.**
2. **AM-3 is strictly detect-only; gateway does not claim mitigation for bus-level tampering.**
3. **No JWT parsing; role labels are non-authoritative metrics attributes.**
4. **Pass conditions accurately reflect ODE fill and drain durations (806 s drain, ~90 ticks AM-1 overflow, ~390 ticks AM-2 dry-run).**
5. **No claims of LSTM detection on in-deadband toggles without empirical proof.**
