import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.attacker_wire.injector import Injector
from scada_live.common.packets import TelemetryPacket

cfg = load_config('scada_live/config.yaml')

class DummyGatewayClient:
    def __init__(self):
        self.last_cmd = (0, 0.0)
        self.last_pkt = None
    def sense(self, seq, ts, level_m):
        return self.last_cmd
    def send_telemetry(self, pkt):
        self.last_pkt = pkt
    def send_truth(self, truth):
        pass

grid = [
    ("Physical State", True),
    ("Physical State", False),
    ("Forced Command", True),
    ("Forced Command", False)
]

print("=== 2x2 Grid Evaluation: LSTM Sensitivity to Pump Alignment and Noise Clamp ===")

for mode, clamp in grid:
    cfg.simulation.clamp_flow_noise = clamp
    plant = LivePlant(cfg, standalone_mode=True)
    ids = StreamingIDS(cfg, policy_version="v2")
    fake_client = DummyGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake_client)
    
    lstm_scores = []
    
    for t in range(400):
        obs = plant.observe()
        ctrl = plant.controller.step(obs)
        fake_client.last_cmd = (ctrl["pump_command"], ctrl["valve_command"])
        cmd_p, cmd_v = inj.sense(t, float(t), obs)
        pkt = plant.advance(cmd_p, cmd_v)
        fake_client.last_pkt = None
        inj.send_telemetry(pkt.to_dict())
        
        p = fake_client.last_pkt
        if mode == "Physical State":
            pump_on_val = bool(p["pump_on"]) # Actual physical state
        else:
            pump_on_val = bool(p["pump_cmd"]) # Forced from command
            
        ids_pkt = TelemetryPacket(
            run_id="run1", ts=float(t), seq=t, src_t=p.get('src_t', float(t)), received=True,
            level_m=p["level_m"], q_in=p["q_in"], q_out=p["q_out"],
            pump_cmd=p["pump_cmd"], valve_cmd=p["valve_cmd"],
            pump_on=pump_on_val, valve_pct=float(p["valve_pct"])
        )
        res = ids.update(ids_pkt)
        lstm_scores.append(res['scores']['lstm'])
        
    window_scores = lstm_scores[200:231]
    max_200_230 = max(window_scores)
    ticks_above_95 = sum(1 for s in lstm_scores if s > 0.95)
    
    print(f"Mode: {mode:<15} | Clamp: {str(clamp):<5} | Max LSTM (t=200..230): {max_200_230:.4f} | Ticks > 0.95: {ticks_above_95:2d}")
