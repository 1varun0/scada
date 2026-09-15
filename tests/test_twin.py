"""
Unit Tests — Digital Twin

Tests:
- Independence from observed values
- Reinitialization correctness
- Residual computation
- Drift behavior over time
"""

import pytest
from digital_twin.physics_twin import PhysicsTwin
from config.parameters import PARAMS


class TestPhysicsTwin:
    """Tests for the Independent Physics Digital Twin."""

    def test_initial_level(self):
        """Twin initializes at the specified level."""
        twin = PhysicsTwin(initial_level_m=1.5)
        assert twin.level == 1.5

    def test_step_with_inflow(self):
        """Twin level rises with net inflow."""
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0)
        new_level = twin.step(q_in=0.005, q_out=0.0, dt=1.0)
        expected = 1.0 + 0.005 / 2.0
        assert abs(new_level - expected) < 1e-10

    def test_step_with_outflow(self):
        """Twin level drops with net outflow."""
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0)
        new_level = twin.step(q_in=0.0, q_out=0.004, dt=1.0)
        expected = 1.0 - 0.004 / 2.0
        assert abs(new_level - expected) < 1e-10

    def test_residual_zero_when_aligned(self):
        """Residual is zero when observed equals predicted."""
        twin = PhysicsTwin(initial_level_m=1.0)
        residual = twin.compute_residual(h_observed=1.0)
        assert abs(residual) < 1e-10

    def test_residual_positive_when_observed_higher(self):
        """Positive residual when observed > predicted (potential FDI bias)."""
        twin = PhysicsTwin(initial_level_m=1.0)
        residual = twin.compute_residual(h_observed=1.05)
        assert abs(residual - 0.05) < 1e-10

    def test_residual_negative_when_observed_lower(self):
        """Negative residual when observed < predicted."""
        twin = PhysicsTwin(initial_level_m=1.0)
        residual = twin.compute_residual(h_observed=0.95)
        assert abs(residual - (-0.05)) < 1e-10

    def test_independence_from_observed(self):
        """Twin state is NOT affected by residual computation.

        This is the critical independence test: computing the residual
        with an arbitrary H_observed must not change the Twin's state.
        """
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0)

        # Step the twin
        twin.step(q_in=0.005, q_out=0.004, dt=1.0)
        level_before = twin.level

        # Compute residual with a very different observed value
        twin.compute_residual(h_observed=5.0)

        # Twin level must NOT change
        assert twin.level == level_before

    def test_reinitialization(self):
        """Reset restores Twin to a new initial condition."""
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0)

        # Run some steps to change level
        for _ in range(100):
            twin.step(q_in=0.005, q_out=0.004, dt=1.0)
        assert twin.level != 1.0

        # Reinitialize
        twin.reset(initial_level_m=0.8)
        assert twin.level == 0.8

    def test_twin_tracks_tank_physics(self):
        """Twin with same inputs as tank produces same trajectory.

        This validates that the Twin uses the same physics equation
        as the actual tank model.
        """
        from simulator.tank import Tank

        tank = Tank(initial_level_m=1.0, area_m2=2.0, max_height_m=2.5)
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0, max_height_m=2.5)

        q_in = 0.005
        q_out = 0.003
        dt = 1.0

        for _ in range(50):
            tank.step(q_in, q_out, dt)
            twin.step(q_in, q_out, dt)

        # Should be identical
        assert abs(tank.level - twin.level) < 1e-10

    def test_bounds_clamping(self):
        """Twin clamps level to [0, H_max]."""
        twin = PhysicsTwin(initial_level_m=0.01, area_m2=1.0, max_height_m=2.5)
        new_level = twin.step(q_in=0.0, q_out=1.0, dt=1.0)
        assert new_level == 0.0

        twin2 = PhysicsTwin(initial_level_m=2.49, area_m2=1.0, max_height_m=2.5)
        new_level2 = twin2.step(q_in=1.0, q_out=0.0, dt=1.0)
        assert new_level2 == 2.5

    def test_drift_over_many_steps(self):
        """Twin vs tank with noisy inputs drifts over time.

        This demonstrates why Option B (per-scenario reinit) is needed:
        if inputs differ slightly, the twin drifts.
        """
        from simulator.tank import Tank

        tank = Tank(initial_level_m=1.0, area_m2=2.0)
        twin = PhysicsTwin(initial_level_m=1.0, area_m2=2.0)

        dt = 1.0
        for _ in range(500):
            # Tank gets true flows, twin gets slightly noisy flows
            q_in = 0.005
            q_out = 0.003
            tank.step(q_in, q_out, dt)
            twin.step(q_in + 0.0001, q_out, dt)  # Slight noise

        # Drift should be measurable
        assert abs(tank.level - twin.level) > 0.01
