# Experiments & Empirical Evidence Registry

This directory contains reproducible scripts and measured output logs supporting the claims, tables, and metrics in `projectdocs/PROJECT_REVIEW_CHEAT_SHEET.md`, `projectdocs/Phase6a_Implementation_Plan.md`, and `projectdocs/Phase6b_Implementation_Plan.md`.

Every documented number is generated directly by a committed script and recorded in a committed output file in `experiments/results/`. Zero numbers are back-fitted or hand-typed.

---

## 1. Mapping Table: Documented Numbers to Scripts and Output Files

| Documented Metric / Table | Reference Document & Section | Generating Script | Output Artifact | Key Measured Values |
|---|---|---|---|---|
| **Latch & ODE Continuous vs Discrete Integration** | Cheat Sheet §3 (ODE Verification), Phase 6a Plan | [`experiments/compute_latch_all10.py`](file:///c:/projects/p1/New%20folder/experiments/compute_latch_all10.py) | [`experiments/results/compute_latch_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/compute_latch_output.txt) | Seed 101: $h_{latch}=0.9859\text{ m}$, $t_{ODE}=1297.5\text{ s}$, Pred=1974.5, Obs=1975, Diff=+0.5s. All 10 seeds evaluated with `scipy.integrate.quad`. For $h=0.9788\text{ m}$, $t_{ODE}=1302.2\text{ s}$ (not 1374.5). Discrepancies span -0.22s to +0.74s for overflow, -0.73s to +0.04s for dry-run. |
| **A/B Comparison Per-Seed Detailed Table (80 runs)** | Cheat Sheet §3, Phase 6a Plan §6 Step 3 | [`experiments/print_ab_per_seed.py`](file:///c:/projects/p1/New%20folder/experiments/print_ab_per_seed.py) (from [`experiments/run_comparison.py`](file:///c:/projects/p1/New%20folder/experiments/run_comparison.py)) | [`experiments/results/ab_per_seed_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/ab_per_seed_output.txt), [`experiments/results/ab_comparison_results.csv`](file:///c:/projects/p1/New%20folder/experiments/results/ab_comparison_results.csv) | Full 80-run table: Control_FDI, Negative_Ramp, Positive_Ramp, Stealthy_Ramp. Negative_Ramp monitor mean overflow ticks: exactly 642.9 ± 178.0 (sum = 6429 / 10). Prevention overflow: 0.0 ± 0.0. Positive_Ramp monitor dry-run: 275.3 ± 96.0; Prevention dry-run: 0.0 ± 0.0. Start schedule deterministically [551, 456, 463, 269, 392, 566, 262, 299, 462, 328]. Mean flag delay: 23.2s. |
| **A/B Summary Table (Mean ± Std)** | Cheat Sheet §3, Phase 6a Plan §6 Step 3 | [`experiments/run_comparison.py`](file:///c:/projects/p1/New%20folder/experiments/run_comparison.py) | [`experiments/results/ab_comparison_summary.txt`](file:///c:/projects/p1/New%20folder/experiments/results/ab_comparison_summary.txt) | 4 scenarios x 2 modes x 10 seeds: Peak/min levels, overflow ticks, dry-run ticks, time < 0.3m, takeover ticks. Prevention mode: 0 overflows, 0 dry-runs across all seeds. |
| **Hand-Back Verification (`Ramp_Hold_Return`)** | Cheat Sheet §3, Phase 6a Plan §6 Step 3 | [`experiments/run_handback_check.py`](file:///c:/projects/p1/New%20folder/experiments/run_handback_check.py) (from [`experiments/run_comparison.py`](file:///c:/projects/p1/New%20folder/experiments/run_comparison.py)) | [`experiments/results/handback_verification_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/handback_verification_output.txt) | 10 seeds: Mean hand-back tick $t = 1194.3 \pm 1.1\text{ s}$ once sensor bias returns to 0; mean stabilized level $h = 1.1044\text{ m}$; exactly 2 post-handback false alarm ticks across 10 seeds (0.2/seed over 1200s). Confirmed via clean re-run saved to file. |
| **Stealthy Ramp Multi-Slope Sweep** | Cheat Sheet §3, Phase 6a Plan §6 Step 3 | [`experiments/run_comparison.py`](file:///c:/projects/p1/New%20folder/experiments/run_comparison.py) (lines 394–445) | [`experiments/results/run_comparison_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/run_comparison_output.txt) (lines 150–165) | 10 seeds per slope (40 runs): 0.01 mm/s (1523.1s, mean bias 1.52 cm, ratio 0.435, min 0.160, max 0.769); 0.02 mm/s (929.7s, 1.86 cm, ratio 0.531); 0.05 mm/s (476.6s, 2.38 cm, ratio 0.681); 0.10 mm/s (256.0s, 2.56 cm, ratio 0.731). Empirically demonstrates sensor noise ($3\sigma=1.5\text{ cm}$) constructive addition. No universal "< 3.5 cm" claim. |
| **Constant-Bias Detection Sweep** | Cheat Sheet §3, Phase 6a Plan §6 Step 3 | [`experiments/run_constant_bias_sweep.py`](file:///c:/projects/p1/New%20folder/experiments/run_constant_bias_sweep.py) | [`experiments/results/constant_bias_sweep_results.csv`](file:///c:/projects/p1/New%20folder/experiments/results/constant_bias_sweep_results.csv), [`experiments/results/constant_bias_sweep_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/constant_bias_sweep_output.txt) | Biases 0, 1, 2, 3, 4, 5 cm (10 seeds, 1200s, unclamped noise): 0 cm: 0.017% FA (2/12000 ticks), 0 false takeovers; 1 cm: 0% detections; 2 cm: physics flags every seed at 2 cm (mean 200 s) but CRITICAL only 10% (mean time 1193.0s); 3 cm: 100% detection probability (mean time 12.4s); 4 cm: 100% (2.1s); 5 cm: 100% (2.0s). Effective empirical threshold $\approx 3\text{ cm}$. |
| **Parameter Mismatch & Drift Sensitivity** | Cheat Sheet §3, Phase 6a Plan | [`experiments/run_mismatch_sensitivity.py`](file:///c:/projects/p1/New%20folder/experiments/run_mismatch_sensitivity.py) | [`experiments/results/mismatch_sensitivity_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/mismatch_sensitivity_output.txt), [`experiments/results/mismatch_sensitivity_results.csv`](file:///c:/projects/p1/New%20folder/experiments/results/mismatch_sensitivity_results.csv) | 160 simulation runs: 8 mismatch cases x 2 scenarios x 10 seeds over $T=2400\text{ s}$. Safety envelope $[0.3, 2.5\text{ m}]$ NEVER left (0/160 runs). Confirms twin integrates measured flows: plant pump $+5\%$ and valve $C_v +10\%$ variations cause negligible excursion ($< 1.04\text{ cm}$), proving $C_v$ errors cannot affect twin mass balance. Area $\pm 5\%$: excursion $\le 2.15\text{ cm}$; flow bias $\pm 5\%$: excursion $\le 12.15\text{ cm}$; leak $+2\%$: excursion $\le 5.04\text{ cm}$. |
| **No-Attack Prevention Soak (Clamped vs Unclamped)** | Cheat Sheet §3, §4 | [`experiments/run_soak_comparison.py`](file:///c:/projects/p1/New%20folder/experiments/run_soak_comparison.py) | [`experiments/results/soak_comparison_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/soak_comparison_output.txt), [`experiments/results/soak_comparison_results.csv`](file:///c:/projects/p1/New%20folder/experiments/results/soak_comparison_results.csv) | 10 seeds: 30-min clamped noise yields 0.5 ± 1.6 false takeover ticks (5 ticks total across seeds, earliest t=1545s); 30-min unclamped yields exactly 0.0 ± 0.0 false takeover ticks. 60-min clamped yields 1073.9 ± 338.3 false takeover ticks (10/10 seeds); 60-min unclamped yields exactly 0.0 ± 0.0 false takeover ticks (0/10 seeds). |
| **Clamped Soak Tick 0 Baseline Drift** | Cheat Sheet §3 | [`experiments/run_soak_tick0.py`](file:///c:/projects/p1/New%20folder/experiments/run_soak_tick0.py) | [`experiments/results/run_soak_tick0.txt`](file:///c:/projects/p1/New%20folder/experiments/results/run_soak_tick0.txt) | 30-min run counting flags from tick 0: Exactly 12 physics flags occur between $t=861$ and $t=1790$ due to integrated clamped flow noise. Zero flags before $t=861$. |
| **A3 DoS False Positive Reconciliation** | Cheat Sheet §3 (Artifacts) | [`experiments/reconcile_a3_fp.py`](file:///c:/projects/p1/New%20folder/experiments/reconcile_a3_fp.py) | [`experiments/results/reconcile_a3_fp.txt`](file:///c:/projects/p1/New%20folder/experiments/results/reconcile_a3_fp.txt) | Streaming replay with noisy sensor init at $t=0$: 7,541 ticks. Batch evaluation with deterministic nominal level $H_0=1.0\text{ m}$: 7,561 ticks. Difference: exactly 20 ticks (+25 in A3_001, +56 in A3_002, -57 in A3_012, -4 in A3_015). When StreamingIDS initializes with exact nominal level, streaming replay matches batch evaluation tick-for-tick across all 15 scenarios (exactly 7,561 ticks). |
| **A3 Mechanism Per-Scenario Verification** | Cheat Sheet §3 (Artifacts) | [`experiments/compute_a3_mechanism_detailed.py`](file:///c:/projects/p1/New%20folder/experiments/compute_a3_mechanism_detailed.py) | [`experiments/results/compute_a3_mechanism_detailed.txt`](file:///c:/projects/p1/New%20folder/experiments/results/compute_a3_mechanism_detailed.txt) | All 15 A3 scenarios: duration 21 to 121s, net fill rate $\approx 0.0014\text{ m/s}$, predicted level offset 0.031 to 0.171 m, observed level jump at restoration (A3_010: 1.022 to 1.189 in 1 tick; A3_001 converges in 5 ticks). Total $S_p > 0.95$ ticks = exactly 7,561. |
| **Step 2b DoS Gap Re-Seed Rule** | Cheat Sheet §3, Phase 6a Plan §6 Step 2b | [`experiments/check_a3_gap.py`](file:///c:/projects/p1/New%20folder/experiments/check_a3_gap.py) | [`experiments/results/check_a3_gap.txt`](file:///c:/projects/p1/New%20folder/experiments/results/check_a3_gap.txt) | All 15 A3 scenarios evaluated with real twin state: $v_{max} = \max(0.0025, 0.00316) = 0.003162\text{ m/s}$, $\sigma_{sensor} = 0.005\text{ m}$, $\text{max\_std\_m} = 0.030\text{ m}$. Gap $G = 21$ to $121$, median $m = 1.048$ to $1.189$, $|m - h_{twin}| = 0.020$ to $0.169\text{ m}$, band $= 0.081$ to $0.398\text{ m}$. All 15 scenarios satisfy physical rate band and RE-SEED. |
| **Stored Normals Batch Residual Statistics** | Cheat Sheet §3 (Threshold Selection) | [`experiments/recompute_all60_residuals.py`](file:///c:/projects/p1/New%20folder/experiments/recompute_all60_residuals.py) | [`experiments/results/recompute_all60_residuals.txt`](file:///c:/projects/p1/New%20folder/experiments/results/recompute_all60_residuals.txt) | All 60 stored normals in DB (60,000 ticks): Max absolute residual = 0.034884 m vs $\tau_p = 0.035\text{ m}$ (0.3% margin), p99 = 0.020286 m, 0 ticks > $\tau_p$. 9 held-out normals (9,000 ticks): Max = 0.028822 m, p99 = 0.021046 m, 0 ticks > $\tau_p$. 51 train/val normals (51,000 ticks): Max = 0.034884 m, p99 = 0.020045 m, 0 ticks > $\tau_p$. |
| **Fresh Telemetry Latency Across 90 Attacks** | Cheat Sheet §3 (Attribution) | [`experiments/compute_fresh_latency.py`](file:///c:/projects/p1/New%20folder/experiments/compute_fresh_latency.py) | [`experiments/results/compute_fresh_latency.txt`](file:///c:/projects/p1/New%20folder/experiments/results/compute_fresh_latency.txt) | Evaluates all 90 attacks in DB: Pre-attack alarm in 10 ticks before $t_{start}$ is 0/90. Fresh detection delay: Mean = 0.00s, Median = 0.00s, Max = 0.00s. Physics flags 45/45 FDI and 15/15 Replay at $t_{start}$. LSTM flags 15/15 DoS and 15/15 Auth Misuse at $t_{start}$. |
| **2x2 Grid: LSTM Sensitivity to Pump Alignment** | Cheat Sheet §3, §4 | [`experiments/run_2x2_grid.py`](file:///c:/projects/p1/New%20folder/experiments/run_2x2_grid.py) | [`experiments/results/run_2x2_grid.txt`](file:///c:/projects/p1/New%20folder/experiments/results/run_2x2_grid.txt) | Transient window $t=200..230$: Physical state + Clamped noise: Max LSTM = 0.6688, 0 flags > 0.95. Physical state + Unclamped: Max LSTM = 0.6456, 0 flags. Forced command + Clamped: Max LSTM = 1.0000, 10 flags. Forced command + Unclamped: Max LSTM = 1.0000, 10 flags. |
| **Loop Alignment Verification** | Cheat Sheet §3 | [`experiments/test_aligned_loop.py`](file:///c:/projects/p1/New%20folder/experiments/test_aligned_loop.py) | [`experiments/results/test_aligned_loop.txt`](file:///c:/projects/p1/New%20folder/experiments/results/test_aligned_loop.txt) | Detailed tick-by-tick log ($t=200..225$) demonstrating maximum LSTM score occurs at $t=212$ with value 0.6688, comfortably below 0.95. |
| **Tick 0 Initialization Baseline** | Cheat Sheet §4 | [`experiments/inspect_tick0_baseline.py`](file:///c:/projects/p1/New%20folder/experiments/inspect_tick0_baseline.py) | [`experiments/results/inspect_tick0_baseline.txt`](file:///c:/projects/p1/New%20folder/experiments/results/inspect_tick0_baseline.txt) | First 400 ticks of live operation: Zero false alarms across all engines (Max score < 0.95). Demonstrates deterministic initialization eliminates start-up bias. |
| **Evaluation Dataset Metrics** | Cheat Sheet §3 | [`experiments/compute_metrics.py`](file:///c:/projects/p1/New%20folder/experiments/compute_metrics.py) | [`experiments/results/compute_metrics_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/compute_metrics_output.txt) | Evaluates `data/evaluation_results.csv` (99,000 rows): Pooled Precision = 38.9%, Recall = 99.8%, F1 = 56.0%, FPR = 21.2%. Generous view (excluding post-attack artifacts): Precision = 96.7%, Recall = 99.8%, F1 = 98.2%, FPR = 1.08% (406 FPs out of 37,550 negative ticks). Held-out Normal FPR = 0.000 (0 / 9,000 ticks across 9 held-out scenarios). |
| **Normal Scenarios StreamingIDS Evaluation (60 Normals)** | Cheat Sheet §3 | [`experiments/check_normals.py`](file:///c:/projects/p1/New%20folder/experiments/check_normals.py) | [`experiments/results/check_normals_output.txt`](file:///c:/projects/p1/New%20folder/experiments/results/check_normals_output.txt) | Evaluates all 60 normal scenarios in DB (60,000 ticks; includes 51 training/validation normals): 2 FPs out of 60,000 ticks (FPR = 0.000033). Confirms 0 FPs across the 9 held-out normal scenarios (max LSTM score 0.936, margin 0.014). |
| **Gateway Safety Rule Offline DB Evaluation** | Phase 6b Plan §4 | [`experiments/validate_gateway_rule.py`](file:///c:/projects/p1/New%20folder/experiments/validate_gateway_rule.py) | [`experiments/results/gateway_rule_validation.txt`](file:///c:/projects/p1/New%20folder/experiments/results/gateway_rule_validation.txt) | Evaluates `evaluate_command_with_live_setpoint` on `data/scada_ids.db`: Normals (60,000 ticks): 0 violations (0 FPR, minimum margin 0.0500m to threshold); A1 FDI (45,000 ticks): 1818 inside GT (REGRESSION PIN, post-hoc overlay artifact), 0 outside GT; A2 Replay (15,000 ticks): 0 inside, 0 outside; A3 DoS (15,000 ticks): 0 inside, 0 outside; A4 Auth Misuse (15,000 ticks): 1515 inside GT (100% detection, 101 per scenario), 0 outside GT. |
| **Synthetic Scenario Unit Tests (AM-1 to AM-6)** | Phase 6b Plan §3, §4 | [`scada_live/tests/test_gateway_safety_rule.py`](file:///c:/projects/p1/New%20folder/scada_live/tests/test_gateway_safety_rule.py) | Pytest test suite output | 8 unit tests validating `evaluate_command_with_live_setpoint` against Controller attributes and testing AM-1, AM-2, AM-3, AM-4, AM-5, AM-6 pass/block specifications. |

---

## 2. Reproduction Instructions

To reproduce any output artifact:
```bash
# Latch / ODE table
python experiments/compute_latch_all10.py > experiments/results/compute_latch_output.txt

# Full A/B comparison per-seed table
python experiments/print_ab_per_seed.py > experiments/results/ab_per_seed_output.txt

# Extended A/B comparison and hand-back verification
python experiments/run_comparison.py > experiments/results/run_comparison_output.txt

# Constant-bias sweep
python experiments/run_constant_bias_sweep.py > experiments/results/constant_bias_sweep_output.txt

# Parameter mismatch sensitivity study
python experiments/run_mismatch_sensitivity.py > experiments/results/mismatch_sensitivity_output.txt

# Soak comparison (clamped vs unclamped)
python experiments/run_soak_comparison.py > experiments/results/soak_comparison_output.txt

# A3 DoS false-positive reconciliation
python experiments/reconcile_a3_fp.py > experiments/results/reconcile_a3_fp.txt

# A3 mechanism detailed analysis
python experiments/compute_a3_mechanism_detailed.py > experiments/results/compute_a3_mechanism_detailed.txt

# Step 2b DoS gap rule evaluation
python experiments/check_a3_gap.py > experiments/results/check_a3_gap.txt

# Stored normal residual recomputation
python experiments/recompute_all60_residuals.py > experiments/results/recompute_all60_residuals.txt

# Metrics computation
python experiments/compute_metrics.py > experiments/results/compute_metrics_output.txt

# Normal scenarios StreamingIDS evaluation (60 normals)
python experiments/check_normals.py > experiments/results/check_normals_output.txt

# Hand-back verification (Ramp_Hold_Return)
python experiments/run_handback_check.py > experiments/results/handback_verification_output.txt

# Gateway safety rule offline evaluation
python experiments/validate_gateway_rule.py > experiments/results/gateway_rule_validation.txt
```
