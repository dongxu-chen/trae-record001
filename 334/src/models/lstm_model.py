import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')


def pinball_loss(y_pred, y_true, quantile):
    error = y_true - y_pred
    loss = torch.max(quantile * error, (quantile - 1) * error)
    return torch.mean(loss)


def combined_pinball_loss(y_pred, y_true, quantiles):
    total_loss = 0.0
    for i, q in enumerate(quantiles):
        total_loss += pinball_loss(y_pred[:, :, i], y_true, q)
    return total_loss / len(quantiles)


class LSTMNetwork(nn.Module):
    def __init__(self, input_size=3, hidden_size=64, num_layers=2, output_size=2, dropout=0.2):
        super(LSTMNetwork, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.input_projection = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        self.lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        self.temporal_attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1),
            nn.Softmax(dim=1)
        )
        
        self.feature_attention = nn.Sequential(
            nn.Linear(input_size, input_size),
            nn.Sigmoid()
        )
        
        self.fc_layers = nn.Sequential(
            nn.Linear(hidden_size * 2 + input_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_size)
        )

    def forward(self, x):
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        feat_weights = self.feature_attention(x.mean(dim=1))
        x_weighted = x * feat_weights.unsqueeze(1)
        
        proj = self.input_projection(x_weighted.reshape(-1, x.size(2)))
        proj = proj.reshape(batch_size, seq_len, -1)
        
        h0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
        
        lstm_out, _ = self.lstm(proj, (h0, c0))
        
        attn_weights = self.temporal_attention(lstm_out)
        attn_applied = torch.sum(attn_weights * lstm_out, dim=1)
        
        last_feature = x[:, -1, :]
        combined = torch.cat([attn_applied, last_feature], dim=1)
        
        output = self.fc_layers(combined)
        
        return output


class QuantileLSTMNetwork(nn.Module):
    def __init__(self, input_size=3, hidden_size=48, num_layers=2, quantiles=None, dropout=0.15):
        super(QuantileLSTMNetwork, self).__init__()
        self.quantiles = quantiles or [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
        self.n_quantiles = len(self.quantiles)
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.input_projection = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        self.lstm = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1),
            nn.Softmax(dim=1)
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2 + input_size, 96),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(96, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 2 * self.n_quantiles)
        )

    def forward(self, x):
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        proj = self.input_projection(x.reshape(-1, x.size(2)))
        proj = proj.reshape(batch_size, seq_len, -1)
        
        h0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_size).to(x.device)
        
        lstm_out, _ = self.lstm(proj, (h0, c0))
        
        attn_weights = self.attention(lstm_out)
        attn_applied = torch.sum(attn_weights * lstm_out, dim=1)
        
        last_feature = x[:, -1, :]
        combined = torch.cat([attn_applied, last_feature], dim=1)
        
        output = self.fc(combined)
        return output.view(batch_size, 2, self.n_quantiles)


