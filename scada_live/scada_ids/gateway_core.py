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

def evaluate_command_with_live_setpoint(
    h_est: float,
    pump_cmd: int,
    valve_cmd: float,
    controller,
    epsilon: float = 0.05,
    safe_valve: float = 0.0,
) -> tuple[bool, str]:
    """
    Gateway-side command validation against live controller setpoint and deadband.
    
    Safety Invariants:
    1. Valve must equal default_valve_pct OR (safe_valve with pump_cmd == 0).
    2. Pump ON is invalid if h_est >= setpoint + deadband + epsilon (>= 1.25m).
    3. Pump OFF is invalid if h_est <= setpoint - deadband - epsilon (<= 0.75m).
    
    Returns:
        (is_valid: bool, rejection_reason: str)
    """
    # Strict attribute validation — explicit exceptions
    if not hasattr(controller, 'setpoint'):
        raise AttributeError("Controller missing 'setpoint' attribute")
    setpoint = float(controller.setpoint)
    if not hasattr(controller, '_deadband'):
        raise AttributeError("Controller missing '_deadband' attribute")
    deadband = float(controller._deadband)
    if not hasattr(controller, '_default_valve_pct'):
        raise AttributeError("Controller missing '_default_valve_pct' attribute")
    default_valve = float(controller._default_valve_pct)

    # Valve invariant
    if round(valve_cmd, 6) != round(default_valve, 6):
        if round(valve_cmd, 6) != round(safe_valve, 6) or pump_cmd != 0:
            return False, f"Invalid valve position {valve_cmd}% (allowed: {default_valve}% or safe {safe_valve}% with pump OFF)"

    # Dynamic pump-vs-level hysteresis rules
    upper_limit = round(setpoint + deadband + epsilon, 6)
    if pump_cmd == 1 and round(h_est, 6) >= upper_limit:
        return False, f"Pump ON forbidden at h_est={h_est:.3f}m >= limit={upper_limit:.3f}m"

    lower_limit = round(setpoint - deadband - epsilon, 6)
    if pump_cmd == 0 and round(h_est, 6) <= lower_limit:
        return False, f"Pump OFF forbidden at h_est={h_est:.3f}m <= limit={lower_limit:.3f}m"

    return True, "Valid"

