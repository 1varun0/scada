from dataclasses import replace
import threading
import os
import time
import pickle
import torch
from config.parameters import PARAMS
from simulator.controller import Controller
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.scada_ids.alert_manager import AlertManager
from scada_live.scada_ids.metrics import MetricsCollector
from scada_live.scada_ids.db_writer import DBWriter

def build_controller(cfg):
    """Builds a controller exactly as ProcessSimulator does."""
    return Controller(
        setpoint_m=PARAMS.controller.setpoint_m, 
        deadband_m=PARAMS.controller.deadband_m, 
        default_valve_pct=PARAMS.controller.default_valve_pct
    )

class GatewayCore:
    def __init__(self, cfg, sse_hub):
        self.cfg = cfg
        self.sse_hub = sse_hub
        self.lock = threading.RLock()
        
        self.ids = StreamingIDS(cfg, policy_version="v2")
        self.controller = build_controller(cfg)
        
        self.current_run_id = None
        self.last_rx_wall = time.monotonic()
        self.last_pkt = None
        
        self.alert_manager = AlertManager(cfg)
        self.metrics = MetricsCollector(grace_period_s=10.0)
        self.db_writer = DBWriter("data/live_run.db")
        self.events = []
        self.event_counter = 1
        
        self.watchdog_enabled = cfg.gateway.watchdog_enabled
        self.watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self.watchdog_thread.start()

    def _watchdog_loop(self):
        while True:
            time.sleep(self.cfg.simulation.dt_s / 2) # Check frequently
            if not self.watchdog_enabled:
                continue
            self.check_watchdog(time.monotonic())

    def check_watchdog(self, current_time: float):
        with self.lock:
            if self.last_pkt is None:
                return
            
            time_scale = getattr(self.cfg.simulation, "time_scale", 1.0)
            timeout_s = self.cfg.gateway.watchdog_factor * (self.cfg.simulation.dt_s / time_scale)

            if current_time - self.last_rx_wall > timeout_s:
                try:
                    synth_pkt = replace(self.last_pkt, 
                                        seq=self.last_pkt.seq + 1,
                                        ts=self.last_pkt.ts + self.cfg.simulation.dt_s,
                                        received=False,
                                        q_in=0.0,
                                        q_out=0.0,
                                        pump_cmd=0,
                                        valve_cmd=0.0,
                                        pump_on=False,
                                        valve_pct=0.0)
                    
                    verdict = self._enrich_and_publish(synth_pkt)
                    self.last_rx_wall = current_time
                except Exception as e:
                    print(f"Watchdog exception: {e}")

    def reset(self, initial_level_m: float, run_id: str):
        """Reset the IDS and the controller memory."""
        with self.lock:
            self.ids.reset(initial_level_m, run_id)
            self.controller = build_controller(self.cfg)
            self.alert_manager.reset()
            self.metrics.reset()
            self.events = []
            self.level_buffer = []
            self.current_run_id = run_id
            self.last_pkt = None
            
    def recalibrate(self) -> dict:
        """Soft reset based on recent trusted readings. Returns status dict."""
        with self.lock:
            n_samples = getattr(self.cfg.gateway, "recalibrate_samples", 10)
            if len(self.level_buffer) < n_samples:
                return {"error": "sensor_unstable", "reason": "Not enough samples"}
                
            levels = self.level_buffer[-n_samples:]
            
            # Check physical bounds
            if any(l < 0 or l > getattr(self.cfg.tank, "max_level_m", 2.0) for l in levels):
                return {"error": "sensor_unstable", "reason": "Out of bounds"}
                
            # Check stability (std deviation)
            mean = sum(levels) / len(levels)
            variance = sum((l - mean) ** 2 for l in levels) / len(levels)
            std = variance ** 0.5
            
            if std > getattr(self.cfg.gateway, "max_std_m", 0.05):
                return {"error": "sensor_unstable", "reason": "Level is mid-ramp (std too high)"}
                
            self.ids.recalibrate(levels)
            return {"status": "ok"}
            
    def process_sense(self, level_m: float) -> dict:
        """Handle /api/sense: return pump/valve commands."""
        with self.lock:
            if not hasattr(self, 'level_buffer'):
                self.level_buffer = []
            self.level_buffer.append(level_m)
            # keep reasonable buffer
            if len(self.level_buffer) > 50:
                self.level_buffer.pop(0)
                
            ctrl_cmds = self.controller.step(level_m)
            return {
                "pump_cmd": ctrl_cmds['pump_command'],
                "valve_cmd": ctrl_cmds['valve_command']
            }
            
    def process_telemetry(self, pkt) -> dict:
        """Handle /api/telemetry: evaluate packet and publish SSE."""
        with self.lock:
            # Detect run change FIRST
            if pkt.run_id != self.current_run_id:
                self.reset(self.cfg.tank.initial_level_m, pkt.run_id)
                
            if self.last_pkt is not None and pkt.seq <= self.last_pkt.seq:
                # Discard old packets
                return {"dropped": True}
                
            verdict = self._enrich_and_publish(pkt)
            self.last_pkt = pkt
            self.last_rx_wall = time.monotonic()
            return verdict
            
    def _enrich_and_publish(self, pkt):
        verdict = self.ids.update(pkt)
        
        # Check stale
        stale = False
        if self.last_pkt is not None and pkt.src_t <= self.last_pkt.src_t:
            stale = True
            
        # Alert Manager
        am_state = self.alert_manager.update(
            seq=pkt.seq,
            ts=pkt.ts,
            is_anomaly=verdict["is_anomaly"],
            engines_firing=verdict["engines_firing"],
            received=pkt.received,
            stale=stale,
            hybrid_score=verdict["hybrid"]
        )
        
        # Enrich verdict
        verdict.update(am_state)
        # Assuming calibrating is True during the warm-up
        recalibrating = verdict.get("calibrating", False)
        
        # Metrics
        self.metrics.update_verdict(
            run_id=pkt.run_id,
            seq=pkt.seq,
            ts=pkt.ts,
            is_anomaly=verdict["is_anomaly"],
            alert_state=verdict["alert_state"],
            recalibrating=recalibrating
        )
        
        # Simple Event log tracking for now
        event_dict = None
        if verdict["alert_state"] == "CRITICAL":
            event_dict = {
                "event_id": self.event_counter,
                "run_id": pkt.run_id,
                "seq": pkt.seq,
                "ts": pkt.ts,
                "attack_type": verdict["attack_type"]
            }
            self.events.append(event_dict)
            self.db_writer.write_event(event_dict)
            self.event_counter += 1
            
        tick_dict = {
            "run_id": pkt.run_id,
            "seq": pkt.seq,
            "ts": pkt.ts,
            "level_obs": verdict.get("level_obs", 0.0),
            "level_twin": verdict.get("level_twin", 0.0),
            "is_anomaly": verdict["is_anomaly"],
            "alert_state": verdict["alert_state"]
        }
        self.db_writer.write_tick(tick_dict)
            
        self.alert_manager.history.append(verdict)
        self.sse_hub.publish(verdict)
        return verdict
        
    def process_truth(self, run_id: str, seq: int, ts: float, true_level: float, attack_active: bool, attack_type: str, overflow: bool, dry_run: bool):
        with self.lock:
            self.metrics.update_truth(run_id, seq, ts, true_level, attack_active, attack_type, overflow, dry_run)
            
    def acknowledge(self, recalibrate: bool, ts: float):
        with self.lock:
            self.alert_manager.acknowledge()
            self.metrics.record_ack(recalibrate, ts)
