import pytest
from scada_live.scada_ids.alert_manager import AlertManager
from scada_live.common.config_loader import load_config
from types import SimpleNamespace

@pytest.fixture
def cfg():
    c = load_config()
    c.alert.n_flags = 3
    c.alert.window_w = 5
    c.alert.m_clear = 5
    return c

def test_state_machine(cfg):
    """Test 1: State machine table test."""
    am = AlertManager(cfg)
    
    # Single blip: SAFE -> SUSPICIOUS -> SAFE
    v = am.update(1, 1.0, True, ["physics"], True, False, 0.5)
    assert v['alert_state'] == "SUSPICIOUS"
    
    # 5 clean ticks clears it
    for i in range(2, 7):
        v = am.update(i, float(i), False, [], True, False, 0.0)
    assert v['alert_state'] == "SAFE"
    
    # 3 in 5 -> CRITICAL
    am.update(10, 10.0, True, ["physics"], True, False, 0.5)
    am.update(11, 11.0, False, [], True, False, 0.0)
    am.update(12, 12.0, True, ["physics"], True, False, 0.5)
    assert am.state == "SUSPICIOUS"
    v = am.update(13, 13.0, True, ["physics"], True, False, 0.5)
    assert v['alert_state'] == "CRITICAL"
    assert v['latched'] == True
    
def test_latch_and_ack(cfg):
    """Test 2: Latch and ack."""
    am = AlertManager(cfg)
    
    for i in range(3):
        am.update(i, float(i), True, ["physics"], True, False, 0.5)
        
    assert am.state == "CRITICAL"
    
    # Clean ticks don't clear it
    for i in range(3, 13):
        v = am.update(i, float(i), False, [], True, False, 0.0)
        
    assert v['alert_state'] == "CRITICAL"
    
    # Ack clears it
    am.acknowledge()
    assert am.state == "SAFE"

def test_attribution(cfg):
    """Test 3: Attribution table."""
    am = AlertManager(cfg)
    
    # Availability + received=False -> DoS
    v = am.update(1, 1.0, True, ["availability"], False, False, 0.0)
    assert v['attack_type'] == "DoS"
    am.reset()
    
    # Availability + stale -> Replay
    v = am.update(1, 1.0, True, ["availability"], True, True, 0.0)
    assert v['attack_type'] == "Replay"
    am.reset()
    
    # Policy -> Auth misuse
    v = am.update(1, 1.0, True, ["policy"], True, False, 0.0)
    assert v['attack_type'] == "Auth misuse"
    am.reset()
    
    # Physics -> Sensor/process inconsistency
    v = am.update(1, 1.0, True, ["physics"], True, False, 0.0)
    assert v['attack_type'] == "Sensor/process inconsistency"
    am.reset()
    
    # Multi-engine -> highest priority
    v = am.update(1, 1.0, True, ["physics", "policy", "availability"], False, False, 0.0)
    assert v['attack_type'] == "DoS"
