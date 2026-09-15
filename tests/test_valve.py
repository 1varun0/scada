"""
Unit Tests — Valve Model

Tests:
- Outflow model (Cv * V%/100 * sqrt(H))
- Slew-rate limiting
- Position bounds
- Zero-level outflow
"""

import math
import pytest
from simulator.valve import Valve


class TestValve:
    """Tests for the Valve model."""

    def test_initial_position(self):
        """Valve starts at specified position."""
        valve = Valve(initial_position_pct=50.0)
        assert valve.position == 50.0
        assert valve.command == 50.0

    def test_outflow_at_100_pct(self):
        """Full-open valve outflow matches Cv * sqrt(H)."""
        valve = Valve(initial_position_pct=100.0, flow_coefficient_m3s=0.004)
        q = valve.compute_outflow(tank_level_m=1.0)
        expected = 0.004 * 1.0 * math.sqrt(1.0)  # 0.004
        assert abs(q - expected) < 1e-10

    def test_outflow_at_50_pct(self):
        """Half-open valve delivers half of max outflow."""
        valve = Valve(initial_position_pct=50.0, flow_coefficient_m3s=0.004)
        q = valve.compute_outflow(tank_level_m=1.0)
        expected = 0.004 * 0.5 * math.sqrt(1.0)  # 0.002
        assert abs(q - expected) < 1e-10

    def test_outflow_at_zero_pct(self):
        """Closed valve delivers zero outflow."""
        valve = Valve(initial_position_pct=0.0, flow_coefficient_m3s=0.004)
        q = valve.compute_outflow(tank_level_m=1.0)
        assert q == 0.0

    def test_outflow_at_zero_level(self):
        """Zero tank level means zero outflow regardless of position."""
        valve = Valve(initial_position_pct=100.0, flow_coefficient_m3s=0.004)
        q = valve.compute_outflow(tank_level_m=0.0)
        assert q == 0.0

    def test_outflow_negative_level(self):
        """Negative tank level returns zero outflow."""
        valve = Valve(initial_position_pct=100.0)
        q = valve.compute_outflow(tank_level_m=-0.5)
        assert q == 0.0

    def test_outflow_sqrt_dependency(self):
        """Outflow scales with sqrt(H)."""
        valve = Valve(initial_position_pct=100.0, flow_coefficient_m3s=0.004)
        q1 = valve.compute_outflow(tank_level_m=1.0)
        q4 = valve.compute_outflow(tank_level_m=4.0)
        # sqrt(4) / sqrt(1) = 2
        assert abs(q4 / q1 - 2.0) < 1e-10

    def test_slew_rate_limiting(self):
        """Valve position changes gradually due to slew rate."""
        # response_time=1.5s means full range (100%) in 1.5s
        # slew_rate = 100/1.5 ≈ 66.67 %/s
        valve = Valve(
            initial_position_pct=0.0,
            response_time_s=1.5,
            dt_s=1.0,
        )
        valve.set_command(100.0)
        valve.step()

        # After 1s at 66.67%/s, should be at ~66.67%
        max_change = 100.0 / 1.5 * 1.0
        assert abs(valve.position - max_change) < 0.01

    def test_slew_reaches_target(self):
        """Valve eventually reaches commanded position."""
        valve = Valve(
            initial_position_pct=0.0,
            response_time_s=1.5,
            dt_s=1.0,
        )
        valve.set_command(100.0)
        for _ in range(10):  # More than enough steps
            valve.step()
        assert abs(valve.position - 100.0) < 0.01

    def test_position_bounds(self):
        """Position is clamped to [0, 100]."""
        valve = Valve(initial_position_pct=50.0)
        valve.set_command(150.0)  # Over max
        assert valve.command == 100.0

        valve.set_command(-10.0)  # Under min
        assert valve.command == 0.0

    def test_reset(self):
        """Reset sets both command and position."""
        valve = Valve(initial_position_pct=50.0)
        valve.set_command(100.0)
        valve.step()

        valve.reset(25.0)
        assert valve.position == 25.0
        assert valve.command == 25.0
