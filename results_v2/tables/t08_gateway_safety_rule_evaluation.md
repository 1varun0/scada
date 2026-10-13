# Table T08: Gateway Safety Rule Offline Evaluation

> Source: `experiments/validate_gateway_rule.py` executed in isolated sandbox.
> Raw log: [`e1_gateway_rule_validation.log`](../raw/e1_gateway_rule_validation.log)

## Evaluated Rule Invariant

- **Upper Envelope Limit**: Pump ON forbidden if $h_{\text{est}} > \text{setpoint} + \text{deadband} (0.20) + \epsilon (0.05) = 1.25\text{ m}$ (for setpoint $1.0\text{ m}$).
- **Lower Envelope Limit**: Pump OFF forbidden if $h_{\text{est}} < \text{setpoint} - \text{deadband} (0.20) - \epsilon (0.05) = 0.75\text{ m}$ (for setpoint $1.0\text{ m}$).
- **Valve Envelope Constraint**: Valve command forbidden if $\text{valve} \neq 50\%$ unless safe fail-close condition ($\text{valve} = 0\%$ and $\text{pump} = 0$).

## Multi-Scenario Evaluation Summary across 150 Scenarios (150,000 Ticks)

| Scenario Group | Scenarios | Total Ticks | Violations Inside Window | Violations Outside Window | False Alarm Rate | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Normal (`N_001` - `N_060`)** | 60 | 60,000 | 0 | 0 | **0.00% (0 / 60,000)** | ✅ ZERO False Alarms |
| - *Recovery* | 10 | 10,000 | - | 0 | 0.00% | ✅ Safe |
| - *Setpoint Change* | 15 | 15,000 | - | 0 | 0.00% | ✅ Safe |
| - *Steady State* | 20 | 20,000 | - | 0 | 0.00% | ✅ Safe |
| - *Variable Load* | 15 | 15,000 | - | 0 | 0.00% | ✅ Safe |
| **FDI Attacks (`A1_001` - `A1_045`)** | 45 | 45,000 | 1,818 (across 35 runs) | 0 | **0.00% Outside** | ✅ Physical Bounds Catch |
| **Replay Attacks (`A2_001` - `A2_015`)** | 15 | 15,000 | 0 | 0 | **0.00%** | ✅ In-Envelope Playback |
| **DoS Attacks (`A3_001` - `A3_015`)** | 15 | 15,000 | 0 | 0 | **0.00%** | ✅ Failsafe Compliant |
| **Auth Misuse (`A4_001` - `A4_015`)** | 15 | 15,000 | 1,515 (101/run) | 0 | **0.00% Outside** | ✅ **100% Rogue Catch** |

## Rogue Command Catch Rate on Authorization Misuse (`A4`)

| Scenario ID | Subtype / Unauthorized Actuator Instruction | Ground Truth Ticks | Detections Inside Window | Catch Rate |
| :--- | :--- | :---: | :---: | :---: |
| `A4_001` | `valve_open_at_low (VALVE_SET_80)` | 101 | 101 | **100.0%** |
| `A4_002` | `valve_open_at_low (VALVE_SET_90)` | 101 | 101 | **100.0%** |
| `A4_003` | `valve_open_at_low (VALVE_SET_100)` | 101 | 101 | **100.0%** |
| `A4_004` | `pump_on_at_high (PUMP_ON_AT_HIGH)` | 101 | 101 | **100.0%** |
| `A4_005` | `valve_open_at_low (VALVE_SET_70)` | 101 | 101 | **100.0%** |
| `A4_006` | `valve_open_at_low (VALVE_SET_95)` | 101 | 101 | **100.0%** |
| `A4_007` | `pump_on_at_high (PUMP_ON_AT_OVERFLOW)` | 101 | 101 | **100.0%** |
| `A4_008` | `valve_open_at_low (VALVE_SET_85)` | 101 | 101 | **100.0%** |
| `A4_009` | `valve_open_at_low (VALVE_SET_75)` | 101 | 101 | **100.0%** |
| `A4_010` | `pump_on_at_high (PUMP_ON_AT_CRIT_HIGH)` | 101 | 101 | **100.0%** |
| `A4_011` | `valve_open_at_low (VALVE_SET_60)` | 101 | 101 | **100.0%** |
| `A4_012` | `valve_open_at_low (VALVE_SET_100_SUSTAINED)` | 101 | 101 | **100.0%** |
| `A4_013` | `pump_on_at_high (PUMP_FORCE_ON)` | 101 | 101 | **100.0%** |
| `A4_014` | `valve_open_at_low (VALVE_SET_80_LONG)` | 101 | 101 | **100.0%** |
| `A4_015` | `valve_open_at_low (VALVE_SET_90_LONG)` | 101 | 101 | **100.0%** |
