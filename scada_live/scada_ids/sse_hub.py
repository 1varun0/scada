import json
import threading
from queue import Queue, Full

class EventHub:
    def __init__(self, queue_size=200):
        self.queue_size = queue_size
        self.clients = []
        self.lock = threading.Lock()
        
    def subscribe(self) -> Queue:
        q = Queue(maxsize=self.queue_size)
        with self.lock:
            self.clients.append(q)
        return q
        
    def unsubscribe(self, q: Queue):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)
                
    def publish(self, event: dict):
        with self.lock:
            for q in self.clients:
                try:
                    q.put_nowait(event)
                except Full:
                    # Drop oldest and put new
                    try:
                        q.get_nowait()
                        q.put_nowait(event)
                    except Exception:
                        pass
