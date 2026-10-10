# Phase 3a and 3b: Gateway, Alert Manager and Metrics

Detailed implementation plan for the next two build phases. It assumes Phase 0 to 2 are done (config, packets, LivePlant, StreamingIDS with passing equivalence tests). Names follow your existing files; adjust where your code differs.

## 0. Gate: close these before coding Phase 3

The last report contains claims that are not yet backed by evidence. None of them takes long, and two affect the live demo design.

| # | Item | What to do |
| --- | --- | --- |
| 1 | **A4\_001 diagnostic is unreliable** | The script reset the twin to `0.4`, which is the *minimum* level in the data, not the scenario's initial level. A wrong start level can make the physics score fire by itself. Re-run with `get_initial_level_for_scenario('A4_001')` and report, per engine (physics, LSTM, policy, availability), how often it fires on pre-attack rows, attack rows and post-attack rows. The LSTM was not checked at all, yet the report credits it. |
| 2 | **The physics explanation looks doubtful** | The twin integrates the *observed* `q_out`. A real valve opening raises `q_out` and the level then falls consistently, so the residual should stay small. If physics really fires on A4, find out why (sensor noise, valve model mismatch, the start level). Do not repeat the 'rapid flow dynamics' explanation until it is verified. |
| 3 | **Run-switch claim is unsupported** | If each parametrized test builds its own `StreamingIDS`, nothing proves `reset()` works. Add one test: a single instance runs scenario A, then `reset()`, then scenario B (different initial level); B's scores must equal those from a fresh instance. |
| 4 | **'Golden file' is not a golden file** | The current batch loop is a re-implementation reading the database. Either call the real functions from `scripts/run_evaluation.py` or save its output once and compare against that file. Say plainly in the report which one was done. |
| 5 | **The log does not show a 100-packet push test** | The pasted run is 6 tests in `test_phase2_equivalence.py` (5 scenarios plus the soak). The Phase 3 push test does not exist yet; remove that claim. |
| 6 | **Keep the synthetic policy frame separate** | Move the hand-edited frame into its own unit test (`test_policy_streaming_parity_synthetic`) and let the A4\_001 run stay unmodified. |

**Consequence for the demo:** if the policy engine never fires on any A4 scenario, 'Auth misuse is caught by the Policy Engine' is not what your own data shows. For the live demo, design the auth-misuse attack so the policy rule really triggers (for example, force the pump ON while the level is above the high threshold, or open the valve while the level is near the low limit), and say in the review that the batch dataset's Auth Misuse detections come from other engines.

## 1. Decisions Locked for Phase 3

1. **Tick protocol: two calls per tick** (sense, then telemetry), which preserves the batch ordering and therefore your Phase 2 equivalence. The one-tick-delay variant is a possible later option, only after the 30-minute live soak proves it does not create false alarms.
2. **The gateway lives in `scada_ids/server.py`** on `cfg.network.scada_port` (5000). No new top-level `gateway.py`.
3. **The plant runs with `standalone_mode=False`** whenever a gateway is present. Exactly one controller is active at any time.
4. **Ground truth never enters the IDS path.** It travels on a separate endpoint and is read only by the metrics module.
5. **Recalibration data comes from the gateway's own buffer**, never from the browser.
6. **Phase 3 is split:** 3a is the gateway and 3b is the alert manager, truth channel and metrics.

## 2. Phase 3a: Gateway

### 2.1 Tick protocol

```
Plant tick t
  1. true_level = tank.level ; observed = noise(true_level)
  2. POST /api/sense      {run_id, seq, ts, src_t, level_m = observed}
         gateway: controller.step(observed) -> pump_cmd, valve_cmd   (reply within 0.5 s)
  3. plant applies commands, steps actuators, computes flows, steps tank
  4. POST /api/telemetry  {full packet including pump_cmd and valve_cmd}
         gateway: ids.update -> alert_manager.update -> metrics -> SSE publish
  5. POST /api/truth      {seq, run_id, true_level, attack_active, attack_type, overflow, dry_run}
         (metrics only; never passed to the IDS)
```

Rules:

