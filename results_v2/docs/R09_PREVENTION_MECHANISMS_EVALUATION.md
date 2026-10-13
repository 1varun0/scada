# R09: Prevention Mechanisms & Active Defense Evaluation

## 1. Active Defense Architecture Overview

In contrast to passive intrusion detection systems that merely alert operators, the SCADA Hybrid IDS implements four autonomous active prevention mechanisms within [`scada_live/scada_ids/gateway_core.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/gateway_core.py):

```
                                  Telemetry Flow
                 ┌──────────────────────────────────────────────┐
                 │                                              │
┌──────────────┐ │ ┌──────────────────┐  ┌──────────────────┐  │ ┌──────────────┐
│ Plant Sensor │─┴─► Ingress Filter   ├──► Digital Twin     ├──┴─► Closed-Loop  │
│ Telemetry    │   │ (Envelope Check) │  │ Takeover/Handback│    │ Controller   │
└──────────────┘   └──────────────────┘  └──────────────────┘    └──────┬───────┘
                                                                        │
                                Actuator Commands                       │
                 ┌──────────────────────────────────────────────┐       │
                 │                                              │◄──────┘
┌──────────────┐ │ ┌──────────────────┐                         │
│ Plant Pump & │◄┴─┤ 4-Way Actuator   │◄────────────────────────┘
│ Valve Wire   │   │ Consistency Check│
└──────────────┘   └──────────────────┘
```

---

## 2. The Four Autonomous Prevention Mechanisms

### Mechanism 1: Digital Twin Takeover (Sensor Attack Mitigation)
- **Trigger**: Asserted when the fused score triggers `CRITICAL` state ($3\text{-of-}5$ sliding window).
- **Action**: The gateway decouples the closed-loop controller from spoofed physical sensors and routes the Digital Twin state estimate $\hat{h}_{\text{twin}}$ into controller logic.
- **Physical Invariant**: Mass conservation $\frac{d\hat{h}}{dt} = \frac{Q_{\text{in}} - Q_{\text{out}}}{A}$ tracks the true plant level accurately using measured flowmeter telemetry.

### Mechanism 2: Automatic Safe Handback Gating
- **Problem**: Abruptly switching control authority back to the sensor after attack cessation can cause sudden controller jumps or re-trigger alarms.
- **Handback Conditions**:
  1. Residual $|H_{\text{obs}} - \hat{h}_{\text{twin}}| \le \epsilon_{\text{handback}} = 0.05\text{ m}$ ($5\text{ cm}$).
  2. Physical residual remains clean for at least 10 consecutive ticks.
  3. Operator has acknowledged the incident (or `auto_handback == True`).
- **Result**: Zero level discontinuities or controller bumps upon attack termination.

### Mechanism 3: Ingress Command Filtering & Continuous Hold Enforcement
- **Ingress Filtering**: Rejects malformed JSON, out-of-bounds parameters, and unauthorized roles via HTTP 403 Forbidden.
- **Continuous Hold Dropping**: If an attacker gains valid credentials and issues an in-band override command (e.g., pump ON for 1500 ticks), the gateway continuously monitors plant level at every step. If $H_{\text{obs}}$ breaches $1.25\text{ m}$ (upper envelope) or $0.75\text{ m}$ (lower envelope), the hold is immediately dropped and autonomous control resumes.

### Mechanism 4: Actuator 4-Way Consistency Check (Downstream Wire Tampering)
- **Problem**: Attackers with physical access can tamper with wire control lines downstream of the gateway, executing rogue actuator actions.
- **Consistency Rule**: Compares commanded state (`pump_cmd`, `valve_cmd`) against measured physical response over a 3-tick sliding window.
- **Detection**: If the plant actuates while the gateway commanded OFF for 3 consecutive steps, a high-severity `ACTUATOR_TAMPER_ALERT` is emitted within $\le 3$ ticks.

---

## 3. Empirical Verification: Phase 6b A/B Evaluation (AM-1 – AM-7)

Evaluated across 10 evaluation seeds (101 to 110) comparing Monitor Mode against Prevention Mode ([`t10_auth_misuse_prevention_ab.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t10_auth_misuse_prevention_ab.md)):

| Threat Scenario | Attack Description | Monitor Mode Harm | Prevention Mode Harm | Prevention Outcome |
| :--- | :--- | :---: | :---: | :---: |
| **AM-1** | Overflow Misuse (Pump Latched ON at 1.30m) | 121.0 overflow ticks | **0.0 overflow ticks** | ✅ 100% Blocked at Ingress |
| **AM-2** | Dry-Run Misuse (Valve Latched 90% at 0.90m) | 151.0 dry-run ticks | **0.0 dry-run ticks** | ✅ 100% Blocked at Ingress |
| **AM-3** | Wire / Fieldbus Tamper (Actuator Hijacked) | 58.0 overflow ticks | **58.0 overflow ticks** | ✅ Fast Alert (Harm Invariant) |
| **AM-4** | In-Deadband Pump Toggle (Hysteresis Band) | 0.0 overflow ticks | **0.0 overflow ticks** | ✅ Quiescent in Deadband |
| **AM-5** | In-Band Hold - Filling (Pump ON, 1500s Hold) | 211.0 overflow ticks | **0.0 overflow ticks** | ✅ Dropped at Safety Boundary |
| **AM-6** | In-Band Hold - Draining (Pump OFF, 1800s Hold)| 1.0 dry-run tick | **0.0 dry-run ticks** | ✅ Dropped at Safety Boundary |
| **AM-7** | Unauthenticated Hold Cap (1500s $\rightarrow$ 60s) | 0.0 overflow ticks | **0.0 overflow ticks** | ✅ Capped to 60s Safely |

---

## 4. The Physical Invariance of Wire Tampering (AM-3)

A vital theoretical and practical insight proven by scenario AM-3:
- In both Monitor Mode and Prevention Mode, physical overflow harm is **identical (58.0 ticks)**.
- **Explanation**: Downstream wire tampering bypasses the network gateway entirely; the physical wire to the pump is directly manipulated on the plant floor.
- **Conclusion**: Software ingress filtering and gateway takeover can protect against cyber-borne commands, but physical downstream tampering requires hardwired physical safety relief valves and electromechanical interlocks. The gateway successfully detects tampering in **0 ticks** with 17 alerts, alerting plant operators to dispatch physical security.
