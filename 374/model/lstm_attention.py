import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Model
from tensorflow.keras.layers import (LSTM, Dense, Input, Attention, Concatenate,
                                      Flatten, Layer)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import tensorflow as tf
import warnings
warnings.filterwarnings('ignore')


class SinusoidalPositionalEncoding(Layer):
    def __init__(self, max_len=500, **kwargs):
        super(SinusoidalPositionalEncoding, self).__init__(**kwargs)
        self.max_len = max_len

    def build(self, input_shape):
        d_model = input_shape[-1]
        position = np.arange(self.max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        pe = np.zeros((self.max_len, d_model))
        pe[:, 0::2] = np.sin(position * div_term)
        if d_model % 2 == 1:
            pe[:, 1::2] = np.cos(position * div_term[:-1])
        else:
            pe[:, 1::2] = np.cos(position * div_term)
        self.pe = self.add_weight(
            name='positional_encoding',
            shape=(self.max_len, d_model),
            initializer=tf.keras.initializers.Constant(pe),
            trainable=False
        )
        super(SinusoidalPositionalEncoding, self).build(input_shape)

    def call(self, inputs):
        seq_len = tf.shape(inputs)[1]
        return inputs + self.pe[:seq_len, :]

    def get_config(self):
        config = super(SinusoidalPositionalEncoding, self).get_config()
        config.update({'max_len': self.max_len})
        return config


class LoadPredictor:
    def __init__(self, seq_length=168, pred_length=168):
        self.seq_length = seq_length
        self.pred_length = pred_length
        self.feature_scaler = MinMaxScaler()
        self.target_scaler = MinMaxScaler()
        self.model = None
        self.feature_names = None

    def prepare_features(self, df):
        df = df.copy()
        df['hour'] = df['timestamp'].dt.hour
        df['dayofweek'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month
        df['dayofyear'] = df['timestamp'].dt.dayofyear

        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['dow_sin'] = np.sin(2 * np.pi * df['dayofweek'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['dayofweek'] / 7)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

        existing_window_cols = ['is_pre_holiday', 'is_post_holiday',
                                'pre_holiday_decay', 'post_holiday_decay']
        has_window = all(c in df.columns for c in existing_window_cols)

        if not has_window:
            holiday_dates = df[df['is_holiday'] == 1]['timestamp'].dt.normalize().unique()
            holiday_set = set(pd.Timestamp(d) for d in holiday_dates)
            df['normalized_date'] = df['timestamp'].dt.normalize()

            def holiday_window_features(row_date):
                row_ts = pd.Timestamp(row_date)
                if holiday_set:
                    past_holidays = [h for h in holiday_set if h <= row_ts]
                    future_holidays = [h for h in holiday_set if h >= row_ts]
                    days_from_last = (row_ts - max(past_holidays)).days if past_holidays else 999
                    days_to_next = (min(future_holidays) - row_ts).days if future_holidays else 999
                    is_holiday = 1 if row_ts in holiday_set else 0
                    is_pre_holiday = 1 if (0 < days_to_next <= 3) and is_holiday == 0 else 0
                    is_post_holiday = 1 if (0 < days_from_last <= 3) and is_holiday == 0 else 0
                    pre_holiday_decay = max(0, 1 - days_to_next / 3) if days_to_next <= 3 else 0
                    post_holiday_decay = max(0, 1 - days_from_last / 3) if days_from_last <= 3 else 0
                    return pd.Series([is_pre_holiday, is_post_holiday,
                                      pre_holiday_decay, post_holiday_decay])
                return pd.Series([0, 0, 0, 0])

            window_feats = df['normalized_date'].apply(holiday_window_features)
            window_feats.columns = existing_window_cols
            df = pd.concat([df, window_feats], axis=1)

        feature_cols = ['temperature', 'humidity', 'is_holiday',
                        'is_pre_holiday', 'is_post_holiday',
                        'pre_holiday_decay', 'post_holiday_decay',
                        'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos',
                        'month_sin', 'month_cos']

        industry_cols = [c for c in df.columns if c.startswith('industry_')]
        feature_cols.extend(industry_cols)

        self.feature_names = feature_cols
        return df[feature_cols].values, df['load'].values

    def create_sequences(self, features, target):
        X, y = [], []
        for i in range(len(features) - self.seq_length - self.pred_length + 1):
            X.append(features[i:i + self.seq_length])
            y.append(target[i + self.seq_length:i + self.seq_length + self.pred_length])
        return np.array(X), np.array(y)

    def build_model(self, input_dim):
        encoder_inputs = Input(shape=(self.seq_length, input_dim))
        encoder_pe = SinusoidalPositionalEncoding(max_len=500)(encoder_inputs)
        encoder_lstm = LSTM(128, return_sequences=True, return_state=True)
        encoder_outputs, state_h, state_c = encoder_lstm(encoder_pe)

        decoder_inputs = Input(shape=(self.pred_length, input_dim))
        decoder_pe = SinusoidalPositionalEncoding(max_len=500)(decoder_inputs)
        decoder_lstm = LSTM(128, return_sequences=True)
        decoder_outputs = decoder_lstm(decoder_pe, initial_state=[state_h, state_c])

        attention = Attention(name='attention')
        context = attention([decoder_outputs, encoder_outputs])

        concat = Concatenate(axis=-1)([decoder_outputs, context])
        outputs = Dense(64, activation='relu')(concat)
        outputs = Dense(1)(outputs)
        outputs = Flatten()(outputs)

        model = Model(inputs=[encoder_inputs, decoder_inputs], outputs=outputs)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='huber_loss',
                       metrics=['mae', 'mse'])
        return model

    def train(self, df, epochs=50, batch_size=32):
        features, target = self.prepare_features(df)

        features_scaled = self.feature_scaler.fit_transform(features)
        target_scaled = self.target_scaler.fit_transform(target.reshape(-1, 1)).flatten()

        X, y = self.create_sequences(features_scaled, target_scaled)

        input_dim = features_scaled.shape[1]
        self.model = self.build_model(input_dim)

        X_enc = X
        X_dec = np.zeros((X.shape[0], self.pred_length, input_dim))
        for i in range(X.shape[0]):
            last_known = X[i, -1:, :]
            X_dec[i] = np.tile(last_known, (self.pred_length, 1))

        split_idx = int(len(X) * 0.8)
        X_enc_train, X_enc_val = X_enc[:split_idx], X_enc[split_idx:]
        X_dec_train, X_dec_val = X_dec[:split_idx], X_dec[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]

        early_stopping = EarlyStopping(monitor='val_loss', patience=10,
                                        restore_best_weights=True)
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                                       patience=5, min_lr=1e-6)

        history = self.model.fit(
            [X_enc_train, X_dec_train], y_train,
            validation_data=([X_enc_val, X_dec_val], y_val),
            epochs=epochs, batch_size=batch_size,
            callbacks=[early_stopping, reduce_lr],
            verbose=1
        )
        return history.history

    def predict(self, df_historical, df_future):
        features_hist, _ = self.prepare_features(df_historical)
        features_future, _ = self.prepare_features(df_future)

        features_hist_scaled = self.feature_scaler.transform(features_hist)
        features_future_scaled = self.feature_scaler.transform(features_future)

        encoder_input = features_hist_scaled[-self.seq_length:].reshape(1, self.seq_length, -1)
        decoder_input = features_future_scaled[:self.pred_length].reshape(1, self.pred_length, -1)

        pred_scaled = self.model.predict([encoder_input, decoder_input], verbose=0)
        pred = self.target_scaler.inverse_transform(pred_scaled).flatten()

        return pred

    def get_attention_weights(self, df_historical, df_future):
        features_hist, _ = self.prepare_features(df_historical)
        features_future, _ = self.prepare_features(df_future)

        features_hist_scaled = self.feature_scaler.transform(features_hist)
        features_future_scaled = self.feature_scaler.transform(features_future)

        encoder_input = features_hist_scaled[-self.seq_length:].reshape(1, self.seq_length, -1)
        decoder_input = features_future_scaled[:self.pred_length].reshape(1, self.pred_length, -1)

        attention_layer = self.model.get_layer('attention')
        attention_model = Model(inputs=self.model.input,
                                 outputs=attention_layer.output)
        weights = attention_model.predict([encoder_input, decoder_input], verbose=0)
        return weights[0]


def generate_sample_data(days=730):
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=days * 24, freq='h')

    hours = dates.hour
    dayofweek = dates.dayofweek
    month = dates.month

    daily_pattern = np.sin(2 * np.pi * hours / 24) * 0.3
    weekly_pattern = np.where(dayofweek < 5, 1.0, 0.7)
    seasonal_pattern = 0.2 * np.sin(2 * np.pi * month / 12)

    base_load = 5000
    temperature = 20 + 15 * np.sin(2 * np.pi * month / 12) + np.random.randn(len(dates)) * 3
    humidity = 50 + 10 * np.sin(2 * np.pi * month / 12) + np.random.randn(len(dates)) * 5

    temp_effect = (temperature - 20) * 10 * np.abs(temperature - 20) / 100
    humidity_effect = (humidity - 50) * 5

    holidays = pd.date_range('2024-01-01', periods=days, freq='d')
    holiday_set = set()
    for h in holidays:
        if h.month == 1 and h.day == 1:
            for i in range(24):
                holiday_set.add(h + pd.Timedelta(hours=i))
        if h.month == 10 and h.day == 1:
            for i in range(24):
                holiday_set.add(h + pd.Timedelta(hours=i))
        if h.month == 12 and h.day == 25:
            for i in range(24):
                holiday_set.add(h + pd.Timedelta(hours=i))

    is_holiday = np.array([1 if d in holiday_set else 0 for d in dates])

    normalized_dates = dates.normalize()
    unique_dates = np.unique(normalized_dates)
    holiday_dates_set = set()
    for d in unique_dates:
        if pd.Timestamp(d) in holiday_set:
            holiday_dates_set.add(pd.Timestamp(d).normalize())

    pre_holiday_effect = np.zeros(len(dates))
    post_holiday_effect = np.zeros(len(dates))
    for i, d in enumerate(dates):
        dn = pd.Timestamp(d).normalize()
        for hd in holiday_dates_set:
            delta = (hd - dn).days
            if 0 < delta <= 3:
                pre_holiday_effect[i] = (1 - delta / 3) * 300
                break
            if -3 <= delta < 0:
                post_holiday_effect[i] = (1 - abs(delta) / 3) * 400
                break

    holiday_effect = -is_holiday * 500 + pre_holiday_effect + post_holiday_effect

    solar_capacity_mw = 800
    pv_output = simulate_pv_output(dates, solar_capacity_mw, temperature)

    hvac_load = np.maximum(0, (temperature - 20) * 80) + np.random.randn(len(dates)) * 30
    lighting_load = np.where((hours >= 6) & (hours <= 8) | (hours >= 18) & (hours <= 22),
                             200 + np.random.randn(len(dates)) * 50,
                             20 + np.random.randn(len(dates)) * 10)
    appliance_load = 300 + np.random.randn(len(dates)) * 80 + np.where(dayofweek < 5, 50, -30)
    industrial_motor_load = np.where(dayofweek < 5, 700 + np.random.randn(len(dates)) * 100,
                                     100 + np.random.randn(len(dates)) * 30)
    ev_charging_load = np.where((hours >= 19) & (hours <= 23),
                                250 + np.random.randn(len(dates)) * 60,
                                np.where((hours >= 0) & (hours <= 6),
                                         150 + np.random.randn(len(dates)) * 40,
                                         20 + np.random.randn(len(dates)) * 10))

    other_load = base_load * (1 + seasonal_pattern + daily_pattern) \
                 + weekly_pattern * 300 + np.random.randn(len(dates)) * 50

    gross_load = (temp_effect + humidity_effect + holiday_effect
                  + hvac_load + lighting_load + appliance_load
                  + industrial_motor_load + ev_charging_load + other_load)
    gross_load = np.maximum(gross_load, 1000)

    net_load = gross_load - pv_output

    industry_residential = hvac_load + lighting_load + appliance_load
    industry_commercial = np.where(dayofweek < 5, 1.0, 0.3) * np.random.randn(len(dates)) * 100 + 300
    industry_industrial = industrial_motor_load

    df = pd.DataFrame({
        'timestamp': dates,
        'load': net_load,
        'gross_load': gross_load,
        'pv_output': pv_output,
        'temperature': temperature,
        'humidity': humidity,
        'is_holiday': is_holiday,
        'hvac_load': hvac_load,
        'lighting_load': lighting_load,
        'appliance_load': appliance_load,
        'industrial_motor_load': industrial_motor_load,
        'ev_charging_load': ev_charging_load,
        'industry_residential': industry_residential,
        'industry_commercial': industry_commercial,
        'industry_industrial': industry_industrial
    })
    return df


