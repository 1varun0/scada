import sys
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

cfg = load_config('scada_live/config.yaml')
plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg)

errors_obs = []
errors_true = []

for _ in range(1800):
    pkt = plant.step()
    res = ids.update(pkt)
    errors_obs.append(res['level_obs'] - res['level_twin'])
    errors_true.append(plant.last_true_level - res['level_twin'])

slope_obs, _ = np.polyfit(range(1800), errors_obs, 1)
slope_true, _ = np.polyfit(range(1800), errors_true, 1)

print(f"Obs error slope: {slope_obs:.8f} m/tick")
print(f"True error slope: {slope_true:.8f} m/tick")
print(f"Max true error: {max(abs(np.array(errors_true))):.5f}")
