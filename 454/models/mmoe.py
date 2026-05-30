import os
import sys
import tensorflow as tf
from typing import Dict, List, Tuple
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, get_feature_embedding_dims


class ExpertLayer(tf.keras.layers.Layer):
    def __init__(self, hidden_units: List[int], dropout_rate: float = 0.2, **kwargs):
        super().__init__(**kwargs)
        self.hidden_units = hidden_units
        self.dropout_rate = dropout_rate
        self.layers = []

    def build(self, input_shape):
        for i, units in enumerate(self.hidden_units):
            self.layers.extend([
                tf.keras.layers.Dense(units, activation="relu", name=f"expert_dense_{i}"),
                tf.keras.layers.BatchNormalization(name=f"expert_bn_{i}"),
                tf.keras.layers.Dropout(self.dropout_rate, name=f"expert_dropout_{i}")
            ])
        super().build(input_shape)

    def call(self, inputs, training=False):
        x = inputs
        for layer in self.layers:
            x = layer(x, training=training) if isinstance(layer, tf.keras.layers.Dropout) or isinstance(layer, tf.keras.layers.BatchNormalization) else layer(x)
        return x


class TowerLayer(tf.keras.layers.Layer):
    def __init__(self, hidden_units: List[int], output_activation: str = "sigmoid", **kwargs):
        super().__init__(**kwargs)
        self.hidden_units = hidden_units
        self.output_activation = output_activation
        self.layers = []

    def build(self, input_shape):
        for i, units in enumerate(self.hidden_units):
            self.layers.extend([
                tf.keras.layers.Dense(units, activation="relu", name=f"tower_dense_{i}"),
                tf.keras.layers.BatchNormalization(name=f"tower_bn_{i}")
            ])
        self.layers.append(tf.keras.layers.Dense(1, activation=self.output_activation, name="tower_output"))
        super().build(input_shape)

    def call(self, inputs, training=False):
        x = inputs
        for layer in self.layers:
            x = layer(x, training=training) if isinstance(layer, tf.keras.layers.BatchNormalization) else layer(x)
        return x


class MMoE(tf.keras.Model):
    def __init__(self, feature_info: Dict, config: Dict, use_adaptive_embedding: bool = True):
        super().__init__()
        self.feature_info = feature_info
        self.config = config
        self.model_config = config["models"]["mmoe"]
        self.use_adaptive_embedding = use_adaptive_embedding

        self.num_experts = self.model_config["num_experts"]
        self.expert_hidden_units = self.model_config["expert_hidden_units"]
        self.tower_hidden_units = self.model_config["tower_hidden_units"]
        self.num_tasks = self.model_config["num_tasks"]
        self.default_embedding_dim = self.model_config["embedding_dim"]
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
        self._build_experts()
        self._build_gates()
        self._build_towers()

        self.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss={
                "click": tf.keras.losses.BinaryCrossentropy(),
                "conversion": tf.keras.losses.BinaryCrossentropy()
            },
            loss_weights={"click": 0.7, "conversion": 0.3},
            metrics={
                "click": [
                    tf.keras.metrics.AUC(name="auc"),
                    tf.keras.metrics.Precision(name="precision"),
                    tf.keras.metrics.Recall(name="recall")
                ],
                "conversion": [
                    tf.keras.metrics.AUC(name="auc"),
                    tf.keras.metrics.Precision(name="precision"),
                    tf.keras.metrics.Recall(name="recall")
                ]
            }
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

    def _build_experts(self):
        self.experts = []
        for i in range(self.num_experts):
            expert = ExpertLayer(self.expert_hidden_units, dropout_rate=0.2, name=f"expert_{i}")
            self.experts.append(expert)

    def _build_gates(self):
        self.gates = []
        for i in range(self.num_tasks):
            gate = tf.keras.layers.Dense(
                self.num_experts,
                activation="softmax",
                name=f"gate_{i}"
            )
            self.gates.append(gate)

    def _build_towers(self):
        self.towers = []
        task_names = ["click", "conversion"]
        for i in range(self.num_tasks):
            tower = TowerLayer(
                self.tower_hidden_units,
                output_activation="sigmoid",
                name=f"tower_{task_names[i]}"
            )
            self.towers.append(tower)

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
        for feat in self.categorical_features:
            if feat in categorical_inputs:
                emb = self.embedding_layers[feat](categorical_inputs[feat])
                embeddings.append(emb)

        if embeddings:
            batch_size = tf.shape(numerical_concat)[0]
            embedding_flat = tf.concat([tf.reshape(e, [batch_size, -1]) for e in embeddings], axis=1)
            combined_input = tf.concat([numerical_concat, embedding_flat], axis=1)
        else:
            combined_input = numerical_concat

        expert_outputs = []
        for expert in self.experts:
            expert_out = expert(combined_input, training=training)
            expert_outputs.append(tf.expand_dims(expert_out, axis=1))

        expert_outputs = tf.concat(expert_outputs, axis=1)

        task_outputs = []
        for i, (gate, tower) in enumerate(zip(self.gates, self.towers)):
            gate_weights = gate(combined_input)
            gate_weights = tf.expand_dims(gate_weights, axis=-1)
            weighted_experts = tf.reduce_sum(expert_outputs * gate_weights, axis=1)
            task_output = tower(weighted_experts, training=training)
            task_outputs.append(task_output)

        return {
            "click": task_outputs[0],
            "conversion": task_outputs[1] if len(task_outputs) > 1 else task_outputs[0]
        }

    def get_gate_weights(self, inputs) -> List[np.ndarray]:
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
        for feat in self.categorical_features:
            if feat in categorical_inputs:
                emb = self.embedding_layers[feat](categorical_inputs[feat])
                embeddings.append(emb)

        if embeddings:
            batch_size = tf.shape(numerical_concat)[0]
            embedding_flat = tf.concat([tf.reshape(e, [batch_size, -1]) for e in embeddings], axis=1)
            combined_input = tf.concat([numerical_concat, embedding_flat], axis=1)
        else:
            combined_input = numerical_concat

        gate_weights_list = []
        for gate in self.gates:
            gate_weights = gate(combined_input)
            gate_weights_list.append(gate_weights.numpy())

        return gate_weights_list

    def save_model(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.save(path)
