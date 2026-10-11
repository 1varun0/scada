import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.attacker_wire.injector import Injector
from scada_live.common.packets import TelemetryPacket

cfg = load_config('scada_live/config.yaml')
cfg.simulation.clamp_flow_noise = True

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

plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg, policy_version="v2")
fake_client = DummyGatewayClient()
inj = Injector("http://fake", "run1", real_client=fake_client)

flags = []
for t in range(400):
    obs = plant.observe()
    ctrl_cmds = plant.controller.step(obs)
    fake_client.last_cmd = (ctrl_cmds["pump_command"], ctrl_cmds["valve_command"])
    cmd_p, cmd_v = inj.sense(t, float(t), obs)
    if cmd_p is None:
        pump_exec, valve_exec = 0, 0.0
    else:
        pump_exec, valve_exec = cmd_p, cmd_v
        
    pkt = plant.advance(pump_exec, valve_exec)
    fake_client.last_pkt = None
    inj.send_telemetry(pkt.to_dict())
    
    if fake_client.last_pkt is not None:
        p = fake_client.last_pkt
        ids_pkt = TelemetryPacket(
            run_id="run1", ts=float(t), seq=t, src_t=p.get('src_t', float(t)), received=True,
            level_m=p["level_m"], q_in=p["q_in"], q_out=p["q_out"],
            pump_cmd=p["pump_cmd"], valve_cmd=p["valve_cmd"],
            pump_on=bool(p["pump_on"]), valve_pct=float(p["valve_pct"])
        )
    else:
        ids_pkt = TelemetryPacket(
            run_id="run1", ts=float(t), seq=t, src_t=float(t), received=False,
            level_m=pkt.level_m, q_in=0.0, q_out=0.0,
            pump_cmd=0, valve_cmd=0.0,
            pump_on=False, valve_pct=0.0
        )
    res = ids.update(ids_pkt)
    scores = res['scores']
    
    # Check if any engine > 0.95
    firing = [e for e, s in scores.items() if s > 0.95]
    if firing:
        flags.append((t, firing, scores))
    if t < 15:
        print(f"t={t:2d}: Phy={scores['physics']:.4f} LSTM={scores['lstm']:.4f} Pol={scores['policy']:.4f} Av={scores['availability']:.4f} | rcv={ids_pkt.received} L={ids_pkt.level_m:.4f} Qin={ids_pkt.q_in:.5f} Qout={ids_pkt.q_out:.5f}")

print("\n=== Every tick where any engine > 0.95 (0 to 399) ===")
if not flags:
    print("NONE. Zero false alarms across all 400 ticks!")
else:
    for t, firing, sc in flags:
        print(f"Tick {t:3d}: Firing={firing} | Phy={sc['physics']:.4f} LSTM={sc['lstm']:.4f} Pol={sc['policy']:.4f} Av={sc['availability']:.4f}")
