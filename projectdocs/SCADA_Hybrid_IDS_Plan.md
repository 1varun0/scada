# SCADA Hybrid IDS: Live Simulation Design and Implementation Plan

Pre-implementation planning document for the Capstone project. It covers the architecture, components, interfaces, attack and prevention logic, demo script, build order and risks. Class and file names are placeholders; rename them to match your existing code.

## 1. Goal and Scope

**Goal:** turn the existing batch Hybrid IDS (Physics Twin + LSTM-AE + Policy + Availability, Max-Vote fusion at 0.95) into a live, real-time red-team versus blue-team demonstration.

**What the finished demo shows:**

- A running single-tank water SCADA plant that keeps going on its own.
- A **Defender console** showing tank level, pump state, four engine scores, alert banner, event log and prevention status.
- A separate **Attacker console** that launches FDI, Replay, DoS and Auth Misuse attacks and gets feedback such as 'command blocked' or 'detected'.
- Two modes: **Monitor-only** (the attack succeeds, e.g. the tank overflows) and **Prevention** (the IDS blocks or neutralises the attack and the tank stays safe).

**Out of scope (say so in the review):** real PLC hardware, real network traffic capture, multi-tank plants, retraining the LSTM.

## 2. Design Principles

1. **The plant always knows the truth.** The attacker corrupts only what travels on the wire.
2. **The IDS never sees ground truth.** Labels (attack\_active, attack\_type) go only to the metrics panel.
3. **The IDS sits in the data path** (gateway), not beside it, otherwise prevention is impossible.
4. **Attacks go through the same channels a real attacker would use**, never by editing plant variables directly.
5. **Build in layers.** Each phase must work on its own before the next one starts (see section 12).

## 3. System Architecture

Three processes plus two browser UIs:

```
  ATTACKER CONSOLE (browser, :5001)        DEFENDER CONSOLE (browser, :5000)
          |                                          ^
          v                                          | SSE
  +-----------------+   telemetry   +------------------------------+   pump cmd   +---------------+
  | attacker_wire   | ------------> |  scada_ids                   | -----------> |  plant_sim    |
  | (compromised    |               |  - Streaming IDS (4 engines) |              |  (physics +   |
  |  network node + | <-----------  |  - Alert manager             | <----------- |   actuators)  |
  |  injector)      |   feedback    |  - Prevention controller     |  raw sensor  |               |
  +-----------------+               |  - Control server (logic)    |              +---------------+
                                    +------------------------------+
```

| Process | Role | Port |
| --- | --- | --- |
| `plant_sim` | True physics, sensors, pump actuator. Source of truth. Emits one telemetry packet per tick. | 5100 |
| `attacker_wire` | Sits on the sensor-to-SCADA link and the command link. Applies active attacks to packets passing through. Serves the attacker UI. | 5001 |
| `scada_ids` | Receives (possibly tampered) telemetry, runs the IDS, runs the control logic, applies prevention, forwards pump commands, serves the defender UI. | 5000 |

Why this split: the attacker really is a separate system, the IDS is really a gateway, and each can be explained in one sentence.

## 4. Technology Choices

| Layer | Choice | Reason / alternative |
| --- | --- | --- |
| Language | Python 3.10+ | Your models and engines are already Python |
| Plant physics | Own Python integrator (Euler, dt = 1 s) | Reuses your dataset-generation physics |
| Transport v1 | HTTP/JSON between processes (Flask or FastAPI) | Easiest to debug |
| Transport v2 (upgrade) | Modbus TCP via `pymodbus` (pin the version, its API changes between releases) | Looks like real ICS traffic |
| Live push to browser | Server-Sent Events | Simple with Flask, no extra library |
| Charts | Chart.js | Already in your dashboard |
| ML inference | PyTorch, `torch.no_grad()`, model loaded once | Existing LSTM-AE |
| Storage | SQLite (events and metrics) | Already in the project |
| Packaging | A `run_all.py` launcher, optional Docker Compose later | One command to start the demo |

