# Source File Note: scada_live/plant_sim/ (plant.py, gateway_client.py, server.py)

## 1. Purpose
Simulates the physical single-tank water process in real time (`LivePlant`), connects to the Gateway via synchronous sensing and asynchronous telemetry (`GatewayClient`), and exposes an HTTP/SSE interface (`plant_sim/server.py`) [CODE scada_live/plant_sim/plant.py:1-12, scada_live/plant_sim/gateway_client.py:1-13, scada_live/plant_sim/server.py:1-10].

## 2. Public Classes / Functions
### `plant.py`:
- `class LivePlant` [CODE scada_live/plant_sim/plant.py:12-122]:
  - `__init__(cfg, seed=42000, standalone_mode=False)` [CODE scada_live/plant_sim/plant.py:13-42]: Instantiates `Tank`, `Pump`, `Valve`, `NoiseGenerator`, and optional `Controller`. Respects `cfg.simulation.clamp_flow_noise` flag.
  - `apply_command(pump_value: str)` [CODE scada_live/plant_sim/plant.py:43-49]: Translates "ON" / "OFF" to `pump.set_command(1 / 0)`.
  - `observe() -> float` [CODE scada_live/plant_sim/plant.py:50-54]: Reads true tank level and returns noisy observed level.
  - `advance(pump_cmd: int, valve_cmd: float) -> TelemetryPacket` [CODE scada_live/plant_sim/plant.py:56-97]: Applies commands, steps actuators, computes outflows, steps mass balance, updates overflow/dry run counts, returns `TelemetryPacket`.
  - `step() -> TelemetryPacket` [CODE scada_live/plant_sim/plant.py:99-109]: Standalone step combining `observe()` and `advance()`.
  - `reset()` [CODE scada_live/plant_sim/plant.py:110-122]: Resets tank, pump, valve, controller, and noise generator.

### `gateway_client.py`:
- `class GatewayClient` [CODE scada_live/plant_sim/gateway_client.py:7-72]:
  - `sense(seq, ts, level_m) -> Tuple[int, float]` [CODE scada_live/plant_sim/gateway_client.py:22-38]: Synchronous POST to `/api/sense` with 0.5s timeout. Returns `(pump_cmd, valve_cmd)`. On timeout/failure, returns `(None, None)`.
  - `send_telemetry(pkt_dict)` [CODE scada_live/plant_sim/gateway_client.py:40-46]: Queues packet to internal worker thread (`queue.Queue(maxsize=100)`).
  - `send_truth(truth_dict)` [CODE scada_live/plant_sim/gateway_client.py:48-57]: Fire-and-forget daemon thread POST to `/api/truth`.
  - `_sender_loop()` [CODE scada_live/plant_sim/gateway_client.py:59-71]: Worker loop draining telemetry queue to `/api/telemetry`.

### `server.py`:
- Routes:
  - `GET /telemetry`: SSE generator yielding JSON telemetry packets [CODE scada_live/plant_sim/server.py:20-31].
  - `POST /command`: Accepts `CommandPacket` ("PUMP", "ON"/"OFF") [CODE scada_live/plant_sim/server.py:33-50].
  - `GET /status`: Health check returning tick counter, overflow, and dry run counts [CODE scada_live/plant_sim/server.py:51-60].
- `plant_loop()` [CODE scada_live/plant_sim/server.py:61-74]: Background simulation loop sleeping `(dt_s / time_scale) - elapsed`.
- `start_server(standalone_mode=True)` [CODE scada_live/plant_sim/server.py:75-81].

## 3. Who Calls It
- `LivePlant` and `GatewayClient` are initialized in `run_demo.py:main()`.
- `plant_sim/server.py` is used when running multi-process architecture.

## 4. Tests Covering It
- `scada_live/tests/test_phase1_plant.py`: Tests plant initialization, stepping, and sensor noise.
- `scada_live/tests/test_phase2_equivalence.py`: Validates exact numerical equivalence between batch `ProcessSimulator` and `LivePlant`.

## 5. Surprises, Mismatches, or Dead Code
- In `LivePlant.reset()` [CODE scada_live/plant_sim/plant.py:115], `self.noise = NoiseGenerator(...)` does not pass `clamp_flow_noise=clamp`, reverting to `clamp_flow_noise=False` even if configured differently.
