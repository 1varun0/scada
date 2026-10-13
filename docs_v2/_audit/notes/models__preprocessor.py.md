# Source File Note: `models/preprocessor.py`

## Purpose
Prepares SCADA telemetry data for training and evaluating the LSTM Autoencoder. Provides `MinMaxScaler` normalization across 5 core continuous/actuator features and generates scenario-partitioned sliding windows.

## Public Classes and Functions
- `class SCADADataset(torch.utils.data.Dataset)`:
  - `__init__(X: np.ndarray)`: Stores FloatTensor of shape $(N, W, D)$.
  - `__len__() -> int`: Returns sample count $N$.
  - `__getitem__(idx: int) -> torch.FloatTensor`: Returns tensor slice.
- `class DataPreprocessor(window_size: int = 10, feature_cols: list[str] = None)`
  - `__init__(...)`: Default `window_size = 10`, `scaler = MinMaxScaler()`. Default `feature_cols = ['tank_level_observed', 'q_in', 'q_out', 'pump_state', 'valve_state']` (5 features).
  - `fit(df: pd.DataFrame) -> None`: Fits `MinMaxScaler` on specified feature columns.
  - `transform(df: pd.DataFrame) -> pd.DataFrame`: Normalizes feature columns via fitted scaler.
  - `create_windows(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]`: Partitions dataframe by `scenario_id` (preventing window spillover across scenarios) and extracts rolling windows of length $W$. Returns `(X, scenario_ids, sequence_ids)` where sequence_id represents the rightmost (current) tick in each window.
  - `fit_transform_windows(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]`: Convenience method running fit, transform, and window extraction.

## Inputs and Outputs
- `fit(df)`: Input Pandas DataFrame.
- `transform(df)`: Input Pandas DataFrame, output scaled DataFrame.
- `create_windows(df)`:
  - Input: Pandas DataFrame with `scenario_id`, `sequence_id`, and feature columns.
  - Output: `(X, scenario_ids, sequence_ids)` where $X \in \mathbb{R}^{M \times 10 \times 5}$.

## Config Keys and Constants Read
- Does not directly import `PARAMS`; default feature list hard-coded at line 28.

## Who Calls It
- `models.trainer.LSTMTrainer`
- `scripts.train_lstm`
- `scripts.run_evaluation`
- `engines.temporal_engine.TemporalEngine`
- `scada_live.scada_ids.streaming_ids.StreamingIDS`

## Side Effects
- Mutates internal `scaler` and `is_fitted` flag.

## Tests Covering It
- `tests/test_engines.py`

## Surprising / Notable Observations
- Feature dimensionality: Exactly 5 features (`tank_level_observed`, `q_in`, `q_out`, `pump_state`, `valve_state`). Notice that cyber/metadata columns (`data_age_ms`, `user_role`, `communication_status`) are not fed to the LSTM-AE.
- Window size: Fixed at $W=10$ steps ($10\text{ seconds}$).
- Boundary-aware windowing: Grouping by `scenario_id` at line 62 guarantees that sliding windows never cross boundaries between different simulation scenarios. For a scenario of length 1,000 steps, exactly $1000 - 10 + 1 = 991$ windows are produced (ticks 9 to 999).
