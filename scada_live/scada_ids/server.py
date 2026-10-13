import json
import time
import os
import hmac
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
    data = gateway.metrics.get_metrics()
    data["commands"] = {
        "received": gateway.commands_received,
        "blocked": gateway.commands_blocked,
        "would_block": gateway.commands_would_block,
        "holds_dropped": gateway.holds_dropped,
        "holds_would_drop": gateway.holds_would_drop,
        "wire_tamper_alerts": gateway.wire_tamper_alerts
    }
    return jsonify(data)

@app.route('/api/mode', methods=['GET', 'POST'])
def mode():
    if request.method == 'GET':
        return jsonify({"status": "ok", "mode": gateway.mode}), 200
    data = request.get_json(silent=True) or {}
    new_mode = data.get('mode', 'monitor')
    if new_mode not in ('monitor', 'prevention'):
        return jsonify({"error": "mode must be 'monitor' or 'prevention'"}), 400
    gateway.set_mode(new_mode)
    return jsonify({"status": "ok", "mode": new_mode}), 200

@app.route('/api/command', methods=['POST'])
def handle_command():
    if not request.is_json:
        return jsonify({"error": "Bad Request", "details": "Request body must be JSON"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Bad Request", "details": "Invalid JSON format"}), 400

    # 1. Schema & Field Type Validation
    if 'pump_cmd' not in data or 'valve_cmd' not in data:
        return jsonify({"error": "Bad Request", "details": "Missing required fields 'pump_cmd' or 'valve_cmd'"}), 400

    pump_cmd_val = data['pump_cmd']
    valve_cmd_val = data['valve_cmd']

    # Reject boolean for pump_cmd and ensure it is integer 0 or 1
    if isinstance(pump_cmd_val, bool) or not isinstance(pump_cmd_val, int) or pump_cmd_val not in (0, 1):
        return jsonify({"error": "Bad Request", "details": "pump_cmd must be 0 or 1"}), 400
    pump_cmd = int(pump_cmd_val)

    # Reject boolean for valve_cmd and ensure it is numeric between 0.0 and 100.0
    if isinstance(valve_cmd_val, bool) or not isinstance(valve_cmd_val, (int, float)):
        return jsonify({"error": "Bad Request", "details": "valve_cmd must be numeric between 0.0 and 100.0"}), 400
    valve_cmd = float(valve_cmd_val)
    if not (0.0 <= valve_cmd <= 100.0):
        return jsonify({"error": "Bad Request", "details": "valve_cmd must be between 0.0 and 100.0"}), 400

    hold_ticks_val = data.get('hold_ticks', 1)
    if isinstance(hold_ticks_val, bool) or not isinstance(hold_ticks_val, int) or hold_ticks_val <= 0:
        return jsonify({"error": "Bad Request", "details": "hold_ticks must be a positive integer"}), 400
    requested_hold_ticks = int(hold_ticks_val)

    # 2. Hold Duration Cap for Non-Authenticated Callers (Fail-Closed, hmac.compare_digest)
    # Check untracked config sources: env var SCADA_SHARED_SECRET, app.config['SHARED_SECRET'], app.config['SCADA_CONFIG']
    shared_secret = os.environ.get("SCADA_SHARED_SECRET", "")
    if not shared_secret and app.config.get('SHARED_SECRET'):
        shared_secret = str(app.config['SHARED_SECRET'])
    if not shared_secret:
        cfg_obj = app.config.get('SCADA_CONFIG', cfg)
        api_cfg = getattr(cfg_obj, 'api', None) if cfg_obj else None
        if api_cfg and getattr(api_cfg, 'shared_secret', None):
            shared_secret = str(api_cfg.shared_secret)
    shared_secret = shared_secret.strip()

    is_authenticated = False
    if shared_secret:
        auth_header = request.headers.get('Authorization', '')
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        api_key = request.headers.get('X-API-Key', '').strip()
        is_authenticated = (
            (bool(bearer_token) and hmac.compare_digest(bearer_token, shared_secret))
            or (bool(api_key) and hmac.compare_digest(api_key, shared_secret))
        )

    if not is_authenticated:
        effective_hold_ticks = min(requested_hold_ticks, 60)
        is_capped = (requested_hold_ticks > 60)
    else:
        effective_hold_ticks = requested_hold_ticks
        is_capped = False

    # Metadata role attribute for telemetry logging ONLY (MUST NOT be used in validation)
    role = request.headers.get('X-Actor-Role', 'unauthenticated')

    # 3. Gateway Ingress Filtering & Mode Handling
    gateway.commands_received += 1
    is_valid, reason = gateway.evaluate_ingress_command(
        pump_cmd, valve_cmd, effective_hold_ticks, role
    )

    if not is_valid:
        if gateway.mode == "monitor":
            # Monitor: dispatch would_block, record metric, pass through
            gateway.commands_would_block += 1
            hub.publish({
                "event_type": "Auth misuse",
                "source": "command_filter",
                "action": "would_block",
                "pump_cmd": pump_cmd,
                "valve_cmd": valve_cmd,
                "reason": reason,
                "role": role
            })
            gateway.apply_override(pump_cmd, valve_cmd, effective_hold_ticks)
            return jsonify({
                "status": "accepted_monitor",
                "would_block": True,
                "reason": reason,
                "hold_ticks": effective_hold_ticks,
                "pump_cmd": pump_cmd,
                "valve_cmd": valve_cmd,
                "capped": is_capped,
                "authenticated": is_authenticated,
                "role": role
            }), 200
        else:
            # Prevention: block at ingress
            gateway.commands_blocked += 1
            hub.publish({
                "event_type": "Auth misuse",
                "source": "command_filter",
                "action": "command_blocked",
                "pump_cmd": pump_cmd,
                "valve_cmd": valve_cmd,
                "reason": reason,
                "role": role
            })
            return jsonify({
                "status": "blocked",
                "reason": reason
            }), 403

    # Valid command — apply hold
    gateway.apply_override(pump_cmd, valve_cmd, effective_hold_ticks)
    return jsonify({
        "status": "accepted",
        "hold_ticks": effective_hold_ticks,
        "pump_cmd": pump_cmd,
        "valve_cmd": valve_cmd,
        "capped": is_capped,
        "authenticated": is_authenticated,
        "role": role
    }), 200


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
        if control.injector.attack_active:
            return jsonify({'error': 'Attack already in progress'}), 409
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
