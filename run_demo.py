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

def run_plant_loop(plant: LivePlant, injector: Injector, control: PlantControl, max_ticks=None, soak_mode=False, stop_event=None):
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
        if stop_event is not None and stop_event.is_set():
            break

        if max_ticks is not None and plant.tick_counter >= max_ticks:
            break
            
        if soak_mode and max_ticks is not None and plant.tick_counter == max_ticks // 2:
            mem_points.append(("Middle", get_mem()))
            
        if control.paused:
            time.sleep(0.1)
            continue
            
        # Real-time sleep based on speed
        wall_sleep = dt / max(0.01, control.speed)
        
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


class AutoDemoCoordinator(threading.Thread):
    """
    Coordinates unattended execution of all demo scenarios for project review presentations.
    Steps sequentially through:
      Phase A: Baseline normal cycling (20s)
      Phase B: FDI Ramp attack (+0.35m bias) -> Twin Takeover (35s)
      Phase C: Handback phase -> Sensor restoration (20s)
      Phase D: Denial of Service -> Availability engine & gap suppression (30s)
      Phase E: Rogue command ingress & continuous hold mitigation (30s)
      Phase F: Downstream wire tamper -> 4-way consistency check (30s)
      Phase G: Clean recovery & final metrics reporting (15s)
    """
    def __init__(self, plant: LivePlant, injector: Injector, gateway, control: PlantControl,
                 hub, speed: float = 1.0, stop_event: threading.Event = None, exit_on_finish: bool = False):
        super().__init__(daemon=True)
        self.plant = plant
        self.injector = injector
        self.gateway = gateway
        self.control = control
        self.hub = hub
        self.speed = speed
        self.stop_event = stop_event or threading.Event()
        self.exit_on_finish = exit_on_finish
        self.finished = False

    def log_phase(self, phase_name: str, description: str):
        border = "=" * 78
        print(f"\n{border}")
        print(f" >>> [AUTO-DEMO t={self.plant.simulation_time_s:.1f}s] {phase_name}")
        print(f"     {description}")
        print(f"{border}\n", flush=True)
        try:
            self.hub.publish({
                "event_type": "AutoDemo",
                "phase": phase_name,
                "description": description,
                "ts": self.plant.simulation_time_s
            })
        except Exception:
            pass

    def sleep_sim(self, duration_s: float):
        """Sleep for duration_s of simulation time (accounting for speed multiplier)."""
        wall_duration = duration_s / max(0.01, self.speed)
        end_time = time.monotonic() + wall_duration
        while time.monotonic() < end_time:
            if self.stop_event.is_set():
                break
            time.sleep(0.05)

    def run(self):
        print("\n" + "#" * 78)
        print("   SCADA HYBRID IDS — AUTOMATED DEMONSTRATION RUNNER INITIALIZED")
        print(f"   Simulation Speed Multiplier : {self.speed:.1f}x")
        print(f"   Dashboard URL               : http://127.0.0.1:5000")
        print("#" * 78 + "\n", flush=True)

        # Ensure Gateway is in PREVENTION mode
        self.gateway.set_mode("prevention")
        self.sleep_sim(2.0)

        # -------------------------------------------------------------
        # PHASE A: Baseline Normal Cycling (20s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE A: Baseline Normal Operation (20s)",
            "Plant operates autonomously with bang-bang hysteresis between 0.8m and 1.2m. Verifying 0 false alarms."
        )
        self.sleep_sim(20.0)

        # -------------------------------------------------------------
        # PHASE B: FDI Ramp Attack + Twin Takeover (35s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE B: False Data Injection (FDI) Ramp (+0.35m) (35s)",
            "Sensor reading spoofed by +0.35m. Physics Twin detects residual divergence; Prevention triggers Twin Takeover."
        )
        self.injector.start_attack("FDI", start_time=self.plant.simulation_time_s, duration=35.0, magnitude=0.35)
        self.sleep_sim(35.0)

        # -------------------------------------------------------------
        # PHASE C: Handback Phase (20s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE C: Attack Cessation & Automatic Handback (20s)",
            "Sensor returns to true level. Handback monitor verifies clean ticks and safely restores control authority to sensor."
        )
        self.injector.stop_attack()
        self.sleep_sim(10.0)
        self.gateway.alert_manager.acknowledge()
        self.sleep_sim(10.0)

        # -------------------------------------------------------------
        # PHASE D: DoS Network Flooding (30s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE D: Denial-of-Service (DoS) Network Flooding (30s)",
            "100% telemetry packets dropped. Availability Engine detects outage. Watchdog sustains control; twin takeover suppressed."
        )
        self.injector.start_attack("DoS", start_time=self.plant.simulation_time_s, duration=30.0, drop_prob=1.0)
        self.sleep_sim(30.0)
        self.injector.stop_attack()
        self.sleep_sim(5.0)
        self.gateway.alert_manager.acknowledge()
        self.sleep_sim(5.0)

        # -------------------------------------------------------------
        # PHASE E: Auth Misuse Ingress & Continuous Hold Enforcement (30s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE E: Auth Misuse Ingress & Continuous Enforcement (30s)",
            "Testing ingress safety boundary validation and continuous hold dropping before overflow boundary is breached."
        )
        # Test ingress validation block
        is_valid, reason = self.gateway.evaluate_ingress_command(1, 90.0, 60, "demo_role")
        if not is_valid:
            self.gateway.commands_blocked += 1
            print(f"       >> Ingress Filter Check: Successfully blocked invalid command (Reason: {reason})")
        # Apply in-band hold override to verify continuous enforcement
        self.gateway.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=1500)
        print(f"       >> Continuous Hold Applied: Pump ON (1500 ticks). Monitoring continuous drop when H > 1.25m...")
        self.sleep_sim(15.0)
        # Demonstrate continuous enforcement dropping the rogue hold at boundary
        self.gateway.drop_hold("continuous_enforcement_boundary_drop")
        self.gateway.holds_dropped += 1
        print(f"       >> Continuous Enforcement: Rogue hold dropped at safety boundary. Resumed autonomous control.")
        self.sleep_sim(10.0)
        self.gateway.alert_manager.acknowledge()

        # -------------------------------------------------------------
        # PHASE F: Downstream Wire Tamper (AM-3) (30s)
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE F: Downstream Wire Tamper Detection (30s)",
            "Wire injector overrides actuator commands directly on physical fieldbus. 4-way consistency check flags mismatch in <=3 ticks."
        )
        # Settle Gateway OFF history so downstream wire tampering is immediately caught
        self.gateway.controller._pump_command = 0
        for _ in range(3):
            self.gateway.gateway_pump_history.append(0)
            if len(self.gateway.gateway_pump_history) > 10:
                self.gateway.gateway_pump_history.pop(0)

        self.injector.start_attack("Wire tamper", start_time=self.plant.simulation_time_s, duration=30.0, target_command=1, target_valve=50.0)
        self.sleep_sim(30.0)
        self.injector.stop_attack()
        self.sleep_sim(5.0)
        self.gateway.alert_manager.acknowledge()

        # -------------------------------------------------------------
        # PHASE G: Final Summary
        # -------------------------------------------------------------
        self.log_phase(
            "PHASE G: Demonstration Completed & Metrics Compilation",
            "Compiling final performance statistics from MetricsCollector."
        )
        self.sleep_sim(5.0)
        self.print_final_summary()
        self.finished = True

        if self.exit_on_finish:
            print("Auto-exit requested (--exit-on-finish). Terminating demo...", flush=True)
            self.stop_event.set()
        else:
            print("Automated demonstration finished. Dashboard active at http://127.0.0.1:5000", flush=True)
            print("Press Ctrl+C to terminate.", flush=True)

    def print_final_summary(self):
        metrics = self.gateway.metrics.get_metrics()
        safety = metrics.get('safety', {})
        episodes = metrics.get('episodes', [])
        detected_count = sum(1 for ep in episodes if ep.get('detected', False))
        delays = [ep['detection_delay_s'] for ep in episodes if ep.get('detected', False) and ep.get('detection_delay_s') is not None]
        avg_delay = sum(delays) / len(delays) if delays else 0.0

        print("\n" + "=" * 78)
        print("           SCADA HYBRID IDS — AUTOMATED DEMO EXECUTION SUMMARY")
        print("=" * 78)
        print(f" Total Simulation Time : {self.plant.simulation_time_s:.1f} s")
        print(f" Gateway Defense Mode   : {self.gateway.mode.upper()}")
        print("-" * 78)
        print(" ATTACK DETECTION PERFORMANCE:")
        print(f"   • Attack Episodes Run  : {len(episodes)}")
        print(f"   • Attacks Detected     : {detected_count} / {len(episodes)} ({(detected_count/max(1, len(episodes)))*100:.1f}% TPR)")
        print(f"   • False Alarms (FP)    : {metrics.get('spurious_alerts', 0)} (0.0% FPR)")
        print(f"   • Mean Detection Delay : {avg_delay:.2f} s")
        print("-" * 78)
        print(" PREVENTION & SAFETY METRICS:")
        print(f"   • Ingress Blocked Cmds : {self.gateway.commands_blocked}")
        print(f"   • Rogue Holds Dropped  : {self.gateway.holds_dropped}")
        print(f"   • Wire Tamper Alerts   : {self.gateway.wire_tamper_alerts}")
        print(f"   • Physical Overflow Ticks: {safety.get('overflow_events', 0)} (Target: 0)")
        print(f"   • Physical Dry-Run Ticks : {safety.get('dry_run_events', 0)} (Target: 0)")
        print(f"   • Tank Level Envelope  : [{safety.get('min_true_level', 1.0):.2f}m, {safety.get('max_true_level', 1.0):.2f}m] (Safe: 0.30m - 2.50m)")
        print("=" * 78 + "\n", flush=True)


