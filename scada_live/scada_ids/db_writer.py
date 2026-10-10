import sqlite3
import threading
import queue
import time
from typing import Dict, Any

class DBWriter:
    def __init__(self, db_path="data/live_run.db"):
        self.db_path = db_path
        self.q = queue.Queue()
        self.thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.thread.start()
        
    def write_tick(self, tick_data: Dict[str, Any]):
        self.q.put(("tick", tick_data))
        
    def write_event(self, event_data: Dict[str, Any]):
        self.q.put(("event", event_data))
        
    def _writer_loop(self):
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS live_ticks (
                run_id TEXT,
                seq INTEGER,
                ts REAL,
                level_obs REAL,
                level_twin REAL,
                is_anomaly INTEGER,
                alert_state TEXT,
                PRIMARY KEY(run_id, seq)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS live_events (
                event_id INTEGER,
                run_id TEXT,
                seq INTEGER,
                ts REAL,
                attack_type TEXT,
                PRIMARY KEY(event_id)
            )
        ''')
        conn.commit()
        
        batch = []
        while True:
            try:
                item = self.q.get(timeout=1.0)
                batch.append(item)
            except queue.Empty:
                if batch:
                    self._flush(conn, c, batch)
                    batch = []
                continue
                
            if len(batch) >= 100:
                self._flush(conn, c, batch)
                batch = []
                
    def _flush(self, conn, c, batch):
        ticks = [item[1] for item in batch if item[0] == "tick"]
        events = [item[1] for item in batch if item[0] == "event"]
        
        if ticks:
            c.executemany('''
                INSERT OR IGNORE INTO live_ticks 
                (run_id, seq, ts, level_obs, level_twin, is_anomaly, alert_state)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [(t['run_id'], t['seq'], t['ts'], t['level_obs'], t['level_twin'], t['is_anomaly'], t['alert_state']) for t in ticks])
            
        if events:
            c.executemany('''
                INSERT OR IGNORE INTO live_events
                (event_id, run_id, seq, ts, attack_type)
                VALUES (?, ?, ?, ?, ?)
            ''', [(e['event_id'], e['run_id'], e['seq'], e['ts'], e['attack_type']) for e in events])
            
        conn.commit()
