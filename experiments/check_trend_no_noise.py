import sys
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

cfg = load_config('scada_live/config.yaml')
cfg.simulation.sensor_noise_level_m = 0.0
cfg.simulation.sensor_noise_flow_m3s = 0.0
plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg)

errors = []
for _ in range(1800):
    pkt = plant.step()
    res = ids.update(pkt)
    errors.append(plant.last_true_level - res['level_twin'])

print("Slope without noise:", np.polyfit(range(1800), errors, 1)[0])
print("Max error without noise:", max(abs(np.array(errors))))
