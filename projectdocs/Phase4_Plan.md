# Phase 4 (Revised): Defender Dashboard, Demo Runner and Injector

This plan replaces the earlier Phase 4 draft. It keeps the dashboard goals but fixes the data path, the injector placement, the truth channel, the history source and the tests, and it adds a gate of checks that must be closed before building.

## 0. Gate: close these before building

### 0.1 Reconcile the evaluation numbers

The latest recomputation (A4\_001: F1 0.22, precision 0.13, recall 1.00) conflicts with the cheat sheet (per-attack F1 1.000). Neither is 'wrong' until the definitions are compared, and the agent's script has weaknesses of its own.

- **Find the cheat sheet's definition.** Look in `scripts/run_evaluation.py` (or whichever script produced the per-attack table): which rows count (attack window only, attack scenarios only, all ticks), and whether normal-scenario ticks enter the denominator.
- **Use each scenario's own `ground_truth` column** to find attack start and end. The last script hard-coded 200 to 300 s for every attack type, which may be wrong for FDI, Replay and DoS.
- **Produce one table:** attack type x phase (pre, during, post, plus the N scenarios) x engine, with tick counts of rows above 0.95 and rows flagged by fusion. Print the actual output, not a summary.
- **Test the start-up idea, do not assume it.** The LSTM flags A4 from t = 9 s to about 113 s. Compare the initial level of A4 scenarios with the normal scenarios (for instance if A4 starts low and normal runs start at 1.0 m, the LSTM is seeing data unlike its training set), and check whether the N scenarios show LSTM flags at all.
- **Then correct the documents.** The cheat sheet says false positives occur only after attacks. If pre-attack LSTM flags exist, that sentence is false and must change. Report both tick-level and episode-level numbers with their definitions. Do not edit the stored batch results; live numbers are reported separately.

### 0.2 Verify policy v2, do not assume it

The rule as described reads backwards ('pump ON when level > 1.2 + epsilon'). The violations should be:

- pump command **ON** while the observed level is **above** the OFF threshold plus epsilon;
- pump command **OFF** while the observed level is **below** the ON threshold minus epsilon.

The A4 attack is a **valve** command (`VALVE_SET_80`), which a pump-only rule never catches. Add a valve rule: the valve command must be one of the values the legitimate controller can issue (default position, fail-safe position, any documented override). Confirm the exact set in `controller.py`.

| Check | Pass condition |
| --- | --- |
| Direction | Unit tests for both violation directions and the boundary values (`>=` versus `>`) |
| Silent on normal | Zero v2 fires on every N scenario and on the pre-attack part of A1 to A4 |
| Catches the attack | v2 fires on A4 attack ticks, and on a pump-forced-ON test frame |
| Batch untouched | `evaluate()` (v1) unchanged and the Phase 2 equivalence tests still green |
| Scoped | A config flag (`ids.policy_version`) selects v2 for the live system only; batch results stay on v1 and the two are reported separately |

Expected behaviour to explain in the review: the controller derives its commands from the observed level, so an FDI changes the level the controller sees and policy stays quiet. Policy only catches commands that contradict the control logic for the level that was observed.

### 0.3 Evidence

The log shows edits to `policy_engine.py`, `gateway_core.py` and the tests, but no test run afterwards. Run `pytest -v` over all phases (0, 1, 2, 3a, 3b) and paste the full output, together with `git status`, before starting Phase 4.

## 1. Goals and Scope

- A real-time Defender Dashboard served by the gateway on `127.0.0.1:5000`.
- A single-process **demo runner** that still sends every packet over loopback HTTP, so the Phase 5 split needs no protocol change.
- A plain-logic **injector** (FDI, Replay, DoS, Auth misuse) that Phase 5 later wraps in its own Flask app.
- A temporary demo-attack panel, hidden once the attacker console exists.
- The old batch dashboard stays available (mounted at `/batch` or another port); it is evidence for your batch results.

## 2. Architecture of the Demo Runner

```
run_demo.py (one process, three threads)

  LivePlant thread  --HTTP-->  Injector (in the client path)  --HTTP-->  Gateway server (Flask thread, :5000)
        ^                          |                                           |
        |                          +-- truth (attack_active, type) ----------->| /api/truth (metrics only)
        +-------- commands in the /api/sense reply <---------------------------+
```

- `run_demo.py` starts the gateway server in a thread, then the plant loop. The plant uses the existing `GatewayClient` pointed at `http://127.0.0.1:5000`.
- The **injector wraps `GatewayClient`** (sense and telemetry calls). In Phase 5 the same class moves into the attacker process unchanged.
- Everything binds to `127.0.0.1`. Run Flask with `debug=False, use_reloader=False, threaded=True`.
- `PlantControl` is a small interface owned by the runner (pause, resume, set speed, reset). The gateway never holds a reference to the plant; in Phase 5 the same interface is implemented over HTTP.

