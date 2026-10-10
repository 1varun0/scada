import requests
import json
from typing import Generator

class TransportClient:
    """Sends packets to a remote process over HTTP."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def send_telemetry(self, packet_dict: dict) -> bool:
        """POST a telemetry packet. Returns True on success."""
        try:
            response = self.session.post(f"{self.base_url}/telemetry", json=packet_dict)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def send_command(self, command_dict: dict) -> dict:
        """POST a command packet. Returns the response dict."""
        try:
            response = self.session.post(f"{self.base_url}/command", json=command_dict)
            if response.status_code == 200:
                return response.json()
            return {}
        except requests.RequestException:
            return {}
    
    def stream_sse(self, endpoint: str) -> Generator[dict, None, None]:
        """Connect to an SSE endpoint and yield parsed JSON events."""
        try:
            with self.session.get(f"{self.base_url}/{endpoint.lstrip('/')}", stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data:'):
                            data_str = decoded_line[5:].strip()
                            if data_str:
                                yield json.loads(data_str)
        except requests.RequestException:
            pass

class TransportServer:
    """Mixin/helper for Flask apps to emit SSE streams."""
    
    @staticmethod
    def sse_response(generator_func):
        """Wraps a generator into a Flask SSE Response."""
        from flask import Response
        return Response(generator_func(), mimetype='text/event-stream')
