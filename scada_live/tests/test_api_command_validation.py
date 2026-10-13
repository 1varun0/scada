import pytest
import json
import os
from types import SimpleNamespace
from scada_live.scada_ids.server import app, cfg

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Ensure no residual test secret
    app.config.pop('SHARED_SECRET', None)
    app.config.pop('SCADA_CONFIG', None)
    if 'SCADA_SHARED_SECRET' in os.environ:
        del os.environ['SCADA_SHARED_SECRET']
    with app.test_client() as client:
        yield client
    app.config.pop('SHARED_SECRET', None)
    app.config.pop('SCADA_CONFIG', None)
    if 'SCADA_SHARED_SECRET' in os.environ:
        del os.environ['SCADA_SHARED_SECRET']

def test_non_json_request(client):
    """Non-JSON content type must return 400."""
    resp = client.post('/api/command', data="pump_cmd=1&valve_cmd=50", content_type="application/x-www-form-urlencoded")
    assert resp.status_code == 400
    assert "JSON" in resp.json.get("details", "")

def test_malformed_json_request(client):
    """Malformed JSON body must return 400."""
    resp = client.post('/api/command', data="{pump_cmd: 1, invalid", content_type="application/json")
    assert resp.status_code == 400

def test_non_dict_json_request(client):
    """JSON payload that is a list or scalar must return 400."""
    resp = client.post('/api/command', json=[1, 2, 3])
    assert resp.status_code == 400
    resp2 = client.post('/api/command', json="just a string")
    assert resp2.status_code == 400

def test_missing_required_fields(client):
    """Missing pump_cmd or valve_cmd must return 400."""
    resp = client.post('/api/command', json={"valve_cmd": 50.0})
    assert resp.status_code == 400
    assert "Missing" in resp.json.get("details", "")

    resp2 = client.post('/api/command', json={"pump_cmd": 1})
    assert resp2.status_code == 400
    assert "Missing" in resp2.json.get("details", "")

    resp3 = client.post('/api/command', json={})
    assert resp3.status_code == 400

def test_wrong_field_types(client):
    """Boolean, string, and wrong types must return 400."""
    # pump_cmd cannot be boolean True/False
    resp = client.post('/api/command', json={"pump_cmd": True, "valve_cmd": 50.0})
    assert resp.status_code == 400
    assert "pump_cmd" in resp.json.get("details", "")

    # pump_cmd cannot be string
    resp = client.post('/api/command', json={"pump_cmd": "1", "valve_cmd": 50.0})
    assert resp.status_code == 400

    # pump_cmd cannot be float
    resp = client.post('/api/command', json={"pump_cmd": 1.0, "valve_cmd": 50.0})
    assert resp.status_code == 400

    # valve_cmd cannot be boolean
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": True})
    assert resp.status_code == 400

    # valve_cmd cannot be string
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": "50.0"})
    assert resp.status_code == 400

    # hold_ticks cannot be boolean, string, or float
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": True})
    assert resp.status_code == 400

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": "10"})
    assert resp.status_code == 400

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 10.5})
    assert resp.status_code == 400

def test_out_of_range_values(client):
    """Values outside valid physical / operational bounds must return 400."""
    # pump_cmd must be 0 or 1
    resp = client.post('/api/command', json={"pump_cmd": 2, "valve_cmd": 50.0})
    assert resp.status_code == 400

    resp = client.post('/api/command', json={"pump_cmd": -1, "valve_cmd": 50.0})
    assert resp.status_code == 400

    # valve_cmd must be between 0.0 and 100.0
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": -0.1})
    assert resp.status_code == 400

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 100.1})
    assert resp.status_code == 400

    # hold_ticks must be >= 1
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 0})
    assert resp.status_code == 400

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": -5})
    assert resp.status_code == 400

def test_valid_commands_and_default_hold(client):
    """Valid commands accept boundary inputs, validate schema, and default hold_ticks to 1."""
    # Valid low boundary (pump 0, safe valve 0.0)
    resp = client.post('/api/command', json={"pump_cmd": 0, "valve_cmd": 0.0})
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["pump_cmd"] == 0
    assert resp.json["valve_cmd"] == 0.0
    assert resp.json["hold_ticks"] == 1
    assert resp.json["capped"] is False
    assert resp.json["authenticated"] is False

    # Valid normal command (pump 1, default valve 50.0)
    resp2 = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0})
    assert resp2.status_code == 200
    assert resp2.json["status"] == "accepted"
    assert resp2.json["pump_cmd"] == 1
    assert resp2.json["valve_cmd"] == 50.0
    assert resp2.json["hold_ticks"] == 1
    assert resp2.json["capped"] is False

def test_unauthenticated_hold_cap(client):
    """Unauthenticated requests must be capped to 60 ticks with capped=True when requested > 60."""
    # Requested hold <= 60 is preserved
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 45})
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 45
    assert resp.json["capped"] is False
    assert resp.json["authenticated"] is False

    # Requested hold > 60 is capped to 60
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 500})
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 60
    assert resp.json["capped"] is True
    assert resp.json["authenticated"] is False

def test_authenticated_hold_bearer_and_api_key(client):
    """Authenticated requests with valid secret injected by tests are uncapped with capped=False."""
    # Inject test secret via app.config
    app.config['SHARED_SECRET'] = "phase6b_test_secret"

    # Bearer token
    headers_bearer = {"Authorization": "Bearer phase6b_test_secret"}
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 500}, headers=headers_bearer)
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 500
    assert resp.json["capped"] is False
    assert resp.json["authenticated"] is True

    # X-API-Key header
    headers_api_key = {"X-API-Key": "phase6b_test_secret"}
    resp = client.post('/api/command', json={"pump_cmd": 0, "valve_cmd": 50.0, "hold_ticks": 300}, headers=headers_api_key)
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 300
    assert resp.json["capped"] is False
    assert resp.json["authenticated"] is True

def test_wrong_secret_capped(client):
    """Invalid secret fails authentication and caps hold to 60."""
    app.config['SHARED_SECRET'] = "phase6b_test_secret"
    headers = {"Authorization": "Bearer wrong_secret"}
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 500}, headers=headers)
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 60
    assert resp.json["capped"] is True
    assert resp.json["authenticated"] is False

def test_missing_config_secret_fails_closed(client):
    """If shared_secret is missing or empty in configuration, fail closed (cap all callers)."""
    # No secret set in config or env
    app.config.pop('SHARED_SECRET', None)
    test_cfg = SimpleNamespace(api=SimpleNamespace(shared_secret=""))
    app.config['SCADA_CONFIG'] = test_cfg

    try:
        headers = {"Authorization": "Bearer phase6b_test_secret"}
        resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 500}, headers=headers)
        assert resp.status_code == 200
        assert resp.json["status"] == "accepted"
        assert resp.json["hold_ticks"] == 60
        assert resp.json["capped"] is True
        assert resp.json["authenticated"] is False
    finally:
        app.config.pop('SCADA_CONFIG', None)

def test_actor_role_does_not_bypass_cap(client):
    """X-Actor-Role is strictly metadata and must never bypass the 60-tick cap."""
    headers = {"X-Actor-Role": "admin"}
    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 500}, headers=headers)
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted"
    assert resp.json["hold_ticks"] == 60
    assert resp.json["capped"] is True
    assert resp.json["authenticated"] is False
    assert resp.json["role"] == "admin"