- If step 2 times out or fails, the plant applies the existing fail-safe (pump OFF, valve 0%) and puts those values in the packet's `pump_cmd` and `valve_cmd`, so the IDS sees what really happened.
- Steps 4 and 5 are sent from a small background sender thread so a slow gateway cannot stretch the tick.
- In Phase 5 the attacker wire sits in front of steps 2 and 4 (FDI changes `level_m`; Replay changes `src_t`; DoS drops step 4). The plant's target URL is configurable so no code change is needed then.

### 2.2 Files

```
scada_live/scada_ids/server.py        # Flask app: routes only
scada_live/scada_ids/gateway_core.py  # GatewayCore: owns ids, controller, alert manager, metrics, lock
scada_live/scada_ids/sse_hub.py       # EventHub (bounded queues, keep-alive)
scada_live/plant_sim/gateway_client.py# sender thread + sense client used by LivePlant
scada_live/tools/watch_sse.py         # console viewer, prints verdicts and state changes
scada_live/tests/test_phase3a_gateway.py
```

Keeping the logic in `GatewayCore` (plain Python, no Flask) lets you test it directly and reuse it for the single-process dashboard in Phase 4.

### 2.3 Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/sense` | Plant sends the observed level, gateway returns `{pump_cmd, valve_cmd, run_id, mode}` |
| POST | `/api/telemetry` | Full packet for scoring. Returns `{ok, state, seq}` |
| POST | `/api/truth` | Ground truth for metrics only |
| GET | `/stream` | SSE of verdicts, first message is a snapshot |
| GET | `/api/state` | Current verdict, alert state, mode |
| GET | `/api/history?n=120` | Last n verdicts to prefill charts |
| POST | `/api/reset` | New run: resets IDS, controller, alert manager (optionally metrics) |
| POST | `/api/ack` | 3b: acknowledge and optionally recalibrate |
| POST | `/api/mode` | Reserved for Phase 6 (`monitor` or `prevention`); in 3a it only stores the value |
| POST | `/api/command` | Reserved for Phase 5/6 (rogue commands arrive here); returns 501 in 3a |

### 2.4 Shared state and locking

- `GatewayCore` holds one `threading.RLock`. Sense, telemetry, reset, recalibrate and ack all take it, so a recalibration can never happen in the middle of `ids.update()`.
- Keep the critical section short: scoring takes milliseconds; SSE publishing happens after the lock is released.
- **Run changes:** when a request carries a new `run_id`, the gateway resets the IDS (with the initial level from config), the controller's hysteresis memory and the alert manager before processing the packet.
- **Controller construction:** your `Controller` probably reads `PARAMS`, not the YAML namespace. Build it in one helper (`build_controller()`) that matches how `ProcessSimulator` builds it, and test that it makes the same decisions as the batch controller on a recorded level sequence.
- **Sequence handling:** if a telemetry `seq` is not the one the last sense call expected, count it in `sequence_anomalies` and log it. Do not crash and do not silently reorder. A packet older than the last one processed is discarded.

### 2.5 SSE hub

```python
class EventHub:
    def subscribe(self) -> Queue: ...     # Queue(maxsize=cfg.gateway.sse_queue_size)
    def unsubscribe(self, q): ...
    def publish(self, event: dict): ...   # put_nowait; if full, drop the oldest then put
```

- The stream generator waits with `q.get(timeout=15)`; on timeout it yields a comment line (`: keepalive`) so dead connections are noticed and removed.
- A guard lock protects the subscriber list. Remove the queue in a `finally` block, not only on `GeneratorExit`.
- On connect, send a snapshot (latest verdict plus alert state) first, so a refreshed browser tab is not blank.
- Keep the last `history_size` verdicts in a `deque` for `/api/history`.

### 2.6 Plant-side changes (LivePlant integration)

- `LivePlant` gets a `gateway_url` and a `run_id` (new one per start or reset).
- Split `step()` into two phases: `observe()` (read true level, add noise) and `advance(pump_cmd, valve_cmd)` (the rest). `standalone_mode=True` still runs the built-in controller between them, so Phase 1 equivalence tests keep passing unchanged.
- Use a requests `Session`, a 0.5 s timeout for sense, and a fixed-deadline loop based on `time.monotonic()`.
- `POST /speed` on the plant process forwards runtime changes of `time_scale`; the gateway's defender UI calls it in Phase 4.

