"""
Unit Tests — Process Simulator & Scenario Runner

Integration tests:
- End-to-end scenario execution
- Deterministic replay (same seed → same output)
- Record structure validation
- Telemetry field completeness
"""

import pytest
from config.scenarios import ScenarioConfig, SetpointProfile, SETPOINT_CONSTANT
from simulator.process_simulator import ProcessSimulator
from config.parameters import PARAMS


class TestProcessSimulator:
    """Integration tests for the ProcessSimulator."""

    def _make_scenario(self, **kwargs) -> ScenarioConfig:
        """Helper to create a test scenario."""
        defaults = {
            "scenario_id": "TEST_001",
            "random_seed": 99999,
            "duration_s": 10.0,  # Short for tests
            "initial_level_m": 1.0,
            "operating_condition": "Test",
            "setpoint_profile": SetpointProfile(
                profile_type=SETPOINT_CONSTANT,
                initial_setpoint_m=1.0,
            ),
        }
        defaults.update(kwargs)
        return ScenarioConfig(**defaults)

    def test_produces_correct_number_of_records(self):
        """Simulator produces T/Δt records."""
        scenario = self._make_scenario(duration_s=10.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()
        expected_steps = int(10.0 / PARAMS.simulation.dt_s)
        assert len(records) == expected_steps

    def test_record_has_required_fields(self):
        """Each record contains all required telemetry fields."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        required_fields = [
            "scenario_id", "sequence_id", "simulation_time_s",
            "source_time_s", "data_age_ms", "packet_received",
            "communication_status", "operating_condition",
            "tank_level_setpoint", "tank_level_observed",
            "q_in", "q_out", "pump_command", "pump_state",
            "valve_command", "valve_state", "control_command",
            "user_id", "user_role", "is_authenticated", "is_authorized",
            "attack_type", "ground_truth",
        ]
        for field in required_fields:
            assert field in records[0], f"Missing field: {field}"

    def test_sequence_id_increments(self):
        """Sequence IDs are sequential starting from 0."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        for i, r in enumerate(records):
            assert r["sequence_id"] == i

    def test_simulation_time_increments(self):
        """Simulation time increments by Δt."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        dt = PARAMS.simulation.dt_s
        for i, r in enumerate(records):
            assert abs(r["simulation_time_s"] - i * dt) < 1e-10

    def test_normal_ground_truth(self):
        """All records from base simulator have ground_truth=0."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        for r in records:
            assert r["ground_truth"] == 0
            assert r["attack_type"] == "None"

    def test_deterministic_replay(self):
        """Same seed produces identical output."""
        scenario = self._make_scenario(random_seed=42, duration_s=10.0)

        sim1 = ProcessSimulator(scenario)
        records1 = sim1.run()

        sim2 = ProcessSimulator(scenario)
        records2 = sim2.run()

        for r1, r2 in zip(records1, records2):
            assert r1["tank_level_observed"] == r2["tank_level_observed"]
            assert r1["q_in"] == r2["q_in"]
            assert r1["q_out"] == r2["q_out"]

    def test_different_seeds_produce_different_noise(self):
        """Different seeds produce different noise patterns."""
        s1 = self._make_scenario(random_seed=1, duration_s=10.0)
        s2 = self._make_scenario(random_seed=2, duration_s=10.0)

        r1 = ProcessSimulator(s1).run()
        r2 = ProcessSimulator(s2).run()

        # Observed levels should differ due to different noise
        levels_differ = any(
            r1[i]["tank_level_observed"] != r2[i]["tank_level_observed"]
            for i in range(len(r1))
        )
        assert levels_differ

    def test_tank_level_changes(self):
        """Tank level actually changes during simulation."""
        scenario = self._make_scenario(duration_s=100.0, initial_level_m=0.5)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        # With H0=0.5 < 0.8, pump should turn ON and level should rise
        first_level = records[0]["_true_level"]
        last_level = records[-1]["_true_level"]
        assert last_level > first_level

    def test_internal_fields_present(self):
        """Internal fields (_true_level, etc.) are present for Twin validation."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        assert "_true_level" in records[0]
        assert "_q_in_true" in records[0]
        assert "_q_out_true" in records[0]

    def test_normal_comms(self):
        """Base simulator always produces NORMAL communication status."""
        scenario = self._make_scenario(duration_s=5.0)
        sim = ProcessSimulator(scenario)
        records = sim.run()

        for r in records:
            assert r["packet_received"] == 1
            assert r["communication_status"] == "NORMAL"
            assert r["data_age_ms"] == 0
