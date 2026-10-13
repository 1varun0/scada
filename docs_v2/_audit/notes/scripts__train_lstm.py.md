# Source File Note: `scripts/train_lstm.py`

## Purpose
Training driver for the Engine 2 LSTM Autoencoder. Implements scenario-level train/validation/test splitting across 60 normal scenarios, fits the feature scaler, generates sliding windows, optimizes model parameters, and persists trained checkpoints.

## Public Classes and Functions
- `load_normal_data(db_path="data/scada_ids.db") -> pd.DataFrame`: Queries all normal rows (`scenario_id LIKE 'N_%'`) from SQLite, ordered by `(scenario_id, sequence_id)`.
- `train_val_test_split_scenarios(df, val_ratio=0.15, test_ratio=0.15)`:
  - Shuffles unique scenario IDs with fixed seed `np.random.seed(42)`.
  - Partitions scenarios into Test ($15\% = 9$), Val ($15\% = 9$), and Train ($70\% = 42$).
  - Returns tuple of 3 partitioned DataFrames and 3 scenario ID lists.
- `main()`:
  - Fits `DataPreprocessor(window_size=10)` on training set features.
  - Transforms train and val splits; creates sliding windows.
  - Instantiates `LSTMAutoencoder(input_dim=5, hidden_dim=32, num_layers=1)`.
  - Runs `ModelTrainer` with `batch_size=128`, `learning_rate=1e-3`, `epochs=20`, `patience=3`.
  - Serializes:
    - `checkpoints/lstm_ae_v1.pt`
    - `checkpoints/scaler_v1.pkl`
    - `checkpoints/data_split_v1.json`

## Inputs and Outputs
- Inputs: `data/scada_ids.db` (`scada_telemetry` table normal rows).
- Outputs:
  - `checkpoints/lstm_ae_v1.pt`
  - `checkpoints/scaler_v1.pkl`
  - `checkpoints/data_split_v1.json`

## Config Keys and Constants Read
- Hard-coded split ratios: `val_ratio=0.15`, `test_ratio=0.15`.
- Hard-coded hyperparameters: `input_dim=5`, `hidden_dim=32`, `num_layers=1`, `batch_size=128`, `learning_rate=1e-3`, `epochs=20`, `patience=3`.

## Who Calls It
- Executed via CLI: `python scripts/train_lstm.py`.

## Side Effects
- Overwrites checkpoint files in `checkpoints/`.

## Tests Covering It
- Model training workflow.

## Surprising / Notable Observations
- Exact split numbers:
  - Total normal scenarios: 60.
  - Train: 42 scenarios (42,000 samples).
  - Validation: 9 scenarios (9,000 samples).
  - Held-out test: 9 scenarios (9,000 samples).
  - Total train + validation = 51 scenarios.
- Strict scenario isolation: Splitting by whole scenario IDs (`train_val_test_split_scenarios`) guarantees that windows never leak information between training, validation, and evaluation splits.
- Scaler fitting: The `MinMaxScaler` is fit exclusively on `df_train` (the 42 training scenarios), preventing data leakage into the scaler parameters.
