# Phase 6b Implementation Plan: Authorization Misuse Detection, Command Filtering & Actuator Consistency

> **Status:** Draft / Pending User Approval — STOPPED FOR REVIEW.  
> **Scope:** Architecture and design specification for Phase 6b (Command filtering, authorization misuse mitigation, channel vs tamper variants, continuous enforcement, actuator-feedback consistency). **NO Phase 6b implementation code is written in this step.**

---

## 1. Overview & Objectives

In Phase 6a, we verified physical protection against sensor-spoofing attacks (FDI ramps, DoS gaps, stealthy drift) via Digital Twin takeover.
In Phase 6b, we address **actuator-level command attacks (Authorization Misuse / Rogue Commands)**:

1. **Ingress Filtering vs Bus Tampering vs Continuous Hold Enforcement:**
   - **"Channel" Ingress Misuse (AM-1, AM-2):** Malicious commands arrive at the Gateway ingress API (`POST /api/command`). The Gateway evaluates them against process safety constraints via a dedicated gateway-side function (`evaluate_command_with_live_setpoint`) and **blocks** them before plant dispatch in Prevention mode.
     - **AM-1 (High-Level Pump Latch):** Starts at $H = 1.30\text{ m}$ (above the $1.25\text{ m}$ boundary $[1.0 + 0.20 + 0.05]$) with `pump_cmd = 1, valve_cmd = 50%`. Ingress filter blocks it immediately.
     - **AM-2 (Low-Level Drainage):** Starts at $H \approx 0.90\text{ m}$ with `pump_cmd = 0, valve_cmd = 90%`. Ingress filter blocks it immediately.
   - **"Wire / Fieldbus Tamper" (AM-3):** Commands are altered downstream on the physical wire/fieldbus (injector reply override). The Gateway **cannot prevent or mitigate a bus-level override** because downstream plant hardware ignores gateway commands; AM-3 is **DETECT-ONLY**. Success is defined by detection delay ($\le 3\text{ ticks}$) and attribution, with identical physical harm across both Monitor and Prevention modes.
   - **"In-Deadband Toggle" (AM-4):** An attacker toggles the pump within the operational deadband ($0.8\text{ m} \le H \le 1.2\text{ m}$, e.g. at $1.0\text{ m}$). This represents a documented blind spot for policy and physics engines. Evaluated empirically without unverified claims.
   - **"In-Band Malicious Hold" (AM-5):** Attacker issues a superficially valid command at nominal level ($H \approx 1.0\text{ m}$, `pump_cmd = 1`, `hold_ticks = 1200`). Ingress filtering allows it initially because $H = 1.0\text{ m}$ is within the valid deadband envelope. However, **Continuous Enforcement** re-evaluates the hold on every simulation tick against the live level estimate $h_{est}$ and drops the hold when level crosses $H > 1.25\text{ m}$ ($setpoint + deadband + \epsilon$), preventing tank overflow.
2. **Alert Manager & Metrics Integration:**
   - Every blocked command or dropped hold raises an alert/event (`event_type: "Auth misuse"`, `source: "command_filter"`) in the existing `EventHub` and `MetricsCollector` via Flask routes in `scada_ids/server.py`.
   - **No FastAPI/Starlette, no external Prometheus client:** Built entirely on the existing Flask backend and internal metric collectors.
   - **IDS Verdict Invariant:** IDS verdict scoring and telemetry engine outputs are **100% identical** between Monitor and Prevention modes.
3. **Rigorous Physical Pass Conditions:**
   - Attacks start from steady-state nominal cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$), with AM-1 specifically starting at $1.30\text{ m}$.
   - With an attack hold duration of $1200\text{ s}$, AM-1 overflows for $\approx 120$ ticks in Monitor mode (analytical fill time $\approx 1078\text{ s}$); AM-2 causes dry-run for $\approx 390$ ticks (analytical drain time $\approx 806\text{ s}$); AM-5 overflows for $\approx 90$ ticks in Monitor mode.
   - Pass criterion: At least one overflow/dry-run event in at least 9 of 10 seeds in Monitor mode; exactly 0 overflow and 0 dry-run events across all 10 seeds in Prevention mode.
