from dataclasses import dataclass, asdict

@dataclass
class TelemetryPacket:
    # ─── Wire fields (what the IDS sees) ─────────────────────
    seq: int                    # sequence_id from process_simulator
    run_id: str                 # unique scenario/run identifier
    ts: float                   # simulation_time_s (system clock)
    src_t: float                # source_time_s (sensor clock)
    received: bool              # packet_received (True = arrived OK)
    level_m: float              # tank_level_observed (noisy measurement)
    q_in: float                 # q_in (observed, noisy)
    q_out: float                # q_out (observed, noisy)
    pump_on: bool               # pump_state (1/0 -> True/False)
    pump_cmd: int               # pump_command
    valve_pct: float            # valve_state (0-100%)
    valve_cmd: float            # valve_command

    # ─── Ground truth (NEVER seen by IDS) ────────────────────
    # Stripped by attacker_wire before forwarding to scada_ids.
    # Sent out-of-band to metrics module only.
    _true_level: float = 0.0   # h_true from plant
    _attack_active: bool = False
    _attack_type: str = "None"

    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'TelemetryPacket':
        return cls(**d)
    
    def strip_truth(self) -> dict:
        """Return a dict WITHOUT ground-truth fields (for IDS consumption)."""
        d = self.to_dict()
        return {k: v for k, v in d.items() if not k.startswith('_')}
    
    def truth_only(self) -> dict:
        """Return ONLY the ground-truth fields (for metrics)."""
        d = self.to_dict()
        return {k: v for k, v in d.items() if k.startswith('_')}

@dataclass
class CommandPacket:
    seq: int                    # command sequence number
    ts: float                   # timestamp when issued
    src: str                    # "scada_master" or "attacker"
    cmd: str                    # "PUMP"
    value: str                  # "ON" or "OFF"

    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'CommandPacket':
        return cls(**d)
