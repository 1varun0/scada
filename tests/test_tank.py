"""
Unit Tests — Tank Physics Model

Tests:
- Mass balance correctness
- Boundary clipping (0, H_max)
- Steady-state behavior
- Reset functionality
"""

import pytest
from simulator.tank import Tank
from config.parameters import PARAMS


class TestTank:
    """Tests for the Tank physics model."""

    def test_initial_level(self):
        """Tank initializes at the specified level."""
        tank = Tank(initial_level_m=1.5)
        assert tank.level == 1.5

    def test_default_initial_level(self):
        """Tank defaults to PARAMS initial level."""
        tank = Tank()
        assert tank.level == PARAMS.tank.initial_level_m

    def test_mass_balance_fill(self):
        """Tank level rises with net inflow."""
        tank = Tank(initial_level_m=1.0, area_m2=2.0)
        q_in = 0.005  # m³/s
        q_out = 0.0
        dt = 1.0

        new_level = tank.step(q_in, q_out, dt)
        expected = 1.0 + (0.005 - 0.0) / 2.0 * 1.0  # 1.0025
        assert abs(new_level - expected) < 1e-10

    def test_mass_balance_drain(self):
        """Tank level drops with net outflow."""
        tank = Tank(initial_level_m=1.0, area_m2=2.0)
        q_in = 0.0
        q_out = 0.004
        dt = 1.0

        new_level = tank.step(q_in, q_out, dt)
        expected = 1.0 + (0.0 - 0.004) / 2.0 * 1.0  # 0.998
        assert abs(new_level - expected) < 1e-10

    def test_mass_balance_steady(self):
        """Tank level unchanged when inflow equals outflow."""
        tank = Tank(initial_level_m=1.0, area_m2=2.0)
        q_in = 0.003
        q_out = 0.003
        dt = 1.0

        new_level = tank.step(q_in, q_out, dt)
        assert abs(new_level - 1.0) < 1e-10

    def test_clamp_upper(self):
        """Tank level clamped at H_max."""
        tank = Tank(initial_level_m=2.49, max_height_m=2.5, area_m2=1.0)
        # Large inflow should push past max
        new_level = tank.step(q_in=1.0, q_out=0.0, dt=1.0)
        assert new_level == 2.5

    def test_clamp_lower(self):
        """Tank level clamped at 0."""
        tank = Tank(initial_level_m=0.01, area_m2=1.0)
        # Large outflow should push below 0
        new_level = tank.step(q_in=0.0, q_out=1.0, dt=1.0)
        assert new_level == 0.0

    def test_initial_level_clamped(self):
        """Initial level outside bounds is clamped."""
        tank = Tank(initial_level_m=5.0, max_height_m=2.5)
        assert tank.level == 2.5

        tank2 = Tank(initial_level_m=-1.0)
        assert tank2.level == 0.0

    def test_multiple_steps(self):
        """Multiple steps accumulate correctly."""
        tank = Tank(initial_level_m=1.0, area_m2=2.0)
        for _ in range(100):
            tank.step(q_in=0.005, q_out=0.004, dt=1.0)

        # After 100 steps: 1.0 + 100 * (0.001/2.0) = 1.05
        expected = 1.0 + 100 * 0.001 / 2.0
        assert abs(tank.level - expected) < 1e-8

    def test_reset(self):
        """Tank reset changes level."""
        tank = Tank(initial_level_m=1.0)
        tank.step(0.005, 0.0, 1.0)
        assert tank.level != 1.0

        tank.reset(1.0)
        assert tank.level == 1.0

    def test_properties(self):
        """Properties return correct values."""
        tank = Tank(initial_level_m=1.0, area_m2=2.0, max_height_m=2.5)
        assert tank.area == 2.0
        assert tank.max_height == 2.5
