# Table T09: Constant Sensor Bias Detection Sensitivity Sweep

> Source: `experiments/run_constant_bias_sweep.py` executed in isolated sandbox copy.
> Evaluates 6 constant level biases (0 to 5 cm) across 10 evaluation seeds (101 to 110, 1200 ticks each, clamp_flow_noise=False).
> Raw data: [`constant_bias_sweep_results.csv`](../raw/constant_bias_sweep_results.csv), runner log [`e2_constant_bias_sweep.log`](../raw/e2_constant_bias_sweep.log).

## Detection Rates and Alert Latency Matrix

| Bias (cm) | Bias (m) | P(CRITICAL) Rate | Detection Count | Mean Time to CRITICAL (s) | P(S_p > 0.95) Rate | Mean Time to Flag (s) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 cm | 0.000 m | **0.0%** | 0 / 10 | N/A (Never Triggered) | 20.0% | 1134.5 s |
| 1 cm | 0.010 m | **0.0%** | 0 / 10 | N/A (Never Triggered) | 40.0% | 645.0 s |
| 2 cm | 0.020 m | **10.0%** | 1 / 10 | 1193.0 ± 0.0 s | 100.0% | 199.6 s |
| 3 cm | 0.030 m | **100.0%** | 10 / 10 | 12.4 ± 9.2 s | 100.0% | 0.7 s |
| 4 cm | 0.040 m | **100.0%** | 10 / 10 | 2.1 ± 0.3 s | 100.0% | 0.0 s |
| 5 cm | 0.050 m | **100.0%** | 10 / 10 | 2.0 ± 0.0 s | 100.0% | 0.0 s |

## Empirical Threshold & Safety Observations

- **False-Alarm Rate at 0 cm Bias**: 2 / 12000 ticks (**0.017%**).
- **False Takeover Events on Normal Water Flow**: **0 / 12000 ticks (0.00%)**.
- **Physical Threshold Boundary**: Nominal threshold $\tau_p = 0.035\text{ m}$ ($3.5\text{ cm}$).
- **Noise Immunity Envelope**: Biases $\le 2\text{ cm}$ reside within natural sensor Gaussian noise ($3\sigma = 1.5\text{ cm}$) and almost never cross the CRITICAL threshold (only 1 late crossing at $t=1193\text{ s}$).
- **Rapid Breach Response**: Biases $\ge 4\text{ cm}$ strictly exceed $\tau_p$ and trigger **100% detection within $\approx 2.1\text{ s}$**.
