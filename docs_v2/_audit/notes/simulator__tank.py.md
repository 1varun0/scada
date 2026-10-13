# Source File Note: `simulator/tank.py`

## Purpose
Implements the single cylindrical water tank mass-balance physical model using discrete Forward Euler integration bounded by physical height limits $[0, H_{\text{max}}]$.

## Public Classes and Functions
- `class Tank(initial_level_m: float | None = None, area_m2: float | None = None, max_height_m: float | None = None)`
  - `@property level -> float`: Current liquid level in meters.
  - `@property area -> float`: Tank cross-sectional area $A$ in m².
  - `@property max_height -> float`: Tank physical height $H_{\text{max}}$ in meters.
  - `step(q_in: float, q_out: float, dt: float) -> float`: Computes $\Delta H = \frac{Q_{\text{in}} - Q_{\text{out}}}{A}\Delta t$, updates $H \leftarrow \text{clamp}(H + \Delta H, 0, H_{\text{max}})$, and returns the new level.
  - `reset(level_m: float) -> None`: Clamps specified level to $[0, H_{\text{max}}]$ and assigns to `_level`.

## Inputs and Outputs
- `step(q_in: float, q_out: float, dt: float)`:
  - Inputs: `q_in` ($m^3/s \ge 0$), `q_out` ($m^3/s \ge 0$), `dt` ($s > 0$).
  - Output: float (new level $H(t+\Delta t)$ clamped to $[0, H_{\text{max}}]$).

## Config Keys and Constants Read
- `PARAMS.tank.cross_section_area_m2` [CODE simulator/tank.py:23] (default: 1.0 m²)
- `PARAMS.tank.max_height_m` [CODE simulator/tank.py:24] (default: 2.0 m)
- `PARAMS.tank.initial_level_m` [CODE simulator/tank.py:25] (default: 1.0 m)

## Who Calls It
- `simulator.process_simulator.ProcessSimulator`
- `scada_live.plant_sim.plant.SimulatedPlant`
- `tests/test_tank.py`

## Side Effects
- In-memory state tracking only.

## Tests Covering It
- `tests/test_tank.py`:
  - `test_tank_initial_state`
  - `test_tank_step_fill`
  - `test_tank_step_drain`
  - `test_tank_clamp_max`
  - `test_tank_clamp_min`
  - `test_tank_reset`

## Surprising / Notable Observations
- Integration method: Forward Euler ($H_{k+1} = H_k + \frac{Q_{\text{in}} - Q_{\text{out}}}{A} \Delta t$).
- Physical saturation: Levels are hard-clamped at $H_{\text{max}} = 2.0\text{ m}$ (representing overflow/spill) and $0.0\text{ m}$ (dry tank). No overflow liquid accumulator is modeled.
