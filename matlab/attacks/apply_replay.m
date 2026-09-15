%% APPLY_REPLAY - Replay Attack (A2)
%
%  Substitutes tank_level_observed with historical readings.
%  CRITICAL: Preserves the original source_time_s from the replayed
%  period so that data_age_ms correctly reflects the stale data.
%
%  The replay_source_sequence_id field records which original sequence_id
%  each replayed measurement came from (ground-truth metadata).
%
%  Usage:
%    telemetry = apply_replay(telemetry, attack_cfg);

function telemetry = apply_replay(telemetry, attack_cfg)

    n = height(telemetry);
    t = telemetry.simulation_time_s;
    dt = 1.0;  % Fixed timestep

    % Calculate replay buffer indices
    % The buffer captures readings from BEFORE the attack window
    buffer_duration_s = attack_cfg.replay_buffer_s;
    buffer_start_idx  = -1;
    attack_start_idx  = -1;
    attack_end_idx    = -1;

    % Find buffer and attack window indices
    for k = 1:n
        if buffer_start_idx == -1 && t(k) >= (attack_cfg.attack_start - buffer_duration_s)
            buffer_start_idx = k;
        end
        if attack_start_idx == -1 && t(k) >= attack_cfg.attack_start
            attack_start_idx = k;
        end
        if t(k) <= attack_cfg.attack_end
            attack_end_idx = k;
        end
    end

    if buffer_start_idx == -1 || attack_start_idx == -1
        warning('Replay attack: could not find valid indices. Skipping.');
        return;
    end

    % Extract the historical buffer
    buffer_len = attack_start_idx - buffer_start_idx;
    if buffer_len <= 0
        warning('Replay attack: buffer is empty. Skipping.');
        return;
    end

    buffer_levels     = telemetry.tank_level_observed(buffer_start_idx : attack_start_idx - 1);
    buffer_source_ts  = telemetry.source_time_s(buffer_start_idx : attack_start_idx - 1);
    buffer_seq_ids    = telemetry.sequence_id(buffer_start_idx : attack_start_idx - 1);

    % Apply replay: substitute readings within attack window
    for k = attack_start_idx : min(attack_end_idx, n)
        % Cycle through the buffer
        buf_idx = mod(k - attack_start_idx, buffer_len) + 1;

        % Replace observed level with historical value
        telemetry.tank_level_observed(k) = buffer_levels(buf_idx);

        % CRITICAL: Preserve the ORIGINAL source timestamp
        % This is what makes data_age_ms correctly detect the replay
        telemetry.source_time_s(k) = buffer_source_ts(buf_idx);

        % Recalculate data age from stale source timestamp
        telemetry.data_age_ms(k) = round((t(k) - buffer_source_ts(buf_idx)) * 1000);

        % Record which original sequence was replayed (ground truth)
        telemetry.replay_source_sequence_id(k) = buffer_seq_ids(buf_idx);

        % Mark as attack
        telemetry.attack_type{k}      = 'Replay';
        telemetry.attack_parameter(k) = attack_cfg.parameter_value;
        telemetry.ground_truth(k)     = 1;
    end
end
