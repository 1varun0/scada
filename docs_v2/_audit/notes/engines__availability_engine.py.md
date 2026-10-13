# Source File Note: `engines/availability_engine.py`

## Purpose
Implements Engine 4 (Communication Integrity Engine, $S_a$), detecting packet loss (A3 DoS) and stale/replayed data (A2 Replay) via packet arrival flags and timestamp latency evaluation.

## Public Classes and Functions
- `class AvailabilityEngine(tau_a_ms: float = 1500.0, tau_a_max_ms: float = 5000.0)`
  - `__init__(tau_a_ms: float = 1500.0, tau_a_max_ms: float = 5000.0)`: Stores thresholds.
  - `evaluate(simulation_time_s: float, source_time_s: float, packet_received: bool) -> tuple[float, float]`: Evaluates availability metrics. Returns `(data_age_ms, s_a)`.

## Inputs and Outputs
- `evaluate()`:
  - Inputs:
    - `simulation_time_s`: float (current SCADA host clock in seconds).
    - `source_time_s`: float (packet timestamp from sensor in seconds).
    - `packet_received`: bool (arrival flag; False if communication link failed/blocked).
  - Outputs:
    - `tuple[float, float]`: `(data_age_ms, s_a)` where $S_a \in [0.0, 1.0]$.

## Config Keys and Constants Read
- Defaults: `tau_a_ms = 1500.0` (corresponds to `PARAMS.controller.tau_a_ms = 1500.0`) and `tau_a_max_ms = 5000.0`.

## Who Calls It
- `evaluation.ablation`
- `scripts.run_evaluation`
- `tests.test_engines`
- `scada_live.scada_ids.streaming_ids.StreamingIDS`

## Side Effects
- Pure stateless calculation; no side effects.

## Tests Covering It
- `tests/test_engines.py`:
  - `test_availability_engine_normal`
  - `test_availability_engine_dos_packet_loss`
  - `test_availability_engine_replay_latency_ramp`

## Surprising / Notable Observations
- Piecewise ramp formula for replay latency:
  $$S_a = \begin{cases} 1.0 & \text{if } \text{packet\_received} = \text{False} \\ 0.0 & \text{if } \text{data\_age\_ms} \le \tau_a \\ \min\left(\frac{\text{data\_age\_ms} - \tau_a}{\tau_{a,\text{max}} - \tau_a}, 1.0\right) & \text{if } \text{data\_age\_ms} > \tau_a \end{cases}$$
- For packet drop (DoS), line 30 immediately returns `(0.0, 1.0)`. Note that returned `data_age_ms` is `0.0` rather than infinity or elapsed dead time.
