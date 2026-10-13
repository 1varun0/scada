import pytest
import os
from types import SimpleNamespace
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore, evaluate_command_with_live_setpoint
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.scada_ids.server import app, gateway, hub
from scada_live.plant_sim.plant import LivePlant
from simulator.controller import Controller


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cfg():
    return load_config()

@pytest.fixture
def test_hub():
    return EventHub()

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config.pop('SHARED_SECRET', None)
    app.config.pop('SCADA_CONFIG', None)
    if 'SCADA_SHARED_SECRET' in os.environ:
        del os.environ['SCADA_SHARED_SECRET']
    gateway.reset(1.0, "test_run")
    gateway.set_mode("monitor")
    with app.test_client() as c:
        yield c
    app.config.pop('SHARED_SECRET', None)
    app.config.pop('SCADA_CONFIG', None)
    if 'SCADA_SHARED_SECRET' in os.environ:
        del os.environ['SCADA_SHARED_SECRET']
    gateway.reset(1.0, "test_run")
    gateway.set_mode("monitor")


# ── Sub-Step 2.1: evaluate_command_with_live_setpoint Unit Tests ──────────────

class DummyController:
    def __init__(self, setpoint=1.0, deadband=0.2, default_valve=50.0):
        self.setpoint = setpoint
        self._deadband = deadband
        self._default_valve_pct = default_valve


def test_evaluate_function_valid_commands():
    """Verify valid commands within deadband and envelope pass validation."""
    ctrl = DummyController(setpoint=1.0, deadband=0.2, default_valve=50.0)
    
    # h=1.0, pump=1, valve=50 -> Valid
    ok, reason = evaluate_command_with_live_setpoint(1.0, 1, 50.0, ctrl)
    assert ok is True
    assert reason == "Valid"

    # h=1.0, pump=0, valve=50 -> Valid
    ok, reason = evaluate_command_with_live_setpoint(1.0, 0, 50.0, ctrl)
    assert ok is True
    assert reason == "Valid"

    # h=1.0, pump=0, valve=0.0 -> Valid (safe valve + pump OFF)
    ok, reason = evaluate_command_with_live_setpoint(1.0, 0, 0.0, ctrl)
    assert ok is True
    assert reason == "Valid"


def test_evaluate_function_invalid_commands():
    """Verify out-of-envelope commands fail validation with informative reasons."""
    ctrl = DummyController(setpoint=1.0, deadband=0.2, default_valve=50.0)

    # h=1.30, pump=1, valve=50 -> Blocked (pump ON above upper limit 1.25)
    ok, reason = evaluate_command_with_live_setpoint(1.30, 1, 50.0, ctrl)
    assert ok is False
    assert "Pump ON forbidden" in reason

    # h=0.70, pump=0, valve=50 -> Blocked (pump OFF below lower limit 0.75)
    ok, reason = evaluate_command_with_live_setpoint(0.70, 0, 50.0, ctrl)
    assert ok is False
    assert "Pump OFF forbidden" in reason

    # h=1.0, pump=0, valve=90 -> Blocked (invalid valve position)
    ok, reason = evaluate_command_with_live_setpoint(1.0, 0, 90.0, ctrl)
    assert ok is False
    assert "Invalid valve position" in reason

    # h=1.0, pump=1, valve=0.0 -> Blocked (safe valve position only allowed with pump OFF)
    ok, reason = evaluate_command_with_live_setpoint(1.0, 1, 0.0, ctrl)
    assert ok is False
    assert "Invalid valve position" in reason


def test_evaluate_function_boundary_cases():
    """Verify strict mathematical boundary cases at limits:
    upper = 1.0 + 0.2 + 0.05 = 1.25m
    lower = 1.0 - 0.2 - 0.05 = 0.75m
    """
    ctrl = DummyController(setpoint=1.0, deadband=0.2, default_valve=50.0)

    # h=1.25, pump=1 -> Blocked (at exact upper limit)
    ok, reason = evaluate_command_with_live_setpoint(1.25, 1, 50.0, ctrl)
    assert ok is False
    assert "Pump ON forbidden" in reason

    # h=0.75, pump=0 -> Blocked (at exact lower limit)
    ok, reason = evaluate_command_with_live_setpoint(0.75, 0, 50.0, ctrl)
    assert ok is False
    assert "Pump OFF forbidden" in reason

    # h=1.249, pump=1 -> Valid (just inside limit)
    ok, reason = evaluate_command_with_live_setpoint(1.249, 1, 50.0, ctrl)
    assert ok is True

    # h=0.751, pump=0 -> Valid (just inside limit)
    ok, reason = evaluate_command_with_live_setpoint(0.751, 0, 50.0, ctrl)
    assert ok is True