def simulate_pv_output(timestamps, capacity_mw=500, temperature=None):
    hours = timestamps.hour.values
    doy = timestamps.dayofyear.values

    declination = 23.45 * np.sin(2 * np.pi * (284 + doy) / 365)
    hour_angle = 15 * (hours - 12)

    lat_rad = np.radians(35.0)
    dec_rad = np.radians(declination)
    ha_rad = np.radians(hour_angle)

    cos_zenith = (np.sin(lat_rad) * np.sin(dec_rad)
                  + np.cos(lat_rad) * np.cos(dec_rad) * np.cos(ha_rad))
    cos_zenith = np.maximum(cos_zenith, 0)

    clear_sky_irradiance = cos_zenith * 1000
    clear_sky_irradiance[cos_zenith <= 0] = 0

    daily_cloud_factor = np.random.uniform(0.4, 1.0, size=len(timestamps) // 24 + 1)
    cloud_factor = np.repeat(daily_cloud_factor, 24)[:len(timestamps)]
    cloud_factor += np.random.randn(len(timestamps)) * 0.1
    cloud_factor = np.clip(cloud_factor, 0.1, 1.0)

    ghi = clear_sky_irradiance * cloud_factor

    if temperature is not None:
        temp_factor = 1 - 0.005 * (temperature - 25)
    else:
        temp_factor = 1.0

    pv_efficiency = 0.22 * temp_factor
    module_area = capacity_mw * 1e6 / (1000 * pv_efficiency)
    pv_output = ghi * module_area * pv_efficiency / 1e6

    np.random.seed(42)
    pv_output += np.random.randn(len(pv_output)) * 0.02 * capacity_mw
    pv_output = np.maximum(pv_output, 0)

    return pv_output


def decompose_load(total_load, temperature, hour, dayofweek, timestamps):
    """
    非侵入式负荷分解(NILM) - 从总负荷中识别各类用电设备占比
    """
    n = len(total_load)

    hvac = np.maximum(0, (temperature - 20) * 70) \
           + np.where(hour >= 9, 1.2, 0.8) * np.maximum(0, (temperature - 20) * 10)
    hvac = np.maximum(hvac, 0)

    lighting = np.zeros(n)
    morning_mask = (hour >= 6) & (hour <= 8)
    evening_mask = (hour >= 18) & (hour <= 22)
    lighting[morning_mask] = 280 + np.random.randn(sum(morning_mask)) * 40
    lighting[evening_mask] = 420 + np.random.randn(sum(evening_mask)) * 50
    lighting[~(morning_mask | evening_mask)] = 30 + np.random.randn(n - sum(morning_mask) - sum(evening_mask)) * 8

    weekday_mask = dayofweek < 5
    industrial = np.zeros(n)
    industrial[weekday_mask] = 750 + np.random.randn(sum(weekday_mask)) * 120
    industrial[~weekday_mask] = 120 + np.random.randn(n - sum(weekday_mask)) * 40
    industrial[(hour < 8) | (hour > 18)] *= 0.3

    ev = np.zeros(n)
    ev_home_mask = (hour >= 19) & (hour <= 23)
    ev_overnight_mask = (hour >= 0) & (hour <= 6)
    ev_peak_mask = (hour >= 10) & (hour <= 14)
    ev[ev_home_mask] = 300 + np.random.randn(sum(ev_home_mask)) * 70
    ev[ev_overnight_mask] = 180 + np.random.randn(sum(ev_overnight_mask)) * 45
    ev[ev_peak_mask] = 120 + np.random.randn(sum(ev_peak_mask)) * 30

    appliance = np.zeros(n)
    appliance_mask = (hour >= 7) & (hour <= 23)
    appliance[appliance_mask] = 380 + np.random.randn(sum(appliance_mask)) * 90
    appliance[~appliance_mask] = 80 + np.random.randn(n - sum(appliance_mask)) * 25
    appliance[weekday_mask] *= 0.9

    residual = total_load - (hvac + lighting + industrial + ev + appliance)
    residual = np.maximum(residual, 0)

    components = pd.DataFrame({
        'timestamp': timestamps,
        'hvac': hvac,
        'lighting': lighting,
        'industrial_motor': industrial,
        'ev_charging': ev,
        'home_appliance': appliance,
        'other': residual
    })

    component_sums = components[['hvac', 'lighting', 'industrial_motor',
                                  'ev_charging', 'home_appliance', 'other']].sum()
    total = component_sums.sum()
    percentages = (component_sums / total * 100).round(2)

    breakdown = [
        {'component': '空调采暖', 'load': float(component_sums['hvac']),
         'percentage': float(percentages['hvac']),
         'description': '制冷与采暖设备，占比最大，与温度强相关'},
        {'component': '照明系统', 'load': float(component_sums['lighting']),
         'percentage': float(percentages['lighting']),
         'description': '商业与居民照明，早晚高峰特征明显'},
        {'component': '工业电机', 'load': float(component_sums['industrial_motor']),
         'percentage': float(percentages['industrial_motor']),
         'description': '工业生产设备，工作日8-18点为主要时段'},
        {'component': '电动汽车', 'load': float(component_sums['ev_charging']),
         'percentage': float(percentages['ev_charging']),
         'description': 'EV充电负荷，夜间与午间为充电高峰'},
        {'component': '家用电器', 'load': float(component_sums['home_appliance']),
         'percentage': float(percentages['home_appliance']),
         'description': '家电、办公设备等常规用电'},
        {'component': '其他负荷', 'load': float(component_sums['other']),
         'percentage': float(percentages['other']),
         'description': '未识别的其他用电负荷'}
    ]

    hourly_profile = {}
    for h in range(24):
        mask = hour == h
        if mask.any():
            hourly_profile[str(h)] = {
                'hvac': float(hvac[mask].mean()),
                'lighting': float(lighting[mask].mean()),
                'industrial_motor': float(industrial[mask].mean()),
                'ev_charging': float(ev[mask].mean()),
                'home_appliance': float(appliance[mask].mean())
            }

    return components, breakdown, hourly_profile


def evaluate_demand_response(predictions, df_historical, df_future,
                              pv_forecast=None, hourly_profile=None):
    """
    需求响应潜力评估 - 计算削峰填谷的调节空间
    """
    analysis = {}

    avg_load = np.mean(predictions)
    peak_load = np.max(predictions)
    valley_load = np.min(predictions)

    peak_valley_diff = peak_load - valley_load
    peak_valley_ratio = peak_load / valley_load if valley_load > 0 else 0

    analysis['peak_valley_diff'] = float(peak_valley_diff)
    analysis['peak_valley_ratio'] = float(peak_valley_ratio)
    analysis['peak_load'] = float(peak_load)
    analysis['valley_load'] = float(valley_load)
    analysis['avg_load'] = float(avg_load)

    peak_hours_idx = np.where(predictions > avg_load * 1.1)[0]
    valley_hours_idx = np.where(predictions < avg_load * 0.9)[0]

    peak_hours_load = predictions[peak_hours_idx]
    valley_hours_load = predictions[valley_hours_idx]

    peak_reduction_potential = float(np.sum(peak_hours_load - avg_load * 1.05))
    valley_increase_potential = float(np.sum(avg_load * 0.95 - valley_hours_load))

    analysis['peak_shave_potential'] = float(peak_reduction_potential)
    analysis['valley_fill_potential'] = float(valley_increase_potential)
    analysis['peak_shave_count'] = int(len(peak_hours_idx))
    analysis['valley_fill_count'] = int(len(valley_hours_idx))

    dr_strategies = []

    if len(peak_hours_idx) > 0:
        peak_times = df_future.iloc[peak_hours_idx]['timestamp']
        peak_hour_list = peak_times.dt.hour.value_counts().head(3).index.tolist()
        dr_strategies.append({
            'type': 'peak_shaving',
            'name': '高峰削减',
            'target_hours': [int(h) for h in peak_hour_list],
            'potential_mw': float(np.mean(peak_hours_load - avg_load * 1.05)),
            'total_reduction_mwh': float(peak_reduction_potential),
            'economic_saving': float(peak_reduction_potential * 1.2),
            'measures': ['工业错峰生产', '空调温度上调', '非关键负荷暂停', '储能放电']
        })

    if len(valley_hours_idx) > 0:
        valley_times = df_future.iloc[valley_hours_idx]['timestamp']
        valley_hour_list = valley_times.dt.hour.value_counts().head(3).index.tolist()
        dr_strategies.append({
            'type': 'valley_filling',
            'name': '填谷',
            'target_hours': [int(h) for h in valley_hour_list],
            'potential_mw': float(np.mean(avg_load * 0.95 - valley_hours_load)),
            'total_increase_mwh': float(valley_increase_potential),
            'economic_benefit': float(valley_increase_potential * 0.6),
            'measures': ['电动汽车充电调度', '储能充电', '可平移负荷转移']
        })

    if pv_forecast is not None:
        surplus_idx = np.where((pv_forecast > 300) & (predictions < avg_load * 1.0))[0]
        if len(surplus_idx) > 0:
            surplus_pv = float(np.sum(pv_forecast[surplus_idx] * 0.3))
            dr_strategies.append({
                'type': 'pv_local_consumption',
                'name': '光伏就地消纳',
                'target_hours': [10, 11, 12, 13, 14],
                'potential_mw': float(np.mean(pv_forecast[surplus_idx] * 0.3)),
                'total_consumption_mwh': surplus_pv,
                'economic_benefit': float(surplus_pv * 0.8),
                'measures': ['制氢负荷启动', '储能充电', '可中断负荷转移']
            })

    total_dr_potential = peak_reduction_potential + valley_increase_potential
    if total_dr_potential > peak_load * 0.3:
        dr_level = 'excellent'
    elif total_dr_potential > peak_load * 0.15:
        dr_level = 'good'
    else:
        dr_level = 'limited'

    analysis['dr_level'] = dr_level
    analysis['total_dr_potential_mwh'] = float(total_dr_potential)
    analysis['strategies'] = dr_strategies

    if hourly_profile:
        weekday_profile = hourly_profile
        flexible_loads = ['ev_charging', 'home_appliance', 'hvac']
        flexibility_by_hour = {}
        for h in range(24):
            if str(h) in weekday_profile:
                hp = weekday_profile[str(h)]
                total_flex = sum(hp.get(f, 0) for f in flexible_loads)
                total_load = sum(hp.values())
                flexibility_by_hour[str(h)] = float(total_flex / total_load * 100) if total_load > 0 else 0
        analysis['flexibility_by_hour'] = flexibility_by_hour

    return analysis