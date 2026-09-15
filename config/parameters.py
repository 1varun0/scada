"""
SCADA IDS — Frozen Physical Parameter Sheet

All numerical constants for the single-tank water SCADA simulation.
These values are frozen for the entire project lifecycle. Every dataset
value, Digital Twin prediction, and detection threshold depends on them.

DO NOT modify these values after Phase 1 validation (E0) without
re-running the entire pipeline.
"""

from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────────
# Tank Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class TankParams:
    """Cylindrical single-tank physical parameters."""
    cross_section_area_m2: float = 2.0       # A — ≈1.6 m diameter
    max_height_m: float = 2.5                # H_max — physical ceiling
    initial_level_m: float = 1.0             # H_0 — 40% fill
    critical_low_m: float = 0.3              # H_crit_low — cavitation risk
    critical_high_m: float = 2.3             # H_crit_high — overflow risk
    overflow_m: float = 2.5                  # H_overflow — absolute max


# ──────────────────────────────────────────────────────────────────────
# Pump Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class PumpParams:
    """ON/OFF pump with fixed flow rate and response delay."""
    q_max_m3s: float = 0.005                 # 5 L/s ≈ 80 GPM
    q_min_m3s: float = 0.005                 # Same as max (binary pump)
    response_delay_s: float = 2.0            # τ_pump — mechanical inertia
    # Pump is binary: ON delivers q_max, OFF delivers 0.


# ──────────────────────────────────────────────────────────────────────
# Valve Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ValveParams:
    """Continuously variable valve with gravity-driven outflow model.

    Outflow model: Q_out = Cv * (V% / 100) * sqrt(H)
    """
    range_min_pct: float = 0.0               # Fully closed
    range_max_pct: float = 100.0             # Fully open
    flow_coefficient_m3s: float = 0.004      # Cv — max outflow at 100%
    response_time_s: float = 1.5             # τ_valve — actuator slew
    safe_position_pct: float = 0.0           # V_safe — fail-safe: closed


# ──────────────────────────────────────────────────────────────────────
# Controller Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ControllerParams:
    """Hysteresis (bang-bang) controller with deterministic fail-safe.

    Pump ON  when H < setpoint - deadband
    Pump OFF when H > setpoint + deadband

    Fail-safe (DoS): Pump = OFF, Valve = V_safe (0%)
    """
    setpoint_m: float = 1.0                  # H_sp — nominal level
    control_interval_s: float = 1.0          # T_c — matches Δt
    deadband_m: float = 0.2                  # d — hysteresis band
    # Detection thresholds
    tau_p: float = 0.035
    tau_l: float = 0.0085
    tau_a_ms: float = 1500.0                 # 1.5 seconds latency threshold
    pump_on_threshold_m: float = 0.8         # H_sp - d
    pump_off_threshold_m: float = 1.2        # H_sp + d
    default_valve_pct: float = 50.0          # Default valve opening


# ──────────────────────────────────────────────────────────────────────
# Simulation Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SimulationParams:
    """Global simulation timing, noise, and reproducibility settings."""
    dt_s: float = 1.0                        # Δt — 1 Hz telemetry
    scenario_duration_s: float = 1000.0      # ~17 min per scenario
    sensor_noise_level_m: float = 0.005      # σ_H — ±5mm Gaussian
    sensor_noise_flow_m3s: float = 0.0001    # σ_Q — ±0.1 L/s
    actuator_delay_steps: int = 1            # 1-step command→execution lag
    base_random_seed: int = 42000            # seed_0 — per-scenario: seed_0 + index


# ──────────────────────────────────────────────────────────────────────
# Composite — All Parameters
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SystemParams:
    """Complete frozen parameter set for the SCADA simulation."""
    tank: TankParams = field(default_factory=TankParams)
    pump: PumpParams = field(default_factory=PumpParams)
    valve: ValveParams = field(default_factory=ValveParams)
    controller: ControllerParams = field(default_factory=ControllerParams)
    simulation: SimulationParams = field(default_factory=SimulationParams)


# Singleton instance — import this throughout the project.
PARAMS = SystemParams()
