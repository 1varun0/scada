"""Phase 1 tests: LivePlant matches ProcessSimulator physics."""

import pytest
from scada_live.common.config_loader import load_config
from scada_live.plant_sim.plant import LivePlant
from config.scenarios import get_scenario_by_id
from simulator.process_simulator import ProcessSimulator
from scada_live.common.packets import TelemetryPacket

@pytest.fixture
def cfg():
    return load_config()

def test_liveplant_step_produces_valid_packet(cfg):
    """LivePlant.step() returns a TelemetryPacket with all fields."""
    plant = LivePlant(cfg, standalone_mode=True)
    pkt = plant.step()
    assert isinstance(pkt, TelemetryPacket)
    assert hasattr(pkt, 'level_m')
    assert hasattr(pkt, 'q_in')
    assert hasattr(pkt, 'q_out')
    assert hasattr(pkt, 'pump_on')

def test_liveplant_standalone_level_rises_from_low(cfg):
    """With H0=0.5 and setpoint=1.0, controller turns pump ON and level rises."""
    cfg.tank.initial_level_m = 0.5
    plant = LivePlant(cfg, standalone_mode=True)
    
    pkt = plant.step()
    # level observed might be ~0.5. Pump is commanded to ON on this tick,
    # but the delay is 2 seconds (2 ticks). So pump actually turns ON after 2 steps.
    for _ in range(3):
        pkt = plant.step()
        
    assert plant.pump.state == 1
    # Check level is rising
    level1 = plant.tank.level
    for _ in range(5):
        plant.step()
    level2 = plant.tank.level
    
    assert level2 > level1

def test_liveplant_deterministic_replay(cfg):
    """Same seed produces identical telemetry sequence."""
    plant1 = LivePlant(cfg, seed=12345, standalone_mode=True)
    plant2 = LivePlant(cfg, seed=12345, standalone_mode=True)
    
    for _ in range(10):
        p1 = plant1.step()
        p2 = plant2.step()
        assert p1.level_m == p2.level_m
        assert p1.q_in == p2.q_in
        assert p1.q_out == p2.q_out

def test_liveplant_matches_process_simulator(cfg):
    """CRITICAL: Run 100 steps of LivePlant (standalone) and ProcessSimulator
    with the same seed/initial conditions. Verify observed levels, flows,
    and pump states match exactly."""
    
    scenario = get_scenario_by_id("N_001")
    scenario.duration_s = 100.0
    
    batch_sim = ProcessSimulator(scenario)
    batch_records = batch_sim.run()
    
    cfg.simulation.clamp_flow_noise = True
    live_plant = LivePlant(cfg, seed=scenario.random_seed, standalone_mode=True)
    live_records = [live_plant.step() for _ in range(100)]
    
    assert len(batch_records) == len(live_records)
    
    for b_rec, l_rec in zip(batch_records, live_records):
        assert abs(b_rec["tank_level_observed"] - l_rec.level_m) < 1e-6
        assert abs(b_rec["q_in"] - l_rec.q_in) < 1e-6
        assert abs(b_rec["q_out"] - l_rec.q_out) < 1e-6
        assert b_rec["pump_state"] == (1 if l_rec.pump_on else 0)
        assert abs(b_rec["valve_state"] - l_rec.valve_pct) < 1e-6

def test_liveplant_overflow_detection(cfg):
    """Force level to overflow and verify overflow_count increments."""
    cfg.tank.initial_level_m = cfg.tank.overflow_m
    cfg.controller.default_valve_pct = 0.0
    plant = LivePlant(cfg, standalone_mode=False)
    plant.step()
    assert plant.overflow_count == 1

def test_liveplant_apply_command(cfg):
    """In non-standalone mode, apply_command("ON") turns the pump on."""
    plant = LivePlant(cfg, standalone_mode=False)
    # Pump starts OFF. Command it ON.
    plant.apply_command("ON")
    
    # Needs delay steps to actually turn on.
    delay = int(cfg.pump.response_delay_s / cfg.simulation.dt_s)
    for _ in range(delay + 1):
        plant.step()
        
    assert plant.pump.state == 1

def test_liveplant_reset(cfg):
    """reset() returns plant to initial conditions."""
    plant = LivePlant(cfg, standalone_mode=True)
    for _ in range(5):
        plant.step()
        
    assert plant.tick_counter == 5
    
    plant.reset()
    assert plant.tick_counter == 0
    assert plant.simulation_time_s == 0.0
    assert plant.tank.level == cfg.tank.initial_level_m
