%% APPLY_FDI - False Data Injection Attack (A1)
%
%  Modifies tank_level_observed during the attack window.
%  Flow telemetry (q_in, q_out) and actuator states remain uncompromised.
%
%  Variants:
%    'bias'         - H_fake = H_actual + b
%    'scale'        - H_fake = alpha * H_actual
%    'intermittent' - Bias applied every 5th step
%
%  Usage:
%    telemetry = apply_fdi(telemetry, attack_cfg);

function telemetry = apply_fdi(telemetry, attack_cfg)

    n = height(telemetry);
    t = telemetry.simulation_time_s;

    for k = 1:n
        if t(k) >= attack_cfg.attack_start && t(k) <= attack_cfg.attack_end

            switch attack_cfg.parameter_type
                case 'bias'
                    telemetry.tank_level_observed(k) = ...
                        telemetry.tank_level_observed(k) + attack_cfg.parameter_value;

                case 'scale'
                    telemetry.tank_level_observed(k) = ...
                        telemetry.tank_level_observed(k) * attack_cfg.parameter_value;

                case 'intermittent'
                    % Apply bias every 5th step within attack window
                    step_in_attack = round((t(k) - attack_cfg.attack_start) / 1.0);
                    if mod(step_in_attack, 5) == 0
                        telemetry.tank_level_observed(k) = ...
                            telemetry.tank_level_observed(k) + attack_cfg.parameter_value;
                    else
                        continue;  % No modification this step
                    end
            end

            % Mark as attack
            telemetry.attack_type{k}      = 'FDI';
            telemetry.attack_parameter(k) = attack_cfg.parameter_value;
            telemetry.ground_truth(k)     = 1;
        end
    end
end
