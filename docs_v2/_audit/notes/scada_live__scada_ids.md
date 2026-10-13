# Source File Note: scada_live/scada_ids/ Core Components

## 1. Purpose
Implements the core live detection and prevention pipeline: stateful detection streaming (`streaming_ids.py`), alert state machine (`alert_manager.py`), centralized gateway coordination and safety enforcement (`gateway_core.py`), HTTP/SSE server (`server.py`), SSE fanout hub (`sse_hub.py`), SQLite persistence (`db_writer.py`), live metrics aggregation (`metrics.py`), and the defender web UI [CODE scada_live/scada_ids/gateway_core.py:1-20, scada_live/scada_ids/server.py:1-17].

## 2. Public Classes / Functions
### `streaming_ids.py`:
- `class StreamingIDS` [CODE scada_live/scada_ids/streaming_ids.py:26-306]:
  - `__init__(cfg, device="cpu", policy_version=None, dos_gap_rule=None)`: Loads `PhysicsEngine`, `PolicyEngine`, `AvailabilityEngine`, `TemporalEngine` (with `LSTMAutoencoder` and scaler), and `FusionEngine`. Computes physical bounds $v_{\max} = \max(Q_{in,\max}/A, C_v \sqrt{H_{\max}}/A) \approx 0.003162\text{ m/s}$ [CODE scada_live/scada_ids/streaming_ids.py:62].
  - `update(pkt: TelemetryPacket) -> dict` [CODE scada_live/scada_ids/streaming_ids.py:147-305]: Computes scores $S_p, S_l, S_c, S_a, S_{\text{hybrid}}$, anomaly verdict, engines firing. Implements Step 2b DoS gap rule re-seed logic [CODE scada_live/scada_ids/streaming_ids.py:168-222].
  - `recalibrate(trusted_levels: list[float])`: Resets digital twin level to mean of trusted readings.
  - `get_twin_estimate() -> float`: Returns current water level estimated by the physics Digital Twin.

### `alert_manager.py`:
- `class AlertManager` [CODE scada_live/scada_ids/alert_manager.py:1-114]:
  - States: `SAFE`, `SUSPICIOUS`, `CRITICAL` [CODE scada_live/scada_ids/alert_manager.py:2-4].
  - N-of-W sliding window: transitions to `CRITICAL` when flags in window $\ge N$ (default 3 of 5). Latches in `CRITICAL` until acknowledged [CODE scada_live/scada_ids/alert_manager.py:75-91].
  - Heuristic root-cause attribution in `_attribute_type()`: assigns "Wire tamper", "DoS", "Replay", "Auth misuse", "Sensor/process inconsistency", or "Unclassified anomaly" [CODE scada_live/scada_ids/alert_manager.py:28-52].

### `gateway_core.py`:
- `evaluate_command_with_live_setpoint(h_est, pump_cmd, valve_cmd, controller, epsilon=0.05, safe_valve=0.0) -> (bool, str)` [CODE scada_live/scada_ids/gateway_core.py:22-66]: Gateway ingress safety validation enforcing valve defaults and dynamic pump deadband limits ($H \le 0.75\text{ m}$ for pump OFF, $H \ge 1.25\text{ m}$ for pump ON).
- `class GatewayCore` [CODE scada_live/scada_ids/gateway_core.py:68-502]:
  - `process_sense(level_m)` [CODE scada_live/scada_ids/gateway_core.py:249-335]: Feeds level to controller. In prevention mode under twin takeover, substitutes digital twin estimate for sensor level. Re-validates active external holds, dropping invalid holds.
  - `process_telemetry(pkt)` [CODE scada_live/scada_ids/gateway_core.py:337-352]: Passes packet to `_enrich_and_publish()`.
  - `_enrich_and_publish(pkt)` [CODE scada_live/scada_ids/gateway_core.py:353-485]: Runs IDS update, checks staleness, executes 4-way actuator consistency check (AM-3 wire tamper), updates `AlertManager`, handles twin takeover and handback state transitions, publishes to SSE and DB writer.
  - `check_watchdog(current_time)` [CODE scada_live/scada_ids/gateway_core.py:128-153]: Injects synthetic unreceived packets (`received=False`, zero flows) if wall-clock gap exceeds timeout ($1.5 \times dt / \text{time\_scale}$).

### `server.py`:
- Flask application hosting 21 routes: `/api/sense`, `/api/telemetry`, `/api/truth`, `/stream`, `/api/reset`, `/api/ack`, `/api/events`, `/api/metrics`, `/api/mode`, `/api/command`, `/api/config`, `/api/state`, `/api/history`, `/api/control/pause`, `/api/control/resume`, `/api/control/speed`, `/api/control/reset`, `/demo/attack/start`, `/demo/attack/stop`, `/demo/truth/stream`, `/` [CODE scada_live/scada_ids/server.py:37-409].

### `sse_hub.py`, `db_writer.py`, `metrics.py`:
- `EventHub`: Thread-safe multi-client queue fanout with bounded queue and drop-oldest overflow handling [CODE scada_live/scada_ids/sse_hub.py:5-34].
- `DBWriter`: Background queue worker writing to SQLite `data/live_run.db` (`live_ticks`, `live_events`) [CODE scada_live/scada_ids/db_writer.py:7-85].
- `MetricsCollector`: In-memory join buffer matching out-of-band truth with verdicts, tracking episode metrics, tick confusion matrix, and safety violations [CODE scada_live/scada_ids/metrics.py:1-182].

### `control_server.py` & `prevention.py`:
- Both contain only stub classes: `class ControlServer: pass # Phase 6` [CODE scada_live/scada_ids/control_server.py:1-2], `class PreventionController: pass # Phase 6` [CODE scada_live/scada_ids/prevention.py:1-2]. All control and prevention logic is implemented directly within `GatewayCore`.

### Web UI Assets:
- `defender.html` [CODE scada_live/scada_ids/static/defender.html:1-157]: Status banner, control source badge, wire tamper badge, mode toggle button, SVG tank and actuator visualization, engine score bars, Chart.js canvas, metrics cards, event log, interactive attack injector panel, and ack dialog.
- `app.js` [CODE scada_live/scada_ids/static/js/app.js:1-328]: Client SSE listener, Chart.js renderer, mode toggle API caller, acknowledge dialog handler, and demo attack trigger.
- `style.css` [CODE scada_live/scada_ids/static/css/style.css:1-271]: Visual styling for dark glassmorphism dashboard, status banners (SAFE, SUSPICIOUS, CRITICAL), and animated indicator badges.

## 3. Tests Covering It
- `scada_live/tests/test_phase3a_gateway.py`
- `scada_live/tests/test_phase3b_alert_metrics.py`
- `scada_live/tests/test_phase3b_metrics.py`
- `scada_live/tests/test_phase4_api.py`
- `scada_live/tests/test_phase6a_prevention.py`
- `scada_live/tests/test_phase6b_command_filtering.py`
- `scada_live/tests/test_gateway_safety_rule.py`
- `scada_live/tests/test_api_command_validation.py`
- `scada_live/tests/test_tamper_consistency_check.py`

## 4. Surprises, Mismatches, or Dead Code
- `control_server.py` and `prevention.py` are stubs with `pass`; their functionality is fully merged into `gateway_core.py`.
- The live Web UI includes a working mode toggle button (`btn-mode-toggle`) communicating with `POST /api/mode`, contradicting claims in earlier documentation that the mode toggle was unimplemented.
