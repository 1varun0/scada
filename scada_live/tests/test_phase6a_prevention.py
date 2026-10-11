import pytest
import time
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.common.packets import TelemetryPacket
from scada_live.plant_sim.plant import LivePlant
from scada_live.scada_ids.streaming_ids import StreamingIDS

@pytest.fixture
def hub():
    return EventHub()

def test_gateway_mode(hub):
    """Verify mode switches correctly and alters level source upon critical physics alert."""
    cfg = load_config()
    gw = GatewayCore(cfg, hub)
    
    # 1. Start in monitor mode
    gw.set_mode("monitor")
    assert gw.mode == "monitor"
    
    # Normal operation
    sense_resp = gw.process_sense(1.0)
    assert sense_resp["level_source"] == "sensor"
    assert not gw.twin_takeover_active
    
    # Feed anomalous packets (FDI: level spoofed to 1.5, physics residual ~0.5m)
    for t in range(10):
        pkt = TelemetryPacket(
            run_id="fdi_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=1.5, q_in=0.002, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        gw.process_telemetry(pkt)
        
    # In monitor mode, even with CRITICAL alert, twin takeover is not engaged
    assert gw.alert_manager.state == "CRITICAL"
    assert not gw.twin_takeover_active
    sense_resp = gw.process_sense(1.5)
    assert sense_resp["level_source"] == "sensor"
    
    # 2. Switch to prevention mode
    gw.set_mode("prevention")
    assert gw.mode == "prevention"
    
    # Next packet triggers takeover
    pkt = TelemetryPacket(
        run_id="fdi_test", seq=10, ts=10.0, src_t=10.0, received=True,
        level_m=1.5, q_in=0.002, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
        pump_on=False, valve_pct=50.0
    )
    gw.process_telemetry(pkt)
    assert gw.twin_takeover_active
    
    # Now process_sense returns level from twin estimate
    sense_resp = gw.process_sense(1.5)
    assert sense_resp["level_source"] == "twin"
    assert abs(sense_resp["active_level"] - gw.ids.get_twin_estimate()) < 1e-4

def test_handback_rules(hub):
    """Verify hand-back logic respects clean_ticks, tolerance, and auto_handback flag."""
    cfg = load_config()
    gw = GatewayCore(cfg, hub)
    gw.set_mode("prevention")
    gw.set_auto_handback(True)
    
    # Trigger CRITICAL physics takeover
    for t in range(5):
        pkt = TelemetryPacket(
            run_id="hb_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=1.5, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        gw.process_telemetry(pkt)
    assert gw.twin_takeover_active
    
    # 1. Clear alert in alert manager (simulate recovery), but keep sensor level far from twin
    gw.alert_manager.acknowledge()
    twin_level = gw.ids.get_twin_estimate()
    
    # Sensor level still diverged (e.g. twin ~ 1.0, sensor = 1.2, > tolerance 0.05)
    for t in range(5, 12):
        pkt = TelemetryPacket(
            run_id="hb_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=twin_level + 0.20, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        gw.process_telemetry(pkt)
    # Should NOT hand back because level difference > tolerance
    assert gw.twin_takeover_active
    
    # 2. Sensor level matches twin within tolerance (< 0.05)
    # Feed 5 clean matching ticks
    for t in range(12, 18):
        pkt = TelemetryPacket(
            run_id="hb_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=twin_level + 0.01, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        gw.process_telemetry(pkt)
        
    # Now handback should trigger
    assert not gw.twin_takeover_active
    assert gw.last_action_taken == "handback"
    
    sense_resp = gw.process_sense(twin_level + 0.01)
    assert sense_resp["level_source"] == "sensor"

def test_mode_independence(hub):
    """Verify IDS anomaly scores and verdicts are strictly identical between Monitor and Prevention modes."""
    cfg = load_config()
    gw_mon = GatewayCore(cfg, hub)
    gw_mon.set_mode("monitor")
    
    gw_prev = GatewayCore(cfg, hub)
    gw_prev.set_mode("prevention")
    
    for t in range(50):
        # Semi-random synthetic packet sequence with occasional noise
        spoofed_lvl = 1.0 + (0.3 if 20 <= t <= 30 else 0.0)
        pkt_mon = TelemetryPacket(
            run_id="indep_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=spoofed_lvl, q_in=0.002, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        pkt_prev = TelemetryPacket(
            run_id="indep_test", seq=t, ts=float(t), src_t=float(t), received=True,
            level_m=spoofed_lvl, q_in=0.002, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
            pump_on=False, valve_pct=50.0
        )
        
        v_mon = gw_mon.process_telemetry(pkt_mon)
        v_prev = gw_prev.process_telemetry(pkt_prev)
        
        # Anomaly scoring must be 100% identical regardless of mode
        assert v_mon["is_anomaly"] == v_prev["is_anomaly"]
        assert v_mon["alert_state"] == v_prev["alert_state"]
        for engine in ["physics", "lstm", "policy", "availability"]:
            assert abs(v_mon["scores"][engine] - v_prev["scores"][engine]) < 1e-6
            
    # Also assert NaN guard counter is 0 on normal/non-DoS sequences
    assert gw_mon.ids.nan_guard_triggers == 0
    assert gw_prev.ids.nan_guard_triggers == 0

def test_twin_control_stability(hub):
    """Force twin control from t=0 on a normal 30-min run (1800s); true level stays in bounds with 0 overflows."""
    cfg = load_config()
    cfg.simulation.clamp_flow_noise = True
    
    plant = LivePlant(cfg, standalone_mode=False)
    gw = GatewayCore(cfg, hub)
    gw.current_run_id = "live_run"
    gw.set_mode("prevention")
    gw.set_auto_handback(False)  # Keep twin control forced for stability test
    gw.twin_takeover_active = True  # Force continuous twin estimator control
    
    for t in range(1800):
        obs = plant.observe()
        cmds = gw.process_sense(obs)
        assert cmds["level_source"] == "twin"
        
        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        gw.process_telemetry(pkt)
        
        # Verify plant level stays safely in operating band [0.6m, 1.4m]
        assert 0.6 <= pkt.level_m <= 1.4, f"Plant level {pkt.level_m} drifted out of bounds at t={t}"
        
    assert plant.overflow_count == 0
    assert plant.dry_run_count == 0
    assert gw.ids.nan_guard_triggers == 0