**Optional upgrades if time remains:** OpenPLC running the control logic, FUXA or ScadaBR as the HMI, Mininet for network-level DoS, Docker Compose to isolate the three processes.

## 5. Suggested Folder Structure

```
scada_live/
  config.yaml                # all constants: dt, thresholds, limits, ports
  run_all.py                 # starts the 3 processes
  common/
    packets.py               # Telemetry / Command dataclasses + JSON schema
    transport.py             # send/receive abstraction (HTTP now, Modbus later)
  plant_sim/
    plant.py                 # LivePlant (physics, noise, step())
    server.py                # API: /telemetry stream, /command
  attacker_wire/
    injector.py              # attack classes (FDI, Replay, DoS, AuthMisuse)
    server.py                # attacker UI + control API + wire proxy
    static/ templates/
  scada_ids/
    streaming_ids.py         # wraps the 4 engines: update(pkt)
    engines/                 # physics.py, lstm.py, policy.py, availability.py
    models/                  # trained LSTM weights, scaler, thresholds
    alert_manager.py         # NORMAL / SUSPICIOUS / ATTACK state machine
    prevention.py            # per-attack response actions
    control_server.py        # hysteresis pump control logic
    metrics.py               # ground-truth comparison, detection delay
    server.py                # defender UI + SSE + control endpoints
    static/ templates/
  tests/
    test_equivalence.py      # streaming IDS == batch IDS on same data
    test_attacks.py
  docs/
```

## 6. Component Specifications

### 6.1 Plant simulator (`plant_sim`)

- **State:** true level `h_true`, pump state, inflow `q_in`, outflow `q_out`, tick counter, simulated clock.
- **Step (per tick):** apply the latest accepted pump command, compute flows, integrate `h += dt*(q_in - q_out)/A + process_noise`, clamp to physical limits, add sensor noise to produce `h_meas`.
- **Initialisation:** use the deterministic initial state `H_0`, not a noisy reading (the bias you already fixed in the twin).
- **Safety events:** record `overflow` when level exceeds the tank maximum and `dry_run` when it falls below the minimum. These are the visible consequences of a successful attack.
- **Speed control:** a `time_scale` setting (1x real time for credibility, 5x for quick demos).
- **Output packet:** see section 7.1.

### 6.2 Attacker wire and console (`attacker_wire`)

Acts as a compromised network node between plant and SCADA. Every telemetry packet passes through `Injector.apply(pkt)`.

| Attack | Injector behaviour | Parameters on the console |
| --- | --- | --- |
| **FDI** | Reports `h_obs = h_true + bias`, or a ramp `bias(t) = rate * t` so it is stealthy. A good variant keeps the spoofed level in the normal band while the real tank fills. | bias size (m), ramp rate, duration |
| **Replay** | Records a window of N normal packets, then loops them back while real values keep moving. | window length, start delay, duration |
| **DoS** | Drops packets (`received=False`), delays them, or floods the SCADA endpoint with junk requests. | drop probability, delay (s), flood rate |
| **Auth misuse** | Sends a pump command that contradicts the control policy (e.g. pump ON at high level, pump OFF at low level) on the command path. | target state, repeat interval |

**Console UI:** attack selector, parameter sliders, Start / Stop, a live status feed (`attack sent`, `accepted`, `blocked by IDS`, `detected after X s`, `source quarantined`), and a score of damage achieved (for example maximum level reached).

**Hidden label:** each tampered packet carries `_truth = {attack_active, attack_type}` that is stripped before it reaches the IDS and sent only to the metrics module through a separate out-of-band channel.

### 6.3 Streaming IDS (`scada_ids/streaming_ids.py`)

A stateful class wrapping the four existing engines:

```python
class StreamingIDS:
    def __init__(self, cfg): ...        # load model, scaler, thresholds once
    def update(self, pkt) -> dict: ...  # one packet in, one verdict out
    def recalibrate(self, trusted_state): ...
```

Per-engine streaming notes:

