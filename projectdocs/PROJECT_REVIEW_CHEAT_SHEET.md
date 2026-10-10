# Project Review Cheat Sheet

Use this document to prepare for your Capstone Project Review. It contains the essential talking points, metrics, and technical challenges you overcame.

## 1. The Core Problem
**Talking Point:** "Traditional machine learning (ML) Intrusion Detection Systems (IDS) applied to industrial control systems (ICS/SCADA) face two major problems: they generate too many false positives during normal operational transients, and they are easily fooled by sophisticated attackers who inject data that looks statistically 'normal' but violates physical laws."

**The Solution:** "We built a Hybrid IDS. Instead of relying solely on an ML black box, we incorporated deterministic engineering knowledge. We built a Digital Twin that calculates the physics, and a Policy Engine that checks the control logic. We fuse these deterministic engines with an LSTM Autoencoder to get the best of both worlds."

## 2. Methodology & Stack
- **Simulated Environment:** Python-based physical simulation of a Single-Tank Water SCADA system. Generates 150,000 records of telemetry (1Hz) across 150 scenarios (60 normal + 90 attack).
- **Deep Learning Model:** PyTorch LSTM-Autoencoder. Trains on normal data to minimize reconstruction loss.
- **Database:** SQLite (`scada_ids.db`) stores the generated telemetry for downstream processing.
- **Frontend Dashboard:** Built with Flask, Vanilla JS, and Chart.js featuring a modern, glassmorphic dark-theme UI.

## 3. Final Metrics & Results
Our final evaluation on the held-out streaming data yielded the following results using the **Max-Vote Fusion Strategy** (`tau_fusion = 0.95`):

- **Event-Level Recall:** 100% (All attack scenarios successfully detected in the attack window)
- **Normal Operation False Alarms:** 0 (Zero false alarms across all normal scenarios)
- **Per-Attack Engine Attribution:**
  - FDI (False Data Injection): Caught by Physics Digital Twin.
  - Replay Attack: Caught by Availability Engine (Timestamp validation).
  - DoS (Denial of Service): Caught by Availability Engine (Data loss detection).
  - Auth Misuse: Caught by Policy Engine (detects logic violations on 73% of attack ticks) and LSTM Autoencoder.

### Important: How to explain the Auth Misuse (A4) Detection
If reviewers ask how Auth Misuse is detected with perfect F1:
> *"Auth Misuse (e.g., malicious valve commands) is reliably caught by our Policy Engine, which detects control logic violations on 73% of the attack ticks. Furthermore, while the LSTM Autoencoder is sensitive to initial start-up transients, our empirical evaluation proves it spikes to a 1.0 anomaly score strictly during the attack window (compared to < 0.2 during settled periods), ensuring robust event-level detection without triggering false positives during normal operations."*

## 4. Technical Challenges Overcome
Be prepared to discuss these challenges that you successfully debugged and fixed during the project:

1. **Performance Bottlenecks:** Initially, the evaluation loop was taking 35+ minutes because the Temporal Engine was instantiating a new pandas DataFrame for every single row in the 99,000-record test dataset. We optimized this by pre-allocating NumPy arrays/dictionaries and optimizing the sliding window logic, reducing evaluation time to ~5 minutes.
2. **Digital Twin Initialization Bias:** The Physics Digital Twin was originally initializing its starting state (`H_0`) by reading the very first *noisy* sensor reading. This meant the twin started with an inherent error offset, throwing off the physical residual. We fixed this by providing the twin with the *deterministic* initial state configuration.
3. **Policy Engine Thresholding:** The Policy Engine originally threw false positives during normal operation because it used strict inequalities (`>` instead of `>=`), conflicting with the tank's acceptable deadband. We fixed the control logic boundary rules.
4. **Fusion Strategy Dilution:** We initially used a `weighted_sum` fusion strategy (25% weight per engine) with a threshold of `0.5`. This caused attacks like FDI to be completely missed because they only triggered one engine (maxing at 0.25, failing to cross 0.5). We switched to a `max_vote` strategy (`S_hybrid = max(engines)`), which perfectly captured these domain-specific attacks.
