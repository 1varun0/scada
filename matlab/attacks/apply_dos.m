%% APPLY_DOS - Denial of Service Attack (A3)
%
%  Simulates communication blocking during the attack window.
%  Sets packet_received=0 and communication_status='BLOCKED'.
%
%  The physical simulation continues (tank level still changes based
%  on gravity drain), but the controller enters FAIL-SAFE mode:
%    Pump = OFF, Valve = 0% (V_safe)
%
%  The telemetry records are still generated with packet_received=0
%  to represent the true physical state progressing independently.
%
%  Usage:
%    telemetry = apply_dos(telemetry, true_levels, attack_cfg, params);

function telemetry = apply_dos(telemetry, true_levels, attack_cfg, params)

    n = height(telemetry);
    t = telemetry.simulation_time_s;
    dt = params.sim.dt;

    % We need to re-simulate the physical process during DoS
    % because the controller switches to fail-safe mode
    H = -1;  % Will be set when DoS starts

    for k = 1:n
        if t(k) >= attack_cfg.attack_start && t(k) <= attack_cfg.attack_end

            % Initialize H from the true level at DoS start
            if H < 0
                H = true_levels(k);
            end

            % Fail-safe: Pump OFF, Valve closed (0%)
            telemetry.pump_command(k) = 0;
            telemetry.pump_state(k)   = 0;
            telemetry.valve_command(k) = params.valve.safe_position;  % 0%
            telemetry.valve_state(k)   = params.valve.safe_position;  % 0%
            telemetry.control_command{k} = 'FAILSAFE';

            % Communication blocked
            telemetry.packet_received(k)       = 0;
            telemetry.communication_status{k}  = 'BLOCKED';

            % Physics continues: pump OFF + valve 0% = no flow
            q_in  = 0.0;
            q_out = 0.0;  % Valve is closed in fail-safe

            % Update true physics
            dH = (q_in - q_out) / params.tank.area * dt;
            H  = max(0, min(H + dH, params.tank.max_height));

            % Observed level = true level + noise (but packet not received)
            telemetry.tank_level_observed(k) = H + params.sim.noise_level * randn();
            telemetry.q_in(k)  = 0.0;
            telemetry.q_out(k) = 0.0;

            % Mark as attack
            telemetry.attack_type{k}      = 'DoS';
            telemetry.attack_parameter(k) = attack_cfg.parameter_value;
            telemetry.ground_truth(k)     = 1;

        elseif t(k) > attack_cfg.attack_end && H >= 0
            % After DoS ends: reset H flag so we don't re-enter
            % The remaining simulation continues from post-DoS state
            H = -1;
        end
    end
end
