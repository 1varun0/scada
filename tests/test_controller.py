"""
Unit Tests — Controller Model

Tests:
- Hysteresis (bang-bang) logic
- Fail-safe activation
- Setpoint updates
- Command overrides (for A4 misuse)
"""

import pytest
from simulator.controller import Controller
from config.parameters import PARAMS


class TestController:
    """Tests for the Hysteresis Controller."""

    def test_pump_on_below_threshold(self):
        """Pump turns ON when level drops below setpoint - deadband."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)
        result = ctrl.step(observed_level_m=0.7)  # Below 0.8
        assert result["pump_command"] == 1

    def test_pump_off_above_threshold(self):
        """Pump turns OFF when level rises above setpoint + deadband."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)
        result = ctrl.step(observed_level_m=1.3)  # Above 1.2
        assert result["pump_command"] == 0

    def test_hysteresis_hold_in_deadband(self):
        """Pump maintains state within the deadband."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)

        # First go low to turn pump ON
        ctrl.step(observed_level_m=0.7)
        assert ctrl.pump_command == 1

        # Now within deadband — should hold ON
        result = ctrl.step(observed_level_m=1.0)
        assert result["pump_command"] == 1
        assert result["control_command"] == "HOLD"

    def test_failsafe_on_dos(self):
        """Fail-safe activates on DoS: Pump=OFF, Valve=0%."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)

        # First turn pump ON
        ctrl.step(observed_level_m=0.7)
        assert ctrl.pump_command == 1

        # DoS — should enter fail-safe
        result = ctrl.step(observed_level_m=0.7, dos_active=True)
        assert result["pump_command"] == 0
        assert result["valve_command"] == PARAMS.valve.safe_position_pct  # 0%
        assert result["control_command"] == "FAILSAFE"
        assert ctrl.is_failsafe

    def test_failsafe_exits_when_dos_ends(self):
        """Controller resumes normal operation when DoS ends."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)

        ctrl.step(observed_level_m=0.7, dos_active=True)
        assert ctrl.is_failsafe

        result = ctrl.step(observed_level_m=0.7, dos_active=False)
        assert not ctrl.is_failsafe
        assert result["pump_command"] == 1  # Low level → pump ON

    def test_setpoint_update(self):
        """Setpoint update changes thresholds."""
        ctrl = Controller(setpoint_m=1.0, deadband_m=0.2)

        # At level 1.3: above 1.2 → pump OFF
        ctrl.step(observed_level_m=1.3)
        assert ctrl.pump_command == 0

        # Update setpoint to 1.5 → new thresholds: 1.3 / 1.7
        ctrl.update_setpoint(1.5)
        # At level 1.3: exactly at threshold, pump ON
        ctrl.step(observed_level_m=1.25)
        assert ctrl.pump_command == 1

    def test_override_command(self):
        """Override forces specific commands (for A4 misuse)."""
        ctrl = Controller(setpoint_m=1.0)
        result = ctrl.override_command(
            pump_command=1,
            valve_command=80.0,
            command_str="VALVE_SET_80",
        )
        assert result["pump_command"] == 1
        assert result["valve_command"] == 80.0
        assert result["control_command"] == "VALVE_SET_80"

    def test_reset(self):
        """Reset returns controller to initial state."""
        ctrl = Controller(setpoint_m=1.0)
        ctrl.step(observed_level_m=0.7)
        assert ctrl.pump_command == 1

        ctrl.reset()
        assert ctrl.pump_command == 0
        assert ctrl.control_command_str == "INIT"
        assert not ctrl.is_failsafe
