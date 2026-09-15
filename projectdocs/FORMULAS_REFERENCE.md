# SCADA IDS: Complete Mathematical & Physical Formulation Reference

This document provides the mathematical foundation and physical equations implemented across the entire SCADA Intrusion Detection System (IDS) project.

---

## Table of Contents
1. [Physical Process & Hydrodynamics](#1-physical-process--hydrodynamics)
2. [Closed-Loop Controller & Setpoint Dynamics](#2-closed-loop-controller--setpoint-dynamics)
3. [Stochastic Sensor Noise Modeling](#3-stochastic-sensor-noise-modeling)
4. [Digital Twin & Physics Consistency Engine](#4-digital-twin--physics-consistency-engine)
5. [Cyber-Physical Attack Formulations](#5-cyber-physical-attack-formulations)
6. [Temporal Behavior Engine (LSTM-Autoencoder)](#6-temporal-behavior-engine-lstm-autoencoder)
7. [Deterministic Safety Policy Engine](#7-deterministic-safety-policy-engine)
8. [Communication Integrity Engine](#8-communication-integrity-engine)
9. [Hybrid Multi-Evidence Fusion Engine](#9-hybrid-multi-evidence-fusion-engine)
10. [Validation & Performance Evaluation Metrics](#10-validation--performance-evaluation-metrics)
11. [System Parameters & Frozen Constants](#11-system-parameters--frozen-constants)

---

## 1. Physical Process & Hydrodynamics

Implemented in:
* Python: [`simulator/tank.py`](file:///c:/projects/p1/New%20folder/simulator/tank.py), [`simulator/pump.py`](file:///c:/projects/p1/New%20folder/simulator/pump.py), [`simulator/valve.py`](file:///c:/projects/p1/New%20folder/simulator/valve.py)
* MATLAB: [`matlab/run_single_scenario.m`](file:///c:/projects/p1/New%20folder/matlab/run_single_scenario.m)

### 1.1 Hydrodynamic Mass Conservation
The rate of change of water volume inside the cylindrical tank is governed by the continuous mass conservation equation:
$$\frac{dV(t)}{dt} = A \frac{dH(t)}{dt} = Q_{in}(t) - Q_{out}(t)$$

$$\frac{dH(t)}{dt} = \frac{Q_{in}(t) - Q_{out}(t)}{A}$$

Discretized via forward Euler integration at simulation step $\Delta t = 1.0\text{ s}$:
$$H(t+\Delta t) = \text{clamp}\left(H(t) + \frac{Q_{in}(t) - Q_{out}(t)}{A} \cdot \Delta t, \; 0, \; H_{max}\right)$$

where:
$$\text{clamp}(x, 0, H_{max}) = \max\left(0, \min(x, H_{max})\right)$$
* $A = 2.0\text{ m}^2$: Tank cross-sectional area ($\approx 1.6\text{ m}$ diameter).
* $H_{max} = 2.5\text{ m}$: Physical ceiling / overflow height.
* $H(t)$: True water level at time $t$.

---

### 1.2 Feed Pump Flow & Inertia Delay
The feed pump is a fixed-speed binary pump (ON/OFF) delivering constant volumetric flow $Q_{max}$ when active:
$$Q_{in}(t) = \begin{cases} Q_{max} & \text{if } \text{pump\_state}(t) = 1 \\ 0.0 & \text{if } \text{pump\_state}(t) = 0 \end{cases}$$

Mechanical inertia and pump startup lag are modeled by a pure time delay $\tau_{pump} = 2.0\text{ s}$:
$$N_{delay} = \max\left(1, \left\lceil \frac{\tau_{pump}}{\Delta t} \right\rceil\right) = 2\text{ steps}$$

$$\text{pump\_state}(t) = \text{pump\_command}(t - \tau_{pump})$$
* $Q_{max} = 0.005\text{ m}^3/\text{s} = 5.0\text{ L/s} \approx 79.25\text{ GPM}$.

---

### 1.3 Discharge Valve Dynamics & Gravity Outflow (Torricelli Model)
Discharge outflow depends on valve opening percentage and hydrostatic pressure head (Torricelli's law):
$$Q_{out}(t) = \begin{cases} C_v \cdot \left(\frac{V(t)}{100}\right) \cdot \sqrt{H(t)} & \text{if } H(t) > 0 \\ 0.0 & \text{if } H(t) \le 0 \end{cases}$$
* $C_v = 0.004\text{ m}^3/\text{s}$: Discharge flow coefficient at $100\%$ opening under unit head ($1\text{ m}$).
* $V(t) \in [0, 100]\%$: Actual valve opening percentage.

Actuator slew-rate limiting (mechanical response time $\tau_{valve} = 1.5\text{ s}$ for full $0 \to 100\%$ stroke):
$$R_{max} = \frac{100.0}{\tau_{valve}} = \frac{100.0}{1.5} \approx 66.67\%/\text{s}$$

$$\Delta V_{allowed} = R_{max} \cdot \Delta t = 66.67\%$$

$$V(t+\Delta t) = \text{clamp}\Big(V(t) + \text{clamp}\left(V_{cmd}(t) - V(t), -\Delta V_{allowed}, \Delta V_{allowed}\right), \; 0, \; 100\Big)$$

---

### 1.4 Theoretical Process Dynamic Rates (at Nominal Level $H = 1.0\text{ m}$)
* **Maximum Inflow Rate:** $Q_{in} = 0.005\text{ m}^3/\text{s}$
* **Maximum Outflow Rate ($V = 100\%$):** $Q_{out,max} = 0.004 \times 1.0 \times \sqrt{1.0} = 0.004\text{ m}^3/\text{s}$
* **Nominal Net Fill Rate (Pump ON, Valve $100\%$):**
  $$\frac{dH}{dt}\Big|_{ON} = \frac{0.005 - 0.004}{2.0} = +0.0005\text{ m/s} = +0.5\text{ mm/s}$$
* **Nominal Drain Rate (Pump OFF, Valve $100\%$):**
  $$\frac{dH}{dt}\Big|_{OFF} = \frac{0.0 - 0.004}{2.0} = -0.0020\text{ m/s} = -2.0\text{ mm/s}$$
* **Time to Drain across Hysteresis Band ($1.2\text{ m} \to 0.8\text{ m}$ with Pump OFF, Valve $50\%$):**
  $$Q_{out,avg} \approx 0.004 \times 0.50 \times \sqrt{1.0} = 0.002\text{ m}^3/\text{s}$$
  $$\Delta t_{cycle} = \frac{A \cdot \Delta H}{Q_{out,avg}} = \frac{2.0 \cdot (1.2 - 0.8)}{0.002} = \frac{0.8}{0.002} = 400\text{ s}$$

---

## 2. Closed-Loop Controller & Setpoint Dynamics

Implemented in: [`simulator/controller.py`](file:///c:/projects/p1/New%20folder/simulator/controller.py), [`config/scenarios.py`](file:///c:/projects/p1/New%20folder/config/scenarios.py).

### 2.1 Hysteresis (Bang-Bang) Control Law
To prevent rapid chattering of the mechanical feed pump, a deadband $d = 0.2\text{ m}$ is placed symmetrically around setpoint $H_{sp}$:
$$\text{Lower Threshold (Pump ON):} \quad H_{on} = H_{sp}(t) - d$$
$$\text{Upper Threshold (Pump OFF):} \quad H_{off} = H_{sp}(t) + d$$

The pump command logic:
$$\text{pump\_command}(t) = \begin{cases} 1 & \text{if } H_{observed}(t) < H_{on} \\ 0 & \text{if } H_{observed}(t) > H_{off} \\ \text{pump\_command}(t-\Delta t) & \text{if } H_{on} \le H_{observed}(t) \le H_{off} \end{cases}$$

$$\text{valve\_command}(t) = V_{default} = 50.0\%$$

### 2.2 Deterministic Fail-Safe Mode
When a Denial of Service (DoS) or communication link drop is identified:
$$\text{pump\_command}(t) = 0 \quad (\text{OFF})$$
$$\text{valve\_command}(t) = V_{safe} = 0.0\% \quad (\text{Fully Closed})$$

---

### 2.3 Setpoint Trajectory Profiles

#### 1. Constant Setpoint Profile
$$H_{sp}(t) = H_{0,sp} = 1.0\text{ m}, \quad \forall t \in [0, T]$$

#### 2. Step Change Setpoint Profile
$$H_{sp}(t) = \begin{cases} H_{0,sp} & \text{for } t < t_{change} \\ H_{final,sp} & \text{for } t \ge t_{change} \end{cases}$$
* Nominal step: $H_{0,sp} = 1.0\text{ m} \to H_{final,sp} = 1.5\text{ m}$ at $t_{change} = 400\text{ s}$.

#### 3. Ramp Setpoint Profile
$$H_{sp}(t) = \begin{cases} H_{0,sp} & \text{for } t \le t_{change} \\ H_{0,sp} + \min\left(\frac{t - t_{change}}{T - t_{change}}, 1.0\right) \cdot (H_{final,sp} - H_{0,sp}) & \text{for } t > t_{change} \end{cases}$$
* Nominal ramp: $H_{0,sp} = 0.8\text{ m} \to H_{final,sp} = 1.4\text{ m}$ starting at $t_{change} = 200\text{ s}$.

---

## 3. Stochastic Sensor Noise Modeling

Implemented in: [`simulator/noise.py`](file:///c:/projects/p1/New%20folder/simulator/noise.py).

### 3.1 Water Level Sensor Noise
Physical level transmitters (e.g., hydrostatic or ultrasonic) exhibit Gaussian measurement imprecision:
$$H_{observed}(t) = H_{true}(t) + \epsilon_H(t)$$
$$\epsilon_H(t) \sim \mathcal{N}(0, \sigma_H^2), \quad \sigma_H = 0.005\text{ m} \; (\pm 5\text{ mm})$$

### 3.2 Flow Meter Sensor Noise
Magnetic/ultrasonic flow transmitters with zero-clamping:
$$Q_{in,obs}(t) = \max\left(0, \; Q_{in,true}(t) + \epsilon_Q(t)\right)$$
$$Q_{out,obs}(t) = \max\left(0, \; Q_{out,true}(t) + \epsilon_Q(t)\right)$$
$$\epsilon_Q(t) \sim \mathcal{N}(0, \sigma_Q^2), \quad \sigma_Q = 0.0001\text{ m}^3/\text{s} \; (\pm 0.1\text{ L/s})$$

---

## 4. Digital Twin & Physics Consistency Engine

Implemented in: [`digital_twin/physics_twin.py`](file:///c:/projects/p1/New%20folder/digital_twin/physics_twin.py).

### 4.1 Digital Twin State Propagation
The Digital Twin runs an isolated hydrodynamic model. **It never consumes $H_{observed}(t)$ for self-correction during a run**, ensuring divergence during False Data Injection attacks.

* **Reinitialization (Option B — Per-Scenario):**
  $$H_{twin}(0) = H_{true}(0)$$

* **Forward Prediction Step:**
  $$H_{twin}(t+\Delta t) = \text{clamp}\left(H_{twin}(t) + \frac{Q_{in,reported}(t) - Q_{out,reported}(t)}{A} \cdot \Delta t, \; 0, \; H_{max}\right)$$

---

### 4.2 Physics Residual Computation
The signed discrepancy between reported physical measurement and Twin prediction:
$$r_{physics}(t) = H_{observed}(t) - H_{twin}(t)$$

---

### 4.3 Normalized Physics Evidence Score ($S_p$)
$$S_p(t) = \min\left(\frac{|r_{physics}(t)|}{\tau_p}, \; 1.0\right) \in [0, 1]$$
where $\tau_p$ is the physics residual threshold established from the maximum of normal operational residuals ($\tau_p = 0.035\text{ m}$).

---

## 5. Cyber-Physical Attack Formulations

Implemented in: [`matlab/attacks/`](file:///c:/projects/p1/New%20folder/matlab/attacks).

### 5.1 A1: False Data Injection (FDI) Attacks
Applied during window $t \in [t_{start}, t_{end}]$:

1. **Additive Constant Bias:**
   $$H_{observed}(t) = H_{true}(t) + \epsilon_H(t) + b$$
   where $b \in \{+0.05\text{ m}, +0.10\text{ m}, +0.20\text{ m}\}$.

2. **Multiplicative Scaling:**
   $$H_{observed}(t) = \alpha \cdot \left(H_{true}(t) + \epsilon_H(t)\right)$$
   where $\alpha = 1.10$.

3. **Intermittent Pulsing Bias:**
   $$H_{observed}(t) = H_{true}(t) + \epsilon_H(t) + b \cdot \mathbf{1}_{\left\{(k - k_{start}) \bmod 5 = 0\right\}}$$
   where $b = +0.15\text{ m}$, pulsing every 5 seconds.

---

### 5.2 A2: Replay Attacks & Data Age Formulation
Adversary captures a buffer of length $T_{buf}$ prior to attack start:
$$\mathcal{B} = \Big\{\left(H_{obs}(\tau), t_{source}(\tau), \text{seq}(\tau)\right) \;\Big|\; \tau \in [t_{start} - T_{buf}, \; t_{start})\Big\}$$

During the attack window $t \in [t_{start}, t_{start} + T_{buf}]$:
$$\text{buf\_idx}(t) = \left(\left\lfloor \frac{t - t_{start}}{\Delta t} \right\rfloor \bmod |\mathcal{B}|\right) + 1$$

$$H_{observed}(t) = \mathcal{B}[\text{buf\_idx}(t)].H$$
$$t_{source}(t) = \mathcal{B}[\text{buf\_idx}(t)].t_{source}$$
$$\text{replay\_source\_sequence\_id}(t) = \mathcal{B}[\text{buf\_idx}(t)].\text{seq}$$

$$\text{DataAge}_{ms}(t) = \left(t_{sim}(t) - t_{source}(t)\right) \times 1000$$

---

### 5.3 A3: Denial of Service (DoS) Attacks
During communication blackout $t \in [t_{start}, t_{start} + T_{dos}]$:
$$\text{packet\_received}(t) = 0$$
$$\text{communication\_status}(t) = \text{"BLOCKED"}$$
$$\text{Physical Actuation:} \quad \text{pump\_command}(t) = 0, \quad \text{valve\_command}(t) = 0\%$$
$$\text{Physical Process:} \quad Q_{in}(t) = 0, \quad Q_{out}(t) = 0 \implies \frac{dH}{dt} = 0$$

---

### 5.4 A4: Authenticated Misuse Attacks
Legitimate session tokens used to inject safety-violating commands:
$$\text{is\_authenticated}(t) = 1, \quad \text{is\_authorized}(t) = 1, \quad \text{user\_id} = \text{"attacker\_01"}$$

1. **Unsafe Valve Discharge at Low Storage Level ($H < 0.4\text{ m}$):**
   $$\text{valve\_command}(t) = 80\%\text{--}100\%, \quad \text{pump\_command}(t) = 0$$
2. **Forced Overfill Pump Command at High Level ($H > 2.1\text{ m}$):**
   $$\text{pump\_command}(t) = 1, \quad \text{valve\_command}(t) = 0\%$$

---

## 6. Temporal Behavior Engine (LSTM-Autoencoder)

### 6.1 Input Feature Vector
At each timestep $t$, the 5-dimensional process state is assembled:
$$\mathbf{x}_t = \begin{bmatrix} H_{observed}(t) \\ Q_{in}(t) \\ Q_{out}(t) \\ \text{pump\_state}(t) \\ \text{valve\_state}(t) \end{bmatrix} \in \mathbb{R}^5$$

*(Ground truth, policy flags, and residuals are explicitly forbidden as LSTM inputs).*

---

### 6.2 Feature Standardization
Fitted strictly on normal training scenarios:
$$\tilde{\mathbf{x}}_t = \frac{\mathbf{x}_t - \boldsymbol{\mu}_{train}}{\boldsymbol{\sigma}_{train}} \quad \text{or} \quad \tilde{\mathbf{x}}_t = \frac{\mathbf{x}_t - \mathbf{x}_{min}}{\mathbf{x}_{max} - \mathbf{x}_{min}}$$

---

### 6.3 Sliding Window Tensor
Given window length $W$ (e.g., $W = 10\text{ s}$):
$$\mathbf{X}_t = \begin{bmatrix} \tilde{\mathbf{x}}_{t-W+1} \\ \tilde{\mathbf{x}}_{t-W+2} \\ \vdots \\ \tilde{\mathbf{x}}_t \end{bmatrix} \in \mathbb{R}^{W \times 5}$$

---

### 6.4 Autoencoder Reconstruction Loss & Score ($S_l$)
$$\hat{\mathbf{X}}_t = f_{decoder}\Big(f_{encoder}(\mathbf{X}_t)\Big)$$

Mean Squared Reconstruction Error:
$$e_t = \frac{1}{W \cdot D} \sum_{w=1}^{W} \sum_{d=1}^{D} \left(X_{w,d} - \hat{X}_{w,d}\right)^2$$

Normalized Temporal Evidence Score:
$$S_l(t) = \min\left(\frac{e_t}{\tau_l}, \; 1.0\right) \in [0, 1]$$
where $\tau_l$ is the reconstruction error threshold determined on the normal validation set.

---

## 7. Deterministic Safety Policy Engine

Evaluates instantaneous process safety rule constraints.

### 7.1 Safety Invariants
$$R_1: \text{If } H_{observed}(t) \le H_{crit,low} \; (0.3\text{ m}) \land V_{command}(t) > V_{safe,max} \; (50\%) \implies \text{VIOLATION}$$
$$R_2: \text{If } H_{observed}(t) \ge H_{crit,high} \; (2.3\text{ m}) \land \text{pump\_command}(t) == 1 \implies \text{VIOLATION}$$

### 7.2 Safety Evidence Score ($S_c$)
$$S_c(t) = \begin{cases} 1.0 & \text{if } R_1 \lor R_2 \text{ is True} \\ 0.0 & \text{otherwise} \end{cases}$$

---

## 8. Communication Integrity Engine

Monitors network packet delivery and telemetry freshness.

### 8.1 Availability & Freshness Score ($S_a$)
$$S_a(t) = \begin{cases} 
1.0 & \text{if } \text{packet\_received}(t) == 0 \\
\min\left(\frac{\text{DataAge}_{ms}(t)}{\tau_{a,max}}, \; 1.0\right) & \text{if } \text{DataAge}_{ms}(t) > \tau_a \\
0.0 & \text{otherwise}
\end{cases}$$
* $\tau_a = 1{,}500\text{ ms}$ ($1.5\text{ s}$ freshness threshold).
* $\tau_{a,max} = 5{,}000\text{ ms}$ ($5\text{ s}$ full replay penalty saturation).

---

## 9. Hybrid Multi-Evidence Fusion Engine

Combines heterogeneous evidence into a unified anomaly metric.

### 9.1 Linear Convex Combination
$$S_{hybrid}(t) = w_p S_p(t) + w_l S_l(t) + w_c S_c(t) + w_a S_a(t)$$

subject to the constraints:
$$\sum_{i \in \{p, l, c, a\}} w_i = 1.0, \qquad w_i \ge 0, \qquad S_i(t) \in [0, 1]$$

---

### 9.2 Binary Decision Rule
$$\hat{y}(t) = \begin{cases} 1 & \text{if } S_{hybrid}(t) > \tau_{fusion} \\ 0 & \text{if } S_{hybrid}(t) \le \tau_{fusion} \end{cases}$$
where $\tau_{fusion} \in (0, 1)$ is the decision threshold calibrated on the validation set.

---

### 9.3 Max-Vote Fusion Strategy (Production Default)
In the final production configuration, the system uses a **Max-Vote** strategy instead of the linear combination:

$$S_{hybrid}(t) = \max\Big(S_p(t),\; S_l(t),\; S_c(t),\; S_a(t)\Big)$$

$$\hat{y}(t) = \begin{cases} 1 & \text{if } S_{hybrid}(t) > \tau_{fusion} \\ 0 & \text{if } S_{hybrid}(t) \le \tau_{fusion} \end{cases}$$
where $\tau_{fusion} = 0.95$.

This ensures that a single engine detecting a clear violation of its domain is sufficient to raise an alert, eliminating the dilution problem inherent in weighted averaging when attacks only trigger one engine.

---

## 10. Validation & Performance Evaluation Metrics

Implemented in: [`scripts/run_e0_validation.py`](file:///c:/projects/p1/New%20folder/scripts/run_e0_validation.py).

### 10.1 Phase 1 Gate (E0 Validation) Metrics
Validates that the Digital Twin tracks noise-free ground truth $H_{true}(t)$ across $N$ validation samples:

* **Mean Absolute Error (MAE):**
  $$\text{MAE} = \frac{1}{N} \sum_{k=1}^N \Big|H_{true}(k) - H_{twin}(k)\Big| \qquad (\text{Pass Criterion: } \text{MAE} < 0.02\text{ m})$$

* **Root Mean Squared Error (RMSE):**
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{k=1}^N \Big(H_{true}(k) - H_{twin}(k)\Big)^2}$$

* **Percentile Residuals:**
  $$\text{P}_{95} = \text{Percentile}_{95}\Big(|H_{true} - H_{twin}|\Big)$$
  $$\text{P}_{99} = \text{Percentile}_{99}\Big(|H_{true} - H_{twin}|\Big)$$

* **Maximum Absolute Error:**
  $$\text{Max Error} = \max_{k \in \{1,\dots,N\}} \Big|H_{true}(k) - H_{twin}(k)\Big|$$

---

### 10.2 Detection Classification Metrics
Given True Positives ($TP$), False Positives ($FP$), True Negatives ($TN$), False Negatives ($FN$):

$$\text{Precision} = \frac{TP}{TP + FP}$$

$$\text{Recall (TPR)} = \frac{TP}{TP + FN}$$

$$F_1\text{-Score} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}} = \frac{2TP}{2TP + FP + FN}$$

$$\text{False Positive Rate (FPR)} = \frac{FP}{FP + TN}$$

$$\text{False Alarm Rate (alarms/hr)} = \frac{FP}{\text{Total Normal Operating Hours}} = \frac{FP}{\frac{N_{normal} \cdot \Delta t}{3600}}$$

---

### 10.3 Detection Latency
For each attack scenario with start time $t_{attack\_start}$:
$$t_{first\_detection} = \min \left\{ t \;\Big|\; \hat{y}(t) = 1 \;\land\; t \ge t_{attack\_start} \right\}$$

$$\Delta t_{detect} = t_{first\_detection} - t_{attack\_start}$$

Summary statistics computed across all episodes:
$$\text{Median Latency}, \quad \text{Mean Latency}, \quad \text{P}_{95}\text{ Latency}, \quad \text{Max Latency}$$

---

## 11. System Parameters & Frozen Constants

| Subsystem | Parameter Description | Symbol | Value | Physical Unit |
|---|---|---|---|---|
| **Tank** | Cross-Sectional Area | $A$ | $2.0$ | $\text{m}^2$ |
| | Maximum Physical Height | $H_{max}$ | $2.5$ | $\text{m}$ |
| | Default Initial Level | $H_0$ | $1.0$ | $\text{m}$ |
| | Critical Low Threshold | $H_{crit,low}$ | $0.3$ | $\text{m}$ |
| | Critical High Threshold | $H_{crit,high}$ | $2.3$ | $\text{m}$ |
| **Pump** | Maximum Delivery Flow | $Q_{max}$ | $0.005$ | $\text{m}^3/\text{s}$ ($5.0\text{ L/s}$) |
| | Mechanical Response Delay | $\tau_{pump}$ | $2.0$ | $\text{s}$ ($2\text{ steps}$) |
| **Valve** | Outflow Coefficient | $C_v$ | $0.004$ | $\text{m}^3/\text{s}$ |
| | Mechanical Stroke Time | $\tau_{valve}$ | $1.5$ | $\text{s}$ |
| | Maximum Slew Rate | $R_{max}$ | $66.67$ | $\%/\text{s}$ |
| | Fail-Safe Safe Position | $V_{safe}$ | $0.0$ | $\%$ (Closed) |
| **Controller**| Nominal Setpoint | $H_{sp}$ | $1.0$ | $\text{m}$ |
| | Hysteresis Deadband | $d$ | $0.2$ | $\text{m}$ |
| | Pump ON Threshold | $H_{on}$ | $0.8$ | $\text{m}$ |
| | Pump OFF Threshold | $H_{off}$ | $1.2$ | $\text{m}$ |
| | Default Normal Valve Opening | $V_{default}$| $50.0$| $\%$ |
| **Simulation**| Discrete Time Step | $\Delta t$ | $1.0$ | $\text{s}$ ($1\text{ Hz}$) |
| | Scenario Duration | $T$ | $1000.0$| $\text{s}$ ($\approx 16.67\text{ min}$) |
| | Level Sensor Noise STD | $\sigma_H$ | $0.005$ | $\text{m}$ ($\pm 5\text{ mm}$) |
| | Flow Sensor Noise STD | $\sigma_Q$ | $0.0001$| $\text{m}^3/\text{s}$ ($\pm 0.1\text{ L/s}$) |
| | Base Random Seed | $seed_0$ | $42000$ | — |