class GatewayCore:
    def __init__(self, cfg, sse_hub, dos_gap_rule=True):
        self.cfg = cfg
        self.sse_hub = sse_hub
        self.lock = threading.RLock()
        
        self.ids = StreamingIDS(cfg, policy_version="v2", dos_gap_rule=dos_gap_rule)
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

        # Prevention configuration & state
        prev_cfg = getattr(cfg, "prevention", None)
        self.mode = getattr(prev_cfg, "default_mode", "monitor") if prev_cfg else "monitor"
        self.takeover_engines = getattr(prev_cfg, "takeover_engines", ["physics"]) if prev_cfg else ["physics"]
        self.trigger_state = getattr(prev_cfg, "trigger_state", "CRITICAL") if prev_cfg else "CRITICAL"
        self.handback_tolerance_m = getattr(prev_cfg, "handback_tolerance_m", 0.05) if prev_cfg else 0.05
        self.handback_clean_ticks = getattr(prev_cfg, "handback_clean_ticks", 5) if prev_cfg else 5
        self.auto_handback = getattr(prev_cfg, "auto_handback", False) if prev_cfg else False
        self.twin_takeover_active = False
        self.clean_ticks = 0
        self.last_action_taken = "none"

        # External override / command hold state
        self.external_override_active = False
        self.held_pump_cmd = 0
        self.held_valve_cmd = 50.0
        self.hold_ticks_remaining = 0

        # Command pipeline metrics
        self.commands_received = 0
        self.commands_blocked = 0
        self.commands_would_block = 0
        self.holds_dropped = 0
        self.holds_would_drop = 0

        # Gateway-issued pump history for wire tamper detection
        self.gateway_pump_history = []
        self.wire_tamper_detected = False
        self.wire_tamper_alerts = 0

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
            self.twin_takeover_active = False
            self.clean_ticks = 0
            self.last_action_taken = "none"
            self.external_override_active = False
            self.held_pump_cmd = 0
            self.held_valve_cmd = 50.0
            self.hold_ticks_remaining = 0
            self.commands_received = 0
            self.commands_blocked = 0
            self.commands_would_block = 0
            self.holds_dropped = 0
            self.holds_would_drop = 0
            self.gateway_pump_history = []
            self.wire_tamper_detected = False
            self.wire_tamper_alerts = 0

    def set_mode(self, mode: str):
        """Set gateway mode: 'monitor' or 'prevention'."""
        with self.lock:
            self.mode = mode
            if mode == "monitor":
                self.twin_takeover_active = False
                self.last_action_taken = "none"

    def set_auto_handback(self, val: bool):
        """Enable or disable automatic handback to sensor."""
        with self.lock:
            self.auto_handback = bool(val)
            
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
            
    def evaluate_ingress_command(self, pump_cmd: int, valve_cmd: float, 
                                  hold_ticks: int, role: str) -> tuple[bool, str]:
        """Evaluate an incoming command against live plant state.
        Returns (is_valid, reason)."""
        with self.lock:
            if hasattr(self, 'level_buffer') and self.level_buffer:
                h_est = self.level_buffer[-1]
            else:
                h_est = self.ids.get_twin_estimate()
            
            return evaluate_command_with_live_setpoint(
                h_est, pump_cmd, valve_cmd, self.controller
            )

    def apply_override(self, pump_cmd: int, valve_cmd: float, hold_ticks: int):
        """Activate an external command override hold."""
        with self.lock:
            self.external_override_active = True
            self.held_pump_cmd = pump_cmd
            self.held_valve_cmd = valve_cmd
            self.hold_ticks_remaining = hold_ticks

    def drop_hold(self, reason: str):
        """Drop an active external hold."""
        with self.lock:
            self.external_override_active = False
            self.hold_ticks_remaining = 0
            # Sync controller state from last known telemetry
            if self.last_pkt is not None:
                self.controller._pump_command = 1 if self.last_pkt.pump_on else 0

    def process_sense(self, level_m: float) -> dict:
        """Handle /api/sense: return pump/valve commands, applying overrides and enforcement."""
        with self.lock:
            if not hasattr(self, 'level_buffer'):
                self.level_buffer = []
            self.level_buffer.append(level_m)
            # keep reasonable buffer
            if len(self.level_buffer) > 50:
                self.level_buffer.pop(0)

            # --- Twin takeover (Phase 6a, unchanged) ---
            if self.mode == "prevention" and self.twin_takeover_active:
                active_level = self.ids.get_twin_estimate()
                level_source = "twin"
            else:
                active_level = level_m
                level_source = "sensor"

            # --- External Override Hold ---
            if self.external_override_active and self.hold_ticks_remaining > 0:
                # Continuous enforcement: re-validate hold against live level
                h_est = active_level
                is_valid, reason = evaluate_command_with_live_setpoint(
                    h_est, self.held_pump_cmd, self.held_valve_cmd, self.controller
                )

                if not is_valid:
                    if self.mode == "prevention":
                        # Drop the hold
                        self.holds_dropped += 1
                        self.sse_hub.publish({
                            "event_type": "Auth misuse",
                            "source": "continuous_enforcement",
                            "action": "hold_dropped",
                            "reason": reason,
                            "h_est": h_est
                        })
                        self.drop_hold(reason)
                        # Fall through to autonomous controller below
                    else:
                        # Monitor: log would_drop but allow hold to continue
                        self.holds_would_drop += 1
                        self.sse_hub.publish({
                            "event_type": "Auth misuse",
                            "source": "continuous_enforcement",
                            "action": "would_drop",
                            "reason": reason,
                            "h_est": h_est
                        })

                # If hold is still active after enforcement check
                if self.external_override_active and self.hold_ticks_remaining > 0:
                    self.hold_ticks_remaining -= 1
                    if self.hold_ticks_remaining == 0:
                        self.external_override_active = False
                        # Sync controller from telemetry
                        if self.last_pkt is not None:
                            self.controller._pump_command = 1 if self.last_pkt.pump_on else 0

                    # Track issued command for tamper detection
                    self.gateway_pump_history.append(self.held_pump_cmd)
                    if len(self.gateway_pump_history) > 10:
                        self.gateway_pump_history.pop(0)

                    return {
                        "pump_cmd": self.held_pump_cmd,
                        "valve_cmd": self.held_valve_cmd,
                        "level_source": level_source,
                        "active_level": active_level,
                        "action_taken": "external_hold"
                    }

            # --- Autonomous controller (normal path) ---
            ctrl_cmds = self.controller.step(active_level)

            # Track issued command for tamper detection
            self.gateway_pump_history.append(ctrl_cmds['pump_command'])
            if len(self.gateway_pump_history) > 10:
                self.gateway_pump_history.pop(0)

            return {
                "pump_cmd": ctrl_cmds['pump_command'],
                "valve_cmd": ctrl_cmds['valve_command'],
                "level_source": level_source,
                "active_level": active_level,
                "action_taken": self.last_action_taken
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

        # 4-Way Actuator Consistency Check (AM-3 Wire Tamper)
        wire_tamper = (
            len(self.gateway_pump_history) >= 3
            and self.gateway_pump_history[-1] == 0
            and self.gateway_pump_history[-2] == 0
            and self.gateway_pump_history[-3] == 0
            and (
                pkt.pump_cmd == 1
                or pkt.pump_on is True
                or (pkt.q_in is not None and pkt.q_in > 0.001)
            )
        )

        if wire_tamper:
            self.wire_tamper_detected = True
            self.wire_tamper_alerts += 1
            verdict["is_anomaly"] = True
            if "engines_firing" not in verdict:
                verdict["engines_firing"] = []
            if "actuator_consistency" not in verdict["engines_firing"]:
                verdict["engines_firing"].append("actuator_consistency")
            self.sse_hub.publish({
                "event_type": "Wire tamper",
                "source": "actuator_consistency",
                "seq": pkt.seq,
                "ts": pkt.ts,
                "gateway_history": list(self.gateway_pump_history[-3:]),
                "echoed_pump_cmd": pkt.pump_cmd,
                "echoed_pump_on": pkt.pump_on,
                "q_in": pkt.q_in,
                "action": "wire_tamper_detected"
            })
            
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
        
        # Prevention State Machine
        is_critical = (am_state["alert_state"] == self.trigger_state)
        engines_firing = verdict.get("engines_firing", [])
        suppress_physics = verdict.get("suppress_physics_takeover", False)
        
        eligible_takeover_engines = [
            e for e in engines_firing
            if e in self.takeover_engines and not (e == "physics" and suppress_physics)
        ]
        
        if self.mode == "prevention":
            if is_critical and len(eligible_takeover_engines) > 0:
                self.twin_takeover_active = True
                self.last_action_taken = "twin_takeover"
                self.clean_ticks = 0
            elif self.twin_takeover_active:
                if not verdict["is_anomaly"]:
                    self.clean_ticks += 1
                    twin_est = self.ids.get_twin_estimate()
                    if self.clean_ticks >= self.handback_clean_ticks and abs(pkt.level_m - twin_est) < self.handback_tolerance_m:
                        if self.auto_handback:
                            self.twin_takeover_active = False
                            self.last_action_taken = "handback"
                            self.alert_manager.acknowledge()
                else:
                    self.clean_ticks = 0
        else:
            self.twin_takeover_active = False
            self.last_action_taken = "none"
            
        verdict["mode"] = self.mode
        verdict["twin_takeover_active"] = self.twin_takeover_active
        verdict["action_taken"] = self.last_action_taken

        # Enrich verdict
        verdict.update(am_state)
        if wire_tamper:
            verdict["attack_type"] = "Wire tamper"
        verdict["wire_tamper"] = wire_tamper
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

    def step(self, pkt) -> dict:
        """Unified in-process step for testing and simulation harnesses."""
        with self.lock:
            sense_res = self.process_sense(pkt.level_m)
            verdict = self.process_telemetry(pkt)
            verdict.update(sense_res)
            return verdict
