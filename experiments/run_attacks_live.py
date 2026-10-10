import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS
from scada_live.attacker_wire.injector import Injector
from scada_live.common.packets import TelemetryPacket

cfg = load_config('scada_live/config.yaml')

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

attacks = [
    ("FDI", {"duration": 100, "magnitude": 0.2}),
    ("Replay", {"duration": 100}),
    ("DoS", {"duration": 100}),
    ("Auth misuse", {"duration": 100, "target_command": 1, "target_valve": 0.0})
]

for attack_name, kwargs in attacks:
    print(f"\n=== Live Attack: {attack_name} ===")
    plant = LivePlant(cfg, standalone_mode=True)
    ids = StreamingIDS(cfg, policy_version="v2")
    fake_client = DummyGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake_client)
    
    # Attack for 100 ticks, but declare it early so Replay can record
    inj.start_attack(attack_name, start_time=100.0, **kwargs)
    
    # 100 ticks normal
    for t in range(100):
        pkt = plant.step()
        fake_client.last_cmd = (plant.controller.pump_command, plant.controller.valve_command)
        cmd_p, cmd_v = inj.sense(t, float(t), pkt.level_m)
        plant.pump.set_command(cmd_p)
        plant.valve.set_command(cmd_v)
        
        inj.send_telemetry({"seq": t, "ts": float(t), "level_m": pkt.level_m, "q_in": pkt.q_in, "q_out": pkt.q_out, "pump_cmd": cmd_p, "valve_cmd": cmd_v})
        if fake_client.last_pkt is not None:
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=float(t), received=float(t),
                level_m=fake_client.last_pkt["level_m"], q_in=fake_client.last_pkt.get("q_in", pkt.q_in), 
                q_out=fake_client.last_pkt.get("q_out", pkt.q_out),
                pump_cmd=fake_client.last_pkt.get("pump_cmd", cmd_p), 
                valve_cmd=fake_client.last_pkt.get("valve_cmd", cmd_v),
                pump_on=bool(fake_client.last_pkt.get("pump_cmd", cmd_p)),
                valve_pct=fake_client.last_pkt.get("valve_cmd", cmd_v)
            )
            ids.update(ids_pkt)
    
    fires = {'physics': [], 'lstm': [], 'policy': [], 'availability': []}
    
    for t in range(100, 200):
        pkt = plant.step()
        fake_client.last_cmd = (plant.controller.pump_command, plant.controller.valve_command)
        
        cmd_p, cmd_v = inj.sense(t, float(t), pkt.level_m)
        if cmd_p is not None:
            plant.pump.set_command(cmd_p)
            plant.valve.set_command(cmd_v)
        
        fake_client.last_pkt = None
        inj.send_telemetry({"seq": t, "ts": float(t), "level_m": pkt.level_m, "q_in": pkt.q_in, "q_out": pkt.q_out, "pump_cmd": cmd_p, "valve_cmd": cmd_v})
        
        if fake_client.last_pkt is not None:
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=fake_client.last_pkt.get('src_t', float(t)), received=float(t),
                level_m=fake_client.last_pkt["level_m"], q_in=fake_client.last_pkt.get("q_in", pkt.q_in), 
                q_out=fake_client.last_pkt.get("q_out", pkt.q_out),
                pump_cmd=fake_client.last_pkt.get("pump_cmd", cmd_p), 
                valve_cmd=fake_client.last_pkt.get("valve_cmd", cmd_v),
                pump_on=bool(fake_client.last_pkt.get("pump_cmd", cmd_p)),
                valve_pct=fake_client.last_pkt.get("valve_cmd", cmd_v)
            )
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                v_str = f"{ids_pkt.valve_cmd:.0f}" if ids_pkt.valve_cmd is not None else "None"
                print(f"Tick {t:3d}: seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv={ids_pkt.received} L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={v_str} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
            for e in fires:
                if res['scores'][e] > 0.95:
                    fires[e].append(t)
        else:
            # Dropped packet (simulate DoS timeout)
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=float(t), received=0.0,
                level_m=pkt.level_m, q_in=pkt.q_in, q_out=pkt.q_out, pump_cmd=cmd_p, valve_cmd=cmd_v,
                pump_on=bool(cmd_p), valve_pct=cmd_v
            )
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                v_str = f"{ids_pkt.valve_cmd:.0f}" if ids_pkt.valve_cmd is not None else "None"
                print(f"Tick {t:3d}: DROP! seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv=0.0 L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={v_str} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
            for e in fires:
                if res['scores'][e] > 0.95:
                    fires[e].append(t)
                    
    inj.stop_attack()
    for t in range(200, 250):
        pkt = plant.step()
        fake_client.last_cmd = (plant.controller.pump_command, plant.controller.valve_command)
        
        cmd_p, cmd_v = inj.sense(t, float(t), pkt.level_m)
        if cmd_p is not None:
            plant.pump.set_command(cmd_p)
            plant.valve.set_command(cmd_v)
        
        fake_client.last_pkt = None
        inj.send_telemetry({"seq": t, "ts": float(t), "level_m": pkt.level_m, "q_in": pkt.q_in, "q_out": pkt.q_out, "pump_cmd": cmd_p, "valve_cmd": cmd_v})
        
        if fake_client.last_pkt is not None:
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=fake_client.last_pkt.get('src_t', float(t)), received=float(t),
                level_m=fake_client.last_pkt["level_m"], q_in=fake_client.last_pkt.get("q_in", pkt.q_in), 
                q_out=fake_client.last_pkt.get("q_out", pkt.q_out),
                pump_cmd=fake_client.last_pkt.get("pump_cmd", cmd_p), 
                valve_cmd=fake_client.last_pkt.get("valve_cmd", cmd_v),
                pump_on=bool(fake_client.last_pkt.get("pump_cmd", cmd_p)),
                valve_pct=fake_client.last_pkt.get("valve_cmd", cmd_v)
            )
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                print(f"Tick {t:3d}: seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv={ids_pkt.received} L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={ids_pkt.valve_cmd:.0f} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
            for e in fires:
                if res['scores'][e] > 0.95:
                    fires[e].append(t)
        else:
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=float(t), received=0.0,
                level_m=pkt.level_m, q_in=pkt.q_in, q_out=pkt.q_out,
                pump_cmd=cmd_p, valve_cmd=cmd_v,
                pump_on=bool(cmd_p), valve_pct=cmd_v
            )
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                print(f"Tick {t:3d}: DROP! seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv=0.0 L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={ids_pkt.valve_cmd:.0f} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
            for e in fires:
                if res['scores'][e] > 0.95:
                    fires[e].append(t)
                
    for e in fires:
        if fires[e]:
            start = fires[e][0]
            end = fires[e][-1]
            count = len(fires[e])
            print(f"  {e.upper()} fired on {count} ticks (first at t={start}, last at t={end})")
        else:
            print(f"  {e.upper()} fired 0 times")