- **Physics twin:** keeps its own `h_twin`, integrates `q_in` and `q_out` every tick, residual `|h_obs - h_twin|`, normalised by its threshold.
- **LSTM-AE:** `deque(maxlen=10)` of the 5 variables, scores once full, returns 0 during the 10-tick warm-up and reports a 'calibrating' flag.
- **Policy:** stateless rule checks plus the hysteresis memory (previous pump state) with the `>=` boundary fix.
- **Availability:** tracks the last timestamp, counts missed packets and repeated identical values (frozen data), and checks sequence numbers.
- **Fusion:** `hybrid = max(s_p, s_l, s_c, s_a)`, alert when `hybrid > 0.95`, plus `source_engine = argmax`.

**Acceptance test:** replaying a stored scenario through `update()` must reproduce the batch results (same scores within floating-point tolerance). Do this before anything else is built on top.

### 6.4 Alert manager (`alert_manager.py`)

```
NORMAL --(1 flagged tick)--> SUSPICIOUS --(N consecutive flags, N=3)--> ATTACK_DETECTED
   ^                              |                                           |
   +----(M clean ticks, M=5)------+                       (latched until operator acknowledges)
```

- Attack **type attribution** from the source engine: Physics -> FDI, Availability -> DoS or Replay (frozen values = Replay, missing packets = DoS), Policy -> Auth misuse, LSTM-only -> 'Anomaly (unclassified)'.
- When several engines fire, list them all and show the highest-scoring one as the primary.
- Each event is stored with: id, timestamp, state, attack type, engines, scores, and detection delay (detection time minus attack start time, from the hidden label, shown in metrics only).
- **Acknowledge and Recalibrate** button: clears the latch and calls `ids.recalibrate()`. This is the clean answer to the lingering false-positive issue in your cheat sheet.

### 6.5 Prevention controller (`prevention.py`)

Only active when the mode toggle is on **Prevention**. In **Monitor-only** it raises alerts and takes no action.

| Attack | Trigger | Response |
| --- | --- | --- |
| FDI | Physics engine latched | Control server switches its level input from the sensor to the **twin estimate**; the UI shows 'Sensor untrusted, using Digital Twin' |
| Auth misuse | Policy engine flags a command | Command is **rejected** before forwarding; the pump keeps its last safe state; the attacker console receives 'blocked' |
| DoS | Availability engine: drops or flood | Hold last good value, rate-limit or quarantine the source, apply a safe default after a timeout |
| Replay | Availability engine: frozen or repeated data, stale timestamp or sequence | Discard the stale packets and fall back to the twin |
| LSTM-only anomaly | Temporal engine alone | Alert only (no automated action), operator decides |

**Assumption to state clearly:** the twin relies on `q_in` and `q_out` being trustworthy (derived from the commands the control server itself issued). If you also let the attacker spoof flows, say that this is future work.

### 6.6 Control server (`control_server.py`)

The SCADA master. Takes the level (sensor value, or the twin estimate when prevention has overridden it) and applies the hysteresis rules, for example pump OFF above the high threshold, ON below the low threshold, with the exact deadband boundaries from your policy engine. Issues pump commands to the plant through the gateway.

### 6.7 Defender console

- **Status banner:** green NORMAL, amber SUSPICIOUS, flashing red `ATTACK DETECTED: FDI (Physics Engine)`, plus a 'Calibrating (x/10)' state at startup.
- **Level chart:** observed level, true level (revealed in a clearly labelled 'Ground truth (demo only)' toggle) and twin prediction, with the safe band shaded.
- **Four engine bars** with a threshold line at 0.95, plus the hybrid score.
- **Tank and pump graphic** (SVG) animated with level and pump state.
- **Mode toggle:** Monitor-only / Prevention.
- **Event log table:** time, type, engines, score, response taken, detection delay.
- **Controls:** Acknowledge and Recalibrate, speed selector, pause, reset scenario.
- **Metrics card:** detection delay, true detections, false alarms, missed attacks, and overflow count (compare across the two modes).

