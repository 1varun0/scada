# Table T04: Dataset Partitioning and Benchmark Coverage

> Source: `checkpoints/data_split_v1.json` cross-referenced with `data/evaluation_results.csv`.

## Partition Split Summary

| Partition | Scenarios Included | Scenario IDs | Record Count | Fraction of Dataset | In `evaluation_results.csv`? |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Training** | 42 Normal | `N_041`, `N_005`, ..., `N_039` (42 total) | 42,000 | 28.0% | ❌ No (Zero leakage) |
| **Validation** | 9 Normal | `N_058`, `N_047`, `N_051`, `N_032`, `N_004`, `N_053`, `N_018`, `N_009`, `N_007` | 9,000 | 6.0% | ❌ No (Zero leakage) |
| **Test Normal** | 9 Normal | `N_001`, `N_006`, `N_037`, `N_046`, `N_014`, `N_055`, `N_034`, `N_049`, `N_013` | 9,000 | 6.0% | ✅ Yes (All 9) |
| **Test Attacks** | 90 Attacks | `A1_001` - `A1_045`, `A2_001` - `A2_015`, `A3_001` - `A3_015`, `A4_001` - `A4_015` | 90,000 | 60.0% | ✅ Yes (All 90) |
| **Total Test Set** | **99 Scenarios** | **9 Normal + 90 Attack** | **99,000** | **66.0%** | **✅ 100% Exact Match** |
| **Full Dataset** | **150 Scenarios** | **60 Normal + 90 Attack** | **150,000** | **100.0%** | - |

## Data Leakage Verification

- Training scenario leakage into evaluation set: **0 scenarios** (Verified clean).
- Validation scenario leakage into evaluation set: **0 scenarios** (Verified clean).
- Test normal scenarios exact match: **True**.
- Attack scenarios coverage in evaluation set: **True** (90 of 90 evaluated).
