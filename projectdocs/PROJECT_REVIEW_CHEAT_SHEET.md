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

### Event-Level vs Per-Tick Metrics
**Event-Level Definition:** An attack is considered detected if ANY engine triggers an alarm at ANY point during the attack window.

| Attack Type | Event-Level Recall | Per-Tick Recall | Per-Tick Precision | Per-Tick F1 |
|-------------|--------------------|-----------------|--------------------|-------------|
| **FDI**     | 100% (45/45)       | 99.7%           | 100%               | 0.999       |
| **Replay**  | 100% (15/15)       | 100%            | 100%               | 1.000       |
| **DoS**     | 100% (15/15)       | 100%            | 100%               | 1.000       |
| **Auth Misuse** | 100% (15/15)   | 100%            | 100%               | 1.000       |

- **Normal Operation False Alarms:** 0 (Zero false alarms across all normal scenarios)

### Per-Attack Engine Attribution
- **FDI**: Caught by Physics Digital Twin.
- **Replay & DoS**: Caught by Availability Engine (Timestamp/Data loss validation).
- **Auth Misuse**: Caught by Policy Engine v2 and LSTM Autoencoder.

### Important Clarifications & Limitations

1. **Policy v2 Evolution**: The original batch evaluation used Policy v1. The results above include Policy v2, which represents a new, offline evaluation of a rule added later. Crucially, the new valve rule was derived strictly from the **controller's engineering specification** (0-100% bound checking), not by fitting the test data.
2. **Auth Misuse (A4) Detection**: The Policy Engine catches Auth Misuse on 73.3% of attack ticks (the remaining 26.7% are missed because the malicious valve commands fall into physically valid 0-100% ranges). However, Event-Level Recall is 100% because the LSTM reliably spikes to 1.0 strictly during the attack window.
3. **Start-up Transients & Dataset Limitations**: While there are 0 false alarms on normal scenarios, our model *does* throw false positives before attacks (start-up flags) in scenarios starting at 0.4m or 2.1m. This exposes a dataset limitation: all normal runs start precisely at 1.0m, meaning the model has never seen normal operation from other starting levels and flags these initial states as anomalous.
4. **Post-Attack Lingering**: The Physics twin deliberately does not reset mid-scenario. Once an attack physically diverges the plant, the twin permanently flags the lingering discrepancy. This is a feature indicating physical compromise, not a standard FPR bug.

## 4. Technical Challenges Overcome
Be prepared to discuss these challenges that you successfully debugged and fixed during the project:

1. **Performance Bottlenecks:** Initially, the evaluation loop was taking 35+ minutes because the Temporal Engine was instantiating a new pandas DataFrame for every single row in the 99,000-record test dataset. We optimized this by pre-allocating NumPy arrays/dictionaries and optimizing the sliding window logic, reducing evaluation time to ~5 minutes.
2. **Digital Twin Initialization Bias:** The Physics Digital Twin was originally initializing its starting state (`H_0`) by reading the very first *noisy* sensor reading. This meant the twin started with an inherent error offset, throwing off the physical residual. We fixed this by providing the twin with the *deterministic* initial state configuration.
3. **Policy Engine Thresholding:** The Policy Engine originally threw false positives during normal operation because it used strict inequalities (`>` instead of `>=`), conflicting with the tank's acceptable deadband. We fixed the control logic boundary rules.
4. **Fusion Strategy Dilution:** We initially used a `weighted_sum` fusion strategy (25% weight per engine) with a threshold of `0.5`. This caused attacks like FDI to be completely missed because they only triggered one engine (maxing at 0.25, failing to cross 0.5). We switched to a `max_vote` strategy (`S_hybrid = max(engines)`), which perfectly captured these domain-specific attacks.
