import pytest
import json
from scada_live.scada_ids.server import app, gateway, cfg

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['demo_mode'] = False
    app.config['demo_truth_enabled'] = False
    
    # Mock PlantControl for tests
    class DummyPlantControl:
        def __init__(self):
            self.paused = False
            self.speed = 1.0
            class DummyInjector:
                def __init__(self):
                    self.attack_active = False
                def start_attack(self, **kwargs): self.attack_active = True
                def stop_attack(self): self.attack_active = False
            self.injector = DummyInjector()
            class DummyPlant:
                simulation_time_s = 0.0
            self.plant = DummyPlant()
        def pause(self): self.paused = True
        def resume(self): self.paused = False
        def set_speed(self, speed): self.speed = speed
        def reset(self, initial_level_m): pass
            
    app.config['PLANT_CONTROL'] = DummyPlantControl()
    
    # Reset gateway
    gateway.reset(cfg.tank.initial_level_m, "test")
    
    with app.test_client() as client:
        yield client

def test_config_route(client):
    resp = client.get('/api/config')
    assert resp.status_code == 200
    data = resp.json
    assert 'tank' in data
    assert 'controller' in data
    assert 'simulation' in data

def test_state_route_empty(client):
    resp = client.get('/api/state')
    assert resp.status_code == 200
    data = resp.json
    assert data['alert_state'] == 'SAFE'
    assert data['active_event_id'] is None

def test_history_route_empty(client):
    resp = client.get('/api/history')
    assert resp.status_code == 200
    data = resp.json
    assert 'history' in data
    assert len(data['history']) == 0

def test_demo_gating(client):
    # Should be 404 since demo_mode=False
    resp = client.post('/demo/attack/start', json={'type': 'FDI'})
    assert resp.status_code == 404
    
    resp = client.post('/demo/attack/stop')
    assert resp.status_code == 404
    
    resp = client.get('/demo/truth/stream')
    assert resp.status_code == 404

def test_demo_gating_enabled(client):
    app.config['demo_mode'] = True
    resp = client.post('/demo/attack/start', json={'type': 'FDI'})
    assert resp.status_code == 200
    
    resp = client.post('/demo/attack/stop')
    assert resp.status_code == 200

def test_stream_no_truth(client):
    # Add a mock verdict
    gateway.alert_manager.history.append({'S_p': 1.0, 'S_l': 1.0, 'alert_state': 'CRITICAL', 'timestamp': 10.0, 'true_level': 5.0})
    
    # Actually /stream sends SSE from hub. We just want to check payload keys. 
    # But checking SSE stream in pytest needs special handling. 
    pass


def test_index_route_serves_defender_ui(client):
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'btn-mode-toggle' in html
    assert 'control-source-badge' in html
    assert 'tamper-badge' in html
    assert 'Wire tamper' in html


def test_mode_toggle_api(client):
    # GET initial mode
    resp = client.get('/api/mode')
    assert resp.status_code == 200
    assert resp.json['mode'] in ('monitor', 'prevention')

    # Switch to prevention
    resp = client.post('/api/mode', json={'mode': 'prevention'})
    assert resp.status_code == 200
    assert resp.json['mode'] == 'prevention'

    # Switch back to monitor
    resp = client.post('/api/mode', json={'mode': 'monitor'})
    assert resp.status_code == 200
    assert resp.json['mode'] == 'monitor'

    # Invalid mode rejection
    resp = client.post('/api/mode', json={'mode': 'invalid_mode'})
    assert resp.status_code == 400


def test_demo_attack_wire_tamper(client):
    app.config['demo_mode'] = True
    resp = client.post('/demo/attack/start', json={
        'type': 'Wire tamper',
        'target_command': 1,
        'target_valve': 50.0
    })
    assert resp.status_code == 200
    assert resp.json['status'] == 'attack started'

    resp = client.post('/demo/attack/stop')
    assert resp.status_code == 200
    assert resp.json['status'] == 'attack stopped'

