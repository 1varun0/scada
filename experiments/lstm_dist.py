import sys
import os
import numpy as np
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

def get_lstm_scores(clamp_flow: bool):
    cfg = load_config('scada_live/config.yaml')
    plant = LivePlant(cfg, standalone_mode=True)
    plant.noise._clamp_flow = clamp_flow
    ids = StreamingIDS(cfg)
    
    scores = []
    for _ in range(1800):
        pkt = plant.step()
        res = ids.update(pkt)
        scores.append(res['scores']['lstm'])
    return np.array(scores)

print("Running LivePlant with clamp=True...")
scores_clamped = get_lstm_scores(True)
print(f"Max: {scores_clamped.max():.4f}, p99: {np.percentile(scores_clamped, 99):.4f}, >0.95: {(scores_clamped > 0.95).sum()}")

print("\nRunning LivePlant with clamp=False...")
scores_unclamped = get_lstm_scores(False)
print(f"Max: {scores_unclamped.max():.4f}, p99: {np.percentile(scores_unclamped, 99):.4f}, >0.95: {(scores_unclamped > 0.95).sum()}")

print("\nQuerying stored normal scenarios (from evaluation_results.csv)...")
import pandas as pd
df = pd.read_csv('data/evaluation_results.csv')
df_n = df[df['scenario_id'].str.startswith('N')]
s_l = df_n['S_l'].values
print(f"Max: {s_l.max():.4f}, p99: {np.percentile(s_l, 99):.4f}, >0.95: {(s_l > 0.95).sum()}")