### 2.7 Missed-packet watchdog

In Phase 5 a DoS will mean telemetry simply never arrives. Batch represents this as a row with `received=False`, old stale values and an old `source_time_s`. The gateway therefore needs its own clock:

- A watchdog thread checks `time.monotonic() - last_rx_wall`. If it exceeds `1.5 * dt / time_scale`, it feeds the IDS a synthetic packet: last values repeated, `received=False`, `src_t` = last real `src_t`, `ts` = previous `ts + dt`, `seq` + 1.
- If the real packet for that `seq` arrives late, it is discarded (already processed).
- Gate it with `gateway.watchdog_enabled`. Implement it and unit test it in 3a (using a fake clock); it is switched on for live runs once the wire exists.

### 2.8 Validation and errors

- Validate every field and type. Missing or malformed input returns 400 with a message, never a `KeyError`.
- Reject non-finite numbers.
- Unknown `run_id` on `/api/truth` is accepted but flagged (truth can arrive before the first packet).
- No `flask_cors`: the dashboard is served by the same app.
- Run with `debug=False, use_reloader=False, threaded=True` (the reloader loads the LSTM twice and can wipe state).

### 2.9 Config additions (`config.yaml`)

```yaml
gateway:
  sense_timeout_s: 0.5
  sse_queue_size: 200
  sse_keepalive_s: 15
  history_size: 300
  watchdog_enabled: false      # true once the attacker wire exists
  watchdog_factor: 1.5
alert:
  n_flags: 3                   # flags needed to escalate
  window_w: 5                  # ... within the last W ticks (set W = N for strictly consecutive)
  m_clear: 5                   # clean ticks to leave SUSPICIOUS
recalibration:
  n_samples: 10
  max_std_m: 0.03              # readings must be this stable to recalibrate
persistence:
  db_path: data/live_run.db    # separate from scada_ids.db
```

### 2.10 Tests (`test_phase3a_gateway.py`)

1. **Verdict parity:** push a recorded scenario through Flask's test client (sense then telemetry per tick). Verdicts must equal a direct `ids.update()` run on the same packets, and returned commands must equal the batch controller's choices.
2. **LivePlant through the gateway:** a 300-tick run ends with sane levels and no false alarms in normal operation.
3. **SSE:** two clients connect; one disconnects; the other keeps receiving; the subscriber list shrinks; a client that never reads does not grow memory beyond the queue size.
4. **Concurrency:** call reset and recalibrate repeatedly from another thread while packets arrive. No exceptions, no deadlock, and verdict sequence numbers stay monotonic.
5. **Sense failure:** gateway offline or slow, plant falls back to fail-safe and the packet records the fail-safe commands.
6. **Watchdog (fake clock):** a gap in telemetry produces a synthetic `received=False` packet and a late real packet is discarded.
7. **Validation:** malformed bodies return 400; a changed `run_id` resets state.
8. **30-minute live soak:** LivePlant plus gateway at 5x speed, count false alarms and per-request latency (target: p95 under 50 ms).

### 2.11 Acceptance criteria for 3a

| Check | Pass condition |
| --- | --- |
| Parity | Gateway verdicts and commands equal the direct batch-style run |
| Protocol | Two calls per tick work end to end, fail-safe on sense failure |
| SSE | Snapshot on connect, keep-alive, no leak with a stalled client |
| Concurrency | Reset and recalibrate under load without errors |
| Watchdog | Synthetic missed packets verified with a fake clock |
| Soak | 30 min live run, no false alarms in normal operation, p95 latency under 50 ms |
| Hygiene | Port from config, no reloader, bad input returns 400 |

## 3. Phase 3b: Alert Manager, Truth Channel and Metrics

### 3.1 Alert state machine (`alert_manager.py`)

```
NORMAL --(flag)--> SUSPICIOUS --(>= N flags in last W ticks)--> ATTACK_DETECTED (latched)
   ^                   |                                              |
   +--(M clean ticks)--+                       operator ack (/api/ack)-+--> NORMAL
```