def test_evaluate_function_strict_attribute_validation():
    """Missing controller safety attributes must raise explicit AttributeError."""
    class BadController1:
        _deadband = 0.2
        _default_valve_pct = 50.0

    with pytest.raises(AttributeError, match="setpoint"):
        evaluate_command_with_live_setpoint(1.0, 1, 50.0, BadController1())

    class BadController2:
        setpoint = 1.0
        _default_valve_pct = 50.0

    with pytest.raises(AttributeError, match="_deadband"):
        evaluate_command_with_live_setpoint(1.0, 1, 50.0, BadController2())

    class BadController3:
        setpoint = 1.0
        _deadband = 0.2

    with pytest.raises(AttributeError, match="_default_valve_pct"):
        evaluate_command_with_live_setpoint(1.0, 1, 50.0, BadController3())


# ── Sub-Step 2.3 & 2.6: Ingress Filtering & Mode API Tests ────────────────────

def test_mode_toggle_api(client):
    """POST /api/mode switches mode between monitor and prevention; rejects invalid modes."""
    # Set prevention
    resp = client.post('/api/mode', json={"mode": "prevention"})
    assert resp.status_code == 200
    assert resp.json["mode"] == "prevention"
    assert gateway.mode == "prevention"

    # Get mode
    resp_get = client.get('/api/mode')
    assert resp_get.status_code == 200
    assert resp_get.json["mode"] == "prevention"

    # Set monitor
    resp = client.post('/api/mode', json={"mode": "monitor"})
    assert resp.status_code == 200
    assert resp.json["mode"] == "monitor"
    assert gateway.mode == "monitor"

    # Invalid mode rejected
    resp_bad = client.post('/api/mode', json={"mode": "super_prevention"})
    assert resp_bad.status_code == 400


def test_ingress_block_prevention_mode(client):
    """Prevention mode blocks out-of-envelope commands at ingress with HTTP 403."""
    gateway.set_mode("prevention")
    gateway.level_buffer = [1.30]  # Above 1.25m boundary

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 100})
    assert resp.status_code == 403
    assert resp.json["status"] == "blocked"
    assert "Pump ON forbidden" in resp.json["reason"]
    assert gateway.commands_blocked >= 1
    assert gateway.external_override_active is False


def test_ingress_would_block_monitor_mode(client):
    """Monitor mode accepts out-of-envelope command with accepted_monitor, dispatches would_block, and applies override."""
    gateway.set_mode("monitor")
    gateway.level_buffer = [1.30]  # Above 1.25m boundary

    resp = client.post('/api/command', json={"pump_cmd": 1, "valve_cmd": 50.0, "hold_ticks": 100})
    assert resp.status_code == 200
    assert resp.json["status"] == "accepted_monitor"
    assert resp.json["would_block"] is True
    assert "Pump ON forbidden" in resp.json["reason"]
    assert gateway.commands_would_block >= 1
    assert gateway.external_override_active is True
    assert gateway.held_pump_cmd == 1
    assert gateway.hold_ticks_remaining == 60  # unauthenticated capped to 60


# ── Sub-Step 2.4: Continuous Enforcement Tests ────────────────────────────────

def test_continuous_enforcement_prevention_drops_hold(cfg, test_hub):
    """Prevention mode: an active hold is dropped when live plant level breaches the safety limit."""
    gw = GatewayCore(cfg, test_hub)
    gw.set_mode("prevention")
    gw.reset(1.0, "test_drop")
    gw.set_mode("prevention")

    # Apply valid override at nominal level 1.0m
    gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=200)
    assert gw.external_override_active is True

    # Nominal level sense: hold remains active
    res1 = gw.process_sense(1.0)
    assert res1["action_taken"] == "external_hold"
    assert res1["pump_cmd"] == 1
    assert gw.external_override_active is True

    res2 = gw.process_sense(1.20)
    assert res2["action_taken"] == "external_hold"
    assert gw.external_override_active is True

    # Level crosses limit (1.26m > 1.25m): continuous enforcement drops hold!
    res3 = gw.process_sense(1.26)
    assert gw.external_override_active is False
    assert gw.holds_dropped == 1
    # Autonomous controller resumes and, seeing h=1.26 > 1.20, commands pump OFF (0)
    assert res3["pump_cmd"] == 0


def test_continuous_enforcement_monitor_allows_hold(cfg, test_hub):
    """Monitor mode: continuous enforcement logs would_drop but allows hold to persist."""
    gw = GatewayCore(cfg, test_hub)
    gw.set_mode("monitor")
    gw.reset(1.0, "test_monitor_hold")

    # Apply valid override at nominal level 1.0m
    gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=200)
    assert gw.external_override_active is True

    # Level crosses limit (1.26m > 1.25m)
    res = gw.process_sense(1.26)
    # In monitor mode, hold is NOT dropped
    assert gw.external_override_active is True
    assert gw.holds_would_drop == 1
    assert res["action_taken"] == "external_hold"
    assert res["pump_cmd"] == 1