4. **Recorded Architectural Decisions:**
   - **Flask Routes & Existing Hub:** Server implementation uses existing Flask framework in `scada_ids/server.py` and `EventHub`/`MetricsCollector`.
   - **No JWT / Cryptographic Tokens:** `X-Actor-Role` is a self-declared role label used solely for telemetry attribution and metrics; it does **not** influence blocking decisions. Non-authenticated or external sources have their `hold_ticks` capped (e.g., max 60 ticks) requiring continuous re-send.
   - **Tamper Hook Location:** The bus-level tamper hook lives strictly in the injector/wire layer (reply override middleware / synthetic fieldbus fault), **never** inside `LivePlant` core or `GatewayCore`.

---

## 2. Threat Scenarios & Physical Mechanics

### 2.1 Attack Scenarios Summary

| Threat ID | Threat Class | Ingress Point | Primary Detection Engine | Mitigable by Gateway? | Pass Condition (10 Seeds) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AM-1** | Channel Ingress Misuse | `POST /api/command` | Gateway Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ overflow event in $\ge 9/10$ seeds (~120 ov ticks); Prevention: 0 ov ticks. |
| **AM-2** | Channel Ingress Misuse | `POST /api/command` | Gateway Command Filter | **Yes** (Ingress Drop) | Monitor: $\ge 1$ dry-run event in $\ge 9/10$ seeds (~390 dry ticks); Prevention: 0 dry ticks. |
| **AM-3** | Wire / Fieldbus Tamper | Downstream Wire Reply Override | 4-Way Actuator Consistency | **No** (Detect-Only) | Detection delay $\le 3$ ticks, correct attribution; physical harm identical in Monitor and Prevention. |
| **AM-4** | In-Deadband Toggle | `POST /api/command` | Empirical Engine Test | No (Within Deadband) | Policy & Physics Twin do NOT fire; record empirical engine behavior without unverified claims. |
| **AM-5** | In-Band Malicious Hold | `POST /api/command` | Continuous Enforcement Filter | **Yes** (Hold Drop) | Monitor: $\ge 1$ overflow event in $\ge 9/10$ seeds (~90 ov ticks); Prevention: 0 ov ticks. |

---

### 2.2 Detailed Threat Mechanics

#### AM-1: Overflow Misuse (Pump Latched ON at High Level)
- **Initiation Point:** Initiated at $H = 1.30\text{ m}$. (Note: $1.25\text{ m}$ sits exactly on the boundary $1.0 + 0.20 + 0.05\text{ m}$, so $1.30\text{ m}$ cleanly tests unambiguous out-of-band rejection).
- **Command Payload:** Rogue command forces `pump_cmd = 1`, `valve_cmd = 50.0%`, with `hold_ticks = 1200`.
- **Physical Dynamics & Analytical Timing:**
  - Net fill rate: $\frac{dh}{dt} = \frac{Q_{in} - Q_{out}}{A} = \frac{0.005 - 0.002\sqrt{h}}{2.0} = 0.0025 - 0.001\sqrt{h}$.
  - Analytical fill time from $h = 1.30\text{ m}$ to tank crest overflow ($h = 2.50\text{ m}$):
    $$t_{fill} = \int_{1.30}^{2.50} \frac{dh}{0.0025 - 0.001\sqrt{h}} \approx 1077.95\text{ s} \approx 1078\text{ s}$$
  - For an attack hold duration of $1200\text{ s}$, the tank hits overflow at $t \approx 1078\text{ s}$ and remains overflowing for the remaining $1200 - 1078 = 122 \approx 120\text{ ticks}$.
- **Monitor Mode:** Command is dispatched to the plant. Tank overflows for $\approx 120$ ticks, hitting $2.50\text{ m}$.
- **Prevention Mode:** Gateway command filter blocks the rogue command at ingress ($1.30\text{ m} > setpoint + deadband + \epsilon = 1.25\text{ m}$). Autonomous controller commands pump OFF ($0$). Tank remains within $[0.8, 1.2\text{ m}]$ with 0 overflow ticks.

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
- **Prevention Mode:** Command filter blocks the rogue command at ingress (valve $90\% \ne 50\%$ and $\ne 0\%$). Autonomous controller maintains default valve position ($50\%$) and energizes pump ($1$). Tank level stays $\ge 0.78\text{ m}$ with 0 dry-run ticks.

