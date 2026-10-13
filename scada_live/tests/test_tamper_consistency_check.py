import pytest
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.common.packets import TelemetryPacket
from scada_live.plant_sim.plant import LivePlant
from scada_live.attacker_wire.injector import Injector


@pytest.fixture
def cfg():
    return load_config()

@pytest.fixture
def test_hub():
    return EventHub()


def test_legitimate_turn_off_no_false_alarm(cfg, test_hub):
    """Verify legitimate pump turn-off transitions (1 -> 0) with mechanical delay
    produce exactly 0 wire tamper alerts.
    """
    gw = GatewayCore(cfg, test_hub)
    gw.reset(1.0, "legit_test")

    # Simulate plant with Pump settling ON
    # History has [1, 1, 1]
    for _ in range(5):
        gw.gateway_pump_history.append(1)
        if len(gw.gateway_pump_history) > 10:
            gw.gateway_pump_history.pop(0)

    # Controller issues 0 at tick t
    # Tick t: gateway issued 0, plant still has pump_on=True, q_in=0.005 due to response delay D=2
    gw.gateway_pump_history.append(0)
    pkt_t = TelemetryPacket(
        seq=1, run_id="legit_test", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.005, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
        pump_on=True, valve_pct=50.0
    )
    v_t = gw.process_telemetry(pkt_t)
    assert v_t.get("wire_tamper", False) is False
    assert gw.wire_tamper_alerts == 0

    # Tick t+1: gateway issued 0, history has [..., 1, 0, 0], plant transitioning
    gw.gateway_pump_history.append(0)
    pkt_t1 = TelemetryPacket(
        seq=2, run_id="legit_test", ts=2.0, src_t=2.0, received=True,
        level_m=1.0, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
        pump_on=False, valve_pct=50.0
    )
    v_t1 = gw.process_telemetry(pkt_t1)
    assert v_t1.get("wire_tamper", False) is False
    assert gw.wire_tamper_alerts == 0

    # Tick t+2: settled OFF
    gw.gateway_pump_history.append(0)
    pkt_t2 = TelemetryPacket(
        seq=3, run_id="legit_test", ts=3.0, src_t=3.0, received=True,
        level_m=1.0, q_in=0.0, q_out=0.002, pump_cmd=0, valve_cmd=50.0,
        pump_on=False, valve_pct=50.0
    )
    v_t2 = gw.process_telemetry(pkt_t2)
    assert v_t2.get("wire_tamper", False) is False
    assert gw.wire_tamper_alerts == 0


def test_30min_soak_zero_wire_tamper_alerts(cfg, test_hub):
    """Run 1800 ticks (30 minutes simulated) of normal autonomous cycling
    and verify zero wire tamper false alarms occur across all pump transitions.
    """
    gw = GatewayCore(cfg, test_hub)
    gw.reset(cfg.tank.initial_level_m, "soak_test")
    plant = LivePlant(cfg, seed=42, standalone_mode=False)
    plant.run_id = "soak_test"

    pump_turn_offs = 0
    prev_pump_cmd = 0

    for t in range(1800):
        obs = plant.observe()
        cmds = gw.process_sense(obs)
        if prev_pump_cmd == 1 and cmds["pump_cmd"] == 0:
            pump_turn_offs += 1
        prev_pump_cmd = cmds["pump_cmd"]

        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        gw.process_telemetry(pkt)

    # In 30 minutes, there are typically 2-4 cycling transitions (tank period is ~11 mins)
    assert pump_turn_offs >= 2, f"Expected >= 2 pump turn-offs in 30 mins, got {pump_turn_offs}"
    # Exactly 0 false alarms!
    assert gw.wire_tamper_alerts == 0, f"Expected 0 wire tamper alerts, got {gw.wire_tamper_alerts}"


def test_am3_wire_tamper_detection_delay(cfg, test_hub):
    """AM-3: Downstream wire tamper forcing pump ON is detected within <= 3 ticks."""
    events = []
    class MockHub:
        def publish(self, event):
            if isinstance(event, dict) and event.get("event_type") == "Wire tamper":
                events.append(event)

    gw = GatewayCore(cfg, MockHub())
    gw.reset(1.0, "am3_test")
    plant = LivePlant(cfg, seed=101, standalone_mode=False)
    plant.run_id = "am3_test"

    # Run normal plant until pump is settled OFF for at least 5 ticks
    for _ in range(10):
        obs = plant.observe()
        cmds = gw.process_sense(obs)
        pkt = plant.advance(0, 50.0) # Keep pump OFF
        gw.process_telemetry(pkt)

    assert list(gw.gateway_pump_history[-3:]) == [0, 0, 0]
    assert plant.pump.state == 0

    # Inject wire tamper: force pump_cmd = 1 into plant
    tamper_start_tick = plant.tick_counter
    detected_tick = None

    for _ in range(10):
        obs = plant.observe()
        cmds = gw.process_sense(obs) # Gateway issues 0
        # Wire tamper downstream forces 1 into plant advance
        pkt = plant.advance(1, cmds["valve_cmd"])
        verdict = gw.process_telemetry(pkt)
        if verdict.get("wire_tamper", False):
            detected_tick = plant.tick_counter - 1
            break

    assert detected_tick is not None, "Wire tamper was not detected"
    delay = detected_tick - tamper_start_tick
    assert delay <= 3, f"Expected detection delay <= 3 ticks, got {delay}"
    assert len(events) >= 1
    assert events[0]["action"] == "wire_tamper_detected"