def test_hold_expiry_natural(cfg, test_hub):
    """A valid hold naturally decrements each tick and expires after hold_ticks ticks."""
    gw = GatewayCore(cfg, test_hub)
    gw.set_mode("prevention")
    gw.reset(1.0, "test_expiry")
    gw.set_mode("prevention")

    gw.apply_override(pump_cmd=0, valve_cmd=50.0, hold_ticks=3)
    assert gw.hold_ticks_remaining == 3

    # Tick 1
    r1 = gw.process_sense(1.0)
    assert r1["action_taken"] == "external_hold"
    assert gw.hold_ticks_remaining == 2

    # Tick 2
    r2 = gw.process_sense(1.0)
    assert r2["action_taken"] == "external_hold"
    assert gw.hold_ticks_remaining == 1

    # Tick 3: last tick of hold
    r3 = gw.process_sense(1.0)
    assert r3["action_taken"] == "external_hold"
    assert gw.hold_ticks_remaining == 0
    assert gw.external_override_active is False

    # Tick 4: autonomous controller stepped
    r4 = gw.process_sense(1.0)
    assert r4["action_taken"] != "external_hold"


def test_controller_state_sync_on_drop(cfg, test_hub):
    """On hold drop or expiry, controller._pump_command is synchronized from last telemetry packet."""
    from scada_live.common.packets import TelemetryPacket

    gw = GatewayCore(cfg, test_hub)
    gw.reset(1.0, "test_sync")

    # Set last telemetry packet with pump_on = True
    pkt = TelemetryPacket(
        seq=1, run_id="test_sync", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.005, q_out=0.002, pump_cmd=1, valve_cmd=50.0,
        pump_on=True, valve_pct=50.0
    )
    gw.process_telemetry(pkt)

    # Controller starts with pump OFF
    gw.controller._pump_command = 0
    gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=10)
    gw.drop_hold("test drop")

    assert gw.controller._pump_command == 1

    # When telemetry has pump_on = False
    pkt2 = TelemetryPacket(
        seq=2, run_id="test_sync", ts=2.0, src_t=2.0, received=True,
        level_m=1.0, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
        pump_on=False, valve_pct=50.0
    )
    gw.process_telemetry(pkt2)
    gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=10)
    gw.drop_hold("test drop 2")

    assert gw.controller._pump_command == 0


def test_monitor_prevention_event_invariance(cfg):
    """Monitor and Prevention modes dispatch would_drop / hold_dropped at the EXACT SAME simulation tick."""
    events_monitor = []
    events_prevention = []

    class MockHub:
        def __init__(self, log):
            self.log = log
        def publish(self, event):
            if isinstance(event, dict) and event.get("source") == "continuous_enforcement":
                self.log.append(event)

    # 1. Run in Monitor Mode
    hub_m = MockHub(events_monitor)
    gw_m = GatewayCore(cfg, hub_m)
    gw_m.set_mode("monitor")
    gw_m.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=500)

    # Level rises deterministically: 1.0, 1.05, 1.10, ..., 1.25, 1.30
    for i in range(10):
        level = 1.0 + i * 0.035  # i=7 -> 1.245, i=8 -> 1.28
        gw_m.process_sense(level)

    # 2. Run in Prevention Mode
    hub_p = MockHub(events_prevention)
    gw_p = GatewayCore(cfg, hub_p)
    gw_p.set_mode("prevention")
    gw_p.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=500)

    for i in range(10):
        level = 1.0 + i * 0.035
        gw_p.process_sense(level)

    # Both modes must record exactly one enforcement event at the first tick where level > 1.25
    assert len(events_monitor) >= 1
    assert len(events_prevention) >= 1

    first_m = events_monitor[0]
    first_p = events_prevention[0]

    assert first_m["action"] == "would_drop"
    assert first_p["action"] == "hold_dropped"
    assert first_m["h_est"] == first_p["h_est"]
    assert first_m["reason"] == first_p["reason"]


# ── Sub-Step 2.7: AM-5 & AM-6 Integration Scenarios (10 Seeds) ────────────────

