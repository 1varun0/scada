class FusionEngine:
    """
    Engine 5: Hybrid Fusion
    Combines the scores from the 4 evidence engines into a final anomaly decision.
    
    Supports two fusion strategies:
      - 'weighted_sum': Traditional weighted sum (default for ablation)
      - 'max_vote': Anomaly if ANY engine exceeds its individual threshold
    """
    def __init__(self, w_p: float, w_l: float, w_c: float, w_a: float, 
                 tau_fusion: float, strategy: str = "weighted_sum"):
        """
        Args:
            w_p: Weight for Physics Engine score.
            w_l: Weight for Temporal (LSTM) Engine score.
            w_c: Weight for Policy Engine score.
            w_a: Weight for Availability Engine score.
            tau_fusion: Threshold for final anomaly decision.
            strategy: 'weighted_sum' or 'max_vote'
        """
        # Ensure weights sum to ~1.0
        total = w_p + w_l + w_c + w_a
        if total > 0 and abs(total - 1.0) > 1e-5:
            w_p /= total
            w_l /= total
            w_c /= total
            w_a /= total
            
        self.w_p = w_p
        self.w_l = w_l
        self.w_c = w_c
        self.w_a = w_a
        self.tau_fusion = tau_fusion
        self.strategy = strategy
        
    def evaluate(self, s_p: float, s_l: float, s_c: float, s_a: float) -> tuple[float, int]:
        """
        Fuse the scores and return the final decision.
        
        Args:
            s_p: Normalized physics score [0,1]
            s_l: Normalized temporal score [0,1]
            s_c: Normalized policy score [0,1]
            s_a: Normalized availability score [0,1]
            
        Returns:
            Tuple of (s_hybrid, predicted_anomaly)
            s_hybrid is the combined score in [0, 1].
            predicted_anomaly is 1 if anomalous, else 0.
        """
        if self.strategy == "max_vote":
            return self._evaluate_max_vote(s_p, s_l, s_c, s_a)
        else:
            return self._evaluate_weighted_sum(s_p, s_l, s_c, s_a)
    
    def _evaluate_weighted_sum(self, s_p, s_l, s_c, s_a):
        """Traditional weighted sum fusion."""
        s_hybrid = (self.w_p * s_p) + (self.w_l * s_l) + (self.w_c * s_c) + (self.w_a * s_a)
        predicted_anomaly = 1 if s_hybrid > self.tau_fusion else 0
        return s_hybrid, predicted_anomaly
    
    def _evaluate_max_vote(self, s_p, s_l, s_c, s_a):
        """Max-vote: anomaly if ANY active engine exceeds threshold.
        
        The hybrid score is the weighted max for ranking/AUC purposes.
        The binary decision is based on any individual engine exceeding tau_fusion.
        """
        active_scores = []
        if self.w_p > 0:
            active_scores.append(s_p)
        if self.w_l > 0:
            active_scores.append(s_l)
        if self.w_c > 0:
            active_scores.append(s_c)
        if self.w_a > 0:
            active_scores.append(s_a)
        
        s_hybrid = max(active_scores) if active_scores else 0.0
        predicted_anomaly = 1 if s_hybrid > self.tau_fusion else 0
        return s_hybrid, predicted_anomaly
