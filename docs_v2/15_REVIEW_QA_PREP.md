# 15 — Review Q&A Preparation & Capstone Defense Guide

- **Audience**: Presenting engineers, defense candidates, technical auditors, and faculty evaluators
- **Scope**: 25 hardest, most critical technical review and oral defense questions spanning numbers, physics, ML, attack mechanics, active prevention, and sim-to-real boundaries
- **Status**: Complete & Code-Audited
- **Evidence Tags**: `[CODE]`, `[MEASURED]`, `[EXISTING-DOC]`, `[DESIGN-INTENT]`

---

## Thematic Index of Defense Questions

- **Category 1: Dataset, Scenarios & Discrepancies** (Q01 – Q05)
- **Category 2: Digital Twin & Physical Principles** (Q06 – Q09)
- **Category 3: Multi-Engine Detection & Fusion Mechanics** (Q10 – Q14)
- **Category 4: Closed-Loop Active Prevention & Control** (Q15 – Q18)
- **Category 5: Authorization Misuse & Hardware Boundaries** (Q19 – Q22)
- **Category 6: Engineering Realism & Sim-to-Real Gap** (Q23 – Q25)

---

## Category 1: Dataset, Scenarios & Discrepancies

### Q01: Why do legacy project documents claim 170 scenarios (80 normal + 90 attack) when the database only contains 150 scenarios (60 normal + 90 attack)?
- **Direct Talking Point**: The database `data/scada_ids.db` and MATLAB generator `matlab/run_all_scenarios.m` create exactly **150 scenarios** ($150,000\text{ rows}$). The number 170 is a documented historical documentation artifact from early planning before the normal baseline was finalized at 60 scenarios [EXISTING-DOC DOC_VS_CODE_DISCREPANCIES.md#discrepancy-1].
- **Deep Technical Explanation**:
  Direct inspection of `config/scenarios.py` reveals two generator functions: `generate_normal_scenarios()` which yields 60 configs (`N_001` to `N_060`), and `generate_attack_scenarios()` which yields 90 configs (`A1_001` to `A1_045`, `A2_001` to `A2_015`, `A3_001` to `A3_015`, `A4_001` to `A4_015`) [CODE config/scenarios.py:104-342]. SQLite table metadata confirms:
  ```sql
  SELECT COUNT(DISTINCT scenario_id) FROM scada_telemetry; -- Returns 150
  SELECT COUNT(*) FROM scada_telemetry;                     -- Returns 150,000
  ```
  The legacy claim of 80 normal scenarios included 20 proposed high-load transient runs that were never implemented in MATLAB or Python generators.
- **Evidence Citations**: `[CODE config/scenarios.py:104-166]`, `[MEASURED docs_v2/_audit/outputs/db_queries_output.txt]`.
- **Potential Pitfall / Gotcha**: If a reviewer asks, "Did you lose 20 scenarios?", answer: *"No, exactly 150 scenarios were generated and evaluated; 170 was an unadjusted specification target from Phase 0 planning."*

---

### Q02: Why does the batch evaluation dataset evaluate 99 scenarios (99,000 rows) instead of all 150 scenarios or a standard 15% test split?
- **Direct Talking Point**: The 99 scenarios in `data/evaluation_results.csv` consist of **9 held-out normal test scenarios + all 90 attack scenarios** [MEASURED evaluation/evaluation_results.csv]. The remaining 51 normal scenarios were strictly reserved for unsupervised training (41 scenarios) and validation (10 scenarios) of the LSTM Autoencoder [CODE checkpoints/data_split_v1.json].
- **Deep Technical Explanation**:
  Evaluating unsupervised anomaly detection on training data inflates performance. Hence, 51 of the 60 normal scenarios ($51,000\text{ rows}$) were partitioned exclusively into `train_scenarios` (41) and `val_scenarios` (10). The test evaluation set was constructed using the 9 held-out normal scenarios ($9,000\text{ rows}$) and evaluated alongside all 90 attack scenarios ($90,000\text{ rows}$), totaling $99,000\text{ rows}$ (99 scenarios).
- **Evidence Citations**: `[CODE checkpoints/data_split_v1.json:1-68]`, `[CODE scripts/run_evaluation.py:270-285]`.
- **Potential Pitfall / Gotcha**: Do not say "we tested on a random 15% split". The split is structured by scenario IDs: normal scenarios are partitioned by ID, while all attack scenarios are evaluated to compute comprehensive threat recall.

---

### Q03: Why is the batch pooled precision only 38.9% (pooled FPR 21.2%) when event-level recall is 100% and normal scenario FPR is 0.00%?
- **Direct Talking Point**: The 38.9% pooled precision is an artifact caused entirely by **post-attack false alarms** during DoS (A3) and Authenticated Misuse (A4) scenarios in the stored batch dataset, where open-loop generators created abrupt $+0.167\text{ m}$ level jumps at attack completion [EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:53-70].
- **Deep Technical Explanation**:
  Over the 9 held-out normal scenarios ($9,000\text{ ticks}$), there are **0 false alarms** (0.00% FPR) [MEASURED data/evaluation_results.csv]. Across all 60 normal scenarios in the database ($60,000\text{ ticks}$), there are only 2 false positive ticks (FPR = $0.0033\%$). Furthermore, during pre-attack normal ticks across all 90 attack scenarios, there are only 405 false positive ticks (caused by high initial starts $H_0 = 2.1\text{ m}$).
  However, in A3 (DoS) and A4 (Auth Misuse), the MATLAB post-hoc generators stopped modifying rows when the attack ended, abruptly reverting the table to the unattacked peaceful trajectory. The continuous Physics Twin refused to teleport $+0.167\text{ m}$ in 1 second, resulting in 18,062 post-attack false positive ticks ($7,561\text{ in A3} + 10,485\text{ in A4}$).
  When evaluated excluding post-attack ticks (the "Generous View"), **precision is 96.7%, recall is 99.8%, F1 is 98.2%, and FPR is 1.08%**.
- **Evidence Citations**: `[MEASURED data/evaluation_results.csv]`, `[CODE experiments/check_normals.py:1-120]`.
- **Potential Pitfall / Gotcha**: Never claim "precision is 99% across the board". State clearly: *"Batch pooled precision across all rows is 38.9% due to generator step discontinuities; clean pre-attack precision is 96.7%."*

---

### Q04: What are the post-hoc attack generation artifacts in MATLAB, and why are they fundamentally open-loop?
- **Direct Talking Point**: In MATLAB, normal simulations ran to completion first; attack scripts (`apply_fdi.m`, `apply_dos.m`, `apply_auth_misuse.m`) subsequently overwritten table columns in memory without re-running closed-loop plant physics or controller feedback [EXISTING-DOC DOC_VS_CODE_DISCREPANCIES.md#discrepancy-11].
- **Deep Technical Explanation**:
  1. *FDI (`apply_fdi.m`)*: Modifies only `tank_level_observed(k)`. Because the controller already executed during `run_single_scenario.m`, actuator states (`pump_command`, `valve_command`) remained those of the peaceful normal run. The controller was never fooled into cutting the pump in the stored dataset.
  2. *DoS (`apply_dos.m`)*: Freezes level during $[t_{\text{start}}, t_{\text{end}}]$ with zero flows. At $t > t_{\text{end}}$, the script sets `H = -1` and exits. The table abruptly resumes the peaceful filling trajectory at $t_{\text{end}} + 1$, creating a step jump of up to $+0.167\text{ m}$ in 1 second.
  3. *Auth Misuse (`apply_auth_misuse.m`)*: Locally integrates rapid draining or filling during $[200, 300]\text{ s}$. At $t = 301\text{ s}$, the script stops, snapping the water level from $0.15\text{ m}$ back to $1.00\text{ m}$ in 1 second.
- **Evidence Citations**: `[CODE matlab/attacks/apply_fdi.m:15-38]`, `[CODE matlab/attacks/apply_dos.m:20-41]`, `[CODE matlab/attacks/apply_auth_misuse.m:30-85]`.
- **Potential Pitfall / Gotcha**: Be ready to contrast batch open-loop generation with Phase 4–7 live simulation (`LivePlant`), which is 100% closed-loop.

---

### Q05: Why does the system throw false alarms before attacks (pre-attack FPs) in scenarios starting at $H_0 = 2.1\text{ m}$ or $0.4\text{ m}$?
- **Direct Talking Point**: The LSTM Autoencoder was trained strictly on normal scenarios starting at $1.0\text{ m}$, $0.8\text{ m}$, and $0.5\text{ m}$. When evaluated on A4 scenarios initialized at $H_0 = 2.1\text{ m}$ or $0.4\text{ m}$, the model encounters an out-of-distribution state manifold during initial transients [EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:81].
- **Deep Technical Explanation**:
  The normal training set contains steady-state profiles ($1.0\text{ m}$), setpoint steps ($1.0 \to 1.5\text{ m}$), ramps ($0.8 \to 1.4\text{ m}$), and recoveries ($0.5 \to 1.0\text{ m}$) [CODE config/scenarios.py:109-165]. Liquid levels never exceed $1.70\text{ m}$ during training.
  In A4 scenarios (`A4_004`, `A4_007`, `A4_010`, `A4_013`), initial conditions were configured at $H_0 = 2.10\text{ m}$ to make rogue pump commands immediately hazardous. During ticks $0\text{--}100\text{ s}$, the LSTM reconstruction error produces scaled scores $S_l \approx 0.96$, crossing the $0.95$ threshold and generating 405 pre-attack false positive ticks before the attack initiates at $t = 200\text{ s}$.
- **Evidence Citations**: `[CODE checkpoints/data_split_v1.json:1-40]`, `[MEASURED experiments/results/check_normals_output.txt]`.
- **Potential Pitfall / Gotcha**: Acknowledge this honestly as a training distribution limitation, not an algorithmic defect.

---

## Category 2: Digital Twin & Physical Principles

### Q06: How is the continuous liquid level ODE discretized, and why does Euler integration with $dt = 1.0\text{ s}$ suffice without numerical instability?
- **Direct Talking Point**: The system uses Forward Euler integration: $H_{k+1} = H_k + \frac{Q_{\text{in},k} - Q_{\text{out},k}}{A} \Delta t$. Because the tank cross-sectional area is large ($A = 2.0\text{ m}^2$) and maximum flows are small ($Q \le 0.005\text{ m}^3\text{/s}$), the physical time constant is $\tau_{\text{plant}} \approx 400\text{ s}$, making $dt = 1.0\text{ s}$ unconditionally stable [CODE digital_twin/physics_twin.py:53-56].
- **Deep Technical Explanation**:
  Linearizing outflow $Q_{\text{out}} = C_v \left(\frac{V\%}{100}\right) \sqrt{H}$ around nominal operating level $H_0 = 1.0\text{ m}$ with $V = 50\%$:
  $$\left.\frac{\partial Q_{\text{out}}}{\partial H}\right|_{H_0} = \frac{C_v \cdot 0.5}{2 \sqrt{H_0}} = \frac{0.004 \times 0.5}{2 \times 1.0} = 0.0010\text{ m}^2\text{/s}$$
  The linearized plant pole is $\lambda = -\frac{1}{A} \frac{\partial Q_{\text{out}}}{\partial H} = -\frac{0.0010}{2.0} = -0.0005\text{ s}^{-1}$.
  For Forward Euler stability, the requirement is $|1 + \lambda \Delta t| < 1$, which translates to $\Delta t < \frac{2}{0.0005} = 4,000\text{ s}$.
  At $\Delta t = 1.0\text{ s}$, the integration operates at $0.025\%$ of the stability threshold, producing negligible truncation error.
- **Evidence Citations**: `[CODE digital_twin/physics_twin.py:53-56]`, `[CODE docs_v2/03_FORMULAS_REFERENCE_V2.md]`.
- **Potential Pitfall / Gotcha**: If asked about RK4 (Runge-Kutta 4th order), note: *"RK4 was evaluated, but for linear inflow and square-root outflow at 1Hz, RK4 and Euler agree within $0.0001\text{ mm}$, rendering higher-order solvers computationally redundant."*

---

### Q07: Why did the Digital Twin slowly drift out of bounds during 30-minute soak runs when using clamped flow noise, and why does un-clamped noise fix it?
- **Direct Talking Point**: Half-Gaussian rectification from `max(0, Q + noise)` induces an asymmetric positive expected value $\mathbb{E}[\eta] = \sigma \sqrt{2/\pi}$, causing continuous positive flow drift ($+14\text{ cm}$ over 30 min) [MEASURED experiments/results/soak_comparison_output.txt]. Un-clamped symmetric Gaussian noise has $\mathbb{E}[\eta] = 0$, eliminating drift entirely.
- **Deep Technical Explanation**:
  When flow meter noise ($\sigma = 0.0001\text{ m}^3\text{/s}$) is passed through `max(0, Q + \eta)` at low flow or pump shutoff ($Q = 0$), negative noise fluctuations are truncated to zero while positive fluctuations pass through unhindered. This transforms the zero-mean Gaussian distribution into a half-normal distribution with mean $\mu = \sigma \sqrt{2/\pi} \approx +0.00008\text{ m}^3\text{/s}$.
  Integrating this biased flow over $T = 1800\text{ s}$ yields:
  $$\Delta H = \frac{1800 \times 0.00008}{2.0\text{ m}^2} \approx +0.072\text{ m}$$
  Under lower operational duty cycles, the drift accumulates to $+0.14\text{ m}$, crossing $\tau_p = 0.080\text{ m}$ and falsely tripping twin takeover in 10 out of 10 seeds. Setting `clamp_flow_noise: false` restores zero-mean symmetry ($\mathbb{E}[\eta] = 0$), yielding 0 false takeovers over 60 minutes across all 10 seeds.
- **Evidence Citations**: `[CODE scada_live/config.yaml:18]`, `[MEASURED experiments/results/soak_comparison_output.txt]`.
- **Potential Pitfall / Gotcha**: Make sure to explain that clamped noise is preserved for replicating the batch dataset, but un-clamped noise is standard for live deployment.

---

### Q08: How does the Digital Twin remain invariant to valve discharge coefficient ($C_v$) calibration errors or nonlinear pipe friction?
- **Direct Talking Point**: The Digital Twin integrates mass conservation directly using measured inflow and outflow rates from physical flow meters: $\frac{d\hat{H}}{dt} = \frac{Q_{\text{in,meas}} - Q_{\text{out,meas}}}{A}$ [CODE digital_twin/physics_twin.py:53-56]. Because the twin does not evaluate Torricelli's valve discharge equation ($C_v \sqrt{H}$), valve errors never enter twin calculations.
- **Deep Technical Explanation**:
  In a supervisory control loop, valve $C_v$ errors or mechanical wear alter the plant's physical discharge hydraulics. However, the discharge flow meter measures the *actual* resulting volumetric discharge $Q_{\text{out}}$ and transmits it in the telemetry packet.
  The digital twin's state update is strictly:
  $$\hat{H}_{k+1} = \hat{H}_k + \frac{Q_{\text{in}} - Q_{\text{out}}}{A} \Delta t$$
  Because $C_v$ does not appear in this equation, errors in $C_v$ (even up to $\pm 20\%$) have zero mathematical impact on the twin residual [MEASURED experiments/results/mismatch_sensitivity_output.txt]. Only calibration errors in the flow meters themselves ($\Delta Q$) or tank cross-sectional area ($\Delta A$) can cause twin divergence.
- **Evidence Citations**: `[CODE digital_twin/physics_twin.py:53-56]`, `[MEASURED experiments/results/mismatch_sensitivity_output.txt]`.
- **Potential Pitfall / Gotcha**: A reviewer might confuse the plant controller (which uses level to command valves) with the twin observer (which uses flow to track mass balance). Emphasize that the twin is a mass-balance observer.

---

### Q09: If flow sensor bias accumulates drift over time ($\Delta H = \frac{\Delta Q}{A} \cdot t$), why doesn't the twin cause false takeovers or plant damage during extended operations?
- **Direct Talking Point**: During normal operation, the controller uses the *sensed* liquid level, not the twin; the twin only runs as a background residual monitor. Furthermore, during active twin takeover, degraded mode is bounded by a 600-second watchdog timeout (`max_degraded_s = 600`) [CODE scada_live/config.yaml:72].
- **Deep Technical Explanation**:
  Under a severe 5% flow meter calibration bias on nominal flow $Q = 0.002\text{ m}^3\text{/s}$ in a tank of area $A = 2.0\text{ m}^2$, the rate of error accumulation is:
  $$\frac{dh}{dt} = \frac{0.05 \times 0.002}{2.0} = 0.00005\text{ m/s} = 0.05\text{ mm/s}$$
  Across the maximum allowable open-loop degraded window of $600\text{ s}$, the total accumulated drift is:
  $$\Delta H = 600\text{ s} \times 0.05\text{ mm/s} = 30\text{ mm} = 3.0\text{ cm}$$
  A $3.0\text{ cm}$ drift is safely absorbed within the $[0.80, 1.20]\text{ m}$ operational deadband ($40\text{ cm}$ wide) and remains far from safety limits ($0.30\text{ m}$ dry-run, $2.20\text{ m}$ overflow). If the attack persists beyond 600s, the watchdog transitions the plant to a hardwired fail-safe state.
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:420-435]`, `[EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:125-128]`.
- **Potential Pitfall / Gotcha**: Never claim the digital twin can run open-loop indefinitely. Open-loop observers are strictly time-bounded.

---

## Category 3: Multi-Engine Detection & Fusion Mechanics

### Q10: How were detection thresholds chosen, and did threshold calibration overfit on attack data?
- **Direct Talking Point**: All detection thresholds were calibrated strictly on unattacked normal operational baselines or physical engineering specifications; **zero attack scenarios were used for threshold selection** [EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:35-40].
- **Deep Technical Explanation**:
  1. *Physics Threshold ($\tau_p = 0.035\text{ m}$ batch, $0.080\text{ m}$ live)*: In batch mode, set to $2 \times \text{p99}$ residual of normal baseline scenario $E_0$ ($0.0175\text{ m}$). In live mode, set to $0.080\text{ m}$ to accommodate $3\sigma$ sensor noise ($1.5\text{ cm}$) plus dynamic setpoint change residuals ($2.5\text{ cm}$) with a $2\times$ safety buffer.
  2. *Temporal LSTM Threshold ($\tau_l = 0.0085$ MSE, $0.95$ scaled)*: Set to the maximum reconstruction error observed on the normal validation split (`df_val` from 10 unattacked normal scenarios).
  3. *Availability Thresholds ($\tau_a = 1500\text{ ms}$, $\tau_{a,\text{max}} = 5000\text{ ms}$)*: Derived from SCADA network SLAs: at a 1Hz polling interval, $1500\text{ ms}$ indicates packet loss/jitter, and $5000\text{ ms}$ indicates total communication loss.
- **Evidence Citations**: `[CODE config/parameters.py:89]`, `[CODE checkpoints/data_split_v1.json:1-68]`, `[CODE engines/availability_engine.py:46-48]`.
- **Potential Pitfall / Gotcha**: Highlight that zero attack scenarios were accessed during hyperparameter tuning, maintaining methodological rigor.

---

### Q11: What is the exact separation margin for the 9 held-out normal test scenarios under the LSTM Autoencoder and Physics Twin?
- **Direct Talking Point**: On the 9 held-out normal test scenarios ($9,000\text{ ticks}$), the maximum LSTM reconstruction score is **0.936** (margin of **0.014** to threshold $0.950$), and the maximum physics residual is **0.0288 m** (margin of **0.0062 m** to threshold $0.0350\text{ m}$), producing **0 false alarms** [MEASURED evaluation/evaluation_results.csv].
- **Deep Technical Explanation**:
  Inspecting the per-scenario maximums across all 9 held-out normals:
  - `N_001`: Max $S_l = 0.803$ (margin 0.147)
  - `N_006`: Max $S_l = 0.936$ (margin 0.014)
  - `N_013`: Max $S_l = 0.850$ (margin 0.100)
  - `N_014`: Max $S_l = 0.815$ (margin 0.135)
  - `N_034`: Max $S_l = 0.762$ (margin 0.188)
  - `N_037`: Max $S_l = 0.769$ (margin 0.181)
  - `N_046`: Max $S_l = 0.792$ (margin 0.158)
  - `N_049`: Max $S_l = 0.722$ (margin 0.228)
  - `N_055`: Max $S_l = 0.821$ (margin 0.129)
  In live 30-minute soak tests, the maximum live LSTM score is $0.838$ (margin of $0.112$ to $0.950$).
- **Evidence Citations**: `[MEASURED data/evaluation_results.csv]`, `[EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:21-34]`.
- **Potential Pitfall / Gotcha**: The margin on `N_006` is narrow (0.014). If asked, explain that `N_006` experienced a high noise peak, but still remained safely below threshold.

---

### Q12: Why did you abandon weighted-sum fusion in favor of Max-Vote Fusion with Veto Overrides?
- **Direct Talking Point**: Weighted averaging dilutes sharp single-domain anomalies: an attack that triggers a score of $1.0$ on one engine only scores $0.35$ in a weighted sum, failing to cross a $0.50$ threshold [EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:199]. Max-Vote captures domain-specific attacks instantly.
- **Deep Technical Explanation**:
  Under weighted fusion:
  $$S_{\text{hybrid}} = 0.35 S_p + 0.35 S_l + 0.15 S_c + 0.15 S_a$$
  If an adversary injects a pure False Data Injection bias, the Physics Twin fires ($S_p = 1.0$), but the Availability ($S_a = 0$) and Policy ($S_c = 0$) engines remain quiescent. The resulting hybrid score is $0.35 \times 1.0 = 0.35$, which falls below the $0.50$ alarm threshold.
  Max-Vote Fusion sets $S_{\text{hybrid}} = \max(S_p, S_l, S_c, S_a)$, ensuring that if any specialized domain engine detects an impossible physical condition, the alarm triggers immediately. Veto Overrides guarantee that protocol violations (e.g., DoS watchdog timeouts or wire tamper) immediately force CRITICAL state.
- **Evidence Citations**: `[CODE engines/fusion_engine.py:84-118]`, `[CODE scada_live/scada_ids/gateway_core.py:350-395]`.
- **Potential Pitfall / Gotcha**: A reviewer may ask, "Doesn't max-vote increase false alarms?" Answer: *"No, because each constituent engine's threshold was strictly calibrated on normal data to have near-zero FPR."*

---

### Q13: What is the empirical detection cliff for constant sensor bias attacks, and what is the smallest bias your system can reliably detect?
- **Direct Talking Point**: The empirical detection cliff is at **$\approx 3.0\text{ cm}$**: biases $\le 1.0\text{ cm}$ produce 0% CRITICAL detections; $2.0\text{ cm}$ produces sporadic warnings; biases $\ge 3.0\text{ cm}$ achieve 100% detection within $12.4\text{ s}$ [MEASURED data/bias_sweep_results.csv].
- **Deep Technical Explanation**:
  Constant bias sweeps evaluated across 10 random seeds over $1200\text{ s}$ established:
  - $0.0\text{ cm}$ (Baseline): 0 false takeovers, FPR = $0.017\%$ ($2 / 12,000\text{ ticks}$).
  - $1.0\text{ cm}$: 0% detection rate; mean detection delay is $\infty$.
  - $2.0\text{ cm}$: 10% detection rate (mean delay $1193\text{ s}$) due to constructive sensor noise peaks ($3\sigma = 1.5\text{ cm}$).
  - $3.0\text{ cm}$: **100% detection rate** (mean delay $12.4\text{ s}$).
  - $4.0\text{--}5.0\text{ cm}$: **100% detection rate** (mean delay $\le 2.0\text{ s}$).
  We do not claim that any bias below $\tau_p = 3.5\text{ cm}$ or $8.0\text{ cm}$ is completely invisible; sensor noise ($3\sigma = 1.5\text{ cm}$) constructively sums with the bias, causing biases of $3.0\text{ cm}$ to reliably trip detection.
- **Evidence Citations**: `[MEASURED data/bias_sweep_results.csv]`, `[MEASURED experiments/results/constant_bias_sweep_output.txt]`.
- **Potential Pitfall / Gotcha**: Do not claim "our system detects 1 mm biases". State clearly that physics residual limits set the boundary at $3.0\text{ cm}$.

---

### Q14: How does the Availability Engine differentiate between network jitter, packet drops, and a full Denial of Service outage?
- **Direct Talking Point**: The Availability Engine uses a two-tier SLA threshold: packet inter-arrival latency $\Delta t \in (1500, 5000]\text{ ms}$ triggers WARNING, while $\Delta t > 5000\text{ ms}$ triggers CRITICAL outage [CODE engines/availability_engine.py:46-48].
- **Deep Technical Explanation**:
  At a nominal 1Hz polling interval:
  - Normal packets arrive with latency $\Delta t \approx 1000 \pm 50\text{ ms}$ ($S_a = 0.0$).
  - Transient network jitter or isolated drops ($1500\text{ ms} < \Delta t \le 5000\text{ ms}$) scale the anomaly score linearly:
    $$S_a = \frac{\Delta t - 1500}{5000 - 1500}$$
    producing a WARNING alert without disconnecting the controller.
  - Complete outages ($\Delta t > 5000\text{ ms}$) saturate $S_a = 1.0$, trigger CRITICAL alarm state, activate local actuator fail-safe fallbacks (`pump = 0, valve = default`), and engage watchdog packet synthesis.
- **Evidence Citations**: `[CODE engines/availability_engine.py:46-75]`, `[CODE scada_live/scada_ids/alert_manager.py:25-50]`.
- **Potential Pitfall / Gotcha**: Emphasize that single dropped packets do not trip fail-safe shutdown; the system requires sustained communication failure ($5\text{ s}$).

---

## Category 4: Closed-Loop Active Prevention & Control

### Q15: How does the Gateway transition from Monitor mode to Prevention mode, and what is the exact mechanism of Digital Twin Takeover?
- **Direct Talking Point**: In Monitor mode, the gateway logs anomalies but executes control using the received sensor reading; in Prevention mode, an anomaly switches the feedback variable from `sensed_level` to the internal Digital Twin estimate $\hat{H}$ [CODE scada_live/scada_ids/gateway_core.py:408-417].
- **Deep Technical Explanation**:
  In `GatewayCore.process_sense(measured_level)`:
  ```python
  if self.mode == "prevention" and self.level_source == "twin":
      control_level = self.ids.get_twin_estimate()
  else:
      control_level = measured_level
  ```
  When the IDS detects an active attack ($S_{\text{hybrid}} \ge 0.50$ or CRITICAL state), `GatewayCore` switches `level_source = "twin"`. The autonomous deadband controller continues regulating the physical plant using $\hat{H}$, completely isolating control actuation from spoofed sensor telemetry.
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:408-417]`, `[CODE experiments/run_full_evaluation.py:126-128]`.
- **Potential Pitfall / Gotcha**: Ensure you clarify that Prevention mode does not halt the plant; it actively maintains normal water production via analytical redundancy.

---

### Q16: How does the Gateway prevent "control chatter" or thrashing between sensed level and twin level during active spoofing?
- **Direct Talking Point**: The gateway implements an asymmetric hysteresis latch: takeover occurs instantly on CRITICAL alarm, but handback to the sensor requires residual stability within tolerance ($0.05\text{ m}$) for sustained consecutive ticks [CODE scada_live/scada_ids/gateway_core.py:418-430].
- **Deep Technical Explanation**:
  Once twin takeover is active, control remains locked to the twin even if the anomaly score drops to WARNING. Control is only handed back to the physical sensor if:
  $$|H_{\text{sensed}} - \hat{H}_{\text{twin}}| \le \text{handback\_tolerance\_m} \ (0.05\text{ m})$$
  and the IDS alert manager clears to NORMAL. Because the handback tolerance ($5.0\text{ cm}$) exceeds $3\sigma$ sensor noise ($1.5\text{ cm}$), noise fluctuations cannot trigger false handbacks while active spoofing persists. In tests with transient bias removal (`Ramp_Hold_Return`), control handed back smoothly at $t = 1194.3 \pm 1.1\text{ s}$ without a single chatter oscillation [MEASURED experiments/results/handback_verification_output.txt].
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:418-430]`, `[MEASURED experiments/results/handback_verification_output.txt]`.
- **Potential Pitfall / Gotcha**: Mention that if the sensor never recovers, the watchdog allows degraded twin control for up to 600s before safe shutdown.

---

### Q17: What is the Step 2b DoS Gap Re-Seed Rule, and why was it necessary upon communication restoration?
- **Direct Talking Point**: Following a DoS communication blackout, the twin has integrated zero flow while the real tank moved. The Step 2b rule collects $K=5$ packets, verifies low variance, and checks physical rate bounds before re-synchronizing the twin [CODE scada_live/scada_ids/streaming_ids.py:75-145].
- **Deep Technical Explanation**:
  During a 60-second DoS outage, the twin holds level constant ($dH=0$). Upon link restoration, the observed level may differ by $10\text{ cm}$. Without re-seeding, this discrepancy creates an artificial residual that persists for thousands of ticks.
  The Step 2b rule executes:
  1. Buffer $K = 5$ valid packets following the outage.
  2. Verify stability: standard deviation $\sigma \le 0.03\text{ m}$.
  3. Physical Rate Test: Verify that the difference between the median post-gap reading $m$ and the twin $\hat{H}$ is physically reachable given maximum pump and valve flow rates over outage duration $G$:
     $$|m - \hat{H}_{\text{twin}}| \le v_{\text{max}} \cdot G \cdot dt + 3\sigma_{\text{sensor}}$$
     where $v_{\text{max}} = 0.003162\text{ m/s}$.
  4. If true, re-seed $\hat{H} \leftarrow m$. If false, reject re-seed and engage twin takeover.
- **Evidence Citations**: `[CODE scada_live/scada_ids/streaming_ids.py:75-145]`, `[EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:90]`.
- **Potential Pitfall / Gotcha**: A reviewer might note that an attacker could inject a small bias within rate bounds after a gap. Acknowledge this limitation honestly: the rule bounds jumps to physical reality; eliminating it completely requires independent out-of-band flow confirmation.

---

### Q18: What is the theoretical and practical limit of open-loop Digital Twin Takeover (`max_degraded_s = 600\text{ s}`)?
- **Direct Talking Point**: The theoretical limit of open-loop ODE integration is bounded by unmeasured physical parameter drift and flow sensor bias; 600 seconds bounds accumulated drift to $\le 3.0\text{ cm}$, safely inside the $40\text{ cm}$ operational deadband [CODE scada_live/config.yaml:72].
- **Deep Technical Explanation**:
  Any open-loop observer without measurement feedback accumulates error over time:
  $$e(t) = \int_0^t \frac{\Delta Q_{\text{in}}(\tau) - \Delta Q_{\text{out}}(\tau)}{A} d\tau$$
  Under a 5% calibration mismatch, drift accumulates at $0.05\text{ mm/s}$.
  Over $t = 600\text{ s}$, drift is $30\text{ mm}$ ($3.0\text{ cm}$). Because normal deadband cycling spans $[0.80, 1.20]\text{ m}$, a $3\text{ cm}$ offset causes minor cycling phase shifts but zero risk of tank overflow ($2.20\text{ m}$) or dry-run ($0.30\text{ m}$). After 600s, the gateway transitions to a safe standby state.
- **Evidence Citations**: `[CODE scada_live/config.yaml:72]`, `[EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:125-128]`.
- **Potential Pitfall / Gotcha**: Never claim the digital twin can run indefinitely. Always emphasize that open-loop control is a bounded degraded operational mode.

---

## Category 5: Authorization Misuse & Hardware Boundaries

### Q19: How can your system detect Authenticated Misuse (A4 / AM-1..AM-6) if the adversary possesses legitimate operator credentials and valid HMAC tokens?
- **Direct Talking Point**: Cyber authentication verifies *identity*, not *process safety*. Our system evaluates commands against physical state-space invariants: commands that drive the plant toward safety violations are blocked regardless of cryptographic credentials [CODE scada_live/scada_ids/gateway_core.py:270-305].
- **Deep Technical Explanation**:
  In scenarios A4 and AM-1 through AM-6, the attacker holds valid credentials (`is_authenticated = 1, is_authorized = 1, role = 'operator'`). Cryptographic firewalls allow the command through.
  `GatewayCore.evaluate_ingress_command()` enforces deterministic physical safety interlocks:
  1. *High-Level Interlock*: If current tank level $H \ge 1.25\text{ m}$, any command ordering `pump_cmd = 1` is immediately rejected.
  2. *Low-Level Interlock*: If current tank level $H \le 0.95\text{ m}$, any command ordering drain valve opening `valve_cmd > 60%` is immediately rejected.
  3. *State Combination Interlock*: Prohibits conflicting actuator combinations (e.g., pump ON with valve 100% open).
  In Monitor mode, these attacks cause 121 overflow ticks and 151 dry-run ticks; in Prevention mode, ingress filtering achieves **100% harm reduction (0.0 overflow/dry ticks)** across all 10 evaluation seeds.
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:270-305]`, `[MEASURED data/full_evaluation_results.csv]`.
- **Potential Pitfall / Gotcha**: Make the distinction clear: *"Identity is managed at the perimeter; safety is enforced at the physics boundary."*

