import json
import time
from queue import Empty
from flask import Flask, request, jsonify, Response
from scada_live.common.config_loader import load_config
from scada_live.common.packets import TelemetryPacket
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub

app = Flask(__name__)
cfg = load_config()

hub = EventHub(queue_size=200)
gateway = GatewayCore(cfg, hub)

def parse_packet(data: dict) -> TelemetryPacket:
    try:
        return TelemetryPacket(
            seq=data['seq'],
            run_id=data['run_id'],
            ts=float(data['ts']),
            src_t=float(data['src_t']),
            received=bool(data['received']),
            level_m=float(data['level_m']),
            q_in=float(data['q_in']),
            q_out=float(data['q_out']),
            pump_on=bool(data['pump_on']),
            pump_cmd=int(data['pump_cmd']),
            valve_pct=float(data['valve_pct']),
            valve_cmd=float(data['valve_cmd'])
        )
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(f"Invalid packet format: {e}")

@app.route('/api/sense', methods=['POST'])
def sense():
    data = request.json
    if not data or 'level_m' not in data:
        return jsonify({"error": "Missing level_m"}), 400
        
    cmds = gateway.process_sense(float(data['level_m']))
    return jsonify(cmds)

@app.route('/api/telemetry', methods=['POST'])
def telemetry():
    data = request.json
    if not data:
        return jsonify({"error": "Empty body"}), 400
        
    try:
        pkt = parse_packet(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    gateway.process_telemetry(pkt)
    return jsonify({"ok": True, "seq": pkt.seq})

@app.route('/api/truth', methods=['POST'])
def truth():
    data = request.json
    if not data:
        return jsonify({"error": "Empty body"}), 400
    try:
        gateway.process_truth(
            run_id=data['run_id'],
            seq=data['seq'],
            ts=float(data.get('ts', 0.0)),
            true_level=float(data['true_level']),
            attack_active=bool(data.get('attack_active', data.get('ground_truth', 0) == 1)),
            attack_type=data.get('attack_type', 'None'),
            overflow=bool(data.get('overflow', False)),
            dry_run=bool(data.get('dry_run', False))
        )
    except KeyError as e:
        return jsonify({"error": f"Missing field {e}"}), 400
    
    if app.config.get('demo_truth_enabled', False):
        hub.publish({'event': 'truth', 'data': data})
        
    return jsonify({"ok": True})

@app.route('/stream')
def stream():
    def event_stream():
        q = hub.subscribe()
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    # Do NOT send truth events to the normal /stream
                    if isinstance(msg, dict) and msg.get('event') == 'truth':
                        continue
                    yield f"data: {json.dumps(msg)}\n\n"
                except Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            hub.unsubscribe(q)
            
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/reset', methods=['POST'])
def reset():
    data = request.json or {}
    run_id = data.get('run_id', 'manual_reset')
    initial_level_m = float(data.get('initial_level_m', cfg.tank.initial_level_m))
    gateway.reset(initial_level_m, run_id)
    return jsonify({"status": "reset"})

@app.route('/api/ack', methods=['POST'])
def ack():
    data = request.json or {}
    recalibrate = bool(data.get('recalibrate', False))
    ts = time.monotonic()
    
    # 3.6 Acknowledge and recalibrate logic
    gateway.acknowledge(recalibrate, ts)
    
    if recalibrate:
        status = gateway.recalibrate()
        if "error" in status:
            return jsonify(status), 409
        
    return jsonify({"status": "ack"})

@app.route('/api/events', methods=['GET'])
def events():
    # In Phase 3b, this returns from GatewayCore's in-memory list
    return jsonify(gateway.events)

@app.route('/api/metrics', methods=['GET'])
def metrics():
    return jsonify(gateway.metrics.get_metrics())

@app.route('/api/mode', methods=['POST'])
def mode():
    # Placeholder for Phase 6
    return jsonify({"status": "mode_set"})

@app.route('/api/command', methods=['POST'])
def command():
    return jsonify({"error": "Not implemented"}), 501

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'tank': {
            'critical_low_m': cfg.tank.critical_low_m,
            'critical_high_m': cfg.tank.critical_high_m,
            'overflow_m': cfg.tank.overflow_m
        },
        'controller': {
            'pump_on_threshold_m': cfg.controller.pump_on_threshold_m,
            'pump_off_threshold_m': cfg.controller.pump_off_threshold_m,
            'default_valve_pct': cfg.controller.default_valve_pct
        },
        'simulation': {
            'time_scale': getattr(cfg.simulation, 'time_scale', 1.0)
        },
        'demo_mode': app.config.get('demo_mode', False)
    }), 200

