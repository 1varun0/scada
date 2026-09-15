"""
SCADA IDS — Scenario Definitions & Seeds

Deterministic scenario configurations for normal and attack data generation.
Each scenario_id maps to a complete configuration including random seed,
setpoint profile, operating condition, and (for attack scenarios) attack
parameters with start/end times.

Scenario ID conventions:
    N_001 – N_060   Normal operating scenarios
    A1_001 – A1_045  FDI attack scenarios
    A2_001 – A2_015  Replay attack scenarios
    A3_001 – A3_015  DoS attack scenarios
    A4_001 – A4_015  Authenticated Misuse scenarios
"""

from dataclasses import dataclass, field
from typing import Optional, List
from config.parameters import PARAMS


# ──────────────────────────────────────────────────────────────────────
# Setpoint Profile Types
# ──────────────────────────────────────────────────────────────────────
SETPOINT_CONSTANT = "constant"
SETPOINT_STEP = "step"
SETPOINT_RAMP = "ramp"


@dataclass
class SetpointProfile:
    """Defines how the tank level setpoint evolves over time."""
    profile_type: str = SETPOINT_CONSTANT
    initial_setpoint_m: float = 1.0
    final_setpoint_m: float = 1.0
    change_time_s: float = 400.0   # When step/ramp begins

    def get_setpoint(self, t: float, duration: float) -> float:
        """Return the setpoint at simulation time t."""
        if self.profile_type == SETPOINT_CONSTANT:
            return self.initial_setpoint_m
        elif self.profile_type == SETPOINT_STEP:
            return (self.final_setpoint_m if t >= self.change_time_s
                    else self.initial_setpoint_m)
        elif self.profile_type == SETPOINT_RAMP:
            if t <= self.change_time_s:
                return self.initial_setpoint_m
            ramp_duration = duration - self.change_time_s
            if ramp_duration <= 0:
                return self.final_setpoint_m
            progress = min((t - self.change_time_s) / ramp_duration, 1.0)
            return (self.initial_setpoint_m
                    + progress * (self.final_setpoint_m - self.initial_setpoint_m))
        else:
            raise ValueError(f"Unknown setpoint profile: {self.profile_type}")


# ──────────────────────────────────────────────────────────────────────
# Attack Configuration
# ──────────────────────────────────────────────────────────────────────
@dataclass
class AttackConfig:
    """Attack parameters for a single scenario."""
    attack_type: str = "None"           # "None", "FDI", "Replay", "DoS", "Auth_Misuse"
    attack_id: str = ""                 # Unique episode identifier
    attack_start_s: float = 300.0       # When attack begins
    attack_end_s: float = 350.0         # When attack ends
    parameter_type: str = ""            # "bias", "scale", "intermittent", etc.
    parameter_value: float = 0.0        # Numerical attack magnitude
    replay_buffer_s: float = 0.0        # For A2: how far back to replay
    unsafe_command: str = ""            # For A4: the unsafe command string
    description: str = ""


# ──────────────────────────────────────────────────────────────────────
# Scenario Configuration
# ──────────────────────────────────────────────────────────────────────
@dataclass
class ScenarioConfig:
    """Complete configuration for one simulation scenario."""
    scenario_id: str = ""
    random_seed: int = 42000
    duration_s: float = PARAMS.simulation.scenario_duration_s
    initial_level_m: float = PARAMS.tank.initial_level_m
    operating_condition: str = "Normal_Load"
    setpoint_profile: SetpointProfile = field(default_factory=SetpointProfile)
    attack: AttackConfig = field(default_factory=AttackConfig)

    # Convenience properties
    @property
    def is_attack(self) -> bool:
        return self.attack.attack_type != "None"


# ──────────────────────────────────────────────────────────────────────
# Scenario Generation Functions
# ──────────────────────────────────────────────────────────────────────

