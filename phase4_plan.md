# Phase 4 Implementation Plan: Defender Dashboard & Demo Runner

## Overview
Phase 4 builds the **real-time Defender Dashboard** and a **single-process demo runner** (`run_demo.py`). Since we need live attacks to verify the UI, this phase pulls forward the attack injector logic from Phase 5 into a simple HTTP client loop, allowing us to launch attacks from the UI before the multi-process split.

## 1. Directory Structure Updates
```
scada_live/
├── run_demo.py            (New: In-process runner + HTTP injector)
└── scada_ids/
    ├── server.py          (Existing: adding /api/state, /api/history, /api/config)
    ├── templates/
    │   └── defender.html  (New: Main UI layout)
    └── static/
        ├── css/
        │   └── style.css  (New: UI styling and safe animations)
        ├── js/
        │   ├── app.js     (New: SSE wiring, fixed-buffer Chart.js)
        │   └── chart.js   (New: Vendored local Chart.js)
```

## 2. Server.py / API Enhancements
- **`/api/config`**: Returns physical tank limits (critical high/low, overflow, controller setpoints) to replace hardcoded bands.
- **`/api/history`**: Returns the last $N$ ticks from the gateway's internal `level_buffer` so the UI can prefill the chart on load or reconnect.
- **`/api/state`**: Current alert state and active event ID (for initial load without waiting for the next SSE tick).
- **`PlantControl` interface**: Instead of the gateway holding a reference to the plant, demo controls (`/speed`, `/pause`, `/reset`) will route to a `PlantControl` instance that manages the simulation thread. Pause must suspend the watchdog to prevent false DoS alerts. Speed changes must update the watchdog timeout dynamically.
- **Host Binding**: Bind to `127.0.0.1`.

## 3. Demo Runner & Injector (`run_demo.py`)
To test the UI, we need live attacks. We will build `run_demo.py` which:
1. Starts the `LivePlant` thread.
2. Starts the `scada_ids.server` on :5000.
3. Runs an interceptor loop acting as a basic Injector (FDI, Replay, DoS, Auth misuse). 
4. Exposes a temporary "demo attack" control panel (to be replaced by the Phase 5 attacker console) that triggers attacks and guarantees ground truth is sent to the `/api/truth` endpoint.

## 4. Front-End Components (defender.html & style.css)

### A. Status Banner & Ack Flow
- Banner reflects `SAFE` (green), `SUSPICIOUS` (amber, slow pulse), `CRITICAL` (red).
- **No Fast Flashing**: Use a slow pulse and respect `prefers-reduced-motion`. 
- **Calibrating**: Calibrating is NOT a main alert state. Show it as a secondary blue badge (`calibrating` and `recalibrating_ticks_left`).
- **Ack Dialog**: 
  - Shows attack type, engines firing, and event time.
  - Warns that recalibration trusts the current sensor readings.
  - Handles `409 sensor_unstable` with a readable error (e.g., "Cannot recalibrate mid-ramp").
  - The "Acknowledge" button is disabled if no alert is latched.

### B. Telemetry Chart (Chart.js)
- Vendor Chart.js locally.
- Real-time line chart with **fixed-length buffers** and **animations disabled** (`animation: false`) to ensure flat memory usage over 30+ minute runs.
- Plots `level_obs`, `level_twin`, and dynamic safe bands from `/api/config`.
- **Demo Truth Channel**: A separate toggle ("Ground truth (demo only)") to display `true_level` without exposing it to the IDS.

### C. Process Visualization (Inline SVG)
- An inline SVG (not `<img>` so it can be scripted).
- Shows animated water level (`level_obs`), valve position percentage, commanded vs. actual pump state, and critical limit lines.

### D. Event Log, Metrics & Robustness
- **Event Log**: Render text with `textContent` (no `innerHTML`) for safety.
- **Link Lost State**: If no SSE message arrives for ~3s, show a "Link Lost" overlay. On reconnect, fetch `/api/history` to restore the chart.
- **Mode Toggle**: Visually disable the Monitor/Prevention toggle (label it 'Phase 6').
- **Presentation Mode**: A toggle to increase font sizes and contrast for projector viewing.

## 5. Outstanding Phase 3 Items Addressed
- The 5x HTTP gateway soak test (verifying p95 latency) was pending since Phase 3b ran in-process. `run_demo.py` will enable running this soak test over real HTTP.

## 6. Acceptance Criteria
- [ ] UI loads locally on `127.0.0.1:5000` with no console errors.
- [ ] Launching demo attacks successfully triggers the full state machine and ack flow.
- [ ] Memory remains flat over a 30-minute run at 5x speed.
- [ ] Link recovery works seamlessly.
- [ ] Watchdog timeout scales dynamically with the `time_scale` setting.
