import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.optimizers import Adam
import config


class FM(layers.Layer):
    def __init__(self, **kwargs):
        super(FM, self).__init__(**kwargs)
    
    def build(self, input_shape):
        super(FM, self).build(input_shape)
    
    def call(self, inputs):
        if len(inputs.shape) != 3:
            raise ValueError(f"Expected 3D tensor, got shape {inputs.shape}")
        
        square_of_sum = tf.square(tf.reduce_sum(inputs, axis=1))
        sum_of_square = tf.reduce_sum(tf.square(inputs), axis=1)
        cross_term = 0.5 * (square_of_sum - sum_of_square)
        
        return cross_term


class MultiTaskOutputLayer(layers.Layer):
    def __init__(self, num_tasks, **kwargs):
        super(MultiTaskOutputLayer, self).__init__(**kwargs)
        self.num_tasks = num_tasks
    
    def build(self, input_shape):
        self.task_weights = []
        for i in range(self.num_tasks):
            self.task_weights.append(
                self.add_weight(
                    shape=(input_shape[-1], 1),
                    initializer='glorot_uniform',
                    name=f'task_weight_{i}'
                )
            )
        super(MultiTaskOutputLayer, self).build(input_shape)
    
    def call(self, inputs):
        outputs = []
        for weight in self.task_weights:
            logits = tf.matmul(inputs, weight)
            outputs.append(tf.sigmoid(logits))
        return tf.concat(outputs, axis=-1)


class FMOnlyModel(Model):
    def __init__(self, feature_spec, num_tasks=1):
        super(FMOnlyModel, self).__init__()
        self.feature_spec = feature_spec
        self.num_tasks = num_tasks
        
        self._build_embeddings()
        self._build_fm_layers()
        self._build_output_layer()
    
    def _build_embeddings(self):
        self.embedding_layers = {}
        self.linear_embeddings = {}
        
        for feat_name, feat_info in self.feature_spec.items():
            if feat_info['type'] == 'categorical':
                vocab_size = feat_info.get('vocab_size', 1000)
                embed_dim = feat_info.get('embed_dim', config.EMBEDDING_DIM)
                
                self.embedding_layers[feat_name] = layers.Embedding(
                    input_dim=vocab_size,
                    output_dim=embed_dim,
                    embeddings_initializer='glorot_uniform',
                    name=f'embedding_{feat_name}'
                )
                
                self.linear_embeddings[feat_name] = layers.Embedding(
                    input_dim=vocab_size,
                    output_dim=1,
                    embeddings_initializer='glorot_uniform',
                    name=f'linear_{feat_name}'
                )
            
            elif feat_info['type'] == 'dense':
                self.linear_embeddings[feat_name] = layers.Dense(
                    units=1,
                    use_bias=False,
                    name=f'linear_dense_{feat_name}'
                )
    
    def _build_fm_layers(self):
        self.fm_layer = FM()
        self.fm_bias = self.add_weight(
            shape=(1,),
            initializer='zeros',
            trainable=True,
            name='fm_bias'
        )
    
    def _build_output_layer(self):
        if self.num_tasks == 1:
            self.output_layer = layers.Dense(
                units=1,
                activation='sigmoid',
                kernel_initializer='glorot_uniform',
                name='output'
            )
        else:
            self.output_layer = MultiTaskOutputLayer(
                num_tasks=self.num_tasks,
                name='multi_task_output'
            )
    
    def call(self, inputs, training=False):
        linear_terms = []
        fm_embeddings = []
        
        for feat_name, feat_info in self.feature_spec.items():
            x = inputs[feat_name]
            
            if feat_info['type'] == 'categorical':
                embed = self.embedding_layers[feat_name](x)
                linear_term = self.linear_embeddings[feat_name](x)
                
                if len(embed.shape) == 3:
                    embed = tf.reduce_mean(embed, axis=1)
                    linear_term = tf.reduce_sum(linear_term, axis=1)
                elif len(embed.shape) == 4:
                    embed = tf.reshape(embed, [-1, embed.shape[1] * embed.shape[2], embed.shape[3]])
                    embed = tf.reduce_mean(embed, axis=1)
                    linear_term = tf.reduce_sum(linear_term, axis=[1, 2])
                
                fm_embeddings.append(tf.expand_dims(embed, axis=1))
                linear_terms.append(linear_term)
            
            elif feat_info['type'] == 'dense':
                if len(x.shape) == 1:
                    x = tf.expand_dims(x, axis=-1)
                elif len(x.shape) > 2:
                    x = tf.reshape(x, [-1, x.shape[1]])
                
                linear_term = self.linear_embeddings[feat_name](x)
                linear_terms.append(linear_term)
                
                dnn_dense = layers.Dense(config.EMBEDDING_DIM, activation='relu')(x)
                fm_embeddings.append(tf.expand_dims(dnn_dense, axis=1))
        
        linear_output = tf.add_n(linear_terms)
        
        fm_input = tf.concat(fm_embeddings, axis=1)
        fm_output = self.fm_layer(fm_input)
        
        concat_output = tf.concat([linear_output, fm_output], axis=-1)
        final_output = self.output_layer(concat_output)
        
        return final_output
    
    def get_embedding_weights(self):
        embedding_weights = {}
        for feat_name in self.embedding_layers.keys():
            embedding_weights[feat_name] = {
                'embedding': self.embedding_layers[feat_name].get_weights()[0],
                'linear': self.linear_embeddings[feat_name].get_weights()[0]
            }
        return embedding_weights