## 3. Injector Specification

The injector sits between plant and gateway on both calls. It never edits plant variables directly.

| Attack | Sense call (`level_m` out, commands back) | Telemetry call | Truth it reports |
| --- | --- | --- | --- |
| **FDI** | Replaces `level_m` with `true + bias` or a ramp (`rate * t`) | Same spoofed `level_m` (sense and telemetry must agree) | attack\_active, type FDI, bias value |
| **Replay** | Sends recorded old `level_m` | Re-sends recorded packets with their **old `src_t`** while `ts` keeps moving | type Replay |
| **DoS** | Optional: drop to trigger the plant's fail-safe | Drops the call (the gateway watchdog synthesises `received=False`) | type DoS |
| **Auth misuse** | Overrides the command in the reply (pump forced ON above the OFF threshold, or valve set to an unauthorised position); the plant executes it | The packet carries the rogue `pump_cmd` or `valve_cmd` so the policy engine sees it | type Auth misuse |

Rules:

- Attack parameters: type, start time or 'now', duration, magnitude (bias or ramp rate, record window length, drop probability, target command).
- **Truth ownership:** the injector reports `attack_active` and `attack_type`; the plant reports `true_level`, overflow and dry-run flags. `/api/truth` accepts partial records and merges them on `(run_id, seq)`.
- Provide a **stealthy FDI variant** that keeps the spoofed level inside the normal band while the real level drifts, to show the twin's value.
- Provide the auth-misuse design that triggers policy v2 (pump ON above threshold, or valve override) as well as the A4-style valve command, and record which engine catches each.
- Injector unit tests use a fake plant and a fake gateway: each attack changes only the fields in the table above.

## 4. Server APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Defender dashboard |
| GET | `/stream` | SSE verdicts (no ground truth) |
| GET | `/api/config` | Tank limits (critical low and high, overflow, controller thresholds), alert settings, `time_scale`, `demo_mode` |
| GET | `/api/state` | Current alert state, active event, mode, calibrating info, paused flag |
| GET | `/api/history?n=300` | Last n **verdicts** (level\_obs, level\_twin, scores, alert state, commands), taken from the verdict history deque, not the level buffer |
| GET | `/api/events`, `/api/metrics` | From Phase 3b |
| POST | `/api/ack` | Acknowledge, optional recalibrate |
| POST | `/api/control/speed`, `/pause`, `/resume`, `/reset` | Routed to `PlantControl`; the gateway also updates its own paused flag and watchdog |
| GET | `/demo/truth/stream` | Demo-only SSE with `true_level` and attack truth; returns 404 unless `demo_truth_enabled` |
| POST | `/demo/attack/start`, `/demo/attack/stop` | Demo attacks; 404 unless `demo_mode` is on |

Behaviour requirements:

- **Pause** sets the gateway's paused flag so the watchdog does not synthesise missed packets and the alert manager does not count time. **Resume** clears it.
- **Speed change** updates `time_scale` where the watchdog reads it (read the live value on every check, never a copy).
- **Reset** starts a new `run_id`, resets IDS, controller, alert manager and the history deque, and the UI clears its chart after a confirm dialog.
- `/stream` must never carry truth fields; a test checks the stream payload keys.

## 5. Front-End Specification

### 5.1 Layout

One page, dark theme: status banner on top, left column with tank and pump SVG plus the engine bars, centre with the level chart, right column with the event log and metrics, bottom strip with controls.

### 5.2 Status banner and acknowledge flow

- Alert states `SAFE` (green), `SUSPICIOUS` (amber, slow pulse), `CRITICAL` (red, slow pulse). Always show the state as text as well as colour.
- **Calibrating** is a separate blue badge using `calibrating` and `recalibrating_ticks_left`. A latched CRITICAL banner is never replaced by the badge.
- The banner shows attack type (labelled 'likely'), engines firing and time since detection.
- **Acknowledge dialog:** shows type, engines and event time; states 'Recalibrating trusts current sensor readings'; offers 'Acknowledge' and 'Acknowledge and recalibrate'; shows a readable message for `409 sensor_unstable`; the button is disabled when nothing is latched.
- Respect `prefers-reduced-motion`; no fast flashing.

### 5.3 Level chart

- Chart.js **vendored locally at a pinned version** (no CDN, so a venue network failure cannot break the demo). Use an index or category axis so no date adapter is needed.
- Fixed-length buffers (for example 300 points), `animation: false`, and updates batched per animation frame.
- Series: observed level, twin level, shaded safe band and critical lines from `/api/config`. Optional 'Ground truth (demo only)' series fed by the demo truth stream, off by default.
- Mark detection and acknowledge moments with vertical lines.

### 5.4 Engine scores

