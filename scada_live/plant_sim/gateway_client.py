import threading
import time
import requests
import queue
from typing import Dict, Any, Tuple

class GatewayClient:
    """
    Client for LivePlant to talk to the Gateway Server.
    Uses two-call protocol:
      1. sense() -> pump_cmd, valve_cmd (synchronous, 0.5s timeout)
      2. telemetry() (asynchronous via queue)
    """
    def __init__(self, target_url: str, run_id: str):
        self.target_url = target_url.rstrip('/')
        self.run_id = run_id
        self.session = requests.Session()
        self.q = queue.Queue(maxsize=100)
        self.worker = threading.Thread(target=self._sender_loop, daemon=True)
        self.worker.start()
        
    def sense(self, seq: int, ts: float, level_m: float) -> Tuple[int, float]:
        """
        Sends the observed level and expects commands back.
        If it fails, returns (None, None) so plant can use fail-safe.
        """
        try:
            resp = self.session.post(
                f"{self.target_url}/api/sense",
                json={"seq": seq, "run_id": self.run_id, "ts": ts, "level_m": level_m},
                timeout=0.5
            )
            if resp.status_code == 200:
                data = resp.json()
                return int(data['pump_cmd']), float(data['valve_cmd'])
        except Exception:
            pass
        return None, None
        
    def send_telemetry(self, pkt_dict: Dict[str, Any]):
        """Queues the full telemetry packet for async sending."""
        pkt_dict['run_id'] = self.run_id
        try:
            self.q.put_nowait(pkt_dict)
        except queue.Full:
            pass # Drop if gateway is totally unresponsive
            
    def send_truth(self, truth_dict: Dict[str, Any]):
        """Send ground truth for metrics."""
        truth_dict['run_id'] = self.run_id
        # We can send this synchronously on a short timeout, or in a fire-and-forget thread
        def _post_truth():
            try:
                self.session.post(f"{self.target_url}/api/truth", json=truth_dict, timeout=1.0)
            except Exception:
                pass
        threading.Thread(target=_post_truth, daemon=True).start()
            
    def _sender_loop(self):
        while True:
            pkt = self.q.get()
            try:
                self.session.post(
                    f"{self.target_url}/api/telemetry",
                    json=pkt,
                    timeout=1.0
                )
            except Exception:
                pass
            finally:
                self.q.task_done()
