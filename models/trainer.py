import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
import os
import json

from models.lstm_autoencoder import LSTMAutoencoder
from models.preprocessor import SCADADataset

class ModelTrainer:
    """Trainer for the LSTM Autoencoder."""
    
    def __init__(
        self, 
        model: LSTMAutoencoder,
        device: str = "cpu",
        learning_rate: float = 1e-3,
        batch_size: int = 64
    ):
        self.model = model.to(device)
        self.device = device
        self.batch_size = batch_size
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()
        
    def train(self, train_dataset: SCADADataset, val_dataset: SCADADataset = None, epochs: int = 50, patience: int = 5) -> dict:
        """
        Train the autoencoder using only normal data.
        Early stopping based on validation loss if provided.
        """
        train_loader = DataLoader(train_dataset, batch_size=self.batch_size, shuffle=True)
        
        val_loader = None
        if val_dataset is not None:
            val_loader = DataLoader(val_dataset, batch_size=self.batch_size, shuffle=False)
            
        history = {'train_loss': [], 'val_loss': []}
        best_val_loss = float('inf')
        best_state = None
        patience_counter = 0
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            
            pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
            for batch in pbar:
                batch = batch.to(self.device)
                self.optimizer.zero_grad()
                
                # Forward
                reconstruction = self.model(batch)
                loss = self.criterion(reconstruction, batch)
                
                # Backward
                loss.backward()
                self.optimizer.step()
                
                train_loss += loss.item() * batch.size(0)
                pbar.set_postfix({'loss': loss.item()})
                
            train_loss /= len(train_loader.dataset)
            history['train_loss'].append(train_loss)
            
            # Validation
            if val_loader is not None:
                self.model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch in val_loader:
                        batch = batch.to(self.device)
                        reconstruction = self.model(batch)
                        loss = self.criterion(reconstruction, batch)
                        val_loss += loss.item() * batch.size(0)
                
                val_loss /= len(val_loader.dataset)
                history['val_loss'].append(val_loss)
                print(f"Epoch {epoch+1} - Train Loss: {train_loss:.6f} - Val Loss: {val_loss:.6f}")
                
                # Early Stopping — save best model weights
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
                    print(f"  -> New best val loss: {best_val_loss:.6f}")
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        print(f"Early stopping at epoch {epoch+1}")
                        break
            else:
                print(f"Epoch {epoch+1} - Train Loss: {train_loss:.6f}")
        
        # Restore best model weights
        if best_state is not None:
            self.model.load_state_dict(best_state)
            print(f"Restored best model weights (val loss: {best_val_loss:.6f})")
                
        return history

    def save_checkpoint(self, filepath: str):
        """Save model weights."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        torch.save(self.model.state_dict(), filepath)
        
    def load_checkpoint(self, filepath: str):
        """Load model weights."""
        self.model.load_state_dict(torch.load(filepath, map_location=self.device))
