import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping

from data_loader import generate_future_dates


class LSTMPredictor:
    def __init__(self, look_back=30, lstm_units=64, dropout_rate=0.2, 
                 epochs=100, batch_size=16, learning_rate=0.001, 
                 patience=10, verbose=0):
        self.look_back = look_back
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.patience = patience
        self.verbose = verbose
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.history = None
        self.last_known_data = None
    
    def _create_sequences(self, data):
        X, y = [], []
        for i in range(len(data) - self.look_back):
            X.append(data[i:(i + self.look_back), 0])
            y.append(data[i + self.look_back, 0])
        return np.array(X), np.array(y)
    
    def _build_model(self):
        model = Sequential([
            LSTM(units=self.lstm_units, return_sequences=True, 
                 input_shape=(self.look_back, 1)),
            Dropout(self.dropout_rate),
            LSTM(units=self.lstm_units, return_sequences=False),
            Dropout(self.dropout_rate),
            Dense(units=self.lstm_units // 2),
            Dense(units=1)
        ])
        
        optimizer = Adam(learning_rate=self.learning_rate)
        model.compile(optimizer=optimizer, loss='mse')
        
        return model
    
    def fit(self, train_data, validation_split=0.1):
        series = train_data['Close'].values.reshape(-1, 1)
        
        scaled_data = self.scaler.fit_transform(series)
        
        X, y = self._create_sequences(scaled_data)
        
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        if validation_split > 0:
            val_size = int(len(X) * validation_split)
            X_train, X_val = X[:-val_size], X[-val_size:]
            y_train, y_val = y[:-val_size], y[-val_size:]
            
            self.model = self._build_model()
            
            early_stopping = EarlyStopping(
                monitor='val_loss',
                patience=self.patience,
                restore_best_weights=True,
                verbose=self.verbose
            )
            
            self.history = self.model.fit(
                X_train, y_train,
                epochs=self.epochs,
                batch_size=self.batch_size,
                validation_data=(X_val, y_val),
                callbacks=[early_stopping],
                verbose=self.verbose
            )
        else:
            self.model = self._build_model()
            self.history = self.model.fit(
                X, y,
                epochs=self.epochs,
                batch_size=self.batch_size,
                verbose=self.verbose
            )
        
        self.last_known_data = scaled_data[-self.look_back:]
        
        return self
    
    def predict(self, steps=30, last_date=None):
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        predictions = []
        current_sequence = self.last_known_data.copy()
        
        for _ in range(steps):
            pred_scaled = self.model.predict(
                current_sequence.reshape(1, self.look_back, 1),
                verbose=0
            )
            predictions.append(pred_scaled[0, 0])
            
            current_sequence = np.roll(current_sequence, -1)
            current_sequence[-1] = pred_scaled
        
        predictions_scaled = np.array(predictions).reshape(-1, 1)
        predictions_actual = self.scaler.inverse_transform(predictions_scaled)
        
        prediction_std = np.std(predictions_actual) * 1.96
        lower_ci = predictions_actual.flatten() - prediction_std
        upper_ci = predictions_actual.flatten() + prediction_std
        
        if last_date is None:
            raise ValueError("last_date must be provided")
        
        future_dates = generate_future_dates(last_date, periods=steps)
        
        predictions_df = pd.DataFrame({
            'Date': future_dates,
            'Predicted_Close': predictions_actual.flatten(),
            'Lower_CI': lower_ci,
            'Upper_CI': upper_ci
        })
        predictions_df.set_index('Date', inplace=True)
        
        return predictions_df
    
    def get_model_summary(self):
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        summary = {
            'look_back': self.look_back,
            'lstm_units': self.lstm_units,
            'dropout_rate': self.dropout_rate,
            'batch_size': self.batch_size,
            'epochs_trained': len(self.history.history['loss']) if self.history else self.epochs,
            'final_loss': self.history.history['loss'][-1] if self.history else None
        }
        
        if 'val_loss' in self.history.history:
            summary['final_val_loss'] = self.history.history['val_loss'][-1]
        
        return summary
