class MetricsCollector:
    def __init__(self, grace_period_s=10.0):
        self.grace_period_s = grace_period_s
        self.reset()
        
    def reset(self):
        # Buffer for joins
        self.truth_buffer = {}
        self.verdict_buffer = {}
        
        # True state tracking
        self.attack_active_true = False
        self.attack_type_true = "None"
        self.last_attack_end_ts = -999.0
        
        # Episode metrics
        self.episodes = [] # list of dicts for each true attack episode
        self.current_episode = None
        
        self.missed_attacks = 0
        self.spurious_alerts = 0
        self.lingering_alerts = 0
        
        # Tick metrics
        self.ticks_true_positive = 0
        self.ticks_false_positive = 0
        self.ticks_true_negative = 0
        self.ticks_false_negative = 0
        
        # Safety
        self.overflow_events = 0
        self.dry_run_events = 0
        self.ticks_critical_high = 0
        self.ticks_critical_low = 0
        self.max_true_level = -999.0
        self.min_true_level = 999.0
        self.ticks_outside_safe_band = 0
        self.operator_errors = 0
        
        # Last known true level for bounding
        self.last_true_level = None
        self.last_ts = 0.0
        
    def update_truth(self, run_id: str, seq: int, ts: float, true_level: float, attack_active: bool, attack_type: str, overflow: bool, dry_run: bool):
        self.truth_buffer[seq] = {
            "ts": ts,
            "true_level": true_level,
            "attack_active": attack_active,
            "attack_type": attack_type,
            "overflow": overflow,
            "dry_run": dry_run
        }
        self._join(seq)
        
    def update_verdict(self, run_id: str, seq: int, ts: float, is_anomaly: bool, alert_state: str, recalibrating: bool):
        self.verdict_buffer[seq] = {
            "ts": ts,
            "is_anomaly": is_anomaly,
            "alert_state": alert_state,
            "recalibrating": recalibrating
        }
        self._join(seq)
        
    def record_ack(self, recalibrate: bool, ts: float):
        if self.attack_active_true and recalibrate:
            self.operator_errors += 1
            
    def _join(self, seq: int):
        if seq in self.truth_buffer and seq in self.verdict_buffer:
            truth = self.truth_buffer.pop(seq)
            verdict = self.verdict_buffer.pop(seq)
            self._process_joined(seq, truth, verdict)
            
        # Clean up old sequences
        old_seqs = [s for s in self.truth_buffer if s < seq - 100]
        for s in old_seqs: del self.truth_buffer[s]
        old_seqs = [s for s in self.verdict_buffer if s < seq - 100]
        for s in old_seqs: del self.verdict_buffer[s]
            
    def _process_joined(self, seq: int, truth: dict, verdict: dict):
        ts = truth["ts"]
        self.last_ts = ts
        
        # Episode tracking
        if truth["attack_active"] and not self.attack_active_true:
            # Attack started
            if self.current_episode:
                # Missed previous episode?
                if not self.current_episode["detected"]:
                    self.missed_attacks += 1
                self.episodes.append(self.current_episode)
                
            self.current_episode = {
                "start_ts": ts,
                "end_ts": None,
                "type": truth["attack_type"],
                "first_flag_ts": None,
                "detected_ts": None,
                "detected": False
            }
        elif not truth["attack_active"] and self.attack_active_true:
            # Attack ended
            if self.current_episode:
                self.current_episode["end_ts"] = ts
                self.last_attack_end_ts = ts
                
                if not self.current_episode["detected"]:
                    self.missed_attacks += 1
                self.episodes.append(self.current_episode)
                self.current_episode = None
                
        self.attack_active_true = truth["attack_active"]
        self.attack_type_true = truth["attack_type"]
        
        # Episode metrics update
        if self.current_episode:
            if verdict["is_anomaly"] and self.current_episode["first_flag_ts"] is None:
                self.current_episode["first_flag_ts"] = ts
            if verdict["alert_state"] == "CRITICAL" and self.current_episode["detected_ts"] is None:
                self.current_episode["detected_ts"] = ts
                self.current_episode["detected"] = True
                
        grace_active = (ts - self.last_attack_end_ts) <= self.grace_period_s
        
        # Lingering / Spurious alerts
        if verdict["alert_state"] == "CRITICAL":
            if not self.attack_active_true:
                if grace_active:
                    pass # Post-attack grace period
                elif (ts - self.last_attack_end_ts) > self.grace_period_s and self.last_attack_end_ts > 0:
                    if not getattr(self, "_in_lingering", False):
                        self.lingering_alerts += 1
                        self._in_lingering = True
                else:
                    if not getattr(self, "_in_spurious", False):
                        self.spurious_alerts += 1
                        self._in_spurious = True
        else:
            self._in_lingering = False
            self._in_spurious = False
                    
        # Tick metrics
        if self.attack_active_true:
            if verdict["is_anomaly"]:
                self.ticks_true_positive += 1
            else:
                self.ticks_false_negative += 1
        else:
            if verdict["is_anomaly"]:
                self.ticks_false_positive += 1
            else:
                self.ticks_true_negative += 1
                
        # Safety metrics
        if truth["overflow"]:
            self.overflow_events += 1
        if truth["dry_run"]:
            self.dry_run_events += 1
            
        true_level = truth["true_level"]
        self.last_true_level = true_level
        self.max_true_level = max(self.max_true_level, true_level)
        self.min_true_level = min(self.min_true_level, true_level)
        
    def get_metrics(self):
        return {
            "episodes": self.episodes,
            "missed_attacks": self.missed_attacks,
            "spurious_alerts": self.spurious_alerts,
            "lingering_alerts": self.lingering_alerts,
            "ticks_tp": self.ticks_true_positive,
            "ticks_fp": self.ticks_false_positive,
            "ticks_tn": self.ticks_true_negative,
            "ticks_fn": self.ticks_false_negative,
            "safety": {
                "overflow_events": self.overflow_events,
                "dry_run_events": self.dry_run_events,
                "max_true_level": self.max_true_level,
                "min_true_level": self.min_true_level,
                "operator_errors": self.operator_errors
            }
        }
