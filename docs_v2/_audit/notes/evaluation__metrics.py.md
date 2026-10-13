# Source File Note: `evaluation/metrics.py`

## Purpose
Provides statistical evaluation functions calculating point-in-time classification metrics (Precision, Recall, F1, FPR, FNR, ROC-AUC, PR-AUC) and episode-level detection latency across simulated attacks.

## Public Classes and Functions
- `calculate_classification_metrics(y_true, y_pred, y_scores=None) -> dict`:
  - Computes scikit-learn metrics: `precision`, `recall`, `f1`, `fpr` ($FP / (FP + TN)$), `fnr` ($FN / (FN + TP)$).
  - If `y_scores` is supplied: computes `roc_auc` and `pr_auc` (average precision).
- `calculate_detection_latency(df_results: pd.DataFrame) -> dict`:
  - Groups by `scenario_id` and finds earliest attack onset time: $t_{\text{start}} = \min(\{t \mid y_{\text{true}}(t) = 1\})$.
  - Finds first alert at or after onset: $t_{\text{detect}} = \min(\{t \ge t_{\text{start}} \mid \hat{y}(t) = 1\})$.
  - Evaluates latency $\Delta t = t_{\text{detect}} - t_{\text{start}}$.
  - Returns `latency_mean`, `latency_median`, `latency_max`, `missed_attacks`, and `detected_attacks`.

## Inputs and Outputs
- `calculate_classification_metrics`:
  - Inputs: arrays `y_true`, `y_pred`, optional `y_scores`.
  - Output: dict of floats.
- `calculate_detection_latency`:
  - Input: DataFrame with `scenario_id`, `sequence_id`, `simulation_time_s`, `ground_truth`, `predicted_anomaly`.
  - Output: dict of floats and ints.

## Config Keys and Constants Read
- None.

## Who Calls It
- `evaluation.ablation`
- `evaluation.reporter`
- `scripts.run_evaluation`
- `scripts.run_ablation`
- `experiments/compute_metrics.py`

## Side Effects
- Pure computation in memory.

## Tests Covering It
- Covered in evaluation workflows.

## Surprising / Notable Observations
- Latency conditioning: Detection latency strictly requires `simulation_time_s >= attack_start_time`. Pre-attack false alarms are not counted as premature detections.
- Handling of missed attacks in latency: If an attack episode produces zero detections ($\hat{y} = 0$ throughout the attack), it increments `missed` and is excluded from the calculation of `latency_mean` and `latency_median`.
