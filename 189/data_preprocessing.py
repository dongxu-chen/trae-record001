import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from config import Config


class AirQualityDataProcessor:
    def __init__(self):
        self.feature_scaler = StandardScaler()
        self.target_scaler = StandardScaler()
        self.config = Config()

    def calculate_iaqi(self, pollutant, concentration):
        breakpoints = self.config.AQI_BREAKPOINTS.get(pollutant, [])
        for bp_low, bp_high, iaqi_low, iaqi_high in breakpoints:
            if bp_low <= concentration <= bp_high:
                if bp_high == bp_low:
                    return iaqi_low
                iaqi = (iaqi_high - iaqi_low) / (bp_high - bp_low) * (concentration - bp_low) + iaqi_low
                return round(iaqi, 2)
        return 500 if concentration > breakpoints[-1][1] else 0

    def calculate_aqi(self, row):
        pollutants = ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3']
        iaqi_values = [self.calculate_iaqi(p, row[p]) for p in pollutants]
        return max(iaqi_values)

    def load_data(self, file_path):
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        df['AQI'] = df.apply(self.calculate_aqi, axis=1)
        return df

    def handle_missing_data(self, df):
        df = df.copy()
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].interpolate(method='linear')
        df[numeric_cols] = df[numeric_cols].ffill().bfill()
        return df

    def create_sequences(self, data, seq_length, pred_length):
        X, y = [], []
        for i in range(len(data) - seq_length - pred_length + 1):
            X.append(data[i:i + seq_length])
            y.append(data[i + seq_length:i + seq_length + pred_length])
        return np.array(X), np.array(y)

    def preprocess(self, df):
        df = self.handle_missing_data(df)
        features = df[self.config.FEATURE_COLS].values
        targets = df[self.config.TARGET_COLS].values

        features_scaled = self.feature_scaler.fit_transform(features)
        targets_scaled = self.target_scaler.fit_transform(targets)

        combined = np.concatenate([features_scaled, targets_scaled], axis=1)

        X, y = self.create_sequences(
            combined,
            self.config.SEQUENCE_LENGTH,
            self.config.PREDICTION_LENGTH
        )

        y = y[:, :, -len(self.config.TARGET_COLS):]

        train_size = int(len(X) * (1 - self.config.TEST_SPLIT - self.config.VALIDATION_SPLIT))
        val_size = int(len(X) * (1 - self.config.TEST_SPLIT))

        X_train, X_val, X_test = X[:train_size], X[train_size:val_size], X[val_size:]
        y_train, y_val, y_test = y[:train_size], y[train_size:val_size], y[val_size:]

        return {
            'X_train': X_train, 'y_train': y_train,
            'X_val': X_val, 'y_val': y_val,
            'X_test': X_test, 'y_test': y_test,
            'feature_scaler': self.feature_scaler,
            'target_scaler': self.target_scaler,
            'df': df
        }

    def prepare_prediction_data(self, df):
        df = self.handle_missing_data(df)
        features = df[self.config.FEATURE_COLS].values
        targets = df[self.config.TARGET_COLS].values

        features_scaled = self.feature_scaler.transform(features)
        targets_scaled = self.target_scaler.transform(targets)

        combined = np.concatenate([features_scaled, targets_scaled], axis=1)
        return combined[-self.config.SEQUENCE_LENGTH:][np.newaxis, :, :]