---

### Q20: What is the purpose of the 60-tick hold cap on unauthenticated commands, and why is continuous per-tick safety enforcement necessary for authenticated insiders?
- **Direct Talking Point**: The 60-tick cap limits unauthenticated command influence to safe durations [CODE scada_live/scada_ids/server.py:245-255]. Continuous per-tick enforcement is vital for authenticated insiders because a command that is safe when issued can become catastrophic if held too long [CODE scada_live/scada_ids/gateway_core.py:318-348].
- **Deep Technical Explanation**:
  An unauthenticated REST command is capped at $\min(\text{requested\_hold}, 60\text{ ticks})$ ($60\text{ s}$), ensuring a transient override cannot cause overflow.
  However, an authenticated insider (who can request 1500-tick holds) bypasses the cap. In scenario AM-5, an operator orders pump ON at $H = 1.00\text{ m}$—a completely safe level at $t = 0$. But holding the pump ON for 1500s will cause massive overflow.
  Continuous safety enforcement re-evaluates the active hold on every simulation tick in `/api/sense`. At $t \approx 174\text{ s}$, when tank level crosses $1.25\text{ m}$, the gateway forcibly drops the hold (`holds_dropped += 1`) and reverts control to the autonomous deadband controller, achieving **0 overflow ticks** (vs 211 overflow ticks in Monitor mode).
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:318-348]`, `[MEASURED data/full_evaluation_results.csv]`.
- **Potential Pitfall / Gotcha**: Emphasize that static ingress checks alone cannot protect against long-duration holds; dynamic per-tick monitoring is mandatory.

---

### Q21: Why does the system achieve 0% harm reduction on Fieldbus Wire Tampering (AM-3) in Prevention mode, and is this a system failure?
- **Direct Talking Point**: AM-3 is an **unmitigable physical hardware bridge** downstream of the controller; software commands cannot break an energized copper wire. The IDS performs flawlessly as a detect-only sensor ($\le 3.0\text{ s}$ detection delay), proving architectural honesty [EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:148].
- **Deep Technical Explanation**:
  In AM-3, the adversary physically bridges the electrical contactor powering the pump motor *downstream* of the PLC/gateway [CODE experiments/run_full_evaluation.py:241-245].
  The gateway issues `pump_cmd = 0`, but electricity flows through the physical bypass, forcing the pump ON.
  Because no software command can de-energize a physical copper jumper, the tank overflows for 53 ticks in both Monitor and Prevention modes (0% software harm reduction).
  The 4-way Actuator Consistency Check detects the tampering in $\le 3\text{ ticks}$ ($3.0\text{ s}$) and publishes `wire_tamper_detected` alarms. Mitigating AM-3 requires hardwired emergency breakers or independent physical float switches outside the software domain.
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:362-372]`, `[MEASURED data/full_evaluation_results.csv]`.
- **Potential Pitfall / Gotcha**: Reviewers respect systems that honestly state physical boundaries. Never pretend software can stop an unmitigable physical hardware tap.

