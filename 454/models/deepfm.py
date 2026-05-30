import os
import sys
import tensorflow as tf
from typing import Dict, List, Tuple
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, get_feature_embedding_dims


class DeepFM(tf.keras.Model):
    def __init__(self, feature_info: Dict, config: Dict, use_adaptive_embedding: bool = True):
        super().__init__()
        self.feature_info = feature_info
        self.config = config
        self.model_config = config["models"]["deepfm"]
        self.use_adaptive_embedding = use_adaptive_embedding

        self.default_embedding_dim = self.model_config["embedding_dim"]
        self.hidden_units = self.model_config["hidden_units"]
        self.dropout_rates = self.model_config["dropout_rates"]
        self.learning_rate = self.model_config["learning_rate"]

        self.numerical_features = feature_info["feature_names"]["numerical"]
        self.categorical_features = feature_info["feature_names"]["categorical"]
        self.vocab_sizes = feature_info.get("vocab_sizes", {})

        if self.use_adaptive_embedding:
            self.embedding_dims = get_feature_embedding_dims(
                self.vocab_sizes,
                min_dim=4,
                max_dim=64,
                scale_factor=0.25
            )
        else:
            self.embedding_dims = {feat: self.default_embedding_dim for feat in self.categorical_features}

        self.total_embedding_dim = sum(self.embedding_dims.values()) if self.categorical_features else 0

        self._build_embeddings()
        self._build_deep_layers()
        self._build_output_layer()

        self.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss=tf.keras.losses.BinaryCrossentropy(),
            metrics=[
                tf.keras.metrics.AUC(name="auc"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
                tf.keras.metrics.BinaryAccuracy(name="accuracy")
            ]
        )

    def _build_embeddings(self):
        self.embedding_layers = {}
        for feat in self.categorical_features:
            vocab_size = self.vocab_sizes.get(feat, 100)
            emb_dim = self.embedding_dims.get(feat, self.default_embedding_dim)
            self.embedding_layers[feat] = tf.keras.layers.Embedding(
                input_dim=vocab_size,
                output_dim=emb_dim,
                embeddings_initializer="random_normal",
                name=f"embedding_{feat}"
            )

    def _build_deep_layers(self):
        self.deep_layers = []
        for i, (units, dropout) in enumerate(zip(self.hidden_units, self.dropout_rates)):
            self.deep_layers.extend([
                tf.keras.layers.Dense(units, activation="relu", name=f"dense_{i}"),
                tf.keras.layers.BatchNormalization(name=f"bn_{i}"),
                tf.keras.layers.Dropout(dropout, name=f"dropout_{i}")
            ])
        self.deep_seq = tf.keras.Sequential(self.deep_layers)

    def _build_output_layer(self):
        self.fm_linear_dense = tf.keras.layers.Dense(1, activation=None, name="fm_linear")
        self.output_layer = tf.keras.layers.Dense(1, activation="sigmoid", name="output")

    def call(self, inputs, training=False):
        numerical_inputs = []
        categorical_inputs = {}

        for feat in self.numerical_features:
            if feat in inputs:
                numerical_inputs.append(tf.expand_dims(inputs[feat], axis=-1))

        for feat in self.categorical_features:
            if feat in inputs:
                categorical_inputs[feat] = inputs[feat]

        numerical_concat = tf.concat(numerical_inputs, axis=1) if numerical_inputs else tf.zeros((tf.shape(list(inputs.values())[0])[0], 0))

        embeddings = []
        embedding_flat_list = []
        for feat in self.categorical_features:
            if feat in categorical_inputs:
                emb = self.embedding_layers[feat](categorical_inputs[feat])
                embeddings.append(emb)
                embedding_flat_list.append(tf.reshape(emb, [-1, self.embedding_dims[feat]]))

        fm_linear = self.fm_linear_dense(numerical_concat)

        if len(embeddings) > 1:
            max_dim = max(self.embedding_dims.values())
            padded_embeddings = []
            for feat, emb in zip(self.categorical_features, embeddings):
                dim = self.embedding_dims[feat]
                if dim < max_dim:
                    padding = tf.zeros((tf.shape(emb)[0], tf.shape(emb)[1], max_dim - dim))
                    padded_emb = tf.concat([emb, padding], axis=-1)
                else:
                    padded_emb = emb
                padded_embeddings.append(padded_emb)
            
            embeddings_concat = tf.concat(padded_embeddings, axis=1)
            sum_square = tf.square(tf.reduce_sum(embeddings_concat, axis=1))
            square_sum = tf.reduce_sum(tf.square(embeddings_concat), axis=1)
            fm_interaction = 0.5 * tf.reduce_sum(sum_square - square_sum, axis=1, keepdims=True)
        else:
            fm_interaction = tf.zeros_like(fm_linear)

        if embedding_flat_list:
            embedding_flat = tf.concat(embedding_flat_list, axis=1)
            deep_input = tf.concat([numerical_concat, embedding_flat], axis=1)
        else:
            deep_input = numerical_concat
        deep_output = self.deep_seq(deep_input, training=training)

        combined = tf.concat([fm_linear, fm_interaction, deep_output], axis=1)
        output = self.output_layer(combined)

        return output

    def get_embedding_weights(self) -> Dict[str, np.ndarray]:
        weights = {}
        for feat in self.categorical_features:
            weights[feat] = self.embedding_layers[feat].get_weights()[0]
        return weights

    def save_model(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.save(path)
