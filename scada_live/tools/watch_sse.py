import sseclient
import requests
import json
import argparse
from scada_live.common.config_loader import load_config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=None)
    args = parser.parse_args()
    
    cfg = load_config()
    url = args.url or f"http://127.0.0.1:{cfg.network.scada_port}/stream"
    
    print(f"Connecting to {url}...")
    response = requests.get(url, stream=True)
    client = sseclient.SSEClient(response)
    
    for event in client.events():
        if event.data == ": keepalive":
            continue
        try:
            data = json.loads(event.data)
            print(f"Seq: {data.get('seq')}, Anomaly: {data.get('is_anomaly')}, Hybrid: {data.get('hybrid', 0):.4f}")
        except Exception as e:
            print(f"Error parsing event: {e}")

if __name__ == "__main__":
    main()
