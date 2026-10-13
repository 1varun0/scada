# R11: Edge Cases, Sensitivity Limits & Physical Envelope Integrity

## 1. Constant Sensor Bias Detection Sensitivity

To establish the empirical detection threshold of the physics-based intrusion detection engine under realistic un-clamped Gaussian noise ($\sigma = 0.5\text{ cm}$), a systematic constant bias sweep was executed across 10 evaluation seeds (101 to 110) over 1200-second horizons ([`t09_constant_bias_sweep.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t09_constant_bias_sweep.md)):

```
Detection Probability P(CRITICAL) vs Sensor Bias:
  0 cm  │ [0/10]  0.0%  (FA rate: 0.017%, 0 false takeovers)
  1 cm  │ [0/10]  0.0%
  2 cm  │ [1/10] 10.0%  (Delayed crossing at t=1193s)
────────┼──────────────────────────────────────────────────────── (tau_p = 3.5 cm)
  3 cm  │ [10/10] 100.0% (Mean time: 12.4s)
  4 cm  │ [10/10] 100.0% (Mean time: 2.1s)
  5 cm  │ [10/10] 100.0% (Mean time: 2.0s)
```

### Physical Rationale & Mathematical Limits
- **The $3\sigma$ Noise Floor**: Natural sensor noise produces random fluctuations up to $3\sigma = 1.5\text{ cm}$. Biases $\le 1\text{ cm}$ remain immersed in Gaussian noise and produce zero false alarms.
- **Nominal Physics Threshold ($\tau_p = 0.035\text{ m} = 3.5\text{ cm}$)**:
  - For biases $\le 2\text{ cm}$, the residual $|h_{\text{obs}} - h_{\text{twin}}|$ stays beneath $3.5\text{ cm}$ almost indefinitely.
  - For biases $\ge 4\text{ cm}$, the measurement strictly exceeds $\tau_p$ at every timestep, triggering `CRITICAL` alert status and digital twin takeover within **$2.1\text{ s}$**.

---

## 2. Plant-Model Mismatch Sensitivity Analysis

In practical industrial environments, the physical plant deviates from the nominal parameters assumed by the Digital Twin due to wear, fouling, or thermal expansion. The sensitivity of the Digital Twin takeover mechanism was evaluated across 8 parametric deviation cases over an extended 2400-second horizon across 10 random seeds ([`t12_plant_model_mismatch_sensitivity.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t12_plant_model_mismatch_sensitivity.md)):

| Evaluated Deviation Case | Parameter Shift | Mean Excursion beyond $[0.8, 1.2\text{ m}]$ | Safety Envelope $[0.3, 2.5\text{ m}]$ Left? | Overflow / Dry Ticks |
| :--- | :--- | :---: | :---: | :---: |
| **Tank Area $+5\%$** | $A = 1.05\text{ m}^2$ | $0.01 \pm 0.03\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Tank Area $-5\%$** | $A = 0.95\text{ m}^2$ | $1.65 \pm 0.23\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Measured $Q_{\text{in}} +5\%$** | Inflow sensor $+5\%$ bias | $9.34 \pm 0.42\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Measured $Q_{\text{in}} -5\%$** | Inflow sensor $-5\%$ bias | $11.30 \pm 0.45\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Measured $Q_{\text{out}} +5\%$** | Outflow sensor $+5\%$ bias | $9.43 \pm 0.52\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Measured $Q_{\text{out}} -5\%$** | Outflow sensor $-5\%$ bias | $11.28 \pm 0.43\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Unmeasured Physical Leak** | $+2\%$ unmetered outflow | $4.58 \pm 0.44\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |
| **Plant Actuator Variations**| Pump $+5\%$, Valve $C_v +10\%$ | $0.57 \pm 0.24\text{ cm}$ | ✅ **No (0/10 seeds)** | 0.0 / 0.0 |

### Mathematical Proof of Actuator Invariance
A critical finding from Table T12 is that plant actuator variations (Pump $+5\%$, Valve $C_v +10\%$) result in virtually zero excursion ($0.57\text{ cm}$):
$$\frac{d\hat{h}_{\text{twin}}}{dt} = \frac{Q_{\text{in, obs}} - Q_{\text{out, obs}}}{A_{\text{twin}}}$$
Because the Digital Twin integrates **measured flowmeter rates** ($Q_{\text{in, obs}}$ and $Q_{\text{out, obs}}$) rather than commanded control signals, actuator mechanical wear or pump head degradation does not cause twin estimation drift. Only flowmeter measurement errors or unmeasured physical leaks introduce divergence.

---

## 3. Extended Soak Stability (30-Minute Horizon)

The stability of the streaming gateway was validated during a continuous 30-minute soak test (1,800 consecutive simulation seconds) under zero attack ([`test_phase6a_prevention.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_phase6a_prevention.py)):
- **Total Ingress Steps**: 1,800 steps.
- **Spurious Takeover Ticks**: **0 ticks (0.0%)**.
- **Physical Bounds**: Level maintained within $[0.60\text{ m}, 1.40\text{ m}]$.
- **Physical Harm Counters**: `plant.overflow_count == 0`, `plant.dry_run_count == 0`.
- **Numerical Stability**: `nan_guard_triggers == 0`.
