import torch
import torch.nn as nn

class LSTMAutoencoder(nn.Module):
    """
    LSTM Autoencoder for capturing temporal behaviors and detecting anomalies
    via reconstruction error.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 32, num_layers: int = 1):
        """
        Args:
            input_dim: Number of features in the input window
            hidden_dim: Size of the LSTM hidden states
            num_layers: Number of LSTM layers
        """
        super(LSTMAutoencoder, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Encoder
        self.encoder = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        
        # Decoder
        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        
        # Output projection
        self.output_layer = nn.Linear(hidden_dim, input_dim)
        
    def forward(self, x):
        """
        x shape: (batch_size, window_size, input_dim)
        """
        batch_size, seq_len, _ = x.size()
        
        # Encode
        # We only care about the final hidden state of the sequence
        _, (hidden, cell) = self.encoder(x)
        
        # hidden shape: (num_layers, batch_size, hidden_dim)
        # We take the top layer's hidden state to use as the latent representation
        latent = hidden[-1].unsqueeze(1) # shape: (batch_size, 1, hidden_dim)
        
        # Repeat the latent vector for the sequence length
        latent_repeated = latent.repeat(1, seq_len, 1) # shape: (batch_size, seq_len, hidden_dim)
        
        # Decode
        decoder_out, _ = self.decoder(latent_repeated) # shape: (batch_size, seq_len, hidden_dim)
        
        # Project back to input dimension
        reconstruction = self.output_layer(decoder_out) # shape: (batch_size, seq_len, input_dim)
        
        return reconstruction
