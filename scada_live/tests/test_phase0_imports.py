"""Phase 0 acceptance test: all modules import and config loads."""

def test_import_packets():
    from scada_live.common.packets import TelemetryPacket, CommandPacket

def test_import_config_loader():
    from scada_live.common.config_loader import load_config

def test_import_transport():
    from scada_live.common.transport import TransportClient, TransportServer

def test_import_stubs():
    from scada_live.plant_sim.plant import LivePlant
    from scada_live.attacker_wire.injector import Injector
    from scada_live.scada_ids.streaming_ids import StreamingIDS
    from scada_live.scada_ids.alert_manager import AlertManager
    from scada_live.scada_ids.prevention import PreventionController
    from scada_live.scada_ids.control_server import ControlServer
    from scada_live.scada_ids.metrics import MetricsCollector

def test_config_loads():
    from scada_live.common.config_loader import load_config
    cfg = load_config()
    assert cfg.tank.initial_level_m == 1.0
    assert cfg.ids.tau_fusion == 0.95
    assert cfg.network.plant_port == 5100
    assert cfg.lstm.input_dim == 5
    assert cfg.simulation.dt_s == 1.0

def test_telemetry_packet_roundtrip():
    from scada_live.common.packets import TelemetryPacket
    pkt = TelemetryPacket(
        seq=1, run_id="test_run", ts=1.0, src_t=1.0, received=True, level_m=1.18,
        q_in=0.005, q_out=0.002, pump_on=True, pump_cmd=1, valve_pct=50.0, valve_cmd=50.0
    )
    d = pkt.to_dict()
    pkt2 = TelemetryPacket.from_dict(d)
    assert pkt2.seq == pkt.seq
    assert pkt2.level_m == pkt.level_m

def test_telemetry_strip_truth():
    from scada_live.common.packets import TelemetryPacket
    pkt = TelemetryPacket(
        seq=1, run_id="test_run", ts=1.0, src_t=1.0, received=True, level_m=1.18,
        q_in=0.005, q_out=0.002, pump_on=True, pump_cmd=1, valve_pct=50.0, valve_cmd=50.0,
        _true_level=1.19, _attack_active=True, _attack_type="FDI"
    )
    clean = pkt.strip_truth()
    assert "_true_level" not in clean
    assert "_attack_active" not in clean
    assert "level_m" in clean

def test_command_packet_roundtrip():
    from scada_live.common.packets import CommandPacket
    cmd = CommandPacket(seq=1, ts=1.0, src="scada_master", cmd="PUMP", value="ON")
    d = cmd.to_dict()
    cmd2 = CommandPacket.from_dict(d)
    assert cmd2.src == "scada_master"
    assert cmd2.value == "ON"

def test_config_prevention_block():
    from scada_live.common.config_loader import load_config
    cfg = load_config()
    assert hasattr(cfg, "prevention")
    assert cfg.prevention.default_mode == "monitor"
    assert cfg.prevention.act_on == ["physics"]
    assert cfg.prevention.fdi_takeover is True
    assert cfg.prevention.handback_tolerance_m == 0.05
    assert cfg.prevention.auto_handback is False
    assert cfg.ids.policy_version == "v1"

def test_streaming_ids_twin_estimate_and_policy_flag():
    from scada_live.common.config_loader import load_config
    from scada_live.scada_ids.streaming_ids import StreamingIDS
    from scada_live.common.packets import TelemetryPacket
    cfg = load_config()
    
    # Default policy version from config
    ids_v1 = StreamingIDS(cfg)
    assert ids_v1.policy_version == "v1"
    assert ids_v1.get_twin_estimate() == cfg.tank.initial_level_m

    # Explicit override to v2
    ids_v2 = StreamingIDS(cfg, policy_version="v2")
    assert ids_v2.policy_version == "v2"

    # Advance twin and check accessor
    pkt = TelemetryPacket(
        seq=1, run_id="test_run", ts=1.0, src_t=1.0, received=True,
        level_m=1.0, q_in=0.005, q_out=0.002, pump_on=True, pump_cmd=1,
        valve_pct=50.0, valve_cmd=50.0
    )
    ids_v1.update(pkt)
    # Area = 2.0 m^2, dH = (0.005 - 0.002)/2.0 * 1.0 = 0.0015 m -> level = 1.0015 m
    assert abs(ids_v1.get_twin_estimate() - 1.0015) < 1e-6

