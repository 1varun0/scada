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

@pytest.mark.parametrize("dos_gap_rule", [False, True])
def test_mode_independence(hub, dos_gap_rule):
    """Verify IDS anomaly scores and verdicts are strictly identical between Monitor and Prevention modes."""
    cfg = load_config()
    cfg.ids.dos_gap_rule = dos_gap_rule
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
    cfg.simulation.clamp_flow_noise = False
    
    plant = LivePlant(cfg, standalone_mode=False)
    gw = GatewayCore(cfg, hub)
    gw.current_run_id = "live_run"
    gw.set_mode("prevention")
    gw.set_auto_handback(False)  # Keep twin control forced for stability test
    gw.twin_takeover_active = True  # Force continuous twin estimator control
    
    true_levels = []
    twin_levels = []
    
    for t in range(1800):
        obs = plant.observe()
        cmds = gw.process_sense(obs)
        assert cmds["level_source"] == "twin"
        
        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        gw.process_telemetry(pkt)
        
        true_levels.append(plant.tank.level)
        twin_levels.append(gw.ids.get_twin_estimate())
        
        # Verify plant level stays safely in operating band [0.6m, 1.4m]
        assert 0.6 <= pkt.level_m <= 1.4, f"Plant level {pkt.level_m} drifted out of bounds at t={t}"
        
    final_diff = abs(twin_levels[-1] - true_levels[-1])
    print(f"\ntest_twin_control_stability (clamp_flow_noise=False): Min True={min(true_levels):.4f}m, Max True={max(true_levels):.4f}m, Final |Twin-True|={final_diff:.4f}m ({final_diff*1000:.2f}mm)")
    
    assert plant.overflow_count == 0
    assert plant.dry_run_count == 0
    assert gw.ids.nan_guard_triggers == 0

def test_dos_recovery_no_false_takeover(hub):
    """Replay A3_003 through GatewayCore in prevention mode with dos_gap_rule=True: takeover must not persist."""
    import sqlite3
    import pandas as pd
    
    cfg = load_config()
    cfg.ids.dos_gap_rule = True
    conn = sqlite3.connect("data/scada_ids.db")
    df = pd.read_sql_query("SELECT * FROM scada_telemetry WHERE scenario_id='A3_003' ORDER BY sequence_id", conn)
    conn.close()
    
    gw = GatewayCore(cfg, hub)
    gw.current_run_id = "A3_003"
    gw.set_mode("prevention")
    gw.set_auto_handback(True)
    
    dos_rows = df[df['packet_received'] == 0]
    t_end = int(dos_rows['simulation_time_s'].max())
    
    print("\n=== test_dos_recovery_no_false_takeover: A3_003 Replay around DoS End ===")
    print(f"{'Tick':<5} | {'Rcvd':<5} | {'Alert State':<12} | {'Engines Firing':<25} | {'Takeover':<9} | {'Action':<15} | {'|Diff|':<7}")
    
    post_dos_takeover_ticks = []
    
    for _, row in df.iterrows():
        t = int(row['simulation_time_s'])
        rcvd = bool(row['packet_received'] == 1)
        pkt = TelemetryPacket(
            run_id="A3_003", seq=int(row['sequence_id']), ts=float(row['simulation_time_s']),
            src_t=float(row['simulation_time_s']), received=rcvd,
            level_m=float(row['tank_level_observed']), q_in=float(row['q_in']), q_out=float(row['q_out']),
            pump_cmd=int(row['pump_command']), valve_cmd=float(row['valve_command']),
            pump_on=bool(row['pump_state'] == 1), valve_pct=float(row['valve_state'])
        )
        v = gw.process_telemetry(pkt)
        twin_est = gw.ids.get_twin_estimate()
        diff = abs(pkt.level_m - twin_est)
        
        if t_end - 5 <= t <= t_end + 15:
            firing_str = str(v.get('engines_firing', []))
            print(f"{t:<5d} | {str(rcvd):<5} | {v['alert_state']:<12} | {firing_str:<25} | {str(gw.twin_takeover_active):<9} | {gw.last_action_taken:<15} | {diff:<7.4f}")
            
        if t > t_end and gw.twin_takeover_active:
            post_dos_takeover_ticks.append(t)
            
    print(f"Post-DoS takeover active ticks (Step 2b rule ON): {len(post_dos_takeover_ticks)} / {len(df[df['simulation_time_s'] > t_end])}")
    # With Step 2b rule ON, twin re-seeds to median level post-DoS and takeover does NOT persist
    assert len(post_dos_takeover_ticks) == 0, f"Expected 0 post-DoS takeover ticks, got {len(post_dos_takeover_ticks)}"

