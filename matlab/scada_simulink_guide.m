%% SCADA_SIMULINK_GUIDE - How to Build the Simulink Model
%
%  This guide describes how to build the equivalent Simulink block
%  diagram for the single-tank water SCADA simulation.
%
%  The MATLAB script (run_single_scenario.m) is the PRIMARY data
%  generator. This Simulink model is the EQUIVALENT visual version
%  for academic presentation and documentation.
%
%  ================================================================
%  HOW TO BUILD THE SIMULINK MODEL
%  ================================================================
%
%  Step 1: Create a new Simulink model
%    >> simulink           % Opens Simulink start page
%    >> new_system('scada_tank_model')
%    >> open_system('scada_tank_model')
%
%  Step 2: Add these blocks from the Simulink Library Browser
%
%  ── TANK SUBSYSTEM ──────────────────────────────────────────────
%
%    [Sum]           → Computes (Q_in - Q_out)
%    [Gain: 1/A]     → Divides by cross-sectional area (1/2.0 = 0.5)
%    [Integrator]    → Integrates dH/dt to get H
%                      Set initial condition = 1.0 (H_0)
%    [Saturation]    → Clamps H to [0, 2.5] (physical bounds)
%
%    Wire: Q_in → (+)Sum(-)← Q_out → Gain(1/A) → Integrator → Saturation → H
%
%  ── PUMP SUBSYSTEM ──────────────────────────────────────────────
%
%    [Switch]        → Selects Q_max (0.005) or 0 based on pump_command
%    [Transport Delay] → 2.0 second delay (mechanical inertia)
%    [Constant: 0.005] → Q_max when ON
%    [Constant: 0]     → Zero flow when OFF
%
%  ── VALVE SUBSYSTEM ─────────────────────────────────────────────
%
%    [Product]       → Multiplies Cv * (V%/100)
%    [Sqrt]          → sqrt(H)
%    [Product]       → Multiplies above result * sqrt(H)
%    [Rate Limiter]  → Slew rate = 66.67 %/s (100/1.5)
%    [Constant: 0.004] → Flow coefficient Cv
%
%    Wire: V_cmd → Rate Limiter → /100 → Product(Cv) → Product(sqrt(H)) → Q_out
%
%  ── CONTROLLER SUBSYSTEM ────────────────────────────────────────
%
%    [Relay Block]   → Hysteresis controller
%                      Switch-on point:  0.8 (pump_on_thresh)
%                      Switch-off point: 1.2 (pump_off_thresh)
%                      Output when on:   1
%                      Output when off:  0
%    [Constant: 50]  → Default valve position
%
%  ── NOISE SUBSYSTEM ─────────────────────────────────────────────
%
%    [Band-Limited White Noise] → Noise power = sigma^2 * dt
%                                 For level: 0.005^2 * 1 = 2.5e-5
%                                 For flow:  0.0001^2 * 1 = 1e-8
%    [Sum]           → Adds noise to true measurements
%
%  ── SCOPES & LOGGING ────────────────────────────────────────────
%
%    [To Workspace]  → Logs H, Q_in, Q_out, pump_state, valve_state
%                      Set "Save format" = "Timeseries"
%    [Scope]         → Visual monitoring during simulation
%
%  Step 3: Configure Simulation Parameters
%    >> set_param('scada_tank_model', 'StopTime', '1000')
%    >> set_param('scada_tank_model', 'FixedStep', '1.0')
%    >> set_param('scada_tank_model', 'Solver', 'ode4')  % Fixed-step Runge-Kutta
%
%  Step 4: Run the simulation
%    >> sim('scada_tank_model')
%
%  ================================================================
%  IMPORTANT NOTES
%  ================================================================
%
%  1. The Simulink model is for VISUAL DOCUMENTATION and academic
%     presentation. The MATLAB script (run_all_scenarios.m) is the
%     primary data generator because it can batch-run 170 scenarios.
%
%  2. For your capstone report, include a screenshot of the Simulink
%     block diagram to show the physical system architecture.
%
%  3. Both the script and Simulink model use the SAME physics:
%     dH/dt = (Q_in - Q_out) / A
%     Q_out = Cv * (V%/100) * sqrt(H)
%
%  ================================================================
%  QUICK START: Create the model programmatically
%  ================================================================

function create_simulink_model()
    % This function creates a basic Simulink model programmatically.
    % You can then open it, rearrange blocks, and save.

    model = 'scada_tank_model';

    % Close if already open
    if bdIsLoaded(model)
        close_system(model, 0);
    end

    new_system(model);
    open_system(model);

    % ── Tank Integrator ──────────────────────────────────────────
    add_block('simulink/Continuous/Integrator', [model '/Tank_Level']);
    set_param([model '/Tank_Level'], 'InitialCondition', '1.0');

    % ── Gain (1/A) ───────────────────────────────────────────────
    add_block('simulink/Math Operations/Gain', [model '/Inv_Area']);
    set_param([model '/Inv_Area'], 'Gain', '0.5');  % 1/2.0

    % ── Saturation (physical bounds) ─────────────────────────────
    add_block('simulink/Discontinuities/Saturation', [model '/Level_Bounds']);
    set_param([model '/Level_Bounds'], 'UpperLimit', '2.5', 'LowerLimit', '0');

    % ── Sum (Q_in - Q_out) ───────────────────────────────────────
    add_block('simulink/Math Operations/Sum', [model '/Flow_Balance']);
    set_param([model '/Flow_Balance'], 'Inputs', '+-');

    % ── Pump constant ────────────────────────────────────────────
    add_block('simulink/Sources/Constant', [model '/Q_max']);
    set_param([model '/Q_max'], 'Value', '0.005');

    % ── Controller (Relay/Hysteresis) ────────────────────────────
    add_block('simulink/Discontinuities/Relay', [model '/Hysteresis_Ctrl']);
    set_param([model '/Hysteresis_Ctrl'], ...
        'OnSwitchValue', '0.8', 'OffSwitchValue', '1.2', ...
        'OnOutputValue', '1', 'OffOutputValue', '0');

    % ── To Workspace (logging) ───────────────────────────────────
    add_block('simulink/Sinks/To Workspace', [model '/Log_Level']);
    set_param([model '/Log_Level'], 'VariableName', 'tank_level', ...
        'SaveFormat', 'Timeseries');

    % ── Scope ────────────────────────────────────────────────────
    add_block('simulink/Sinks/Scope', [model '/Level_Scope']);

    % Set simulation parameters
    set_param(model, 'StopTime', '1000', 'FixedStep', '1.0', ...
        'Solver', 'ode4');

    % Save
    save_system(model);
    fprintf('Simulink model created: %s.slx\n', model);
    fprintf('Open it, connect the blocks, and rearrange as needed.\n');
end
