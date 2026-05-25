import tensorflow as tf
from tensorflow.keras import layers, Model
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import deque
import threading
import pickle
import os

from config import config
from .deepfm import DeepFMModel

logger = logging.getLogger(__name__)


class OnlineDataBuffer:
    def __init__(self, max_size: int = 100000, min_size_for_training: int = 100):
        self.max_size = max_size
        self.min_size_for_training = min_size_for_training
        self.buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def add_sample(self, features: Dict, label: float, timestamp: Optional[datetime] = None):
        timestamp = timestamp or datetime.now()
        with self._lock:
            self.buffer.append({
                'features': features,
                'label': label,
                'timestamp': timestamp
            })

    def add_batch(self, features_list: List[Dict], labels: List[float]):
        timestamp = datetime.now()
        with self._lock:
            for feat, label in zip(features_list, labels):
                self.buffer.append({
                    'features': feat,
                    'label': label,
                    'timestamp': timestamp
                })

    def get_recent_samples(self, n: int, time_window_hours: Optional[float] = None) -> List[Dict]:
        with self._lock:
            samples = list(self.buffer)

        if time_window_hours is not None:
            cutoff = datetime.now() - timedelta(hours=time_window_hours)
            samples = [s for s in samples if s['timestamp'] >= cutoff]

        return samples[-n:]

    def should_train(self) -> bool:
        return len(self.buffer) >= self.min_size_for_training

    def clear_old_samples(self, older_than_hours: float = 24 * 7):
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        with self._lock:
            original_size = len(self.buffer)
            self.buffer = deque(
                [s for s in self.buffer if s['timestamp'] >= cutoff],
                maxlen=self.max_size
            )
            removed = original_size - len(self.buffer)
            if removed > 0:
                logger.info(f"Cleared {removed} old samples from buffer")

    def __len__(self) -> int:
        return len(self.buffer)


class ElasticWeightConsolidation:
    def __init__(self, lambda_ewc: float = 1000.0):
        self.lambda_ewc = lambda_ewc
        self.fisher_matrix = None
        self.optimal_weights = None

    def compute_fisher_matrix(
        self,
        model: Model,
        dataset: tf.data.Dataset,
        num_samples: int = 1000
    ):
        logger.info("Computing Fisher information matrix...")
        self.optimal_weights = [w.numpy() for w in model.trainable_weights]

        fisher_matrix = [np.zeros_like(w) for w in model.trainable_weights]
        sample_count = 0

        for batch in dataset.take(num_samples):
            features, labels = batch
            with tf.GradientTape(persistent=True) as tape:
                predictions = model(features, training=True)
                predictions = tf.clip_by_value(predictions, 1e-7, 1 - 1e-7)
                log_likelihood = tf.math.log(predictions)

            gradients = tape.gradient(log_likelihood, model.trainable_weights)

            for i, grad in enumerate(gradients):
                if grad is not None:
                    fisher_matrix[i] += np.square(grad.numpy())

            sample_count += 1
            if sample_count >= num_samples:
                break

        for i in range(len(fisher_matrix)):
            fisher_matrix[i] /= max(1, sample_count)

        self.fisher_matrix = fisher_matrix
        logger.info("Fisher matrix computation complete")
        return fisher_matrix

    def ewc_loss(self, current_weights: List[tf.Tensor]) -> tf.Tensor:
        if self.fisher_matrix is None or self.optimal_weights is None:
            return tf.constant(0.0)

        penalty = 0.0
        for i, (w_opt, f_i, w_cur) in enumerate(zip(self.optimal_weights, self.fisher_matrix, current_weights)):
            if w_opt.shape == w_cur.shape:
                penalty += tf.reduce_sum(f_i * tf.square(w_cur - w_opt))

        return 0.5 * self.lambda_ewc * penalty

    def save(self, path: str):
        with open(path, 'wb') as f:
            pickle.dump({
                'fisher_matrix': self.fisher_matrix,
                'optimal_weights': self.optimal_weights,
                'lambda_ewc': self.lambda_ewc
            }, f)

    def load(self, path: str):
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.fisher_matrix = data['fisher_matrix']
            self.optimal_weights = data['optimal_weights']
            self.lambda_ewc = data['lambda_ewc']


class ModelEnsemble:
    def __init__(self, models: List[Tuple[str, DeepFMModel]], weights: Optional[List[float]] = None):
        self.models = {name: model for name, model in models}
        self.weights = weights or [1.0 / len(models)] * len(models)
        self._validate_weights()

    def _validate_weights(self):
        if abs(sum(self.weights) - 1.0) > 1e-6:
            total = sum(self.weights)
            self.weights = [w / total for w in self.weights]
            logger.warning(f"Weights normalized to sum to 1.0: {self.weights}")

    def predict(
        self,
        features: Dict[str, tf.Tensor],
        model_names: Optional[List[str]] = None
    ) -> tf.Tensor:
        model_names = model_names or list(self.models.keys())
        predictions = []

        for name, weight in zip(model_names, self.weights):
            if name not in self.models:
                continue
            pred = self.models[name].predict(features)
            predictions.append(weight * pred)

        if not predictions:
            raise ValueError("No valid models for prediction")

        return tf.add_n(predictions)

    def update_weights(self, weights: Dict[str, float]):
        names = list(self.models.keys())
        self.weights = [weights.get(name, 0.0) for name in names]
        self._validate_weights()


