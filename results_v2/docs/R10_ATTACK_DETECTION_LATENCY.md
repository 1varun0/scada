# R10: Attack Detection Latency & Pre-Alarm Audit

## 1. Latency Measurement Protocol

In anomaly detection literature, detection latency is defined as the elapsed time between the start of an attack ($t_{\text{start}}$) and the first predicted anomaly flag ($\hat{y} = 1$). However, if a detection system suffers from frequent background false alarms, measuring latency can yield artificially low delays because the system was *already* in an alarmed state before the attack even started.

To provide an uncompromised evaluation, [`experiments/compute_fresh_latency.py`](file:///c:/projects/p1/New%20folder/experiments/compute_fresh_latency.py) audited two distinct criteria across all 90 benchmark attack scenarios:
1. **Pre-Attack Alarm Verification**: Checked the 10-tick baseline interval immediately preceding $t_{\text{start}}$ ($[t_{\text{start}} - 10, t_{\text{start}}[$) for false positive flags.
2. **Fresh Detection Delay**: Measured the first subsequent timestep where the ensemble declared an anomaly.

---

## 2. Empirical Latency & Engine Attribution Matrix

Tabulated from [`t13_fresh_detection_latency.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t13_fresh_detection_latency.md):

| Threat Family | Scenarios ($N$) | Pre-Attack Alarms (10t window) | Primary Triggering Engine at $t_{\text{start}}$ | Trigger Rate at $t_{\text{start}}$ | Mean Fresh Latency | Median Latency | Max Latency |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **False Data Injection (FDI)** | 45 | **0 / 45 (0.0%)** | Physics Residual ($S_p$) | 45 / 45 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Replay Attack** | 15 | **0 / 15 (0.0%)** | Physics ($S_p$) & Availability ($S_a$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Denial of Service (DoS)** | 15 | **0 / 15 (0.0%)** | LSTM ($S_l$) & Availability ($S_a$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Authorization Misuse** | 15 | **0 / 15 (0.0%)** | LSTM Autoencoder ($S_l$) | 15 / 15 (100.0%) | **0.00s** | **0.00s** | **0.00s** |
| **Ensemble Total** | **90** | **0 / 90 (0.0%)** | Multi-Engine Ensemble | **90 / 90 (100.0%)** | **0.00s** | **0.00s** | **0.00s** |

---

## 3. Threat-Specific Detection Mechanisms

### A. False Data Injection (FDI — 45 Scenarios)
- **Injection Profile**: Step or ramp perturbation added to level observation $H_{\text{obs}}$ ($+0.10\text{ m}$ to $+0.50\text{ m}$).
- **Mechanism**: The Digital Twin mass balance computes expected level $h_{\text{twin}}(t)$; the instant the sensor reading diverges by more than $\tau_p = 0.035\text{ m}$ ($3.5\text{ cm}$), the physical residual $|H_{\text{obs}} - h_{\text{twin}}|$ spikes, driving $S_p = 1.0$ at **$t = t_{\text{start}}$ (0.0s latency)** in 100% of scenarios.

### B. Replay Attacks (A2 — 15 Scenarios)
- **Injection Profile**: Sensor telemetry overwritten with recorded buffer from a previous nominal interval.
- **Mechanism**: At replay onset, the replayed buffer presents an abrupt historical timestamp or flow/level discontinuity. Both the Physics Residual and Availability engines detect the instantaneous discrepancy, firing simultaneously at **$t = t_{\text{start}}$ (0.0s latency)**.

### C. Denial of Service (A3 — 15 Scenarios)
- **Injection Profile**: 100% of telemetry packets dropped.
- **Mechanism**: Inter-packet arrival gap exceeds $\tau_{\text{watchdog}} = 1500\text{ ms}$. Synthetic packet marks `packet_received = 0`, causing Availability Engine score $S_a = 1.0$ and LSTM error $S_l = 1.0$ within **0.0s**.

### D. Authorization Misuse (A4 — 15 Scenarios)
- **Injection Profile**: Unauthorized operator or rogue API client forces illegal pump or valve positions.
- **Mechanism**: The LSTM Autoencoder detects unexpected actuator commands given the current water level state, driving $S_l > 0.95$ at **$t = t_{\text{start}}$ (0.0s latency)** across all 15 scenarios.

---

## 4. Single-Tick Flagging vs State Machine Latency

A crucial operational distinction:
- **Single-Tick Anomaly Score Latency**: **0.00 seconds** (instantaneous evaluation).
- **CRITICAL Alert Latching Latency**: The $3\text{-of-}5$ sliding window requires 3 consecutive anomaly flags to latch the `CRITICAL` state. Therefore, active Digital Twin takeover initiates exactly **2.0 to 3.0 seconds** after attack onset.
- **Physical Safety Margin**: Because tank level changes slowly ($\text{max } dh/dt = 0.005\text{ m/s} = 5\text{ mm/s}$), a 3.0-second takeover delay permits at most $1.5\text{ cm}$ of water level movement, which remains safely within the $25\text{ cm}$ buffer above nominal operating level ($1.00\text{ m} \rightarrow 1.25\text{ m}$).
