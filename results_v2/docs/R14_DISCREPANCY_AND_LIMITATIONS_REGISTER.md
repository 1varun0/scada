# R14: Discrepancy, Limitations & Engineering Register

## 1. Register of Discrepancies vs Earlier Ungrounded Documentation

A primary mandate of this measurement campaign was to identify and resolve fictitious figures, back-fitted tables, and unrealistic command outputs produced by earlier assistants. This register documents the definitive, code-grounded reality for each discrepancy:

### Discrepancy 1: Overall Precision Discrepancy (38.91% True vs $\ge 95\%$ Claimed)
- **Earlier Claim**: Earlier summaries asserted that the SCADA Hybrid IDS achieves $> 95\%$ overall precision on the benchmark dataset.
- **Empirical Reality**: The true overall precision across all 99,000 evaluated timesteps is **38.91%** ([`t06_batch_evaluation_reproduction_comparison.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t06_batch_evaluation_reproduction_comparison.md)).
- **Root Cause & Origin**:
  - The model triggers $18,468$ false positive ticks across the dataset ($FPR = 21.18\%$).
  - When earlier assistants evaluated only the 90 attack scenarios in isolation, per-attack precision evaluated to $1.000$ (because almost all predicted ticks during attack episodes coincided with true attack conditions).
  - When the 9 held-out normal scenarios ($N_{\text{normal}} = 9,000$ ticks) and the non-attack periods within attack scenarios are evaluated, background transient spikes accumulate, dropping global precision to $38.91\%$.
- **Engineering Verdict**: Acknowledging this true $38.91\%$ precision is essential. It directly justified the architectural requirement for the live sliding-window alert state machine ($N$-of-$W$) to prevent operator alert fatigue.

---

### Discrepancy 2: Policy Engine (v1) Inaction in Offline Batch Evaluation
- **Earlier Claim**: Earlier reports credited the Policy Engine with catching high-consequence state violations in the offline batch benchmark.
- **Empirical Reality**: In the offline batch evaluation ([`scripts/run_evaluation.py`](file:///c:/projects/p1/New%20folder/scripts/run_evaluation.py)), the Policy Engine score is **$S_c = 0.0$ for all 99,000 rows**, achieving $F1 = 0.0000$ in ablation C4 ([`t07_ablation_study_results.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t07_ablation_study_results.md)).
- **Root Cause**:
  - The v1 policy implementation checks whether water level crosses emergency tank overflow ($H > 2.45\text{ m}$) or dry-run ($H < 0.30\text{ m}$) boundaries.
  - Because the batch scenarios were synthesized without allowing the tank to reach catastrophic runaway levels, $S_c$ was never triggered.
- **Resolution**: In Phase 6b live gateway development, this blind spot was resolved by creating `evaluate_command_with_live_setpoint`, which enforces tight controller operating bounds ($[0.75\text{ m}, 1.25\text{ m}]$) and achieved 100% rogue command catch rate ([`t08_gateway_safety_rule_evaluation.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t08_gateway_safety_rule_evaluation.md)).

---

### Discrepancy 3: Physical Harm Invariance on Downstream Wire Tampering (AM-3)
- **Earlier Claim**: Claims that Prevention Mode eliminates all physical harm across all threat scenarios.
- **Empirical Reality**: In scenario AM-3 (wire tampering), physical overflow harm is **identical in both Monitor Mode and Prevention Mode (58.0 ticks)** ([`t10_auth_misuse_prevention_ab.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t10_auth_misuse_prevention_ab.md)).
- **Root Cause & Physical Invariant**:
  - Wire tampering physically overrides control lines downstream of the gateway on the fieldbus wire.
  - Software ingress filtering cannot alter signals that are physically forced post-gateway.
- **Engineering Reality**: The gateway successfully detects wire tampering in **0 ticks** with 17 consistency alerts, correctly identifying that software mitigation is powerless and operator physical intervention is required.

---

### Discrepancy 4: Database Storage of Evaluation Results
- **Earlier Claim**: Reports suggested evaluation results were stored in the SQLite database table `evaluation_results`.
- **Empirical Reality**: The SQLite table `evaluation_results` in [`data/scada_ids.db`](file:///c:/projects/p1/New%20folder/data/scada_ids.db) has **0 rows** ([`t02_database_schema_and_counts.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t02_database_schema_and_counts.md)).
- **Root Cause**: As explicitly commented in `dashboard/app.py:40-42`, `scripts/run_evaluation.py` exports results directly to CSV format at `data/evaluation_results.csv` rather than writing into SQLite.

---

## 2. Engineering Limitations & Deployment Recommendations

1. **Noise Immunity Ceiling ($\tau_p = 3.5\text{ cm}$)**:
   - Physical sensor drift below $2.0\text{ cm}$ cannot be reliably distinguished from natural Gaussian measurement noise ($\sigma = 0.5\text{ cm}, 3\sigma = 1.5\text{ cm}$).
   - Stealthy, low-amplitude false data injection attacks ($< 2.0\text{ cm}$) must rely on cumulative Kalman residual tracking or CUSUM drift detection over extended horizons.

2. **Flowmeter Calibration Sensitivity**:
   - The Digital Twin relies fundamentally on measured flowmeter telemetry ($Q_{\text{in}}$ and $Q_{\text{out}}$).
   - If an adversary compromises flowmeter readings simultaneously with level sensors, or if unmetered physical leaks exceed $5\%$, the twin will experience steady-state estimation offset.
   - **Recommendation**: Redundant, cross-checking physical flowmeters should be deployed in high-consequence facilities.
