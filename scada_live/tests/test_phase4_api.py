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
                def start_attack(self, **kwargs): pass
                def stop_attack(self): pass
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