@app.route('/api/state', methods=['GET'])
def get_state():
    control = app.config.get('PLANT_CONTROL')
    window_size = gateway.ids.window_size
    window_len = len(gateway.ids.telemetry_window)
    return jsonify({
        'alert_state': gateway.alert_manager.state,
        'active_event_id': gateway.alert_manager.event_id,
        'calibrating': window_len < window_size,
        'recalibrating_ticks_left': max(0, window_size - window_len),
        'paused': control.paused if control else False,
        'speed': control.speed if control else 1.0
    }), 200

@app.route('/api/history', methods=['GET'])
def get_history():
    n = request.args.get('n', default=300, type=int)
    # Return last N verdicts
    history = list(gateway.alert_manager.history)[-n:]
    return jsonify({'history': history}), 200

@app.route('/api/control/pause', methods=['POST'])
def pause():
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.pause()
        gateway.watchdog_enabled = False # Suspend watchdog
    return jsonify({'status': 'paused'}), 200

@app.route('/api/control/resume', methods=['POST'])
def resume():
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.resume()
        gateway.last_rx_wall = time.monotonic() # Reset watchdog timer
        gateway.watchdog_enabled = True
    return jsonify({'status': 'resumed'}), 200

@app.route('/api/control/speed', methods=['POST'])
def set_speed():
    data = request.get_json()
    speed = float(data.get('speed', 1.0))
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.set_speed(speed)
        cfg.simulation.time_scale = speed # Watchdog reads this dynamically
    return jsonify({'status': 'ok', 'speed': speed}), 200

@app.route('/api/control/reset', methods=['POST'])
def ui_reset():
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.reset(cfg.tank.initial_level_m)
        gateway.reset(cfg.tank.initial_level_m, "demo_run_reset")
    return jsonify({'status': 'reset'}), 200

@app.route('/demo/attack/start', methods=['POST'])
def start_attack():
    if not app.config.get('demo_mode', False):
        return jsonify({'error': 'Demo mode disabled'}), 404
    data = request.get_json()
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.injector.start_attack(
            attack_type=data.get('type'),
            start_time=control.plant.simulation_time_s,
            duration=data.get('duration', 60.0),
            magnitude=data.get('magnitude', 0.0),
            stealth=data.get('stealth', False),
            target_command=data.get('target_command'),
            target_valve=data.get('target_valve'),
            drop_prob=data.get('drop_prob', 1.0)
        )
    return jsonify({'status': 'attack started'}), 200

@app.route('/demo/attack/stop', methods=['POST'])
def stop_attack():
    if not app.config.get('demo_mode', False):
        return jsonify({'error': 'Demo mode disabled'}), 404
    control = app.config.get('PLANT_CONTROL')
    if control:
        control.injector.stop_attack()
    return jsonify({'status': 'attack stopped'}), 200

@app.route('/demo/truth/stream', methods=['GET'])
def stream_truth():
    if not app.config.get('demo_truth_enabled', False):
        return "Demo truth disabled", 404
        
    def generate():
        q = hub.subscribe()
        try:
            while True:
                msg = q.get()
                if msg.get('event') == 'truth':
                    yield f"data: {json.dumps(msg['data'])}\n\n"
        finally:
            hub.unsubscribe(q)
            
    return Response(generate(), mimetype='text/event-stream')

@app.route('/')
def index():
    return app.send_static_file('defender.html')

if __name__ == '__main__':
    app.run(port=cfg.network.scada_port, debug=False, use_reloader=False, threaded=True)