#### AM-3: Tamper Misuse (Bus-Level Actuator Override — Detect-Only)
- **Packet `cmd` Semantics:** Telemetry packet fields `pkt.pump_cmd` and `pkt.valve_cmd` represent what the plant actuators physically received and set (what the plant echoes back in telemetry).
- **Tamper Location:** The tamper acts downstream of the Gateway on the wire (injector reply override middleware intercepting the plant's sense reply). The Gateway issues `pump_cmd = 0, valve_cmd = 50%`, but the wire tamper forces the reply to `pump_cmd = 1`. The plant receives $1$, executes it, and echoes `pkt.pump_cmd = 1, pkt.pump_on = True`.
- **Mitigation Limitation:** **The Gateway cannot mitigate a bus-level override.** Because the override occurs downstream of the gateway's network boundary, software commands cannot override the forced wire state. AM-3 is strictly **detect-only**.
- **4-Way Actuator-Feedback Consistency Detection Rule:**
  The gateway diagnostic compares four distinct signals:
  1. **Issued Command:** Gateway record of the command transmitted to the plant (`gateway_issued_pump_cmd`).
  2. **Echoed Command:** The command echoed back in the telemetry packet (`pkt.pump_cmd`).
  3. **Physical Actuator State:** The plant actuator state (`pkt.pump_on`, `pkt.valve_pct`) evaluated after actuator delay ($\Delta t_{pump} = 2.0\text{ s}$) and valve slew.
  4. **Physical Flowmeter Rate:** Measured inflow $Q_{in,meas}$ (e.g. $Q_{in} > 0.001\text{ m}^3\text{/s}$ confirms physical inflow while gateway commanded pump OFF).
  - *Violation Condition:* If `gateway_issued_pump_cmd == 0` but `pkt.pump_cmd == 1` OR (`pkt.pump_on == True` for $t > \Delta t_{pump}$) OR $Q_{in} > 0.001\text{ m}^3\text{/s}$, trigger `tamper_actuator_mismatch`.
- **Detection Delay Measurement:**
  - Measured from the tick the tamper is executed on the wire to the tick the 4-way consistency check flags an alert ($\le 3\text{ ticks}$).
- **Identical Physical Harm:**
  - Because wire tampering bypasses gateway commands, physical harm (overflow ticks) is **identical** in both Monitor and Prevention modes.

#### AM-4: In-Deadband Pump Toggle at Nominal Level
- **Attack Nature:** Attacker issues valid valve command ($50\%$) but rapidly toggles `pump_cmd` ($0 \leftrightarrow 1$) while the water level is nominal ($H \approx 1.0\text{ m}$, inside the $[0.8, 1.2\text{ m}]$ deadband).
- **Engine Behavior & Blind Spot:**
  - **Policy Filter / Policy v2:** Does **NOT** fire. Inside $[0.75, 1.25\text{ m}]$, both pump ON and pump OFF are legitimate controller states depending on hysteresis history.
  - **Physics Twin:** Does **NOT** fire. Telemetry faithfully echoes the toggled pump state; the twin integrates identical inflow.
  - **Temporal Engine (LSTM):** Evaluated empirically. We make no unverified claims of detection; the evaluation harness will record maximum LSTM anomaly score.

#### AM-5: In-Band Malicious Hold at Nominal Level
- **Attack Nature:** Attacker issues `pump_cmd = 1, valve_cmd = 50.0%, hold_ticks = 1200` while tank level is nominal ($H \approx 1.0\text{ m}$).
- **Ingress Filter Behavior:** At $H = 1.0\text{ m}$, pump ON is completely valid ($1.0\text{ m} \le 1.25\text{ m}$). Ingress filter allows the command.
- **Continuous Enforcement Behavior:**
  - On every simulation tick, the active hold is re-evaluated against the live level estimate $h_{est}$.
  - Tank fills at $\approx 1.16\text{ mm/s}$.
  - When $h_{est}$ crosses $1.25\text{ m}$ ($setpoint + deadband + \epsilon$), Continuous Enforcement flags a safety violation and **drops the hold** (`hold_ticks = 0`).
  - Control reverts immediately to the autonomous controller, which de-energizes the pump.
- **Pass Conditions:**
  - **Monitor Mode:** Command hold persists for 1200 s without continuous enforcement. Tank overflows in $\ge 9$ of 10 seeds ($\approx 90$ overflow ticks).
  - **Prevention Mode:** Continuous enforcement drops the hold at $H \approx 1.25\text{ m}$. Exactly **0 overflow ticks** across all 10 seeds.

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

### 3.2 New Gateway-Side Function: `evaluate_command_with_live_setpoint`

To preserve Phase 2 batch equivalence and avoid modifying existing IDS engine scoring, `PolicyEngine.evaluate_v2` is **not modified**. Instead, a dedicated gateway-side function is introduced in `GatewayCore`:

```python
def evaluate_command_with_live_setpoint(
    h_est: float,
    pump_cmd: int,
    valve_cmd: float,
    controller: Any = None,
    setpoint: float = 1.0,
    deadband: float = 0.20,
    epsilon: float = 0.05,
    default_valve: float = 50.0,
    safe_valve: float = 0.0
) -> tuple[bool, str]:
    """
    Gateway-side command validation against live controller setpoint and deadband.
    
    Safety Invariants:
    1. Pump ON is invalid if h_est > setpoint + deadband + epsilon
    2. Pump OFF is invalid if h_est < setpoint - deadband - epsilon
    3. Valve must equal default_valve_pct OR (safe_position_pct with pump_cmd == 0)
    
    Returns:
        (is_valid, rejection_reason)
    """
    if controller is not None:
        setpoint = getattr(controller, "target_level_m", setpoint)
        if hasattr(controller, "deadband_m"):
            deadband = controller.deadband_m
        elif hasattr(controller, "pump_off_threshold_m"):
            deadband = abs(controller.pump_off_threshold_m - setpoint)
        default_valve = getattr(controller, "default_valve_pct", default_valve)

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

### 3.3 Offline & Scenario Validation Matrix (Measured Numbers)

The function `evaluate_command_with_live_setpoint` was executed against all stored database scenarios via `experiments/validate_gateway_rule.py`:

| Scenario Corpus | Description | Measured Rule Violations | Scenarios Hit | Rationale & Empirical Findings |
| :--- | :--- | :---: | :---: | :--- |
| **All 60 Normal Scenarios (`N_001` to `N_060`)** | Full Phase 1 normal runs (setpoint steps, ramps, nominal cycling; 108,000 ticks) | **0 fires** | **0 / 60** | **0.000 FPR.** Normal controller commands strictly follow setpoint/deadband envelope. |
| **A1 Sensor FDI Ramp (`A1_001` to `A1_045`)** | Sensor ramp spoofing (81,000 ticks) | **1818 fires** | **35 / 45** | Post-hoc dataset artifact: `apply_fdi` added bias to observed sensor level post-simulation, pushing $H_{obs} > 1.25\text{ m}$ while recorded normal pump command was 1. |
| **A2 Sensor FDI Step/Drift (`A2_001` to `A2_015`)** | Sensor step and drift (27,000 ticks) | **0 fires** | **0 / 15** | Step offsets do not pair pump ON with observed levels above $1.25\text{ m}$. |
| **A3 DoS Telemetry Loss (`A3_001` to `A3_015`)** | Telemetry loss (27,000 ticks) | **0 fires** | **0 / 15** | Plant controller fail-safe commands (`pump=0, valve=0%`) strictly satisfy the safe valve rule. |
| **A4 Authorization Misuse (`A4_001` to `A4_015`)** | Rogue actuator commands (15 scenarios, 1,515 attack ticks) | **1515 fires** | **15 / 15** | **100.0% Detection Rate.** Exactly 101 hits in every single scenario (A4_001 to A4_015) catching rogue valve opening (80–100%) and forced pump ON. |
| **AM-1 (Overflow Misuse)** | Pump ON forced at $H = 1.30\text{ m}$ | **1 fire (100% blocked)** | **1 / 1** | $1.30\text{ m} > 1.0 + 0.20 + 0.05 = 1.25\text{ m}$. Ingress blocked. |
| **AM-2 (Dry-Run Misuse)** | Valve $90\%$ forced at $H = 0.90\text{ m}$ | **1 fire (100% blocked)** | **1 / 1** | Valve $90\% \ne 50\%$ and $\ne 0\%$. Ingress blocked. |
| **AM-3 (Wire Tamper)** | Downstream reply override | **0 fires at ingress** | **0 / 1** | Gateway issues valid commands; caught downstream by 4-way wire consistency check. |
| **AM-4 (In-Deadband Toggle)** | Rapid pump toggle at $H = 1.0\text{ m}$ | **0 fires** | **0 / 1** | $1.0\text{ m} \in [0.75, 1.25\text{ m}]$; both pump states legitimate. Documented blind spot. |
| **AM-5 (In-Band Malicious Hold)** | Pump ON held at $H = 1.0\text{ m}$ for 1200 ticks | **0 fires at ingress**; fires on hold drop when $H > 1.25\text{ m}$ | **1 / 1** | Ingress valid at $1.0\text{ m}$; continuous enforcement drops hold when level crosses $1.25\text{ m}$. |

---

## 4. API Design, Continuous Enforcement & Hold Semantics

### 4.1 Flask Route Specification (`POST /api/command`)
Implemented within the existing Flask server (`scada_live/scada_ids/server.py`):

```python
@app.route('/api/command', methods=['POST'])
def handle_command():
    data = request.get_json(force=True)
    role = request.headers.get('X-Actor-Role', 'external')
    
    # 1. Schema Validation
    pump_cmd = int(data.get('pump_cmd'))
    valve_cmd = float(data.get('valve_cmd'))
    hold_ticks = int(data.get('hold_ticks', 1))
    
    # 2. Hold Duration Cap for Non-Authenticated Sources
    if role not in ('supervisor', 'operator_auth'):
        hold_ticks = min(hold_ticks, 60)  # Max 60 ticks without re-authentication
        
    # 3. Gateway Ingress Filtering
    valid, reason = gateway.evaluate_ingress_command(pump_cmd, valve_cmd, hold_ticks, role)
    if not valid:
        return jsonify({"status": "blocked", "reason": reason}), 403
        
    return jsonify({"status": "accepted", "hold_ticks": hold_ticks}), 200
```

### 4.2 Continuous Enforcement Mechanics
1. **Per-Tick Re-Validation:**
   - On every tick $t$, if `external_override_hold_ticks > 0`:
   - Obtain best level estimate $h_{est}$ (using calibrated sensor reading or digital twin level if degraded).
   - Evaluate `evaluate_command_with_live_setpoint(h_est, held_pump_cmd, held_valve_cmd, controller)`.
2. **Hold Dropping on Violation:**
   - If evaluation returns `False`:
     - Set `external_override_hold_ticks = 0`.
     - Emit `Auth misuse` event to `EventHub` (`source: "continuous_enforcement"`).
     - Log warning: `"Continuous enforcement dropped external hold: level limit exceeded"`.
     - Immediately invoke `controller.step(h_est)` to issue legitimate autonomous commands.
3. **Resumption State Synchronization:**
   - When hold expires or drops, the autonomous controller synchronizes its internal state (`controller._pump_command = plant.pump.state`) to prevent erratic toggling.

---

## 5. EventHub & Metrics Integration (Flask Backend)

### 5.1 EventHub Alert Dispatch
When a command is blocked at ingress or dropped via continuous enforcement:
- An alert event is dispatched to the existing `EventHub`:
  ```python
  event_hub.publish({
      "event_type": "Auth misuse",
      "source": "command_filter",
      "severity": "CRITICAL",
      "timestamp": time.time(),
      "details": {
          "action": "blocked" if ingress else "hold_dropped",
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
- `commands_blocked_total`: Incremented on each ingress block.
- `holds_dropped_total`: Incremented on each continuous enforcement drop.
- Accessible via existing Flask metrics / health endpoints.

### 5.3 IDS Verdict Scoring Invariance
- Command filtering occurs at the gateway control boundary.
- Telemetry engines (`StreamingIDS`: Twin, LSTM, Availability, Policy Engine) operate unchanged on observation streams.
- IDS anomaly scores are **100% bit-for-bit identical** between Monitor and Prevention modes.

---

## 6. Experimental Design & Pass Conditions

### 6.1 Simulation Environment & Parameters
- **Horizon:** $T = 2400\text{ s}$ per run.
- **Seeds:** 10 random seeds (101 to 110).
- **Noise Setting:** `clamp_flow_noise = False`.
- **Nominal Cycling:** Steady-state cycling ($0.8\text{ m} \le H \le 1.2\text{ m}$).
- **Hold Duration:** `hold_ticks = 1200`.

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
| **AM-5 (In-Band Malicious Hold)** | Monitor | Pump ON held at $H = 1.0\text{ m}$ for 1200 ticks without continuous enforcement; tank overflows. | $\ge 1$ overflow event in $\ge 9$ of 10 seeds ($> 50$ mean overflow ticks). |
| | Prevention | Ingress allows command; Continuous Enforcement drops hold at $H > 1.25\text{ m}$; pump de-energized. | Exactly **0 overflow ticks** across all 10 seeds. |
| **Normal Soak** | Prevention | 30-minute unattacked normal cycling with legitimate commands. | Exactly **0 false blocks** and **0 false takeovers**. |

---

## 7. Step-by-Step Implementation Checkpoints (Post-Approval)

When Phase 6b is approved for implementation, execution will proceed in strict order:

### Step 1: Ingress API & Command Schema (`POST /api/command`)
- Implement Flask route handler in `scada_ids/server.py`.
- Validate schema (`pump_cmd`, `valve_cmd`, `hold_ticks`).
- Attach `X-Actor-Role` header as metadata label; cap `hold_ticks` for unauthenticated callers.
- *Test:* `test_api_command_validation.py`.

### Step 2: GatewayCore Command Pipeline, Live Validation & Continuous Enforcement
- Implement `evaluate_command_with_live_setpoint(h_est, pump_cmd, valve_cmd, controller)` in `GatewayCore`.
- Add Continuous Enforcement tick loop: re-evaluate active holds every tick, drop hold upon violation.
- Validate across all 60 normal scenarios (0 fires) and offline test suite.
- Dispatch blocked command and dropped hold alerts to `EventHub` and `MetricsCollector`.
- *Test:* `test_phase6b_command_filtering.py`, `test_ids_verdicts_identical_between_monitor_and_prevention`.

### Step 3: Wire Tamper Hook & 4-Way Actuator Consistency
- Place bus tamper injector strictly in downstream wire/reply layer (`attacker_wire/injector.py`), never inside `LivePlant` or `GatewayCore`.
- Implement 4-way consistency check comparing gateway issued command, echoed packet command, actuator state after delay/slew, and $Q_{in}$ flowmeter reading.
- Verify detection delay $\le 3\text{ ticks}$ and identical physical harm between Monitor and Prevention modes.
- *Test:* `test_tamper_consistency_check.py`.

### Step 4: A/B Verification Harness & AM-4/AM-5 Evaluation
- Implement `experiments/run_auth_misuse_ab.py` evaluating 10 seeds across AM-1, AM-2, AM-3, AM-4, AM-5.
- Verify 0 overflows/dry-runs for AM-1, AM-2, AM-5 in Prevention mode.
- Record empirical engine firing measurements for AM-4.
- Update `PROJECT_REVIEW_CHEAT_SHEET.md`.

---

## 8. Summary of Explicit Constraints
1. **NO Phase 6b code written until this plan is formally reviewed and approved.**
2. **AM-3 is strictly detect-only; gateway does not claim mitigation for bus-level tampering.**
3. **No JWT parsing; role labels are non-authoritative metrics attributes; unauthenticated holds are capped.**
4. **Pass conditions accurately reflect ODE fill and drain durations (806 s drain for AM-2, ~1078 s fill for AM-1 starting at 1.3 m, ~120 overflow ticks).**
5. **No modification of `PolicyEngine.evaluate_v2` or batch Phase 2 results; new function is strictly gateway-side.**
6. **No FastAPI/Starlette or external Prometheus client; built on Flask and internal `EventHub`/`MetricsCollector`.**
