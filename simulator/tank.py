"""
SCADA IDS — Tank Physics Model

Implements the single-tank water level dynamics:
    H(t+1) = H(t) + (Q_in - Q_out) / A * Δt

The tank enforces physical bounds [0, H_max].
This is a pure physics model with no side effects.
"""

from config.parameters import PARAMS


class Tank:
    """Single cylindrical water tank with bounded level."""

    def __init__(
        self,
        initial_level_m: float | None = None,
        area_m2: float | None = None,
        max_height_m: float | None = None,
    ):
        self._area = area_m2 or PARAMS.tank.cross_section_area_m2
        self._max_height = max_height_m or PARAMS.tank.max_height_m
        self._level = initial_level_m if initial_level_m is not None else PARAMS.tank.initial_level_m

        # Validate initial state
        self._level = self._clamp(self._level)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def level(self) -> float:
        """Current water level in meters."""
        return self._level

    @property
    def area(self) -> float:
        """Cross-sectional area in m²."""
        return self._area

    @property
    def max_height(self) -> float:
        """Maximum tank height in meters."""
        return self._max_height

    # ── Physics ──────────────────────────────────────────────────────

    def step(self, q_in: float, q_out: float, dt: float) -> float:
        """Advance the tank level by one timestep.

        Args:
            q_in: Volumetric inflow (m³/s). Must be >= 0.
            q_out: Volumetric outflow (m³/s). Must be >= 0.
            dt: Time step in seconds.

        Returns:
            The new water level after clamping to [0, H_max].
        """
        dh = (q_in - q_out) / self._area * dt
        self._level = self._clamp(self._level + dh)
        return self._level

    def reset(self, level_m: float) -> None:
        """Reset the tank to a specific level."""
        self._level = self._clamp(level_m)

    # ── Internal ─────────────────────────────────────────────────────

    def _clamp(self, level: float) -> float:
        """Clamp level to physical bounds [0, H_max]."""
        return max(0.0, min(level, self._max_height))
