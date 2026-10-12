"""
Unit tests for Gateway Safety Rule (evaluate_command_with_live_setpoint)
and Phase 6b synthetic scenario specifications (AM-1 through AM-6).
"""
import pytest
from simulator.controller import Controller
from scada_live.common.config_loader import load_config
from scada_live.scada_ids.gateway_core import GatewayCore
from scada_live.scada_ids.sse_hub import EventHub

def evaluate_command_with_live_setpoint(
    h_est: float,
    pump_cmd: int,
    valve_cmd: float,
    controller: Controller,
    epsilon: float = 0.05,
    safe_valve: float = 0.0
) -> tuple[bool, str]:
    """
    Gateway-side command validation against live controller setpoint and deadband.
    Asserts exact Controller attributes exist; no silent fallback defaults.
    """
    assert hasattr(controller, "setpoint"), "Controller missing 'setpoint' attribute"
    setpoint = float(controller.setpoint)
    assert hasattr(controller, "_deadband"), "Controller missing '_deadband' attribute"
    deadband = float(controller._deadband)
    assert hasattr(controller, "_default_valve_pct"), "Controller missing '_default_valve_pct' attribute"
    default_valve = float(controller._default_valve_pct)

    if valve_cmd != default_valve:
        if valve_cmd != safe_valve or pump_cmd != 0:
            return False, f"Invalid valve position {valve_cmd}%"

    if pump_cmd == 1 and h_est > (setpoint + deadband + epsilon):
        return False, f"Pump ON forbidden at h_est={h_est:.3f}m > limit={setpoint + deadband + epsilon:.3f}m"

    if pump_cmd == 0 and h_est < (setpoint - deadband - epsilon):
        return False, f"Pump OFF forbidden at h_est={h_est:.3f}m < limit={setpoint - deadband - epsilon:.3f}m"

    return True, "Valid"


def test_controller_attributes_exist():
    """Verify Controller has required attributes without silent defaults."""
    ctrl = Controller()
    assert hasattr(ctrl, "setpoint")
    assert hasattr(ctrl, "_deadband")
    assert hasattr(ctrl, "_default_valve_pct")
    assert ctrl.setpoint == 1.0
    assert ctrl._deadband == 0.2
    assert ctrl._default_valve_pct == 50.0


def test_normal_operating_envelope():
    """Commands inside nominal envelope are allowed."""
    ctrl = Controller()
    # At level 1.0m, both pump ON and pump OFF are allowed (within deadband)
    valid, msg = evaluate_command_with_live_setpoint(1.0, 1, 50.0, ctrl)
    assert valid, msg
    valid, msg = evaluate_command_with_live_setpoint(1.0, 0, 50.0, ctrl)
    assert valid, msg

    # Failsafe valve position allowed only with pump OFF
    valid, msg = evaluate_command_with_live_setpoint(1.0, 0, 0.0, ctrl)
    assert valid, msg

    # Failsafe valve position with pump ON is forbidden
    valid, msg = evaluate_command_with_live_setpoint(1.0, 1, 0.0, ctrl)
    assert not valid
    assert "Invalid valve position" in msg


def test_am1_high_level_pump_on_blocked():
    """AM-1: Ingress check blocks pump ON when level is above setpoint + deadband + epsilon."""
    ctrl = Controller()
    # Upper threshold = 1.0 + 0.20 + 0.05 = 1.25m
    valid, msg = evaluate_command_with_live_setpoint(1.30, 1, 50.0, ctrl)
    assert not valid
    assert "Pump ON forbidden" in msg


def test_am2_valve_tampering_blocked():
    """AM-2: Ingress check blocks unauthorized valve positions."""
    ctrl = Controller()
    valid, msg = evaluate_command_with_live_setpoint(0.90, 0, 90.0, ctrl)
    assert not valid
    assert "Invalid valve position 90.0%" in msg


def test_am3_legitimate_gateway_command_allowed():
    """AM-3: Gateway-side command evaluation passes legitimate pump=0, valve=50%."""
    ctrl = Controller()
    valid, msg = evaluate_command_with_live_setpoint(1.00, 0, 50.0, ctrl)
    assert valid, msg


def test_am4_in_deadband_toggle_allowed_blindspot():
    """AM-4: In-deadband toggles within [0.75, 1.25m] pass gateway validation (documented blind spot)."""
    ctrl = Controller()
    valid_off, _ = evaluate_command_with_live_setpoint(1.00, 0, 50.0, ctrl)
    valid_on, _ = evaluate_command_with_live_setpoint(1.00, 1, 50.0, ctrl)
    assert valid_off and valid_on


def test_am5_in_band_hold_dropped_on_envelope_crossing():
    """AM-5: Ingress allowed at 1.0m, but continuous enforcement flags at 1.26m."""
    ctrl = Controller()
    # Ingress at 1.0m
    valid_ing, msg_ing = evaluate_command_with_live_setpoint(1.00, 1, 50.0, ctrl)
    assert valid_ing, msg_ing

    # Continuous enforcement when level crosses 1.25m
    valid_cont, msg_cont = evaluate_command_with_live_setpoint(1.26, 1, 50.0, ctrl)
    assert not valid_cont
    assert "Pump ON forbidden" in msg_cont


def test_am6_pump_off_dropped_on_lower_envelope_crossing():
    """AM-6: Pump OFF held at 1.0m passes ingress, but continuous enforcement flags at 0.74m."""
    ctrl = Controller()
    # Ingress at 1.0m
    valid_ing, msg_ing = evaluate_command_with_live_setpoint(1.00, 0, 50.0, ctrl)
    assert valid_ing, msg_ing

    # Continuous enforcement when level falls below 1.0 - 0.20 - 0.05 = 0.75m
    valid_cont, msg_cont = evaluate_command_with_live_setpoint(0.74, 0, 50.0, ctrl)
    assert not valid_cont
    assert "Pump OFF forbidden" in msg_cont
