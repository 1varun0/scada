# Source File Note: matlab/scada_simulink_guide.m

## 1. Purpose
Provides documentation and a programmatic helper function (`create_simulink_model`) for constructing an equivalent Simulink block diagram (`scada_tank_model.slx`) of the single-tank water SCADA simulation [CODE matlab/scada_simulink_guide.m:1-8].

## 2. Public Classes / Functions
- `function create_simulink_model()` [CODE matlab/scada_simulink_guide.m:97-153]: Creates and configures a Simulink model file (`scada_tank_model.slx`) containing basic blocks (Integrator, Gain 1/A, Saturation, Flow Sum, Pump Constant, Relay Controller, To Workspace, Scope) with solver `ode4` and fixed step 1.0 s.

## 3. Inputs and Outputs
- **Inputs**: None.
- **Outputs**: Generates/saves Simulink model file `scada_tank_model.slx` if run inside MATLAB with Simulink installed.

## 4. Config Keys or Constants Read
- Hardcoded physical constants matching `scada_params.m`: $A = 2.0$, $H \in [0, 2.5]$, $Q_{max} = 0.005$, Relay on 0.8 / off 1.2, stop time 1000, fixed step 1.0 s.

## 5. Who Calls It
- Not called by any pipeline script or Python code. It is an auxiliary guide/script for visual model generation.

## 6. Side Effects
- Creates `scada_tank_model.slx` when invoked.

## 7. Tests Covering It
- None.

## 8. Surprises, Mismatches, or Dead Code
- Line 84 states: "The MATLAB script (run_all_scenarios.m) is the primary data generator because it can batch-run 170 scenarios" [CODE matlab/scada_simulink_guide.m:84], which repeats the legacy "170 scenarios" comment despite the actual generator creating 150 scenarios.
- The programmatic generator creates the blocks but does not add line connections (`add_line`), leaving the blocks unconnected ("Open it, connect the blocks, and rearrange as needed" [CODE matlab/scada_simulink_guide.m:152]).