class LSTMModel:
    def __init__(self, model_dir='models', device=None):
        self.model_dir = model_dir
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.quantile_model = None
        self.input_size = None
        self.output_size = 2
        self.quantiles = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
        self.is_fitted_ = False
        self._coverage_stats = None

    def fit(self, X, y, epochs=100, batch_size=32, learning_rate=0.001):
        self.input_size = X.shape[2]
        
        X = torch.FloatTensor(X)
        y = torch.FloatTensor(y)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        self.model = LSTMNetwork(
            input_size=self.input_size,
            hidden_size=64,
            num_layers=2,
            output_size=self.output_size,
            dropout=0.2
        ).to(self.device)
        
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=1e-5)
        criterion = nn.MSELoss()
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        print(f"\nLSTM point model training on {self.device}...")
        print(f"Input size: {self.input_size} features")
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            self.model.eval()
            with torch.no_grad():
                X_val_dev = X_val.to(self.device)
                y_val_dev = y_val.to(self.device)
                val_outputs = self.model(X_val_dev)
                val_loss = criterion(val_outputs, y_val_dev)
            
            scheduler.step(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= 15:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Train Loss: {train_loss/len(train_loader):.4f}, Val Loss: {val_loss:.4f}")
        
        val_pred = self.model(X_val.to(self.device)).detach().cpu().numpy()
        metrics = self._calculate_metrics(y_val.numpy(), val_pred)
        print(f"LSTM point model training completed.")
        print(f"  MAE: {metrics['mae']:.2f}, RMSE: {metrics['rmse']:.2f}, R2: {metrics['r2']:.4f}")
        
        self._fit_quantile_model(X_train, y_train, X_val, y_val, epochs=100, batch_size=batch_size, learning_rate=learning_rate)
        
        self._calculate_coverage(X_val, y_val)
        
        self.is_fitted_ = True
        return self

    def _fit_quantile_model(self, X_train, y_train, X_val, y_val, epochs=100, batch_size=32, learning_rate=0.001):
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        self.quantile_model = QuantileLSTMNetwork(
            input_size=self.input_size,
            hidden_size=48,
            num_layers=2,
            quantiles=self.quantiles,
            dropout=0.15
        ).to(self.device)
        
        optimizer = optim.Adam(self.quantile_model.parameters(), lr=learning_rate, weight_decay=1e-5)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        print("\nLSTM quantile model training (Pinball Loss)...")
        print(f"Quantiles: {self.quantiles}")
        
        for epoch in range(epochs):
            self.quantile_model.train()
            train_loss = 0
            
            for batch_X, batch_y in train_loader:
                batch_X = batch_X.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.quantile_model(batch_X)
                loss = combined_pinball_loss(outputs, batch_y, self.quantiles)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.quantile_model.parameters(), max_norm=1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            self.quantile_model.eval()
            with torch.no_grad():
                X_val_dev = X_val.to(self.device)
                y_val_dev = y_val.to(self.device)
                val_outputs = self.quantile_model(X_val_dev)
                val_loss = combined_pinball_loss(val_outputs, y_val_dev, self.quantiles)
            
            scheduler.step(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= 15:
                    print(f"Early stopping at epoch {epoch+1}")
                    break
            
            if (epoch + 1) % 10 == 0:
                print(f"Quantile Epoch [{epoch+1}/{epochs}], Loss: {train_loss/len(train_loader):.4f}, Val Loss: {val_loss:.4f}")
        
        print("LSTM quantile model training completed.")

    def _calculate_coverage(self, X_val, y_val):
        self.quantile_model.eval()
        with torch.no_grad():
            X_val_dev = X_val.to(self.device)
            quantile_preds = self.quantile_model(X_val_dev).cpu().numpy()
        
        y_val_np = y_val.numpy()
        coverage_stats = {}
        
        for i, q in enumerate(self.quantiles):
            covered = np.mean(y_val_np <= quantile_preds[:, :, i])
            coverage_stats[q] = covered
        
        for conf in [0.5, 0.8, 0.9, 0.95]:
            lower_q = (1 - conf) / 2
            upper_q = 1 - lower_q
            
            if lower_q in self.quantiles and upper_q in self.quantiles:
                li = self.quantiles.index(lower_q)
                ui = self.quantiles.index(upper_q)
                
                lower = quantile_preds[:, :, li]
                upper = quantile_preds[:, :, ui]
                
                covered = np.mean((y_val_np >= lower) & (y_val_np <= upper))
                coverage_stats[f'{int(conf*100)}%_interval'] = covered
        
        self._coverage_stats = coverage_stats
        print("\nQuantile Coverage Verification:")
        for q, cov in coverage_stats.items():
            if isinstance(q, str):
                print(f"  {q}: {cov:.3f}")
            else:
                print(f"  Q{int(q*100)}: {cov:.3f} (expected: {q:.2f})")

    def predict(self, X):
        if not self.is_fitted_:
            raise RuntimeError("Model must be fitted before predict")
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            predictions = self.model(X_tensor).cpu().numpy()
        
        return predictions

    def predict_with_interval(self, X, confidence=0.9):
        if not self.is_fitted_:
            raise RuntimeError("Model must be fitted before predict")
        
        point_pred = self.predict(X)
        
        self.quantile_model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(self.device)
            quantile_preds = self.quantile_model(X_tensor).cpu().numpy()
        
        lower_q = max(q for q in self.quantiles if q <= (1 - confidence) / 2)
        upper_q = min(q for q in self.quantiles if q >= 1 - (1 - confidence) / 2)
        
        lower_idx = self.quantiles.index(lower_q)
        upper_idx = self.quantiles.index(upper_q)
        
        lower_pred = quantile_preds[:, :, lower_idx]
        upper_pred = quantile_preds[:, :, upper_idx]
        
        lower_pred = np.minimum(lower_pred, point_pred * 0.5)
        upper_pred = np.maximum(upper_pred, point_pred * 1.5)
        
        quantile_dict = {}
        for i, q in enumerate(self.quantiles):
            quantile_dict[q] = quantile_preds[:, :, i]
        
        return {
            'point': point_pred,
            'lower': lower_pred,
            'upper': upper_pred,
            'confidence': confidence,
            'actual_quantiles': [lower_q, upper_q],
            'quantiles': quantile_dict,
            'coverage_stats': self._coverage_stats
        }

    def _calculate_metrics(self, y_true, y_pred):
        return {
            'mae': mean_absolute_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'r2': r2_score(y_true, y_pred)
        }

    def save(self, path):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'quantile_model_state_dict': self.quantile_model.state_dict(),
            'input_size': self.input_size,
            'output_size': self.output_size,
            'quantiles': self.quantiles,
            'coverage_stats': self._coverage_stats
        }, f'{self.model_dir}/{path}')

    @classmethod
    def load(cls, path, model_dir='models', device=None):
        instance = cls(model_dir=model_dir, device=device)
        checkpoint = torch.load(f'{model_dir}/{path}', map_location=instance.device, weights_only=False)
        
        instance.input_size = checkpoint['input_size']
        instance.output_size = checkpoint['output_size']
        instance.quantiles = checkpoint['quantiles']
        instance._coverage_stats = checkpoint['coverage_stats']
        
        instance.model = LSTMNetwork(
            input_size=instance.input_size,
            hidden_size=64,
            num_layers=2,
            output_size=instance.output_size,
            dropout=0.2
        ).to(instance.device)
        instance.model.load_state_dict(checkpoint['model_state_dict'])
        
        instance.quantile_model = QuantileLSTMNetwork(
            input_size=instance.input_size,
            hidden_size=48,
            num_layers=2,
            quantiles=instance.quantiles,
            dropout=0.15
        ).to(instance.device)
        instance.quantile_model.load_state_dict(checkpoint['quantile_model_state_dict'])
        
        instance.is_fitted_ = True
        
        return instance
