"""
SCADA IDS — Process Simulator

Orchestrates a single scenario: initializes tank, pump, valve, controller,
and noise generator, then steps through T/Δt timesteps producing a complete
telemetry record per step.

This is the core simulation engine. It does NOT apply attacks — that is
handled by the attack modules which post-process the telemetry records.
"""

from typing import List, Dict, Any

from config.parameters import PARAMS
from config.scenarios import ScenarioConfig
from simulator.tank import Tank
from simulator.pump import Pump
from simulator.valve import Valve
from simulator.controller import Controller
from simulator.noise import NoiseGenerator


class ProcessSimulator:
    """Runs a single scenario and produces raw telemetry records.

    The simulator generates the *true* physical process data. Attack
    modifications are applied externally by the attack modules.
    """

    def __init__(self, scenario: ScenarioConfig):
        self._scenario = scenario
        self._dt = PARAMS.simulation.dt_s
        self._total_steps = int(scenario.duration_s / self._dt)

        # Initialize components
        self._tank = Tank(initial_level_m=scenario.initial_level_m)
        self._pump = Pump(initial_state=0)
        self._valve = Valve(initial_position_pct=PARAMS.controller.default_valve_pct)
        self._controller = Controller(
            setpoint_m=scenario.setpoint_profile.initial_setpoint_m,
        )
        self._noise = NoiseGenerator(seed=scenario.random_seed)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def scenario(self) -> ScenarioConfig:
        return self._scenario

    @property
    def tank(self) -> Tank:
        return self._tank

    # ── Simulation ───────────────────────────────────────────────────

    def run(self) -> List[Dict[str, Any]]:
        """Execute the full scenario and return telemetry records.

        Returns:
            List of telemetry dicts, one per timestep.
        """
        records = []

        for step_idx in range(self._total_steps):
            t = step_idx * self._dt
            record = self._step(step_idx, t)
            records.append(record)

        return records

    def _step(self, sequence_id: int, t: float) -> Dict[str, Any]:
        """Execute one simulation timestep.

        Flow:
        1. Update setpoint from profile
        2. Read true sensor values + add noise
        3. Controller decides based on observed (noisy) level
        4. Apply commands to pump and valve
        5. Compute flows
        6. Step tank physics
        7. Build telemetry record
        """
        # 1. Update setpoint from scenario profile
        current_setpoint = self._scenario.setpoint_profile.get_setpoint(
            t, self._scenario.duration_s
        )
        self._controller.update_setpoint(current_setpoint)

        # 2. Read true state + add sensor noise
        true_level = self._tank.level
        observed_level = self._noise.add_level_noise(true_level)

        # 3. Controller decides (no DoS in base simulator)
        ctrl = self._controller.step(observed_level, dos_active=False)

        # 4. Apply commands to actuators
        self._pump.set_command(ctrl["pump_command"])
        self._pump.step()
        self._valve.set_command(ctrl["valve_command"])
        self._valve.step()

        # 5. Compute flows
        q_in_true = self._pump.flow
        q_out_true = self._valve.compute_outflow(true_level)

        # Add noise to flow measurements
        q_in_observed = self._noise.add_flow_noise(q_in_true)
        q_out_observed = self._noise.add_flow_noise(q_out_true)

        # 6. Step tank physics (uses TRUE flows, not noisy ones)
        new_level = self._tank.step(q_in_true, q_out_true, self._dt)

        # 7. Build telemetry record
        record = {
            # Identity
            "scenario_id": self._scenario.scenario_id,
            "sequence_id": sequence_id,

            # Time — normal operation: source_time == simulation_time
            "simulation_time_s": t,
            "source_time_s": t,
            "data_age_ms": 0,

            # Communication — normal
            "packet_received": 1,
            "communication_status": "NORMAL",

            # Operating state
            "operating_condition": self._scenario.operating_condition,
            "tank_level_setpoint": current_setpoint,

            # Physical process (observed/noisy values)
            "tank_level_observed": observed_level,
            "q_in": q_in_observed,
            "q_out": q_out_observed,

            # Actuation
            "pump_command": ctrl["pump_command"],
            "pump_state": self._pump.state,
            "valve_command": ctrl["valve_command"],
            "valve_state": self._valve.position,
            "control_command": ctrl["control_command"],

            # Cyber/Auth — default normal operator
            "user_id": "operator_01",
            "user_role": "operator",
            "is_authenticated": 1,
            "is_authorized": 1,

            # Ground truth — base simulator always produces normal data
            "attack_type": "None",
            "attack_parameter": None,
            "ground_truth": 0,
            "replay_source_sequence_id": None,

            # Internal state for Digital Twin / E0 validation
            "_true_level": true_level,
            "_q_in_true": q_in_true,
            "_q_out_true": q_out_true,
        }

        return record
