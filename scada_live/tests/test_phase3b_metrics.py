import pytest
from scada_live.scada_ids.metrics import MetricsCollector

def test_metrics_correctness():
    """Test 5: Metrics correctness."""
    m = MetricsCollector(grace_period_s=1.5)
    
    # Tick 1: Normal
    m.update_truth("run1", 1, 1.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 1, 1.0, False, "SAFE", False)
    
    # Tick 2: Spurious alert
    m.update_truth("run1", 2, 2.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 2, 2.0, True, "CRITICAL", False)
    
    # Tick 3: Normal
    m.update_truth("run1", 3, 3.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 3, 3.0, False, "SAFE", False)
    
    # Tick 4-5: Real attack, detected
    m.update_truth("run1", 4, 4.0, 1.0, True, "DoS", False, False)
    m.update_verdict("run1", 4, 4.0, True, "CRITICAL", False)
    m.update_truth("run1", 5, 5.0, 1.0, True, "DoS", False, False)
    m.update_verdict("run1", 5, 5.0, True, "CRITICAL", False)
    
    # Tick 6-7: Grace period (no attack, still critical)
    m.update_truth("run1", 6, 6.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 6, 6.0, True, "CRITICAL", False)
    m.update_truth("run1", 7, 7.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 7, 7.0, True, "CRITICAL", False)
    
    # Tick 8: Lingering alert
    m.update_truth("run1", 8, 8.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 8, 8.0, True, "CRITICAL", False)
    
    # Tick 9: Real attack, missed
    m.update_truth("run1", 9, 9.0, 1.0, True, "FDI", False, False)
    m.update_verdict("run1", 9, 9.0, False, "SAFE", False)
    
    # Tick 10: End
    m.update_truth("run1", 10, 10.0, 1.0, False, "None", False, False)
    m.update_verdict("run1", 10, 10.0, False, "SAFE", False)
    
    metrics = m.get_metrics()
    
    assert metrics["spurious_alerts"] == 1
    assert metrics["lingering_alerts"] == 1
    assert metrics["missed_attacks"] == 1
    
    episodes = metrics["episodes"]
    assert len(episodes) == 2
    
    assert episodes[0]["type"] == "DoS"
    assert episodes[0]["detected"] == True
    
    assert episodes[1]["type"] == "FDI"
    assert episodes[1]["detected"] == False
