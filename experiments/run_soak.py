import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

cfg = load_config('scada_live/config.yaml')
plant = LivePlant(cfg, standalone_mode=True)
ids = StreamingIDS(cfg, policy_version="v2")

max_error = 0.0
fires = {'physics': 0, 'lstm': 0, 'policy': 0, 'availability': 0}

for _ in range(1800):
    pkt = plant.step()
    res = ids.update(pkt)
    
    error = abs(res['level_obs'] - res['level_twin'])
    if error > max_error:
        max_error = error
        
    for e in ['physics', 'lstm', 'policy', 'availability']:
        if res['scores'][e] > 0.95:
            fires[e] += 1

print(f"Max tracking error on 30-minute live run: {max_error:.5f} m")
print(f"Physics fires: {fires['physics']}")
print(f"LSTM fires: {fires['lstm']}")
print(f"Policy fires: {fires['policy']}")
print(f"Avail fires: {fires['availability']}")
