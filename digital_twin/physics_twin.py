"""
SCADA IDS — Independent Physics Digital Twin

Maintains an isolated predicted state H_twin updated via prior
predictions and control inputs. The Twin NEVER consumes current
compromised sensor readings.

Architecture: Option B — Per-scenario reinitialization.
    H_twin(0) = H_true(0)  (known initial condition)
    H_twin(t+1) = H_twin(t) + (Q_in(t) - Q_out(t)) / A * Δt

The Twin uses the REPORTED (potentially attacked) flow values Q_in
and Q_out, but maintains its own level state independently. This is
critical: the Twin's level prediction diverges from observed values
during FDI attacks, creating a detectable physics residual.

For the physics residual:
    r_physics(t) = H_observed(t) - H_twin(t)
"""

import math
from config.parameters import PARAMS


class PhysicsTwin:
    """Independent Digital Twin for physics-based anomaly detection.

    The Twin runs the same mass-balance equation as the real tank
    but maintains its own state. It is reinitialized at the start
    of each scenario with the known initial condition.

    Important: The Twin uses the reported Q_in and Q_out values
    (which may include sensor noise but are assumed uncompromised
    per the frozen threat model) to update its state. It NEVER
    reads H_observed to correct itself.
    """

    def __init__(
        self,
        initial_level_m: float,
        area_m2: float | None = None,
        max_height_m: float | None = None,
    ):
        self._area = area_m2 or PARAMS.tank.cross_section_area_m2
        self._max_height = max_height_m or PARAMS.tank.max_height_m
        self._level = initial_level_m

    # ── Properties ───────────────────────────────────────────────────

    @property
    def level(self) -> float:
        """Current Twin predicted level in meters."""
        return self._level

    # ── Prediction ───────────────────────────────────────────────────

    def step(self, q_in: float, q_out: float, dt: float) -> float:
        """Advance the Twin by one timestep.

        H_twin(t+1) = H_twin(t) + (Q_in - Q_out) / A * Δt

        Args:
            q_in: Reported volumetric inflow (m³/s).
            q_out: Reported volumetric outflow (m³/s).
            dt: Time step in seconds.

        Returns:
            The new predicted level.
        """
        dh = (q_in - q_out) / self._area * dt
        self._level = max(0.0, min(self._level + dh, self._max_height))
        return self._level

    def compute_residual(self, h_observed: float) -> float:
        """Compute the physics residual.

        r_physics(t) = H_observed(t) - H_twin(t)

        A large absolute residual indicates a potential FDI attack.

        Args:
            h_observed: The observed (potentially compromised) tank level.

        Returns:
            The signed residual (observed - predicted).
        """
        return h_observed - self._level

    def reset(self, initial_level_m: float) -> None:
        """Reinitialize the Twin for a new scenario.

        This implements Option B (per-scenario reinitialization):
        H_twin(0) = H_true(0)
        """
        self._level = initial_level_m
