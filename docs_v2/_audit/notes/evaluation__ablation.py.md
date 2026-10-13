# Source File Note: `evaluation/ablation.py`

## Purpose
Ablation analysis harness evaluating isolated engines and engine combinations against recorded evaluation scores ($S_p, S_l, S_c, S_a$) to quantify individual and combined contributions to intrusion detection performance.

## Public Classes and Functions
- `ABLATION_CONFIGS`: Dictionary defining 8 configurations:
  - `C1`: Physics Only (`w_p=1.0, w_l=0.0, w_c=0.0, w_a=0.0`)
  - `C2`: LSTM Only (`w_p=0.0, w_l=1.0, w_c=0.0, w_a=0.0`)
  - `C3`: Physics + LSTM (`w_p=0.5, w_l=0.5, w_c=0.0, w_a=0.0`)
  - `C4`: Policy Only (`w_p=0.0, w_l=0.0, w_c=1.0, w_a=0.0`)
  - `C5`: Availability Only (`w_p=0.0, w_l=0.0, w_c=0.0, w_a=1.0`)
  - `C6`: Physics + LSTM + Policy (`w_p=0.33, w_l=0.33, w_c=0.34, w_a=0.0`)
  - `C7_sum`: Full Hybrid weighted sum (`w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25`, strategy=`weighted_sum`)
  - `C7_max`: Full Hybrid max vote (`w_p=0.25, w_l=0.25, w_c=0.25, w_a=0.25`, strategy=`max_vote`)
- `find_optimal_threshold(y_true, scores, thresholds=None) -> tuple[float, float]`: Sweeps thresholds $\tau \in [0.05, 0.95]$ in increments of 0.05 to locate $\tau^*$ maximizing F1 score.
- `class AblationRunner(df_results: pd.DataFrame, tau_fusion: float = 0.5, optimize_threshold: bool = True)`
  - `run_config(config_name: str, weights: dict) -> dict`: Evaluates one config, computes classification metrics and detection latency, returns dictionary of metrics.
  - `run_all() -> pd.DataFrame`: Runs all 8 configs and packages results into a summary DataFrame.

## Inputs and Outputs
- `run_config()`:
  - Input: DataFrame containing `S_p`, `S_l`, `S_c`, `S_a`, `ground_truth`, and `scenario_id`.
  - Output: dict of metrics (precision, recall, f1, fpr, latency, auc_roc, tau_optimal).

## Config Keys and Constants Read
- Reads weight configurations from `ABLATION_CONFIGS`.

## Who Calls It
- `scripts.run_ablation`

## Side Effects
- Pure data processing in memory.

## Tests Covering It
- Evaluation and ablation execution scripts.

## Surprising / Notable Observations
- Threshold optimization behavior: `optimize_threshold = True` sweeps thresholds independently per configuration. Thus, the F1 comparisons across configurations reflect each configuration's best achievable performance rather than enforcing a fixed universal threshold.
- `C7_max` implementation: Computes `scores = self.df[active_cols].max(axis=1)` and optimizes $\tau$ against the maximum active score.
