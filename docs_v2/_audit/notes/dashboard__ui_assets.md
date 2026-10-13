# Source File Note: dashboard UI Assets (templates/index.html, static/app.js, static/style.css)

## 1. Purpose
Provides the browser interface for the legacy batch dashboard: HTML markup, Chart.js dual-chart rendering (process states and anomaly score), and dark-mode CSS styling [CODE dashboard/templates/index.html:1-92, dashboard/static/app.js:1-204, dashboard/static/style.css:1-279].

## 2. Key Symbols & Components
- `index.html`:
  - Sidebar with scenario `<select id="scenario-select">`, system status dot/text (`status-indicator`, `status-text`), metric cards (`Avg. Latency`, `Anomalies Detected`) [CODE dashboard/templates/index.html:22-46].
  - Main panel with top canvas `processChart` (tank level, pump state) and bottom row with `scoresChart` (hybrid anomaly score) and `alert-feed` list (`alert-list`) [CODE dashboard/templates/index.html:50-86].
- `app.js`:
  - `loadScenarios()` [CODE dashboard/static/app.js:69-87]: Fetches `/api/scenarios`, populates dropdown, triggers `loadTelemetry` on the first scenario.
  - `loadTelemetry(scenarioId)` [CODE dashboard/static/app.js:90-199]: Fetches `/api/telemetry/<scenarioId>`.
  - Process chart dataset: `tank_level_observed` (cyan line), `pump_state` (green stepped line) [CODE dashboard/static/app.js:101-120].
  - Scores chart dataset: `S_hybrid` (magenta line), fixed threshold dashed line at 0.95 [CODE dashboard/static/app.js:132-149].
  - Alert logging: Scans `predicted_anomaly`, prepends an alert `<li>` for rising edges (`data.predicted_anomaly[i] === 1 && (i === 0 || data.predicted_anomaly[i-1] === 0)`) [CODE dashboard/static/app.js:170-183].
  - Status indicator: sets `status-danger` ("SYSTEM COMPROMISED") if anomalies > 0, else `status-ok` ("NORMAL OPERATION") [CODE dashboard/static/app.js:187-194].
- `style.css`:
  - Dark glassmorphism theme (`--bg-base: #07090F`, `--bg-surface: rgba(18, 22, 33, 0.6)`).
  - Danger pulsing animation `@keyframes pulse-danger` [CODE dashboard/static/style.css:142-146].

## 3. Inputs and Outputs
- **Inputs**: HTTP responses from `/api/scenarios` and `/api/telemetry/<id>`.
- **Outputs**: Rendered interactive DOM and Chart.js canvases in the client browser.

## 4. Config Keys or Constants Read
- Hardcoded threshold line `0.95` [CODE dashboard/static/app.js:143].
- Hardcoded chart y-axis limits: Process y in `[0, 2.5]`, Scores y in `[0, 1.1]` [CODE dashboard/static/app.js:51, 63].

## 5. Who Calls It
- Loaded by browser when visiting `http://localhost:5000/`.

## 6. Side Effects
- Client-side DOM manipulation and Chart.js rendering.

## 7. Tests Covering It
- None.

## 8. Surprises, Mismatches, or Dead Code
- The threshold shown on the chart is hard-coded to `0.95` [CODE dashboard/static/app.js:143], whereas `config/parameters.py` specifies `TAU_HYBRID = 0.85`.
- Average Latency metric card is hardcoded to `0ms` [CODE dashboard/templates/index.html:40] and never updated by JavaScript.