- Input each tick: `is_anomaly`, `hybrid`, `scores`, `engines_firing`, `source_engine`, `calibrating`, `received`, `seq`.
- **Escalation:** N flags inside the last W ticks (default 3 of 5). This tolerates a one-tick gap that a strict 'N consecutive' rule would turn into a missed alert. Setting W equal to N gives strictly consecutive behaviour.
- **De-escalation:** from SUSPICIOUS, M clean ticks return to NORMAL.
- **Latch:** ATTACK\_DETECTED stays until `ack()`. While latched, the open event is updated (peak score, engines seen, last flagged time) and clean ticks are recorded but do not clear it.
- **Warm-up:** the LSTM score is 0 while calibrating, but other engines may still flag; flags during warm-up count.
- Pure Python class with no Flask or clock dependency (the tick supplies the time), so it is easy to unit test.

### 3.2 Attack type attribution

Attribution is a heuristic from engine evidence and should be labelled that way in the UI.

| Evidence | Reported as |
| --- | --- |
| Availability fires and `received=False` | DoS (packet loss) |
| Availability fires, data arrives but `src_t` is stale or repeated | Replay |
| Policy fires | Unauthorised command (Auth misuse) |
| Physics fires, nothing else | Sensor/process inconsistency (likely FDI) |
| LSTM only | Unclassified anomaly |
| Several engines | Highest-priority row above as primary, all others listed as secondary |

Because batch Auth Misuse is mostly picked up by physics (see section 0), attribution can mislabel it as FDI. Keep a confusion matrix of attributed type versus true type in the metrics and show it in the report; it is an honest result, not a defect to hide.

### 3.3 Event record

One record per alert episode: `event_id`, `run_id`, `first_flag_seq`, `detected_seq`, `detected_ts`, `primary_type`, `engines` (all seen), `peak_hybrid`, `peak_by_engine`, `action_taken` (empty until Phase 6), `acknowledged_ts`, `ack_recalibrated` (bool), plus `closed_reason`.

### 3.4 Truth channel

- `POST /api/truth` receives `{run_id, seq, true_level, attack_active, attack_type, overflow, dry_run}` and writes only to the metrics collector. No IDS or alert-manager code path reads it (cover with a test that greps imports or monkeypatches the collector).
- In Phase 5 the attacker wire becomes the source of `attack_active` and `attack_type`, and the plant keeps sending `true_level` and safety flags.
- Truth can arrive slightly before or after the packet; the collector joins on `(run_id, seq)` and tolerates a missing side.

### 3.5 Metrics (`metrics.py`)

Compute both episode-level and tick-level numbers.

**Episode level (for the demo):**

- *Time to first flag* and *time to ATTACK\_DETECTED*, each measured from the true attack start.
- *Detected attack:* ATTACK\_DETECTED reached while the attack is active or within grace period G (config, default 10 s) after it ends.
- *Missed attack:* attack episode with no detection.
- *Spurious alert:* ATTACK\_DETECTED with no attack active and outside the post-attack window.
- *Lingering alert:* ATTACK\_DETECTED raised or kept after an attack ended (the twin divergence case). Report it separately; do not fold it into false alarms silently.

**Tick level (for comparison with your batch table):** precision, recall, F1 and FPR from per-tick flags versus truth, so the live numbers line up with the 99.8% recall and 38.9% precision in the cheat sheet.

**Safety and damage (the Phase 6 headline numbers):** overflow *events* (rising edges) and *ticks* above the critical-high limit, dry-run events and ticks below the critical-low limit, maximum and minimum true level, and time outside the safe band.

**Operator errors:** count recalibrations performed while an attack was actually active (known from truth only).

### 3.6 Acknowledge and recalibrate

```
POST /api/ack  {recalibrate: true|false}
```

