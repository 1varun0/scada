import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    # Attack starts at t=100 for 100 ticks (up to t=200)
    inj.start_attack(attack_name, start_time=100.0, **kwargs)
    
    fires = {'physics': [], 'lstm': [], 'policy': [], 'availability': []}
    
    # Run full 250 ticks
    for t in range(250):
        if t == 200:
            inj.stop_attack()
            
        # 1. Physical plant observes level
        obs = plant.observe()
        
        # 2. Controller determines nominal command based on observed level
        ctrl_cmds = plant.controller.step(obs)
        fake_client.last_cmd = (ctrl_cmds["pump_command"], ctrl_cmds["valve_command"])
        
        # 3. Sense call through injector (may be spoofed, dropped, or overridden)
        cmd_p, cmd_v = inj.sense(t, float(t), obs)
        if cmd_p is None:
            # Communication loss / DoS drop: plant actuators execute fail-safe
            pump_exec = 0
            valve_exec = 0.0
        else:
            pump_exec = cmd_p
            valve_exec = cmd_v
            
        # 4. Plant advances physics with executed commands and returns telemetry packet
        pkt = plant.advance(pump_exec, valve_exec)
        
        # 5. Send telemetry through injector (may drop or spoof)
        fake_client.last_pkt = None
        inj.send_telemetry(pkt.to_dict())
        
        if fake_client.last_pkt is not None:
            p = fake_client.last_pkt
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=p.get('src_t', float(t)), received=float(t),
                level_m=p["level_m"], q_in=p["q_in"], q_out=p["q_out"],
                pump_cmd=p["pump_cmd"], valve_cmd=p["valve_cmd"],
                pump_on=bool(p["pump_on"]), valve_pct=float(p["valve_pct"])
            )
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                v_str = f"{ids_pkt.valve_cmd:.0f}" if ids_pkt.valve_cmd is not None else "None"
                print(f"Tick {t:3d}: seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv={ids_pkt.received} L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={v_str} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
            for e in fires:
                if res['scores'][e] > 0.95:
                    fires[e].append(t)
        else:
            # Dropped packet (simulate gateway watchdog synthetic packet)
            # Carries gateway actual fail-safe commands (0, 0.0), held level, zero flows
            ids_pkt = TelemetryPacket(
                run_id="run1", ts=float(t), seq=t, src_t=float(t), received=0.0,
                level_m=pkt.level_m, q_in=0.0, q_out=0.0,
                pump_cmd=0, valve_cmd=0.0,
                pump_on=False, valve_pct=0.0
            )
            if attack_name == "DoS" and 100 <= t <= 104:
                print(f"[DROP-RX {t}] ids.update() received: seq={ids_pkt.seq}, ts={ids_pkt.ts:.1f}, src_t={ids_pkt.src_t:.1f}, rcv={ids_pkt.received}, level_m={ids_pkt.level_m:.4f}, q_in={ids_pkt.q_in:.4f}, q_out={ids_pkt.q_out:.4f}, pump_cmd={ids_pkt.pump_cmd}, valve_cmd={ids_pkt.valve_cmd:.1f}, pump_on={ids_pkt.pump_on}, valve_pct={ids_pkt.valve_pct:.1f}")
            res = ids.update(ids_pkt)
            if (100 <= t <= 104) or (195 <= t <= 199) or (205 <= t <= 222):
                v_str = f"{ids_pkt.valve_cmd:.0f}" if ids_pkt.valve_cmd is not None else "None"
                print(f"Tick {t:3d}: DROP! seq={ids_pkt.seq} ts={ids_pkt.ts:.1f} src_t={ids_pkt.src_t:.1f} rcv=0.0 L={ids_pkt.level_m:.3f} Qin={ids_pkt.q_in:.4f} Qout={ids_pkt.q_out:.4f} P={ids_pkt.pump_cmd} V={v_str} | Scores: Phy={res['scores']['physics']:.2f} LSTM={res['scores']['lstm']:.2f} Pol={res['scores']['policy']:.2f} Av={res['scores']['availability']:.2f}")
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
