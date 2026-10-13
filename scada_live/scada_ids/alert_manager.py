class AlertManager:
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    CRITICAL = "CRITICAL"
    
    def __init__(self, cfg):
        self.n_flags = cfg.alert.n_flags
        self.window_w = cfg.alert.window_w
        self.m_clear = cfg.alert.m_clear
        
        self.reset()
        
    def reset(self):
        self.state = self.SAFE
        self.window = []
        self.clean_ticks = 0
        self.latched = False
        self.event_id = None
        self.first_flag_seq = None
        self.detected_seq = None
        self.peak_hybrid = 0.0
        if not hasattr(self, 'history'):
            import collections
            self.history = collections.deque(maxlen=1000)
        else:
            self.history.clear()
        
    def _attribute_type(self, engines_firing: list[str], received: bool, stale: bool) -> str:
        if "actuator_consistency" in engines_firing:
            return "Wire tamper"
        if "availability" in engines_firing:
            if not received:
                return "DoS"
            elif stale:
                return "Replay"
        if "policy" in engines_firing:
            return "Auth misuse"
        if "physics" in engines_firing and len(engines_firing) == 1:
            return "Sensor/process inconsistency"
        if "lstm" in engines_firing and len(engines_firing) == 1:
            return "Unclassified anomaly"
            
        # Several engines
        if "availability" in engines_firing and not received:
            return "DoS"
        elif "availability" in engines_firing and stale:
            return "Replay"
        elif "policy" in engines_firing:
            return "Auth misuse"
        elif "physics" in engines_firing:
            return "Sensor/process inconsistency"
        return "Unclassified anomaly"

    def update(self, seq: int, ts: float, is_anomaly: bool, engines_firing: list[str], received: bool, stale: bool, hybrid_score: float):
        self.window.append(is_anomaly)
        if len(self.window) > self.window_w:
            self.window.pop(0)
            
        if is_anomaly:
            self.clean_ticks = 0
            if self.first_flag_seq is None:
                self.first_flag_seq = seq
        else:
            self.clean_ticks += 1
            
        flags_in_window = sum(self.window)
        
        if hybrid_score > self.peak_hybrid:
            self.peak_hybrid = hybrid_score
        
        # State machine
        if self.state == self.SAFE:
            if flags_in_window > 0:
                self.state = self.SUSPICIOUS
            if flags_in_window >= self.n_flags:
                self.state = self.CRITICAL
                self.latched = True
                if self.detected_seq is None:
                    self.detected_seq = seq
        elif self.state == self.SUSPICIOUS:
            if flags_in_window >= self.n_flags:
                self.state = self.CRITICAL
                self.latched = True
                if self.detected_seq is None:
                    self.detected_seq = seq
            elif self.clean_ticks >= self.m_clear:
                self.state = self.SAFE
        elif self.state == self.CRITICAL:
            # Remains CRITICAL until ack, even if clean ticks are met
            # The plan says "latch: cleared only by ack".
            pass
            
        primary_type = "None"
        if self.state != self.SAFE:
            primary_type = self._attribute_type(engines_firing, received, stale)
            
        return {
            "alert_state": self.state,
            "attack_type": primary_type,
            "latched": self.latched,
            "first_flag_seq": self.first_flag_seq,
            "detected_seq": self.detected_seq,
            "peak_hybrid": self.peak_hybrid
        }
        
    def acknowledge(self):
        self.latched = False
        self.state = self.SAFE
        self.clean_ticks = self.m_clear
        self.window = [False] * self.window_w
        self.first_flag_seq = None
        self.detected_seq = None
        self.peak_hybrid = 0.0
