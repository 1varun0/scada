# Source File Note: run_demo.py & scada_live/run_all.py & scada_live/tools/watch_sse.py

## 1. Purpose
- `run_demo.py`: Main unified runner for the live simulation, defender web interface, HTTP soak testing, and automated end-to-end demonstrations [CODE run_demo.py:1-421].
- `scada_live/run_all.py`: Unimplemented legacy launcher stub printed "Phase 5: launcher not yet implemented" [CODE scada_live/run_all.py:1-3].
- `scada_live/tools/watch_sse.py`: Command-line SSE client for watching live telemetry verdicts over `/stream` [CODE scada_live/tools/watch_sse.py:1-30].

## 2. Public Classes / Functions / Entry Points
### `run_demo.py`:
- `class PlantControl` [CODE run_demo.py:14-36]: Controller adapter exposing `pause()`, `resume()`, `set_speed(speed)`, `reset(initial_level_m)`.
- `run_plant_loop(plant, injector, control, max_ticks, soak_mode, stop_event)` [CODE run_demo.py:37-109]: Main simulation loop executing plant observation, injection, advance, and telemetry queuing.
- `class ServerThread(threading.Thread)` [CODE run_demo.py:111-123]: Background Werkzeug server hosting the Flask gateway on port 5000.
- `class AutoDemoCoordinator(threading.Thread)` [CODE run_demo.py:125-320]: Coordinates automated 7-phase presentation:
  - Phase A: Baseline Normal (20s) [CODE run_demo.py:189-194]
  - Phase B: FDI Ramp (+0.35m bias) -> Twin Takeover (35s) [CODE run_demo.py:198-204]
  - Phase C: Attack Cessation & Automatic Handback (20s) [CODE run_demo.py:208-216]
  - Phase D: Denial of Service -> Watchdog & gap suppression (30s) [CODE run_demo.py:220-230]
  - Phase E: Auth misuse ingress block & continuous hold enforcement drop (30s) [CODE run_demo.py:234-253]
  - Phase F: Downstream wire tamper -> 4-way consistency check flags in <=3 ticks (30s) [CODE run_demo.py:257-274]
  - Phase G: Final metrics summary compilation [CODE run_demo.py:277-319]
- `main()` [CODE run_demo.py:322-421]: CLI parser (`--soak`, `--auto`, `--speed`, `--exit-on-finish`).

## 3. Inputs and Outputs
- CLI flags: `--soak` runs 1800 ticks, reports P50/P95/P99 latencies, RSS memory; `--auto` executes the 7-phase demonstration; `--speed <float>` scales simulation time.
- Terminal formatted logs and execution summaries.

## 4. Tests Covering It
- `scada_live/tests/test_phase7_auto_demo.py`: Tests the full automated demo runner in headless mode.

## 5. Surprises, Mismatches, or Dead Code
- `scada_live/run_all.py` is dead code (2 lines). All live demonstrations use root `run_demo.py`.