def _make_seed(index: int) -> int:
    """Deterministic seed: base + scenario index."""
    return PARAMS.simulation.base_random_seed + index


def generate_normal_scenarios() -> List[ScenarioConfig]:
    """Generate all 60 normal operating scenarios."""
    scenarios = []
    idx = 0

    # N_001 – N_020: Steady state, constant setpoint at 1.0m
    for i in range(1, 21):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"N_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            setpoint_profile=SetpointProfile(
                profile_type=SETPOINT_CONSTANT,
                initial_setpoint_m=1.0,
            ),
        ))

    # N_021 – N_035: Step change from 1.0 → 1.5m at t=400s
    for i in range(21, 36):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"N_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Setpoint_Change",
            setpoint_profile=SetpointProfile(
                profile_type=SETPOINT_STEP,
                initial_setpoint_m=1.0,
                final_setpoint_m=1.5,
                change_time_s=400.0,
            ),
        ))

    # N_036 – N_050: Ramp setpoint 0.8 → 1.4m
    for i in range(36, 51):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"N_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Variable_Load",
            setpoint_profile=SetpointProfile(
                profile_type=SETPOINT_RAMP,
                initial_setpoint_m=0.8,
                final_setpoint_m=1.4,
                change_time_s=200.0,
            ),
        ))

    # N_051 – N_060: Recovery from low level (H0=0.5m) to 1.0m
    for i in range(51, 61):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"N_{i:03d}",
            random_seed=_make_seed(idx),
            initial_level_m=0.5,
            operating_condition="Recovery",
            setpoint_profile=SetpointProfile(
                profile_type=SETPOINT_CONSTANT,
                initial_setpoint_m=1.0,
            ),
        ))

    return scenarios


