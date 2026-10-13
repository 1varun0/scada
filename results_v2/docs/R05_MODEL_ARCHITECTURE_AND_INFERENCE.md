# R05: Model Architecture & Inference Performance

## 1. PyTorch LSTM Autoencoder Architecture

The temporal deep-learning anomaly detection module is implemented in PyTorch ([`models/lstm_autoencoder.py`](file:///c:/projects/p1/New%20folder/models/lstm_autoencoder.py)). It learns nominal physical correlation and dynamic trajectories across a sliding temporal window of SCADA measurements:

```
[Input Tensor: Batch x Window(10) x Features(5)]
                      │
                      ▼
        ┌───────────────────────────┐
        │  Encoder: LSTM(5 -> 32)   │
        └───────────────────────────┘
                      │  (Final Hidden State: 32)
                      ▼
        ┌───────────────────────────┐
        │ Latent Repeat (10 steps)  │
        └───────────────────────────┘
                      │
                      ▼
        ┌───────────────────────────┐
        │  Decoder: LSTM(32 -> 32)  │
        └───────────────────────────┘
                      │
                      ▼
        ┌───────────────────────────┐
        │ Linear Projection (32->5) │
        └───────────────────────────┘
                      │
                      ▼
[Output Tensor: Reconstructed Batch x Window(10) x Features(5)]
```

### Parameter Specification
- **Input Dimension (`input_dim`)**: 5 features (`tank_level_observed`, `q_in`, `q_out`, `pump_state`, `valve_state`).
- **Hidden Dimension (`hidden_dim`)**: 32 units.
- **Layers (`num_layers`)**: 1 layer (Encoder and Decoder).
- **Sequence Length ($W$)**: 10 timesteps ($10.0\text{ s}$ horizon).
- **Latent Bottleneck**: 32-dimensional latent vector taken from `hidden[-1]` and repeated across all 10 temporal steps.
- **Reconstruction Loss**: Mean Squared Error (MSE) across the window:
  $$\text{Loss} = \frac{1}{W \times D} \sum_{t=1}^W \sum_{d=1}^D (x_{t, d} - \hat{x}_{t, d})^2$$
- **Anomaly Score ($S_l$)**: Normalization of the reconstruction error against threshold $\tau_l = 0.0085$:
  $$S_l = \min\left(1.0, \frac{\text{MSE}}{\tau_l}\right)$$

---

## 2. Preprocessor Scaling & Invariance

Data normalization is governed by [`models/preprocessor.py`](file:///c:/projects/p1/New%20folder/models/preprocessor.py) using the pre-fitted checkpoint [`checkpoints/scaler_v1.pkl`](file:///c:/projects/p1/New%20folder/checkpoints/scaler_v1.pkl):
- **Algorithm**: `MinMaxScaler(feature_range=(0, 1))`
- **Fitting Guarantee**: Fitted strictly on the 42 normal training scenarios (`N_041` through `N_039`), with zero exposure to test or attack traces.
- **Feature Clipping**: Out-of-bounds observations during extreme adversarial attacks are permitted to scale beyond $[0, 1]$, generating exceptionally high reconstruction errors that immediately flag anomalies.

---

## 3. Hardware Acceleration & Inference Throughput

Benchmarked during the batch reproduction execution ([`d1_run_evaluation.log`](file:///c:/projects/p1/New%20folder/results_v2/raw/d1_run_evaluation.log)):
- **Hardware Device**: NVIDIA GeForce GTX 1650 (4 GB GDDR6), CUDA 12.1 runtime.
- **Total Inferences**: 99,000 sequence evaluations (evaluated sequentially per scenario in 10-step rolling windows).
- **Total Wall-Clock Time**: 259.26 seconds across all 99 scenarios.
- **Per-Scenario Mean Time**: $2.62\text{ s}$ per 1,000-tick scenario.
- **Mean Single-Step Inference Latency**: $\approx 2.62\text{ ms}$ per timestep (including feature extraction, PyTorch tensor GPU transfer, forward pass, and MSE loss computation).
- **Real-Time Feasibility**: With SCADA telemetry arriving at $1.0\text{ s}$ tick intervals, a $2.62\text{ ms}$ processing latency consumes less than **0.3% of the available inter-packet budget**, easily permitting deployment on low-power industrial edge gateways.
