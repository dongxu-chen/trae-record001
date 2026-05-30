import os
import json
import numpy as np
import lightgbm as lgb

from config.config import MODEL_DIR, FEATURE_COLUMNS, LABEL_COLUMN, LIGHTGBM_PARAMS


def _get_lgb_version():
    parts = lgb.__version__.split(".")
    return tuple(int(p) for p in parts[:3])


class LambdaMARTRanker:
    def __init__(self, params=None, feature_columns=None):
        self.params = params or LIGHTGBM_PARAMS.copy()
        self.feature_columns = feature_columns or FEATURE_COLUMNS.copy()
        self.model = None

    def train(self, X_train, y_train, group_train, X_val=None, y_val=None, group_val=None,
              num_boost_round=500, early_stopping_rounds=50):
        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            group=group_train,
            feature_name=self.feature_columns,
        )
        callbacks = [lgb.log_evaluation(period=50)]
        valid_sets = [train_data]
        valid_names = ["train"]

        if X_val is not None and y_val is not None and group_val is not None:
            val_data = lgb.Dataset(
                X_val,
                label=y_val,
                group=group_val,
                feature_name=self.feature_columns,
                reference=train_data,
            )
            valid_sets.append(val_data)
            valid_names.append("valid")
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))

        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )
        return self.model

    def predict(self, X):
        if self.model is None:
            raise ValueError("Model not trained yet")
        return self.model.predict(X)

    def predict_with_scores(self, X):
        raw_scores = self.predict(X)
        exp_scores = np.exp(raw_scores - np.max(raw_scores))
        probabilities = exp_scores / exp_scores.sum()
        return raw_scores, probabilities

    def get_feature_importance(self, importance_type="gain"):
        if self.model is None:
            raise ValueError("Model not trained yet")
        importance = self.model.feature_importance(importance_type=importance_type)
        return dict(zip(self.feature_columns, importance))

    def save_model(self, model_name="lambdamart_model.txt"):
        os.makedirs(MODEL_DIR, exist_ok=True)
        model_path = os.path.join(MODEL_DIR, model_name)
        self.model.save_model(model_path)
        meta = {
            "feature_columns": self.feature_columns,
            "params": self.params,
        }
        meta_path = os.path.join(MODEL_DIR, model_name.replace(".txt", "_meta.json"))
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        return model_path

    def load_model(self, model_name="lambdamart_model.txt"):
        model_path = os.path.join(MODEL_DIR, model_name)
        meta_path = os.path.join(MODEL_DIR, model_name.replace(".txt", "_meta.json"))
        self.model = lgb.Booster(model_file=model_path)
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self.feature_columns = meta.get("feature_columns", self.feature_columns)
            self.params = meta.get("params", self.params)
        return self.model

    def is_loaded(self):
        return self.model is not None
