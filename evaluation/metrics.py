import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

def calculate_classification_metrics(y_true, y_pred, y_scores=None):
    """
    Calculate standard classification metrics.
    
    Args:
        y_true: Ground truth binary labels (0 = normal, 1 = anomaly)
        y_pred: Predicted binary labels
        y_scores: Continuous anomaly scores (optional, for AUC)
        
    Returns:
        dict: Dictionary containing the metrics
    """
    metrics = {
        'precision': precision_score(y_true, y_pred, zero_division=0),
        'recall': recall_score(y_true, y_pred, zero_division=0),
        'f1': f1_score(y_true, y_pred, zero_division=0)
    }
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    metrics['fpr'] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    metrics['fnr'] = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    if y_scores is not None:
        try:
            metrics['roc_auc'] = roc_auc_score(y_true, y_scores)
            metrics['pr_auc'] = average_precision_score(y_true, y_scores)
        except ValueError:
            # Handles case where only one class is present
            metrics['roc_auc'] = float('nan')
            metrics['pr_auc'] = float('nan')
            
    return metrics

def calculate_detection_latency(df_results: pd.DataFrame) -> dict:
    """
    Calculate detection latency for attack scenarios.
    
    Args:
        df_results: DataFrame containing predictions for attack scenarios.
                    Must have columns: 'scenario_id', 'sequence_id', 'simulation_time_s',
                    'ground_truth', 'predicted_anomaly'.
                    
    Returns:
        dict: Latency statistics (median, mean, max, missed)
    """
    latencies = []
    missed = 0
    
    # Analyze each attack scenario
    for scenario_id, group in df_results.groupby('scenario_id'):
        group = group.sort_values('sequence_id')
        
        # Find when the attack actually started
        attack_mask = group['ground_truth'] == 1
        if not attack_mask.any():
            continue # Not an attack scenario
            
        attack_start_time = group.loc[attack_mask, 'simulation_time_s'].iloc[0]
        
        # Find when we first detected it (during or after the attack start)
        detection_mask = (group['predicted_anomaly'] == 1) & (group['simulation_time_s'] >= attack_start_time)
        
        if detection_mask.any():
            detection_time = group.loc[detection_mask, 'simulation_time_s'].iloc[0]
            latency = detection_time - attack_start_time
            latencies.append(latency)
        else:
            missed += 1
            
    if not latencies:
        return {'latency_mean': float('nan'), 'latency_median': float('nan'), 'latency_max': float('nan'), 'missed_attacks': missed}
        
    return {
        'latency_mean': np.mean(latencies),
        'latency_median': np.median(latencies),
        'latency_max': np.max(latencies),
        'missed_attacks': missed,
        'detected_attacks': len(latencies)
    }
