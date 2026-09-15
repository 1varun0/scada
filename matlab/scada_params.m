%% SCADA_PARAMS - Frozen Physical Parameter Sheet
%  Mirrors config/parameters.py exactly.
%  DO NOT modify after E0 validation without re-running entire pipeline.
%
%  Usage: params = scada_params();

function params = scada_params()

    % ── Tank Parameters ──────────────────────────────────────────────
    params.tank.area            = 2.0;      % m^2, cross-sectional area
    params.tank.max_height      = 2.5;      % m, physical ceiling
    params.tank.initial_level   = 1.0;      % m, default H0 (40% fill)
    params.tank.critical_low    = 0.3;      % m, cavitation risk
    params.tank.critical_high   = 2.3;      % m, overflow risk
    params.tank.overflow        = 2.5;      % m, absolute max

    % ── Pump Parameters ──────────────────────────────────────────────
    params.pump.q_max           = 0.005;    % m^3/s (5 L/s)
    params.pump.response_delay  = 2.0;      % seconds
    params.pump.delay_steps     = 2;        % ceil(response_delay / dt)

    % ── Valve Parameters ─────────────────────────────────────────────
    params.valve.cv             = 0.004;    % m^3/s, flow coefficient
    params.valve.response_time  = 1.5;      % seconds
    params.valve.safe_position  = 0.0;      % %, fail-safe = closed
    params.valve.max_slew_rate  = 100.0 / 1.5;  % %/s

    % ── Controller Parameters ────────────────────────────────────────
    params.ctrl.setpoint        = 1.0;      % m, nominal level
    params.ctrl.deadband        = 0.2;      % m, hysteresis band
    params.ctrl.pump_on_thresh  = 0.8;      % m, setpoint - deadband
    params.ctrl.pump_off_thresh = 1.2;      % m, setpoint + deadband
    params.ctrl.default_valve   = 50.0;     % %, default valve opening

    % ── Simulation Parameters ────────────────────────────────────────
    params.sim.dt               = 1.0;      % seconds
    params.sim.duration         = 1000.0;   % seconds per scenario
    params.sim.noise_level      = 0.005;    % m, sensor noise std (H)
    params.sim.noise_flow       = 0.0001;   % m^3/s, sensor noise std (Q)
    params.sim.actuator_delay   = 1;        % steps
    params.sim.base_seed        = 42000;    % deterministic base seed

end
