%% RUN_SINGLE_SCENARIO - Simulate one SCADA scenario
%
%  Runs the tank/pump/valve/controller physics for one scenario and
%  returns a table of telemetry records matching the SQLite schema.
%
%  Usage:
%    params = scada_params();
%    cfg = struct('scenario_id','N_001', 'seed',42001, 'duration',1000, ...
%                 'initial_level',1.0, 'operating_condition','Steady_State', ...
%                 'setpoint_type','constant', 'setpoint_initial',1.0, ...
%                 'setpoint_final',1.0, 'setpoint_change_time',400);
%    [telemetry, true_levels] = run_single_scenario(params, cfg);
%
%  Inputs:
%    params - struct from scada_params()
%    cfg    - scenario configuration struct
%
%  Outputs:
%    telemetry   - table with all schema columns (one row per timestep)
%    true_levels - vector of true (noise-free) tank levels for Twin validation

function [telemetry, true_levels] = run_single_scenario(params, cfg)

    dt       = params.sim.dt;
    n_steps  = floor(cfg.duration / dt);

    % Seed the random number generator for reproducibility
    rng(cfg.seed, 'twister');

    % ── Initialize state ─────────────────────────────────────────────
    H = cfg.initial_level;                  % True tank level
    pump_state   = 0;                       % Actual pump (0=OFF, 1=ON)
    pump_command = 0;                       % Commanded pump
    valve_pos    = params.ctrl.default_valve; % Actual valve position (%)
    valve_cmd    = params.ctrl.default_valve; % Commanded valve
    steps_since_pump_cmd = params.pump.delay_steps; % Start settled

    % Current setpoint (may change via profile)
    setpoint = cfg.setpoint_initial;
    pump_on_thresh  = setpoint - params.ctrl.deadband;
    pump_off_thresh = setpoint + params.ctrl.deadband;

    % ── Pre-allocate output arrays ───────────────────────────────────
    scenario_ids        = cell(n_steps, 1);
    sequence_ids        = zeros(n_steps, 1);
    sim_times           = zeros(n_steps, 1);
    source_times        = zeros(n_steps, 1);
    data_ages           = zeros(n_steps, 1);
    pkt_received        = ones(n_steps, 1);
    comm_status         = cell(n_steps, 1);
    op_conditions       = cell(n_steps, 1);
    setpoints           = zeros(n_steps, 1);
    observed_levels     = zeros(n_steps, 1);
    q_ins               = zeros(n_steps, 1);
    q_outs              = zeros(n_steps, 1);
    pump_cmds           = zeros(n_steps, 1);
    pump_states         = zeros(n_steps, 1);
    valve_cmds          = zeros(n_steps, 1);
    valve_states        = zeros(n_steps, 1);
    ctrl_cmds           = cell(n_steps, 1);
    user_ids            = cell(n_steps, 1);
    user_roles          = cell(n_steps, 1);
    is_auth             = ones(n_steps, 1);
    is_authz            = ones(n_steps, 1);
    attack_types        = cell(n_steps, 1);
    attack_params       = nan(n_steps, 1);
    ground_truths       = zeros(n_steps, 1);
    replay_src_seq      = nan(n_steps, 1);
    true_levels         = zeros(n_steps, 1);

    % ── Simulation loop ──────────────────────────────────────────────
    for k = 1:n_steps
        t = (k-1) * dt;

        % 1. Update setpoint from profile
        setpoint = get_setpoint(cfg, t);
        pump_on_thresh  = setpoint - params.ctrl.deadband;
        pump_off_thresh = setpoint + params.ctrl.deadband;

        % 2. Sensor readings with noise
        H_observed = H + params.sim.noise_level * randn();

        % 3. Controller logic (hysteresis / bang-bang)
        ctrl_cmd_str = 'HOLD';
        if H_observed < pump_on_thresh
            new_pump_cmd = 1;
            ctrl_cmd_str = 'PUMP_ON';
        elseif H_observed > pump_off_thresh
            new_pump_cmd = 0;
            ctrl_cmd_str = 'PUMP_OFF';
        else
            new_pump_cmd = pump_command;  % Hold current
        end

        % Track pump command changes for delay
        if new_pump_cmd ~= pump_command
            pump_command = new_pump_cmd;
            steps_since_pump_cmd = 0;
        end
        steps_since_pump_cmd = steps_since_pump_cmd + 1;

        % Apply pump delay
        if steps_since_pump_cmd >= params.pump.delay_steps
            pump_state = pump_command;
        end

        % Valve: slew-rate limited approach to command
        valve_cmd = params.ctrl.default_valve;
        valve_error = valve_cmd - valve_pos;
        max_change = params.valve.max_slew_rate * dt;
        if abs(valve_error) <= max_change
            valve_pos = valve_cmd;
        elseif valve_error > 0
            valve_pos = valve_pos + max_change;
        else
            valve_pos = valve_pos - max_change;
        end
        valve_pos = max(0, min(100, valve_pos));

        % 4. Compute flows
        if pump_state == 1
            q_in_true = params.pump.q_max;
        else
            q_in_true = 0.0;
        end

        if H > 0
            q_out_true = params.valve.cv * (valve_pos / 100) * sqrt(H);
        else
            q_out_true = 0.0;
        end

        % Add flow noise
        q_in_obs  = max(0, q_in_true  + params.sim.noise_flow * randn());
        q_out_obs = max(0, q_out_true + params.sim.noise_flow * randn());

        % 5. Store true level BEFORE update (for residual alignment)
        true_levels(k) = H;

        % 6. Tank physics (Euler integration)
        dH = (q_in_true - q_out_true) / params.tank.area * dt;
        H  = max(0, min(H + dH, params.tank.max_height));

        % 7. Record telemetry
        scenario_ids{k}     = cfg.scenario_id;
        sequence_ids(k)     = k - 1;  % 0-indexed to match Python
        sim_times(k)        = t;
        source_times(k)     = t;      % Normal: source = sim time
        data_ages(k)        = 0;      % Normal: no lag
        pkt_received(k)     = 1;
        comm_status{k}      = 'NORMAL';
        op_conditions{k}    = cfg.operating_condition;
        setpoints(k)        = setpoint;
        observed_levels(k)  = H_observed;
        q_ins(k)            = q_in_obs;
        q_outs(k)           = q_out_obs;
        pump_cmds(k)        = pump_command;
        pump_states(k)      = pump_state;
        valve_cmds(k)       = valve_cmd;
        valve_states(k)     = valve_pos;
        ctrl_cmds{k}        = ctrl_cmd_str;
        user_ids{k}         = 'operator_01';
        user_roles{k}       = 'operator';
        is_auth(k)          = 1;
        is_authz(k)         = 1;
        attack_types{k}     = 'None';
        attack_params(k)    = NaN;
        ground_truths(k)    = 0;
        replay_src_seq(k)   = NaN;
    end

    % ── Build output table ───────────────────────────────────────────
    telemetry = table( ...
        scenario_ids, sequence_ids, sim_times, source_times, data_ages, ...
        pkt_received, comm_status, op_conditions, setpoints, ...
        observed_levels, q_ins, q_outs, ...
        pump_cmds, pump_states, valve_cmds, valve_states, ctrl_cmds, ...
        user_ids, user_roles, is_auth, is_authz, ...
        attack_types, attack_params, ground_truths, replay_src_seq, ...
        'VariableNames', { ...
            'scenario_id', 'sequence_id', 'simulation_time_s', ...
            'source_time_s', 'data_age_ms', 'packet_received', ...
            'communication_status', 'operating_condition', ...
            'tank_level_setpoint', 'tank_level_observed', 'q_in', 'q_out', ...
            'pump_command', 'pump_state', 'valve_command', 'valve_state', ...
            'control_command', 'user_id', 'user_role', ...
            'is_authenticated', 'is_authorized', ...
            'attack_type', 'attack_parameter', 'ground_truth', ...
            'replay_source_sequence_id' ...
        });
end


%% ── Helper: Setpoint Profile ────────────────────────────────────────
function sp = get_setpoint(cfg, t)
    switch cfg.setpoint_type
        case 'constant'
            sp = cfg.setpoint_initial;
        case 'step'
            if t >= cfg.setpoint_change_time
                sp = cfg.setpoint_final;
            else
                sp = cfg.setpoint_initial;
            end
        case 'ramp'
            if t <= cfg.setpoint_change_time
                sp = cfg.setpoint_initial;
            else
                ramp_dur = cfg.duration - cfg.setpoint_change_time;
                if ramp_dur <= 0
                    sp = cfg.setpoint_final;
                else
                    progress = min((t - cfg.setpoint_change_time) / ramp_dur, 1.0);
                    sp = cfg.setpoint_initial + progress * (cfg.setpoint_final - cfg.setpoint_initial);
                end
            end
        otherwise
            sp = cfg.setpoint_initial;
    end
end
