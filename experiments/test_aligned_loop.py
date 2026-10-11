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

print("=== Running with clamped noise AND actual pump.state ===")
plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg, policy_version="v2")
fake_client = DummyGatewayClient()
inj = Injector("http://fake", "run1", real_client=fake_client)

for t in range(400):
    # Proper closed loop:
    obs = plant.observe()
    ctrl_cmds = plant.controller.step(obs)
    fake_client.last_cmd = (ctrl_cmds["pump_command"], ctrl_cmds["valve_command"])
    
    cmd_p, cmd_v = inj.sense(t, float(t), obs)
    pkt = plant.advance(cmd_p, cmd_v)
    
    inj.send_telemetry(pkt.to_dict())
    if fake_client.last_pkt is not None:
        p_dict = fake_client.last_pkt
        ids_pkt = TelemetryPacket(
            run_id="run1", ts=float(t), seq=t, src_t=p_dict.get('src_t', float(t)), received=float(t),
            level_m=p_dict["level_m"], q_in=p_dict["q_in"], q_out=p_dict["q_out"],
            pump_cmd=p_dict["pump_cmd"], valve_cmd=p_dict["valve_cmd"],
            pump_on=p_dict["pump_on"], valve_pct=p_dict["valve_pct"]
        )
        res = ids.update(ids_pkt)
        
        if 200 <= t <= 225:
            print(f"Tick {t:3d}: LSTM={res['scores']['lstm']:.4f} Phy={res['scores']['physics']:.4f} Pol={res['scores']['policy']:.4f} Av={res['scores']['availability']:.4f} | P_on={ids_pkt.pump_on} P_cmd={ids_pkt.pump_cmd} Qin={ids_pkt.q_in:.5f}")
