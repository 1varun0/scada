import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import torch
from torch.utils.data import Dataset

class SCADADataset(Dataset):
    """PyTorch Dataset for sliding windows."""
    def __init__(self, X):
        # X shape: (num_samples, window_size, num_features)
        self.X = torch.FloatTensor(X)
        
    def __len__(self):
        return len(self.X)
        
    def __getitem__(self, idx):
        return self.X[idx]

class DataPreprocessor:
    """
    Preprocesses SCADA telemetry data for the LSTM-AE.
    Handles per-feature normalization and scenario-aware windowing.
    """
    def __init__(self, window_size: int = 10, feature_cols: list[str] = None):
        self.window_size = window_size
        self.scaler = MinMaxScaler()
        self.feature_cols = feature_cols or [
            'tank_level_observed', 'q_in', 'q_out', 'pump_state', 'valve_state'
        ]
        self.is_fitted = False
        
    def fit(self, df: pd.DataFrame):
        """Fit the scaler on normal training data."""
        self.scaler.fit(df[self.feature_cols].values)
        self.is_fitted = True
        
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize features using the fitted scaler."""
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted before transform.")
            
        df_scaled = df.copy()
        df_scaled[self.feature_cols] = self.scaler.transform(df[self.feature_cols].values)
        return df_scaled
        
    def create_windows(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create sliding windows of size W.
        IMPORTANT: This must be scenario-aware! We group by scenario_id so 
        windows do not cross scenario boundaries.
        
        Returns:
            X: numpy array of shape (num_windows, window_size, num_features)
            scenario_ids: numpy array of scenario IDs corresponding to each window's last timestep
            sequence_ids: numpy array of sequence IDs corresponding to each window's last timestep
        """
        X_list = []
        scenario_list = []
        sequence_list = []
        
        # Group by scenario to avoid boundary crossing
        for scenario_id, group in df.groupby('scenario_id'):
            # Sort by sequence_id just in case
            group = group.sort_values('sequence_id')
            
            data = group[self.feature_cols].values
            seq_ids = group['sequence_id'].values
            
            n_samples = len(data)
            if n_samples < self.window_size:
                continue
                
            for i in range(n_samples - self.window_size + 1):
                window = data[i:i + self.window_size]
                X_list.append(window)
                scenario_list.append(scenario_id)
                sequence_list.append(seq_ids[i + self.window_size - 1])
                
        return np.array(X_list), np.array(scenario_list), np.array(sequence_list)
        
    def fit_transform_windows(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        self.fit(df)
        df_scaled = self.transform(df)
        return self.create_windows(df_scaled)