def test_am3_attribution_and_event(cfg, test_hub):
    """Verify verdict attribution and EventHub diagnostics for wire tamper."""
    events = []
    class MockHub:
        def publish(self, event):
            if isinstance(event, dict) and event.get("event_type") == "Wire tamper":
                events.append(event)

    gw = GatewayCore(cfg, MockHub())
    gw.reset(1.0, "am3_attr")

    # Fill gateway history with 0s
    for _ in range(5):
        gw.gateway_pump_history.append(0)

    # Telemetry echoes plant forced to pump_cmd=1
    pkt = TelemetryPacket(
        seq=1, run_id="am3_attr", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.005, q_out=0.002, pump_cmd=1, valve_cmd=50.0,
        pump_on=True, valve_pct=50.0
    )
    v = gw.process_telemetry(pkt)

    assert v["wire_tamper"] is True
    assert v["attack_type"] == "Wire tamper"
    assert gw.wire_tamper_alerts == 1
    assert len(events) == 1
    assert events[0]["echoed_pump_cmd"] == 1
    assert events[0]["echoed_pump_on"] is True


def test_am3_identical_physical_harm_monitor_vs_prevention(cfg, test_hub):
    """AM-3 Detect-Only Invariance:
    Because downstream wire overrides bypass gateway command routing,
    Monitor and Prevention modes suffer identical overflow harm under wire tamper.
    """
    def run_tamper_sim(mode: str):
        gw = GatewayCore(cfg, test_hub)
        gw.set_mode(mode)
        gw.reset(1.0, f"am3_harm_{mode}")
        gw.set_mode(mode)

        plant = LivePlant(cfg, seed=105, standalone_mode=False)
        plant.run_id = f"am3_harm_{mode}"

        # Settle OFF for 5 ticks
        for _ in range(5):
            obs = plant.observe()
            cmds = gw.process_sense(obs)
            pkt = plant.advance(0, 50.0)
            gw.process_telemetry(pkt)

        # Wire tamper forces pump ON for 1350 ticks
        for _ in range(1350):
            obs = plant.observe()
            cmds = gw.process_sense(obs) # Gateway commands pump OFF
            # Downstream wire forces pump ON
            pkt = plant.advance(1, 50.0)
            gw.process_telemetry(pkt)

        return plant.overflow_count, plant.tank.level

    ov_mon, final_h_mon = run_tamper_sim("monitor")
    ov_prev, final_h_prev = run_tamper_sim("prevention")

    # Overflow events and final levels must be identical
    assert ov_mon > 0, "Expected overflow in monitor mode"
    assert ov_prev > 0, "Expected overflow in prevention mode"
    assert ov_mon == ov_prev, f"Expected identical overflow counts, got mon={ov_mon}, prev={ov_prev}"
    assert abs(final_h_mon - final_h_prev) < 1e-5


def test_am4_in_deadband_toggle_empirical(cfg, test_hub):
    """AM-4: In-deadband toggles at nominal level (1.0m) represent a documented blind spot.
    Verify Policy and Physics engines do NOT trigger false critical alerts.
    """
    gw = GatewayCore(cfg, test_hub)
    gw.reset(1.0, "am4_test")
    plant = LivePlant(cfg, seed=200, standalone_mode=False)
    plant.run_id = "am4_test"

    critical_alerts = 0
    pump_toggle_state = 0

    for t in range(60):
        # Toggle pump every 5 ticks via gateway command override (AM-4 threat model)
        if t % 5 == 0:
            pump_toggle_state = 1 - pump_toggle_state
            gw.apply_override(pump_toggle_state, 50.0, hold_ticks=5)

        obs = plant.observe()
        cmds = gw.process_sense(obs)
        pkt = plant.advance(cmds["pump_cmd"], cmds["valve_cmd"])
        v = gw.process_telemetry(pkt)

        # Policy and Physics engines must NOT declare anomaly inside deadband
        firing = v.get("engines_firing", [])
        if "policy" in firing or "physics" in firing:
            critical_alerts += 1

    # Policy and Physics engines must NOT trigger inside deadband
    assert critical_alerts == 0, f"Policy/Physics triggered {critical_alerts} alerts inside deadband"
