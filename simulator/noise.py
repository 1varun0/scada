"""
SCADA IDS — Sensor Noise Generator

Adds Gaussian noise to sensor readings to simulate real-world
measurement imprecision. Uses per-scenario seeded RNG for
deterministic reproducibility.
"""

import numpy as np
from config.parameters import PARAMS


class NoiseGenerator:
    """Seeded Gaussian noise generator for sensor measurements.

    Each scenario should use a unique seed to ensure different but
    reproducible noise patterns.
    """

    def __init__(
        self,
        seed: int,
        level_noise_std: float | None = None,
        flow_noise_std: float | None = None,
        clamp_flow_noise: bool = True,
    ):
        self._rng = np.random.default_rng(seed)
        self._sigma_h = level_noise_std if level_noise_std is not None else PARAMS.simulation.sensor_noise_level_m
        self._sigma_q = flow_noise_std if flow_noise_std is not None else PARAMS.simulation.sensor_noise_flow_m3s
        self._clamp_flow = clamp_flow_noise

    def add_level_noise(self, true_level: float) -> float:
        """Add Gaussian noise to a tank level reading.

        Args:
            true_level: True tank level in meters.

        Returns:
            Noisy observed level (not clamped — that's the sensor's job).
        """
        return true_level + self._rng.normal(0.0, self._sigma_h)

    def add_flow_noise(self, true_flow: float) -> float:
        """Add Gaussian noise to a flow measurement.

        Args:
            true_flow: True flow rate in m³/s.

        Returns:
            Noisy observed flow.
        """
        noisy = true_flow + self._rng.normal(0.0, self._sigma_q)
        return max(0.0, noisy) if self._clamp_flow else noisy