class OnlineLearningManager:
    def __init__(
        self,
        offline_model: DeepFMModel,
        buffer_max_size: int = 100000,
        min_samples_for_train: int = 100,
        online_learning_rate: float = 0.0001,
        ewc_lambda: float = 100.0,
        use_elastic_learning: bool = True,
        use_ewc: bool = False,
        fusion_alpha: float = 0.7
    ):
        self.offline_model = offline_model
        self.online_model = self._clone_model(offline_model)
        self.buffer = OnlineDataBuffer(
            max_size=buffer_max_size,
            min_size_for_training=min_samples_for_train
        )

        self.online_learning_rate = online_learning_rate
        self.ewc_lambda = ewc_lambda
        self.use_elastic_learning = use_elastic_learning
        self.use_ewc = use_ewc
        self.fusion_alpha = fusion_alpha

        self.ewc = ElasticWeightConsolidation(lambda_ewc=ewc_lambda) if use_ewc else None
        self.last_train_time = None
        self.train_count = 0
        self._lock = threading.Lock()

        if use_elastic_learning:
            self.online_model.enable_elastic_learning(alpha=fusion_alpha, beta=1.0 - fusion_alpha)

        self.ensemble = ModelEnsemble(
            models=[('offline', offline_model), ('online', self.online_model)],
            weights=[1.0 - fusion_alpha, fusion_alpha]
        )

    def _clone_model(self, source_model: DeepFMModel) -> DeepFMModel:
        logger.info("Cloning offline model for online learning...")

        new_model = DeepFMModel(
            num_users=source_model.num_users,
            num_news=source_model.num_news,
            num_categories=source_model.num_categories,
            embedding_dim=source_model.embedding_dim,
            dnn_hidden_units=source_model.dnn_hidden_units,
            learning_rate=self.online_learning_rate,
            max_sequence_length=source_model.max_sequence_length,
            use_time_decay=source_model.use_time_decay,
            use_news_age_decay=source_model.use_news_age_decay,
            use_elastic_learning=True
        )

        new_model.model.set_weights(source_model.model.get_weights())

        logger.info("Model cloning complete")
        return new_model

    def compute_fisher_from_offline(self, dataset: tf.data.Dataset, num_samples: int = 1000):
        if self.ewc is not None:
            self.ewc.compute_fisher_matrix(self.offline_model.model, dataset, num_samples)

    def add_feedback(
        self,
        user_id: int,
        news_id: int,
        category_id: int,
        behavior_sequence: List[int],
        behavior_timestamps: List[datetime],
        news_publish_times: List[datetime],
        candidate_publish_time: datetime,
        label: float,
        current_time: Optional[datetime] = None
    ):
        current_time = current_time or datetime.now()

        features = self.online_model.prepare_features(
            user_ids=[user_id],
            news_ids=[news_id],
            category_ids=[category_id],
            behavior_sequences=[behavior_sequence],
            behavior_timestamps=[behavior_timestamps],
            news_publish_times=[news_publish_times],
            candidate_publish_times=[candidate_publish_time],
            current_time=current_time
        )

        self.buffer.add_sample(features, label, current_time)
        logger.debug(f"Added feedback sample: user={user_id}, news={news_id}, label={label}")

    def train_online(
        self,
        num_samples: int = 2000,
        epochs: int = 1,
        batch_size: int = 64,
        time_window_hours: Optional[float] = None
    ) -> Optional[tf.keras.callbacks.History]:
        if not self.buffer.should_train():
            logger.info("Not enough samples in buffer, skipping online training")
            return None

        with self._lock:
            samples = self.buffer.get_recent_samples(num_samples, time_window_hours)

            if len(samples) < self.buffer.min_size_for_training:
                logger.info("Not enough recent samples, skipping online training")
                return None

            features_batch = {
                k: tf.concat([s['features'][k] for s in samples], axis=0)
                for k in samples[0]['features'].keys()
            }
            labels = tf.constant([s['label'] for s in samples], dtype=tf.float32)

            dataset = tf.data.Dataset.from_tensor_slices((features_batch, labels))
            dataset = dataset.shuffle(len(samples))

            logger.info(f"Starting online training with {len(samples)} samples")

            original_loss = self.online_model.model.loss

            def combined_loss(y_true, y_pred):
                base_loss = original_loss(y_true, y_pred)

                if self.use_ewc and self.ewc is not None:
                    ewc_penalty = self.ewc.ewc_loss(self.online_model.model.trainable_weights)
                    return base_loss + ewc_penalty

                return base_loss

            self.online_model.model.loss = combined_loss

            try:
                history = self.online_model.online_fine_tune(
                    dataset,
                    epochs=epochs,
                    batch_size=batch_size,
                    learning_rate=self.online_learning_rate
                )
            finally:
                self.online_model.model.loss = original_loss

            self.last_train_time = datetime.now()
            self.train_count += 1

            logger.info(f"Online training complete. Total training sessions: {self.train_count}")

            return history

    def predict(
        self,
        features: Dict[str, tf.Tensor],
        use_ensemble: bool = True
    ) -> tf.Tensor:
        if use_ensemble and self.ensemble is not None:
            return self.ensemble.predict(features)
        else:
            return self.online_model.predict(features)

    def update_fusion_weights(self, online_weight: Optional[float] = None):
        if online_weight is not None:
            self.fusion_alpha = online_weight
            self.ensemble.update_weights({
                'offline': 1.0 - online_weight,
                'online': online_weight
            })

        if self.train_count > 0:
            adaptive_weight = min(0.8, 0.3 + 0.05 * self.train_count)
            self.fusion_alpha = adaptive_weight
            self.ensemble.update_weights({
                'offline': 1.0 - adaptive_weight,
                'online': adaptive_weight
            })
            logger.info(f"Adaptive fusion weight: offline={1-adaptive_weight:.3f}, online={adaptive_weight:.3f}")

    def merge_online_into_offline(self, merge_ratio: float = 0.1):
        logger.info(f"Merging online model into offline (ratio={merge_ratio})")

        offline_weights = self.offline_model.model.get_weights()
        online_weights = self.online_model.model.get_weights()

        merged_weights = [
            (1.0 - merge_ratio) * w_off + merge_ratio * w_on
            for w_off, w_on in zip(offline_weights, online_weights)
        ]

        self.offline_model.model.set_weights(merged_weights)
        self.online_model.model.set_weights(merged_weights)

        logger.info("Merge complete")

    def get_model_performance(
        self,
        eval_dataset: tf.data.Dataset
    ) -> Dict[str, Dict[str, float]]:
        results = {}

        for name, model in [('offline', self.offline_model), ('online', self.online_model)]:
            eval_results = model.model.evaluate(eval_dataset, verbose=0)
            results[name] = dict(zip(model.model.metrics_names, eval_results))

        return results

    def save_checkpoint(self, checkpoint_dir: str):
        os.makedirs(checkpoint_dir, exist_ok=True)

        self.online_model.save(os.path.join(checkpoint_dir, 'online_model'))
        self.offline_model.save(os.path.join(checkpoint_dir, 'offline_model'))

        if self.ewc is not None and self.ewc.fisher_matrix is not None:
            self.ewc.save(os.path.join(checkpoint_dir, 'ewc.pkl'))

        with open(os.path.join(checkpoint_dir, 'manager_state.pkl'), 'wb') as f:
            pickle.dump({
                'train_count': self.train_count,
                'last_train_time': self.last_train_time,
                'fusion_alpha': self.fusion_alpha,
                'ensemble_weights': self.ensemble.weights
            }, f)

        logger.info(f"Checkpoint saved to {checkpoint_dir}")

    def load_checkpoint(self, checkpoint_dir: str):
        online_path = os.path.join(checkpoint_dir, 'online_model')
        if os.path.exists(online_path):
            self.online_model = DeepFMModel.load(online_path)
            logger.info("Online model loaded")

        ewc_path = os.path.join(checkpoint_dir, 'ewc.pkl')
        if os.path.exists(ewc_path) and self.ewc is not None:
            self.ewc.load(ewc_path)
            logger.info("EWC state loaded")

        state_path = os.path.join(checkpoint_dir, 'manager_state.pkl')
        if os.path.exists(state_path):
            with open(state_path, 'rb') as f:
                state = pickle.load(f)
                self.train_count = state['train_count']
                self.last_train_time = state['last_train_time']
                self.fusion_alpha = state['fusion_alpha']
                if 'ensemble_weights' in state:
                    self.ensemble.weights = state['ensemble_weights']
            logger.info("Manager state loaded")

    def get_stats(self) -> Dict:
        return {
            'buffer_size': len(self.buffer),
            'train_count': self.train_count,
            'last_train_time': self.last_train_time.isoformat() if self.last_train_time else None,
            'fusion_alpha': self.fusion_alpha,
            'use_elastic_learning': self.use_elastic_learning,
            'use_ewc': self.use_ewc,
            'ensemble_weights': self.ensemble.weights if self.ensemble else None
        }
