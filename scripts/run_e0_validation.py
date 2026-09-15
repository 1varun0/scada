"""
SCADA IDS — E0 Validation: Digital Twin vs Physical Simulator

Phase 1 Gate: This experiment must pass before any Phase 2 (attack) or
Phase 3 (AI/ML) work begins.

The E0 experiment validates that the Digital Twin's predicted level
(H_twin) tracks the true physical level (H_true) under normal noisy
conditions. It runs multiple normal scenarios with varied setpoint
profiles and computes:

    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Squared Error)
    - 95th percentile absolute residual
    - 99th percentile absolute residual
    - Maximum absolute residual
    - Residual distribution characteristics

Pass criterion: MAE < 0.02 m, residual distribution approximately Gaussian.

Usage:
    python scripts/run_e0_validation.py
"""

import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.parameters import PARAMS
from config.scenarios import generate_normal_scenarios, SetpointProfile
from simulator.process_simulator import ProcessSimulator
from digital_twin.physics_twin import PhysicsTwin


def run_e0_validation(num_scenarios: int = 15, verbose: bool = True) -> dict:
    """Run the E0 Twin validation experiment.

    For each normal scenario:
    1. Run the process simulator (which produces true + noisy values)
    2. Initialize the Digital Twin at H_true(0)
    3. Step the Twin using the reported (noisy) Q_in and Q_out
    4. Compare H_twin(t) against H_true(t) at each step

    Note: We compare against H_true, NOT H_observed, because
    H_observed includes sensor noise. The residual in production
    will be H_observed - H_twin, but for E0 we verify the Twin's
    physics accuracy against the noise-free ground truth.

    Args:
        num_scenarios: Number of normal scenarios to run.
        verbose: Whether to print progress.

    Returns:
        dict with MAE, RMSE, percentiles, and raw residuals.
    """
    scenarios = generate_normal_scenarios()[:num_scenarios]
    all_residuals = []

    for i, scenario in enumerate(scenarios):
        if verbose:
            print(f"  Running scenario {scenario.scenario_id} "
                  f"({i+1}/{len(scenarios)})...")

        # Run the process simulator
        sim = ProcessSimulator(scenario)
        records = sim.run()

        # Initialize the Twin at the true initial level
        true_initial = records[0]["_true_level"]
        twin = PhysicsTwin(
            initial_level_m=true_initial,
            area_m2=PARAMS.tank.cross_section_area_m2,
            max_height_m=PARAMS.tank.max_height_m,
        )

        scenario_residuals = []
        for j, record in enumerate(records):
            # Step the Twin using REPORTED (noisy) flows
            # This matches the production pipeline where the Twin
            # receives the same flow measurements as the detector
            q_in = record["q_in"]      # Noisy
            q_out = record["q_out"]    # Noisy
            dt = PARAMS.simulation.dt_s

            if j > 0:  # Don't step at t=0 (already initialized)
                twin.step(q_in, q_out, dt)

            # Compare Twin prediction against TRUE level
            h_true = record["_true_level"]
            h_twin = twin.level
            residual = h_true - h_twin
            scenario_residuals.append(residual)

        all_residuals.extend(scenario_residuals)

    # Compute metrics
    residuals = np.array(all_residuals)
    abs_residuals = np.abs(residuals)

    results = {
        "num_scenarios": len(scenarios),
        "num_samples": len(residuals),
        "mae": float(np.mean(abs_residuals)),
        "rmse": float(np.sqrt(np.mean(residuals**2))),
        "p95": float(np.percentile(abs_residuals, 95)),
        "p99": float(np.percentile(abs_residuals, 99)),
        "max_error": float(np.max(abs_residuals)),
        "mean_residual": float(np.mean(residuals)),
        "std_residual": float(np.std(residuals)),
        "residuals": residuals,
    }

    return results


def print_report(results: dict) -> None:
    """Print a formatted E0 validation report."""
    print("\n" + "=" * 60)
    print("  E0 VALIDATION REPORT — Digital Twin vs True Physics")
    print("=" * 60)
    print(f"  Scenarios tested:     {results['num_scenarios']}")
    print(f"  Total samples:        {results['num_samples']}")
    print("-" * 60)
    print(f"  MAE:                  {results['mae']:.6f} m")
    print(f"  RMSE:                 {results['rmse']:.6f} m")
    print(f"  95th percentile:      {results['p95']:.6f} m")
    print(f"  99th percentile:      {results['p99']:.6f} m")
    print(f"  Max absolute error:   {results['max_error']:.6f} m")
    print(f"  Mean residual:        {results['mean_residual']:.6f} m")
    print(f"  Std residual:         {results['std_residual']:.6f} m")
    print("-" * 60)

    # Pass/fail criterion
    passed = results['mae'] < 0.02
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  Pass criterion (MAE < 0.02 m): {status}")
    print("=" * 60)

    if passed:
        print("\n  E0 PASSED -- Phase 2 is unblocked.")
        print(f"  Suggested physics threshold (tau_p): {results['p99']:.4f} m")
        print(f"  (Based on 99th percentile of normal residuals)")
    else:
        print("\n  E0 FAILED — Investigate Twin physics before proceeding.")

    return passed


def save_plot(results: dict, output_path: str = None) -> None:
    """Save the residual distribution plot."""
    try:
        import matplotlib.pyplot as plt

        if output_path is None:
            output_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "e0_residual_distribution.png"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Histogram
        axes[0].hist(results['residuals'], bins=50, density=True,
                     alpha=0.7, color='steelblue', edgecolor='white')
        axes[0].axvline(0, color='red', linestyle='--', alpha=0.8, label='Zero')
        axes[0].set_xlabel('Residual (H_true - H_twin) [m]')
        axes[0].set_ylabel('Density')
        axes[0].set_title('E0: Twin Residual Distribution')
        axes[0].legend()

        # Time series of absolute residuals
        abs_res = np.abs(results['residuals'])
        axes[1].plot(abs_res, alpha=0.5, linewidth=0.5, color='steelblue')
        axes[1].axhline(results['p95'], color='orange', linestyle='--',
                        label=f"P95 = {results['p95']:.4f} m")
        axes[1].axhline(results['p99'], color='red', linestyle='--',
                        label=f"P99 = {results['p99']:.4f} m")
        axes[1].set_xlabel('Sample Index')
        axes[1].set_ylabel('|Residual| [m]')
        axes[1].set_title('E0: Absolute Residual Over Time')
        axes[1].legend()

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n  Plot saved to: {output_path}")
        plt.close()
    except ImportError:
        print("\n  matplotlib not available — skipping plot.")


if __name__ == "__main__":
    print("SCADA IDS — E0 Twin Validation")
    print("Running normal scenarios to validate Digital Twin accuracy...\n")

    results = run_e0_validation(num_scenarios=15, verbose=True)
    passed = print_report(results)
    save_plot(results)

    sys.exit(0 if passed else 1)
