"""
SCADA IDS — Scenario Runner

Batch execution engine: iterates scenario definitions, runs the
process simulator for each, and writes results to SQLite.
"""

from typing import List, Optional
from tqdm import tqdm

from config.scenarios import ScenarioConfig, generate_normal_scenarios, generate_attack_scenarios
from simulator.process_simulator import ProcessSimulator
from storage.sqlite_client import SCADADatabase


class ScenarioRunner:
    """Batch runner for generating telemetry data across multiple scenarios."""

    def __init__(self, db: SCADADatabase):
        self._db = db

    def run_scenarios(
        self,
        scenarios: List[ScenarioConfig],
        show_progress: bool = True,
    ) -> int:
        """Run a list of scenarios and store telemetry in the database.

        Args:
            scenarios: List of scenario configurations to run.
            show_progress: Whether to show a tqdm progress bar.

        Returns:
            Total number of telemetry records generated.
        """
        total_records = 0
        iterator = tqdm(scenarios, desc="Running scenarios") if show_progress else scenarios

        for scenario in iterator:
            sim = ProcessSimulator(scenario)
            records = sim.run()

            # Strip internal fields (prefixed with _) before storage
            clean_records = []
            for r in records:
                clean = {k: v for k, v in r.items() if not k.startswith("_")}
                clean_records.append(clean)

            self._db.insert_telemetry_batch(clean_records)

            # Also insert attack scenario metadata if applicable
            if scenario.is_attack:
                self._db.insert_attack_scenario({
                    "scenario_id": scenario.scenario_id,
                    "attack_id": scenario.attack.attack_id,
                    "attack_type": scenario.attack.attack_type,
                    "attack_start_time_s": scenario.attack.attack_start_s,
                    "attack_end_time_s": scenario.attack.attack_end_s,
                    "attack_parameter_type": scenario.attack.parameter_type,
                    "attack_parameter_value": scenario.attack.parameter_value,
                    "random_seed": scenario.random_seed,
                    "description": scenario.attack.description,
                    "operating_condition": scenario.operating_condition,
                    "initial_tank_level": scenario.initial_level_m,
                })

            total_records += len(records)

        return total_records

    def run_normal(self, show_progress: bool = True) -> int:
        """Generate all normal scenario data."""
        return self.run_scenarios(generate_normal_scenarios(), show_progress)

    def run_attacks(self, show_progress: bool = True) -> int:
        """Generate all attack scenario data (base telemetry only).

        Note: This runs the base simulator — attack modifications must
        be applied separately by the attack modules.
        """
        return self.run_scenarios(generate_attack_scenarios(), show_progress)
