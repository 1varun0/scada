import pytest
from scada_live.attacker_wire.injector import Injector

class FakeGatewayClient:
    def __init__(self):
        self.sense_calls = []
        self.telemetry_calls = []
        self.truth_calls = []

    def sense(self, seq, ts, level_m):
        self.sense_calls.append((seq, ts, level_m))
        return 0, 50.0

    def send_telemetry(self, pkt):
        self.telemetry_calls.append(pkt)

    def send_truth(self, truth):
        self.truth_calls.append(truth)

def test_injector_fdi():
    fake = FakeGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake)
    inj.start_attack("FDI", 10.0, 5.0, magnitude=0.2)
    
    # Pre-attack
    cmd = inj.sense(1, 5.0, 1.0)
    inj.send_telemetry({"seq": 1, "ts": 5.0, "level_m": 1.0})
    assert fake.sense_calls[-1][2] == 1.0
    assert fake.telemetry_calls[-1]["level_m"] == 1.0
    assert fake.truth_calls[-1]["ground_truth"] == 0
    
    # During attack
    cmd = inj.sense(2, 11.0, 1.0)
    inj.send_telemetry({"seq": 2, "ts": 11.0, "level_m": 1.0})
    assert fake.sense_calls[-1][2] == 1.2
    assert fake.telemetry_calls[-1]["level_m"] == 1.2
    assert fake.truth_calls[-1]["ground_truth"] == 1
    assert fake.truth_calls[-1]["true_level"] == 1.0

def test_injector_replay():
    fake = FakeGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake)
    inj.start_attack("Replay", 10.0, 5.0)
    
    # Pre-attack: record
    inj.sense(1, 8.0, 1.0)
    inj.sense(2, 9.0, 1.1)
    
    # During attack: replay
    inj.sense(3, 11.0, 1.5)
    inj.send_telemetry({"seq": 3, "ts": 11.0, "level_m": 1.5})
    assert fake.sense_calls[-1][2] == 1.0 # Replayed from ts=8.0
    assert fake.telemetry_calls[-1]["level_m"] == 1.0
    assert fake.telemetry_calls[-1]["src_t"] == 8.0

def test_injector_dos():
    fake = FakeGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake)
    inj.start_attack("DoS", 10.0, 5.0, drop_prob=1.0)
    
    cmd = inj.sense(1, 11.0, 1.0)
    inj.send_telemetry({"seq": 1, "ts": 11.0, "level_m": 1.0})
    assert cmd == (None, None)
    assert len(fake.sense_calls) == 0
    assert len(fake.telemetry_calls) == 0
    assert len(fake.truth_calls) == 1 # Truth is still sent

def test_injector_auth_misuse():
    fake = FakeGatewayClient()
    inj = Injector("http://fake", "run1", real_client=fake)
    inj.start_attack("Auth misuse", 10.0, 5.0, target_command=1, target_valve=80.0)
    
    cmd = inj.sense(1, 11.0, 1.0)
    # fake client returned (0, 50.0), injector overrides
    assert cmd == (1, 80.0)
    assert fake.sense_calls[-1][2] == 1.0 # True level is sent