def generate_attack_scenarios() -> List[ScenarioConfig]:
    """Generate all 110 attack scenarios."""
    scenarios = []
    idx = 100  # Offset seeds from normal scenarios

    # ── A1: FDI Bias — Small (b=0.05m) ──────────────────────────────
    for i in range(1, 11):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A1_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="FDI",
                attack_id=f"A1_{i:03d}_FDI_BIAS_SMALL",
                attack_start_s=300.0,
                attack_end_s=500.0,
                parameter_type="bias",
                parameter_value=0.05,
                description="FDI bias +0.05m on tank level",
            ),
        ))

    # ── A1: FDI Bias — Medium (b=0.10m) ─────────────────────────────
    for i in range(11, 21):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A1_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="FDI",
                attack_id=f"A1_{i:03d}_FDI_BIAS_MED",
                attack_start_s=300.0,
                attack_end_s=500.0,
                parameter_type="bias",
                parameter_value=0.10,
                description="FDI bias +0.10m on tank level",
            ),
        ))

    # ── A1: FDI Bias — Large (b=0.20m) ──────────────────────────────
    for i in range(21, 31):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A1_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="FDI",
                attack_id=f"A1_{i:03d}_FDI_BIAS_LARGE",
                attack_start_s=300.0,
                attack_end_s=500.0,
                parameter_type="bias",
                parameter_value=0.20,
                description="FDI bias +0.20m on tank level",
            ),
        ))

    # ── A1: FDI Scale (α=1.10) ──────────────────────────────────────
    for i in range(31, 41):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A1_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="FDI",
                attack_id=f"A1_{i:03d}_FDI_SCALE",
                attack_start_s=300.0,
                attack_end_s=500.0,
                parameter_type="scale",
                parameter_value=1.10,
                description="FDI scale ×1.10 on tank level",
            ),
        ))

    # ── A1: FDI Intermittent (b=0.15m, every 5th step) ─────────────
    for i in range(41, 46):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A1_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="FDI",
                attack_id=f"A1_{i:03d}_FDI_INTERMITTENT",
                attack_start_s=300.0,
                attack_end_s=500.0,
                parameter_type="intermittent",
                parameter_value=0.15,
                description="FDI intermittent bias +0.15m every 5th step",
            ),
        ))

    # ── A2: Replay (various buffer lengths 30–100s) ─────────────────
    buffer_lengths = [30, 40, 50, 60, 70, 80, 90, 100, 35, 45, 55, 65, 75, 85, 95]
    for i, buf_len in enumerate(buffer_lengths, start=1):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A2_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="Replay",
                attack_id=f"A2_{i:03d}_REPLAY_{buf_len}s",
                attack_start_s=400.0,
                attack_end_s=400.0 + buf_len,
                parameter_type="replay",
                parameter_value=float(buf_len),
                replay_buffer_s=float(buf_len),
                description=f"Replay attack with {buf_len}s buffer",
            ),
        ))

    # ── A3: DoS (various durations 20–120s) ─────────────────────────
    dos_durations = [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 25, 45, 75, 105]
    for i, dur in enumerate(dos_durations, start=1):
        idx += 1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A3_{i:03d}",
            random_seed=_make_seed(idx),
            operating_condition="Steady_State",
            attack=AttackConfig(
                attack_type="DoS",
                attack_id=f"A3_{i:03d}_DOS_{dur}s",
                attack_start_s=350.0,
                attack_end_s=350.0 + dur,
                parameter_type="dos_duration",
                parameter_value=float(dur),
                description=f"DoS blocking for {dur}s",
            ),
        ))

    # ── A4: Authenticated Misuse (various unsafe commands) ──────────
    misuse_configs = [
        ("VALVE_SET_80", "valve_open_at_low", 80.0),
        ("VALVE_SET_90", "valve_open_at_low", 90.0),
        ("VALVE_SET_100", "valve_open_at_low", 100.0),
        ("PUMP_ON_AT_HIGH", "pump_on_at_high", 1.0),
        ("VALVE_SET_70", "valve_open_at_low", 70.0),
        ("VALVE_SET_95", "valve_open_at_low", 95.0),
        ("PUMP_ON_AT_OVERFLOW", "pump_on_at_high", 1.0),
        ("VALVE_SET_85", "valve_open_at_low", 85.0),
        ("VALVE_SET_75", "valve_open_at_low", 75.0),
        ("PUMP_ON_AT_CRIT_HIGH", "pump_on_at_high", 1.0),
        ("VALVE_SET_60", "valve_open_at_low", 60.0),
        ("VALVE_SET_100_SUSTAINED", "valve_open_at_low", 100.0),
        ("PUMP_FORCE_ON", "pump_on_at_high", 1.0),
        ("VALVE_SET_80_LONG", "valve_open_at_low", 80.0),
        ("VALVE_SET_90_LONG", "valve_open_at_low", 90.0),
    ]
    for i, (cmd, ptype, pval) in enumerate(misuse_configs, start=1):
        idx += 1
        # Start from a low-level condition to make the misuse dangerous
        init_level = 0.4 if "valve_open" in ptype else 2.1
        scenarios.append(ScenarioConfig(
            scenario_id=f"A4_{i:03d}",
            random_seed=_make_seed(idx),
            initial_level_m=init_level,
            operating_condition="Misuse_Condition",
            attack=AttackConfig(
                attack_type="Auth_Misuse",
                attack_id=f"A4_{i:03d}_MISUSE_{cmd}",
                attack_start_s=200.0,
                attack_end_s=300.0,
                parameter_type=ptype,
                parameter_value=pval,
                unsafe_command=cmd,
                description=f"Authenticated misuse: {cmd}",
            ),
        ))

    return scenarios


def get_all_scenarios() -> List[ScenarioConfig]:
    """Return all normal + attack scenarios."""
    return generate_normal_scenarios() + generate_attack_scenarios()


def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioConfig]:
    """Look up a single scenario by its ID."""
    for s in get_all_scenarios():
        if s.scenario_id == scenario_id:
            return s
    return None
