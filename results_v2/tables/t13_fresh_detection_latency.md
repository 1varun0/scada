# Table T13: Attack Start Detection Latency & Pre-Alarm Audit

> Source: `experiments/compute_fresh_latency.py` executed in isolated sandbox copy.
> Audits detection status exactly at attack onset ($t_{\text{start}}$) and in the 10-tick baseline window prior to attack onset across all 90 test attacks.
> Raw log: [`f1_fresh_latency.log`](../raw/f1_fresh_latency.log).

## Detection Latency and Engine Attribution at Attack Inception

| Threat Class | Scenarios ($N$) | Pre-Attack Alarms (10t before) | Primary Triggering Engine(s) | Trigger Rate at $t_{\text{start}}$ | Mean Fresh Latency (s) | Median Latency (s) | Max Latency (s) |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **FDI (`A1_*`)** | 45 | **0 / 45 (0.0%)** | Physics Residual ($S_p$) | 45 / 45 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Replay (`A2_*`)** | 15 | **0 / 15 (0.0%)** | Physics ($S_p$) & Availability ($S_a$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **DoS (`A3_*`)** | 15 | **0 / 15 (0.0%)** | LSTM ($S_l$) & Availability ($S_a$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Auth Misuse (`A4_*`)** | 15 | **0 / 15 (0.0%)** | LSTM Autoencoder ($S_l$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Overall Total** | **90** | **0 / 90 (0.0%)** | Multi-Engine Hybrid Ensemble | **90 / 90 (100.0%)** | **0.00s** | **0.00s** | **0.00s** |

## Mechanism Analysis

- **Zero Pre-Attack Contamination**: Across all 90 attack scenarios, not a single false positive occurred in the 10 ticks preceding attack onset ($0/90$ scenarios), proving that the detection latency calculation is not masked by pre-existing background alarms.
- **Immediate Engine Activation**: At the exact attack timestep ($t = t_{\text{start}}$), at least one specialized engine immediately triggers beyond threshold $0.95$ for 100% of attack scenarios.
- **Sub-Second Response**: Detection latency is $0.0\text{ s}$ across all 4 threat classes in batch benchmark evaluation.
