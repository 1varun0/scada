# Source File Note: `digital_twin/physics_twin.py`

## Purpose
Implements the independent open-loop Digital Twin model for cylindrical tank water level prediction and signed physics residual calculation ($r_{\text{physics}} = H_{\text{observed}} - H_{\text{twin}}$).

## Public Classes and Functions
- `class PhysicsTwin(initial_level_m: float, area_m2: float | None = None, max_height_m: float | None = None)`
  - `@property level -> float`: Current predicted level $H_{\text{twin}}$ in meters.
  - `step(q_in: float, q_out: float, dt: float) -> float`: Advances the predicted state using forward Euler mass balance: $H_{\text{twin}} \leftarrow \text{clamp}(H_{\text{twin}} + \frac{Q_{\text{in}} - Q_{\text{out}}}{A}\Delta t, 0, H_{\text{max}})$. Returns new level.
  - `compute_residual(h_observed: float) -> float`: Returns signed difference $r_{\text{physics}} = H_{\text{observed}} - H_{\text{twin}}$.
  - `reset(initial_level_m: float) -> None`: Reinitializes $H_{\text{twin}}$ to specified initial level (Option B per-scenario reinitialization).

## Inputs and Outputs
- `step()`:
  - Inputs: `q_in` (float, m³/s), `q_out` (float, m³/s), `dt` (float, s).
  - Output: float ($H_{\text{twin}}$).
- `compute_residual()`:
  - Input: `h_observed` (float, m).
  - Output: float (signed residual in meters).

## Config Keys and Constants Read
- `PARAMS.tank.cross_section_area_m2` [CODE digital_twin/physics_twin.py:44] (default: 2.0 m²)
- `PARAMS.tank.max_height_m` [CODE digital_twin/physics_twin.py:45] (default: 2.5 m)

## Who Calls It
- `engines.physics_engine.PhysicsEngine`
- `scada_live.scada_ids.streaming_ids.StreamingIDS`
- `scripts.run_e0_validation`
- `scripts.run_evaluation`
- `tests.test_twin`

## Side Effects
- In-memory state tracking only.

## Tests Covering It
- `tests/test_twin.py`:
  - `test_twin_initialization`
  - `test_twin_step_mass_balance`
  - `test_twin_bounded`
  - `test_twin_residual_zero_on_perfect_tracking`
  - `test_twin_residual_positive_on_fdi_high`
  - `test_twin_residual_negative_on_fdi_low`
  - `test_twin_reset`

## Surprising / Notable Observations
- Open-loop integration without state observer/Kalman filter: The Twin relies entirely on reported inflow and outflow rates without periodic correction from $H_{\text{observed}}$ (deliberately designed to prevent attack poison from corrupting the twin's reference state).
- Susceptibility to flow-noise bias: Because inflow and outflow measurements are subject to noise, any asymmetric noise (such as the non-negative clamping `max(0, Q + noise)`) leads to systematic cumulative drift in $H_{\text{twin}}$ over long horizons ($>800$ ticks).
