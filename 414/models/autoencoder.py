import logging
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

try:
    import tensorflow as tf
    _TF_AVAILABLE = True
except ImportError:
    _TF_AVAILABLE = False
    tf = None

from config.config import MODEL_CONFIG, FRAUD_THRESHOLDS
from utils.utils import normalize_features

logger = logging.getLogger(__name__)


class PersonalizedAutoencoder:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or MODEL_CONFIG
        self.base_model = None
        self.scaler: Optional[StandardScaler] = None
        self._global_threshold = FRAUD_THRESHOLDS.get("autoencoder_reconstruction_threshold", 2.5)
        self._history = None
        self._is_trained = False
        self._user_adapters: Dict[str, Dict] = {}
        self._user_buffers: Dict[str, deque] = {}
        self._user_thresholds: Dict[str, float] = {}
        self._user_fine_tune_counts: Dict[str, int] = {}
        self._min_samples_for_finetune = self.config.get("ae_min_user_samples", 10)
        self._max_buffer_size = self.config.get("ae_max_user_buffer", 200)
        self._adapter_hidden_dim = self.config.get("ae_adapter_dim", 4)
        self._finetune_learning_rate = self.config.get("ae_finetune_lr", 0.001)
        self._finetune_epochs = self.config.get("ae_finetune_epochs", 3)

    def _check_tf(self):
        if not _TF_AVAILABLE:
            raise RuntimeError(
                "TensorFlow is not installed. Autoencoder model unavailable. "
                "Install TensorFlow or use Isolation Forest only mode."
            )

    def _build_base_model(self, input_dim: int):
        self._check_tf()
        hidden_dims = self.config.get("ae_hidden_dims", [16, 8, 4])

        inputs = tf.keras.layers.Input(shape=(input_dim,), name="base_input")

        x = inputs
        for i, dim in enumerate(hidden_dims):
            x = tf.keras.layers.Dense(dim, activation="relu", name=f"encoder_dense_{i}")(x)
            x = tf.keras.layers.BatchNormalization(name=f"encoder_bn_{i}")(x)
            x = tf.keras.layers.Dropout(0.1, name=f"encoder_dropout_{i}")(x)

        encoded = x

        decoder_dims = list(reversed(hidden_dims))[1:] + [input_dim]
        y = encoded
        for i, dim in enumerate(decoder_dims):
            activation = "relu" if i < len(decoder_dims) - 1 else "linear"
            y = tf.keras.layers.Dense(dim, activation=activation, name=f"decoder_dense_{i}")(y)
            if i < len(decoder_dims) - 1:
                y = tf.keras.layers.BatchNormalization(name=f"decoder_bn_{i}")(y)

        outputs = y

        model = tf.keras.Model(inputs=inputs, outputs=outputs, name="base_autoencoder")
        learning_rate = self.config.get("ae_learning_rate", 0.001)
        optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
        model.compile(optimizer=optimizer, loss="mse", metrics=["mae"])
        return model

    def _build_user_adapter(self, input_dim: int, base_encoded_dim: int):
        self._check_tf()
        inputs = tf.keras.layers.Input(shape=(input_dim,), name="adapter_input")
        base_features = tf.keras.layers.Input(shape=(base_encoded_dim,), name="base_encoded")

        adapter_down = tf.keras.layers.Dense(
            self._adapter_hidden_dim, activation="relu", name="adapter_down"
        )(base_features)
        adapter_up = tf.keras.layers.Dense(base_encoded_dim, activation="linear", name="adapter_up")(adapter_down)

        residual = tf.keras.layers.Add()([base_features, adapter_up])

        decoder_dims = [max(base_encoded_dim * 2, 8), input_dim]
        y = residual
        for i, dim in enumerate(decoder_dims):
            activation = "relu" if i < len(decoder_dims) - 1 else "linear"
            y = tf.keras.layers.Dense(dim, activation=activation, name=f"user_decoder_{i}")(y)

        outputs = y

        adapter_model = tf.keras.Model(
            inputs=[inputs, base_features], outputs=outputs, name="user_adapter"
        )
        optimizer = tf.keras.optimizers.Adam(learning_rate=self._finetune_learning_rate)
        adapter_model.compile(optimizer=optimizer, loss="mse", metrics=["mae"])
        return adapter_model

    def train_base(self, X: np.ndarray, validation_split: float = 0.1) -> "PersonalizedAutoencoder":
        self._check_tf()
        logger.info("Training base Autoencoder on %d samples with %d features", X.shape[0], X.shape[1])
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        input_dim = X_scaled.shape[1]
        self.base_model = self._build_base_model(input_dim)

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=self.config.get("ae_early_stopping_patience", 5),
                restore_best_weights=True,
                mode="min",
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=3,
                min_lr=1e-7,
            ),
        ]

        self._history = self.base_model.fit(
            X_scaled, X_scaled,
            epochs=self.config.get("ae_epochs", 50),
            batch_size=self.config.get("ae_batch_size", 256),
            validation_split=validation_split,
            callbacks=callbacks,
            shuffle=True,
            verbose=0,
        )

        reconstructions = self.base_model.predict(X_scaled, verbose=0)
        mse = np.mean(np.power(X_scaled - reconstructions, 2), axis=1)
        self._global_threshold = np.percentile(mse, 95)
        self._is_trained = True
        logger.info(
            "Base Autoencoder trained. Global threshold=%.4f, MSE range=[%.4f, %.4f]",
            self._global_threshold, mse.min(), mse.max()
        )
        return self

    def _get_encoded(self, X_scaled: np.ndarray) -> np.ndarray:
        if len(self.base_model.layers) < 6:
            encoded_output = self.base_model.layers[-5].output
        else:
            encoded_output = self.base_model.layers[5].output
        encoder = tf.keras.Model(inputs=self.base_model.input, outputs=encoded_output)
        return encoder.predict(X_scaled, verbose=0)

    def _fine_tune_for_user(self, customer_id: str, X_user: np.ndarray):
        self._check_tf()
        if len(X_user) < self._min_samples_for_finetune:
            return False
        X_scaled = self.scaler.transform(X_user)
        input_dim = X_scaled.shape[1]
        base_encoded = self._get_encoded(X_scaled)
        base_encoded_dim = base_encoded.shape[1]

        if customer_id not in self._user_adapters:
            self._user_adapters[customer_id] = {
                "model": self._build_user_adapter(input_dim, base_encoded_dim),
                "last_updated": None,
                "version": 0,
            }

        adapter = self._user_adapters[customer_id]
        adapter_model = adapter["model"]

        adapter_model.fit(
            [X_scaled, base_encoded], X_scaled,
            epochs=self._finetune_epochs,
            batch_size=min(32, len(X_user)),
            verbose=0,
        )

        reconstructions = adapter_model.predict([X_scaled, base_encoded], verbose=0)
        mse = np.mean(np.power(X_scaled - reconstructions, 2), axis=1)
        self._user_thresholds[customer_id] = np.percentile(mse, 90)
        self._user_fine_tune_counts[customer_id] = self._user_fine_tune_counts.get(customer_id, 0) + 1
        adapter["version"] += 1
        adapter["last_updated"] = None

        logger.info(
            "User %s adapter fine-tuned (v%d). Samples=%d, Threshold=%.4f",
            customer_id, adapter["version"], len(X_user), self._user_thresholds[customer_id]
        )
        return True

    def _update_user_buffer(self, customer_id: str, X_sample: np.ndarray):
        if customer_id not in self._user_buffers:
            self._user_buffers[customer_id] = deque(maxlen=self._max_buffer_size)
        self._user_buffers[customer_id].append(X_sample.flatten())
        buffer = self._user_buffers[customer_id]
        if len(buffer) >= self._min_samples_for_finetune and (
            customer_id not in self._user_adapters
            or len(buffer) % max(self._min_samples_for_finetune, 20) == 0
        ):
            X_user = np.array(buffer)
            self._fine_tune_for_user(customer_id, X_user)

    def reconstruct(self, X: np.ndarray, customer_id: Optional[str] = None) -> np.ndarray:
        if not self._is_trained:
            raise RuntimeError("Autoencoder model not trained")
        X_scaled = normalize_features(X, self.scaler)
        if customer_id and customer_id in self._user_adapters and self._user_adapters[customer_id]["model"]:
            base_encoded = self._get_encoded(X_scaled)
            return self._user_adapters[customer_id]["model"].predict([X_scaled, base_encoded], verbose=0)
        return self.base_model.predict(X_scaled, verbose=0)

    def reconstruction_error(self, X: np.ndarray, customer_id: Optional[str] = None) -> np.ndarray:
        if not self._is_trained:
            raise RuntimeError("Autoencoder model not trained")
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if customer_id:
            self._update_user_buffer(customer_id, X)
        X_scaled = normalize_features(X, self.scaler)
        recon = self.reconstruct(X, customer_id)
        return np.mean(np.power(X_scaled - recon, 2), axis=1)

    def fraud_probability(self, X: np.ndarray, customer_id: Optional[str] = None) -> np.ndarray:
        if not _TF_AVAILABLE or not self._is_trained:
            n = X.shape[0] if X.ndim > 1 else 1
            return np.zeros(n)
        errors = self.reconstruction_error(X, customer_id)
        threshold = self._user_thresholds.get(customer_id, self._global_threshold) if customer_id else self._global_threshold
        probs = 1.0 - np.exp(-errors / threshold)
        return np.clip(probs, 0.0, 1.0)

    def predict(self, X: np.ndarray, customer_id: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        if not _TF_AVAILABLE or not self._is_trained:
            n = X.shape[0] if X.ndim > 1 else 1
            return np.zeros(n, dtype=int), np.zeros(n)
        errors = self.reconstruction_error(X, customer_id)
        threshold = self._user_thresholds.get(customer_id, self._global_threshold) if customer_id else self._global_threshold
        labels = (errors > threshold).astype(int)
        return labels, errors

    def score_for_customer(self, X: np.ndarray, customer_id: str) -> Dict:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        errors = self.reconstruction_error(X, customer_id)
        error = float(errors[0])
        has_adapter = customer_id in self._user_adapters
        threshold = self._user_thresholds.get(customer_id, self._global_threshold)
        prob = float(np.clip(1.0 - np.exp(-error / threshold), 0.0, 1.0))
        return {
            "reconstruction_error": error,
            "threshold": threshold,
            "has_user_adapter": has_adapter,
            "adapter_version": self._user_adapters[customer_id]["version"] if has_adapter else 0,
            "finetune_count": self._user_fine_tune_counts.get(customer_id, 0),
            "buffer_size": len(self._user_buffers.get(customer_id, deque())),
            "probability": prob,
            "is_anomaly": error > threshold,
            "label": 1 if error > threshold else 0,
        }

    def anomaly_score(self, X: np.ndarray) -> np.ndarray:
        return self.reconstruction_error(X)

    @property
    def global_threshold(self) -> float:
        return self._global_threshold

    @property
    def user_adapter_count(self) -> int:
        return len(self._user_adapters)

    def get_user_stats(self, customer_id: str) -> Dict:
        return {
            "threshold": self._user_thresholds.get(customer_id, self._global_threshold),
            "has_adapter": customer_id in self._user_adapters,
            "adapter_version": self._user_adapters[customer_id]["version"] if customer_id in self._user_adapters else 0,
            "finetune_count": self._user_fine_tune_counts.get(customer_id, 0),
            "buffer_size": len(self._user_buffers.get(customer_id, deque())),
        }

    def list_users_with_adapters(self) -> List[Dict]:
        return [
            {
                "customer_id": cid,
                "version": adapter["version"],
                "finetune_count": self._user_fine_tune_counts.get(cid, 0),
                "threshold": self._user_thresholds.get(cid, self._global_threshold),
            }
            for cid, adapter in self._user_adapters.items()
        ]

    def save(self, path: Optional[str] = None) -> bool:
        if not _TF_AVAILABLE:
            logger.warning("TensorFlow not available, cannot save Autoencoder model")
            return False
        path = path or self.config.get("autoencoder_path")
        if not path:
            path = os.path.join("models", "saved", "autoencoder_model")
        try:
            save_dir = os.path.dirname(path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
            self.base_model.save(path)
            user_data = {
                cid: {
                    "threshold": self._user_thresholds.get(cid, self._global_threshold),
                    "finetune_count": self._user_fine_tune_counts.get(cid, 0),
                    "buffer": list(self._user_buffers.get(cid, deque())),
                    "version": adapter["version"],
                }
                for cid, adapter in self._user_adapters.items()
            }
            scaler_path = path + "_scaler.joblib"
            joblib.dump({
                "scaler": self.scaler,
                "global_threshold": self._global_threshold,
                "user_data": user_data,
                "config": self.config,
            }, scaler_path)
            logger.info(
                "Autoencoder base model saved to %s (user adapters: %d)",
                path, len(self._user_adapters)
            )
            return True
        except Exception as e:
            logger.error("Failed to save Autoencoder model: %s", e)
            return False

    def load(self, path: Optional[str] = None) -> bool:
        if not _TF_AVAILABLE:
            logger.warning("TensorFlow not available, cannot load Autoencoder model")
            return False
        path = path or self.config.get("autoencoder_path")
        if not path or not os.path.exists(path):
            logger.warning("Autoencoder model file not found: %s", path)
            return False
        try:
            self.base_model = tf.keras.models.load_model(path, compile=False)
            learning_rate = self.config.get("ae_learning_rate", 0.001)
            self.base_model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
                loss="mse",
                metrics=["mae"],
            )
            scaler_path = path + "_scaler.joblib"
            if os.path.exists(scaler_path):
                data = joblib.load(scaler_path)
                self.scaler = data.get("scaler")
                self._global_threshold = data.get("global_threshold", self._global_threshold)
                user_data = data.get("user_data", {})
                self._user_buffers = {}
                self._user_thresholds = {}
                self._user_fine_tune_counts = {}
                self._user_adapters = {}
                for cid, ud in user_data.items():
                    self._user_thresholds[cid] = ud.get("threshold", self._global_threshold)
                    self._user_fine_tune_counts[cid] = ud.get("finetune_count", 0)
                    self._user_buffers[cid] = deque(ud.get("buffer", []), maxlen=self._max_buffer_size)
                    self._user_adapters[cid] = {
                        "model": None,
                        "version": ud.get("version", 0),
                        "last_updated": None,
                    }
                logger.info("User adapters metadata loaded: %d", len(user_data))
            self._is_trained = True
            logger.info("Autoencoder base model loaded from %s", path)
            return True
        except Exception as e:
            logger.error("Failed to load Autoencoder model: %s", e)
            return False

    def is_trained(self) -> bool:
        return self._is_trained
