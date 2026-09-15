"""
SCADA IDS — SQLite Storage Client

WAL-mode SQLite database for storing SCADA telemetry, attack scenario
metadata, experiment runs, and evaluation results.

Tables:
    scada_telemetry     — Raw process observations (one row per timestep)
    attack_scenarios    — Ground-truth attack configuration
    experiment_runs     — Model/experiment configuration & metadata
    evaluation_results  — Per-timestep predictions & scores
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Default database path
_DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "scada_ids.db")


class SCADADatabase:
    """SQLite WAL-mode database for the SCADA IDS project.

    Usage:
        db = SCADADatabase()
        db.initialize()
        db.insert_telemetry_batch(records)
        results = db.query_telemetry(scenario_id="N_001")
        db.close()

    Or as a context manager:
        with SCADADatabase() as db:
            db.insert_telemetry_batch(records)
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or _DEFAULT_DB_PATH

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None

    # ── Connection Management ────────────────────────────────────────

    def connect(self) -> None:
        """Open the database connection and enable WAL mode."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    # ── Schema Initialization ────────────────────────────────────────

    def initialize(self) -> None:
        """Create all tables and indexes if they don't exist."""
        conn = self.connection
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scada_telemetry (
                scenario_id TEXT NOT NULL,
                sequence_id INTEGER NOT NULL,
                simulation_time_s REAL NOT NULL,
                source_time_s REAL NOT NULL,
                data_age_ms INTEGER NOT NULL,
                packet_received INTEGER NOT NULL,
                communication_status TEXT NOT NULL,
                operating_condition TEXT NOT NULL,
                tank_level_setpoint REAL NOT NULL,
                tank_level_observed REAL NOT NULL,
                q_in REAL NOT NULL,
                q_out REAL NOT NULL,
                pump_command INTEGER NOT NULL,
                pump_state INTEGER NOT NULL,
                valve_command REAL NOT NULL,
                valve_state REAL NOT NULL,
                control_command TEXT,
                user_id TEXT,
                user_role TEXT,
                is_authenticated INTEGER,
                is_authorized INTEGER,
                attack_type TEXT NOT NULL DEFAULT 'None',
                attack_parameter REAL,
                ground_truth INTEGER NOT NULL DEFAULT 0,
                replay_source_sequence_id INTEGER,
                PRIMARY KEY (scenario_id, sequence_id)
            );

            CREATE INDEX IF NOT EXISTS idx_telemetry_scenario
                ON scada_telemetry(scenario_id);
            CREATE INDEX IF NOT EXISTS idx_telemetry_attack
                ON scada_telemetry(attack_type);

            CREATE TABLE IF NOT EXISTS attack_scenarios (
                scenario_id TEXT NOT NULL,
                attack_id TEXT NOT NULL PRIMARY KEY,
                attack_type TEXT NOT NULL,
                attack_start_time_s REAL,
                attack_end_time_s REAL,
                attack_parameter_type TEXT,
                attack_parameter_value REAL,
                random_seed INTEGER NOT NULL,
                description TEXT,
                operating_condition TEXT,
                initial_tank_level REAL
            );

            CREATE TABLE IF NOT EXISTS experiment_runs (
                experiment_id TEXT PRIMARY KEY,
                model_version TEXT,
                feature_version TEXT,
                threshold_version TEXT,
                fusion_version TEXT,
                training_scenario_ids TEXT,
                validation_scenario_ids TEXT,
                test_scenario_ids TEXT,
                hyperparameters TEXT,
                thresholds TEXT,
                fusion_weights TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evaluation_results (
                experiment_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                sequence_id INTEGER NOT NULL,
                simulation_time_s REAL NOT NULL,
                h_twin REAL,
                physics_residual REAL,
                S_p REAL,
                lstm_reconstruction_error REAL,
                S_l REAL,
                S_c REAL,
                S_a REAL,
                S_hybrid REAL,
                predicted_anomaly INTEGER,
                ground_truth INTEGER,
                PRIMARY KEY (experiment_id, scenario_id, sequence_id),
                FOREIGN KEY (experiment_id) REFERENCES experiment_runs(experiment_id),
                FOREIGN KEY (scenario_id, sequence_id)
                    REFERENCES scada_telemetry(scenario_id, sequence_id)
            );
        """)
        conn.commit()

    # ── Telemetry CRUD ───────────────────────────────────────────────

    _TELEMETRY_COLUMNS = [
        "scenario_id", "sequence_id", "simulation_time_s", "source_time_s",
        "data_age_ms", "packet_received", "communication_status",
        "operating_condition", "tank_level_setpoint", "tank_level_observed",
        "q_in", "q_out", "pump_command", "pump_state", "valve_command",
        "valve_state", "control_command", "user_id", "user_role",
        "is_authenticated", "is_authorized", "attack_type",
        "attack_parameter", "ground_truth", "replay_source_sequence_id",
    ]

    def insert_telemetry_batch(self, records: List[Dict[str, Any]]) -> None:
        """Bulk insert telemetry records using executemany."""
        if not records:
            return

        placeholders = ", ".join(["?"] * len(self._TELEMETRY_COLUMNS))
        sql = f"""
            INSERT OR REPLACE INTO scada_telemetry
            ({', '.join(self._TELEMETRY_COLUMNS)})
            VALUES ({placeholders})
        """

        rows = []
        for r in records:
            row = tuple(r.get(col) for col in self._TELEMETRY_COLUMNS)
            rows.append(row)

        self.connection.executemany(sql, rows)
        self.connection.commit()

    def query_telemetry(
        self,
        scenario_id: Optional[str] = None,
        attack_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Query telemetry records with optional filters.

        Returns:
            List of dicts, one per row.
        """
        sql = "SELECT * FROM scada_telemetry WHERE 1=1"
        params: List[Any] = []

        if scenario_id:
            sql += " AND scenario_id = ?"
            params.append(scenario_id)
        if attack_type:
            sql += " AND attack_type = ?"
            params.append(attack_type)

        sql += " ORDER BY scenario_id, sequence_id"

        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        cursor = self.connection.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_scenario_ids(self, attack_type: Optional[str] = None) -> List[str]:
        """Get distinct scenario IDs, optionally filtered by attack type."""
        sql = "SELECT DISTINCT scenario_id FROM scada_telemetry"
        params: List[Any] = []

        if attack_type:
            sql += " WHERE attack_type = ?"
            params.append(attack_type)

        sql += " ORDER BY scenario_id"
        cursor = self.connection.execute(sql, params)
        return [row[0] for row in cursor.fetchall()]

    def count_records(self, scenario_id: Optional[str] = None) -> int:
        """Count telemetry records."""
        sql = "SELECT COUNT(*) FROM scada_telemetry"
        params: List[Any] = []
        if scenario_id:
            sql += " WHERE scenario_id = ?"
            params.append(scenario_id)
        return self.connection.execute(sql, params).fetchone()[0]

    # ── Attack Scenarios CRUD ────────────────────────────────────────

    _ATTACK_COLUMNS = [
        "scenario_id", "attack_id", "attack_type", "attack_start_time_s",
        "attack_end_time_s", "attack_parameter_type", "attack_parameter_value",
        "random_seed", "description", "operating_condition", "initial_tank_level",
    ]

    def insert_attack_scenario(self, record: Dict[str, Any]) -> None:
        """Insert a single attack scenario metadata record."""
        placeholders = ", ".join(["?"] * len(self._ATTACK_COLUMNS))
        sql = f"""
            INSERT OR REPLACE INTO attack_scenarios
            ({', '.join(self._ATTACK_COLUMNS)})
            VALUES ({placeholders})
        """
        row = tuple(record.get(col) for col in self._ATTACK_COLUMNS)
        self.connection.execute(sql, row)
        self.connection.commit()

    # ── Experiment Runs CRUD ─────────────────────────────────────────

    def insert_experiment_run(self, record: Dict[str, Any]) -> None:
        """Insert an experiment run configuration.

        JSON-serializable fields (lists, dicts) are automatically
        converted to JSON strings.
        """
        json_fields = [
            "training_scenario_ids", "validation_scenario_ids",
            "test_scenario_ids", "hyperparameters", "thresholds",
            "fusion_weights",
        ]
        processed = dict(record)
        for field in json_fields:
            if field in processed and not isinstance(processed[field], str):
                processed[field] = json.dumps(processed[field])

        columns = [
            "experiment_id", "model_version", "feature_version",
            "threshold_version", "fusion_version", "training_scenario_ids",
            "validation_scenario_ids", "test_scenario_ids",
            "hyperparameters", "thresholds", "fusion_weights", "created_at",
        ]
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"""
            INSERT OR REPLACE INTO experiment_runs
            ({', '.join(columns)})
            VALUES ({placeholders})
        """
        row = tuple(processed.get(col) for col in columns)
        self.connection.execute(sql, row)
        self.connection.commit()

    # ── Evaluation Results CRUD ──────────────────────────────────────

    _EVAL_COLUMNS = [
        "experiment_id", "scenario_id", "sequence_id", "simulation_time_s",
        "h_twin", "physics_residual", "S_p", "lstm_reconstruction_error",
        "S_l", "S_c", "S_a", "S_hybrid", "predicted_anomaly", "ground_truth",
    ]

    def insert_evaluation_batch(self, records: List[Dict[str, Any]]) -> None:
        """Bulk insert evaluation results."""
        if not records:
            return

        placeholders = ", ".join(["?"] * len(self._EVAL_COLUMNS))
        sql = f"""
            INSERT OR REPLACE INTO evaluation_results
            ({', '.join(self._EVAL_COLUMNS)})
            VALUES ({placeholders})
        """
        rows = [
            tuple(r.get(col) for col in self._EVAL_COLUMNS)
            for r in records
        ]
        self.connection.executemany(sql, rows)
        self.connection.commit()

    def query_evaluation(
        self,
        experiment_id: str,
        scenario_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query evaluation results for an experiment."""
        sql = "SELECT * FROM evaluation_results WHERE experiment_id = ?"
        params: List[Any] = [experiment_id]

        if scenario_id:
            sql += " AND scenario_id = ?"
            params.append(scenario_id)

        sql += " ORDER BY scenario_id, sequence_id"
        cursor = self.connection.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    # ── Utilities ────────────────────────────────────────────────────

    def clear_telemetry(self) -> None:
        """Delete all telemetry records (use with caution)."""
        self.connection.execute("DELETE FROM scada_telemetry")
        self.connection.commit()

    def clear_all(self) -> None:
        """Delete all data from all tables (use with caution)."""
        self.connection.executescript("""
            DELETE FROM evaluation_results;
            DELETE FROM experiment_runs;
            DELETE FROM attack_scenarios;
            DELETE FROM scada_telemetry;
        """)
        self.connection.commit()

    def get_wal_mode(self) -> str:
        """Check current journal mode (should return 'wal')."""
        cursor = self.connection.execute("PRAGMA journal_mode;")
        return cursor.fetchone()[0]
