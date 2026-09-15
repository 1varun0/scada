import torch
import torch.nn as nn
import numpy as np

from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import DataPreprocessor

class TemporalEngine:
    """
    Engine 2: Temporal Behavior (Target: Subtle deviations, transients)
    Wraps the trained LSTM-AE to compute real-time reconstruction error.
    """
    def __init__(self, model: LSTMAutoencoder, preprocessor: DataPreprocessor, tau_l: float, device: str = "cpu"):
        """
        Args:
            model: Trained LSTMAutoencoder
            preprocessor: Fitted DataPreprocessor
            tau_l: Threshold for reconstruction error
            device: 'cpu' or 'cuda'
        """
        self.model = model
        self.model.eval()
        self.model.to(device)
        self.preprocessor = preprocessor
        self.tau_l = tau_l
        self.device = device
        self.criterion = nn.MSELoss()
        
    def evaluate(self, window_df) -> tuple[float, float]:
        """
        Evaluate a single window of telemetry.
        
        Args:
            window_df: Pandas DataFrame of shape (W, num_features)
            
        Returns:
            Tuple of (reconstruction_error, S_l)
            S_l is the normalized anomaly score in [0, 1].
        """
        # 1. Preprocess
        window_scaled = self.preprocessor.transform(window_df)
        data = window_scaled[self.preprocessor.feature_cols].values
        
        # 2. Convert to tensor: shape (1, W, num_features)
        x = torch.FloatTensor(data).unsqueeze(0).to(self.device)
        
        # 3. Compute reconstruction
        with torch.no_grad():
            reconstruction = self.model(x)
            loss = self.criterion(reconstruction, x).item()
            
        # 4. Normalize to [0, 1]
        s_l = min(loss / self.tau_l, 1.0) if self.tau_l > 0 else 0.0
        
        return loss, s_l