---

### Q22: How does the 4-way Actuator Consistency Check detect wire tampering in $\le 3\text{ ticks}$ ($3.0\text{ s}$)?
- **Direct Talking Point**: The check compares the controller's command history against echoed actuator telemetry: if the controller ordered the pump OFF for 3 consecutive ticks, but telemetry reports the pump is ON or flow is entering, wire tampering is immediately flagged [CODE scada_live/scada_ids/gateway_core.py:362-372].
- **Deep Technical Explanation**:
  In `GatewayCore.process_telemetry()`:
  ```python
  wire_tamper = (
      len(self.gateway_pump_history) >= 3
      and self.gateway_pump_history[-1] == 0
      and self.gateway_pump_history[-2] == 0
      and self.gateway_pump_history[-3] == 0
      and (
          pkt.pump_cmd == 1
          or pkt.pump_on is True
          or (pkt.q_in is not None and pkt.q_in > 0.001)
      )
  )
  ```
  The condition requires 3 consecutive ticks of gateway OFF history ($D+1=3$) to avoid false alarms during normal actuator switching delays. Across normal deadband cycling and a 30-minute soak run, the check generated exactly 0 false alarms while detecting AM-3 tampering on the very tick the condition was met.
- **Evidence Citations**: `[CODE scada_live/scada_ids/gateway_core.py:362-372]`, `[CODE scada_live/tests/test_tamper_consistency_check.py:68-93]`.
- **Potential Pitfall / Gotcha**: Explain why $D+1=3$ ticks is required: physical mechanical contactors take 1–2 ticks to settle; checking a single tick would trigger false alarms on normal valve/pump switching.

