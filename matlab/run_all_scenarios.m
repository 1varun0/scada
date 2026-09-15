%% RUN_ALL_SCENARIOS - Master MATLAB Data Generation Script
%
%  Generates ALL 170 scenarios (60 normal + 110 attack) and exports
%  each as a CSV file to matlab/data/.
%
%  The CSV files match the SQLite schema exactly and can be imported
%  into the Python pipeline using scripts/import_matlab_csv.py
%
%  Usage (from MATLAB command window):
%    >> cd('c:\projects\p1\New folder\matlab')
%    >> run_all_scenarios
%
%  Output:
%    matlab/data/N_001.csv ... N_060.csv     (60 normal scenarios)
%    matlab/data/A1_001.csv ... A1_045.csv   (45 FDI scenarios)
%    matlab/data/A2_001.csv ... A2_015.csv   (15 Replay scenarios)
%    matlab/data/A3_001.csv ... A3_015.csv   (15 DoS scenarios)
%    matlab/data/A4_001.csv ... A4_015.csv   (15 Auth Misuse scenarios)
%    matlab/data/attack_scenarios.csv        (attack metadata)

clear; clc;
fprintf('=== SCADA IDS - MATLAB Data Generation ===\n\n');

% Add attacks subfolder to path so MATLAB can find apply_fdi, etc.
addpath(fullfile(pwd, 'attacks'));

% Load parameters
params = scada_params();

% Ensure output directory exists
output_dir = fullfile(pwd, 'data');
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

% Track attack metadata for separate export
attack_meta = {};
total_records = 0;

%% ════════════════════════════════════════════════════════════════════
%  NORMAL SCENARIOS (N_001 to N_060)
%% ════════════════════════════════════════════════════════════════════
fprintf('--- Generating Normal Scenarios ---\n');

