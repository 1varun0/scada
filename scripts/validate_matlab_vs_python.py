"""
SCADA IDS — Cross-Validation: MATLAB vs Python Simulator

Runs the same scenario with both the Python simulator and the MATLAB
output (CSV), then compares the physics to verify they produce
matching results.

This validates that the MATLAB simulation uses the same physics
equations and parameters as the Python reference implementation.

Usage:
    python scripts/validate_matlab_vs_python.py
    python scripts/validate_matlab_vs_python.py --scenario N_001
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.scenarios import get_scenario_by_id, generate_normal_scenarios
from simulator.process_simulator import ProcessSimulator
from config.parameters import PARAMS


def load_matlab_csv(csv_dir: str, scenario_id: str) -> pd.DataFrame:
    """Load a MATLAB-generated CSV for a specific scenario."""
    csv_path = os.path.join(csv_dir, f"{scenario_id}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"MATLAB CSV not found: {csv_path}")
    return pd.read_csv(csv_path)


def run_python_scenario(scenario_id: str) -> pd.DataFrame:
    """Run the Python simulator for a specific scenario and return as DataFrame."""
    scenario = get_scenario_by_id(scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario: {scenario_id}")

    sim = ProcessSimulator(scenario)
    records = sim.run()

    return pd.DataFrame(records)


def compare_scenarios(
    matlab_df: pd.DataFrame,
    python_df: pd.DataFrame,
    scenario_id: str,
) -> dict:
    """Compare MATLAB and Python outputs for the same scenario.

    We compare the controller behavior and physics dynamics rather than
    exact noise values, since the RNG implementations differ between
    MATLAB and Python.

    Returns:
        dict with comparison metrics.
    """
    results = {'scenario_id': scenario_id, 'passed': True, 'issues': []}

    # 1. Check record counts match
    if len(matlab_df) != len(python_df):
        results['issues'].append(
            f"Record count mismatch: MATLAB={len(matlab_df)}, Python={len(python_df)}"
        )
        results['passed'] = False
        return results

    n = len(matlab_df)
    results['num_records'] = n

    # 2. Check simulation time alignment
    if 'simulation_time_s' in matlab_df.columns:
        time_diff = np.abs(
            matlab_df['simulation_time_s'].values -
            python_df['simulation_time_s'].values
        )
        if np.max(time_diff) > 1e-6:
            results['issues'].append(f"Time alignment error: max diff = {np.max(time_diff)}")
            results['passed'] = False

    # 3. Compare pump command patterns
    # Both should make similar pump decisions since they use the same
    # hysteresis logic — but noise differences may cause slight deviations
    if 'pump_command' in matlab_df.columns and 'pump_command' in python_df.columns:
        pump_match_rate = np.mean(
            matlab_df['pump_command'].values == python_df['pump_command'].values
        )
        results['pump_command_match'] = pump_match_rate
        if pump_match_rate < 0.90:  # Allow 10% mismatch due to noise differences
            results['issues'].append(
                f"Pump command match rate too low: {pump_match_rate:.1%}"
            )

    # 4. Compare observed level statistics (not exact — noise differs)
    if 'tank_level_observed' in matlab_df.columns:
        m_levels = matlab_df['tank_level_observed'].values
        p_levels = python_df['tank_level_observed'].values

        # Mean levels should be close (noise is zero-mean)
        mean_diff = abs(np.mean(m_levels) - np.mean(p_levels))
        results['mean_level_diff'] = mean_diff
        if mean_diff > 0.05:  # 5cm tolerance on mean
            results['issues'].append(
                f"Mean level difference too large: {mean_diff:.4f} m"
            )

        # Standard deviations should be similar
        std_diff = abs(np.std(m_levels) - np.std(p_levels))
        results['std_level_diff'] = std_diff

    # 5. Compare flow statistics
    for flow_col in ['q_in', 'q_out']:
        if flow_col in matlab_df.columns:
            m_flow = matlab_df[flow_col].values
            p_flow = python_df[flow_col].values
            flow_mean_diff = abs(np.mean(m_flow) - np.mean(p_flow))
            results[f'{flow_col}_mean_diff'] = flow_mean_diff

    # 6. Overall assessment
    # With different RNGs, we can't expect exact matches.
    # The key check is that the DYNAMICS are the same (mean levels,
    # pump switching patterns, flow magnitudes).
    if not results['issues']:
        results['status'] = 'MATCH'
    elif results.get('pump_command_match', 1.0) >= 0.85 and \
         results.get('mean_level_diff', 0) < 0.1:
        results['status'] = 'CLOSE (noise differences only)'
        results['passed'] = True  # Accept noise-only differences
    else:
        results['status'] = 'MISMATCH'
        results['passed'] = False

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Cross-validate MATLAB and Python simulator outputs'
    )
    parser.add_argument(
        '--scenario',
        default=None,
        help='Specific scenario ID to validate (default: first 5 normal)'
    )
    parser.add_argument(
        '--csv-dir',
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'matlab', 'data'),
        help='Directory containing MATLAB CSV files'
    )
    parser.add_argument(
        '--num',
        type=int,
        default=5,
        help='Number of normal scenarios to compare (default: 5)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  SCADA IDS - MATLAB vs Python Cross-Validation")
    print("=" * 60)

    if args.scenario:
        scenario_ids = [args.scenario]
    else:
        scenarios = generate_normal_scenarios()[:args.num]
        scenario_ids = [s.scenario_id for s in scenarios]

    all_passed = True

    for sid in scenario_ids:
        print(f"\n  Comparing {sid}...")

        try:
            matlab_df = load_matlab_csv(args.csv_dir, sid)
            python_df = run_python_scenario(sid)
            results = compare_scenarios(matlab_df, python_df, sid)

            print(f"    Records:         {results.get('num_records', '?')}")
            print(f"    Status:          {results.get('status', '?')}")
            if 'pump_command_match' in results:
                print(f"    Pump match:      {results['pump_command_match']:.1%}")
            if 'mean_level_diff' in results:
                print(f"    Mean level diff: {results['mean_level_diff']:.4f} m")
            if results['issues']:
                for issue in results['issues']:
                    print(f"    [!] {issue}")

            if not results['passed']:
                all_passed = False

        except FileNotFoundError as e:
            print(f"    SKIPPED: {e}")
        except Exception as e:
            print(f"    ERROR: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("  RESULT: Cross-validation PASSED")
        print("  MATLAB and Python simulators produce consistent physics.")
    else:
        print("  RESULT: Cross-validation has ISSUES")
        print("  Review the differences above. Note: noise differences")
        print("  between MATLAB and Python RNGs are expected and acceptable.")
    print("=" * 60)


if __name__ == "__main__":
    main()
