import time
import copy
from typing import Dict, Any, Tuple, Optional

class Injector:
    """
    Wraps GatewayClient. Intercepts sense() and send_telemetry() to inject attacks.
    Reports attack truth via send_truth().
    """
    def __init__(self, target_url: str, run_id: str, real_client=None):
        if real_client is None:
            from scada_live.plant_sim.gateway_client import GatewayClient
            self.client = GatewayClient(target_url, run_id)
        else:
            self.client = real_client
            
        self.attack_type: Optional[str] = None
        self.start_time: Optional[float] = None
        self.duration: float = 0.0
        self.magnitude: float = 0.0
        self.stealth: bool = False
        
        self.target_command: Optional[int] = None # For Auth misuse
        self.target_valve: Optional[float] = None # For Auth misuse
        self.drop_prob: float = 1.0 # For DoS
        
        self.replay_buffer = []
        self.replay_index = 0

    def start_attack(self, attack_type: str, start_time: float, duration: float, magnitude: float = 0.0, 
                     stealth: bool = False, target_command: Optional[int] = None, target_valve: Optional[float] = None,
                     drop_prob: float = 1.0):
        self.attack_type = attack_type
        self.start_time = start_time
        self.duration = duration
        self.magnitude = magnitude
        self.stealth = stealth
        self.target_command = target_command
        self.target_valve = target_valve
        self.drop_prob = drop_prob
        self.replay_buffer = []
        self.replay_index = 0

    def stop_attack(self):
        self.attack_type = None

    def _is_active(self, ts: float) -> bool:
        if self.attack_type is None or self.start_time is None:
            return False
        return self.start_time <= ts <= (self.start_time + self.duration)

    def sense(self, seq: int, ts: float, level_m: float) -> Tuple[Optional[int], Optional[float]]:
        if not self._is_active(ts):
            if self.attack_type == "Replay" and self.start_time is not None and ts < self.start_time:
                # Record for replay
                self.replay_buffer.append((ts, level_m))
            return self.client.sense(seq, ts, level_m)

        if self.attack_type == "DoS":
            import random
            if random.random() < self.drop_prob:
                return None, None # Drop
            return self.client.sense(seq, ts, level_m)

        if self.attack_type == "Replay":
            if self.replay_index < len(self.replay_buffer):
                _, spoofed_level = self.replay_buffer[self.replay_index]
                self.replay_index += 1
            else:
                spoofed_level = level_m
            return self.client.sense(seq, ts, spoofed_level)

        if self.attack_type == "FDI":
            spoofed_level = level_m + self.magnitude # Bias for now
            return self.client.sense(seq, ts, spoofed_level)

        if self.attack_type == "Auth misuse":
            # Pass true level to sense
            pump_cmd, valve_cmd = self.client.sense(seq, ts, level_m)
            # Override response
            if self.target_command is not None:
                pump_cmd = self.target_command
            if self.target_valve is not None:
                valve_cmd = self.target_valve
            return pump_cmd, valve_cmd

        return self.client.sense(seq, ts, level_m)

    def send_telemetry(self, pkt_dict: Dict[str, Any]):
        ts = pkt_dict.get('ts', 0.0)
        
        # Send truth
        truth = {
            'seq': pkt_dict.get('seq', 0),
            'ts': ts,
            'ground_truth': 1 if self._is_active(ts) else 0,
            'attack_type': self.attack_type if self._is_active(ts) else "None",
            'true_level': pkt_dict.get('level_m') # Real level from plant
        }
        self.client.send_truth(truth)
        
        if not self._is_active(ts):
            self.client.send_telemetry(pkt_dict)
            return

        spoofed_pkt = copy.deepcopy(pkt_dict)

        if self.attack_type == "DoS":
            import random
            if random.random() < self.drop_prob:
                return # Drop
                
        elif self.attack_type == "Replay":
            idx = self.replay_index - 1
            if idx >= 0 and idx < len(self.replay_buffer):
                old_ts, old_level = self.replay_buffer[idx]
                spoofed_pkt['src_t'] = old_ts
                spoofed_pkt['level_m'] = old_level
                
        elif self.attack_type == "FDI":
            spoofed_pkt['level_m'] = pkt_dict['level_m'] + self.magnitude
            
        elif self.attack_type == "Auth misuse":
            # Auth misuse overrides command, which was returned in sense.
            # Plant executed it, so pump_cmd and valve_cmd in pkt_dict are already the rogue ones.
            pass

        self.client.send_telemetry(spoofed_pkt)