## 7. Interfaces and Data Formats

### 7.1 Telemetry packet (plant to wire to SCADA)

```json
{
  "seq": 1042,
  "ts": 1042.0,
  "received": true,
  "level_m": 1.18,
  "q_in": 0.42,
  "q_out": 0.35,
  "pump_on": true
}
```

The IDS sees exactly this. Sequence numbers and timestamps are what make Replay and DoS detectable, so include them from the start.

### 7.2 Command packet

```json
{ "seq": 77, "ts": 1042.1, "src": "scada_master | attacker", "cmd": "PUMP", "value": "ON" }
```

### 7.3 IDS verdict (pushed to the dashboard each tick)

```json
{
  "t": 1042, "level_obs": 1.18, "level_twin": 1.17, "pump": true,
  "scores": { "physics": 0.02, "lstm": 0.11, "policy": 0.0, "availability": 0.0 },
  "hybrid": 0.11, "state": "NORMAL", "attack_type": null,
  "mode": "prevention", "action": null, "calibrating": false
}
```

### 7.4 HTTP endpoints

| Process | Endpoint | Purpose |
| --- | --- | --- |
| scada\_ids | `GET /stream` | SSE feed of verdicts |
| scada\_ids | `POST /mode` | monitor or prevention |
| scada\_ids | `POST /ack` | acknowledge and recalibrate |
| scada\_ids | `POST /speed`, `/pause`, `/reset` | demo control |
| scada\_ids | `GET /events`, `/metrics` | event log and statistics |
| attacker\_wire | `POST /attack/start` | `{type, params}` |
| attacker\_wire | `POST /attack/stop` | end the attack |
| attacker\_wire | `GET /feedback` (SSE) | attack feedback messages |
| plant\_sim | `POST /command` | accepted only from the gateway |

## 8. Configuration Parameters (put all of these in `config.yaml`)

- Tank: area, max and min level, high and low control thresholds, initial level `H_0`, pump flow, outflow model.
- Simulation: `dt`, `time_scale`, noise standard deviations.
- IDS: per-engine normalisation thresholds, `tau_fusion = 0.95`, LSTM window 10, consecutive-flag count N, clear count M.
- Prevention: safe-default pump state, DoS rate limit, quarantine duration, stale-packet tolerance.
- Network: ports and addresses.

## 9. Demo Scenarios (rehearse these)

1. **Baseline:** 2 minutes of normal operation. Show green status and engine bars near zero, and point out the warm-up.
2. **FDI, Monitor-only:** attacker ramps the reported level down. The tank actually overflows. Show the red banner, the twin line diverging from the sensor, and the overflow counter.
3. **FDI, Prevention:** same attack. The twin takes over control, the tank stays safe, and the attacker console shows its damage score at zero.
4. **Auth misuse:** attacker forces the pump ON at high level. Policy fires, the command is blocked, and the attacker console shows 'command rejected'.
5. **DoS and Replay:** show the Availability engine and the different attribution (missing packets versus frozen data).
6. **Recovery:** Acknowledge and Recalibrate, then the system returns to NORMAL. Connect this to the lingering-divergence explanation.

Tip: put a scripted 'auto-demo' mode behind a button in case live clicking goes wrong during the review.

## 10. Evaluation and Metrics

- **Detection delay** per attack type (seconds from attack start to ATTACK\_DETECTED).
- **True positive rate** and **false alarm count during normal periods** (the live demo gives you a cleaner FPR than the batch numbers because of the recalibrate step).
- **Damage with and without prevention:** maximum level reached, overflow and dry-run events, time spent outside the safe band.
- **Equivalence check:** streaming results against batch results on the same scenarios.
- **Latency:** per-tick processing time (should be far below the 1 s tick).
- Run 5 to 10 repetitions per attack with randomised start times and report averages. Save a results table for the report.

## 11. Testing Plan

