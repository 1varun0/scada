# Table T10: Authorization Misuse & Prevention A/B Verification Matrix (AM-1 - AM-7)

> Source: `experiments/run_auth_misuse_ab.py` executed in isolated sandbox copy across 10 evaluation seeds (101 to 110).
> Compares physical harm in **Monitor Mode** vs active mitigation in **Prevention Mode**.
> Raw data: [`auth_misuse_ab_results.csv`](../raw/auth_misuse_ab_results.csv), runner log [`e3_auth_misuse_ab.log`](../raw/e3_auth_misuse_ab.log).

## Multi-Threat A/B Harm Comparison Table

| Scenario | Attack Description | Monitor Mode Harm | Prevention Mode Harm | Status | Empirical Verification Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `AM-1` | Overflow Misuse (Pump Latched ON at 1.30m) | `Ov: 121.0t | Dry: 0.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Mon ov=121.0t (>=9/10 seeds), Prev ov=0.0t (100% blocked) |
| `AM-2` | Dry-Run Misuse (Valve Latched 90% at 0.90m) | `Ov: 0.0t | Dry: 151.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Mon dry=151.0t (>=9/10 seeds), Prev dry=0.0t (100% blocked) |
| `AM-3` | Wire / Fieldbus Tamper (Detect-Only Override) | `Ov: 58.0t | Dry: 0.0t` | `Ov: 58.0t | Dry: 0.0t` | ✅ PASSED | Detect delay=0.0t (<=3t), Harm identical: Mon=58.0t, Prev=58.0t |
| `AM-4` | In-Deadband Pump Toggle (Nominal 1.0m) | `Ov: 0.0t | Dry: 0.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Quiescent in deadband (0 ov, 0 dry); empirical ML scores recorded |
| `AM-5` | In-Band Hold - Filling (Pump ON, Hold 1500s) | `Ov: 211.0t | Dry: 0.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Mon ov=211.0t (>=9/10 seeds), Prev ov=0.0t (100% dropped) |
| `AM-6` | In-Band Hold - Draining (Pump OFF, Hold 1800s) | `Ov: 0.0t | Dry: 1.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Mon dry=1.0t (>=9/10 seeds), Prev dry=0.0t (100% dropped) |
| `AM-7` | Unauthenticated Hold Cap (Requested 1500s -> 60s) | `Ov: 0.0t | Dry: 0.0t` | `Ov: 0.0t | Dry: 0.0t` | ✅ PASSED | Hold capped to 60 ticks; 0 overflow ticks in all runs |

## Summary Findings & Protection Invariants

- **AM-1 (Overflow Misuse)**: Latched pump command at 1.30m causes an average of **121.0 overflow ticks** in Monitor mode; Prevention mode achieves **0.0 overflow ticks (100% blocked at ingress)**.
- **AM-2 (Dry-Run Misuse)**: Latched valve 90% at 0.90m causes **151.0 dry-run ticks** in Monitor mode; Prevention mode achieves **0.0 dry-run ticks (100% blocked at ingress)**.
- **AM-3 (Wire / Fieldbus Tamper)**: Actuator hijacked after gateway; detection occurs in **0.0 ticks**; physical harm is identical (**58.0 ticks** in both modes) confirming the theoretical invariant that ingress filtering cannot prevent physical down-wire tampering.
- **AM-4 (In-Deadband Pump Toggle)**: Harmless manipulation inside controller hysteresis deadband ($0.8\text{ m} \le H \le 1.2\text{ m}$) causes **0 physical harm** in both modes.
- **AM-5 (In-Band Hold - Filling)**: Long hold (1500s) causes **211.0 overflow ticks** in Monitor mode; Prevention mode continuous enforcement drops the hold upon upper limit crossing, ensuring **0.0 overflow ticks**.
- **AM-6 (In-Band Hold - Draining)**: Long hold (1800s) causes **1.0 dry-run tick** in Monitor mode; Prevention mode drops hold upon lower limit crossing, ensuring **0.0 dry-run ticks**.
- **AM-7 (Unauthenticated Hold Cap)**: Capping unauthenticated hold duration from 1500s to 60s eliminates overflow risk, yielding **0.0 overflow ticks** in all seeds.

**Overall Verification Outcome**: **100% PASS across all 10 evaluation seeds**.
