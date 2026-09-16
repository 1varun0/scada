# Base Papers & Novel Contributions

This document explains the two base papers that form the foundation of our project, how they relate to our work, and what novel contributions we introduce beyond them.

---

## 1. Base Paper I (Primary)

**Title:** Digital Twin-Driven Intrusion Detection for Industrial SCADA: A Cyber-Physical Case Study

**Authors:** Ali Sayghe

**Published in:** *Sensors* (MDPI), Volume 25, Issue 16, Article 4963, August 2025

**DOI:** https://doi.org/10.3390/s25164963

### 1.1 What This Paper Proposes

Sayghe (2025) presents a **Digital Twin-driven Intrusion Detection (DT-ID) framework** that combines high-fidelity process simulation with hybrid anomaly detection for securing SCADA systems in water treatment plants. The core idea is that traditional network-based IDS (Intrusion Detection Systems) fail to detect process-level attacks — attacks that manipulate sensor readings or control commands without generating abnormal network traffic.

The paper proposes a two-module hybrid detection architecture:

- **Physical Module:** A digital twin runs a parallel physics simulation of the water treatment process. At each timestep, the twin predicts what sensor values *should* be based on the laws of physics (mass balance, chemical kinetics). The residual between the twin's prediction and the actual sensor reading is computed as:

  ```
  r(t) = |y_sensor(t) − y_DT(t)|
  ```

  These residuals are fed into a One-Class SVM (Support Vector Machine) with an RBF kernel to classify normal vs. anomalous behavior.

- **Cyber Module:** A 3-layer LSTM network (128 units per layer) with an attention mechanism processes sliding windows of Modbus/TCP network traffic features (packet sizes, function codes, inter-arrival times) to detect network-level anomalies.

- **Decision Fusion:** The two modules produce independent probability scores that are fused using a weighted sum:

  ```
  P_final = 0.3 × P_cyber + 0.7 × P_physical
  ```

  An anomaly is flagged if `P_final > 0.85`.

### 1.2 Key Results Reported

| Metric | Sayghe (2025) |
|:---|:---:|
| Detection F1-Score | 96.3% |
| False Positive Rate | < 2.5% |
| Detection Latency | < 500 ms |

The paper evaluates against three attack types: **False Data Injection (FDI)**, **Denial of Service (DoS)**, and **Reconnaissance**.

### 1.3 Why This Is Our Base Paper

Our project directly implements and extends the architectural paradigm proposed by Sayghe. The fundamental concept — using a physics-based digital twin running in parallel with the real system to detect process-level anomalies, combined with a learning-based module for temporal pattern detection — is the same. The table below maps each concept from the paper to our implementation:

| Concept in Sayghe (2025) | Our Implementation |
|:---|:---|
| Physics-based digital twin for a water plant | `PhysicsTwin` class — independent mass-balance simulation of a single-tank system |
| Residual computation: \|y_sensor − y_DT\| | `PhysicsEngine.step()` computes `h_observed − h_twin` at every timestep |
| LSTM for temporal anomaly detection | `LSTMAutoencoder` — a sequence-to-sequence LSTM trained to reconstruct normal behavior |
| Hybrid fusion of physics + ML scores | `FusionEngine` — combines 4 engine scores using weighted sum or max-vote strategy |
| Simulated water treatment plant | `ProcessSimulator` — Python-based simulation with tank, pump, valve, controller, and noise |
| Attack injection (FDI, DoS) | 4 attack types (FDI, Replay, DoS, Auth Misuse) across 90 attack scenarios |
| MATLAB/Simulink for physics modeling | MATLAB Simulink for deterministic physics; Python for all AI/evaluation pipelines |

---

## 2. Base Paper II (Theoretical Foundation)

**Title:** Causal Digital Twins for Cyber-Physical Security in Water Systems: A Framework for Robust Anomaly Detection

**Authors:** Mohammadhossein Homaei, Mehran Tarif, Pablo García Rodríguez, Andrés Caro, Mar Ávila

**Published in:** *Machine Learning with Applications* (Elsevier), Volume 23, Article 100824, 2026

**DOI:** https://doi.org/10.1016/j.mlwa.2025.100824

### 2.1 What This Paper Proposes

