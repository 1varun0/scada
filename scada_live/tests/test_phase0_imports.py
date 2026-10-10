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
