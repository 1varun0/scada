# Source File Note: `simulator/noise.py`

## Purpose
Generates reproducible Gaussian measurement noise for water level and flow rate sensors using NumPy's `default_rng(seed)`.

## Public Classes and Functions
- `class NoiseGenerator(seed: int, level_noise_std: float | None = None, flow_noise_std: float | None = None, clamp_flow_noise: bool = True)`
  - `add_level_noise(true_level: float) -> float`: Returns `true_level + Normal(0, sigma_h)`. No clamping applied here.
  - `add_flow_noise(true_flow: float) -> float`: Returns `max(0.0, true_flow + Normal(0, sigma_q))` if `clamp_flow_noise=True`, else raw noisy flow.

## Inputs and Outputs
- `add_level_noise()`:
  - Input: `true_level` (float, meters)
  - Output: float (noisy level in meters)
- `add_flow_noise()`:
  - Input: `true_flow` (float, m³/s)
  - Output: float (noisy flow rate in m³/s, non-negative if clamped)

## Config Keys and Constants Read
- `PARAMS.simulation.sensor_noise_level_m` [CODE simulator/noise.py:28] (default: 0.005 m)
- `PARAMS.simulation.sensor_noise_flow_m3s` [CODE simulator/noise.py:29] (default: 0.0001 m³/s)

## Who Calls It
- `simulator.process_simulator.ProcessSimulator`
- `tests/test_simulator.py`

## Side Effects
- Advances internal NumPy PRNG state (`self._rng`).

## Tests Covering It
- Indirectly covered in `tests/test_simulator.py` (`test_process_simulator_noise_reproducibility`, etc.).

## Surprising / Notable Observations
- Flow noise clamping: Line 53 executes `return max(0.0, noisy) if self._clamp_flow else noisy`. Because `clamp_flow_noise` defaults to `True` [CODE simulator/noise.py:25], whenever true flow is zero (e.g., pump OFF or valve fully closed), negative noise draws are truncated to zero, causing a strictly positive mean bias $E[\tilde{Q}] = \frac{\sigma_q}{\sqrt{2\pi}} \approx 3.99 \times 10^{-5}\text{ m}^3/\text{s}$. Over hundreds of ticks, integrating this clamped flow causes the physics twin to drift if the twin uses clamped measured flows without compensating for truncation bias.
