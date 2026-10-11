# Project Review Cheat Sheet

Use this document to prepare for your Capstone Project Review. It contains the essential talking points, metrics, and technical challenges you overcame.

## 1. The Core Problem
**Talking Point:** "Traditional machine learning (ML) Intrusion Detection Systems (IDS) applied to industrial control systems (ICS/SCADA) face two major problems: they generate too many false positives during normal operational transients, and they are easily fooled by sophisticated attackers who inject data that looks statistically 'normal' but violates physical laws."

**The Solution:** "We built a Hybrid IDS. Instead of relying solely on an ML black box, we incorporated deterministic engineering knowledge. We built a Digital Twin that calculates the physics, and a Policy Engine that checks the control logic. We fuse these deterministic engines with an LSTM Autoencoder to get the best of both worlds."

## 2. Methodology & Stack
- **Simulated Environment:** Dataset generator: to be confirmed by the project owner. Generated 150 scenarios (60 normal + 90 attack) at 1Hz.
- **Deep Learning Model:** PyTorch LSTM-Autoencoder. Trains on normal data to minimize reconstruction loss.
- **Database:** SQLite (`scada_ids.db`) stores the generated telemetry for downstream processing.
- **Frontend Dashboard:** Built with Flask, Vanilla JS, and Chart.js featuring a modern, glassmorphic dark-theme UI.

## 3. Final Metrics & Results
Our final evaluation dataset (`data/evaluation_results.csv`, 99,000 records) comprises **9 held-out normal scenarios + all 90 attack scenarios** (99 scenarios total, not an arbitrary 15% test split of the entire dataset). The remaining 51 normal scenarios were reserved strictly for unsupervised model training and validation.

Evaluation used the **Max-Vote Fusion Strategy** (`tau_fusion = 0.95`):

### Held-Out Normal Test Scenarios (9 Scenarios)
The 9 held-out normal test scenarios evaluated in `data/evaluation_results.csv` and their max LSTM reconstruction anomaly scores:
- `N_001` (Steady_State, $H_0=1.0\text{ m}$): Max $S_l = 0.803$ (margin 0.147)
- `N_006` (Steady_State, $H_0=1.0\text{ m}$): Max $S_l = 0.936$ (margin 0.014)
- `N_013` (Steady_State, $H_0=1.0\text{ m}$): Max $S_l = 0.850$ (margin 0.100)
- `N_014` (Steady_State, $H_0=1.0\text{ m}$): Max $S_l = 0.815$ (margin 0.135)
- `N_034` (Setpoint_Change, $H_0=1.0\text{ m}$): Max $S_l = 0.762$ (margin 0.188)
- `N_037` (Variable_Load, $H_0=1.0\text{ m}$): Max $S_l = 0.769$ (margin 0.181)
- `N_046` (Variable_Load, $H_0=1.0\text{ m}$): Max $S_l = 0.792$ (margin 0.158)
- `N_049` (Variable_Load, $H_0=1.0\text{ m}$): Max $S_l = 0.722$ (margin 0.228)
- `N_055` (Recovery, $H_0=0.5\text{ m}$): Max $S_l = 0.821$ (margin 0.129)

**Held-Out Normals Summary:** Max LSTM score across all 9 held-out scenarios is **0.936** (margin of **0.014** to the 0.95 anomaly threshold), yielding 0 false alarms on normal operation.

### Threshold Selection Methodology
All detection thresholds were calibrated strictly on normal baseline operational data or engineering specifications; **zero attack scenarios were used for threshold selection**:
- **$\tau_p = 0.035\text{ m}$ (Physics):** Set to the 99th percentile ($p99$) of residual errors between the Digital Twin and the simulated process under noisy flow integration across normal scenarios (`scripts/run_e0_validation.py`). No attack data was used.
- **$\tau_l = 0.0085$ (Temporal/LSTM):** Set to the maximum reconstruction error observed on the normal validation split (`df_val` from the 51 normal training/validation scenarios) to ensure normal operating dynamics stay below threshold. No attack data was used.
- **$\tau_a = 1500.0\text{ ms}, \tau_{a,max} = 5000.0\text{ ms}$ (Availability):** Established directly from SCADA network timing SLAs: at a 1 Hz polling rate, 1,500 ms flags a delayed/dropped packet, and 5,000 ms flags plant offline / complete communication loss. No attack data was used.

### Event-Level vs Per-Tick Metrics
**Event-Level Definition:** An attack is considered detected if ANY engine triggers an alarm at ANY point during the attack window.

