"""
SCADA IDS — Pump Model

ON/OFF pump with fixed flow rate and configurable response delay.
The pump tracks both the commanded state and the actual state,
with a delay between command and execution to simulate mechanical inertia.
"""

import math
from config.parameters import PARAMS


class Pump:
    """Binary (ON/OFF) pump with response delay.

    The pump delivers a fixed flow rate when ON (no variable speed).
    A configurable delay (in seconds) simulates mechanical inertia
    between when a command is issued and when the pump actually
    transitions.
    """

    def __init__(
        self,
        initial_state: int = 0,
        q_max_m3s: float | None = None,
        response_delay_s: float | None = None,
        dt_s: float | None = None,
    ):
        self._q_max = q_max_m3s or PARAMS.pump.q_max_m3s
        self._response_delay_s = response_delay_s if response_delay_s is not None else PARAMS.pump.response_delay_s
        self._dt = dt_s or PARAMS.simulation.dt_s

        # Delay in discrete steps (rounded up)
        self._delay_steps = max(1, math.ceil(self._response_delay_s / self._dt))

        # State tracking
        self._command = initial_state        # What the controller wants
        self._state = initial_state          # What the pump is actually doing
        self._steps_since_command = self._delay_steps  # Start as settled

    # ── Properties ───────────────────────────────────────────────────

    @property
    def command(self) -> int:
        """Current commanded state (1=ON, 0=OFF)."""
        return self._command

    @property
    def state(self) -> int:
        """Current actual state (1=ON, 0=OFF)."""
        return self._state

    @property
    def flow(self) -> float:
        """Current actual flow rate in m³/s."""
        return self._q_max if self._state == 1 else 0.0

    # ── Control ──────────────────────────────────────────────────────

    def set_command(self, command: int) -> None:
        """Issue a pump command (1=ON, 0=OFF).

        The actual state will transition after the response delay.
        """
        cmd = 1 if command else 0
        if cmd != self._command:
            self._command = cmd
            self._steps_since_command = 0

    def step(self) -> int:
        """Advance the pump by one timestep.

        Returns:
            The actual pump state after this step.
        """
        self._steps_since_command += 1

        # Transition to commanded state after delay
        if self._steps_since_command >= self._delay_steps:
            self._state = self._command

        return self._state

    def reset(self, state: int = 0) -> None:
        """Reset the pump to a specific state."""
        self._command = state
        self._state = state
        self._steps_since_command = self._delay_steps
