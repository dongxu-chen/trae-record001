import numpy as np
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (Input, Conv1D, MaxPooling1D, UpSampling1D,
                                     concatenate, BatchNormalization, Activation,
                                     Dropout, Dense, Flatten, Reshape)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class CNNDisaggregator:
    def __init__(self, 
                 window_size: int = 60,
                 n_appliances: int = 4,
                 appliance_names: Optional[List[str]] = None):
        self.window_size = window_size
        self.n_appliances = n_appliances
        self.appliance_names = appliance_names or [f'appliance_{i}' for i in range(n_appliances)]
        self.model = None
        self.is_trained = False
        self.mean = 0.0
        self.std = 1.0
    
    def build_unet_model(self, 
                         n_filters: int = 32,
                         kernel_size: int = 3,
                         dropout_rate: float = 0.2) -> 'CNNDisaggregator':
        inputs = Input(shape=(self.window_size, 1))
        
        conv1 = Conv1D(n_filters, kernel_size, padding='same')(inputs)
        conv1 = BatchNormalization()(conv1)
        conv1 = Activation('relu')(conv1)
        conv1 = Conv1D(n_filters, kernel_size, padding='same')(conv1)
        conv1 = BatchNormalization()(conv1)
        conv1 = Activation('relu')(conv1)
        pool1 = MaxPooling1D(pool_size=2)(conv1)
        pool1 = Dropout(dropout_rate)(pool1)
        
        conv2 = Conv1D(n_filters * 2, kernel_size, padding='same')(pool1)
        conv2 = BatchNormalization()(conv2)
        conv2 = Activation('relu')(conv2)
        conv2 = Conv1D(n_filters * 2, kernel_size, padding='same')(conv2)
        conv2 = BatchNormalization()(conv2)
        conv2 = Activation('relu')(conv2)
        pool2 = MaxPooling1D(pool_size=2)(conv2)
        pool2 = Dropout(dropout_rate)(pool2)
        
        conv3 = Conv1D(n_filters * 4, kernel_size, padding='same')(pool2)
        conv3 = BatchNormalization()(conv3)
        conv3 = Activation('relu')(conv3)
        conv3 = Conv1D(n_filters * 4, kernel_size, padding='same')(conv3)
        conv3 = BatchNormalization()(conv3)
        conv3 = Activation('relu')(conv3)
        pool3 = MaxPooling1D(pool_size=2)(conv3)
        pool3 = Dropout(dropout_rate)(pool3)
        
        convm = Conv1D(n_filters * 8, kernel_size, padding='same')(pool3)
        convm = BatchNormalization()(convm)
        convm = Activation('relu')(convm)
        convm = Conv1D(n_filters * 8, kernel_size, padding='same')(convm)
        convm = BatchNormalization()(convm)
        convm = Activation('relu')(convm)
        
        up3 = UpSampling1D(size=2)(convm)
        up3 = Conv1D(n_filters * 4, kernel_size, padding='same')(up3)
        merge3 = concatenate([conv3, up3])
        merge3 = Dropout(dropout_rate)(merge3)
        convu3 = Conv1D(n_filters * 4, kernel_size, padding='same')(merge3)
        convu3 = BatchNormalization()(convu3)
        convu3 = Activation('relu')(convu3)
        convu3 = Conv1D(n_filters * 4, kernel_size, padding='same')(convu3)
        convu3 = BatchNormalization()(convu3)
        convu3 = Activation('relu')(convu3)
        
        up2 = UpSampling1D(size=2)(convu3)
        up2 = Conv1D(n_filters * 2, kernel_size, padding='same')(up2)
        merge2 = concatenate([conv2, up2])
        merge2 = Dropout(dropout_rate)(merge2)
        convu2 = Conv1D(n_filters * 2, kernel_size, padding='same')(merge2)
        convu2 = BatchNormalization()(convu2)
        convu2 = Activation('relu')(convu2)
        convu2 = Conv1D(n_filters * 2, kernel_size, padding='same')(convu2)
        convu2 = BatchNormalization()(convu2)
        convu2 = Activation('relu')(convu2)
        
        up1 = UpSampling1D(size=2)(convu2)
        up1 = Conv1D(n_filters, kernel_size, padding='same')(up1)
        merge1 = concatenate([conv1, up1])
        merge1 = Dropout(dropout_rate)(merge1)
        convu1 = Conv1D(n_filters, kernel_size, padding='same')(merge1)
        convu1 = BatchNormalization()(convu1)
        convu1 = Activation('relu')(convu1)
        convu1 = Conv1D(n_filters, kernel_size, padding='same')(convu1)
        convu1 = BatchNormalization()(convu1)
        convu1 = Activation('relu')(convu1)
        
        outputs = Conv1D(self.n_appliances, 1, activation='relu')(convu1)
        
        self.model = Model(inputs=inputs, outputs=outputs)
        return self
    
    def build_dense_model(self, 
                          n_filters: int = 64,
                          dropout_rate: float = 0.3) -> 'CNNDisaggregator':
        inputs = Input(shape=(self.window_size, 1))
        
        x = Conv1D(n_filters, 5, padding='same', activation='relu')(inputs)
        x = BatchNormalization()(x)
        x = Conv1D(n_filters, 5, padding='same', activation='relu')(x)
        x = BatchNormalization()(x)
        x = MaxPooling1D(2)(x)
        
        x = Conv1D(n_filters * 2, 3, padding='same', activation='relu')(x)
        x = BatchNormalization()(x)
        x = Conv1D(n_filters * 2, 3, padding='same', activation='relu')(x)
        x = BatchNormalization()(x)
        x = MaxPooling1D(2)(x)
        
        x = Flatten()(x)
        x = Dense(512, activation='relu')(x)
        x = Dropout(dropout_rate)(x)
        x = Dense(256, activation='relu')(x)
        x = Dropout(dropout_rate)(x)
        
        outputs = Dense(self.n_appliances * self.window_size, activation='relu')(x)
        outputs = Reshape((self.window_size, self.n_appliances))(outputs)
        
        self.model = Model(inputs=inputs, outputs=outputs)
        return self
    
    def compile(self, 
                learning_rate: float = 0.001,
                loss: str = 'mse') -> 'CNNDisaggregator':
        if self.model is None:
            self.build_unet_model()
        
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
    
    def denormalize(self, X: np.ndarray) -> np.ndarray:
        return X * self.std + self.mean
    
    def prepare_targets(self, y: np.ndarray) -> np.ndarray:
        n_samples = len(y)
        y_seq = np.zeros((n_samples, self.window_size, self.n_appliances))
        for i in range(n_samples):
            y_seq[i, -1, :] = y[i]
        return y_seq
    
    def train(self, 
              X_train: np.ndarray, 
              y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None,
              y_val: Optional[np.ndarray] = None,
              batch_size: int = 32,
              epochs: int = 50,
              model_dir: str = 'models') -> Dict:
        
        X_train_norm = self.normalize(X_train, fit=True)
        X_train_norm = np.expand_dims(X_train_norm, axis=-1)
        
        y_train_seq = self.prepare_targets(y_train)
        
        validation_data = None
        if X_val is not None and y_val is not None:
            X_val_norm = self.normalize(X_val)
            X_val_norm = np.expand_dims(X_val_norm, axis=-1)
            y_val_seq = self.prepare_targets(y_val)
            validation_data = (X_val_norm, y_val_seq)
        
        os.makedirs(model_dir, exist_ok=True)
        
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True, verbose=1),
            ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-6, verbose=1),
            ModelCheckpoint(os.path.join(model_dir, 'cnn_best.h5'), 
                           save_best_only=True, verbose=0)
        ]
        
        history = self.model.fit(
            X_train_norm, y_train_seq,
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
    
    def disaggregate(self, aggregated_power: np.ndarray) -> Dict[str, np.ndarray]:
        if not self.is_trained and self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")
        
        n_samples = len(aggregated_power)
        predictions = np.zeros((n_samples, self.n_appliances))
        
        X = []
        indices = []
        for i in range(self.window_size - 1, n_samples):
            window = aggregated_power[i - self.window_size + 1:i + 1]
            X.append(window)
            indices.append(i)
        
        X = np.array(X)
        X_norm = self.normalize(X)
        X_norm = np.expand_dims(X_norm, axis=-1)
        
        pred_seq = self.model.predict(X_norm, verbose=0)
        pred_single = pred_seq[:, -1, :]
        
        for idx, i in enumerate(indices):
            predictions[i] = pred_single[idx]
        
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
            'mean': float(self.mean),
            'std': float(self.std),
            'is_trained': self.is_trained
        }
        
        import json
        config_path = filepath.replace('.h5', '_config.json')
        with open(config_path, 'w') as f:
            json.dump(config, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'CNNDisaggregator':
        import json
        config_path = filepath.replace('.h5', '_config.json')
        model_path = filepath.replace('.h5', '_model.h5')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        instance = cls(
            window_size=config['window_size'],
            n_appliances=config['n_appliances'],
            appliance_names=config['appliance_names']
        )
        instance.mean = config['mean']
        instance.std = config['std']
        instance.is_trained = config['is_trained']
        instance.model = load_model(model_path)
        
        return instance


if __name__ == '__main__':
    from data_generator import generate_aggregated_data, split_data
    
    print("Generating training data...")
    df = generate_aggregated_data(days=7, sample_interval_min=5)
    train_df, val_df, test_df = split_data(df)
    
    appliance_names = ['air_conditioner', 'refrigerator', 'washing_machine', 'lighting']
    
    def create_windows(df, window_size=60):
        n = len(df)
        X = []
        y = []
        for i in range(window_size - 1, n):
            X.append(df['total_power'].values[i - window_size + 1:i + 1])
            y.append([df[f'{app}_power'].values[i] for app in appliance_names])
        return np.array(X), np.array(y)
    
    window_size = 60
    X_train, y_train = create_windows(train_df, window_size)
    X_val, y_val = create_windows(val_df, window_size)
    
    print(f"Training data shape: X={X_train.shape}, y={y_train.shape}")
    
    print("\nBuilding and training CNN model...")
    cnn = CNNDisaggregator(window_size=window_size, n_appliances=4, appliance_names=appliance_names)
    cnn.build_unet_model()
    cnn.compile(learning_rate=0.001)
    
    print("Model summary:")
    cnn.model.summary()
    
    print("\nTraining for a few epochs...")
    history = cnn.train(
        X_train[:1000], y_train[:1000],
        X_val[:200], y_val[:200],
        batch_size=16,
        epochs=5
    )
    
    print("\nTesting disaggregation...")
    X_test, y_test = create_windows(test_df.iloc[:1000], window_size)
    results = cnn.disaggregate(test_df['total_power'].values[:1000])
    
    print("\nPrediction results sample:")
    for app, pred in results.items():
        print(f"{app}: mean={np.mean(pred):.2f}W, std={np.std(pred):.2f}W")