Four bars (physics, LSTM, policy, availability) with the 0.95 threshold line, the hybrid score, and the firing engines highlighted. Show 'calibrating' on the LSTM bar while its window fills.

### 5.5 Process view

Inline SVG (not an `<img>`): tank with level fill bound to `level_obs`, critical-low and critical-high lines, pump shown with commanded versus actual state, valve with position percent. Optionally a faint marker for the twin level.

### 5.6 Event log, metrics and controls

- Event log built with `textContent` only, newest first, with type, engines, time and detection delay.
- Metrics card from `/api/metrics`: detection delay, detected, missed, spurious and lingering counts, overflow events, ticks outside the safe band.
- Controls: pause or resume, speed (1x, 5x), reset with confirm, presentation mode (larger text and contrast).
- Monitor/Prevention toggle shown **disabled** and labelled 'Phase 6'.

### 5.7 Robustness

- **Link lost:** if no SSE message arrives for about 3 seconds (scaled by speed), show an overlay; on reconnect, refetch `/api/history` and `/api/state` and rebuild the chart.
- Prefill from `/api/history` on page load so a refreshed tab is not blank.
- Escape all server text; no `innerHTML` with server data.

### 5.8 Temporary demo attack panel

Shown only when `demo_mode` is on: attack selector, parameter inputs, start and stop, current attack status. Remove it (or hide it behind the flag) when the Phase 5 attacker console arrives.

## 6. Baseline and Expectations for the Demo

- The live plant starts at the normal initial level (1.0 m) and runs a baseline of several minutes before any attack.
- Record the number of alerts in that baseline. If the LSTM flags during start-up (see 0.1), choose one of these and state it openly in the review: a live-only start-up grace period configured in the gateway (batch results untouched), or documenting it as a known limitation. Do not hide it by changing thresholds.
- Run each attack at least 5 times with randomised start times and keep the results table (detection delay, engines that fired, attribution result) for the report.

## 7. Tests

| Test | What it proves |
| --- | --- |
| Route tests | `/api/config`, `/api/state`, `/api/history` return the documented schema, including the empty state before any packet |
| Stream payload | `/stream` events never contain truth fields; the demo truth stream is 404 when disabled |
| Demo gating | Attack endpoints return 404 when `demo_mode` is off |
| Injector unit tests | Each attack changes only the fields in section 3 |
| Pause and speed | While paused no synthetic missed packets or alerts appear; the watchdog timeout follows speed changes (fake clock) |
| Attack-to-ack flow | Over loopback HTTP: attack starts, CRITICAL is latched with the right type, ack clears it, a continuing attack re-latches |
| HTTP soak | 30 minutes at 5x over HTTP: p95 request latency under 50 ms, zero alert events on the normal baseline, flat memory |
| Reconnect | Restarting the gateway or dropping the connection recovers without a page reload |

Manual checklist: no console errors, projector readability in presentation mode, behaviour at 1x and 5x, browser and screen size used for the review, flat browser memory over a long run.

## 8. Build Order

1. Close the section 0 gate.
2. Injector as plain logic with unit tests.
3. `run_demo.py` with loopback HTTP and `PlantControl`; run the HTTP soak with no UI.
4. New API routes (`/api/config`, `/api/state`, `/api/history`, control and demo routes) with tests.
5. Static page: banner, engine bars and SSE wiring.
6. Chart, SVG, event log and metrics.
7. Ack dialog, link-lost handling, presentation mode.
8. Demo attack panel, attack runs and the results table.

## 9. Acceptance Criteria

- [ ] Section 0 items closed with printed evidence (reconciled metrics table, policy v2 checks, full `pytest -v` and `git status`).
- [ ] Dashboard loads on `127.0.0.1:5000` with no console errors and no external network requests.
- [ ] Each of the four demo attacks drives SAFE, then SUSPICIOUS, then CRITICAL with a labelled likely type, and ack works (including the 409 message).
- [ ] `/stream` carries no ground truth; the truth toggle works only in demo mode.
- [ ] Pause, speed change, reset and link recovery behave as specified.
- [ ] 30-minute HTTP soak at 5x: p95 under 50 ms, flat memory, no alerts on the normal baseline (or the start-up behaviour documented as in section 6).
- [ ] The old batch dashboard is still reachable.

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Published metrics do not match the data | Reconcile and correct the cheat sheet before the review; show both definitions |
| Policy v2 is wrong or too noisy | Direction, boundary and silent-on-normal tests; scoped to the live system |
| LSTM start-up flags spoil the live baseline | Baseline run, explicit decision in section 6, no threshold tuning to hide it |
| Pause or speed changes look like DoS | Paused flag and live `time_scale` in the watchdog, with tests |
| UI memory growth | Fixed buffers, no animation, 30-minute soak |
| Venue network failure | Vendored Chart.js, loopback only |
| Injector and plant disagree on truth | Merge partial truth records on `(run_id, seq)` and test it |