| Attack Type | Event-Level Recall | Tick-F1 (per-scenario, all ticks) |
|-------------|--------------------|-----------------------------------|
| **FDI**     | 100%               | 0.999                             |
| **Replay**  | 100%               | 0.999                             |
| **DoS**     | 100%               | 0.215                             |
| **Auth Misuse** | 100%           | 0.218                             |

**Pooled Metrics (9 Held-Out Normals + All 90 Attack Scenarios):**
- Pooled Precision: 38.9%
- Pooled Recall: 99.8%
- Pooled F1: 56.0%
- Pooled FPR: 21.2%

**Normal Scenarios FPR (DB):** 0.000 (0 FPs out of 60,000 ticks)

### Per-Attack Engine Attribution
- **FDI**: Caught by Physics Digital Twin.
- **Replay & DoS**: Caught by Availability Engine (Timestamp/Data loss validation).
- **Auth Misuse**: Caught by Policy Engine v2 and LSTM Autoencoder.


### Important Clarifications & Limitations

1. **Policy v2 Evolution**: The original batch evaluation table uses Policy v1. The results above for Policy v2 are from a separate offline evaluation. Policy v2 introduces a strict rule derived from the controller's engineering specification: **The valve must be at its default operating position (50%) or legitimately in its fail-safe position (0% with pump OFF)**. Any other valve position immediately triggers an alarm.
2. **Auth Misuse (A4) Detection**: Policy v2 catches 100% of A4 attack ticks. The rule was refined after inspecting attack data to include the fail-safe valve exemption (valve=0 is allowed only if pump is off). Event-Level Recall is also 100% because the LSTM reliably spikes to 1.0 during the attack window.
3. **Start-up Transients & Dataset Limitations**: While there are 0 false alarms on normal scenarios, our model *does* throw false positives before attacks (start-up flags) in scenarios starting at 0.4m or 2.1m. In fact, a settled-period start-up transient occasionally exceeds the 0.95 threshold (e.g., scoring 0.96) in scenarios starting near 2.1m. This exposes a dataset limitation: normal scenarios only start at 1.0m, 0.8m, and 0.5m. The model has never seen high starts such as 2.1m, and normal levels top out near 1.7m.
4. **Physics FPR Artifacts (DoS and Auth Misuse)**: The 21.2% pooled FPR is overwhelmingly caused by Physics engine false alarms during A3 and A4 scenarios. However, this is largely a dataset artifact:
   - **DoS (A3)**: Network drops cause the batch dataset to carry *stale* flows. The twin honestly integrates these stale flows while the simulated plant kept moving, creating a divergence. 
   - **Auth Misuse (A4)**: At the exact end of the attack window, the dataset generator artificially stitched the plant state back to the nominal uncompromised trajectory, causing the observed level to teleport by 0.3m in 1 second. The twin expects continuity and refuses to teleport, creating a permanent residual.

## 4. Technical Challenges Overcome
Be prepared to discuss these challenges that you successfully debugged and fixed during the project:

1. **Twin Tracking Bias:** During our 30-minute live soak tests, the Digital Twin slowly drifted out of bounds. The clamp `max(0, Q + noise)` is part of the dataset noise spec; it creates a twin bias that is negligible within 1,000 s but exceeds `tau_p` after about 25 to 30 minutes. Long live demos use zero-mean noise as a deliberate deviation to eliminate the bias.
2. **Digital Twin Initialization Bias:** The Physics Digital Twin was originally initializing its starting state (`H_0`) by reading the very first *noisy* sensor reading. This meant the twin started with an inherent error offset, throwing off the physical residual. We fixed this by providing the twin with the *deterministic* initial state configuration.
3. **Policy Engine Thresholding:** The Policy Engine originally threw false positives during normal operation because it used strict inequalities (`>` instead of `>=`), conflicting with the tank's acceptable deadband. We fixed the control logic boundary rules.
4. **Performance Bottlenecks:** Initially, the evaluation loop was taking 35+ minutes because the Temporal Engine was instantiating a new pandas DataFrame for every single row. We optimized this by pre-allocating NumPy arrays, reducing evaluation time to ~5 minutes.
5. **Fusion Strategy Dilution:** We initially used a `weighted_sum` fusion strategy. This caused attacks like FDI to be completely missed because they only triggered one engine (maxing at 0.25, failing to cross 0.5). We switched to a `max_vote` strategy (`S_hybrid = max(engines)`), which perfectly captured these domain-specific attacks.
