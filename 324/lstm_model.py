import os
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from config import LSTM_PARAMS, TIME_GATE_PARAMS, MODEL_DIR, RANDOM_SEED, MAX_EPISODES
from utils import calculate_rmse, calculate_mape, create_time_sequences
from data_generator import generate_historical_dramas, generate_social_media_data

np.random.seed(RANDOM_SEED)

try:
    import tensorflow as tf
    from tensorflow.keras.models import Model, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional, Input, Concatenate, Activation, Multiply, Add, Lambda
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
    from tensorflow.keras import backend as K
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. LSTM model will use fallback implementation.")

def create_time_interval_gate(prev_state, time_interval, params=TIME_GATE_PARAMS):
    """
    时间间隔门（Time Interval Gate）- 核心创新机制
    
    原理：
    1. 根据时间间隔计算历史信息的衰减因子
    2. 长期间隔 → 历史信息影响衰减
    3. 可学习衰减率，适应不同数据模式
    
    数学表达：
    decay_gate = sigmoid(W_t * Δt + b_t)
    h_t_new = decay_gate * h_t_prev + (1 - decay_gate) * h_t_candidate
    
    参数：
    - time_interval: 时间间隔（天数）
    - use_trainable_decay: 是否学习衰减率
    - interval_scaling: 'log' 或 'linear'
    """
    max_interval = params['max_interval_days']
    
    if params['interval_scaling'] == 'log':
        scaled_interval = tf.math.log(time_interval + 1.0) / tf.math.log(max_interval + 1.0)
    else:
        scaled_interval = time_interval / max_interval
    
    scaled_interval = tf.clip_by_value(scaled_interval, 0.0, 1.0)
    
    if TENSORFLOW_AVAILABLE and params['use_trainable_decay']:
        decay_gate = Dense(
            units=prev_state.shape[-1],
            activation='sigmoid',
            kernel_initializer='glorot_uniform',
            bias_initializer='zeros',
            name='time_gate_dense'
        )(scaled_interval)
        
        decay_rate = params['time_decay_rate']
        decay_gate = decay_gate * (1.0 - decay_rate) + decay_rate
        
        forget_gate = Dense(
            units=prev_state.shape[-1],
            activation='sigmoid',
            name='time_forget_gate'
        )(Concatenate()([prev_state, scaled_interval]))
        
        update_gate = Dense(
            units=prev_state.shape[-1],
            activation='sigmoid',
            name='time_update_gate'
        )(Concatenate()([prev_state, scaled_interval]))
        
        new_state = forget_gate * prev_state + update_gate * (1 - prev_state)
    else:
        decay_rate = params['time_decay_rate']
        decay_factor = tf.exp(-decay_rate * scaled_interval)
        new_state = prev_state * decay_factor
    
    return new_state

