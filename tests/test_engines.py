import pytest
import pandas as pd
from engines.physics_engine import PhysicsEngine
from engines.policy_engine import PolicyEngine
from engines.availability_engine import AvailabilityEngine

def test_physics_engine():
    engine = PhysicsEngine(tau_p=0.1)
    engine.reset(initial_level_m=1.0, area_m2=2.0, max_height_m=2.5)
    
    # Normal step: q_in = 0.005, q_out = 0.005, h_observed = 1.0, dt = 1.0
    h_twin, residual, s_p = engine.step(q_in=0.005, q_out=0.005, h_observed=1.0, dt=1.0)
    assert h_twin == 1.0
    assert residual == 0.0
    assert s_p == 0.0
    
    # FDI attack: observed is suddenly 1.5, twin should still be 1.0
    h_twin, residual, s_p = engine.step(q_in=0.005, q_out=0.005, h_observed=1.5, dt=1.0)
    assert h_twin == 1.0
    assert residual == 0.5
    # Since 0.5 > tau_p (0.1), s_p should be 1.0
    assert s_p == 1.0

def test_policy_engine():
    engine = PolicyEngine(epsilon_m=0.05)
    
    # Normal operation (no violation)
    s_c = engine.evaluate(h_observed=0.5, pump_command=0, valve_command=50.0)
    assert s_c == 0.0
    
    # Attack 1: Pump ON when tank is nearly overflowing (H > H_max - epsilon)
    # H_max is 2.5, epsilon is 0.05, so H > 2.45
    s_c = engine.evaluate(h_observed=2.46, pump_command=1, valve_command=0.0)
    assert s_c == 1.0
    
    # Attack 2: Valve opened MORE than default when tank is critically low (H < H_crit_low)
    # H_crit_low is 0.3, default valve is 50.0
    s_c = engine.evaluate(h_observed=0.2, pump_command=1, valve_command=80.0)
    assert s_c == 1.0
    
    # Safe operation: Valve at default 50% when tank is critically low should NOT flag
    s_c = engine.evaluate(h_observed=0.15, pump_command=1, valve_command=50.0)
    assert s_c == 0.0 # Normal

def test_availability_engine():
    engine = AvailabilityEngine(tau_a_ms=1500.0, tau_a_max_ms=5000.0)
    
    # Normal
    age, s_a = engine.evaluate(simulation_time_s=10.0, source_time_s=10.0, packet_received=True)
    assert age == 0.0
    assert s_a == 0.0
    
    # DoS Attack (packet not received)
    _, s_a = engine.evaluate(simulation_time_s=10.0, source_time_s=9.0, packet_received=False)
    assert s_a == 1.0
    
    # Replay Attack (old data)
    age, s_a = engine.evaluate(simulation_time_s=10.0, source_time_s=7.0, packet_received=True)
    assert age == 3000.0
    # Linear ramp: (3000 - 1500) / (5000 - 1500) = 1500 / 3500 = 0.42857...
    assert abs(s_a - (3000.0 - 1500.0) / (5000.0 - 1500.0)) < 1e-6
