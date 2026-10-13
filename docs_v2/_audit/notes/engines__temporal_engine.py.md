# Source File Note: `engines/temporal_engine.py`

## Purpose
Implements Engine 2 (Temporal Behavior Engine). Uses a PyTorch LSTM Autoencoder to evaluate sequences of telemetry features, computing reconstruction Mean Squared Error (MSE) and normalizing it to an anomaly score $S_l \in [0, 1]$.

## Public Classes and Functions
- `class TemporalEngine(model: LSTMAutoencoder, preprocessor: DataPreprocessor, tau_l: float, device: str = "cpu")`
  - `__init__(...)`: Puts model into evaluation mode (`model.eval()`), sets device, saves preprocessor, threshold $\tau_l$, and initializes `self.criterion = nn.MSELoss()`.
  - `evaluate(window_df) -> tuple[float, float]`: Preprocesses sliding window DataFrame, formats tensor $(1, W, D)$, passes through LSTM-AE with `torch.no_grad()`, evaluates MSE loss, and scales to $S_l$. Returns `(loss, s_l)`.

## Inputs and Outputs
- `evaluate(window_df)`:
  - Input: Pandas DataFrame with $W$ rows containing the required feature columns.
  - Output: `tuple[float, float]`: `(reconstruction_loss, s_l)` where $S_l \in [0.0, 1.0]$.

## Config Keys and Constants Read
- Threshold $\tau_l$ passed in constructor (default from `PARAMS.controller.tau_l = 0.0085`).

## Who Calls It
- `evaluation.ablation`
- `scripts.run_evaluation`
- `tests.test_engines`

## Side Effects
- CPU/GPU tensor allocation during inference; no persistence or network side effects.

## Tests Covering It
- `tests/test_engines.py`:
  - `test_temporal_engine_evaluate`
  - `test_temporal_engine_threshold_scaling`

## Surprising / Notable Observations
- Window-level evaluation: The MSE loss is computed across all elements of the window tensor $(1 \times W \times D)$:
  $$\mathcal{L} = \frac{1}{W \cdot D} \sum_{t=1}^W \sum_{j=1}^D (\hat{x}_{t,j} - x_{t,j})^2$$
- Normalized score:
  $$S_l = \min\left(\frac{\mathcal{L}}{\tau_l}, 1.0\right)$$
  When reconstruction loss reaches or exceeds $\tau_l$, $S_l = 1.0$.
