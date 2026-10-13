# Source File Note: `models/lstm_autoencoder.py`

## Purpose
Defines the PyTorch sequence-to-sequence `LSTMAutoencoder` neural network module used by Engine 2 (Temporal Engine) to model nominal telemetry dynamics and detect temporal deviations via reconstruction error.

## Public Classes and Functions
- `class LSTMAutoencoder(nn.Module)`
  - `__init__(input_dim: int, hidden_dim: int = 32, num_layers: int = 1)`:
    - Initializes encoder: `nn.LSTM(input_size=input_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)`.
    - Initializes decoder: `nn.LSTM(input_size=hidden_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)`.
    - Output projection: `nn.Linear(hidden_dim, input_dim)`.
  - `forward(x: torch.Tensor) -> torch.Tensor`:
    - Input shape: `(batch_size, seq_len, input_dim)`.
    - Extracts final hidden state $h_T \in \mathbb{R}^{B \times 1 \times H}$.
    - Repeats latent vector $h_T$ along sequence dimension: `(batch_size, seq_len, hidden_dim)`.
    - Passes repeated latent through decoder LSTM and linear projection.
    - Output shape: `(batch_size, seq_len, input_dim)`.

## Inputs and Outputs
- `forward(x)`:
  - Input: 3D FloatTensor of shape $(B, W, D)$ where $B$ is batch size, $W$ is sequence/window length, $D$ is feature dimension.
  - Output: 3D FloatTensor of identical shape $(B, W, D)$ containing reconstructed feature trajectories.

## Config Keys and Constants Read
- Does not directly import `PARAMS`; instantiated with parameters (typically `input_dim=5`, `hidden_dim=32`, `num_layers=1`).

## Who Calls It
- `models.trainer.LSTMTrainer`
- `scripts.train_lstm`
- `engines.temporal_engine.TemporalEngine`
- `scada_live.scada_ids.streaming_ids.StreamingIDS`

## Side Effects
- Standard PyTorch forward pass with parameter allocations.

## Tests Covering It
- `tests/test_engines.py`

## Surprising / Notable Observations
- Bottleneck structure: The entire temporal trajectory over window length $W$ is compressed into a single vector $h_T$ (the final hidden state of the top layer).
- Decoder feed: The decoder receives `latent.repeat(1, seq_len, 1)` as input at every timestep rather than a step-by-step autoregressive output or start-of-sequence token.
- Output projection: Linear layer directly maps hidden representation to reconstructed features without output activation (e.g. no sigmoid or tanh), matching MinMax-scaled input range $[0, 1]$.
