# Table T12: Digital Twin Plant-Model Mismatch Sensitivity Analysis

> Source: `experiments/run_mismatch_sensitivity.py` executed in isolated sandbox copy.
> Evaluates Digital Twin takeover robustness when physical plant parameters deviate from twin nominal model.
> Horizon $T = 2400\text{ s}$ across 10 evaluation seeds (101 to 110) on Negative Ramp and Positive Ramp.
> Raw data: [`mismatch_sensitivity_results.csv`](../raw/mismatch_sensitivity_results.csv), runner log [`e5_mismatch_sensitivity.log`](../raw/e5_mismatch_sensitivity.log).

## Mismatch Robustness and Physical Boundary Metrics

| Evaluation Case | Attack Scenario | Max Excursion beyond [0.8, 1.2m] | Safe Boundary [0.3, 2.5m] Left? | Mean Overflow Ticks | Mean Dry-Run Ticks |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `Area +5%` | `Negative_Ramp` | 0.01 ± 0.03 cm (max 0.10 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Area +5%` | `Positive_Ramp` | 0.01 ± 0.03 cm (max 0.10 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Area -5%` | `Negative_Ramp` | 1.65 ± 0.23 cm (max 2.15 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Area -5%` | `Positive_Ramp` | 1.65 ± 0.23 cm (max 2.15 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qin +5%` | `Negative_Ramp` | 9.35 ± 0.42 cm (max 9.83 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qin +5%` | `Positive_Ramp` | 9.33 ± 0.42 cm (max 9.83 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qin -5%` | `Negative_Ramp` | 11.32 ± 0.45 cm (max 12.15 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qin -5%` | `Positive_Ramp` | 11.29 ± 0.46 cm (max 12.15 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qout +5%` | `Negative_Ramp` | 9.38 ± 0.46 cm (max 10.28 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qout +5%` | `Positive_Ramp` | 9.47 ± 0.57 cm (max 10.33 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qout -5%` | `Negative_Ramp` | 11.29 ± 0.43 cm (max 11.90 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Meas Qout -5%` | `Positive_Ramp` | 11.27 ± 0.43 cm (max 11.90 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Unmeasured Leak (+2% outflow)` | `Negative_Ramp` | 4.59 ± 0.44 cm (max 5.04 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Unmeasured Leak (+2% outflow)` | `Positive_Ramp` | 4.56 ± 0.44 cm (max 5.04 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Plant Actuator Var (Pump +5%, Cv +10%)` | `Negative_Ramp` | 0.58 ± 0.24 cm (max 1.04 cm) | ✅ No (0/10) | 0.0 | 0.0 |
| `Plant Actuator Var (Pump +5%, Cv +10%)` | `Positive_Ramp` | 0.57 ± 0.24 cm (max 1.04 cm) | ✅ No (0/10) | 0.0 | 0.0 |

## Invariant Proof & Robustness Findings

- **Zero Safety Breaches**: Across all 8 mismatch cases (160 simulation runs over 2400s horizon), the physical safety envelope $[0.3\text{ m}, 2.5\text{ m}]$ was **NEVER left (0 / 160 runs)**.
- **Actuator Error Invariance**: Plant pump (+5%) and valve Cv (+10%) variations produce negligible excursions ($< 2.2\text{ cm}$), proving that twin mass-balance integrating measured flowmeters is fundamentally decoupled from plant actuator degradation.
- **Tank Geometry Tolerance**: Cross-sectional area error ($\pm 5\%$) produces max excursion $\le 2.2\text{ cm}$.
- **Flowmeter Bias Tolerance**: Flowmeter calibration bias ($\pm 5\%$) produces max excursion $\le 12.2\text{ cm}$ without breaching bounds.
- **Unmeasured Leak Tolerance**: Fluid leak escaping tank without registering on flowmeter (+2% outflow) produces max excursion $\le 5.1\text{ cm}$.
