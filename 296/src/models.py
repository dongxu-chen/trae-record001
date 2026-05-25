import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sktime.forecasting.arima import ARIMA
from sktime.forecasting.base import ForecastingHorizon
from prophet import Prophet
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import warnings
warnings.filterwarnings('ignore')


class BaseForecaster:
    def __init__(self):
        self.model = None
        self.model_name = 'Base'

    def fit(self, y_train, X_train=None):
        raise NotImplementedError

    def predict(self, horizon, X_test=None):
        raise NotImplementedError

    def evaluate(self, y_true, y_pred):
        metrics = {
            'mae': mean_absolute_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mape': mean_absolute_percentage_error(y_true, y_pred) * 100
        }
        return metrics


class ARIMAForecaster(BaseForecaster):
    def __init__(self, order=(1, 1, 1), seasonal_order=(0, 0, 0, 0)):
        super().__init__()
        self.order = order
        self.seasonal_order = seasonal_order
        self.model_name = 'ARIMA'

    def fit(self, y_train, X_train=None):
        if not isinstance(y_train.index, pd.DatetimeIndex):
            y_train.index = pd.to_datetime(y_train.index)
        y_train = y_train.asfreq(y_train.index.inferred_freq)
        
        self.model = ARIMA(
            order=self.order,
            seasonal_order=self.seasonal_order,
            suppress_warnings=True
        )
        self.model.fit(y_train, X=X_train)
        return self

    def predict(self, horizon, X_test=None):
        fh = ForecastingHorizon(np.arange(1, horizon + 1), is_relative=True)
        forecast = self.model.predict(fh=fh, X=X_test)
        return forecast.values


class ProphetForecaster(BaseForecaster):
    def __init__(self, yearly_seasonality=True, weekly_seasonality=True,
                 daily_seasonality=True, changepoint_prior_scale=0.05):
        super().__init__()
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.changepoint_prior_scale = changepoint_prior_scale
        self.model_name = 'Prophet'
        self.freq = None

    def fit(self, y_train, X_train=None):
        df_train = pd.DataFrame({
            'ds': y_train.index,
            'y': y_train.values
        })
        self.freq = pd.infer_freq(y_train.index)

        self.model = Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            changepoint_prior_scale=self.changepoint_prior_scale
        )
        self.model.fit(df_train)
        return self

    def predict(self, horizon, X_test=None):
        future = self.model.make_future_dataframe(
            periods=horizon,
            freq=self.freq
        )
        forecast = self.model.predict(future)
        return forecast['yhat'].tail(horizon).values


class XGBoostForecaster(BaseForecaster):
    def __init__(self, n_estimators=100, max_depth=3, learning_rate=0.1,
                 subsample=1.0, colsample_bytree=1.0):
        super().__init__()
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.model_name = 'XGBoost'
        self.last_known_value = None
        self.feature_columns = None

    def fit(self, y_train, X_train=None):
        if X_train is None:
            raise ValueError("XGBoost requires feature matrix X_train")

        self.feature_columns = X_train.columns.tolist()
        self.last_known_value = y_train.iloc[-1]

        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=42,
            objective='reg:squarederror'
        )
        self.model.fit(X_train, y_train)
        return self

    def predict(self, horizon, X_test=None):
        if X_test is None:
            raise ValueError("XGBoost requires feature matrix X_test")
        
        X_test_aligned = X_test[self.feature_columns]
        forecast = self.model.predict(X_test_aligned)
        return forecast[:horizon]