- Ack is always allowed; the operator decides. (A rule such as 'only after M clean ticks' would deadlock in monitor-only mode, because after an attack the twin itself is what stays flagged.)
- If `recalibrate` is true, the gateway takes the **last `n_samples` observed levels from its own buffer**. It rejects with 409 `sensor_unstable` if their standard deviation exceeds `max_std_m` (the level is mid-ramp) or any are outside physical bounds. Otherwise it calls `ids.recalibrate(levels)`, which also clears the LSTM window.
- **Important caveat:** recalibration trusts the current sensor readings. If an FDI is still active, the twin will resync to the spoofed level and the physics engine will go quiet. That is why this is an operator action, why the UI must say 'Recalibrating trusts current sensor readings', and why the metrics count recalibrations made during a live attack.
- If the attack is still going after ack, the engines fire again and the alert re-latches within N ticks; the event log shows that as a new event.
- After recalibration the LSTM is blind for 10 ticks. Expose `recalibrating_ticks_left` in the verdict so the dashboard shows it.

### 3.7 Persistence

Write events and a per-tick compact log to `data/live_run.db` (new tables `live_events`, `live_ticks`), not to `scada_ids.db`, which holds your batch evidence. Write on a background thread in batches so SQLite never slows the tick. `/api/events` reads from memory with the DB as backup.

### 3.8 Endpoints added in 3b

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/events` | Event log (newest first, optional `run_id`) |
| GET | `/api/metrics` | Current episode-level and tick-level metrics, confusion matrix |
| POST | `/api/ack` | Described above |
| POST | `/api/truth` | Described above |

The SSE verdict gains `alert_state`, `attack_type`, `engines_firing`, `latched`, `recalibrating_ticks_left`, `pump_cmd`, `valve_cmd`, `mode`.

### 3.9 Tests (`test_phase3b_alert_metrics.py`)

1. **State machine table test:** scripted flag sequences (single blip, 3 of 5, gap inside the window, long attack, flicker) and expected states.
2. **Latch and ack:** the alert stays latched through clean ticks and clears only on ack; re-latches if flags continue.
3. **Attribution table:** each evidence row from 3.2 produces the expected type, including the multi-engine case.
4. **Replay through the gateway:** feed the stored FDI, Replay and DoS scenarios; the right event appears with a sensible detection delay.
5. **Metrics correctness:** a hand-built truth/flag sequence with known answers for delay, detected, missed, spurious and lingering counts.
6. **Truth isolation:** the IDS output is identical whether or not truth messages are sent.
7. **Recalibration:** accepted on stable data, 409 on a ramp, operator-error counter increments if an attack was active.
8. **Normal 30-minute run:** no events.

### 3.10 Acceptance criteria for 3b

| Check | Pass condition |
| --- | --- |
| State machine | All scripted sequences give the expected transitions |
| Latch | Cleared only by ack; re-latches on continued flags |
| Attribution | Table behaviour verified; confusion matrix produced |
| Metrics | Hand-checked scenario matches expected counts |
| Truth isolation | IDS verdicts unchanged with or without truth |
| Recalibration | Stability check works; operator-error count works |
| Persistence | Events and ticks stored in `live_run.db` without affecting latency |

## 4. Build Order Inside Phase 3

1. Close the section 0 items.
2. `GatewayCore` plus `EventHub` with unit tests (no Flask).
3. Flask routes and `LivePlant` split into `observe()` and `advance()`; run the parity test.
4. Watchdog with a fake clock.
5. Alert manager (pure class and table tests).
6. Truth channel and metrics collector.
7. Ack and recalibration, persistence.
8. `watch_sse.py` console viewer, then the 30-minute soak at 5x.

Phase 4 (the defender dashboard) then only needs to consume `/stream`, `/api/events`, `/api/metrics` and the control endpoints.

## 5. Risks

| Risk | Mitigation |
| --- | --- |
| Gateway-added timing differs from batch order | Two-call protocol, parity test, soak test |
| Controller built differently from batch | One `build_controller()` helper plus a decision-equivalence test |
| Twin trusts a spoofed level after recalibration | Operator-only action, UI warning, operator-error metric |
| Alert flicker or missed intermittent attacks | N-of-W rule, tested with scripted sequences |
| Slow client blocks the stream | Bounded queues with drop-oldest and keep-alives |
| Attribution confusion for Auth Misuse | Report it openly, design the live attack to trigger policy, show the matrix |
| SQLite writes slow the loop | Background batch writer, separate database |
