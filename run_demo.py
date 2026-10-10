import threading
import time
import argparse
import sys
from werkzeug.serving import make_server

from scada_live.common.config_loader import load_config
from scada_live.scada_ids.server import app as gateway_app, gateway, hub
from scada_live.plant_sim.plant import LivePlant
from scada_live.attacker_wire.injector import Injector
from scada_live.plant_sim.gateway_client import GatewayClient
from scada_live.common.packets import TelemetryPacket

class PlantControl:
    def __init__(self, plant: LivePlant, injector: Injector):
        self.plant = plant
        self.injector = injector
        self.paused = False
        self.speed = 1.0

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_speed(self, speed: float):
        self.speed = speed

    def reset(self, initial_level_m: float = 1.0):
        # We need to restart plant
        self.plant.cfg.tank.initial_level_m = initial_level_m
        self.plant.reset()
        self.injector.stop_attack()
        self.injector.replay_buffer = []

def run_plant_loop(plant: LivePlant, injector: Injector, control: PlantControl, max_ticks=None):
    dt = plant.cfg.simulation.dt_s
    while True:
        if max_ticks is not None and plant.tick_counter >= max_ticks:
            break
            
        if control.paused:
            time.sleep(0.1)
            continue
            
        # Real-time sleep based on speed
        wall_sleep = dt / control.speed
        
        # 1-2. Plant observes itself
        level_obs = plant.observe()
        
        # 3. Attacker injects into sense()
        # To call sense, we need seq, ts, level_m
        pump_cmd, valve_cmd = injector.sense(
            seq=plant.tick_counter,
            ts=plant.simulation_time_s,
            level_m=level_obs
        )
        
        if pump_cmd is None or valve_cmd is None:
            # Drop/DoS - use fallback
            pump_cmd = 0
            valve_cmd = plant.cfg.controller.default_valve_pct
            
        # 4-9. Plant advances
        pkt = plant.advance(pump_cmd, valve_cmd)
        
        # 10. Injector proxies telemetry
        injector.send_telemetry(pkt.to_dict())
        
        plant.tick_counter += 1
        plant.simulation_time_s += dt
        
        time.sleep(wall_sleep)


class ServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1', port=5000):
        threading.Thread.__init__(self)
        self.server = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--soak", action="store_true", help="Run HTTP soak test (no UI)")
    args = parser.parse_args()

    cfg = load_config()
    cfg.gateway.watchdog_enabled = True # Ensure watchdog is enabled
    
    # Initialize gateway server (already initialized when importing app)
    gateway_app.config['demo_mode'] = True
    gateway_app.config['demo_truth_enabled'] = True
    
    # We will patch gateway_app later to inject PlantControl for UI actions
    server = ServerThread(gateway_app, host="127.0.0.1", port=5000)
    server.start()
    
    # Wait for server
    time.sleep(1)
    
    # Initialize plant and injector
    run_id = "demo_run"
    plant = LivePlant(cfg, standalone_mode=False)
    plant.run_id = run_id
    real_client = GatewayClient("http://127.0.0.1:5000", run_id)
    injector = Injector("http://127.0.0.1:5000", run_id, real_client=real_client)
    
    control = PlantControl(plant, injector)
    
    # Expose control to the Flask app (for later APIs)
    gateway_app.config['PLANT_CONTROL'] = control
    
    if args.soak:
        print("Running 30-min soak test at 5x speed...")
        control.set_speed(5.0)
        # 30 min wall-time at 5x speed = 150 min simulation time (9000 ticks)
        # But we actually want a flat test to complete quickly in automated harness? 
        # Soak test could run for a set number of ticks. Let's say 30 real minutes if manual, 
        # but we can just run it until KeyboardInterrupt.
        try:
            run_plant_loop(plant, injector, control)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.join()
            print("Soak test finished.")
            
    else:
        print("Demo running at http://127.0.0.1:5000")
        try:
            run_plant_loop(plant, injector, control)
        except KeyboardInterrupt:
            server.shutdown()
            server.join()
            print("Exiting demo.")

if __name__ == "__main__":
    main()
