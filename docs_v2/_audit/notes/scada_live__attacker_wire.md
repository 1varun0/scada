# Source File Note: scada_live/attacker_wire/ (injector.py, server.py)

## 1. Purpose
Provides network attack interception and spoofing: `Injector` wraps `GatewayClient` to intercept `sense()` calls and modify `send_telemetry()` packets [CODE scada_live/attacker_wire/injector.py:1-9].

## 2. Public Classes / Functions
### `injector.py`:
- `class Injector` [CODE scada_live/attacker_wire/injector.py:5-131]:
  - `__init__(target_url, run_id, real_client=None)` [CODE scada_live/attacker_wire/injector.py:10-29].
  - `start_attack(attack_type, start_time, duration, magnitude=0.0, stealth=False, target_command=None, target_valve=None, drop_prob=1.0)` [CODE scada_live/attacker_wire/injector.py:30-43]: Configures active attack parameters and clears replay buffer.
  - `stop_attack()` [CODE scada_live/attacker_wire/injector.py:44-46]: Clears `attack_type = None`.
  - `_is_active(ts) -> bool` [CODE scada_live/attacker_wire/injector.py:47-50]: Checks if $start\_time \le ts \le start\_time + duration$.
  - `sense(seq, ts, level_m) -> Tuple[Optional[int], Optional[float]]` [CODE scada_live/attacker_wire/injector.py:52-89]:
    - If not active: buffers pre-attack levels if attack is "Replay"; delegates to `client.sense()`.
    - If active and "DoS": drops request with probability `drop_prob` (returns `(None, None)`).
    - If active and "Replay": replays recorded level from `replay_buffer`.
    - If active and "FDI": injects bias `level_m + self.magnitude`.
    - If active and "Auth misuse" or "Wire tamper": calls `client.sense(seq, ts, level_m)`, then overrides returned command with `target_command` (or 1 for wire tamper) and `target_valve`.
  - `send_telemetry(pkt_dict)` [CODE scada_live/attacker_wire/injector.py:91-131]:
    - Reports ground truth out-of-band via `client.send_truth(truth)` [CODE scada_live/attacker_wire/injector.py:95-102].
    - If active: drops packet for DoS, replaces `src_t` and `level_m` for Replay, adds magnitude for FDI, passes through for Auth misuse / Wire tamper (commands already executed on plant).

### `server.py`:
- `attacker_wire/server.py` contains only `# Phase 5: Flask server on :5001` [CODE scada_live/attacker_wire/server.py:1-2].

## 3. Who Calls It
- Initialized in `run_demo.py:main()` [CODE run_demo.py:350].
- Intercepts communication between `LivePlant` and the gateway.

## 4. Tests Covering It
- `scada_live/tests/test_phase4_injector.py`: Tests FDI, DoS, Replay, and Auth misuse injection and truth emissions.

## 5. Surprises, Mismatches, or Dead Code
- Standalone attacker Flask server (`attacker_wire/server.py`) is completely un-implemented. All live attack injections operate in-process via `Injector` wrapping `GatewayClient`.
- In `sense()` for FDI [CODE scada_live/attacker_wire/injector.py:74], only constant bias `magnitude` is implemented; ramp FDI is not dynamically scaled over time within `Injector` itself, though caller can pass configured magnitude.
