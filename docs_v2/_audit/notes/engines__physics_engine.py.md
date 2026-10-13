# Source File Note: `engines/physics_engine.py`

## Purpose
Implements Engine 1 (Physics Consistency Engine), targeting A1 False Data Injection (FDI) attacks. Manages `PhysicsTwin` lifecycle, computes raw signed residual $r = H_{\text{observed}} - H_{\text{twin}}$, and scales it to normalized score $S_p \in [0, 1]$.

## Public Classes and Functions
- `class PhysicsEngine(tau_p: float)`
  - `__init__(tau_p: float)`: Stores threshold $\tau_p$; initializes `twin = None`.
  - `reset(initial_level_m: float, area_m2: float = None, max_height_m: float = None) -> None`: Instantiates or reinitializes `self.twin`.
  - `step(q_in: float, q_out: float, h_observed: float, dt: float) -> tuple[float, float, float]`: Steps the twin, computes raw residual, and scales score. Returns `(h_twin, residual, s_p)`.

## Inputs and Outputs
- `step()` inputs:
  - `q_in`, `q_out`: floats ($m^3/s$).
  - `h_observed`: float (meters).
  - `dt`: float (seconds).
- `step()` outputs:
  - `tuple[float, float, float]`: `(h_twin, residual, s_p)` where $S_p \in [0.0, 1.0]$.

## Config Keys and Constants Read
- Threshold $\tau_p$ passed via constructor (default from `PARAMS.controller.tau_p = 0.035`).

## Who Calls It
- `evaluation.ablation`
- `scripts.run_evaluation`
- `tests.test_engines`

## Side Effects
- In-memory state tracking only.

## Tests Covering It
- `tests/test_engines.py`:
  - `test_physics_engine_step_clean`
  - `test_physics_engine_step_attack`
  - `test_physics_engine_uninitialized_error`

## Surprising / Notable Observations
- Linear score normalization with hard ceiling at 1.0:
  $$S_p = \min\left(\frac{|H_{\text{observed}} - H_{\text{twin}}|}{\tau_p}, 1.0\right)$$
- If `step()` is invoked prior to `reset()`, raises `RuntimeError`.
