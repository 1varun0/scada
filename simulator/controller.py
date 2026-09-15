"""
SCADA IDS — Hysteresis Controller

Bang-bang controller with deterministic fail-safe behavior.

Normal operation:
    Pump ON  when H < setpoint - deadband
    Pump OFF when H > setpoint + deadband
    Valve position adjusted to balance flow

Fail-safe (DoS detected):
    Pump = OFF, Valve = V_safe (0%)
"""

from config.parameters import PARAMS


class Controller:
    """Hysteresis (bang-bang) controller with fail-safe mode.

    The controller issues pump ON/OFF commands based on the observed
    tank level relative to the setpoint ± deadband. The valve position
    is set to a default opening for normal flow balancing.

    When a DoS condition is detected (communication blocked), the
    controller enters fail-safe mode: Pump=OFF, Valve=0%.
    """

    def __init__(
        self,
        setpoint_m: float | None = None,
        deadband_m: float | None = None,
        default_valve_pct: float | None = None,
    ):
        self._deadband = deadband_m if deadband_m is not None else PARAMS.controller.deadband_m
        self._default_valve_pct = default_valve_pct if default_valve_pct is not None else PARAMS.controller.default_valve_pct

        # Mutable setpoint — can change via setpoint profiles
        self._setpoint = setpoint_m if setpoint_m is not None else PARAMS.controller.setpoint_m

        # Derived thresholds
        self._pump_on_threshold = self._setpoint - self._deadband
        self._pump_off_threshold = self._setpoint + self._deadband

        # State
        self._pump_command = 0   # 0=OFF, 1=ON
        self._valve_command = self._default_valve_pct
        self._control_command_str = "INIT"
        self._is_failsafe = False

    # ── Properties ───────────────────────────────────────────────────

    @property
    def setpoint(self) -> float:
        """Current setpoint in meters."""
        return self._setpoint

    @property
    def pump_command(self) -> int:
        """Current pump command (1=ON, 0=OFF)."""
        return self._pump_command

    @property
    def valve_command(self) -> float:
        """Current valve command (0–100 %)."""
        return self._valve_command

    @property
    def control_command_str(self) -> str:
        """Human-readable description of the last control action."""
        return self._control_command_str

    @property
    def is_failsafe(self) -> bool:
        """Whether the controller is in fail-safe mode."""
        return self._is_failsafe

    # ── Control Logic ────────────────────────────────────────────────

    def update_setpoint(self, setpoint_m: float) -> None:
        """Update the setpoint and recalculate thresholds."""
        self._setpoint = setpoint_m
        self._pump_on_threshold = self._setpoint - self._deadband
        self._pump_off_threshold = self._setpoint + self._deadband

    def step(self, observed_level_m: float, dos_active: bool = False) -> dict:
        """Execute one control cycle.

        Args:
            observed_level_m: Current observed tank level in meters.
            dos_active: Whether a DoS condition is currently active.

        Returns:
            dict with keys: pump_command, valve_command, control_command
        """
        if dos_active:
            return self._failsafe()

        self._is_failsafe = False

        # Hysteresis logic
        if observed_level_m < self._pump_on_threshold:
            self._pump_command = 1
            self._control_command_str = "PUMP_ON"
        elif observed_level_m > self._pump_off_threshold:
            self._pump_command = 0
            self._control_command_str = "PUMP_OFF"
        else:
            # Within deadband — maintain current state
            self._control_command_str = "HOLD"

        # Valve: default opening for normal operation
        self._valve_command = self._default_valve_pct

        return {
            "pump_command": self._pump_command,
            "valve_command": self._valve_command,
            "control_command": self._control_command_str,
        }

    def override_command(
        self,
        pump_command: int | None = None,
        valve_command: float | None = None,
        command_str: str = "OVERRIDE",
    ) -> dict:
        """Force a specific command (used for A4 authenticated misuse).

        Args:
            pump_command: Override pump command (or None to keep current).
            valve_command: Override valve command (or None to keep current).
            command_str: Description of the override.

        Returns:
            dict with the override commands.
        """
        if pump_command is not None:
            self._pump_command = pump_command
        if valve_command is not None:
            self._valve_command = valve_command
        self._control_command_str = command_str

        return {
            "pump_command": self._pump_command,
            "valve_command": self._valve_command,
            "control_command": self._control_command_str,
        }

    def _failsafe(self) -> dict:
        """Execute deterministic fail-safe: Pump=OFF, Valve=0%."""
        self._is_failsafe = True
        self._pump_command = 0
        self._valve_command = PARAMS.valve.safe_position_pct  # 0%
        self._control_command_str = "FAILSAFE"

        return {
            "pump_command": self._pump_command,
            "valve_command": self._valve_command,
            "control_command": self._control_command_str,
        }

    def reset(self, setpoint_m: float | None = None) -> None:
        """Reset the controller state."""
        if setpoint_m is not None:
            self.update_setpoint(setpoint_m)
        self._pump_command = 0
        self._valve_command = self._default_valve_pct
        self._control_command_str = "INIT"
        self._is_failsafe = False
