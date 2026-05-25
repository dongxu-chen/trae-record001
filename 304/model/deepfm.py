import tensorflow as tf
from tensorflow.keras import layers, Model
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
import logging

from config import config

logger = logging.getLogger(__name__)
from .attention import BehaviorSequenceAttention, TimeDecayLayer, TemporalFactorizationLayer


class DeepFMModel:
    def __init__(
        self,
        num_users: int,
        num_news: int,
        num_categories: int,
        embedding_dim: int = None,
        dnn_hidden_units: List[int] = None,
        learning_rate: float = None,
        max_sequence_length: int = 50,
        use_time_decay: bool = True,
        use_news_age_decay: bool = True,
        use_elastic_learning: bool = False,
        use_multi_objective: bool = True,
        duration_loss_weight: float = 0.5
    ):
        self.num_users = num_users
        self.num_news = num_news
        self.num_categories = num_categories
        self.embedding_dim = embedding_dim or config.EMBEDDING_DIM
        self.dnn_hidden_units = dnn_hidden_units or config.DNN_HIDDEN_UNITS
        self.learning_rate = learning_rate or config.LEARNING_RATE
        self.max_sequence_length = max_sequence_length
        self.use_time_decay = use_time_decay
        self.use_news_age_decay = use_news_age_decay
        self.use_elastic_learning = use_elastic_learning
        self.use_multi_objective = use_multi_objective
        self.duration_loss_weight = duration_loss_weight

        self._offline_weights = None
        self._elastic_alpha = 0.7
        self._elastic_beta = 0.3

        self.model = self._build_model()

    def _build_model(self) -> Model:
        user_id_input = layers.Input(shape=(1,), name='user_id', dtype=tf.int32)
        news_id_input = layers.Input(shape=(1,), name='news_id', dtype=tf.int32)
        category_id_input = layers.Input(shape=(1,), name='category_id', dtype=tf.int32)
        behavior_sequence_input = layers.Input(
            shape=(self.max_sequence_length,),
            name='behavior_sequence',
            dtype=tf.int32
        )
        mask_input = layers.Input(
            shape=(self.max_sequence_length,),
            name='mask',
            dtype=tf.float32
        )

        behavior_time_diffs_input = layers.Input(
            shape=(self.max_sequence_length,),
            name='behavior_time_diffs',
            dtype=tf.float32
        )
        news_ages_input = layers.Input(
            shape=(self.max_sequence_length,),
            name='news_ages',
            dtype=tf.float32
        )
        candidate_news_age_input = layers.Input(
            shape=(1,),
            name='candidate_news_age',
            dtype=tf.float32
        )

        user_embedding_layer = layers.Embedding(
            input_dim=self.num_users,
            output_dim=self.embedding_dim,
            embeddings_initializer='glorot_uniform',
            name='user_embedding'
        )
        news_embedding_layer = layers.Embedding(
            input_dim=self.num_news,
            output_dim=self.embedding_dim,
            embeddings_initializer='glorot_uniform',
            name='news_embedding'
        )
        category_embedding_layer = layers.Embedding(
            input_dim=self.num_categories,
            output_dim=self.embedding_dim,
            embeddings_initializer='glorot_uniform',
            name='category_embedding'
        )

        user_emb = user_embedding_layer(user_id_input)
        user_emb = layers.Flatten()(user_emb)

        news_emb = news_embedding_layer(news_id_input)
        news_emb = layers.Flatten()(news_emb)

        category_emb = category_embedding_layer(category_id_input)
        category_emb = layers.Flatten()(category_emb)

        behavior_sequence_emb = news_embedding_layer(behavior_sequence_input)

        attention_layer = BehaviorSequenceAttention(
            embedding_dim=self.embedding_dim,
            hidden_units=self.embedding_dim * 2,
            use_time_decay=self.use_time_decay,
            half_life_hours=168.0,
            use_news_age_decay=self.use_news_age_decay,
            news_age_half_life=72.0,
            name='behavior_attention'
        )

        attention_kwargs = {'mask': mask_input}
        if self.use_time_decay:
            attention_kwargs['behavior_time_diffs'] = behavior_time_diffs_input
        if self.use_news_age_decay:
            attention_kwargs['news_ages'] = news_ages_input

        user_interest_emb = attention_layer(
            [news_emb, behavior_sequence_emb],
            **attention_kwargs
        )

        news_age_decay_layer = TimeDecayLayer(half_life_hours=72.0, min_decay=0.5, name='candidate_age_decay')
        candidate_age_factor = news_age_decay_layer(candidate_news_age_input)
        candidate_age_factor = layers.Flatten()(candidate_age_factor)

        time_fusion_layer = TemporalFactorizationLayer(num_time_bins=24, name='temporal_fusion')
        time_features = tf.concat([
            candidate_news_age_input,
            candidate_age_factor,
            tf.zeros_like(candidate_news_age_input)
        ], axis=-1)
        time_aware_news_emb = time_fusion_layer([time_features, news_emb])

        sparse_features = [user_emb, time_aware_news_emb, category_emb, user_interest_emb]
        dense_input = layers.Concatenate()(sparse_features)

        time_dense_features = layers.Concatenate()([candidate_age_factor])
        dense_input = layers.Concatenate()([dense_input, time_dense_features])

        fm_output = self._fm_layer(sparse_features)

        dnn_output = dense_input
        for units in self.dnn_hidden_units:
            dnn_output = layers.Dense(units, activation='relu')(dnn_output)
            dnn_output = layers.Dropout(0.2)(dnn_output)
            dnn_output = layers.BatchNormalization()(dnn_output)

        concat_output = layers.Concatenate()([fm_output, dnn_output])
        final_output = layers.Dense(64, activation='relu')(concat_output)
        final_output = layers.Dropout(0.2)(final_output)

        if self.use_multi_objective:
            click_output = layers.Dense(1, activation='sigmoid', name='click_output')(final_output)

            duration_hidden = layers.Dense(32, activation='relu')(final_output)
            duration_hidden = layers.Dropout(0.2)(duration_hidden)
            duration_output = layers.Dense(1, activation='relu', name='duration_output')(duration_hidden)

            outputs = [click_output, duration_output]
            loss = {
                'click_output': self._elastic_weighted_bce_loss if self.use_elastic_learning else self._weighted_bce_loss,
                'duration_output': self._mse_duration_loss
            }
            loss_weights = {
                'click_output': 1.0,
                'duration_output': self.duration_loss_weight
            }
            metrics = {
                'click_output': [
                    tf.keras.metrics.AUC(name='auc'),
                    tf.keras.metrics.BinaryAccuracy(name='accuracy'),
                    tf.keras.metrics.Precision(name='precision'),
                    tf.keras.metrics.Recall(name='recall')
                ],
                'duration_output': [
                    tf.keras.metrics.MeanAbsoluteError(name='mae'),
                    tf.keras.metrics.RootMeanSquaredError(name='rmse')
                ]
            }
        else:
            outputs = layers.Dense(1, activation='sigmoid', name='output')(final_output)
            loss = self._elastic_weighted_bce_loss if self.use_elastic_learning else self._weighted_bce_loss
            loss_weights = None
            metrics = [
                tf.keras.metrics.AUC(name='auc'),
                tf.keras.metrics.BinaryAccuracy(name='accuracy'),
                tf.keras.metrics.Precision(name='precision'),
                tf.keras.metrics.Recall(name='recall')
            ]

        model = Model(
            inputs=[
                user_id_input,
                news_id_input,
                category_id_input,
                behavior_sequence_input,
                mask_input,
                behavior_time_diffs_input,
                news_ages_input,
                candidate_news_age_input
            ],
            outputs=outputs,
            name='DeepFM_TimeAware_Attention_MultiObjective'
        )

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss=loss,
            loss_weights=loss_weights,
            metrics=metrics
        )

        return model

    def _fm_layer(self, feature_embeddings: List[tf.Tensor]) -> tf.Tensor:
        feature_matrix = tf.stack(feature_embeddings, axis=1)

        sum_square = tf.square(tf.reduce_sum(feature_matrix, axis=1))
        square_sum = tf.reduce_sum(tf.square(feature_matrix), axis=1)

        cross_term = 0.5 * (sum_square - square_sum)

        linear_term = tf.concat(feature_embeddings, axis=1)
        linear_term = layers.Dense(
            self.embedding_dim,
            activation='relu',
            kernel_regularizer=tf.keras.regularizers.l2(0.001)
        )(linear_term)

        fm_output = layers.Concatenate()([linear_term, cross_term])

        return fm_output

    def _weighted_bce_loss(self, y_true, y_pred):
        weight = tf.constant([1.0, 3.0], dtype=tf.float32)
        y_true = tf.cast(y_true, tf.float32)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)

        weights = y_true * weight[1] + (1 - y_true) * weight[0]
        loss = -weights * (y_true * tf.math.log(y_pred) + (1 - y_true) * tf.math.log(1 - y_pred))

        return tf.reduce_mean(loss)

    def _mse_duration_loss(self, y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        y_pred = tf.cast(y_pred, tf.float32)

        y_pred = tf.maximum(y_pred, 0.0)

        error = y_true - y_pred
        squared_error = tf.square(error)

        huber_delta = 30.0
        abs_error = tf.abs(error)
        huber_loss = tf.where(
            abs_error <= huber_delta,
            0.5 * squared_error,
            huber_delta * (abs_error - 0.5 * huber_delta)
        )

        return tf.reduce_mean(huber_loss)

    def _elastic_weighted_bce_loss(self, y_true, y_pred):
        base_loss = self._weighted_bce_loss(y_true, y_pred)

        if self._offline_weights is not None:
            elastic_penalty = 0.0
            current_weights = self.model.trainable_weights

            for w_offline, w_online in zip(self._offline_weights, current_weights):
                if w_offline.shape == w_online.shape:
                    w_diff = w_online - w_offline
                    elastic_penalty += tf.reduce_sum(tf.square(w_diff))

            elastic_penalty = elastic_penalty * self._elastic_beta
            total_loss = self._elastic_alpha * base_loss + 0.5 * elastic_penalty
            return total_loss

        return base_loss

    def enable_elastic_learning(self, alpha: float = 0.7, beta: float = 0.3):
        self.use_elastic_learning = True
        self._elastic_alpha = alpha
        self._elastic_beta = beta
        self._offline_weights = [w.numpy() for w in self.model.trainable_weights]
        logger.info(f"Elastic learning enabled: alpha={alpha}, beta={beta}")

    def calculate_time_diffs(
        self,
        behavior_timestamps: List[datetime],
        current_time: Optional[datetime] = None
    ) -> List[float]:
        current_time = current_time or datetime.now()
        time_diffs = []
        for ts in behavior_timestamps:
            diff_hours = (current_time - ts).total_seconds() / 3600
            time_diffs.append(max(0.0, diff_hours))
        return time_diffs

    def calculate_news_ages(
        self,
        news_publish_times: List[Optional[datetime]],
        current_time: Optional[datetime] = None
    ) -> List[float]:
        current_time = current_time or datetime.now()
        ages = []
        for publish_time in news_publish_times:
            if publish_time is None:
                ages.append(0.0)
            else:
                age_hours = (current_time - publish_time).total_seconds() / 3600
                ages.append(max(0.0, age_hours))
        return ages

    def prepare_features(
        self,
        user_ids: List[int],
        news_ids: List[int],
        category_ids: List[int],
        behavior_sequences: List[List[int]],
        behavior_timestamps: Optional[List[List[datetime]]] = None,
        news_publish_times: Optional[List[List[datetime]]] = None,
        candidate_publish_times: Optional[List[datetime]] = None,
        padding_value: int = 0,
        current_time: Optional[datetime] = None
    ) -> Dict[str, tf.Tensor]:
        current_time = current_time or datetime.now()
        batch_size = len(user_ids)

        padded_sequences = []
        masks = []
        behavior_time_diffs = []
        news_ages = []
        candidate_news_ages = []

        for i, seq in enumerate(behavior_sequences):
            if len(seq) >= self.max_sequence_length:
                padded = seq[-self.max_sequence_length:]
                mask = [1.0] * self.max_sequence_length
            else:
                padded = seq + [padding_value] * (self.max_sequence_length - len(seq))
                mask = [1.0] * len(seq) + [0.0] * (self.max_sequence_length - len(seq))

            padded_sequences.append(padded)
            masks.append(mask)

            if behavior_timestamps and i < len(behavior_timestamps):
                ts_list = behavior_timestamps[i][-self.max_sequence_length:]
                ts_diff = self.calculate_time_diffs(ts_list, current_time)
                ts_diff = ts_diff + [0.0] * (self.max_sequence_length - len(ts_diff))
                behavior_time_diffs.append(ts_diff)
            else:
                behavior_time_diffs.append([0.0] * self.max_sequence_length)

            if news_publish_times and i < len(news_publish_times):
                pt_list = news_publish_times[i][-self.max_sequence_length:]
                na_list = self.calculate_news_ages(pt_list, current_time)
                na_list = na_list + [0.0] * (self.max_sequence_length - len(na_list))
                news_ages.append(na_list)
            else:
                news_ages.append([0.0] * self.max_sequence_length)

            if candidate_publish_times and i < len(candidate_publish_times):
                cpt = candidate_publish_times[i]
                cna = self.calculate_news_ages([cpt], current_time)[0]
                candidate_news_ages.append([cna])
            else:
                candidate_news_ages.append([0.0])

        return {
            'user_id': tf.constant(user_ids, dtype=tf.int32),
            'news_id': tf.constant(news_ids, dtype=tf.int32),
            'category_id': tf.constant(category_ids, dtype=tf.int32),
            'behavior_sequence': tf.constant(padded_sequences, dtype=tf.int32),
            'mask': tf.constant(masks, dtype=tf.float32),
            'behavior_time_diffs': tf.constant(behavior_time_diffs, dtype=tf.float32),
            'news_ages': tf.constant(news_ages, dtype=tf.float32),
            'candidate_news_age': tf.constant(candidate_news_ages, dtype=tf.float32)
        }

    def online_fine_tune(
        self,
        online_dataset,
        epochs: int = 1,
        batch_size: int = 64,
        learning_rate: float = None
    ):
        if learning_rate is None:
            learning_rate = self.learning_rate * 0.1

        original_lr = tf.keras.backend.get_value(self.model.optimizer.learning_rate)
        tf.keras.backend.set_value(self.model.optimizer.learning_rate, learning_rate)

        try:
            history = self.model.fit(
                online_dataset.batch(batch_size),
                epochs=epochs,
                verbose=1
            )
        finally:
            tf.keras.backend.set_value(self.model.optimizer.learning_rate, original_lr)

        return history

    def train(self, train_dataset, val_dataset=None, epochs=None, batch_size=None):
        epochs = epochs or config.EPOCHS
        batch_size = batch_size or config.BATCH_SIZE

        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_auc',
                patience=3,
                restore_best_weights=True,
                mode='max'
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_auc',
                factor=0.5,
                patience=2,
                mode='max'
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath=f'{config.MODEL_PATH}/checkpoint',
                monitor='val_auc',
                save_best_only=True,
                mode='max'
            )
        ]

        history = self.model.fit(
            train_dataset.batch(batch_size),
            validation_data=val_dataset.batch(batch_size) if val_dataset else None,
            epochs=epochs,
            callbacks=callbacks
        )

        return history

    def predict(self, features: Dict[str, tf.Tensor]) -> tf.Tensor:
        predictions = self.model.predict(features, verbose=0)

        if self.use_multi_objective and isinstance(predictions, list) and len(predictions) >= 2:
            return predictions[0]

        return predictions

    def predict_multi_objective(self, features: Dict[str, tf.Tensor]) -> Dict[str, tf.Tensor]:
        predictions = self.model.predict(features, verbose=0)

        if self.use_multi_objective and isinstance(predictions, list) and len(predictions) >= 2:
            return {
                'click_prob': predictions[0],
                'predicted_duration': predictions[1]
            }

        return {
            'click_prob': predictions,
            'predicted_duration': tf.zeros_like(predictions)
        }

    def save(self, path: str = None):
        path = path or config.MODEL_PATH
        self.model.save(path)

    @classmethod
    def load(cls, path: str = None) -> 'DeepFMModel':
        path = path or config.MODEL_PATH
        custom_objects = {
            'BehaviorSequenceAttention': BehaviorSequenceAttention,
            'TimeDecayLayer': TimeDecayLayer,
            'TemporalFactorizationLayer': TemporalFactorizationLayer
        }
        with tf.keras.utils.custom_object_scope(custom_objects):
            model = tf.keras.models.load_model(path)

        instance = cls.__new__(cls)
        instance.model = model
        instance.embedding_dim = config.EMBEDDING_DIM
        instance.max_sequence_length = 50
        instance.use_time_decay = True
        instance.use_news_age_decay = True
        instance.use_elastic_learning = False
        instance.use_multi_objective = len(model.outputs) >= 2
        instance.duration_loss_weight = 0.5
        instance._offline_weights = None
        instance._elastic_alpha = 0.7
        instance._elastic_beta = 0.3

        return instance

    def get_user_embedding(self, user_id: int) -> tf.Tensor:
        user_embedding_layer = self.model.get_layer('user_embedding')
        return user_embedding_layer(tf.constant([user_id]))[0]

    def get_news_embedding(self, news_id: int) -> tf.Tensor:
        news_embedding_layer = self.model.get_layer('news_embedding')
        return news_embedding_layer(tf.constant([news_id]))[0]

    def get_embedding_weights(self) -> Dict[str, tf.Tensor]:
        return {
            'user_embeddings': self.model.get_layer('user_embedding').get_weights()[0],
            'news_embeddings': self.model.get_layer('news_embedding').get_weights()[0],
            'category_embeddings': self.model.get_layer('category_embedding').get_weights()[0]
        }