Homaei et al. (2026) present a **Causal Digital Twin (CDT) framework** that goes beyond statistical correlation to use **causal inference** for anomaly detection in water infrastructure ICS. The key argument is that existing anomaly detection methods (including deep learning) rely on statistical correlations, which leads to:

1. **High false positive rates** — because correlations cannot distinguish between normal operational changes (e.g., setpoint changes) and actual attacks.
2. **No root cause analysis** — correlations show *that* something is anomalous, but not *why*.
3. **Vulnerability to adversarial evasion** — attackers can manipulate data to maintain statistical correlations while violating physical laws.

The CDT framework operates at three levels of Pearl's Causal Hierarchy:

- **Level 1 — Association:** Observational pattern detection (similar to traditional ML).
- **Level 2 — Intervention:** Predicting system response to defensive actions using do-calculus.
- **Level 3 — Counterfactual:** "What-if" analysis on past attack events.

The framework is evaluated on three real-world benchmark datasets: **SWaT** (Secure Water Treatment), **WADI** (Water Distribution), and **HAI** (Hardware-in-the-loop AI).

### 2.2 Key Results Reported

| Metric | Homaei et al. (2026) |
|:---|:---:|
| F1-Score (SWaT) | 0.944 ± 0.014 |
| F1-Score (WADI) | 0.902 ± 0.021 |
| F1-Score (HAI) | 0.923 ± 0.018 |
| FP Reduction vs. Baselines | 48% (vs. InterFusion), 70% (vs. CNN-1D) |
| Root Cause Accuracy | 78.4% |
| Stealthy Attack Detection | 91.7% |
| Real-time Latency | 3.2 ms |

### 2.3 Why This Is Our Base Paper

Homaei et al. provide the **theoretical justification** for the design choices we made. While we did not implement their full causal inference pipeline (which involves structural causal models, do-calculus, and counterfactual reasoning), their work establishes several principles that directly shaped our architecture:

| Principle from Homaei et al. (2026) | How It Influenced Our Project |
|:---|:---|
| "Physics-based reasoning outperforms correlation-based ML for ICS anomaly detection" | Our ablation study confirms this: the Physics Engine alone (79.4% recall) far outperforms the LSTM alone (24.9% recall) |
| "Combining multiple detection mechanisms reduces false positives" | Our 4-engine hybrid fusion achieves 0% FPR on normal operating data |
| "Water systems are a critical and underserved domain for ICS security" | Validates our choice of a water tank SCADA system as the target domain |
| "Multi-scale temporal analysis improves stealthy attack detection" | Our sliding window approach (W=10) captures temporal patterns the physics engine alone cannot detect |
| "Digital Twins must be independent of sensor data to avoid adversarial contamination" | Our Physics Twin advances using only flow measurements, never trusting sensor readings for its internal state |

---

## 3. Our Novel Contributions Beyond Both Base Papers

The following table summarizes what is **new** in our project — capabilities that exist in neither Sayghe (2025) nor Homaei et al. (2026):

### 3.1 Architectural Upgrades

| Feature | Sayghe (2025) | Homaei et al. (2026) | Our Project |
|:---|:---:|:---:|:---:|
| Number of detection engines | 2 (cyber + physical) | 1 (causal anomaly score) | **4** (physics, temporal, policy, availability) |
| Policy/command safety engine | ❌ | ❌ | ✅ Deterministic rules checking pump/valve commands against tank level |
| Availability/freshness engine | ❌ | ❌ | ✅ Monitors packet arrival and timestamp freshness for DoS and replay detection |
| Fusion strategy comparison | Fixed weights (0.3/0.7) | N/A | **Ablation study across 8 configurations** comparing weighted-sum vs. max-vote |
| ML architecture | LSTM + Attention + SVM | Structural Causal Models | **LSTM-Autoencoder** (unsupervised reconstruction error) |

### 3.2 Evaluation Scale

