import numpy as np
import lightgbm as lgb
import joblib
import sys
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LIGHTGBM_PARAMS, MODEL_DIR, PRED_LEN


def prepare_features_for_lgb(sequences, road_ids):
    n_samples, history_len, n_features = sequences.shape

    features = []
    for i in range(n_samples):
        seq = sequences[i]
        road_id = road_ids[i]

        speed_mean = np.mean(seq[:, 0])
        speed_std = np.std(seq[:, 0])
        speed_last = seq[-1, 0]
        speed_trend = seq[-1, 0] - seq[0, 0]

        flow_mean = np.mean(seq[:, 1])
        flow_std = np.std(seq[:, 1])
        flow_last = seq[-1, 1]

        occ_mean = np.mean(seq[:, 2])
        occ_std = np.std(seq[:, 2])
        occ_last = seq[-1, 2]

        last_features = seq[-1, 3:]

        feature_row = [
            road_id,
            speed_mean, speed_std, speed_last, speed_trend,
            flow_mean, flow_std, flow_last,
            occ_mean, occ_std, occ_last,
        ]
        feature_row.extend(last_features)
        features.append(feature_row)

    return np.array(features)


class LightGBMPredictor:
    def __init__(self, params=None):
        self.params = params if params else LIGHTGBM_PARAMS
        self.models = []
        self.feature_names = None

    def train(self, X_train, y_train, X_val=None, y_val=None):
        self.models = []
        feature_names = [
            "road_id",
            "speed_mean", "speed_std", "speed_last", "speed_trend",
            "flow_mean", "flow_std", "flow_last",
            "occ_mean", "occ_std", "occ_last",
            "hour", "minute", "weekday", "is_weekend",
            "morning_peak", "evening_peak", "day_of_year", "month",
            "temperature", "rainfall", "visibility", "weather_type",
            "has_event", "event_type", "event_severity",
        ]
        self.feature_names = feature_names

        for horizon in range(PRED_LEN):
            y_train_horizon = y_train[:, horizon]

            train_data = lgb.Dataset(
                X_train,
                label=y_train_horizon,
                feature_name=feature_names,
                categorical_feature=["road_id", "weekday", "weather_type", "event_type"]
            )

            valid_sets = [train_data]
            if X_val is not None and y_val is not None:
                y_val_horizon = y_val[:, horizon]
                val_data = lgb.Dataset(
                    X_val,
                    label=y_val_horizon,
                    feature_name=feature_names,
                    categorical_feature=["road_id", "weekday", "weather_type", "event_type"],
                    reference=train_data
                )
                valid_sets.append(val_data)

            model = lgb.train(
                self.params,
                train_data,
                num_boost_round=500,
                valid_sets=valid_sets,
                callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
            )

            self.models.append(model)
            print(f"Trained LightGBM model for horizon {horizon + 1}")

    def predict(self, X):
        predictions = []
        for model in self.models:
            pred = model.predict(X, num_iteration=model.best_iteration)
            pred = np.clip(pred, 0, 10)
            predictions.append(pred)
        return np.array(predictions).T

    def evaluate(self, X, y):
        y_pred = self.predict(X)
        mse = mean_squared_error(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        print(f"LightGBM Evaluation - MSE: {mse:.4f}, MAE: {mae:.4f}")
        return mse, mae

    def save(self, path=os.path.join(MODEL_DIR, "lgb_models")):
        os.makedirs(path, exist_ok=True)
        for i, model in enumerate(self.models):
            joblib.dump(model, os.path.join(path, f"lgb_model_horizon_{i}.pkl"))
        print(f"Saved LightGBM models to {path}")

    def load(self, path=os.path.join(MODEL_DIR, "lgb_models")):
        self.models = []
        for i in range(PRED_LEN):
            model_path = os.path.join(path, f"lgb_model_horizon_{i}.pkl")
            model = joblib.load(model_path)
            self.models.append(model)
        print(f"Loaded LightGBM models from {path}")
