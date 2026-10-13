# Source File Note: experiments/ Registry & Empirical Evidence

## 1. Purpose
Documents the empirical benchmark scripts, A/B comparison tests, parameter sweeps, and validation experiments stored under `experiments/` [CODE experiments/README.md:1-83].

## 2. Key Scripts & Generated Output Artifacts
- `experiments/run_full_evaluation.py` [CODE experiments/run_full_evaluation.py:1-9]:
  - Consolidated 10-repetition multi-threat benchmark evaluating all 12 operational and attack scenarios across 10 random seeds (201-210) in both Monitor and Prevention modes (240 total simulation runs).
  - Committed results: `data/full_evaluation_results.csv` and `reports/full_evaluation_report.md`.
- `experiments/compute_latch_all10.py` [CODE experiments/README.md:13]:
  - Evaluates continuous ODE drain and overflow times via `scipy.integrate.quad` vs discrete simulation ticks across 10 seeds. Output: `experiments/results/compute_latch_output.txt`.
- `experiments/print_ab_per_seed.py` / `experiments/run_comparison.py` [CODE experiments/README.md:14-15]:
  - 80 simulation runs comparing Monitor vs Prevention modes across 10 seeds for Control_FDI, Negative_Ramp, Positive_Ramp, and Stealthy_Ramp. Outputs: `experiments/results/ab_per_seed_output.txt`, `experiments/results/ab_comparison_results.csv`, `experiments/results/ab_comparison_summary.txt`.
  - Negative_Ramp monitor mean overflow ticks: $642.9 \pm 178.0\text{ ticks}$; Prevention overflow: $0.0 \pm 0.0\text{ ticks}$.
  - Positive_Ramp monitor dry-run: $275.3 \pm 96.0\text{ ticks}$; Prevention dry-run: $0.0 \pm 0.0\text{ ticks}$.
- `experiments/run_constant_bias_sweep.py` [CODE experiments/README.md:18]:
  - Constant bias sweep from 0 to 5 cm across 10 seeds. Empirical threshold $\approx 3\text{ cm}$ (100% detection probability in 12.4s). Output: `experiments/results/constant_bias_sweep_results.csv`.
- `experiments/run_mismatch_sensitivity.py` [CODE experiments/README.md:19]:
  - 160 simulation runs (8 mismatch cases $\times$ 2 scenarios $\times$ 10 seeds over $T=2400\text{s}$). Safety envelope $[0.3, 2.5\text{m}]$ never breached. Confirms digital twin integrates measured flows rather than simulating valves from first principles. Output: `experiments/results/mismatch_sensitivity_results.csv`.
- `experiments/run_soak_comparison.py` & `run_soak_tick0.py` [CODE experiments/README.md:20-21]:
  - Evaluates clamped vs unclamped noise drift over 30 and 60 minutes. Clamped noise drifts past $\tau_p = 0.035\text{m}$ after ~860 ticks (first flag at $t=861\text{s}$) due to asymmetric bias $E[\max(0, Q + \mathcal{N}(0, \sigma_Q^2))] > 0$. Unclamped noise produces 0 false takeover ticks over 60 minutes. Outputs: `experiments/results/soak_comparison_results.csv`, `experiments/results/run_soak_tick0.txt`.
- `experiments/reconcile_a3_fp.py` & `compute_a3_mechanism_detailed.py` [CODE experiments/README.md:22-23]:
  - Reconciles 7,561 post-attack residual false positive ticks in A3 DoS batch evaluation. Output: `experiments/results/reconcile_a3_fp.txt`.
- `experiments/check_a3_gap.py` [CODE experiments/README.md:24]:
  - Validates Step 2b DoS gap re-seed rule across all 15 A3 scenarios. Output: `experiments/results/check_a3_gap.txt`.
- `experiments/recompute_all60_residuals.py` [CODE experiments/README.md:25]:
  - Recomputes physics residual distribution across all 60 stored normal scenarios (60,000 ticks). Max absolute residual is $0.034884\text{ m}$ vs $\tau_p = 0.035\text{ m}$ (0.3% margin). 0 ticks exceed $\tau_p$. Output: `experiments/results/recompute_all60_residuals.txt`.
- `experiments/compute_metrics.py` [CODE experiments/README.md:30]:
  - Evaluates `data/evaluation_results.csv` (99,000 rows): Pooled Precision = 38.9%, Recall = 99.8%, F1 = 56.0%, FPR = 21.2%. Generous view (excluding post-attack artifacts): Precision = 96.7%, Recall = 99.8%, F1 = 98.2%, FPR = 1.08%. Output: `experiments/results/compute_metrics_output.txt`.
- `experiments/validate_gateway_rule.py` [CODE experiments/README.md:32]:
  - Evaluates gateway safety command rule against entire `data/scada_ids.db` database. 60 normal scenarios have 0 false violations. 15 A4 Auth Misuse scenarios have 1,515 detections inside ground truth (101/scenario, 100% TPR) and 0 false positives outside. Output: `experiments/results/gateway_rule_validation.txt`.