| Aspect | Sayghe (2025) | Homaei et al. (2026) | Our Project |
|:---|:---:|:---:|:---:|
| Total scenarios | Not specified | Uses existing SWaT/WADI/HAI datasets | **150 scenarios** (60 normal + 90 attack) |
| Total telemetry records | Not specified | ~950K (SWaT + WADI + HAI combined) | **150,000 records** at 1 Hz |
| Attack types tested | 3 (FDI, DoS, Recon) | 41 (from SWaT benchmark) | **4 types, 90 scenarios** (FDI: 45, Replay: 15, DoS: 15, Auth Misuse: 15) |
| Attack parameter variation | Single configuration per type | Fixed benchmark attacks | **Multiple severity levels** (e.g., FDI bias: 0.05m, 0.10m, 0.20m; DoS: 20s to 120s) |
| Operating conditions tested | Steady state | Varies by dataset | **4 conditions** (Steady State, Setpoint Change, Variable Load, Recovery) |

### 3.3 Methodological Contributions

| Contribution | Description |
|:---|:---|
| **Max-Vote Fusion Strategy** | We identified that the traditional weighted-sum fusion (as used by Sayghe) causes attacks to be missed when they only trigger one engine. Our max-vote strategy (`S_hybrid = max(active engines)`) solves this — achieving 100% scenario-level detection. This is a direct improvement over the base paper's fixed weighted sum. |
| **Comprehensive Ablation Study** | We evaluated 8 engine configurations (C1–C7) to quantify each engine's individual and combined contribution. This is absent in both base papers and provides empirical evidence for the value of each detection module. |
| **Scenario-Aware Data Splitting** | We split training/test data by entire scenario IDs rather than random row shuffling to prevent temporal autocorrelation leakage — a critical methodological detail not discussed in either base paper. |
| **End-to-End Reproducible Pipeline** | Our project includes a complete pipeline from MATLAB simulation → SQLite database → Python evaluation → Flask dashboard, making the entire experiment reproducible. Neither base paper provides this level of end-to-end integration. |
| **Real-Time Interactive Dashboard** | A web-based visualization tool (Flask + Chart.js) allowing scenario-by-scenario inspection of engine scores, physical state, and anomaly decisions — not provided by either base paper. |

### 3.4 Results Comparison

| Metric | Sayghe (2025) | Homaei et al. (2026) | Our Project |
|:---|:---:|:---:|:---:|
| **Detection Rate (Recall)** | Included in 96.3% F1 | ~94% (SWaT) | **99.8%** |
| **FPR on Normal Data** | < 2.5% | 5.3% (SWaT) | **0.0%** |
| **Scenario-Level Detection** | Not reported | Not reported | **100% (90/90 attack scenarios)** |
| **Detection Latency** | < 500 ms | 3.2 ms | **0s median** |
| **Ablation Study** | ❌ | ❌ | ✅ 8 configurations |

> **Note on FPR:** Our 0% FPR on normal data means the system never raises false alarms during genuinely normal operations. The overall FPR of 21% is entirely due to post-attack digital twin divergence within attack scenarios (where `ground_truth` reverts to 0 but the twin remains diverged by design). This is explained further in the Project Review Cheat Sheet.

---

## 4. Summary: How to Explain This in the Review

### The 30-Second Pitch

> "Our project builds on two recent papers in SCADA cybersecurity. The first, by Sayghe (2025), proposed combining a digital twin with machine learning for hybrid anomaly detection. The second, by Homaei et al. (2026), established that physics-based causal reasoning outperforms pure ML for industrial control system security.
>
> We take the architectural blueprint from Sayghe and extend it from a 2-engine system to a 4-engine system — adding a Policy Engine for command safety validation and an Availability Engine for communication integrity monitoring. We also replace the fixed fusion weights with a systematic ablation study comparing 8 different engine configurations, discovering that a max-vote fusion strategy outperforms the weighted-sum approach used in the base paper.
>
> Our results confirm the theoretical prediction from Homaei et al.: deterministic physics-based engines individually outperform the ML engine, but the hybrid combination of all four achieves the best overall detection performance."

### If the Reviewer Asks: "What Exactly Is New?"

1. **Two new detection engines** (Policy + Availability) that neither base paper has
2. **Max-vote fusion** that solves the weighted-sum dilution problem identified in the base paper
3. **8-configuration ablation study** providing empirical evidence for each engine's contribution
4. **4 attack types across 90 scenarios** with multiple severity levels (vs. 3 types in the base paper)
5. **Interactive real-time dashboard** for scenario inspection
6. **Zero false positives on normal data** (vs. < 2.5% in base paper)
