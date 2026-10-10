"""Plant simulator server — serves telemetry via SSE, accepts pump commands."""

import json
import time
import threading
from flask import Flask, request, jsonify, Response
from scada_live.common.config_loader import load_config
from scada_live.common.packets import CommandPacket
from scada_live.plant_sim.plant import LivePlant

app = Flask(__name__)
cfg = load_config()

# ─── Shared state ────────────────────────────────────────────
plant: LivePlant = None          # set in start_server()
latest_packet_dict: dict = None  # latest telemetry as dict
running = False
lock = threading.Lock()          # protects apply_command vs step

@app.route('/telemetry')
def telemetry_stream():
    """SSE feed of telemetry packets."""
    def generate():
        last_seq = -1
        while running:
            pkt = latest_packet_dict
            if pkt and pkt["seq"] > last_seq:
                last_seq = pkt["seq"]
                yield f"data: {json.dumps(pkt)}\n\n"
            time.sleep(0.05)
    return Response(generate(), mimetype='text/event-stream')

@app.route('/command', methods=['POST'])
def receive_command():
    """Receive pump commands from the SCADA gateway."""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    try:
        cmd = CommandPacket.from_dict(data)
        if cmd.cmd == "PUMP":
            with lock:
                plant.apply_command(cmd.value)
            return jsonify({"status": "accepted"})
    except Exception:
        pass
        
    return jsonify({"status": "rejected", "message": "Unknown command"}), 400

@app.route('/status')
def status():
    """Plant health check."""
    return jsonify({
        "running": running,
        "tick": plant.tick_counter if plant else 0,
        "overflow_count": plant.overflow_count if plant else 0,
        "dry_run_count": plant.dry_run_count if plant else 0,
    })

def plant_loop():
    """Main simulation loop — runs in a background thread."""
    global latest_packet_dict, running
    running = True
    while running:
        start = time.time()
        with lock:
            pkt = plant.step()
            latest_packet_dict = pkt.to_dict()

        elapsed = time.time() - start
        target = cfg.simulation.dt_s / cfg.simulation.time_scale
        time.sleep(max(0, target - elapsed))

def start_server(standalone_mode=True):
    """Initialize plant and start the server."""
    global plant
    plant = LivePlant(cfg, seed=cfg.simulation.random_seed, standalone_mode=standalone_mode)
    threading.Thread(target=plant_loop, daemon=True).start()
    app.run(host=cfg.network.plant_host, port=cfg.network.plant_port, threaded=True)

if __name__ == '__main__':
    start_server(standalone_mode=True)
