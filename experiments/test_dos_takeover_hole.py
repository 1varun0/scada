import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sqlite3
import pandas as pd

from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.common.packets import TelemetryPacket
from scada_live.plant_sim.plant import LivePlant

cfg = load_config('scada_live/config.yaml')
hub = EventHub()

print("=== Part 1: Replay A3_003 through GatewayCore in Prevention Mode ===")
conn = sqlite3.connect('data/scada_ids.db')
df = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A3_003' ORDER BY sequence_id", conn)
conn.close()

gw = GatewayCore(cfg, hub)
gw.current_run_id = "A3_003"
gw.set_mode("prevention")
gw.set_auto_handback(True)

# Replay ticks
dos_rows = df[df['packet_received'] == 0]
t_start = int(dos_rows['simulation_time_s'].min())
t_end = int(dos_rows['simulation_time_s'].max())

print(f"DoS window: t={t_start} to t={t_end} (duration={t_end - t_start + 1}s)")
print(f"{'Tick':<5} | {'Rcvd':<5} | {'Alert State':<12} | {'Engines Firing':<25} | {'Takeover':<9} | {'Action':<15} | {'Sensor':<7} | {'Twin':<7} | {'|Diff|':<7}")
print("-" * 105)

for _, row in df.iterrows():
    t = int(row['simulation_time_s'])
    rcvd = bool(row['packet_received'] == 1)
    pkt = TelemetryPacket(
        run_id="A3_003", seq=int(row['sequence_id']), ts=float(row['simulation_time_s']),
        src_t=float(row['simulation_time_s']), received=rcvd,
        level_m=float(row['tank_level_observed']), q_in=float(row['q_in']), q_out=float(row['q_out']),
        pump_cmd=int(row['pump_command']), valve_cmd=float(row['valve_command']),
        pump_on=bool(row['pump_state'] == 1), valve_pct=float(row['valve_state'])
    )
    v = gw.process_telemetry(pkt)
    twin_est = gw.ids.get_twin_estimate()
    diff = abs(pkt.level_m - twin_est)
    
    # Print around end of DoS: t_end - 5 to t_end + 15
    if t_end - 5 <= t <= t_end + 15:
        firing_str = str(v.get('engines_firing', []))
        print(f"{t:<5d} | {str(rcvd):<5} | {v['alert_state']:<12} | {firing_str:<25} | {str(gw.twin_takeover_active):<9} | {gw.last_action_taken:<15} | {pkt.level_m:<7.4f} | {twin_est:<7.4f} | {diff:<7.4f}")

print("\n=== Part 2: test_twin_control_stability with clamp_flow_noise=False (1800 ticks / 30 min) ===")
cfg_unclamped = load_config('scada_live/config.yaml')
cfg_unclamped.simulation.clamp_flow_noise = False

plant = LivePlant(cfg_unclamped, standalone_mode=False)
gw_stab = GatewayCore(cfg_unclamped, hub)
gw_stab.current_run_id = plant.run_id = "live_run"
gw_stab.set_mode("prevention")
gw_stab.set_auto_handback(False) # Forced twin estimator control
gw_stab.twin_takeover_active = True

true_levels = []
twin_levels = []

for t in range(1800):
    obs = plant.observe()
    cmds = gw_stab.process_sense(obs)
    pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
    gw_stab.process_telemetry(pkt)
    
    true_levels.append(plant.tank.level)
    twin_levels.append(gw_stab.ids.get_twin_estimate())

min_true = min(true_levels)
max_true = max(true_levels)
final_true = true_levels[-1]
final_twin = twin_levels[-1]
final_diff = abs(final_twin - final_true)

print(f"30-Minute Run with clamp_flow_noise=False:")
print(f"  Min True Level:      {min_true:.4f} m (controller lower threshold is 0.8m)")
print(f"  Max True Level:      {max_true:.4f} m (controller upper threshold is 1.2m)")
print(f"  Final True Level:    {final_true:.4f} m")
print(f"  Final Twin Level:    {final_twin:.4f} m")
print(f"  Final |Twin - True|: {final_diff:.4f} m ({final_diff*1000:.2f} mm)")
print(f"  Overflow Count:      {plant.overflow_count}")
print(f"  Dry Run Count:       {plant.dry_run_count}")
