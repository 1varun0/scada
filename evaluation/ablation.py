import pandas as pd
import numpy as np
from engines.fusion_engine import FusionEngine
from evaluation.metrics import calculate_classification_metrics, calculate_detection_latency

ABLATION_CONFIGS = {
    "C1": {"w_p": 1.0, "w_l": 0.0, "w_c": 0.0, "w_a": 0.0, "desc": "Physics Only"},
    "C2": {"w_p": 0.0, "w_l": 1.0, "w_c": 0.0, "w_a": 0.0, "desc": "LSTM Only"},
    "C3": {"w_p": 0.5, "w_l": 0.5, "w_c": 0.0, "w_a": 0.0, "desc": "Physics + LSTM"},
    "C4": {"w_p": 0.0, "w_l": 0.0, "w_c": 1.0, "w_a": 0.0, "desc": "Policy Only"},
    "C5": {"w_p": 0.0, "w_l": 0.0, "w_c": 0.0, "w_a": 1.0, "desc": "Availability Only"},
    "C6": {"w_p": 0.33, "w_l": 0.33, "w_c": 0.34, "w_a": 0.0, "desc": "Physics+LSTM+Policy"},
    "C7_sum": {"w_p": 0.25, "w_l": 0.25, "w_c": 0.25, "w_a": 0.25, "desc": "Full Hybrid (sum)", "strategy": "weighted_sum"},
    "C7_max": {"w_p": 0.25, "w_l": 0.25, "w_c": 0.25, "w_a": 0.25, "desc": "Full Hybrid (max)", "strategy": "max_vote"},
}

def find_optimal_threshold(y_true, scores, thresholds=None):
    """Find the threshold that maximizes F1 score."""
    if thresholds is None:
        thresholds = np.arange(0.05, 1.0, 0.05)
    
    best_f1, best_tau = 0.0, 0.5
    for tau in thresholds:
        preds = (scores > tau).astype(int)
        metrics = calculate_classification_metrics(y_true, preds)
        if metrics['f1'] > best_f1:
            best_f1 = metrics['f1']
            best_tau = tau
    return best_tau, best_f1

class AblationRunner:
    def __init__(self, df_results: pd.DataFrame, tau_fusion: float = 0.5, 
                 optimize_threshold: bool = True):
        """
        Args:
            df_results: DataFrame containing raw individual engine scores:
                        S_p, S_l, S_c, S_a, and ground_truth.
            tau_fusion: Default threshold for the fusion engine.
            optimize_threshold: If True, find optimal threshold per config (fair comparison).
        """
        self.df = df_results
        self.tau_fusion = tau_fusion
        self.optimize_threshold = optimize_threshold
        
    def run_config(self, config_name: str, weights: dict) -> dict:
        """Run a single ablation configuration."""
        strategy = weights.get('strategy', 'weighted_sum')
        desc = weights.get('desc', config_name)
        
        engine = FusionEngine(
            w_p=weights['w_p'],
            w_l=weights['w_l'],
            w_c=weights['w_c'],
            w_a=weights['w_a'],
            tau_fusion=self.tau_fusion,
            strategy=strategy
        )
        
        # Calculate fused scores using the engine's strategy
        if strategy == "max_vote":
            # For max_vote, the score is the max of active engines
            active_cols = []
            if weights['w_p'] > 0: active_cols.append('S_p')
            if weights['w_l'] > 0: active_cols.append('S_l')
            if weights['w_c'] > 0: active_cols.append('S_c')
            if weights['w_a'] > 0: active_cols.append('S_a')
            scores = self.df[active_cols].max(axis=1) if active_cols else pd.Series(0.0, index=self.df.index)
        else:
            scores = (
                engine.w_p * self.df['S_p'] +
                engine.w_l * self.df['S_l'] +
                engine.w_c * self.df['S_c'] +
                engine.w_a * self.df['S_a']
            )
        
        # Determine threshold
        tau = self.tau_fusion
        if self.optimize_threshold:
            tau, _ = find_optimal_threshold(self.df['ground_truth'], scores)
        
        predictions = (scores > tau).astype(int)
        
        # Create a temp dataframe for latency calculation
        df_temp = self.df.copy()
        df_temp['predicted_anomaly'] = predictions
        
        metrics = calculate_classification_metrics(self.df['ground_truth'], predictions, scores)
        latency = calculate_detection_latency(df_temp)
        
        return {**metrics, **latency, 'tau_optimal': tau, 'description': desc}

    def run_all(self) -> pd.DataFrame:
        """Run all configurations and return a summary DataFrame."""
        results = {}
        for name, weights in ABLATION_CONFIGS.items():
            results[name] = self.run_config(name, weights)
            
        return pd.DataFrame.from_dict(results, orient='index')