class DeepFM(Model):
    def __init__(self, feature_spec, pretrained_embeddings=None, num_tasks=1):
        super(DeepFM, self).__init__()
        self.feature_spec = feature_spec
        self.pretrained_embeddings = pretrained_embeddings
        self.num_tasks = num_tasks
        
        self._build_embeddings()
        self._build_fm_layers()
        self._build_dnn_layers()
        self._build_output_layer()
    
    def _build_embeddings(self):
        self.embedding_layers = {}
        self.linear_embeddings = {}
        
        for feat_name, feat_info in self.feature_spec.items():
            if feat_info['type'] == 'categorical':
                vocab_size = feat_info.get('vocab_size', 1000)
                embed_dim = feat_info.get('embed_dim', config.EMBEDDING_DIM)
                
                if self.pretrained_embeddings and feat_name in self.pretrained_embeddings:
                    pretrained_emb = self.pretrained_embeddings[feat_name]['embedding']
                    pretrained_linear = self.pretrained_embeddings[feat_name]['linear']
                    
                    self.embedding_layers[feat_name] = layers.Embedding(
                        input_dim=vocab_size,
                        output_dim=embed_dim,
                        embeddings_initializer=tf.constant_initializer(pretrained_emb),
                        trainable=True,
                        name=f'embedding_{feat_name}'
                    )
                    
                    self.linear_embeddings[feat_name] = layers.Embedding(
                        input_dim=vocab_size,
                        output_dim=1,
                        embeddings_initializer=tf.constant_initializer(pretrained_linear),
                        trainable=True,
                        name=f'linear_{feat_name}'
                    )
                else:
                    self.embedding_layers[feat_name] = layers.Embedding(
                        input_dim=vocab_size,
                        output_dim=embed_dim,
                        embeddings_initializer='glorot_uniform',
                        name=f'embedding_{feat_name}'
                    )
                    
                    self.linear_embeddings[feat_name] = layers.Embedding(
                        input_dim=vocab_size,
                        output_dim=1,
                        embeddings_initializer='glorot_uniform',
                        name=f'linear_{feat_name}'
                    )
            
            elif feat_info['type'] == 'dense':
                self.linear_embeddings[feat_name] = layers.Dense(
                    units=1,
                    use_bias=False,
                    name=f'linear_dense_{feat_name}'
                )
    
    def _build_fm_layers(self):
        self.fm_layer = FM()
        self.fm_bias = self.add_weight(
            shape=(1,),
            initializer='zeros',
            trainable=True,
            name='fm_bias'
        )
    
    def _build_dnn_layers(self):
        self.dnn_layers = []
        for i, units in enumerate(config.HIDDEN_UNITS):
            self.dnn_layers.append(layers.Dense(
                units=units,
                activation='relu',
                name=f'dnn_dense_{i}'
            ))
            self.dnn_layers.append(layers.BatchNormalization(name=f'dnn_bn_{i}'))
            self.dnn_layers.append(layers.Dropout(config.DROPOUT_RATE, name=f'dnn_dropout_{i}'))
    
    def _build_output_layer(self):
        if self.num_tasks == 1:
            self.output_layer = layers.Dense(
                units=1,
                activation='sigmoid',
                kernel_initializer='glorot_uniform',
                name='output'
            )
        else:
            self.output_layer = MultiTaskOutputLayer(
                num_tasks=self.num_tasks,
                name='multi_task_output'
            )
    
    def call(self, inputs, training=False):
        linear_terms = []
        fm_embeddings = []
        dnn_inputs = []
        
        for feat_name, feat_info in self.feature_spec.items():
            x = inputs[feat_name]
            
            if feat_info['type'] == 'categorical':
                embed = self.embedding_layers[feat_name](x)
                linear_term = self.linear_embeddings[feat_name](x)
                
                if len(embed.shape) == 3:
                    embed = tf.reduce_mean(embed, axis=1)
                    linear_term = tf.reduce_sum(linear_term, axis=1)
                elif len(embed.shape) == 4:
                    embed = tf.reshape(embed, [-1, embed.shape[1] * embed.shape[2], embed.shape[3]])
                    embed = tf.reduce_mean(embed, axis=1)
                    linear_term = tf.reduce_sum(linear_term, axis=[1, 2])
                
                fm_embeddings.append(tf.expand_dims(embed, axis=1))
                linear_terms.append(linear_term)
                dnn_inputs.append(embed)
            
            elif feat_info['type'] == 'dense':
                if len(x.shape) == 1:
                    x = tf.expand_dims(x, axis=-1)
                elif len(x.shape) > 2:
                    x = tf.reshape(x, [-1, x.shape[1]])
                
                linear_term = self.linear_embeddings[feat_name](x)
                linear_terms.append(linear_term)
                
                dnn_dense = layers.Dense(config.EMBEDDING_DIM, activation='relu')(x)
                fm_embeddings.append(tf.expand_dims(dnn_dense, axis=1))
                dnn_inputs.append(dnn_dense)
        
        linear_output = tf.add_n(linear_terms)
        
        fm_input = tf.concat(fm_embeddings, axis=1)
        fm_output = self.fm_layer(fm_input)
        
        dnn_output = tf.concat(dnn_inputs, axis=-1)
        for layer in self.dnn_layers:
            if isinstance(layer, layers.BatchNormalization) or isinstance(layer, layers.Dropout):
                dnn_output = layer(dnn_output, training=training)
            else:
                dnn_output = layer(dnn_output)
        
        concat_output = tf.concat([linear_output, fm_output, dnn_output], axis=-1)
        final_output = self.output_layer(concat_output)
        
        return final_output
    
    def freeze_fm_layers(self):
        for feat_name in self.embedding_layers.keys():
            self.embedding_layers[feat_name].trainable = False
            if feat_name in self.linear_embeddings:
                self.linear_embeddings[feat_name].trainable = False
    
    def unfreeze_fm_layers(self):
        for feat_name in self.embedding_layers.keys():
            self.embedding_layers[feat_name].trainable = True
            if feat_name in self.linear_embeddings:
                self.linear_embeddings[feat_name].trainable = True
    
    def online_train_step(self, features, labels, learning_rate=None):
        if learning_rate is None:
            learning_rate = config.ONLINE_LEARNING_RATE
        
        with tf.GradientTape() as tape:
            predictions = self(features, training=True)
            
            if self.num_tasks == 1:
                loss = tf.keras.losses.binary_crossentropy(labels, predictions)
            else:
                losses = []
                for i, target in enumerate(config.MULTI_TARGET):
                    weight = config.TARGET_WEIGHTS.get(target, 1.0)
                    target_loss = tf.keras.losses.binary_crossentropy(
                        labels[:, i:i+1], predictions[:, i:i+1]
                    )
                    losses.append(weight * target_loss)
                loss = tf.reduce_mean(losses)
        
        gradients = tape.gradient(loss, self.trainable_variables)
        optimizer = tf.keras.optimizers.SGD(learning_rate=learning_rate)
        optimizer.apply_gradients(zip(gradients, self.trainable_variables))
        
        return loss.numpy()