class LSTMForecaster(BaseForecaster):
    def __init__(self, units=50, dropout=0.2, epochs=50, batch_size=32,
                 sequence_length=10):
        super().__init__()
        self.units = units
        self.dropout = dropout
        self.epochs = epochs
        self.batch_size = batch_size
        self.sequence_length = sequence_length
        self.model_name = 'LSTM'
        self.scaler = None
        self.y_mean = 0
        self.y_std = 1

    def _create_sequences(self, data, sequence_length):
        X, y = [], []
        for i in range(sequence_length, len(data)):
            X.append(data[i-sequence_length:i, :])
            y.append(data[i, 0])
        return np.array(X), np.array(y)

    def fit(self, y_train, X_train=None):
        self.y_mean = y_train.mean()
        self.y_std = y_train.std()
        y_scaled = (y_train.values - self.y_mean) / self.y_std

        if X_train is not None:
            X_scaled = (X_train.values - X_train.values.mean(axis=0)) / (X_train.values.std(axis=0) + 1e-8)
            data = np.column_stack([y_scaled, X_scaled])
        else:
            data = y_scaled.reshape(-1, 1)

        X_seq, y_seq = self._create_sequences(data, self.sequence_length)

        self.model = Sequential([
            LSTM(units=self.units, return_sequences=True,
                 input_shape=(X_seq.shape[1], X_seq.shape[2])),
            Dropout(self.dropout),
            LSTM(units=self.units, return_sequences=False),
            Dropout(self.dropout),
            Dense(units=1)
        ])
        self.model.compile(optimizer='adam', loss='mean_squared_error')

        early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
        self.model.fit(
            X_seq, y_seq,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.2,
            callbacks=[early_stop],
            verbose=0
        )
        return self

    def predict(self, horizon, X_test=None):
        predictions = []
        last_sequence = self._get_last_sequence_for_prediction(X_test)
        
        for i in range(horizon):
            pred_scaled = self.model.predict(last_sequence, verbose=0)[0, 0]
            pred = pred_scaled * self.y_std + self.y_mean
            predictions.append(pred)
            
            next_point = np.array([[pred_scaled]])
            if last_sequence.shape[2] > 1 and X_test is not None and i < len(X_test):
                x_row = X_test.iloc[i].values
                x_scaled = (x_row - x_row.mean()) / (x_row.std() + 1e-8)
                next_point = np.column_stack([[[pred_scaled]], [x_scaled[:last_sequence.shape[2]-1]]])
            
            last_sequence = np.roll(last_sequence, -1, axis=1)
            last_sequence[0, -1, :] = next_point[0, :last_sequence.shape[2]]

        return np.array(predictions)

    def _get_last_sequence_for_prediction(self, X_test=None):
        if X_test is not None:
            X_scaled = (X_test.values - X_test.values.mean(axis=0)) / (X_test.values.std(axis=0) + 1e-8)
            dummy_y = np.zeros(X_scaled.shape[0])
            data = np.column_stack([dummy_y, X_scaled])
            seq = data[-self.sequence_length:, :].reshape(1, self.sequence_length, -1)
        else:
            seq = np.zeros((1, self.sequence_length, 1))
        return seq


def create_model(model_type, params=None):
    params = params or {}
    
    models = {
        'arima': lambda p: ARIMAForecaster(
            order=(p.get('p', 1), p.get('d', 1), p.get('q', 1)),
            seasonal_order=(p.get('P', 0), p.get('D', 0), p.get('Q', 0), p.get('s', 0))
        ),
        'prophet': lambda p: ProphetForecaster(
            yearly_seasonality=p.get('yearly_seasonality', True),
            weekly_seasonality=p.get('weekly_seasonality', True),
            daily_seasonality=p.get('daily_seasonality', True),
            changepoint_prior_scale=p.get('changepoint_prior_scale', 0.05)
        ),
        'xgboost': lambda p: XGBoostForecaster(
            n_estimators=p.get('n_estimators', 100),
            max_depth=p.get('max_depth', 3),
            learning_rate=p.get('learning_rate', 0.1),
            subsample=p.get('subsample', 1.0),
            colsample_bytree=p.get('colsample_bytree', 1.0)
        ),
        'lstm': lambda p: LSTMForecaster(
            units=p.get('units', 50),
            dropout=p.get('dropout', 0.2),
            epochs=p.get('epochs', 50),
            batch_size=p.get('batch_size', 32),
            sequence_length=p.get('sequence_length', 10)
        )
    }
    
    return models[model_type.lower()](params)
