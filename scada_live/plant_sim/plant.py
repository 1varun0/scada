"""
LivePlant — Real-time single-tank water SCADA plant simulator.
"""

from simulator.tank import Tank
from simulator.pump import Pump
from simulator.valve import Valve
from simulator.noise import NoiseGenerator
from simulator.controller import Controller
from scada_live.common.packets import TelemetryPacket

class LivePlant:
    def __init__(self, cfg, seed=42000, standalone_mode=False):
        """
        Args:
            cfg: Loaded config namespace (from config_loader).
            seed: Random seed for noise reproducibility.
            standalone_mode: If True, run the built-in hysteresis controller.
                           If False, plant only executes externally-received commands.
        """
        self.cfg = cfg
        self.seed = seed
        self.standalone_mode = standalone_mode
        self.dt = cfg.simulation.dt_s
        
        self.tank = Tank(initial_level_m=cfg.tank.initial_level_m, area_m2=cfg.tank.cross_section_area_m2, max_height_m=cfg.tank.max_height_m)
        self.pump = Pump(initial_state=0, q_max_m3s=cfg.pump.q_max_m3s, response_delay_s=cfg.pump.response_delay_s, dt_s=self.dt)
        self.valve = Valve(initial_position_pct=cfg.controller.default_valve_pct, flow_coefficient_m3s=cfg.valve.flow_coefficient_m3s, response_time_s=cfg.valve.response_time_s, dt_s=self.dt)
        clamp = getattr(cfg.simulation, 'clamp_flow_noise', False)
        self.noise = NoiseGenerator(seed=seed, level_noise_std=cfg.simulation.sensor_noise_level_m, flow_noise_std=cfg.simulation.sensor_noise_flow_m3s, clamp_flow_noise=clamp)
        
        if self.standalone_mode:
            self.controller = Controller(setpoint_m=cfg.controller.setpoint_m, deadband_m=cfg.controller.deadband_m, default_valve_pct=cfg.controller.default_valve_pct)
        else:
            self.controller = None
            
        self.tick_counter = 0
        self.simulation_time_s = 0.0
        
        self.overflow_count = 0
        self.dry_run_count = 0

    def apply_command(self, pump_value: str) -> None:
        """Apply an external pump command ("ON" / "OFF")."""
        if pump_value == "ON":
            self.pump.set_command(1)
        elif pump_value == "OFF":
            self.pump.set_command(0)

    def observe(self) -> float:
        """Step 1-2: Read true level and add noise."""
        self.last_true_level = self.tank.level
        self.last_observed_level = self.noise.add_level_noise(self.last_true_level)
        return self.last_observed_level

    def advance(self, pump_cmd: int, valve_cmd: float) -> TelemetryPacket:
        """Step 4-9: Apply commands, step actuators, return packet."""
        self.pump.set_command(pump_cmd)
        self.valve.set_command(valve_cmd)

        self.pump.step()
        self.valve.step()

        q_in_true = self.pump.flow
        q_out_true = self.valve.compute_outflow(self.last_true_level)

        q_in_observed = self.noise.add_flow_noise(q_in_true)
        q_out_observed = self.noise.add_flow_noise(q_out_true)

        new_level = self.tank.step(q_in_true, q_out_true, self.dt)

        if new_level >= self.cfg.tank.overflow_m:
            self.overflow_count += 1
        if new_level <= 0.0:
            self.dry_run_count += 1

        pkt = TelemetryPacket(
            seq=self.tick_counter,
            run_id=getattr(self, "run_id", "live_run"),
            ts=self.simulation_time_s,
            src_t=self.simulation_time_s,
            received=True,
            level_m=self.last_observed_level,
            q_in=q_in_observed,
            q_out=q_out_observed,
            pump_on=(self.pump.state == 1),
            pump_cmd=self.pump.command,
            valve_pct=self.valve.position,
            valve_cmd=self.valve.command,
            _true_level=self.last_true_level,
            _attack_active=False,
            _attack_type="None"
        )

        self.tick_counter += 1
        self.simulation_time_s += self.dt
        return pkt

    def step(self) -> TelemetryPacket:
        """Standalone step for tests and Phase 1."""
        observed = self.observe()
        if self.standalone_mode:
            ctrl = self.controller.step(observed)
            return self.advance(ctrl["pump_command"], ctrl["valve_command"])
        else:
            # Non-standalone mode typically relies on observe() and advance() being called explicitly,
            # but if step() is called, preserve existing commands.
            return self.advance(self.pump.command, self.valve.command)

    def reset(self) -> None:
        """Reset plant to initial conditions."""
        self.tank.reset(self.cfg.tank.initial_level_m)
        self.pump.reset(0)
        self.valve.reset(self.cfg.controller.default_valve_pct)
        self.noise = NoiseGenerator(seed=self.seed, level_noise_std=self.cfg.simulation.sensor_noise_level_m, flow_noise_std=self.cfg.simulation.sensor_noise_flow_m3s)
        if self.standalone_mode:
            self.controller.reset(self.cfg.controller.setpoint_m)
        self.tick_counter = 0
        self.simulation_time_s = 0.0
        self.overflow_count = 0
        self.dry_run_count = 0
