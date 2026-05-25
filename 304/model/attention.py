import tensorflow as tf
from tensorflow.keras import layers
import numpy as np
from typing import Optional


class TimeDecayLayer(layers.Layer):
    def __init__(self, half_life_hours: float = 168.0, min_decay: float = 0.3, **kwargs):
        super(TimeDecayLayer, self).__init__(**kwargs)
        self.half_life_hours = half_life_hours
        self.min_decay = min_decay

    def call(self, time_diffs_hours, mask=None):
        decay = tf.exp(-tf.math.log(2.0) * time_diffs_hours / self.half_life_hours)
        decay = tf.maximum(decay, self.min_decay)

        if mask is not None:
            mask = tf.cast(mask, tf.float32)
            decay = decay * mask

        return decay

    def get_config(self):
        config = super(TimeDecayLayer, self).get_config()
        config.update({
            'half_life_hours': self.half_life_hours,
            'min_decay': self.min_decay
        })
        return config


class AttentionLayer(layers.Layer):
    def __init__(self, hidden_units: int = 64, use_time_decay: bool = True,
                 half_life_hours: float = 168.0, **kwargs):
        super(AttentionLayer, self).__init__(**kwargs)
        self.hidden_units = hidden_units
        self.use_time_decay = use_time_decay
        self.half_life_hours = half_life_hours

        self.dense_q = layers.Dense(hidden_units, activation='relu')
        self.dense_k = layers.Dense(hidden_units, activation='relu')
        self.dense_v = layers.Dense(hidden_units, activation='relu')
        self.dense_output = layers.Dense(1)

        if use_time_decay:
            self.time_decay = TimeDecayLayer(half_life_hours=half_life_hours)

    def build(self, input_shape):
        super(AttentionLayer, self).build(input_shape)

    def call(self, inputs, mask=None, time_diffs=None):
        query, keys, values = inputs

        q = self.dense_q(query)
        k = self.dense_k(keys)
        v = self.dense_v(values)

        q_expanded = tf.expand_dims(q, 1)

        scores = tf.matmul(q_expanded, k, transpose_b=True)
        scores = scores / tf.sqrt(tf.cast(self.hidden_units, tf.float32))

        if self.use_time_decay and time_diffs is not None:
            time_decay_factors = self.time_decay(time_diffs, mask=mask)
            time_decay_factors = tf.expand_dims(time_decay_factors, 1)
            scores = scores + tf.math.log(time_decay_factors + 1e-9)

        if mask is not None:
            mask = tf.cast(mask, tf.float32)
            scores = scores + (1.0 - mask) * -1e9

        weights = tf.nn.softmax(scores, axis=-1)

        output = tf.matmul(weights, v)
        output = tf.squeeze(output, 1)

        return output

    def compute_output_shape(self, input_shape):
        return (input_shape[0][0], self.hidden_units)

    def get_config(self):
        config = super(AttentionLayer, self).get_config()
        config.update({
            'hidden_units': self.hidden_units,
            'use_time_decay': self.use_time_decay,
            'half_life_hours': self.half_life_hours
        })
        return config


class MultiHeadAttentionLayer(layers.Layer):
    def __init__(self, num_heads: int = 4, hidden_units: int = 64,
                 use_time_decay: bool = True, half_life_hours: float = 168.0, **kwargs):
        super(MultiHeadAttentionLayer, self).__init__(**kwargs)
        self.num_heads = num_heads
        self.hidden_units = hidden_units
        self.head_dim = hidden_units // num_heads
        self.use_time_decay = use_time_decay
        self.half_life_hours = half_life_hours

        self.dense_q = layers.Dense(hidden_units)
        self.dense_k = layers.Dense(hidden_units)
        self.dense_v = layers.Dense(hidden_units)
        self.dense_output = layers.Dense(hidden_units)

        if use_time_decay:
            self.time_decay = TimeDecayLayer(half_life_hours=half_life_hours)

    def build(self, input_shape):
        super(MultiHeadAttentionLayer, self).build(input_shape)

    def call(self, inputs, mask=None, time_diffs=None):
        query, keys, values = inputs
        batch_size = tf.shape(query)[0]
        seq_len = tf.shape(keys)[1]

        q = self.dense_q(query)
        k = self.dense_k(keys)
        v = self.dense_v(values)

        q = self._split_heads(q, batch_size)
        k = self._split_heads(k, batch_size)
        v = self._split_heads(v, batch_size)

        scores = tf.matmul(q, k, transpose_b=True)
        scores = scores / tf.sqrt(tf.cast(self.head_dim, tf.float32))

        if self.use_time_decay and time_diffs is not None:
            time_decay_factors = self.time_decay(time_diffs, mask=mask)
            time_decay_factors = tf.expand_dims(time_decay_factors, 1)
            time_decay_factors = tf.expand_dims(time_decay_factors, 1)
            scores = scores + tf.math.log(time_decay_factors + 1e-9)

        if mask is not None:
            mask = tf.cast(mask, tf.float32)
            mask = tf.expand_dims(mask, 1)
            mask = tf.expand_dims(mask, 1)
            scores = scores + (1.0 - mask) * -1e9

        weights = tf.nn.softmax(scores, axis=-1)

        output = tf.matmul(weights, v)
        output = tf.transpose(output, perm=[0, 2, 1, 3])
        output = tf.reshape(output, [batch_size, -1, self.hidden_units])
        output = output[:, -1, :]

        output = self.dense_output(output)

        return output

    def _split_heads(self, x, batch_size):
        x = tf.reshape(x, [batch_size, -1, self.num_heads, self.head_dim])
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def get_config(self):
        config = super(MultiHeadAttentionLayer, self).get_config()
        config.update({
            'num_heads': self.num_heads,
            'hidden_units': self.hidden_units,
            'use_time_decay': self.use_time_decay,
            'half_life_hours': self.half_life_hours
        })
        return config


