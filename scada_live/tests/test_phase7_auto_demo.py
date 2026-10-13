import pytest
import threading
import time
from unittest.mock import MagicMock
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub
from scada_live.plant_sim.plant import LivePlant
from scada_live.attacker_wire.injector import Injector
from run_demo import PlantControl, AutoDemoCoordinator


@pytest.fixture
def test_setup():
    cfg = load_config()
    hub = EventHub()
    gateway = GatewayCore(cfg, hub)
    plant = LivePlant(cfg, standalone_mode=False)
    client_mock = MagicMock()
    client_mock.sense.return_value = (0, 50.0)
    injector = Injector("http://127.0.0.1:5000", "test_auto", real_client=client_mock)
    control = PlantControl(plant, injector)
    return cfg, hub, gateway, plant, injector, control


def test_coordinator_init(test_setup):
    cfg, hub, gateway, plant, injector, control = test_setup
    stop_event = threading.Event()
    coord = AutoDemoCoordinator(
        plant=plant,
        injector=injector,
        gateway=gateway,
        control=control,
        hub=hub,
        speed=10.0,
        stop_event=stop_event,
        exit_on_finish=True
    )
    assert coord.speed == 10.0
    assert coord.exit_on_finish is True
    assert coord.finished is False


def test_coordinator_sleep_sim_interrupt(test_setup):
    cfg, hub, gateway, plant, injector, control = test_setup
    stop_event = threading.Event()
    coord = AutoDemoCoordinator(
        plant=plant,
        injector=injector,
        gateway=gateway,
        control=control,
        hub=hub,
        speed=1.0,
        stop_event=stop_event
    )
    t0 = time.monotonic()
    # Trigger stop after 0.1s
    timer = threading.Timer(0.1, stop_event.set)
    timer.start()
    coord.sleep_sim(10.0) # Requested 10s sleep should break early
    t1 = time.monotonic()
    assert (t1 - t0) < 1.0


def test_coordinator_print_summary(test_setup, capsys):
    cfg, hub, gateway, plant, injector, control = test_setup
    coord = AutoDemoCoordinator(
        plant=plant,
        injector=injector,
        gateway=gateway,
        control=control,
        hub=hub,
        speed=5.0
    )
    coord.print_final_summary()
    captured = capsys.readouterr()
    assert "SCADA HYBRID IDS — AUTOMATED DEMO EXECUTION SUMMARY" in captured.out
    assert "ATTACK DETECTION PERFORMANCE" in captured.out
    assert "PREVENTION & SAFETY METRICS" in captured.out


def test_coordinator_fast_execution(test_setup):
    """Execute coordinator at ultra-high speed (500x) to verify state machine transitions."""
    cfg, hub, gateway, plant, injector, control = test_setup
    stop_event = threading.Event()
    coord = AutoDemoCoordinator(
        plant=plant,
        injector=injector,
        gateway=gateway,
        control=control,
        hub=hub,
        speed=500.0,
        stop_event=stop_event,
        exit_on_finish=True
    )
    coord.start()
    coord.join(timeout=15.0)

    assert coord.finished is True
    assert stop_event.is_set()
    assert gateway.mode == "prevention"