class TimeIntervalLSTM:
    """
    带时间间隔门的LSTM模型
    
    创新点：
    1. 时间间隔感知：显式建模相邻观测之间的时间间隔
    2. 自适应衰减：根据间隔长度自动调节历史信息的影响
    3. 可学习参数：衰减率可从数据中学习，而非人工固定
    4. 多尺度处理：对不同长度的间隔有不同的处理策略
    """
    
    def __init__(self, seq_length=5, params=None, time_gate_params=None):
        self.seq_length = seq_length
        self.params = params or LSTM_PARAMS
        self.time_gate_params = time_gate_params or TIME_GATE_PARAMS
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model_path = os.path.join(MODEL_DIR, 'time_gate_lstm_model.h5')
        self.scaler_path = os.path.join(MODEL_DIR, 'time_gate_lstm_scaler.pkl')
        self.tensorflow_available = TENSORFLOW_AVAILABLE
        self.fallback_coefficients = None
        self.time_gate_weights = None
    
    def _prepare_time_intervals(self, dates):
        """计算时间间隔"""
        intervals = np.zeros(len(dates))
        for i in range(1, len(dates)):
            intervals[i] = (dates[i] - dates[i-1]).days
        
        intervals = np.clip(intervals, 0, self.time_gate_params['max_interval_days'])
        return intervals
    
    def _prepare_training_data_with_time_gate(self, dramas_data, augment_features=True):
        """准备带时间间隔门的训练数据"""
        all_sequences = []
        all_intervals = []
        all_targets = []
        
        for drama in dramas_data:
            ratings = np.array(drama['ratings'])
            social_df = drama['social_data']
            dates = drama['dates']
            n = len(ratings)
            
            if n < self.seq_length + 1:
                continue
            
            intervals = self._prepare_time_intervals(dates)
            
            features = []
            for i in range(n):
                feature_vec = [ratings[i]]
                
                if augment_features:
                    social_features = [
                        social_df.iloc[i]['post_volume'],
                        social_df.iloc[i]['repost_volume'],
                        social_df.iloc[i]['like_volume'],
                        social_df.iloc[i]['comment_volume'],
                        social_df.iloc[i]['search_index'],
                        social_df.iloc[i]['sentiment_score'],
                        dates[i].weekday(),
                        1 if dates[i].weekday() >= 5 else 0,
                        i + 1,
                        drama['info']['num_episodes'],
                        intervals[i]
                    ]
                    feature_vec.extend(social_features)
                
                features.append(feature_vec)
            
            features = np.array(features, dtype=np.float64)
            normalized_features = np.zeros_like(features)
            
            for j in range(features.shape[1]):
                col = features[:, j]
                if np.std(col) > 0:
                    normalized_features[:, j] = (col - np.min(col)) / (np.max(col) - np.min(col) + 1e-8)
            
            X_seq, y_seq = create_time_sequences(normalized_features, self.seq_length)
            
            interval_seq = []
            for i in range(len(X_seq)):
                interval_seq.append(intervals[i:i+self.seq_length])
            
            all_sequences.extend(X_seq)
            all_intervals.extend(interval_seq)
            all_targets.extend(y_seq[:, 0])
        
        X = np.array(all_sequences)
        X_intervals = np.array(all_intervals).reshape(-1, self.seq_length, 1)
        y = np.array(all_targets)
        
        return X, X_intervals, y
    
    def _build_time_gate_lstm_model(self, input_shape, interval_shape):
        """构建带时间间隔门的LSTM模型"""
        if not self.tensorflow_available:
            return None
        
        main_input = Input(shape=input_shape, name='main_features')
        interval_input = Input(shape=interval_shape, name='time_intervals')
        
        x = Bidirectional(LSTM(
            units=self.params['units'],
            return_sequences=True,
            dropout=self.params['dropout'],
            recurrent_dropout=self.params.get('recurrent_dropout', 0.1)
        ), name='bidir_lstm_1')(main_input)
        
        x = LSTM(
            units=self.params['units'] // 2,
            return_sequences=True,
            dropout=self.params['dropout'],
            name='lstm_2'
        )(x)
        
        time_gate = Dense(self.params['units'] // 2, activation='sigmoid', name='time_gate')(
            Concatenate(axis=-1)([x, interval_input])
        )
        
        time_decay = Lambda(
            lambda t: tf.exp(-self.time_gate_params['time_decay_rate'] * t),
            name='time_decay'
        )(interval_input)
        
        time_decay = Dense(self.params['units'] // 2, activation='sigmoid', name='decay_projection')(time_decay)
        
        gated_x = Multiply(name='time_gated_features')([x, time_gate])
        decayed_x = Multiply(name='time_decayed_features')([gated_x, time_decay])
        
        combined = Add(name='combine_gated')([x, decayed_x])
        
        x = LSTM(
            units=self.params['units'] // 4,
            return_sequences=False,
            dropout=self.params['dropout'],
            name='lstm_3'
        )(combined)
        
        x = Dropout(self.params['dropout'], name='dropout_1')(x)
        
        interval_flat = Lambda(lambda t: tf.reduce_mean(t, axis=1), name='interval_mean')(interval_input)
        x = Concatenate(name='concat_interval')([x, interval_flat])
        
        x = Dense(units=64, activation='relu', name='dense_1')(x)
        x = Dropout(self.params['dropout'], name='dropout_2')(x)
        x = Dense(units=32, activation='relu', name='dense_2')(x)
        x = Dense(units=16, activation='relu', name='dense_3')(x)
        
        output = Dense(units=1, activation='linear', name='output')(x)
        
        model = Model(inputs=[main_input, interval_input], outputs=output, name='TimeIntervalLSTM')
        
        optimizer = Adam(learning_rate=0.001)
        model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        
        return model
    
    def train(self, num_dramas=100, epochs=None):
        epochs = epochs or self.params['epochs']
        
        print(f"Generating {num_dramas} historical dramas for Time-Interval LSTM training...")
        dramas_data = generate_historical_dramas(num_dramas)
        
        print("Preparing time sequences with interval gates...")
        X, X_intervals, y = self._prepare_training_data_with_time_gate(dramas_data)
        
        print(f"Feature shape: {X.shape}, Interval shape: {X_intervals.shape}, Target shape: {y.shape}")
        
        if X.shape[0] == 0:
            print("Not enough data for training.")
            return None
        
        X_train, X_test, X_int_train, X_int_test, y_train, y_test = train_test_split(
            X, X_intervals, y, test_size=0.2, random_state=RANDOM_SEED
        )
        
        if self.tensorflow_available:
            print("Building Time-Interval LSTM model...")
            self.model = self._build_time_gate_lstm_model(X_train.shape[1:], X_int_train.shape[1:])
            
            early_stopping = EarlyStopping(
                monitor='val_loss', patience=10, restore_best_weights=True
            )
            checkpoint = ModelCheckpoint(
                self.model_path, monitor='val_loss', save_best_only=True
            )
            
            print("Training Time-Interval LSTM model...")
            history = self.model.fit(
                [X_train, X_int_train], y_train,
                epochs=epochs,
                batch_size=self.params['batch_size'],
                validation_split=self.params['validation_split'],
                callbacks=[early_stopping, checkpoint],
                verbose=1
            )
            
            y_pred = self.model.predict([X_test, X_int_test], verbose=0).flatten()
            
            self.save()
            
            return {
                'history': history.history,
                'y_true': y_test,
                'y_pred': y_pred,
                'rmse': calculate_rmse(y_test, y_pred),
                'mape': calculate_mape(y_test, y_pred)
            }
        else:
            print("Using fallback Time-Interval LSTM implementation...")
            self._train_fallback(X_train, y_train)
            
            y_pred = self._predict_fallback(X_test)
            
            self.save()
            
            return {
                'y_true': y_test,
                'y_pred': y_pred,
                'rmse': calculate_rmse(y_test, y_pred),
                'mape': calculate_mape(y_test, y_pred)
            }
    
    def _train_fallback(self, X_train, y_train):
        X_flat = X_train.reshape(X_train.shape[0], -1)
        
        ones = np.ones((X_flat.shape[0], 1))
        X_aug = np.hstack([X_flat, ones])
        
        try:
            self.fallback_coefficients = np.linalg.lstsq(X_aug, y_train, rcond=None)[0]
        except:
            self.fallback_coefficients = np.zeros(X_aug.shape[1])
            self.fallback_coefficients[-1] = np.mean(y_train)
    
    def _predict_fallback(self, X):
        if self.fallback_coefficients is None:
            return np.zeros(X.shape[0])
        
        X_flat = X.reshape(X.shape[0], -1)
        ones = np.ones((X_flat.shape[0], 1))
        X_aug = np.hstack([X_flat, ones])
        
        return X_aug @ self.fallback_coefficients
    
    def predict(self, drama_info, dates, known_ratings, social_df, episode_idx):
        if self.model is None and self.fallback_coefficients is None:
            self.load()
        
        n = len(known_ratings)
        intervals = self._prepare_time_intervals(dates)
        
        if n < self.seq_length:
            padded = np.zeros(self.seq_length)
            padded[-n:] = known_ratings if n > 0 else []
            recent_ratings = padded
            padded_intervals = np.ones(self.seq_length)
            if n > 0:
                padded_intervals[-n:] = intervals[:min(n, len(intervals))]
        else:
            recent_ratings = known_ratings[-self.seq_length:]
            start_idx = max(0, n - self.seq_length)
            end_idx = min(n, len(intervals))
            padded_intervals = intervals[start_idx:end_idx]
            if len(padded_intervals) < self.seq_length:
                padding = np.ones(self.seq_length - len(padded_intervals))
                padded_intervals = np.concatenate([padding, padded_intervals])
        
        features_seq = []
        for i in range(self.seq_length):
            actual_idx = max(0, n - self.seq_length + i)
            
            feature_vec = [recent_ratings[i]]
            
            if actual_idx < len(social_df):
                social_features = [
                    social_df.iloc[actual_idx]['post_volume'],
                    social_df.iloc[actual_idx]['repost_volume'],
                    social_df.iloc[actual_idx]['like_volume'],
                    social_df.iloc[actual_idx]['comment_volume'],
                    social_df.iloc[actual_idx]['search_index'],
                    social_df.iloc[actual_idx]['sentiment_score'],
                    dates[actual_idx].weekday(),
                    1 if dates[actual_idx].weekday() >= 5 else 0,
                    actual_idx + 1,
                    drama_info['num_episodes'],
                    padded_intervals[i]
                ]
                feature_vec.extend(social_features)
            else:
                feature_vec.extend([0] * 11)
            
            features_seq.append(feature_vec)
        
        features_seq = np.array(features_seq, dtype=np.float64)
        
        normalized = np.zeros_like(features_seq)
        for j in range(features_seq.shape[1]):
            col = features_seq[:, j]
            if np.std(col) > 0:
                normalized[:, j] = (col - np.min(col)) / (np.max(col) - np.min(col) + 1e-8)
        
        X = normalized.reshape(1, self.seq_length, -1)
        X_interval = padded_intervals.reshape(1, self.seq_length, 1)
        
        if self.tensorflow_available and self.model is not None:
            pred_norm = self.model.predict([X, X_interval], verbose=0)[0][0]
        else:
            pred_norm = self._predict_fallback(X)[0]
        
        all_ratings = np.array(known_ratings)
        if len(all_ratings) > 1 and np.std(all_ratings) > 0:
            pred_denorm = pred_norm * (np.max(all_ratings) - np.min(all_ratings)) + np.min(all_ratings)
        else:
            pred_denorm = pred_norm * 2.0
        
        current_interval = intervals[min(episode_idx, len(intervals)-1)] if episode_idx < len(intervals) else 1
        time_decay = np.exp(-self.time_gate_params['time_decay_rate'] * current_interval)
        pred_denorm = pred_denorm * (0.8 + 0.2 * time_decay)
        
        trend = 0
        if len(known_ratings) >= 3:
            recent = known_ratings[-3:]
            trend = np.polyfit(range(len(recent)), recent, 1)[0] * 0.1
        
        final_pred = pred_denorm + trend
        return max(0.1, min(8.0, final_pred))
    
    def predict_all_episodes(self, drama_info, dates, initial_ratings, social_df):
        n = len(dates)
        predictions = []
        known_ratings = list(initial_ratings)
        
        for i in range(n):
            if i < len(initial_ratings):
                pred = initial_ratings[i]
            else:
                pred = self.predict(drama_info, dates, known_ratings, social_df, i)
            
            predictions.append(pred)
            known_ratings.append(pred)
        
        return predictions
    
    def get_time_gate_effect(self, intervals):
        """计算不同时间间隔的门控效果"""
        decay_rate = self.time_gate_params['time_decay_rate']
        effects = []
        
        for interval in intervals:
            if self.time_gate_params['interval_scaling'] == 'log':
                scaled = np.log(interval + 1) / np.log(self.time_gate_params['max_interval_days'] + 1)
            else:
                scaled = interval / self.time_gate_params['max_interval_days']
            
            effect = np.exp(-decay_rate * scaled)
            effects.append({
                'interval_days': interval,
                'scaled_interval': scaled,
                'decay_effect': effect,
                'information_retention': effect * 100
            })
        
        return pd.DataFrame(effects)
    
    def save(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        if self.tensorflow_available and self.model is not None:
            self.model.save(self.model_path)
        
        with open(self.scaler_path, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'fallback_coefficients': self.fallback_coefficients,
                'seq_length': self.seq_length,
                'time_gate_params': self.time_gate_params
            }, f)
        
        print(f"Time-Interval LSTM model saved.")
    
    def load(self):
        if not os.path.exists(self.scaler_path):
            print("Time-Interval LSTM model not found, training a new model...")
            self.train(num_dramas=30)
            return
        
        with open(self.scaler_path, 'rb') as f:
            data = pickle.load(f)
            self.scaler = data['scaler']
            self.fallback_coefficients = data['fallback_coefficients']
            self.seq_length = data['seq_length']
            if 'time_gate_params' in data:
                self.time_gate_params = data['time_gate_params']
        
        if self.tensorflow_available and os.path.exists(self.model_path):
            self.model = load_model(self.model_path, compile=False)
            print(f"Time-Interval LSTM TensorFlow model loaded from {self.model_path}")
        else:
            print("Using fallback Time-Interval LSTM implementation.")
    
    def is_trained(self):
        return self.model is not None or self.fallback_coefficients is not None

if __name__ == '__main__':
    print("Testing Time-Interval LSTM model...")
    predictor = TimeIntervalLSTM(seq_length=5)
    
    intervals_to_test = [1, 2, 3, 5, 7, 14, 30]
    gate_effects = predictor.get_time_gate_effect(intervals_to_test)
    print("\nTime Gate Effects (不同时间间隔的信息保留率):")
    print(gate_effects.to_string(index=False))
    
    eval_results = predictor.train(num_dramas=20, epochs=15)
    
    if eval_results and 'rmse' in eval_results:
        print(f"\nTime-Interval LSTM Evaluation:")
        print(f"  RMSE: {eval_results['rmse']:.4f}")
        print(f"  MAPE: {eval_results['mape']:.2f}%")
    
    from data_generator import generate_drama_basic_info, generate_episodic_ratings
    
    test_drama = generate_drama_basic_info('TEST002')
    dates, ratings = generate_episodic_ratings(test_drama)
    social_df = generate_social_media_data(test_drama, dates, ratings)
    
    n_known = 10
    known_ratings = ratings[:n_known]
    
    predictions = predictor.predict_all_episodes(test_drama, dates, known_ratings, social_df)
    
    print(f"\nTime-Interval LSTM Predictions for {test_drama['drama_name']}:")
    for i, (date, true, pred) in enumerate(zip(dates, ratings, predictions)):
        status = " (known)" if i < n_known else " (predicted)"
        print(f"  Ep{i+1:2d} ({date.strftime('%Y-%m-%d')}): True={true:.3f}, Pred={pred:.3f}{status}")
