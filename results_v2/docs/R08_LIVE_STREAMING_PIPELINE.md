# R08: Live Streaming Pipeline & Gateway Architecture

## 1. System Topology & Process Boundaries

The live simulation deployment operates as a decoupled, multi-tier streaming system designed to mirror an industrial SCADA architecture:

```
┌─────────────────┐       ┌─────────────────┐       ┌────────────────────────┐
│    LivePlant    │       │ Attacker Wire   │       │      GatewayCore       │
│  (Physical Sim) │◄─────►│    Injector     │◄─────►│   (IDS / Prevention)   │
└─────────────────┘       └─────────────────┘       └───────────┬────────────┘
                                                                │
                                                     SSE Event  │ HTTP REST
                                                     Broadcaster│ Endpoints
                                                                ▼
                                                    ┌────────────────────────┐
                                                    │ Dashboard UI / Clients │
                                                    └────────────────────────┘
```

---

## 2. The Two-Call Gateway Protocol

Industrial control requires actuator commands to be calculated *before* the plant advances to the next timestep. The system resolves this via a deterministic two-call HTTP protocol:

1. **Phase 1: Sense (`POST /api/sense`)**
   - The plant submits the freshly measured water level $H_{\text{obs}}$ (or attacker-modified reading).
   - `GatewayCore` updates its Digital Twin state estimate $\hat{h}_{\text{twin}}$.
   - If **Prevention Mode** is active and Twin Takeover is asserted, the gateway substitutes $\hat{h}_{\text{twin}}$ in place of $H_{\text{obs}}$.
   - The controller determines optimal actuator commands (`pump_cmd`, `valve_cmd`) and returns them in the HTTP 200 response.

2. **Physical Step**: The plant applies the commands, advances by $\Delta t = 1.0\text{ s}$, and produces physical flow rates $Q_{\text{in}}$ and $Q_{\text{out}}$.

3. **Phase 2: Telemetry (`POST /api/telemetry`)**
   - The plant submits the complete executed `TelemetryPacket` containing actuator states (`pump_state`, `valve_state`), flow rates, timestamp, and sequence counter.
   - `GatewayCore` passes the packet into `StreamingIDS`.
   - All 4 evidence engines ($S_p, S_l, S_c, S_a$) evaluate the packet and emit a fused anomaly score $S_{\text{hybrid}}$.

---

## 3. Availability Watchdog Timer

To prevent unmonitored plant drift during network outages or packet floods:
- A dedicated background watchdog thread monitors packet arrival intervals.
- **Timeout Threshold**: $\tau_{\text{watchdog}} = 1500\text{ ms}$ (1.5 ticks).
- **Synthetic Packet Synthesis**: If the inter-packet gap exceeds 1500 ms, the watchdog synthesizes an availability outage packet with `packet_received = 0` and increments `data_age_ms`.
- **Failsafe Assertion**: The controller automatically commands `pump_command = 0` and `valve_command = 0%` to prevent tank overflow or dry-run during communication loss.
- **Takeover Suppression**: Digital Twin takeover is explicitly suppressed during DoS outages to prevent model divergence without real flowmeter feedback.

---

## 4. Alert State Machine & Sliding Window Latching

To prevent transient high-frequency noise spikes from causing operator alert fatigue, `GatewayCore` utilizes a sliding $N$-of-$W$ window alert manager ([`scada_live/scada_ids/alert_manager.py`](file:///c:/projects/p1/New%20folder/scada_live/scada_ids/alert_manager.py)):
- **Window Width ($W$)**: 5 consecutive timesteps.
- **Trigger Threshold ($N$)**: 3 positive anomaly scores ($S_{\text{hybrid}} > 0.95$).
- **State Progression**:
  - `NORMAL`: 0–2 flags in window.
  - `WARNING`: Initial anomaly flag detected.
  - `CRITICAL`: 3 out of 5 ticks flagged. In Prevention Mode, this state immediately triggers **Twin Takeover**.
- **Alert Latching**: Once `CRITICAL` is reached, the state latches until an operator acknowledges the condition via `POST /api/ack` or automatic handback criteria are fully satisfied.
