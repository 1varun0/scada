"""
SCADA IDS — Valve Model

Continuously variable valve (0–100%) with gravity-driven outflow model
and slew-rate limiting to simulate actuator dynamics.

Outflow model:  Q_out = Cv * (V% / 100) * sqrt(H)
"""

import math
from config.parameters import PARAMS


class Valve:
    """Continuously variable valve with slew-rate limiting.

    The valve position is commanded as a percentage (0–100%).
    The actual position approaches the command with a slew rate
    determined by the response time parameter.

    Outflow is gravity-driven: Q_out = Cv * (V_actual% / 100) * sqrt(H)
    """

    def __init__(
        self,
        initial_position_pct: float = 50.0,
        flow_coefficient_m3s: float | None = None,
        response_time_s: float | None = None,
        dt_s: float | None = None,
    ):
        self._cv = flow_coefficient_m3s or PARAMS.valve.flow_coefficient_m3s
        self._response_time = response_time_s if response_time_s is not None else PARAMS.valve.response_time_s
        self._dt = dt_s or PARAMS.simulation.dt_s

        # Maximum slew rate: full range (100%) in response_time seconds
        self._max_slew_rate = 100.0 / self._response_time if self._response_time > 0 else float('inf')

        # State
        self._command_pct = initial_position_pct
        self._position_pct = initial_position_pct

    # ── Properties ───────────────────────────────────────────────────

    @property
    def command(self) -> float:
        """Commanded valve position in percent (0–100)."""
        return self._command_pct

    @property
    def position(self) -> float:
        """Actual valve position in percent (0–100)."""
        return self._position_pct

    # ── Control ──────────────────────────────────────────────────────

    def set_command(self, position_pct: float) -> None:
        """Issue a valve position command (0.0 – 100.0 %)."""
        self._command_pct = max(0.0, min(100.0, position_pct))

    def step(self) -> float:
        """Advance the valve by one timestep with slew-rate limiting.

        Returns:
            The actual valve position after this step.
        """
        error = self._command_pct - self._position_pct
        max_change = self._max_slew_rate * self._dt

        if abs(error) <= max_change:
            self._position_pct = self._command_pct
        elif error > 0:
            self._position_pct += max_change
        else:
            self._position_pct -= max_change

        # Enforce bounds
        self._position_pct = max(0.0, min(100.0, self._position_pct))
        return self._position_pct

    def compute_outflow(self, tank_level_m: float) -> float:
        """Calculate outflow based on current valve position and tank level.

        Q_out = Cv * (V% / 100) * sqrt(H)

        Args:
            tank_level_m: Current tank water level in meters.

        Returns:
            Volumetric outflow in m³/s. Returns 0 if level <= 0.
        """
        if tank_level_m <= 0.0:
            return 0.0
        return self._cv * (self._position_pct / 100.0) * math.sqrt(tank_level_m)

    def reset(self, position_pct: float = 50.0) -> None:
        """Reset the valve to a specific position."""
        self._command_pct = position_pct
        self._position_pct = position_pct
