# Source File Note: `matlab/attacks/apply_auth_misuse.m`

## Purpose
MATLAB post-processing function applying Authenticated Misuse (A4) attacks. Simulates an authorized operator issuing process-unsafe commands during the attack window $[200, 300]\text{s}$, driving rapid drain or filling.

## Public Classes and Functions
- `function telemetry = apply_auth_misuse(telemetry, true_levels, attack_cfg, params)`:
  - Within attack window:
    - Case `'valve_open_at_low'`: forces `valve_command = parameter_value` ($60\text{--}100\%$), `pump_command = 0`, `control_command = attack_cfg.unsafe_command`. Computes outflow $Q_{\text{out}} = C_v \left(\frac{V\%}{100}\right)\sqrt{H}$.
    - Case `'pump_on_at_high'`: forces `pump_command = 1`, `valve_command = 0%`. Sets $Q_{\text{in}} = Q_{\text{max}}$, $Q_{\text{out}} = 0.0$.
    - Updates local Euler integration $H \leftarrow \text{clamp}(H + dH, 0, H_{\text{max}})$.
    - Applies noise: `tank_level_observed = H + noise_level * randn()`.
    - Applies clamped flow noise: `telemetry.q_in = max(0, q_in + noise_flow * randn())` and `telemetry.q_out = max(0, q_out + noise_flow * randn())`.
    - Sets cyber credentials: `is_authenticated = 1`, `is_authorized = 1`, `user_id = 'attacker_01'`, `user_role = 'operator'`.
    - Sets `attack_type = 'Auth_Misuse'`, `ground_truth = 1`.
  - When $t > t_{\text{end}}$: resets `H = -1` and exits attack branch.

## Inputs and Outputs
- Inputs: Completed normal table, true levels, attack config struct, parameters struct.
- Output: Modified MATLAB table.

## Config Keys and Constants Read
- Reads `params.sim.dt` (1.0s), `params.valve.cv` (0.004 m³/s), `params.pump.q_max` (0.005 m³/s), `params.tank.area` (2.0 m²), `params.tank.max_height` (2.5 m), `params.sim.noise_level` (0.005 m), `params.sim.noise_flow` (0.0001 m³/s).

## Who Calls It
- `matlab/run_all_scenarios.m`
- `matlab/run_single_scenario.m`

## Side Effects
- In-memory table modifications.

## Tests Covering It
- Policy engine tests and evaluation scripts.

## Surprising / Notable Observations
- Explicit flow noise clamping: Lines 75-76 explicitly execute `max(0, q_in + params.sim.noise_flow * randn())` and `max(0, q_out + params.sim.noise_flow * randn())`, confirming that non-negative flow noise clamping is embedded directly in MATLAB attack data generation.
- Post-attack discontinuity: Like DoS, the script ceases simulation when $t > 300\text{s}$. Ticks $301\text{--}1000$ revert directly to the normal run's trajectory, creating a discontinuous level step at $t = 301\text{s}$.
- Credential illusion: The attacker uses valid operator permissions (`is_authenticated = 1`, `is_authorized = 1`), proving that cyber-only authorization filters cannot detect this attack without domain-level process safety awareness.
