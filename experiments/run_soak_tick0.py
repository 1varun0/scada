import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.common.packets import TelemetryPacket

cfg = load_config('scada_live/config.yaml')
cfg.simulation.clamp_flow_noise = True

plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg, policy_version="v2")

flags = []
print("=== Running 30-Minute Soak Test (1800 ticks) Counting Flags from Tick 0 ===")

for t in range(1800):
    obs = plant.observe()
    ctrl = plant.controller.step(obs)
    pkt = plant.advance(ctrl["pump_command"], ctrl["valve_command"])
    
    ids_pkt = TelemetryPacket(
        run_id="soak_run", ts=float(t), seq=t, src_t=float(t), received=True,
        level_m=pkt.level_m, q_in=pkt.q_in, q_out=pkt.q_out,
        pump_cmd=pkt.pump_cmd, valve_cmd=pkt.valve_cmd,
        pump_on=pkt.pump_on, valve_pct=pkt.valve_pct
    )
    res = ids.update(ids_pkt)
    scores = res['scores']
    firing = [e for e, s in scores.items() if s > 0.95]
    if firing:
        flags.append((t, firing, scores))

print(f"Total ticks evaluated: 1800 (t=0 to 1799)")
print(f"Total flags (> 0.95) from tick 0: {len(flags)}")
if flags:
    for t, firing, sc in flags:
        print(f"Tick {t:4d}: Firing={firing} | Phy={sc['physics']:.4f} LSTM={sc['lstm']:.4f} Pol={sc['policy']:.4f} Av={sc['availability']:.4f}")
else:
    print("Zero flags across all 1800 ticks (from tick 0 to 1799)!")