def test_live_dos_60s_reseed(hub):
    """Verify live telemetry-only DoS of 60s with Step 2b rule ON vs OFF."""
    cfg = load_config()
    
    def run_sim(rule_on: bool):
        cfg.ids.dos_gap_rule = rule_on
        gw = GatewayCore(cfg, hub)
        gw.current_run_id = "live_dos_60s"
        gw.set_mode("prevention")
        gw.set_auto_handback(True)
        plant = LivePlant(cfg, standalone_mode=True)
        plant.run_id = "live_dos_60s"
        
        err_before, err_at, err_30s_post = None, None, None
        for t in range(200):
            obs = plant.observe()
            ctrl = plant.controller.step(obs)
            pkt = plant.advance(ctrl["pump_command"], ctrl["valve_command"])
            pkt.run_id = "live_dos_60s"
            
            if 100 <= t < 160:
                synth = TelemetryPacket(
                    run_id="live_dos_60s", seq=t, ts=float(t), src_t=float(t), received=False,
                    level_m=pkt.level_m, q_in=0.0, q_out=0.0, pump_cmd=0, valve_cmd=0.0,
                    pump_on=False, valve_pct=0.0
                )
                gw.process_telemetry(synth)
            else:
                gw.process_telemetry(pkt)
                
            err = abs(pkt.level_m - gw.ids.get_twin_estimate())
            if t == 99:
                err_before = err
            elif t == 159:
                err_at = err
            elif t == 190:
                err_30s_post = err
        return err_before, err_at, err_30s_post

    b_off, at_off, post_off = run_sim(rule_on=False)
    b_on, at_on, post_on = run_sim(rule_on=True)
    
    print(f"\nLive DoS 60s (Rule OFF): Before={b_off:.4f}m, At End={at_off:.4f}m, 30s Post={post_off:.4f}m")
    print(f"Live DoS 60s (Rule ON ): Before={b_on:.4f}m, At End={at_on:.4f}m, 30s Post={post_on:.4f}m")
    
    # Before DoS, error is low for both
    assert b_off < 0.02 and b_on < 0.02
    # At end of DoS, twin fell behind in both
    assert at_off > 0.035 and at_on > 0.035
    # 30s after DoS: Rule OFF stays diverged (>0.035m); Rule ON re-seeds to near-zero (<0.015m)
    assert post_off > 0.035
    assert post_on < 0.015

def test_dos_followed_by_fdi_step_refusal(hub):
    """Verify DoS 30s followed by an out-of-band FDI step is REFUSED and physics keeps firing.
    
    Note: If the spoofed level falls within v_max * G * dt + 3 * sigma, it is adopted.
    This rule only bounds physically impossible jumps; the command-driven shadow estimator
    (Phase 6c) is the true structural fix.
    """
    cfg = load_config()
    cfg.ids.dos_gap_rule = True
    gw = GatewayCore(cfg, hub)
    gw.current_run_id = "dos_fdi_test"
    gw.set_mode("prevention")
    gw.set_auto_handback(True)
    plant = LivePlant(cfg, standalone_mode=True)
    plant.run_id = "dos_fdi_test"
    
    G = 30
    dt = float(cfg.simulation.dt_s)
    sigma = float(cfg.simulation.sensor_noise_level_m)
    v_max = max(cfg.pump.q_max_m3s / cfg.tank.cross_section_area_m2,
                cfg.valve.flow_coefficient_m3s * (cfg.tank.max_height_m**0.5) / cfg.tank.cross_section_area_m2)
    band = v_max * G * dt + 3.0 * sigma
    print(f"\nTest DoS 30s + FDI Refusal: G={G}, v_max={v_max:.6f} m/s, Physical Band={band:.4f}m")
    
    # Apply a +0.20m FDI step exceeding the physical band (~0.1099m)
    spoof_offset = 0.20
    physics_firing_ticks = []
    
    for t in range(120):
        obs = plant.observe()
        ctrl = plant.controller.step(obs)
        pkt = plant.advance(ctrl["pump_command"], ctrl["valve_command"])
        pkt.run_id = "dos_fdi_test"
        
        if 50 <= t < 80:
            synth = TelemetryPacket(
                run_id="dos_fdi_test", seq=t, ts=float(t), src_t=float(t), received=False,
                level_m=pkt.level_m, q_in=0.0, q_out=0.0, pump_cmd=0, valve_cmd=0.0,
                pump_on=False, valve_pct=0.0
            )
            v = gw.process_telemetry(synth)
        elif t >= 80:
            spoofed = TelemetryPacket(
                run_id="dos_fdi_test", seq=t, ts=float(t), src_t=float(t), received=True,
                level_m=pkt.level_m + spoof_offset, q_in=pkt.q_in, q_out=pkt.q_out,
                pump_cmd=pkt.pump_cmd, valve_cmd=pkt.valve_cmd,
                pump_on=pkt.pump_on, valve_pct=pkt.valve_pct
            )
            v = gw.process_telemetry(spoofed)
            if "physics" in v.get("engines_firing", []):
                physics_firing_ticks.append(t)
        else:
            v = gw.process_telemetry(pkt)
            
    # Twin must NOT adopt the spoofed level (difference to true level remains bounded)
    final_twin = gw.ids.get_twin_estimate()
    final_true = plant.tank.level
    assert abs(final_twin - final_true) < 0.05, f"Twin adopted spoofed level! Twin={final_twin}, True={final_true}"
    # Physics must keep firing after collection window finishes
    assert len(physics_firing_ticks) >= 30, f"Physics did not keep firing: {len(physics_firing_ticks)} ticks"
    assert gw.twin_takeover_active, "Twin takeover should be active under FDI attack"

