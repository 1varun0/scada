# Source File Note: `config/parameters.py`

## Purpose
Defines the frozen dataclass hierarchy containing all global physical parameters, timing constants, actuator limits, and detection thresholds for the SCADA IDS project. Instantiates the singleton `PARAMS = SystemParams()`.

## Public Classes and Functions
- `@dataclass(frozen=True) class TankParams`:
  - `cross_section_area_m2: float = 2.0` ($A$)
  - `max_height_m: float = 2.5` ($H_{\text{max}}$)
  - `initial_level_m: float = 1.0` ($H_0$)
  - `critical_low_m: float = 0.3` ($H_{\text{crit\_low}}$)
  - `critical_high_m: float = 2.3` ($H_{\text{crit\_high}}$)
  - `overflow_m: float = 2.5` ($H_{\text{overflow}}$)
- `@dataclass(frozen=True) class PumpParams`:
  - `q_max_m3s: float = 0.005` ($Q_{\text{max}}$)
  - `q_min_m3s: float = 0.005` ($Q_{\text{min}}$)
  - `response_delay_s: float = 2.0` ($\tau_{\text{pump}}$)
- `@dataclass(frozen=True) class ValveParams`:
  - `range_min_pct: float = 0.0`
  - `range_max_pct: float = 100.0`
  - `flow_coefficient_m3s: float = 0.004` ($C_v$)
  - `response_time_s: float = 1.5` ($\tau_{\text{valve}}$)
  - `safe_position_pct: float = 0.0` ($V_{\text{safe}}$)
- `@dataclass(frozen=True) class ControllerParams`:
  - `setpoint_m: float = 1.0` ($H_{\text{sp}}$)
  - `control_interval_s: float = 1.0` ($T_c$)
  - `deadband_m: float = 0.2` ($d$)
  - `tau_p: float = 0.035` (Physics residual threshold $\tau_p$)
  - `tau_l: float = 0.0085` (LSTM reconstruction threshold $\tau_l$)
  - `tau_a_ms: float = 1500.0` (Availability latency threshold $\tau_a$)
  - `pump_on_threshold_m: float = 0.8` ($H_{\text{sp}} - d$)
  - `pump_off_threshold_m: float = 1.2` ($H_{\text{sp}} + d$)
  - `default_valve_pct: float = 50.0`
- `@dataclass(frozen=True) class SimulationParams`:
  - `dt_s: float = 1.0` ($\Delta t$)
  - `scenario_duration_s: float = 1000.0`
  - `sensor_noise_level_m: float = 0.005` ($\sigma_H$)
  - `sensor_noise_flow_m3s: float = 0.0001` ($\sigma_Q$)
  - `actuator_delay_steps: int = 1`
  - `base_random_seed: int = 42000`
- `@dataclass(frozen=True) class SystemParams`:
  - Aggregates `tank`, `pump`, `valve`, `controller`, and `simulation`.
- `PARAMS = SystemParams()`: Singleton imported globally.

## Inputs and Outputs
- Immutable dataclass instances initialized with defaults.

## Config Keys and Constants Read
- Source of truth for constants across the entire Python codebase.

## Who Calls It
- Imported by virtually all modules: `simulator/*`, `digital_twin/*`, `engines/*`, `models/*`, `storage/*`, `scripts/*`, `tests/*`.

## Side Effects
- None.

## Tests Covering It
- Indirectly verified by all unit tests.

## Surprising / Notable Observations
- Threshold values defined in code without derivation formulas: `tau_p = 0.035`, `tau_l = 0.0085`, `tau_a_ms = 1500.0` [CODE config/parameters.py:73-75]. There is no comment or derivation function in this file explaining the mathematical origin of `0.035` or `0.0085`.
- Note the parameter difference between `config/parameters.py` and `scada_live/config.yaml`: in `parameters.py`, `TankParams.cross_section_area_m2 = 2.0` [CODE config/parameters.py:21], whereas we must check `config.yaml` to verify whether it matches or differs.
