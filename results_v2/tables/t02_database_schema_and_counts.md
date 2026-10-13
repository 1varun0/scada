# Table T02: Database Tables and Schema Specification

> Source: `data/scada_ids.db` (Sandbox copy), queried with SQLite in read-only mode via `results_v2/scripts/query_dataset_facts.py`.

## Table Inventory & Record Counts

| Table Name | Primary Purpose | Record Count | Column Count | Primary Key |
| :--- | :--- | :---: | :---: | :--- |
| `scada_telemetry` | Per-tick SCADA sensor and actuator stream across all 150 scenarios | 150,000 | 25 | `scenario_id, sequence_id` |
| `attack_scenarios` | Ground truth attack configuration, windows, and operating condition metadata | 90 | 11 | `attack_id` |
| `experiment_runs` | Model training runs, hyperparameters, and detection threshold definitions | 0 | 12 | `experiment_id` |
| `evaluation_results` | Pre-computed benchmark IDS outputs and residual scores for 99 test scenarios | 0 | 14 | `experiment_id, scenario_id, sequence_id` |

## Detailed Schema Definitions

### `scada_telemetry` Schema

| Column Name | Data Type | Not Null | Default Value | PK |
| :--- | :---: | :---: | :---: | :---: |
| `scenario_id` | `TEXT` | True | - | 1 |
| `sequence_id` | `INTEGER` | True | - | 2 |
| `simulation_time_s` | `REAL` | True | - | 0 |
| `source_time_s` | `REAL` | True | - | 0 |
| `data_age_ms` | `INTEGER` | True | - | 0 |
| `packet_received` | `INTEGER` | True | - | 0 |
| `communication_status` | `TEXT` | True | - | 0 |
| `operating_condition` | `TEXT` | True | - | 0 |
| `tank_level_setpoint` | `REAL` | True | - | 0 |
| `tank_level_observed` | `REAL` | True | - | 0 |
| `q_in` | `REAL` | True | - | 0 |
| `q_out` | `REAL` | True | - | 0 |
| `pump_command` | `INTEGER` | True | - | 0 |
| `pump_state` | `INTEGER` | True | - | 0 |
| `valve_command` | `REAL` | True | - | 0 |
| `valve_state` | `REAL` | True | - | 0 |
| `control_command` | `TEXT` | False | - | 0 |
| `user_id` | `TEXT` | False | - | 0 |
| `user_role` | `TEXT` | False | - | 0 |
| `is_authenticated` | `INTEGER` | False | - | 0 |
| `is_authorized` | `INTEGER` | False | - | 0 |
| `attack_type` | `TEXT` | True | 'None' | 0 |
| `attack_parameter` | `REAL` | False | - | 0 |
| `ground_truth` | `INTEGER` | True | 0 | 0 |
| `replay_source_sequence_id` | `INTEGER` | False | - | 0 |

### `attack_scenarios` Schema

| Column Name | Data Type | Not Null | Default Value | PK |
| :--- | :---: | :---: | :---: | :---: |
| `scenario_id` | `TEXT` | True | - | 0 |
| `attack_id` | `TEXT` | True | - | 1 |
| `attack_type` | `TEXT` | True | - | 0 |
| `attack_start_time_s` | `REAL` | False | - | 0 |
| `attack_end_time_s` | `REAL` | False | - | 0 |
| `attack_parameter_type` | `TEXT` | False | - | 0 |
| `attack_parameter_value` | `REAL` | False | - | 0 |
| `random_seed` | `INTEGER` | True | - | 0 |
| `description` | `TEXT` | False | - | 0 |
| `operating_condition` | `TEXT` | False | - | 0 |
| `initial_tank_level` | `REAL` | False | - | 0 |

### `experiment_runs` Schema

| Column Name | Data Type | Not Null | Default Value | PK |
| :--- | :---: | :---: | :---: | :---: |
| `experiment_id` | `TEXT` | False | - | 1 |
| `model_version` | `TEXT` | False | - | 0 |
| `feature_version` | `TEXT` | False | - | 0 |
| `threshold_version` | `TEXT` | False | - | 0 |
| `fusion_version` | `TEXT` | False | - | 0 |
| `training_scenario_ids` | `TEXT` | False | - | 0 |
| `validation_scenario_ids` | `TEXT` | False | - | 0 |
| `test_scenario_ids` | `TEXT` | False | - | 0 |
| `hyperparameters` | `TEXT` | False | - | 0 |
| `thresholds` | `TEXT` | False | - | 0 |
| `fusion_weights` | `TEXT` | False | - | 0 |
| `created_at` | `TEXT` | True | - | 0 |

### `evaluation_results` Schema

| Column Name | Data Type | Not Null | Default Value | PK |
| :--- | :---: | :---: | :---: | :---: |
| `experiment_id` | `TEXT` | True | - | 1 |
| `scenario_id` | `TEXT` | True | - | 2 |
| `sequence_id` | `INTEGER` | True | - | 3 |
| `simulation_time_s` | `REAL` | True | - | 0 |
| `h_twin` | `REAL` | False | - | 0 |
| `physics_residual` | `REAL` | False | - | 0 |
| `S_p` | `REAL` | False | - | 0 |
| `lstm_reconstruction_error` | `REAL` | False | - | 0 |
| `S_l` | `REAL` | False | - | 0 |
| `S_c` | `REAL` | False | - | 0 |
| `S_a` | `REAL` | False | - | 0 |
| `S_hybrid` | `REAL` | False | - | 0 |
| `predicted_anomaly` | `INTEGER` | False | - | 0 |
| `ground_truth` | `INTEGER` | False | - | 0 |
