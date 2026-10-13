# Source File Note: `engines/fusion_engine.py`

## Purpose
Implements Engine 5 (Hybrid Evidence Fusion Engine). Combines normalized evidence scores ($S_p, S_l, S_c, S_a$) into a unified hybrid anomaly score $S_{\text{hybrid}} \in [0, 1]$ and produces a binary detection decision $\hat{y} \in \{0, 1\}$.

## Public Classes and Functions
- `class FusionEngine(w_p: float, w_l: float, w_c: float, w_a: float, tau_fusion: float, strategy: str = "weighted_sum")`
  - `__init__(...)`: Normalizes weights to sum to 1.0 if `total > 0` and `abs(total - 1.0) > 1e-5`. Stores weights, threshold `tau_fusion`, and strategy name (`"weighted_sum"` or `"max_vote"`).
  - `evaluate(s_p: float, s_l: float, s_c: float, s_a: float) -> tuple[float, int]`: Dispatches to `_evaluate_max_vote` or `_evaluate_weighted_sum`. Returns `(s_hybrid, predicted_anomaly)`.
  - `_evaluate_weighted_sum(...) -> tuple[float, int]`: Calculates $S_{\text{hybrid}} = \sum w_i S_i$ and checks $S_{\text{hybrid}} > \tau_{\text{fusion}}$.
  - `_evaluate_max_vote(...) -> tuple[float, int]`: Calculates $S_{\text{hybrid}} = \max(\{S_i \mid w_i > 0\})$ and checks $S_{\text{hybrid}} > \tau_{\text{fusion}}$.

## Inputs and Outputs
- `evaluate()`:
  - Inputs: floats $S_p, S_l, S_c, S_a \in [0.0, 1.0]$.
  - Output: `tuple[float, int]`: `(s_hybrid, predicted_anomaly)` where `s_hybrid` $\in [0.0, 1.0]$ and `predicted_anomaly` $\in \{0, 1\}$.

## Config Keys and Constants Read
- Weights and threshold passed explicitly via constructor.

## Who Calls It
- `evaluation.ablation`
- `scripts.run_evaluation`
- `scripts.run_ablation`
- `tests.test_fusion`

## Side Effects
- Stateless computation; no side effects.

## Tests Covering It
- `tests/test_fusion.py`:
  - `test_fusion_weighted_sum`
  - `test_fusion_max_vote`
  - `test_fusion_weight_normalization`
  - `test_fusion_decision_threshold`

## Surprising / Notable Observations
- Decision rule uses strict inequality: `predicted_anomaly = 1 if s_hybrid > self.tau_fusion else 0` [CODE engines/fusion_engine.py:59, 79]. If $S_{\text{hybrid}}$ exactly equals $\tau_{\text{fusion}}$, it evaluates as normal (0).
- In `max_vote` mode, an engine's score is considered active only if its corresponding weight is strictly positive ($w_i > 0$). This allows ablation studies to cleanly deactivate engines while running under max-vote mode.
