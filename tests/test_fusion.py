import pytest
from engines.fusion_engine import FusionEngine

def test_fusion_engine():
    engine = FusionEngine(w_p=0.4, w_l=0.3, w_c=0.2, w_a=0.1, tau_fusion=0.5)
    
    # Normal state
    score, anomaly = engine.evaluate(s_p=0.0, s_l=0.0, s_c=0.0, s_a=0.0)
    assert score == 0.0
    assert anomaly == 0
    
    # Physics anomaly only (score = 0.4)
    score, anomaly = engine.evaluate(s_p=1.0, s_l=0.0, s_c=0.0, s_a=0.0)
    assert score == 0.4
    assert anomaly == 0 # 0.4 is not > 0.5
    
    # Physics + Temporal anomaly (score = 0.7)
    score, anomaly = engine.evaluate(s_p=1.0, s_l=1.0, s_c=0.0, s_a=0.0)
    assert score == 0.7
    assert anomaly == 1 # 0.7 > 0.5

def test_fusion_engine_normalization():
    # Weights sum to 2.0 instead of 1.0
    engine = FusionEngine(w_p=0.8, w_l=0.6, w_c=0.4, w_a=0.2, tau_fusion=0.5)
    
    # Should be normalized to 0.4, 0.3, 0.2, 0.1
    assert engine.w_p == pytest.approx(0.4)
    assert engine.w_l == pytest.approx(0.3)
    
    score, anomaly = engine.evaluate(s_p=1.0, s_l=0.0, s_c=0.0, s_a=0.0)
    assert score == pytest.approx(0.4)
    assert anomaly == 0