class BehaviorSequenceAttention(layers.Layer):
    def __init__(self, embedding_dim: int, hidden_units: int = 64,
                 use_time_decay: bool = True, half_life_hours: float = 168.0,
                 use_news_age_decay: bool = True, news_age_half_life: float = 72.0, **kwargs):
        super(BehaviorSequenceAttention, self).__init__(**kwargs)
        self.embedding_dim = embedding_dim
        self.hidden_units = hidden_units
        self.use_time_decay = use_time_decay
        self.half_life_hours = half_life_hours
        self.use_news_age_decay = use_news_age_decay
        self.news_age_half_life = news_age_half_life

        self.dense_q = layers.Dense(hidden_units, activation='relu')
        self.dense_k = layers.Dense(hidden_units, activation='relu')
        self.dense_v = layers.Dense(embedding_dim)
        self.score_dense = layers.Dense(1, use_bias=False)

        if use_time_decay:
            self.behavior_time_decay = TimeDecayLayer(half_life_hours=half_life_hours, min_decay=0.2)

        if use_news_age_decay:
            self.news_age_decay = TimeDecayLayer(half_life_hours=news_age_half_life, min_decay=0.5)

    def build(self, input_shape):
        super(BehaviorSequenceAttention, self).build(input_shape)

    def call(self, inputs, mask=None, behavior_time_diffs=None, news_ages=None):
        target_emb, behavior_embs = inputs
        batch_size = tf.shape(behavior_embs)[0]
        seq_len = tf.shape(behavior_embs)[1]

        q = self.dense_q(target_emb)
        k = self.dense_k(behavior_embs)

        q_expanded = tf.expand_dims(q, 1)
        k_reshaped = k

        q_tiled = tf.tile(q_expanded, [1, seq_len, 1])

        concat = tf.concat([q_tiled, k_reshaped, q_tiled * k_reshaped], axis=-1)

        scores = self.score_dense(concat)
        scores = tf.squeeze(scores, -1)

        if self.use_time_decay and behavior_time_diffs is not None:
            behavior_decay = self.behavior_time_decay(behavior_time_diffs, mask=mask)
            scores = scores + tf.math.log(behavior_decay + 1e-9)

        if self.use_news_age_decay and news_ages is not None:
            news_age_decay = self.news_age_decay(news_ages, mask=mask)
            scores = scores + tf.math.log(news_age_decay + 1e-9)

        if mask is not None:
            mask = tf.cast(mask, tf.float32)
            scores = scores + (1.0 - mask) * -1e9

        weights = tf.nn.softmax(scores, axis=-1)
        weights_expanded = tf.expand_dims(weights, -1)

        weighted_sum = tf.reduce_sum(weights_expanded * behavior_embs, axis=1)

        return weighted_sum

    def compute_output_shape(self, input_shape):
        return (input_shape[0][0], self.embedding_dim)

    def get_config(self):
        config = super(BehaviorSequenceAttention, self).get_config()
        config.update({
            'embedding_dim': self.embedding_dim,
            'hidden_units': self.hidden_units,
            'use_time_decay': self.use_time_decay,
            'half_life_hours': self.half_life_hours,
            'use_news_age_decay': self.use_news_age_decay,
            'news_age_half_life': self.news_age_half_life
        })
        return config


class TemporalFactorizationLayer(layers.Layer):
    def __init__(self, num_time_bins: int = 24, **kwargs):
        super(TemporalFactorizationLayer, self).__init__(**kwargs)
        self.num_time_bins = num_time_bins
        self.time_embedding = layers.Embedding(num_time_bins, 8)

    def call(self, inputs):
        time_features, item_emb = inputs

        hour_of_day = tf.cast(time_features[:, 0], tf.int32)
        day_of_week = tf.cast(time_features[:, 1], tf.int32)
        is_weekend = tf.cast(time_features[:, 2], tf.float32)

        hour_emb = self.time_embedding(hour_of_day)
        day_emb = self.time_embedding(day_of_week + 24)

        time_emb = tf.concat([hour_emb, day_emb, tf.expand_dims(is_weekend, -1)], axis=-1)

        time_gate = layers.Dense(item_emb.shape[-1], activation='sigmoid')(time_emb)
        time_bias = layers.Dense(item_emb.shape[-1], activation='tanh')(time_emb)

        output = item_emb * (1 + time_gate) + time_bias

        return output

    def get_config(self):
        config = super(TemporalFactorizationLayer, self).get_config()
        config.update({'num_time_bins': self.num_time_bins})
        return config
