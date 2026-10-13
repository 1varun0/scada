# Source File Note: scada_live/config.yaml

## 1. Purpose
Defines configuration parameters for the real-time simulation, gateway, detection engines, prevention controller, and network services [CODE scada_live/config.yaml:1-110].

## 2. Structure & Sections
- `tank`: `cross_section_area_m2: 2.0`, `max_height_m: 2.5`, `initial_level_m: 1.0`, `critical_low_m: 0.3`, `critical_high_m: 2.3`, `overflow_m: 2.5` [CODE scada_live/config.yaml:2-8].
- `pump`: `q_max_m3s: 0.005`, `response_delay_s: 2.0` [CODE scada_live/config.yaml:11-13].
- `valve`: `flow_coefficient_m3s: 0.004`, `response_time_s: 1.5`, `safe_position_pct: 0.0` [CODE scada_live/config.yaml:16-19].
- `controller`: `setpoint_m: 1.0`, `deadband_m: 0.2`, `pump_on_threshold_m: 0.8`, `pump_off_threshold_m: 1.2`, `default_valve_pct: 50.0` [CODE scada_live/config.yaml:22-27].
- `simulation`: `dt_s: 1.0`, `time_scale: 1.0`, `sensor_noise_level_m: 0.005`, `sensor_noise_flow_m3s: 0.0001`, `clamp_flow_noise: false`, `random_seed: 42000` [CODE scada_live/config.yaml:30-36].
- `ids`: `tau_p: 0.035`, `tau_l: 0.0085`, `tau_a_ms: 1500.0`, `tau_a_max_ms: 5000.0`, `tau_fusion: 0.95`, `policy_version: "v1"`, `dos_gap_rule: false`, `gap_collect_timeout_ticks: 20`, `lstm_window: 10`, `consecutive_flag_count: 3`, `clear_count: 5`, `epsilon_m: 0.05` [CODE scada_live/config.yaml:39-51].
- `lstm`: `weights_path: "checkpoints/lstm_ae_v1.pt"`, `scaler_path: "checkpoints/scaler_v1.pkl"`, `input_dim: 5`, `hidden_dim: 32`, `num_layers: 1`, `feature_cols: [...]` [CODE scada_live/config.yaml:54-65].
- `prevention`: `default_mode: "monitor"`, `act_on: ["physics"]`, `takeover_engines: ["physics"]`, `trigger_state: "CRITICAL"`, `fdi_takeover: true`, `handback_tolerance_m: 0.05`, `handback_clean_ticks: 5`, `auto_handback: false`, `safe_pump_state: 0`, `safe_valve_pct: 0.0`, `dos_rate_limit_per_s: 10`, `quarantine_duration_s: 30`, `stale_packet_tolerance_s: 5.0` [CODE scada_live/config.yaml:68-81].
- `network`: `plant_host: "127.0.0.1"`, `plant_port: 5100`, `scada_host: "127.0.0.1"`, `scada_port: 5000`, `attacker_host: "127.0.0.1"`, `attacker_port: 5001` [CODE scada_live/config.yaml:85-91].
- `gateway`: `sense_timeout_s: 0.5`, `sse_queue_size: 200`, `sse_keepalive_s: 15`, `history_size: 300`, `watchdog_enabled: false`, `watchdog_factor: 1.5` [CODE scada_live/config.yaml:93-99].
- `alert`: `n_flags: 3`, `window_w: 5`, `m_clear: 5` [CODE scada_live/config.yaml:100-103].
- `recalibration`: `n_samples: 10`, `max_std_m: 0.03` [CODE scada_live/config.yaml:104-106].
- `persistence`: `db_path: data/live_run.db` [CODE scada_live/config.yaml:107-108].

## 3. Who Reads It
- Loaded by `scada_live/common/config_loader.py:load_config()` [CODE scada_live/common/config_loader.py:5-15].
- Read by `LivePlant`, `StreamingIDS`, `GatewayCore`, `AlertManager`, `server.py`, `run_demo.py`.

## 4. Surprises, Mismatches, or Dead Code
- `simulation.clamp_flow_noise: false` [CODE scada_live/config.yaml:35]: Unlike the MATLAB batch dataset (which clamped flow noise with `max(0, Q+noise)`), the live default is `false`.
- `ids.policy_version: "v1"` in config.yaml, but `GatewayCore.__init__` instantiates `StreamingIDS(cfg, policy_version="v2", ...)` [CODE scada_live/scada_ids/gateway_core.py:74], overriding the YAML default for live operation.
- `ids.dos_gap_rule: false` in config.yaml, but `GatewayCore.__init__` sets `dos_gap_rule=True` by default parameter [CODE scada_live/scada_ids/gateway_core.py:69, 74].
- `gateway.watchdog_enabled: false` in config.yaml, but `run_demo.py:main` explicitly sets `cfg.gateway.watchdog_enabled = True` [CODE run_demo.py:331].
- `prevention.dos_rate_limit_per_s: 10` and `quarantine_duration_s: 30` [CODE scada_live/config.yaml:79-80] are not referenced in `gateway_core.py` (planned Phase 6 features).