% N_001 to N_020: Steady state
for i = 1:20
    cfg = make_normal_cfg(i, 'Steady_State', 'constant', 1.0, 1.0, 400, 1.0, params);
    [telemetry, ~] = run_single_scenario(params, cfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    total_records = total_records + height(telemetry);
    fprintf('  %s done (%d rows)\n', cfg.scenario_id, height(telemetry));
end

% N_021 to N_035: Setpoint step change 1.0 -> 1.5m
for i = 21:35
    cfg = make_normal_cfg(i, 'Setpoint_Change', 'step', 1.0, 1.5, 400, 1.0, params);
    [telemetry, ~] = run_single_scenario(params, cfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    total_records = total_records + height(telemetry);
    fprintf('  %s done (%d rows)\n', cfg.scenario_id, height(telemetry));
end

% N_036 to N_050: Ramp setpoint 0.8 -> 1.4m
for i = 36:50
    cfg = make_normal_cfg(i, 'Variable_Load', 'ramp', 0.8, 1.4, 200, 1.0, params);
    [telemetry, ~] = run_single_scenario(params, cfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    total_records = total_records + height(telemetry);
    fprintf('  %s done (%d rows)\n', cfg.scenario_id, height(telemetry));
end

% N_051 to N_060: Recovery from low level
for i = 51:60
    cfg = make_normal_cfg(i, 'Recovery', 'constant', 1.0, 1.0, 400, 0.5, params);
    [telemetry, ~] = run_single_scenario(params, cfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    total_records = total_records + height(telemetry);
    fprintf('  %s done (%d rows)\n', cfg.scenario_id, height(telemetry));
end

fprintf('  Normal scenarios complete: 60 scenarios\n\n');

%% ════════════════════════════════════════════════════════════════════
%  ATTACK SCENARIOS
%% ════════════════════════════════════════════════════════════════════
fprintf('--- Generating Attack Scenarios ---\n');
seed_offset = 100;

% ── A1: FDI Bias Small (b=0.05m) ────────────────────────────────────
for i = 1:10
    [cfg, acfg] = make_attack_cfg(i, 'A1', seed_offset+i, ...
        'FDI', 'bias', 0.05, 300, 500, params);
    acfg.description = 'FDI bias +0.05m';
    [telemetry, true_lvls] = run_single_scenario(params, cfg);
    telemetry = apply_fdi(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (FDI bias=0.05)\n', cfg.scenario_id);
end

% ── A1: FDI Bias Medium (b=0.10m) ───────────────────────────────────
for i = 11:20
    [cfg, acfg] = make_attack_cfg(i, 'A1', seed_offset+i, ...
        'FDI', 'bias', 0.10, 300, 500, params);
    acfg.description = 'FDI bias +0.10m';
    [telemetry, ~] = run_single_scenario(params, cfg);
    telemetry = apply_fdi(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (FDI bias=0.10)\n', cfg.scenario_id);
end

% ── A1: FDI Bias Large (b=0.20m) ────────────────────────────────────
for i = 21:30
    [cfg, acfg] = make_attack_cfg(i, 'A1', seed_offset+i, ...
        'FDI', 'bias', 0.20, 300, 500, params);
    acfg.description = 'FDI bias +0.20m';
    [telemetry, ~] = run_single_scenario(params, cfg);
    telemetry = apply_fdi(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (FDI bias=0.20)\n', cfg.scenario_id);
end

% ── A1: FDI Scale (alpha=1.10) ──────────────────────────────────────
for i = 31:40
    [cfg, acfg] = make_attack_cfg(i, 'A1', seed_offset+i, ...
        'FDI', 'scale', 1.10, 300, 500, params);
    acfg.description = 'FDI scale x1.10';
    [telemetry, ~] = run_single_scenario(params, cfg);
    telemetry = apply_fdi(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (FDI scale=1.10)\n', cfg.scenario_id);
end

% ── A1: FDI Intermittent (b=0.15m, every 5th step) ─────────────────
for i = 41:45
    [cfg, acfg] = make_attack_cfg(i, 'A1', seed_offset+i, ...
        'FDI', 'intermittent', 0.15, 300, 500, params);
    acfg.description = 'FDI intermittent bias +0.15m every 5th step';
    [telemetry, ~] = run_single_scenario(params, cfg);
    telemetry = apply_fdi(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (FDI intermittent)\n', cfg.scenario_id);
end

% ── A2: Replay (various buffer lengths) ─────────────────────────────
buffer_lengths = [30 40 50 60 70 80 90 100 35 45 55 65 75 85 95];
for i = 1:15
    buf_len = buffer_lengths(i);
    [cfg, acfg] = make_attack_cfg(i, 'A2', seed_offset+45+i, ...
        'Replay', 'replay', buf_len, 400, 400+buf_len, params);
    acfg.replay_buffer_s = buf_len;
    acfg.description = sprintf('Replay %ds buffer', buf_len);
    [telemetry, ~] = run_single_scenario(params, cfg);
    telemetry = apply_replay(telemetry, acfg);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (Replay %ds)\n', cfg.scenario_id, buf_len);
end

% ── A3: DoS (various durations) ─────────────────────────────────────
dos_durations = [20 30 40 50 60 70 80 90 100 110 120 25 45 75 105];
for i = 1:15
    dur = dos_durations(i);
    [cfg, acfg] = make_attack_cfg(i, 'A3', seed_offset+60+i, ...
        'DoS', 'dos_duration', dur, 350, 350+dur, params);
    acfg.description = sprintf('DoS %ds blocking', dur);
    [telemetry, true_lvls] = run_single_scenario(params, cfg);
    telemetry = apply_dos(telemetry, true_lvls, acfg, params);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (DoS %ds)\n', cfg.scenario_id, dur);
end

% ── A4: Auth Misuse ─────────────────────────────────────────────────
misuse_cmds = {'VALVE_SET_80','VALVE_SET_90','VALVE_SET_100', ...
    'PUMP_ON_AT_HIGH','VALVE_SET_70','VALVE_SET_95', ...
    'PUMP_ON_AT_OVERFLOW','VALVE_SET_85','VALVE_SET_75', ...
    'PUMP_ON_AT_CRIT_HIGH','VALVE_SET_60','VALVE_SET_100_SUSTAINED', ...
    'PUMP_FORCE_ON','VALVE_SET_80_LONG','VALVE_SET_90_LONG'};
misuse_types = {'valve_open_at_low','valve_open_at_low','valve_open_at_low', ...
    'pump_on_at_high','valve_open_at_low','valve_open_at_low', ...
    'pump_on_at_high','valve_open_at_low','valve_open_at_low', ...
    'pump_on_at_high','valve_open_at_low','valve_open_at_low', ...
    'pump_on_at_high','valve_open_at_low','valve_open_at_low'};
misuse_vals = [80 90 100 1 70 95 1 85 75 1 60 100 1 80 90];
misuse_h0   = [0.4 0.4 0.4 2.1 0.4 0.4 2.1 0.4 0.4 2.1 0.4 0.4 2.1 0.4 0.4];

for i = 1:15
    [cfg, acfg] = make_attack_cfg(i, 'A4', seed_offset+75+i, ...
        'Auth_Misuse', misuse_types{i}, misuse_vals(i), 200, 300, params);
    cfg.initial_level = misuse_h0(i);
    cfg.operating_condition = 'Misuse_Condition';
    acfg.unsafe_command = misuse_cmds{i};
    acfg.description = sprintf('Auth misuse: %s', misuse_cmds{i});
    [telemetry, true_lvls] = run_single_scenario(params, cfg);
    telemetry = apply_auth_misuse(telemetry, true_lvls, acfg, params);
    export_csv(telemetry, output_dir, cfg.scenario_id);
    attack_meta{end+1} = make_attack_meta(cfg, acfg); %#ok<SAGROW>
    total_records = total_records + height(telemetry);
    fprintf('  %s done (Misuse: %s)\n', cfg.scenario_id, misuse_cmds{i});
end

%% ════════════════════════════════════════════════════════════════════
%  Export attack metadata
%% ════════════════════════════════════════════════════════════════════
if ~isempty(attack_meta)
    meta_table = vertcat(attack_meta{:});
    writetable(meta_table, fullfile(output_dir, 'attack_scenarios.csv'));
    fprintf('\nAttack metadata saved to data/attack_scenarios.csv\n');
end

fprintf('\n=== COMPLETE ===\n');
fprintf('Total scenarios: 170\n');
fprintf('Total records:   %d\n', total_records);
fprintf('Output dir:      %s\n', output_dir);
fprintf('\nNext step: Run in Python:\n');
fprintf('  python scripts/import_matlab_csv.py\n');


%% ════════════════════════════════════════════════════════════════════
%  HELPER FUNCTIONS
%% ════════════════════════════════════════════════════════════════════

function cfg = make_normal_cfg(idx, op_cond, sp_type, sp_init, sp_final, sp_change, h0, params)
    cfg.scenario_id         = sprintf('N_%03d', idx);
    cfg.seed                = params.sim.base_seed + idx;
    cfg.duration            = params.sim.duration;
    cfg.initial_level       = h0;
    cfg.operating_condition = op_cond;
    cfg.setpoint_type       = sp_type;
    cfg.setpoint_initial    = sp_init;
    cfg.setpoint_final      = sp_final;
    cfg.setpoint_change_time = sp_change;
end

function [cfg, acfg] = make_attack_cfg(idx, prefix, seed_idx, ...
        attack_type, param_type, param_val, start_s, end_s, params)
    cfg.scenario_id         = sprintf('%s_%03d', prefix, idx);
    cfg.seed                = params.sim.base_seed + 100 + seed_idx;
    cfg.duration            = params.sim.duration;
    cfg.initial_level       = params.tank.initial_level;
    cfg.operating_condition = 'Steady_State';
    cfg.setpoint_type       = 'constant';
    cfg.setpoint_initial    = params.ctrl.setpoint;
    cfg.setpoint_final      = params.ctrl.setpoint;
    cfg.setpoint_change_time = 400;

    acfg.attack_type      = attack_type;
    acfg.attack_id        = sprintf('%s_%03d_%s', prefix, idx, attack_type);
    acfg.attack_start     = start_s;
    acfg.attack_end       = end_s;
    acfg.parameter_type   = param_type;
    acfg.parameter_value  = param_val;
    acfg.replay_buffer_s  = 0;
    acfg.unsafe_command   = '';
    acfg.description      = '';
end

function meta = make_attack_meta(cfg, acfg)
    meta = table( ...
        {cfg.scenario_id}, {acfg.attack_id}, {acfg.attack_type}, ...
        acfg.attack_start, acfg.attack_end, ...
        {acfg.parameter_type}, acfg.parameter_value, ...
        cfg.seed, {acfg.description}, ...
        {cfg.operating_condition}, cfg.initial_level, ...
        'VariableNames', { ...
            'scenario_id', 'attack_id', 'attack_type', ...
            'attack_start_time_s', 'attack_end_time_s', ...
            'attack_parameter_type', 'attack_parameter_value', ...
            'random_seed', 'description', ...
            'operating_condition', 'initial_tank_level' ...
        });
end

function export_csv(telemetry, output_dir, scenario_id)
    filepath = fullfile(output_dir, [scenario_id '.csv']);
    writetable(telemetry, filepath);
end