def build_feature_spec():
    feature_spec = {}
    
    feature_spec['title'] = {
        'type': 'categorical',
        'vocab_size': config.TITLE_VOCAB_SIZE,
        'embed_dim': config.EMBEDDING_DIM
    }
    
    feature_spec['tags'] = {
        'type': 'categorical',
        'vocab_size': config.TAGS_VOCAB_SIZE,
        'embed_dim': config.EMBEDDING_DIM
    }
    
    feature_spec['category'] = {
        'type': 'categorical',
        'vocab_size': len(config.VIDEO_CATEGORIES) + 1,
        'embed_dim': config.EMBEDDING_DIM
    }
    
    feature_spec['user_id'] = {
        'type': 'categorical',
        'vocab_size': 10000,
        'embed_dim': config.EMBEDDING_DIM
    }
    
    feature_spec['user_history'] = {
        'type': 'categorical',
        'vocab_size': config.USER_HISTORY_SIZE,
        'embed_dim': config.EMBEDDING_DIM
    }
    
    feature_spec['duration'] = {
        'type': 'dense'
    }
    
    feature_spec['cover'] = {
        'type': 'dense'
    }
    
    return feature_spec


def create_fm_model(num_tasks=1):
    feature_spec = build_feature_spec()
    model = FMOnlyModel(feature_spec, num_tasks=num_tasks)
    
    if num_tasks == 1:
        loss = 'binary_crossentropy'
    else:
        loss = weighted_binary_crossentropy
    
    model.compile(
        optimizer=Adam(learning_rate=config.FM_LEARNING_RATE),
        loss=loss,
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    
    return model


def create_deepfm_model(pretrained_embeddings=None, num_tasks=1):
    feature_spec = build_feature_spec()
    model = DeepFM(feature_spec, pretrained_embeddings, num_tasks=num_tasks)
    
    if num_tasks == 1:
        loss = 'binary_crossentropy'
    else:
        loss = weighted_binary_crossentropy
    
    model.compile(
        optimizer=Adam(learning_rate=config.LEARNING_RATE),
        loss=loss,
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    
    return model


def weighted_binary_crossentropy(y_true, y_pred):
    losses = []
    for i, target in enumerate(config.MULTI_TARGET):
        weight = config.TARGET_WEIGHTS.get(target, 1.0)
        target_loss = tf.keras.losses.binary_crossentropy(
            y_true[:, i:i+1], y_pred[:, i:i+1]
        )
        losses.append(weight * target_loss)
    return tf.reduce_mean(losses)


def save_model(model, path, model_type='deepfm'):
    os.makedirs(path, exist_ok=True)
    model.save_weights(os.path.join(path, f'{model_type}_weights'))
    print(f"Model saved to {path}")


def load_model(model_path, model_type='deepfm', num_tasks=1):
    feature_spec = build_feature_spec()
    
    if model_type == 'fm':
        model = FMOnlyModel(feature_spec, num_tasks=num_tasks)
    else:
        model = DeepFM(feature_spec, num_tasks=num_tasks)
    
    model.load_weights(os.path.join(model_path, f'{model_type}_weights')).expect_partial()
    
    if num_tasks == 1:
        loss = 'binary_crossentropy'
    else:
        loss = weighted_binary_crossentropy
    
    model.compile(
        optimizer=Adam(learning_rate=config.LEARNING_RATE),
        loss=loss,
        metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]
    )
    
    print(f"Model loaded from {model_path}")
    return model


def predict_multi_target(model, features):
    predictions = model.predict(features, verbose=0)
    
    if model.num_tasks == 1:
        return {'click': predictions.flatten()}
    
    results = {}
    for i, target in enumerate(config.MULTI_TARGET):
        results[target] = predictions[:, i].flatten()
    return results


def rank_videos(model, user_features, video_features_list, target='click'):
    scores = []
    
    for video_features in video_features_list:
        combined_features = {}
        combined_features.update(user_features)
        combined_features.update(video_features)
        
        for k, v in combined_features.items():
            if isinstance(v, np.ndarray):
                combined_features[k] = np.expand_dims(v, axis=0)
            else:
                combined_features[k] = np.array([v])
        
        predictions = predict_multi_target(model, combined_features)
        score = predictions.get(target, predictions.get('click', [0]))[0]
        scores.append(score)
    
    ranked_indices = np.argsort(scores)[::-1]
    return ranked_indices, scores