---

## Category 6: Engineering Realism & Sim-to-Real Gap

### Q23: Why does your implementation use a monolithic gateway architecture rather than separate distributed microservices on ports 5001, 5002, and 5003?
- **Direct Talking Point**: Microservices introduce non-deterministic TCP socket latency, process startup race conditions, and localhost connection overhead on Windows hosts, corrupting precise 1Hz real-time simulation loops [EXISTING-DOC 14_PROJECT_HISTORY_AND_DECISIONS.md#adr-01].
- **Deep Technical Explanation**:
  Porting multi-process REST architectures (`plant` on 5002, `attacker` on 5001, `gateway` on 5003) to local test runners resulted in port binding collisions, orphaned background processes, and timing jitter exceeding $200\text{ ms}$ per tick. During fast benchmarking (`--speed 0.001`), socket exhaustion occurred within seconds.
  Consolidating `LivePlant`, `Injector`, and `GatewayCore` into a synchronous in-process loop within `run_demo.py` guaranteed exact mathematical reproducibility, sub-millisecond execution per tick, and clean single-process lifecycle management while still exposing a full external REST/SSE API on port 5000.
- **Evidence Citations**: `[CODE run_demo.py:340-375]`, `[EXISTING-DOC 14_PROJECT_HISTORY_AND_DECISIONS.md#adr-01]`.
- **Potential Pitfall / Gotcha**: Clarify that the monolithic design is a simulation architecture choice; the software boundaries between `LivePlant` and `GatewayCore` remain strictly modular and decoupled via standard packet dataclasses.

---

### Q24: What are the primary sim-to-real transfer limitations if this IDS were deployed to a physical industrial water treatment facility tomorrow?
- **Direct Talking Point**: Physical deployment faces four sim-to-real gaps: unmodeled pipe hydraulic friction, temperature/fluid viscosity shifts, non-ideal valve stiction/hysteresis, and network packet jitter over fieldbus protocols [EXISTING-DOC 11_KNOWN_LIMITATIONS_AND_FINDINGS.md#4-the-sim-to-real-gap].
- **Deep Technical Explanation**:
  1. *Hydraulic Modeling*: The simulation assumes ideal Torricelli outflow $Q = C_v \sqrt{H}$. Real piping networks exhibit length-dependent head losses, bends, and turbulent friction factors modeled by Darcy-Weisbach equations.
  2. *Actuator Nonlinearities*: The simulation models valves as instantaneous first-order lags. Real industrial pneumatic and motorized valves exhibit deadband, backlash, and stiction that distort flow-pressure curves.
  3. *Sensor Physics*: The simulation uses additive Gaussian white noise. Real 4–20 mA current loops experience 50/60 Hz electromagnetic interference, analog-to-digital converter quantization steps, and temperature-induced zero drift.
  4. *Protocol Integration*: Live simulation communicates over HTTP/JSON REST and SSE streams. Industrial facilities use Modbus TCP, DNP3, Ethernet/IP, or OPC UA, requiring dedicated protocol parsers and hardware security modules (HSMs).
- **Evidence Citations**: `[EXISTING-DOC 11_KNOWN_LIMITATIONS_AND_FINDINGS.md:65-110]`.
- **Potential Pitfall / Gotcha**: An evaluator will appreciate an honest, detailed engineering appraisal of physical deployment requirements rather than hand-waving claims of "production readiness".

---

### Q25: How does your 182-test test suite prove that your reported results are reproducible and code-verified?
- **Direct Talking Point**: The repository contains two automated test suites comprising **182 passing unit and integration tests (0 failures)**: the 66-test batch suite validates mathematical equivalence and ML pipelines, while the 116-test live suite validates streaming protocols, safety rules, and benchmark scenarios [MEASURED docs_v2/_audit/outputs/pytest_batch_output.txt, pytest_live_output.txt].
- **Deep Technical Explanation**:
  Executing the automated test suites:
  1. *Batch Test Suite* (`pytest tests/`): Executes 66 tests in $1.86\text{ s}$, verifying tank mass conservation, Euler step bounds, SQLite schema constraints, LSTM inference, and engine residual functions.
  2. *Live Test Suite* (`pytest scada_live/tests/`): Executes 116 tests in $314.58\text{ s}$, verifying plant physics equivalence against batch simulator, API command validation, 30-minute zero-tamper soak runs, Step 2b DoS gap re-seed rules, and the multi-threat benchmark across all evaluation seeds.
  Together with bit-for-bit SHA-256 baseline hash validation across all 353 repository files, the test suites prove that every claim and metric is mathematically grounded in active code.
- **Evidence Citations**: `[MEASURED pytest_batch_output.txt]`, `[MEASURED pytest_live_output.txt]`, `[CODE docs_v2/09_TESTING_GUIDE.md]`.
- **Potential Pitfall / Gotcha**: Keep the execution commands ready: `pytest tests/` and `pytest scada_live/tests/`.

---

## 7. Oral Defense Quick-Reference Card

| Challenge Topic | Key Metric / Value to State | Code / Data Evidence Citation |
| :--- | :--- | :--- |
| **Total Scenario Population** | Exactly **150 scenarios** (60 normal, 90 attack) in SQLite; 99 in evaluation dataset | `[CODE config/scenarios.py:104-342]`, `[MEASURED data/evaluation_results.csv]` |
| **Event-Level Recall** | **100.0%** across all 90 attack scenarios and 12 live benchmark threats | `[MEASURED data/evaluation_results.csv]`, `[MEASURED reports/full_evaluation_report.md]` |
| **Normal Operational FPR** | **0.00%** on held-out test normals (0/9,000 ticks); **0.0033%** on all 60 normals (2/60,000 ticks) | `[MEASURED data/evaluation_results.csv]`, `[MEASURED experiments/results/check_normals_output.txt]` |
| **Batch Pooled Precision** | **38.9%** pooled (due to 18,062 post-attack generator revert jumps); **96.7%** pre-attack | `[MEASURED data/evaluation_results.csv]`, `[EXISTING-DOC PROJECT_REVIEW_CHEAT_SHEET.md:53-68]` |
| **Physical Harm Reduction** | **100.0% elimination** across all mitigable channels (AM-1, AM-2, AM-5, AM-6, Ramp A/B) | `[MEASURED data/full_evaluation_results.csv]`, `[MEASURED data/auth_misuse_ab_results.csv]` |
| **Unmitigable Channel** | AM-3 Fieldbus Wire Tamper: **0% harm reduction** (53 overflow ticks in both modes); $\le 3\text{t}$ detect | `[MEASURED data/full_evaluation_results.csv]`, `[CODE scada_live/scada_ids/gateway_core.py:362-372]` |
| **Detection Cliff** | Constant bias cliff at **$\approx 3.0\text{ cm}$** ($100\%$ detection in $12.4\text{ s}$); biases $\le 1\text{ cm}$ undetected | `[MEASURED data/bias_sweep_results.csv]` |
| **Soak Stability** | **0 false takeovers** over 60 minutes across all 10 seeds under un-clamped Gaussian noise | `[MEASURED experiments/results/soak_comparison_output.txt]` |
| **Test Suite Coverage** | **182 passed tests, 0 failures** (66 batch tests in $1.86\text{s}$, 116 live tests in $314.58\text{s}$) | `[MEASURED pytest_batch_output.txt]`, `[MEASURED pytest_live_output.txt]` |
