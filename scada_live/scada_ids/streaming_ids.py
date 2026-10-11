"""
StreamingIDS — Stateful wrapper around the 4 anomaly detection engines.
"""

import numpy as np
import os
import torch
import pandas as pd
from collections import deque
import pickle
import threading
import logging

logger = logging.getLogger(__name__)

from engines.physics_engine import PhysicsEngine
from engines.temporal_engine import TemporalEngine
from engines.policy_engine import PolicyEngine
from engines.availability_engine import AvailabilityEngine
from engines.fusion_engine import FusionEngine
from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import DataPreprocessor
from scada_live.common.packets import TelemetryPacket
from scada_live.common.config_loader import load_config

class StreamingIDS:
    def __init__(self, cfg, device="cpu", policy_version=None, dos_gap_rule=None):
        self.cfg = cfg
        self.device = device
        if policy_version is not None:
            self.policy_version = policy_version
        elif hasattr(cfg, "ids") and hasattr(cfg.ids, "policy_version"):
            self.policy_version = cfg.ids.policy_version
        else:
            self.policy_version = "v1"
            
        if dos_gap_rule is not None:
            self.dos_gap_rule = bool(dos_gap_rule)
        elif hasattr(cfg, "ids") and hasattr(cfg.ids, "dos_gap_rule"):
            self.dos_gap_rule = bool(cfg.ids.dos_gap_rule)
        else:
            self.dos_gap_rule = False

        self.current_run_id = None
        self.lock = threading.RLock()

        # Step 2b: DoS gap tracking state
        self.gap_ticks = 0
        self.reseed_buffer = []
        self.is_collecting_reseed = False
        self.reseed_gap_length = 0
        self.reseed_collect_ticks = 0
        self.suppress_physics_takeover = False
        ids_cfg = getattr(cfg, "ids", None)
        self.gap_collect_timeout_ticks = int(getattr(ids_cfg, "gap_collect_timeout_ticks", 20)) if ids_cfg else 20
        
        # Physical constants for Step 2b v_max derivation
        area = float(getattr(cfg.tank, "cross_section_area_m2", 2.0))
        q_in_max = float(getattr(cfg.pump, "q_max_m3s", 0.005))
        cv = float(getattr(cfg.valve, "flow_coefficient_m3s", 0.004))
        h_max = float(getattr(cfg.tank, "max_height_m", 2.5))
        self.v_max = max(q_in_max / area, cv * (h_max ** 0.5) / area)
        self.sigma_sensor = float(getattr(cfg.simulation, "sensor_noise_level_m", 0.005))
        recal_cfg = getattr(cfg, "recalibration", None)
        self.max_std_m = float(getattr(recal_cfg, "max_std_m", 0.03)) if recal_cfg else 0.03
        
        # 1. Physics Engine
        self.physics_engine = PhysicsEngine(tau_p=cfg.ids.tau_p)
        self.physics_engine.reset(cfg.tank.initial_level_m)
        
        # 2. Policy Engine
        self.policy_engine = PolicyEngine(epsilon_m=cfg.ids.epsilon_m)
        
        # 3. Availability Engine
        self.availability_engine = AvailabilityEngine(
            tau_a_ms=cfg.ids.tau_a_ms, tau_a_max_ms=cfg.ids.tau_a_max_ms
        )
        
        # 4. Temporal Engine
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Preprocessor loading matching run_evaluation.py
        self.preprocessor = DataPreprocessor(window_size=cfg.ids.lstm_window)
        scaler_path = os.path.join(base_dir, cfg.lstm.scaler_path)
        with open(scaler_path, "rb") as f:
            self.preprocessor.scaler = pickle.load(f)
        self.preprocessor.is_fitted = True
        
        self.lstm_model = LSTMAutoencoder(
            input_dim=cfg.lstm.input_dim,
            hidden_dim=cfg.lstm.hidden_dim,
            num_layers=cfg.lstm.num_layers
        )
        weights_path = os.path.join(base_dir, cfg.lstm.weights_path)
        self.lstm_model.load_state_dict(torch.load(weights_path, map_location=device, weights_only=True))
        self.lstm_model.eval()
        
        self.temporal_engine = TemporalEngine(
            model=self.lstm_model, preprocessor=self.preprocessor, 
            tau_l=cfg.ids.tau_l, device=device
        )
        
        self.window_size = cfg.ids.lstm_window
        self.telemetry_window = deque(maxlen=self.window_size)
        
        # 5. Fusion Engine
        self.fusion_engine = FusionEngine(
            w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25,
            tau_fusion=cfg.ids.tau_fusion, strategy="max_vote"
        )
        self.nan_guard_triggers = 0
        
    def reset(self, initial_level_m: float, run_id: str):
        """Hard reset for a new scenario run."""
        with self.lock:
            self.physics_engine.reset(initial_level_m)
            self.telemetry_window.clear()
            self.current_run_id = run_id
            self.gap_ticks = 0
            self.reseed_buffer.clear()
            self.is_collecting_reseed = False
            self.reseed_gap_length = 0
            self.reseed_collect_ticks = 0
            self.suppress_physics_takeover = False
            
            # Note: AvailabilityEngine does not have internal state to reset.
            # It just evaluates (sim_t - src_t). PolicyEngine is also stateless.
        
    def recalibrate(self, trusted_levels: list[float]):
        """Soft reset based on recent trusted readings."""
        with self.lock:
            if not trusted_levels:
                return
            mean_level = sum(trusted_levels) / len(trusted_levels)
            self.physics_engine.reset(mean_level)
            self.telemetry_window.clear()

    def get_twin_estimate(self) -> float:
        """Return the current water level estimate from the physics Digital Twin."""
        with self.lock:
            if self.physics_engine.twin is not None:
                return float(self.physics_engine.twin.level)
            return float(self.cfg.tank.initial_level_m)


    @torch.no_grad()
    def update(self, pkt: TelemetryPacket) -> dict:
        with self.lock:
            # Detect scenario boundaries
            if self.current_run_id != pkt.run_id:
                # Fallback reset if not explicitly reset by caller
                self.physics_engine.reset(self.cfg.tank.initial_level_m)
                self.telemetry_window.clear()
                self.current_run_id = pkt.run_id
                self.gap_ticks = 0
                self.reseed_buffer.clear()
                self.is_collecting_reseed = False
                self.reseed_gap_length = 0
                self.reseed_collect_ticks = 0
                self.suppress_physics_takeover = False
                
            # Sanitize inputs to guarantee finite scores and equivalence to batch rows
            is_rx = bool(pkt.received)
            level_m = float(pkt.level_m) if (pkt.level_m is not None and not pd.isna(pkt.level_m)) else 0.0
            
            # Step 2b DoS gap rule evaluation
            self.suppress_physics_takeover = False
            if self.dos_gap_rule:
                if not is_rx:
                    self.gap_ticks += 1
                    self.is_collecting_reseed = False
                    self.reseed_buffer.clear()
                    self.reseed_collect_ticks = 0
                else:
                    if self.gap_ticks > 0:
                        self.reseed_gap_length = self.gap_ticks
                        self.gap_ticks = 0
                        self.is_collecting_reseed = True
                        self.reseed_buffer = []
                        self.reseed_collect_ticks = 0
                    
                    if self.is_collecting_reseed:
                        self.reseed_collect_ticks += 1
                        if 0.0 <= level_m <= getattr(self.cfg.tank, "max_height_m", 2.5):
                            self.reseed_buffer.append(level_m)
                        self.suppress_physics_takeover = True
                        
                        if len(self.reseed_buffer) == 5:
                            m = float(np.median(self.reseed_buffer))
                            std_m = float(np.std(self.reseed_buffer, ddof=1)) if len(self.reseed_buffer) > 1 else 0.0
                            h_twin = self.get_twin_estimate()
                            G = self.reseed_gap_length
                            dt = float(getattr(self.cfg.simulation, "dt_s", 1.0))
                            band = self.v_max * G * dt + 3.0 * self.sigma_sensor
                            diff = abs(m - h_twin)
                            
                            if std_m <= self.max_std_m and diff <= band:
                                self.physics_engine.reset(m)
                                logger.info(
                                    f"[DoS-Gap Re-seed] Accepted: gap={G}, m={m:.4f}, twin={h_twin:.4f}, "
                                    f"diff={diff:.4f}, band={band:.4f}, std={std_m:.4f}"
                                )
                            else:
                                logger.warning(
                                    f"[DoS-Gap Refusal] Refused: gap={G}, m={m:.4f}, twin={h_twin:.4f}, "
                                    f"diff={diff:.4f}, band={band:.4f}, std={std_m:.4f}"
                                )
                                
                            self.is_collecting_reseed = False
                            self.reseed_buffer.clear()
                            self.reseed_collect_ticks = 0
                            self.suppress_physics_takeover = False
                        elif self.reseed_collect_ticks >= self.gap_collect_timeout_ticks:
                            logger.warning(
                                f"[DoS-Gap Timeout Refusal] Collection timed out after {self.reseed_collect_ticks} ticks "
                                f"with {len(self.reseed_buffer)} valid samples. Refusing re-seed."
                            )
                            self.is_collecting_reseed = False
                            self.reseed_buffer.clear()
                            self.reseed_collect_ticks = 0
                            self.suppress_physics_takeover = False

            # Missing packets carry zero flows and fail-safe states in batch rows
            if is_rx:
                q_in = float(pkt.q_in) if (pkt.q_in is not None and not pd.isna(pkt.q_in)) else 0.0
                q_out = float(pkt.q_out) if (pkt.q_out is not None and not pd.isna(pkt.q_out)) else 0.0
                pump_cmd = int(pkt.pump_cmd) if pkt.pump_cmd is not None else 0
                valve_cmd = float(pkt.valve_cmd) if (pkt.valve_cmd is not None and not pd.isna(pkt.valve_cmd)) else 0.0
                pump_state = 1.0 if (pkt.pump_on if pkt.pump_on is not None else False) else 0.0
                valve_state = float(pkt.valve_pct) if (pkt.valve_pct is not None and not pd.isna(pkt.valve_pct)) else 0.0
            else:
                q_in = 0.0
                q_out = 0.0
                pump_cmd = int(pkt.pump_cmd) if pkt.pump_cmd is not None else 0
                valve_cmd = float(pkt.valve_cmd) if (pkt.valve_cmd is not None and not pd.isna(pkt.valve_cmd)) else 0.0
                pump_state = 0.0
                valve_state = 0.0
                
            # 1. Physics Engine
            h_twin, p_residual, s_p = self.physics_engine.step(
                q_in=q_in, q_out=q_out, 
                h_observed=level_m, dt=self.cfg.simulation.dt_s
            )
            
            # 2. Availability Engine (using src_t)
            data_age, s_a = self.availability_engine.evaluate(
                simulation_time_s=pkt.ts, source_time_s=pkt.src_t, packet_received=is_rx
            )
            
            if self.policy_version == "v2":
                s_c = self.policy_engine.evaluate_v2(
                    h_observed=level_m, pump_command=pump_cmd, valve_command=valve_cmd
                )
            else:
                s_c = self.policy_engine.evaluate(
                    h_observed=level_m, pump_command=pump_cmd, valve_command=valve_cmd
                )
            
            # 4. Temporal Engine
            # Batch adds all rows to the window buffer. 
            self.telemetry_window.append({
                'tank_level_observed': level_m,
                'q_in': q_in,
                'q_out': q_out,
                'pump_state': pump_state,
                'valve_state': valve_state
            })
            
            s_l = 0.0
            calibrating = True
            if len(self.telemetry_window) == self.window_size:
                calibrating = False
                window_df = pd.DataFrame(list(self.telemetry_window))
                _, s_l = self.temporal_engine.evaluate(window_df)
                if pd.isna(s_l) or not np.isfinite(s_l):
                    self.nan_guard_triggers += 1
                    logger.warning(
                        f"NaN guard triggered on tick {pkt.seq}: s_l was {s_l}, defaulted to 0.0"
                    )
                    s_l = 0.0
                
            # 5. Fusion
            s_hybrid, predicted_anomaly = self.fusion_engine.evaluate(s_p, s_l, s_c, s_a)
            
            # Determine source engine (and engines firing)
            scores = {"physics": s_p, "lstm": s_l, "policy": s_c, "availability": s_a}
            engines_firing = [name for name, score in scores.items() if score > self.cfg.ids.tau_fusion]
            source_engine = max(scores, key=scores.get) if predicted_anomaly else None
            
            return {
                "t": pkt.seq,
                "run_id": pkt.run_id,
                "received": pkt.received,
                "level_obs": pkt.level_m,
                "level_twin": h_twin,
                "pump": pkt.pump_on,
                "scores": scores,
                "physics_residual": p_residual,
                "hybrid": s_hybrid,
                "is_anomaly": bool(predicted_anomaly),
                "calibrating": calibrating,
                "source_engine": source_engine,
                "engines_firing": engines_firing,
                "suppress_physics_takeover": self.suppress_physics_takeover
            }
