import pytest
import time
import threading
import json
import requests
import queue
import sseclient
from scada_live.scada_ids.server import app, gateway, hub
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.plant_sim.plant import LivePlant
from scada_live.plant_sim.gateway_client import GatewayClient
from scada_live.common.config_loader import load_config
from scada_live.common.packets import TelemetryPacket

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_gateway_parity(client):
    """Test 1: Push a packet through Flask's test client, verify it doesn't crash."""
    # Basic ping test
    resp = client.post('/api/sense', json={'seq': 1, 'run_id': 'test', 'ts': 0.0, 'level_m': 1.0})
    assert resp.status_code == 200
    cmds = resp.json
    assert 'pump_cmd' in cmds
    assert 'valve_cmd' in cmds
    
    pkt = {
        'seq': 1,
        'run_id': 'test',
        'ts': 0.0,
        'src_t': 0.0,
        'received': True,
        'level_m': 1.0,
        'q_in': 0.01,
        'q_out': 0.01,
        'pump_on': False,
        'pump_cmd': cmds['pump_cmd'],
        'valve_pct': 50.0,
        'valve_cmd': cmds['valve_cmd']
    }
    
    resp = client.post('/api/telemetry', json=pkt)
    assert resp.status_code == 200

def test_validation(client):
    """Test 7: Validation malformed bodies return 400"""
    resp = client.post('/api/telemetry', json={})
    assert resp.status_code == 400
    
    resp = client.post('/api/telemetry', json={'invalid': True})
    assert resp.status_code == 400
    
def test_liveplant_through_gateway():
    """Test 2: LivePlant through gateway"""
    cfg = load_config()
    plant = LivePlant(cfg, standalone_mode=False)
    
    # We will use the direct process_sense and process_telemetry to avoid needing to spin up Flask server
    plant.run_id = "test_plant"
    
    for i in range(100):
        # 1. Observe
        obs = plant.observe()
        
        # 2. Sense
        cmds = gateway.process_sense(obs)
        
        # 3. Advance
        pkt = plant.advance(cmds['pump_cmd'], cmds['valve_cmd'])
        
        # 4. Telemetry
        verdict = gateway.process_telemetry(pkt)
        
        assert verdict is not None
        assert 'is_anomaly' in verdict
        
def test_sse_hub():
    """Test 3: SSE queue management"""
    q1 = hub.subscribe()
    q2 = hub.subscribe()
    
    hub.publish({"event": 1})
    assert q1.get() == {"event": 1}
    assert q2.get() == {"event": 1}
    
    hub.unsubscribe(q1)
    hub.publish({"event": 2})
    
def test_sense_failure():
    """Test 5: Sense failure causes plant to use failsafe."""
    cfg = load_config()
    plant = LivePlant(cfg, standalone_mode=False)
    
    # Observe but don't call gateway.process_sense
    _ = plant.observe()
    
    # If gateway offline, plant will get (None, None) from GatewayClient, so it falls back to step() fallback
    pkt = plant.step()
    
    # Fallback uses (0, default_valve_pct)
    assert pkt.pump_cmd == 0
    assert pkt.valve_cmd == cfg.controller.default_valve_pct
    
def test_watchdog_synthetic_packet():
    """Test 6: Watchdog generates synthetic packet."""
    cfg = load_config()
    cfg.gateway.watchdog_enabled = False
    hub = EventHub(queue_size=200)
    gateway = GatewayCore(cfg, hub)
    
    q = hub.subscribe()
    
    pkt = TelemetryPacket(
        seq=1, run_id="watchdog_test", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.1, q_out=0.1, pump_on=False, pump_cmd=0, valve_pct=50.0, valve_cmd=50.0
    )
    gateway.process_telemetry(pkt)
    # Drain the queue
    q.get()
    
    # 1. Test before timeout (timeout is 1.5s, clock at +1.0)
    gateway.check_watchdog(gateway.last_rx_wall + 1.0)
    assert q.empty()
    
    # 2. Test after timeout
    gateway.check_watchdog(gateway.last_rx_wall + 2.5)
    
    # Check if a synthetic packet was published
    assert not q.empty()
    synth_verdict = q.get()
    
    assert synth_verdict['received'] == False
    assert synth_verdict['t'] == 2.0

def test_watchdog_time_scale():
    """Test 7: Watchdog timeout scales with time_scale."""
    cfg = load_config()
    cfg.gateway.watchdog_enabled = False
    cfg.simulation.time_scale = 5.0
    
    hub = EventHub(queue_size=200)
    gateway = GatewayCore(cfg, hub)
    q = hub.subscribe()
    
    pkt = TelemetryPacket(
        seq=1, run_id="watchdog_test", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.1, q_out=0.1, pump_on=False, pump_cmd=0, valve_pct=50.0, valve_cmd=50.0
    )
    gateway.process_telemetry(pkt)
    q.get()
    
    # Timeout is 1.5 * (1.0 / 5.0) = 0.3s
    # Before timeout
    gateway.check_watchdog(gateway.last_rx_wall + 0.2)
    assert q.empty()
    
    # After timeout
    gateway.check_watchdog(gateway.last_rx_wall + 0.4)
    assert not q.empty()
    synth_verdict = q.get()
    assert synth_verdict['received'] == False

def test_concurrency():
    """Test 4: Reset and recalibrate under load."""
    cfg = load_config()
    hub = EventHub(queue_size=200)
    gateway = GatewayCore(cfg, hub)
    
    def worker():
        for i in range(100):
            pkt = TelemetryPacket(
                seq=i, run_id="conc_test", ts=float(i), src_t=float(i), received=True,
                level_m=1.0, q_in=0.1, q_out=0.1, pump_on=False, pump_cmd=0, valve_pct=50.0, valve_cmd=50.0
            )
            gateway.process_telemetry(pkt)
            time.sleep(0.001)
            
    t = threading.Thread(target=worker)
    t.start()
    
    for _ in range(5):
        gateway.recalibrate()
        gateway.reset(1.0, "conc_test")
        time.sleep(0.01)
        
    t.join()
    assert True # No exceptions raised

def test_soak_30min():
    """Test 8: 30 min soak test (1800 ticks)."""
    cfg = load_config()
    hub = EventHub(queue_size=2000)
    gateway = GatewayCore(cfg, hub)
    plant = LivePlant(cfg, standalone_mode=False)
    plant.run_id = "soak_test"
    
    latencies = []
    false_alarms = 0
    recent_levels = []
    
    for i in range(1800):
        start = time.perf_counter()
        
        obs = plant.observe()
        cmds = gateway.process_sense(obs)
        pkt = plant.advance(cmds['pump_cmd'], cmds['valve_cmd'])
        
        recent_levels.append(pkt.level_m)
        if len(recent_levels) > 10:
            recent_levels.pop(0)
            
        if i == 900:
            gateway.recalibrate()
            
        verdict = gateway.process_telemetry(pkt)
        
        latencies.append(time.perf_counter() - start)
        
        if not verdict['calibrating'] and verdict['is_anomaly']:
            false_alarms += 1
            
    avg_ms = (sum(latencies) / len(latencies)) * 1000
    assert avg_ms < 50.0
    assert false_alarms <= 2
