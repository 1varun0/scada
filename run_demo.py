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

def run_plant_loop(plant: LivePlant, injector: Injector, control: PlantControl, max_ticks=None, soak_mode=False):
    dt = plant.cfg.simulation.dt_s
    latencies = []
    mem_points = []
    
    import sys, os
    def get_mem():
        if sys.platform != 'win32':
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        else:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024.0 * 1024.0)

    if soak_mode:
        mem_points.append(("Start", get_mem()))

    while True:
        if max_ticks is not None and plant.tick_counter >= max_ticks:
            break
            
        if soak_mode and max_ticks is not None and plant.tick_counter == max_ticks // 2:
            mem_points.append(("Middle", get_mem()))
            
        if control.paused:
            time.sleep(0.1)
            continue
            
        # Real-time sleep based on speed
        wall_sleep = dt / control.speed
        
        t0 = time.perf_counter()
        
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
        
        t1 = time.perf_counter()
        if soak_mode:
            latencies.append((t1 - t0) * 1000.0) # ms
            
        plant.tick_counter += 1
        plant.simulation_time_s += dt
        
        if not soak_mode or control.speed < 100.0:
            time.sleep(wall_sleep)
            
    if soak_mode:
        mem_points.append(("End", get_mem()))
        return latencies, mem_points


class ServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1', port=5000):
        threading.Thread.__init__(self)
        self.server = make_server(host, port, app, threaded=True)
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
        print("Running automated soak test...")
        from scada_live.scada_ids.server import gateway
        gateway.cfg.simulation.time_scale = 5.0
        control.set_speed(5.0)
        
        try:
            latencies, mem_points = run_plant_loop(plant, injector, control, max_ticks=1800, soak_mode=True)
        except KeyboardInterrupt:
            latencies, mem_points = [], []
        finally:
            server.shutdown()
            server.join()
            
            metrics_dict = gateway.metrics.get_metrics()
            spurious = metrics_dict.get('spurious_alerts', 0)
            
            if latencies:
                latencies.sort()
                p50 = latencies[int(len(latencies)*0.5)]
                p95 = latencies[int(len(latencies)*0.95)]
                p99 = latencies[int(len(latencies)*0.99)]
            else:
                p50 = p95 = p99 = 0.0
            
            print(f"Soak test finished.")
            for name, val in mem_points:
                print(f"Memory ({name}): {val:.2f} MB")
            print(f"P50 Latency: {p50:.3f} ms")
            print(f"P95 Latency: {p95:.3f} ms")
            print(f"P99 Latency: {p99:.3f} ms")
            print(f"False Alarms: {spurious}")
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
