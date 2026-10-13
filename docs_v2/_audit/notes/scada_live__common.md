# Source File Note: scada_live/common/ (config_loader.py, packets.py, transport.py)

## 1. Purpose
Provides foundational abstractions: configuration deserialization (`config_loader.py`), network packet schemas (`packets.py`), and HTTP/SSE networking clients (`transport.py`) [CODE scada_live/common/config_loader.py:1-27, scada_live/common/packets.py:1-57, scada_live/common/transport.py:1-53].

## 2. Public Classes / Functions
### `config_loader.py`:
- `load_config(config_path=None) -> SimpleNamespace` [CODE scada_live/common/config_loader.py:5-15]: Loads `config.yaml` and recursively converts dictionaries and lists into `SimpleNamespace` for dot-access syntax.
- `_dict_to_namespace(d) -> SimpleNamespace` [CODE scada_live/common/config_loader.py:17-26].

### `packets.py`:
- `@dataclass class TelemetryPacket` [CODE scada_live/common/packets.py:3-42]:
  - Wire fields: `seq: int`, `run_id: str`, `ts: float`, `src_t: float`, `received: bool`, `level_m: float`, `q_in: float`, `q_out: float`, `pump_on: bool`, `pump_cmd: int`, `valve_pct: float`, `valve_cmd: float` [CODE scada_live/common/packets.py:6-17].
  - Out-of-band ground-truth fields: `_true_level: float = 0.0`, `_attack_active: bool = False`, `_attack_type: str = "None"` [CODE scada_live/common/packets.py:22-24].
  - Methods: `to_dict()`, `from_dict()`, `strip_truth()`, `truth_only()` [CODE scada_live/common/packets.py:26-41].
- `@dataclass class CommandPacket` [CODE scada_live/common/packets.py:43-57]:
  - Fields: `seq: int`, `ts: float`, `src: str`, `cmd: str`, `value: str`.

### `transport.py`:
- `class TransportClient` [CODE scada_live/common/transport.py:5-44]: `send_telemetry(packet_dict)`, `send_command(command_dict)`, `stream_sse(endpoint)`.
- `class TransportServer` [CODE scada_live/common/transport.py:45-53]: `sse_response(generator_func)` helper wrapping generators in Flask event-stream responses.

## 3. Who Calls It
- `load_config` is called by every live component.
- `TelemetryPacket` is constructed by `LivePlant`, parsed by `server.py`, consumed by `StreamingIDS` and `GatewayCore`.
- `CommandPacket` is parsed by `plant_sim/server.py`.

## 4. Tests Covering It
- `scada_live/tests/test_phase0_imports.py`: Verifies imports, packet creation, and truth stripping.

## 5. Surprises, Mismatches, or Dead Code
- `TelemetryPacket` ground truth fields are prefixed with an underscore (`_true_level`, etc.) to explicitly demarcate out-of-band data from wire data [CODE scada_live/common/packets.py:19-25].
