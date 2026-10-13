# Source File Note: `matlab/attacks/apply_replay.m`

## Purpose
MATLAB post-processing function applying Replay (A2) attack modifications by substituting current tank level measurements with a pre-attack historical recording window and preserving original timestamps.

## Public Classes and Functions
- `function telemetry = apply_replay(telemetry, attack_cfg)`:
  - Extracts historical window: $[t_{\text{start}} - \Delta t_{\text{buf}}, t_{\text{start}})$.
  - Captures `buffer_levels`, `buffer_source_ts`, and `buffer_seq_ids`.
  - For each step $k$ in attack window, cycles cyclically through buffer indices.
  - Replaces `tank_level_observed(k)`.
  - Sets `source_time_s(k) = buffer_source_ts(buf_idx)`.
  - Calculates `data_age_ms(k) = round((t(k) - source_time_s(k)) * 1000)`.
  - Sets `replay_source_sequence_id(k) = buffer_seq_ids(buf_idx)`.
  - Sets `attack_type{k} = 'Replay'`, `attack_parameter(k) = parameter_value`, `ground_truth(k) = 1`.

## Inputs and Outputs
- Inputs:
  - `telemetry`: Completed normal simulation table.
  - `attack_cfg`: struct with `attack_start`, `attack_end`, `replay_buffer_s`, `parameter_value`.
- Output: Modified table.

## Config Keys and Constants Read
- Reads fields from struct `attack_cfg`.

## Who Calls It
- `matlab/run_all_scenarios.m`
- `matlab/run_single_scenario.m`

## Side Effects
- In-memory table modifications.

## Tests Covering It
- Cross-validation and availability engine tests.

## Surprising / Notable Observations
- Partial signal replay: Only `tank_level_observed` is replaced from the replay buffer. Actuator states (`pump_state`, `valve_state`) and flow measurements (`q_in`, `q_out`) continue to reflect the contemporaneous (peaceful) state.
- Stale timestamp preservation: Crucially, `source_time_s` is assigned the historical timestamp (lines 65-68), causing `data_age_ms` to jump from 0 ms to between 30,000 ms and 100,000 ms on the exact tick the attack starts. This makes the attack instantly detectable by the Availability Engine ($S_a = 1.0$), since $\tau_a = 1500\text{ ms}$.
