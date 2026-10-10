import matplotlib.pyplot as plt
import sqlite3
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

cfg = load_config('scada_live/config.yaml')
plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg)


errors = []
flags = 0

for _ in range(1800):
    pkt = plant.step()
    res = ids.update(pkt)
    
    error = res['level_obs'] - res['level_twin']
    errors.append(error)
    if res['scores']['physics'] > 0.95:
        flags += 1

print(f"Physics flags in 1800 ticks: {flags}")
plt.plot(errors)
plt.title('Twin Residual over Time (1800 ticks)')
plt.savefig('experiments/residual.png')