def test_am5_filling_prevention_zero_overflows(cfg, test_hub):
    """AM-5: In prevention mode, continuous enforcement drops malicious pump ON hold at h>1.25m,
    preventing overflow across all 10 evaluation seeds (101-110).
    """
    for seed in range(101, 111):
        gw = GatewayCore(cfg, test_hub)
        gw.set_mode("prevention")
        run_id = f"am5_prev_{seed}"
        gw.reset(cfg.tank.initial_level_m, run_id)
        gw.set_mode("prevention")

        plant = LivePlant(cfg, seed=seed, standalone_mode=False)
        plant.run_id = run_id

        # Authenticated attacker injects malicious pump ON hold
        gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=1500)

        # Run 500 simulation ticks (enough to cross 1.25m at ~174s and stabilize)
        for t in range(500):
            obs_level = plant.observe()
            cmds = gw.process_sense(obs_level)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            gw.process_telemetry(pkt)

        # Must have dropped the hold
        assert gw.holds_dropped >= 1, f"Seed {seed}: hold was not dropped"
        assert gw.external_override_active is False
        # Exactly 0 overflows
        assert plant.overflow_count == 0, f"Seed {seed}: tank overflowed with count {plant.overflow_count}"
        assert plant.tank.level < cfg.tank.overflow_m


def test_am5_filling_monitor_overflows(cfg, test_hub):
    """AM-5: In monitor mode, continuous enforcement allows hold to persist,
    causing tank overflow (overflow_count > 0 in >= 9/10 seeds).
    """
    overflow_seeds = 0
    # Test 10 seeds; run 1350 ticks (analytical fill time to 2.50m crest is ~1288s)
    for seed in range(101, 111):
        gw = GatewayCore(cfg, test_hub)
        gw.set_mode("monitor")
        run_id = f"am5_mon_{seed}"
        gw.reset(cfg.tank.initial_level_m, run_id)
        gw.set_mode("monitor")

        plant = LivePlant(cfg, seed=seed, standalone_mode=False)
        plant.run_id = run_id

        # Attacker injects malicious pump ON hold
        gw.apply_override(pump_cmd=1, valve_cmd=50.0, hold_ticks=1500)

        for t in range(1350):
            obs_level = plant.observe()
            cmds = gw.process_sense(obs_level)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            gw.process_telemetry(pkt)

        if plant.overflow_count > 0 or plant.tank.level >= cfg.tank.overflow_m:
            overflow_seeds += 1

    assert overflow_seeds >= 9, f"Expected >= 9 seeds to overflow in monitor mode, got {overflow_seeds}"


def test_am6_draining_prevention_zero_dry_runs(cfg, test_hub):
    """AM-6: In prevention mode, continuous enforcement drops malicious pump OFF hold at h<0.75m,
    preventing dry-run across all 10 evaluation seeds (101-110).
    """
    for seed in range(101, 111):
        gw = GatewayCore(cfg, test_hub)
        gw.set_mode("prevention")
        run_id = f"am6_prev_{seed}"
        gw.reset(cfg.tank.initial_level_m, run_id)
        gw.set_mode("prevention")

        plant = LivePlant(cfg, seed=seed, standalone_mode=False)
        plant.run_id = run_id

        # Authenticated attacker injects malicious pump OFF hold
        gw.apply_override(pump_cmd=0, valve_cmd=50.0, hold_ticks=1800)

        # Run 600 simulation ticks (crosses 0.75m at ~268s and recovers)
        for t in range(600):
            obs_level = plant.observe()
            cmds = gw.process_sense(obs_level)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            gw.process_telemetry(pkt)

        # Hold must have been dropped
        assert gw.holds_dropped >= 1, f"Seed {seed}: hold was not dropped"
        assert gw.external_override_active is False
        # Exactly 0 dry-runs
        assert plant.dry_run_count == 0, f"Seed {seed}: tank dry-ran with count {plant.dry_run_count}"
        assert plant.tank.level > 0.05, f"Seed {seed}: tank level too low ({plant.tank.level}m)"


def test_am6_draining_monitor_dry_runs(cfg, test_hub):
    """AM-6: In monitor mode, continuous enforcement allows pump OFF hold to persist,
    causing dry-run (level <= 0.05m or dry_run_count > 0 in >= 9/10 seeds).
    """
    dry_run_seeds = 0
    # Drain time to dry-run is ~1553s; run 1650 ticks
    for seed in range(101, 111):
        gw = GatewayCore(cfg, test_hub)
        gw.set_mode("monitor")
        run_id = f"am6_mon_{seed}"
        gw.reset(cfg.tank.initial_level_m, run_id)
        gw.set_mode("monitor")

        plant = LivePlant(cfg, seed=seed, standalone_mode=False)
        plant.run_id = run_id

        # Attacker injects malicious pump OFF hold
        gw.apply_override(pump_cmd=0, valve_cmd=50.0, hold_ticks=1800)

        for t in range(1650):
            obs_level = plant.observe()
            cmds = gw.process_sense(obs_level)
            pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
            gw.process_telemetry(pkt)

        if plant.dry_run_count > 0 or plant.tank.level <= 0.05:
            dry_run_seeds += 1

    assert dry_run_seeds >= 9, f"Expected >= 9 seeds to dry-run in monitor mode, got {dry_run_seeds}"