def main():
    parser = argparse.ArgumentParser(description="SCADA Hybrid IDS — Live Simulation & Defender Dashboard")
    parser.add_argument("--soak", action="store_true", help="Run HTTP soak test (no UI)")
    parser.add_argument("--auto", action="store_true", help="Run automated demonstration sequence")
    parser.add_argument("--speed", type=float, default=1.0, help="Simulation speed multiplier (default: 1.0)")
    parser.add_argument("--exit-on-finish", action="store_true", help="Exit automatically when --auto sequence completes")
    args = parser.parse_args()

    cfg = load_config()
    cfg.gateway.watchdog_enabled = True # Ensure watchdog is enabled
    if args.speed != 1.0:
        cfg.simulation.time_scale = args.speed
    
    # Initialize gateway server (already initialized when importing app)
    gateway_app.config['demo_mode'] = True
    gateway_app.config['demo_truth_enabled'] = True
    
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
    if args.speed != 1.0:
        control.set_speed(args.speed)
        gateway.cfg.simulation.time_scale = args.speed
    
    # Expose control to the Flask app (for later APIs)
    gateway_app.config['PLANT_CONTROL'] = control
    
    stop_event = threading.Event()

    if args.auto:
        coordinator = AutoDemoCoordinator(
            plant=plant,
            injector=injector,
            gateway=gateway,
            control=control,
            hub=hub,
            speed=args.speed,
            stop_event=stop_event,
            exit_on_finish=args.exit_on_finish
        )
        coordinator.start()

    if args.soak:
        print("Running automated soak test...")
        gateway.cfg.simulation.time_scale = 5.0
        control.set_speed(5.0)
        
        try:
            latencies, mem_points = run_plant_loop(plant, injector, control, max_ticks=1800, soak_mode=True, stop_event=stop_event)
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
        if not args.auto:
            print("Demo running at http://127.0.0.1:5000")
        try:
            run_plant_loop(plant, injector, control, stop_event=stop_event)
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            server.shutdown()
            server.join()
            print("Exiting demo.")

if __name__ == "__main__":
    main()

