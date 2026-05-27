import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (Input, Conv1D, MaxPooling1D, UpSampling1D,
                                     concatenate, BatchNormalization, Activation,
                                     Dropout, Dense, Flatten, Reshape, Add,
                                     GlobalAveragePooling1D, Multiply)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class MultiScaleFeatureExtractor:
    def __init__(self, scales: List[int] = [5, 15, 30, 60]):
        self.scales = scales
    
    def extract_multi_scale_features(self, 
                                      power_series: np.ndarray,
                                      window_size: int = 60) -> np.ndarray:
        n_samples = len(power_series)
        n_windows = n_samples - window_size + 1
        
        features = []
        
        for scale in self.scales:
            if scale > 1:
                smoothed = np.convolve(power_series, np.ones(scale)/scale, mode='same')
            else:
                smoothed = power_series
            
            scale_features = np.zeros((n_windows, window_size))
            for i in range(n_windows):
                scale_features[i] = smoothed[i:i+window_size]
            
            features.append(scale_features)
        
        return np.stack(features, axis=-1)
    
    def extract_statistical_features(self, 
                                      power_series: np.ndarray,
                                      window_size: int = 60) -> np.ndarray:
        n_samples = len(power_series)
        n_windows = n_samples - window_size + 1
        
        stat_features = np.zeros((n_windows, 8))
        
        for i in range(n_windows):
            window = power_series[i:i+window_size]
            
            stat_features[i, 0] = np.mean(window)
            stat_features[i, 1] = np.std(window)
            stat_features[i, 2] = np.max(window)
            stat_features[i, 3] = np.min(window)
            stat_features[i, 4] = np.percentile(window, 25)
            stat_features[i, 5] = np.percentile(window, 75)
            stat_features[i, 6] = np.percentile(window, 75) - np.percentile(window, 25)
            stat_features[i, 7] = np.mean(np.abs(np.diff(window)))
        
        return stat_features
    
    def extract_all_features(self, 
                              power_series: np.ndarray,
                              window_size: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        multi_scale = self.extract_multi_scale_features(power_series, window_size)
        statistical = self.extract_statistical_features(power_series, window_size)
        return multi_scale, statistical


class SqueezeExcitation1D(tf.keras.layers.Layer):
    def __init__(self, ratio: int = 16, **kwargs):
        super(SqueezeExcitation1D, self).__init__(**kwargs)
        self.ratio = ratio
    
    def build(self, input_shape):
        channels = input_shape[-1]
        self.global_avg_pool = GlobalAveragePooling1D()
        self.dense1 = Dense(channels // self.ratio, activation='relu')
        self.dense2 = Dense(channels, activation='sigmoid')
        super(SqueezeExcitation1D, self).build(input_shape)
    
    def call(self, inputs):
        x = self.global_avg_pool(inputs)
        x = self.dense1(x)
        x = self.dense2(x)
        x = tf.expand_dims(x, axis=1)
        return Multiply()([inputs, x])
    
    def get_config(self):
        config = super(SqueezeExcitation1D, self).get_config()
        config.update({'ratio': self.ratio})
        return config


class MultiScaleCNNDisaggregator:
    def __init__(self, 
                 window_size: int = 60,
                 n_appliances: int = 4,
                 appliance_names: Optional[List[str]] = None,
                 scales: List[int] = [5, 15, 30]):
        self.window_size = window_size
        self.n_appliances = n_appliances
        self.appliance_names = appliance_names or [f'appliance_{i}' for i in range(n_appliances)]
        self.scales = scales
        self.n_scales = len(scales)
        self.model = None
        self.is_trained = False
        self.mean = 0.0
        self.std = 1.0
        self.feature_extractor = MultiScaleFeatureExtractor(scales=scales)
    
    def _multi_scale_block(self, x, n_filters: int, kernel_size: int = 3):
        branches = []
        
        for dilation in [1, 2, 4]:
            conv = Conv1D(n_filters, kernel_size, padding='same', 
                          dilation_rate=dilation, activation='relu')(x)
            conv = BatchNormalization()(conv)
            branches.append(conv)
        
        concat = concatenate(branches, axis=-1)
        concat = SqueezeExcitation1D(ratio=8)(concat)
        
        return concat
    
    def build_model(self, 
                    n_filters: int = 32,
                    kernel_size: int = 3,
                    dropout_rate: float = 0.2) -> 'MultiScaleCNNDisaggregator':
        multi_scale_input = Input(shape=(self.window_size, self.n_scales), 
                                  name='multi_scale_input')
        stat_input = Input(shape=(8,), name='statistical_input')
        
        x1 = Conv1D(n_filters, kernel_size, padding='same')(multi_scale_input)
        x1 = BatchNormalization()(x1)
        x1 = Activation('relu')(x1)
        
        x1 = self._multi_scale_block(x1, n_filters)
        pool1 = MaxPooling1D(pool_size=2)(x1)
        pool1 = Dropout(dropout_rate)(pool1)
        
        x2 = self._multi_scale_block(pool1, n_filters * 2)
        pool2 = MaxPooling1D(pool_size=2)(x2)
        pool2 = Dropout(dropout_rate)(pool2)
        
        x3 = self._multi_scale_block(pool2, n_filters * 4)
        
        up2 = UpSampling1D(size=2)(x3)
        up2 = Conv1D(n_filters * 2, kernel_size, padding='same')(up2)
        merge2 = concatenate([x2, up2])
        merge2 = Dropout(dropout_rate)(merge2)
        
        up1 = UpSampling1D(size=2)(merge2)
        up1 = Conv1D(n_filters, kernel_size, padding='same')(up1)
        merge1 = concatenate([x1, up1])
        merge1 = Dropout(dropout_rate)(merge1)
        
        conv_final = Conv1D(n_filters, kernel_size, padding='same', activation='relu')(merge1)
        conv_final = BatchNormalization()(conv_final)
        
        stat_dense = Dense(32, activation='relu')(stat_input)
        stat_dense = BatchNormalization()(stat_dense)
        stat_dense = Dropout(dropout_rate)(stat_dense)
        stat_dense = Dense(n_filters, activation='relu')(stat_dense)
        stat_dense = tf.expand_dims(stat_dense, axis=1)
        stat_dense = tf.tile(stat_dense, [1, self.window_size, 1])
        
        combined = concatenate([conv_final, stat_dense])
        combined = Conv1D(n_filters, 1, activation='relu')(combined)
        
        outputs = Conv1D(self.n_appliances, 1, activation='relu')(combined)
        
        self.model = Model(inputs=[multi_scale_input, stat_input], outputs=outputs)
        return self
    
    def compile(self, 
                learning_rate: float = 0.001,
                loss: str = 'mse') -> 'MultiScaleCNNDisaggregator':
        if self.model is None:
            self.build_model()
        
        optimizer = Adam(learning_rate=learning_rate)
        
        if loss == 'mse':
            self.model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        elif loss == 'mae':
            self.model.compile(optimizer=optimizer, loss='mae', metrics=['mse'])
        else:
            self.model.compile(optimizer=optimizer, loss=loss)
        
        return self
    
    def normalize(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        if fit:
            self.mean = np.mean(X)
            self.std = np.std(X) + 1e-8
        return (X - self.mean) / self.std
    
    def prepare_data(self, power_series: np.ndarray, fit_norm: bool = False):
        multi_scale_features, stat_features = self.feature_extractor.extract_all_features(
            power_series, self.window_size
        )
        
        multi_scale_norm = self.normalize(multi_scale_features, fit=fit_norm)
        
        return [multi_scale_norm, stat_features]
    
    def prepare_targets(self, y: np.ndarray) -> np.ndarray:
        n_samples = len(y)
        y_seq = np.zeros((n_samples, self.window_size, self.n_appliances))
        for i in range(n_samples):
            y_seq[i, -1, :] = y[i]
        return y_seq
    
    def train(self, 
              power_series_train: np.ndarray, 
              targets_train: np.ndarray,
              power_series_val: Optional[np.ndarray] = None,
              targets_val: Optional[np.ndarray] = None,
              batch_size: int = 32,
              epochs: int = 50,
              model_dir: str = 'models') -> Dict:
        
        X_train = self.prepare_data(power_series_train, fit_norm=True)
        y_train_seq = self.prepare_targets(targets_train)
        
        validation_data = None
        if power_series_val is not None and targets_val is not None:
            X_val = self.prepare_data(power_series_val)
            y_val_seq = self.prepare_targets(targets_val)
            validation_data = (X_val, y_val_seq)
        
        os.makedirs(model_dir, exist_ok=True)
        
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6, verbose=1),
            ModelCheckpoint(os.path.join(model_dir, 'multiscale_cnn_best.h5'), 
                           save_best_only=True, verbose=0)
        ]
        
        history = self.model.fit(
            X_train, y_train_seq,
            batch_size=batch_size,
            epochs=epochs,
            validation_data=validation_data,
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        
        return {
            'loss': history.history['loss'],
            'val_loss': history.history.get('val_loss', []),
            'mae': history.history.get('mae', []),
            'val_mae': history.history.get('val_mae', [])
        }
    
    def disaggregate(self, power_series: np.ndarray) -> Dict[str, np.ndarray]:
        if not self.is_trained and self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")
        
        n_samples = len(power_series)
        predictions = np.zeros((n_samples, self.n_appliances))
        
        if n_samples < self.window_size:
            pad_length = self.window_size - n_samples
            power_padded = np.pad(power_series, (pad_length, 0), mode='edge')
            X = self.prepare_data(power_padded)
            pred_seq = self.model.predict(X, verbose=0)
            pred_single = pred_seq[:, -1, :]
            predictions = pred_single[-n_samples:]
        else:
            X = self.prepare_data(power_series)
            pred_seq = self.model.predict(X, verbose=0)
            pred_single = pred_seq[:, -1, :]
            
            for i in range(self.window_size - 1, n_samples):
                predictions[i] = pred_single[i - self.window_size + 1]
            
            for i in range(self.window_size - 1):
                predictions[i] = predictions[self.window_size - 1]
        
        results = {}
        for i, name in enumerate(self.appliance_names):
            results[name] = np.maximum(0, predictions[:, i])
        
        return results
    
    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        model_path = filepath.replace('.h5', '_model.h5')
        self.model.save(model_path)
        
        config = {
            'window_size': self.window_size,
            'n_appliances': self.n_appliances,
            'appliance_names': self.appliance_names,
            'scales': self.scales,
            'mean': float(self.mean),
            'std': float(self.std),
            'is_trained': self.is_trained
        }
        
        import json
        config_path = filepath.replace('.h5', '_config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'MultiScaleCNNDisaggregator':
        import json
        config_path = filepath.replace('.h5', '_config.json')
        model_path = filepath.replace('.h5', '_model.h5')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        instance = cls(
            window_size=config['window_size'],
            n_appliances=config['n_appliances'],
            appliance_names=config['appliance_names'],
            scales=config['scales']
        )
        instance.mean = config['mean']
        instance.std = config['std']
        instance.is_trained = config['is_trained']
        instance.model = load_model(model_path, 
                                    custom_objects={'SqueezeExcitation1D': SqueezeExcitation1D})
        
        return instance


if __name__ == '__main__':
    from data_generator import generate_aggregated_data, split_data
    
    print("Generating training data...")
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    train_df, val_df, test_df = split_data(df)
    
    appliance_names = ['air_conditioner', 'refrigerator', 'washing_machine', 'lighting']
    
    def create_targets(data_df):
        n = len(data_df)
        y = []
        for i in range(n):
            y.append([data_df[f'{app}_power'].values[i] for app in appliance_names])
        return np.array(y)
    
    window_size = 60
    y_train = create_targets(train_df)[window_size-1:]
    y_val = create_targets(val_df)[window_size-1:]
    
    print(f"Training data: {len(train_df)} samples")
    print(f"Target shape: {y_train.shape}")
    
    print("\nBuilding Multi-Scale CNN model...")
    cnn = MultiScaleCNNDisaggregator(
        window_size=window_size,
        n_appliances=4,
        appliance_names=appliance_names,
        scales=[5, 15, 30]
    )
    cnn.build_model(n_filters=16)
    cnn.compile(learning_rate=0.001)
    
    print("Model summary:")
    cnn.model.summary()
    
    print("\nTraining for a few epochs...")
    history = cnn.train(
        train_df['total_power'].values, y_train,
        val_df['total_power'].values, y_val,
        batch_size=32,
        epochs=5
    )
    
    print("\nTesting disaggregation...")
    results = cnn.disaggregate(test_df['total_power'].values[:500])
    
    print("\nPrediction results sample:")
    for app, pred in results.items():
        print(f"{app}: mean={np.mean(pred):.2f}W, std={np.std(pred):.2f}W")
