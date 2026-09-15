%% APPLY_AUTH_MISUSE - Authenticated Misuse Attack (A4)
%
%  The attacker operates through a valid authenticated/authorized session
%  but issues a command that violates process safety constraints.
%
%  is_authenticated = 1, is_authorized = 1, but the control_command
%  is physically unsafe given the current tank state.
%
%  Example: Opening valve to 80% when tank level is critically low.
%
%  The unsafe command immediately triggers the Policy Engine, while
%  the resulting process trajectory may subsequently generate temporal
%  anomaly evidence from the LSTM-AE.
%
%  Usage:
%    telemetry = apply_auth_misuse(telemetry, true_levels, attack_cfg, params);

function telemetry = apply_auth_misuse(telemetry, true_levels, attack_cfg, params)

    n = height(telemetry);
    t = telemetry.simulation_time_s;
    dt = params.sim.dt;

    H = -1;  % Will be set when attack starts

    for k = 1:n
        if t(k) >= attack_cfg.attack_start && t(k) <= attack_cfg.attack_end

            % Initialize H from true level at attack start
            if H < 0
                H = true_levels(k);
            end

            % Parse the unsafe command
            switch attack_cfg.parameter_type
                case 'valve_open_at_low'
                    % Force valve to unsafe opening when level is low
                    unsafe_valve_pct = attack_cfg.parameter_value;
                    telemetry.valve_command(k) = unsafe_valve_pct;
                    telemetry.valve_state(k)   = unsafe_valve_pct;
                    telemetry.pump_command(k)   = 0;  % Pump OFF makes it worse
                    telemetry.pump_state(k)     = 0;
                    telemetry.control_command{k} = attack_cfg.unsafe_command;

                    % Physics: pump OFF, valve open
                    q_in  = 0.0;
                    if H > 0
                        q_out = params.valve.cv * (unsafe_valve_pct / 100) * sqrt(H);
                    else
                        q_out = 0.0;
                    end

                case 'pump_on_at_high'
                    % Force pump ON when tank is near overflow
                    telemetry.pump_command(k) = 1;
                    telemetry.pump_state(k)   = 1;
                    telemetry.valve_command(k) = 0;  % Valve closed makes it worse
                    telemetry.valve_state(k)   = 0;
                    telemetry.control_command{k} = attack_cfg.unsafe_command;

                    % Physics: pump ON, valve closed
                    q_in  = params.pump.q_max;
                    q_out = 0.0;

                otherwise
                    continue;
            end

            % Update true physics
            dH = (q_in - q_out) / params.tank.area * dt;
            H  = max(0, min(H + dH, params.tank.max_height));

            % Observed level
            telemetry.tank_level_observed(k) = H + params.sim.noise_level * randn();
            telemetry.q_in(k)  = max(0, q_in  + params.sim.noise_flow * randn());
            telemetry.q_out(k) = max(0, q_out + params.sim.noise_flow * randn());

            % Auth fields: authenticated and authorized but unsafe
            telemetry.is_authenticated(k) = 1;
            telemetry.is_authorized(k)    = 1;
            telemetry.user_id{k}          = 'attacker_01';
            telemetry.user_role{k}        = 'operator';

            % Mark as attack
            telemetry.attack_type{k}      = 'Auth_Misuse';
            telemetry.attack_parameter(k) = attack_cfg.parameter_value;
            telemetry.ground_truth(k)     = 1;

        elseif t(k) > attack_cfg.attack_end && H >= 0
            H = -1;
        end
    end
end
