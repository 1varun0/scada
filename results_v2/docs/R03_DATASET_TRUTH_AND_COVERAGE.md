# R03: Dataset Truth & Coverage Specification

## 1. Database Architecture & Schema Specification

The dataset is stored in SQLite format at [`data/scada_ids.db`](file:///c:/projects/p1/New%20folder/data/scada_ids.db) and queried via Python `sqlite3` in read-only mode (`mode=ro`). The schema structure and record counts are tabulated in [`t02_database_schema_and_counts.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t02_database_schema_and_counts.md):

| Table Name | Primary Purpose | Record Count | Columns | Primary Key |
| :--- | :--- | :---: | :---: | :--- |
| `scada_telemetry` | Per-tick physical sensor readings and control commands | **150,000** | 25 | `scenario_id, sequence_id` |
| `attack_scenarios` | Ground-truth metadata and injection parameter specs | **90** | 11 | `attack_id` |
| `experiment_runs` | Training configuration tracking (table empty in DB) | **0** | 12 | `experiment_id` |
| `evaluation_results` | Pre-computed benchmark outputs (stored in CSV, table empty in DB) | **0** | 14 | `experiment_id, scenario_id, sequence_id` |

> **Architecture Note**: Offline evaluation results and metrics are preserved in CSV format ([`data/evaluation_results.csv`](file:///c:/projects/p1/New%20folder/data/evaluation_results.csv)), leaving the SQLite table `evaluation_results` at 0 records. This design pattern is documented in `dashboard/app.py:40-42`.

---

## 2. Ingress Regularity & Ground Truth Distribution

Analysis of all 150,000 rows in `scada_telemetry` reveals absolute temporal and structural consistency ([`t03_attack_scenarios_breakdown.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t03_attack_scenarios_breakdown.md)):
- **Total Scenarios**: Exactly 150 scenarios (60 Normal scenarios `N_001`–`N_060`, 90 Attack scenarios `A1_001`–`A4_015`).
- **Ticks per Scenario**: Exactly **1,000 ticks** per scenario (`sequence_id` spans 0 to 999).
- **Time Ingress**: `simulation_time_s` spans from $0.0\text{ s}$ to $999.0\text{ s}$ with uniform $\Delta t = 1.0\text{ s}$.
- **Ground Truth Distribution**:
  - **Normal Ticks (`ground_truth == 0`)**: **138,215 ticks** (92.14% of dataset).
  - **Attack Ticks (`ground_truth == 1`)**: **11,785 ticks** (7.86% of dataset).
- **Dropped Packets**: Exactly **1,035 ticks** have `packet_received == 0`. Every single dropped packet corresponds strictly to ground-truth DoS ($A_3$) attack intervals.
- **Telemetry Age**: `data_age_ms` has a baseline value of 0 ms, mean of 482.17 ms, and reaches a maximum ceiling of 200,000 ms during prolonged DoS outages.

---

## 3. Threat Distribution Breakdown

Audited from the `attack_scenarios` metadata table across all 90 attack instances ([`t03_attack_scenarios_breakdown.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t03_attack_scenarios_breakdown.md)):

| Threat Class | Scenario Prefix | Count | Operating Condition | Injection Start Window | Injection End Window | Mean Attack Duration | Initial Level ($H_0$) |
| :--- | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **False Data Injection (FDI)** | `A1_*` | 45 | `Steady_State` | $t = 300\text{ s}$ | $t = 500\text{ s}$ | **200.0 s** | 1.00 m |
| **Replay Attack** | `A2_*` | 15 | `Steady_State` | $t = 400\text{ s}$ | $t \in [430, 500]\text{ s}$ | **65.0 s** | 1.00 m |
| **Denial of Service (DoS)** | `A3_*` | 15 | `Steady_State` | $t = 350\text{ s}$ | $t \in [370, 470]\text{ s}$ | **68.0 s** | 1.00 m |
| **Authorization Misuse** | `A4_*` | 15 | `Misuse_Condition` | $t = 200\text{ s}$ | $t = 300\text{ s}$ | **100.0 s** | $0.40 - 2.10\text{ m}$ |
| **Total Attack Scenarios** | - | **90** | - | - | - | - | - |

---

## 4. Partition Integrity & Zero-Leakage Audit

The partition manifest defined in [`checkpoints/data_split_v1.json`](file:///c:/projects/p1/New%20folder/checkpoints/data_split_v1.json) was cross-referenced with the offline evaluation set ([`t04_dataset_split_and_coverage.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t04_dataset_split_and_coverage.md)):

| Partition | Scenarios Contained | Records | Fraction | In `evaluation_results.csv`? | Leakage Audit |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Training (Normal)** | 42 scenarios (`N_041`, `N_005`, ..., `N_039`) | 42,000 | 28.0% | ❌ No | **0 / 42 scenarios in evaluation (Clean)** |
| **Validation (Normal)** | 9 scenarios (`N_058`, `N_047`, ..., `N_007`) | 9,000 | 6.0% | ❌ No | **0 / 9 scenarios in evaluation (Clean)** |
| **Test (Normal)** | 9 scenarios (`N_001`, `N_006`, ..., `N_013`) | 9,000 | 6.0% | ✅ Yes | **9 / 9 scenarios evaluated** |
| **Test (Attacks)** | 90 scenarios (`A1_001` through `A4_015`) | 90,000 | 60.0% | ✅ Yes | **90 / 90 scenarios evaluated** |
| **Total Test Split** | **99 Scenarios** | **99,000** | **66.0%** | **✅ Yes** | **100% Exact Partition Match** |
| **Full Repository Data** | **150 Scenarios** | **150,000** | **100.0%** | - | - |

**Integrity Verification**: Training scenario leakage = **0 scenarios**; Validation scenario leakage = **0 scenarios**. The evaluation benchmark is 100% out-of-sample and uncorrupted by training traces.

---

## 5. Physical Signal Statistics Across Scenario Groups

Extracted directly from `scada_telemetry` ([`t05_signal_statistics_by_scenario_type.md`](file:///c:/projects/p1/New%20folder/results_v2/tables/t05_signal_statistics_by_scenario_type.md)):

| Scenario Group | Records | Level Min (m) | Level Mean (m) | Level Max (m) | Mean $Q_{\text{in}}$ (m³/s) | Mean $Q_{\text{out}}$ (m³/s) | Pump Duty Cycle | Attack Tick Ratio |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Normal (`N_*`)** | 60,000 | 0.4897 | 1.0541 | 1.7125 | 0.002703 | 0.002040 | **53.69%** | **0.00%** |
| **FDI (`A1_*`)** | 45,000 | 0.7833 | 0.9873 | 1.4113 | 0.002001 | 0.001964 | **39.54%** | **18.32%** |
| **Replay (`A2_*`)** | 15,000 | 0.7893 | 0.9600 | 1.2099 | 0.002023 | 0.001964 | **39.99%** | **6.60%** |
| **DoS (`A3_*`)** | 15,000 | 0.7890 | 0.9609 | 1.2131 | 0.001646 | 0.001819 | **32.43%** | **6.90%** |
| **Auth Misuse (`A4_*`)** | 15,000 | 0.3891 | 1.0385 | 2.1043 | 0.001985 | 0.002016 | **39.21%** | **10.10%** |

These measurements demonstrate that `Normal` runs exhibit higher pump duty cycles (53.69%) due to active load perturbations, whereas `Auth Misuse` spans the broadest water level excursions ($0.3891\text{ m}$ to $2.1043\text{ m}$) reflecting adversarial overrides.
