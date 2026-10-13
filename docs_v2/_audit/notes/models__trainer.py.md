# Source File Note: `models/trainer.py`

## Purpose
Training framework for `LSTMAutoencoder`. Encapsulates DataLoader setup, Adam optimizer, MSE reconstruction loss calculation, validation tracking, early stopping, and checkpoint persistence.

## Public Classes and Functions
- `class ModelTrainer(model: LSTMAutoencoder, device: str = "cpu", learning_rate: float = 1e-3, batch_size: int = 64)`
  - `__init__(...)`: Configures optimizer `Adam(lr=learning_rate)`, loss criterion `nn.MSELoss()`, batch size, and execution device.
  - `train(train_dataset: SCADADataset, val_dataset: SCADADataset = None, epochs: int = 50, patience: int = 5) -> dict`: Executes training loop across epochs, logs loss per epoch, performs early stopping if `val_loss` fails to improve for `patience` consecutive epochs, restores best model weights, and returns dictionary history (`{'train_loss': [...], 'val_loss': [...]}`).
  - `save_checkpoint(filepath: str) -> None`: Creates destination directory if necessary and serializes `self.model.state_dict()` via `torch.save()`.
  - `load_checkpoint(filepath: str) -> None`: Loads weights into model via `self.model.load_state_dict(torch.load(..., map_location=device))`.

## Inputs and Outputs
- `train()`:
  - Inputs: `train_dataset: SCADADataset`, optional `val_dataset: SCADADataset`, integer `epochs`, integer `patience`.
  - Output: dict `{'train_loss': list[float], 'val_loss': list[float]}`.
- `save_checkpoint()` / `load_checkpoint()`: Filepath string pointing to `.pt` weights.

## Config Keys and Constants Read
- Hyperparameters passed explicitly (defaults: `learning_rate=1e-3`, `batch_size=64`, `epochs=50`, `patience=5`).

## Who Calls It
- `scripts.train_lstm`

## Side Effects
- Mutates PyTorch model weights.
- `save_checkpoint()` writes file to disk (e.g. `checkpoints/lstm_ae_v1.pt`).
- Prints epoch progress to standard output via `tqdm` and `print`.

## Tests Covering It
- Indirectly verified by model training and integration runs.

## Surprising / Notable Observations
- State restoration: Lines 96-98 clone and restore `best_state` when training finishes or early stops, guaranteeing that the model in memory has the lowest validation loss weights rather than the terminal epoch weights.
- Checkpoint format: Stores bare `state_dict` (not a full checkpoint bundle containing optimizer state or epoch counter).
