import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from .data_processing import DataProcessor
from .prophet_features import ProphetFeatureExtractor
from .autoencoder import AutoencoderTrainer


class AnomalyDetector:
    def __init__(self, seq_length=30, hidden_dims=[64, 32], latent_dim=16,
                 use_dynamic_threshold=True, threshold_window=30,
                 base_percentile=95, volatility_scale=1.5):
        self.seq_length = seq_length
        self.hidden_dims = hidden_dims
        self.latent_dim = latent_dim
        self.scaler = StandardScaler()
        self.prophet_extractor = ProphetFeatureExtractor()
        self.autoencoder = None

        self.use_dynamic_threshold = use_dynamic_threshold
        self.threshold_window = threshold_window
        self.base_percentile = base_percentile
        self.volatility_scale = volatility_scale
        self.threshold = None
        self.dynamic_thresholds = None
        self.historical_recon_errors = None

        self.anomaly_scores = None
        self.user_feedback = pd.DataFrame(
            columns=['ds', 'is_anomaly', 'confidence', 'feedback_time']
        )
        self.last_training_time = None
        self.training_history = []

        self.timestamp_gaps = None

    def fit(self, df, epochs=100, batch_size=32, verbose=True):
        df = DataProcessor.preprocess_data(df)

        prophet_features = self.prophet_extractor.extract_features(df)

        features = self._combine_features(df, prophet_features)

        scaled_features = self.scaler.fit_transform(features)

        sequences = DataProcessor.create_sequences(scaled_features, self.seq_length)
        sequences_flat = sequences.reshape(sequences.shape[0], -1)

        input_dim = sequences_flat.shape[1]
        self.autoencoder = AutoencoderTrainer(
            input_dim=input_dim,
            hidden_dims=self.hidden_dims,
            latent_dim=self.latent_dim
        )

        losses = self.autoencoder.train(
            sequences_flat,
            epochs=epochs,
            batch_size=batch_size,
            verbose=verbose
        )

        recon_errors = self.autoencoder.get_reconstruction_errors(sequences_flat)
        self.historical_recon_errors = recon_errors

        self.threshold = np.percentile(recon_errors, self.base_percentile)

        self.last_training_time = pd.Timestamp.now()
        self.training_history.append({
            'time': self.last_training_time,
            'epochs': epochs,
            'samples': len(df),
            'final_loss': losses[-1] if losses else None
        })

        return losses

    def incremental_fit(self, df, feedback_weight=2.0, epochs=30, batch_size=16, verbose=True):
        if self.autoencoder is None:
            return self.fit(df, epochs=epochs, batch_size=batch_size, verbose=verbose)

        df = DataProcessor.preprocess_data(df)

        prophet_features = self.prophet_extractor.extract_features(df)
        features = self._combine_features(df, prophet_features)
        scaled_features = self.scaler.transform(features)
        sequences = DataProcessor.create_sequences(scaled_features, self.seq_length)
        sequences_flat = sequences.reshape(sequences.shape[0], -1)

        sample_weights = np.ones(len(sequences_flat))
        if len(self.user_feedback) > 0:
            for idx, fb in self.user_feedback.iterrows():
                fb_idx = np.searchsorted(df['ds'].values, fb['ds'])
                seq_idx = fb_idx - self.seq_length + 1
                if 0 <= seq_idx < len(sample_weights):
                    window_start = max(0, seq_idx - 2)
                    window_end = min(len(sample_weights), seq_idx + 3)
                    sample_weights[window_start:window_end] *= feedback_weight

        self.autoencoder.model.train()
        data_tensor = torch.FloatTensor(sequences_flat)
        weights_tensor = torch.FloatTensor(sample_weights)

        dataset = TensorDataset(data_tensor, weights_tensor)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = optim.Adam(self.autoencoder.model.parameters(), lr=1e-4)
        criterion = nn.MSELoss(reduction='none')

        losses = []
        for epoch in range(epochs):
            epoch_loss = 0
            for batch_data, batch_weights in dataloader:
                batch_data = batch_data.to(self.autoencoder.device)
                batch_weights = batch_weights.to(self.autoencoder.device)

                optimizer.zero_grad()
                x_recon, _ = self.autoencoder.model(batch_data)
                loss = criterion(x_recon, batch_data)
                weighted_loss = (loss.mean(dim=1) * batch_weights).mean()
                weighted_loss.backward()
                optimizer.step()

                epoch_loss += weighted_loss.item()

            avg_loss = epoch_loss / len(dataloader)
            losses.append(avg_loss)

            if verbose and (epoch + 1) % 10 == 0:
                print(f'Incremental Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.6f}')

        recon_errors = self.autoencoder.get_reconstruction_errors(sequences_flat)
        if self.historical_recon_errors is not None:
            self.historical_recon_errors = np.concatenate([
                self.historical_recon_errors[-1000:],
                recon_errors
            ])
        else:
            self.historical_recon_errors = recon_errors

        self.last_training_time = pd.Timestamp.now()
        self.training_history.append({
            'time': self.last_training_time,
            'epochs': epochs,
            'samples': len(df),
            'type': 'incremental',
            'feedback_count': len(self.user_feedback),
            'final_loss': losses[-1] if losses else None
        })

        return losses

    def check_timestamp_continuity(self, df, expected_freq='D', gap_threshold=1):
        df_sorted = df.sort_values('ds').reset_index(drop=True)
        time_diff = df_sorted['ds'].diff()

        if expected_freq == 'D':
            expected_delta = pd.Timedelta(days=1)
        elif expected_freq == 'H':
            expected_delta = pd.Timedelta(hours=1)
        else:
            expected_delta = pd.Timedelta(expected_freq)

        gaps = time_diff > (expected_delta * gap_threshold)
        gap_indices = gaps[gaps].index

        gap_info = []
        for idx in gap_indices:
            if idx > 0:
                gap_info.append({
                    'gap_start': df_sorted['ds'].iloc[idx - 1],
                    'gap_end': df_sorted['ds'].iloc[idx],
                    'gap_duration': time_diff.iloc[idx],
                    'gap_days': time_diff.iloc[idx].total_seconds() / 86400
                })

        self.timestamp_gaps = gap_info
        return gap_info

    def detect_anomalies(self, df, expected_freq='D'):
        df = DataProcessor.preprocess_data(df)

        gap_info = self.check_timestamp_continuity(df, expected_freq=expected_freq)

        prophet_features = self.prophet_extractor.extract_features(df)

        features = self._combine_features(df, prophet_features)

        scaled_features = self.scaler.transform(features)

        sequences = DataProcessor.create_sequences(scaled_features, self.seq_length)
        sequences_flat = sequences.reshape(sequences.shape[0], -1)

        recon_errors = self.autoencoder.get_reconstruction_errors(sequences_flat)

        prophet_scores = self.prophet_extractor.get_anomaly_scores_from_prophet(df)

        aligned_prophet_scores = prophet_scores[self.seq_length - 1:]

        combined_scores = self._combine_scores(recon_errors, aligned_prophet_scores)

        self.anomaly_scores = self._align_scores_to_df(df, combined_scores)

        if self.use_dynamic_threshold:
            self.dynamic_thresholds = self._compute_dynamic_threshold(
                recon_errors, df, len(df) - len(combined_scores)
            )
            anomalies = self.anomaly_scores > self.dynamic_thresholds
        else:
            anomalies = self.anomaly_scores > self.threshold

        result_df = df.copy()
        result_df['anomaly_score'] = self.anomaly_scores
        if self.use_dynamic_threshold:
            result_df['dynamic_threshold'] = self.dynamic_thresholds
        result_df['is_anomaly'] = anomalies
        result_df['anomaly_type'] = self._classify_anomaly_type(result_df, gap_info)

        result_df['is_timestamp_gap'] = False
        for gap in gap_info:
            gap_end_idx = result_df[result_df['ds'] == gap['gap_end']].index
            if len(gap_end_idx) > 0:
                result_df.loc[gap_end_idx[0], 'is_timestamp_gap'] = True
                result_df.loc[gap_end_idx[0], 'anomaly_type'] = 'timestamp_gap'
                result_df.loc[gap_end_idx[0], 'is_anomaly'] = True

        return result_df

    def _compute_dynamic_threshold(self, recon_errors, df, pad_length):
        full_errors = np.zeros(len(df))
        full_errors[:pad_length] = np.nan
        full_errors[pad_length:] = recon_errors

        volatility = pd.Series(full_errors).rolling(
            window=self.threshold_window, min_periods=5
        ).std().values

        volatility = np.nan_to_num(volatility, nan=np.nanstd(recon_errors))

        base_threshold = np.percentile(
            self.historical_recon_errors if self.historical_recon_errors is not None else recon_errors,
            self.base_percentile
        )

        vol_factor = 1 + (volatility / (np.nanmean(volatility) + 1e-8) - 1) * self.volatility_scale
        dynamic_thresh = base_threshold * vol_factor

        dynamic_thresh[:pad_length] = base_threshold

        return dynamic_thresh

    def _combine_features(self, df, prophet_features):
        features = pd.DataFrame()
        features['value'] = df['y'].values
        features['value_diff'] = df['y'].diff().fillna(0).values
        features['value_pct_change'] = df['y'].pct_change().fillna(0).values
        features['rolling_mean_7'] = df['y'].rolling(7, min_periods=1).mean().values
        features['rolling_std_7'] = df['y'].rolling(7, min_periods=1).std().fillna(0).values
        features['rolling_mean_14'] = df['y'].rolling(14, min_periods=1).mean().values
        features['rolling_std_14'] = df['y'].rolling(14, min_periods=1).std().fillna(0).values

        for col in prophet_features.columns:
            features[col] = prophet_features[col].values

        features = features.fillna(0)

        return features.values

    def _combine_scores(self, recon_scores, prophet_scores):
        recon_normalized = (recon_scores - np.mean(recon_scores)) / (np.std(recon_scores) + 1e-8)
        prophet_normalized = (prophet_scores - np.mean(prophet_scores)) / (np.std(prophet_scores) + 1e-8)

        combined = 0.6 * recon_normalized + 0.4 * prophet_normalized
        return combined

    def _align_scores_to_df(self, df, scores):
        full_scores = np.zeros(len(df))
        full_scores[:self.seq_length - 1] = 0
        full_scores[self.seq_length - 1:] = scores
        return full_scores

    def _classify_anomaly_type(self, df, gap_info=None):
        anomaly_types = ['normal'] * len(df)

        for i in range(len(df)):
            if not df['is_anomaly'].iloc[i]:
                continue

            pct_change = 0
            if i > 0:
                pct_change = (df['y'].iloc[i] - df['y'].iloc[i - 1]) / (df['y'].iloc[i - 1] + 1e-8)

            if pct_change < -0.05:
                anomaly_types[i] = 'flash_crash'
            elif abs(pct_change) > 0.03:
                anomaly_types[i] = 'volatility_spike'
            elif pd.isna(df['y'].iloc[i]):
                anomaly_types[i] = 'missing_data'
            else:
                anomaly_types[i] = 'anomaly'

        return anomaly_types

    def update_base_threshold(self, percentile):
        if self.historical_recon_errors is not None:
            self.threshold = np.percentile(self.historical_recon_errors, percentile)
            self.base_percentile = percentile

    def add_user_feedback(self, timestamp, is_anomaly, confidence=1.0):
        new_feedback = pd.DataFrame({
            'ds': [pd.to_datetime(timestamp)],
            'is_anomaly': [is_anomaly],
            'confidence': [confidence],
            'feedback_time': [pd.Timestamp.now()]
        })
        self.user_feedback = pd.concat([self.user_feedback, new_feedback], ignore_index=True)

    def retrain_with_feedback(self, df, epochs=50, batch_size=32, feedback_weight=2.0):
        if len(self.user_feedback) == 0:
            return None

        return self.incremental_fit(
            df,
            feedback_weight=feedback_weight,
            epochs=epochs,
            batch_size=batch_size,
            verbose=False
        )

    def get_anomaly_intervals(self, df, min_duration=1):
        result_df = self.detect_anomalies(df)
        anomalies = result_df[result_df['is_anomaly']]

        if len(anomalies) == 0:
            return []

        intervals = []
        start_idx = None

        for i in range(len(result_df)):
            if result_df['is_anomaly'].iloc[i] and start_idx is None:
                start_idx = i
            elif not result_df['is_anomaly'].iloc[i] and start_idx is not None:
                if i - start_idx >= min_duration:
                    intervals.append({
                        'start': result_df['ds'].iloc[start_idx],
                        'end': result_df['ds'].iloc[i - 1],
                        'duration': i - start_idx,
                        'max_score': result_df['anomaly_score'].iloc[start_idx:i].max(),
                        'type': result_df['anomaly_type'].iloc[start_idx:i].value_counts().index[0]
                    })
                start_idx = None

        if start_idx is not None:
            intervals.append({
                'start': result_df['ds'].iloc[start_idx],
                'end': result_df['ds'].iloc[-1],
                'duration': len(result_df) - start_idx,
                'max_score': result_df['anomaly_score'].iloc[start_idx:].max(),
                'type': result_df['anomaly_type'].iloc[start_idx:].value_counts().index[0]
            })

        return intervals

    def get_model_status(self):
        return {
            'is_trained': self.autoencoder is not None and self.autoencoder.is_trained,
            'last_training_time': self.last_training_time,
            'training_count': len(self.training_history),
            'feedback_count': len(self.user_feedback),
            'base_threshold': self.threshold,
            'use_dynamic_threshold': self.use_dynamic_threshold,
            'historical_errors_count': len(self.historical_recon_errors) if self.historical_recon_errors is not None else 0
        }
