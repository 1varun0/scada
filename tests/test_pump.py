"""
Unit Tests — Pump Model

Tests:
- ON/OFF flow delivery
- Response delay behavior
- Command vs state tracking
- Reset functionality
"""

import pytest
from simulator.pump import Pump


class TestPump:
    """Tests for the ON/OFF Pump model."""

    def test_initial_off(self):
        """Pump starts OFF with zero flow."""
        pump = Pump(initial_state=0)
        assert pump.state == 0
        assert pump.flow == 0.0

    def test_initial_on(self):
        """Pump can start ON."""
        pump = Pump(initial_state=1, q_max_m3s=0.005)
        assert pump.state == 1
        assert pump.flow == 0.005

    def test_flow_rate_on(self):
        """ON pump delivers q_max flow."""
        pump = Pump(initial_state=1, q_max_m3s=0.005)
        assert pump.flow == 0.005

    def test_flow_rate_off(self):
        """OFF pump delivers zero flow."""
        pump = Pump(initial_state=0)
        assert pump.flow == 0.0

    def test_response_delay(self):
        """Pump doesn't transition immediately — respects delay."""
        pump = Pump(initial_state=0, response_delay_s=2.0, dt_s=1.0)
        pump.set_command(1)

        # Step 1: command issued, delay not reached
        pump.step()
        assert pump.command == 1
        assert pump.state == 0  # Still OFF

        # Step 2: delay reached (2 steps for 2s delay at 1s dt)
        pump.step()
        assert pump.state == 1  # Now ON

    def test_immediate_if_no_change(self):
        """No delay if command matches current state."""
        pump = Pump(initial_state=1, response_delay_s=2.0, dt_s=1.0)
        pump.set_command(1)  # Same as current
        pump.step()
        assert pump.state == 1  # Still ON, no transition needed

    def test_command_tracking(self):
        """Command and state are tracked independently."""
        pump = Pump(initial_state=0, response_delay_s=3.0, dt_s=1.0)
        pump.set_command(1)

        assert pump.command == 1
        assert pump.state == 0

    def test_reset(self):
        """Reset sets both command and state."""
        pump = Pump(initial_state=0)
        pump.set_command(1)
        pump.step()
        pump.step()

        pump.reset(0)
        assert pump.command == 0
        assert pump.state == 0
        assert pump.flow == 0.0

    def test_rapid_toggle(self):
        """Rapid toggle doesn't cause issues."""
        pump = Pump(initial_state=0, response_delay_s=2.0, dt_s=1.0)
        pump.set_command(1)
        pump.step()
        pump.set_command(0)  # Toggle back before ON takes effect
        pump.step()
        pump.step()
        # Should be OFF since last command was OFF
        assert pump.state == 0