| Test | Pass condition |
| --- | --- |
| Streaming equals batch | Scores match on a stored scenario |
| Plant unit tests | Mass balance holds, limits are clamped, deterministic with a fixed seed |
| Each attack, Monitor-only | Detected within an agreed delay and the correct type is attributed |
| Each attack, Prevention | No overflow or dry-run, action shown in the log |
| Normal run, 30 minutes | No latched alerts |
| Restart and reset | Clean state, LSTM warm-up shown again |
| Process crash handling | Dashboard shows 'link lost' rather than freezing silently |

## 12. Build Order and Rough Timeline

| Phase | Deliverable | Done when |
| --- | --- | --- |
| 0 | `config.yaml`, packet schemas, folder skeleton | Everything imports |
| 1 | `LivePlant` stepping in the console | Level behaves like your dataset |
| 2 | `StreamingIDS` in one process, **equivalence test** | Matches batch results |
| 3 | Alert manager and event log | State transitions print correctly |
| 4 | Defender dashboard with SSE (single process, in-process attacks) | Live charts and banner work |
| 5 | Split into 3 processes with HTTP transport, add the attacker console | Attacks launched from the other UI |
| 6 | Prevention controller and mode toggle | Monitor versus Prevention contrast visible |
| 7 | Metrics, auto-demo, polish, tests | Demo script runs unattended |
| 8 (optional) | Modbus transport, OpenPLC or FUXA, Docker Compose | Only if time remains |

Phases 0 to 4 give a complete, presentable demo on their own. Phases 5 to 6 are what make it a two-sided exercise.

## 13. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Streaming results differ from batch | Equivalence test in phase 2; share the same preprocessing code |
| Twin drifts after attacks (lingering FP) | Acknowledge and Recalibrate; in prevention mode the twin is in the control loop so it stays aligned |
| Alert flicker | N-consecutive rule and hysteresis on clearing |
| Attacks too obvious or too weak | Parameterised attacks; test a stealthy ramp FDI as well as a step |
| Time lost on Modbus or Docker | Keep HTTP transport behind an interface; Modbus is an upgrade, not a dependency |
| Live demo failure | Auto-demo mode, pre-recorded backup video, fixed random seeds |
| IDS blocks legitimate operator commands | Whitelist the control server as a trusted source; log every block with its reason |
| Reviewers ask if it is just a simulation | Be upfront: state the assumptions (trusted flow signals, simulated network) and show how the transport layer can be swapped for real protocols |

## 14. Pre-Implementation Checklist

- [ ] Confirm the exact class and function names of the four engines and how to call them one row at a time.
- [ ] Confirm trained artefacts: LSTM weights, scaler, per-engine thresholds, window size.
- [ ] Extract plant constants (tank area, limits, pump flow, noise levels) into `config.yaml`.
- [ ] Decide time scale (1x or 5x) and total demo length.
- [ ] Decide the exact attack parameters for each scenario and fix the random seeds.
- [ ] Decide what the twin does after recalibration (reset to last trusted estimate or to a verified sensor reading).
- [ ] Agree the safe defaults for prevention (pump state on DoS, behaviour on stale data).
- [ ] Sketch the two UI layouts on paper before coding.
- [ ] Install and pin dependencies (Flask or FastAPI, PyTorch, Chart.js, optionally pymodbus).
- [ ] Prepare a backup recording of the demo.

## 15. Questions Reviewers May Ask

- **Why a gateway and not a passive sensor?** Prevention requires acting before a bad packet affects the plant.
- **What if the attacker also spoofs the flow measurements?** The twin would be fooled; mitigation is cross-checking with the pump state and the policy engine, and it is listed as future work.
- **How do you avoid false positives from the lingering twin divergence?** The operator recalibration step, and the twin is kept aligned in prevention mode.
- **Why max-vote fusion?** Each engine owns a distinct attack domain, and a weighted sum diluted single-engine detections (the FDI case in your cheat sheet).
- **How would this move to real equipment?** Replace the HTTP transport with Modbus/OPC UA, run the same `StreamingIDS` on a mirrored network tap or inline gateway.
