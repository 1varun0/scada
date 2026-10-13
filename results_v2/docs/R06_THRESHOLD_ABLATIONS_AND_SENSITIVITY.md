# R06: Threshold Ablations & Engine Sensitivity Analysis

## 1. Multi-Engine Ablation Framework

The SCADA Hybrid IDS integrates multiple detection engines to provide defense-in-depth across diverse physical and cyber attack vectors. To evaluate the individual contribution of each engine and verify ensemble synergy, an ablation study spanning configurations C1 through C7 was executed via [`scripts/run_ablation.py`](file:///c:/projects/p1/New%20folder/scripts/run_ablation.py) on the 99,000-tick evaluation set.

The resulting performance matrix is tabulated in [`t07_ablation_study_results.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t07_ablation_study_results.md):

| Config | Engine Weights ($w_p, w_l, w_c, w_a$) | Description | Precision | Recall | F1-Score | FPR | FNR | ROC-AUC | Optimal $\tau$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **C1** | `(1.0, 0.0, 0.0, 0.0)` | Physics Only ($S_p$) | `0.3380` | `0.7818` | `0.4720` | `0.2069` | `0.2182` | `0.7668` | 0.95 |
| **C2** | `(0.0, 1.0, 0.0, 0.0)` | LSTM Only ($S_l$) | `0.4391` | `0.4549` | `0.4468` | `0.0785` | `0.5451` | `0.7955` | 0.15 |
| **C3** | `(0.5, 0.5, 0.0, 0.0)` | Physics + LSTM | `0.5849` | `0.6311` | **`0.6071`** | `0.0605` | `0.3689` | `0.9392` | 0.55 |
| **C4** | `(0.0, 0.0, 1.0, 0.0)` | Policy Only ($S_c$) | `0.0000` | `0.0000` | `0.0000` | `0.0000` | `1.0000` | `0.5000` | 0.50 |
| **C5** | `(0.0, 0.0, 0.0, 1.0)` | Availability Only ($S_a$) | **`1.0000`** | `0.1718` | `0.2933` | `0.0000` | `0.8282` | `0.5859` | 0.05 |
| **C6** | `(0.33, 0.33, 0.34, 0.0)` | Physics + LSTM + Policy | `0.4495` | `0.8822` | `0.5955` | `0.1460` | `0.1178` | `0.9392` | 0.35 |
| **C7_sum**| `(0.25, 0.25, 0.25, 0.25)` | Hybrid (Weighted Sum) | `0.3848` | **`0.9989`** | `0.5555` | `0.2158` | `0.0011` | **`0.9513`** | 0.25 |
| **C7_max**| `(0.25, 0.25, 0.25, 0.25)` | Hybrid (Max Vote) | `0.3891` | `0.9982` | `0.5600` | `0.2118` | `0.0018` | `0.8946` | 0.95 |

---

## 2. Key Physical Insights from Ablation

### A. Physics Model Strength (C1)
The mass-balance residual engine alone achieves **78.18% recall**, capturing large-amplitude sensor spoofing (FDI) and replay attacks that violate physical conservation laws. However, it cannot detect stealthy timing attacks (DoS gaps where values freeze) or unauthenticated actuator commands that stay within normal water levels.

### B. Deep Learning Synergy (C3)
Combining Physics and LSTM Autoencoder yields the **highest overall F1-score (0.6071)** with balanced precision (58.49%) and recall (63.11%), dropping the False Positive Rate to just **6.05%**. The LSTM autoencoder learns subtle multi-variate trajectory correlations, while the physical model suppresses false extrapolations.

### C. Zero-False-Alarm Availability Engine (C5)
Availability monitoring based on inter-packet arrival gaps achieves **100.0% precision** ($FPR = 0.00\%$), but has low recall (17.18%) because it only fires during DoS packet drop episodes (which constitute exactly 1,035 attack ticks).

### D. Policy Engine Dormancy in Offline Batch (C4)
The v1 Policy Engine exhibits $F1 = 0.0000$ across all 99,000 timesteps:
- **Explanation**: The v1 policy implementation in offline evaluation checks whether water level crosses hard limits ($H > 2.45\text{ m}$ or $H < 0.30\text{ m}$).
- In the offline dataset, no scenario breaches these extreme emergency boundaries, meaning $S_c$ evaluates to $0.0$ at every step.
- This dormancy directly motivated the creation of the live **Gateway Safety Rule** (`evaluate_command_with_live_setpoint`), which checks tighter controller envelope boundaries ($[0.75\text{ m}, 1.25\text{ m}]$) and achieved 100% rogue command catch rate in Phase E.

### E. Max-Vote vs Weighted-Sum Fusion (C7)
- **Max-Vote (`C7_max`)**: An anomaly is declared if *any* single engine exceeds threshold $\tau_{\text{fusion}} = 0.95$. This prioritizes recall (**99.82%**), ensuring that single-vector attacks (like DoS detected only by timing, or Auth Misuse detected only by LSTM) are never missed.
- **Weighted-Sum (`C7_sum`)**: Scores are averaged, requiring multiple engines to co-activate to reach high thresholds. At optimal threshold $\tau = 0.25$, it achieves slightly higher ROC-AUC (0.9513).
