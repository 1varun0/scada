# Table T11: LSTM Autoencoder Pump Alignment & Noise Clamp 2x2 Grid

> Source: `experiments/run_2x2_grid.py` executed in isolated sandbox copy.
> Evaluates LSTM anomaly score response during actuator transient (t=200..230s) across feature source and noise clamping.
> Raw log: [`e4_2x2_grid.log`](../raw/e4_2x2_grid.log).

## 2x2 Factorial Sensitivity Matrix

| Feature Source | Noise Clamping (`clamp_flow_noise`) | Peak Reconstruction Score ($S_l$) | Ticks Exceeding Threshold ($S_l > 0.95$) | Anomaly Flagging |
| :--- | :---: | :---: | :---: | :---: |
| `Physical State` | `True` | 0.6688 | 0 | ✅ Normal (Clean) |
| `Physical State` | `False` | 0.6456 | 0 | ✅ Normal (Clean) |
| `Forced Command` | `True` | 1.0000 | 10 | ❌ False Anomaly Triggered |
| `Forced Command` | `False` | 1.0000 | 10 | ❌ False Anomaly Triggered |

## Key Physical Insights

- **Physical State Parity**: When input feature `pump_state` accurately reflects actual plant actuator state, peak LSTM reconstruction error remains below **0.67** (well below threshold $0.95$), generating **zero false alarm ticks** regardless of noise clamp settings.
- **Command Desynchronization Vulnerability**: When the feature vector is fed with commanded state during delayed mechanical ramp, artificial state mismatch drives the error to **1.0000** for **10 ticks**, demonstrating why physical sensor telemetry must reflect physical actuator feedback rather than naked control intents.
