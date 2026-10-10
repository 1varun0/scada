import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

def check_trend(clamp_flow_noise: bool, zero_noise: bool):
    cfg = load_config('scada_live/config.yaml')
    if zero_noise:
        cfg.simulation.sensor_noise_level_m = 0.0
        cfg.simulation.sensor_noise_flow_m3s = 0.0

    plant = LivePlant(cfg, standalone_mode=True)
    plant.noise._clamp_flow = clamp_flow_noise
    
    ids = StreamingIDS(cfg)
    
    errors = []
    for _ in range(1800):
        pkt = plant.step()
        res = ids.update(pkt)
        errors.append(plant.last_true_level - res['level_twin'])

    slope = np.polyfit(range(1800), errors, 1)[0]
    max_err = max(abs(np.array(errors)))
    return slope, max_err

print("=== Clamped Noise ===")
s, e = check_trend(True, False)
print(f"Slope: {s:.8f} m/tick, Max Error: {e:.5f} m")

print("\n=== Unclamped Noise ===")
s, e = check_trend(False, False)
print(f"Slope: {s:.8f} m/tick, Max Error: {e:.5f} m")

print("\n=== Zero Noise ===")
s, e = check_trend(True, True)
print(f"Slope: {s:.8f} m/tick, Max Error: {e:.5f} m")
