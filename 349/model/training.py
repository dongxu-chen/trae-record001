import json
import joblib
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple, Optional

from config import XGB_PARAMS, XGB_MODEL_FILE, SCALER_FILE, FEATURE_NAMES_FILE
from model.feature_engineering import (
    FEATURE_COLUMNS, build_feature_vector, feature_vector_to_array, compute_ground_truth_score
)


def prepare_training_data(companies: list, kg_features_list: List[Dict[str, float]]) -> Tuple[np.ndarray, np.ndarray]:
    X_list = []
    y_list = []

    for company, kg_feats in zip(companies, kg_features_list):
        features = build_feature_vector(company, kg_feats)
        X_list.append(feature_vector_to_array(features))
        y = compute_ground_truth_score(company, kg_feats)
        y_list.append(y)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.float32)

    return X, y


def train_model(
    companies: list,
    kg_features_list: List[Dict[str, float]],
    use_kg: bool = True
) -> Tuple[xgb.XGBRegressor, StandardScaler]:
    X, y = prepare_training_data(companies, kg_features_list)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = xgb.XGBRegressor(**XGB_PARAMS)
    model.fit(X_scaled, y)

    save_model(model, scaler)

    return model, scaler


def save_model(model: xgb.XGBRegressor, scaler: StandardScaler) -> None:
    model.save_model(str(XGB_MODEL_FILE))
    joblib.dump(scaler, str(SCALER_FILE))

    feature_names = FEATURE_COLUMNS
    with open(FEATURE_NAMES_FILE, "w", encoding="utf-8") as f:
        json.dump(feature_names, f, ensure_ascii=False, indent=2)


def load_model() -> Tuple[xgb.XGBRegressor, StandardScaler]:
    model = xgb.XGBRegressor()
    model.load_model(str(XGB_MODEL_FILE))

    scaler = joblib.load(str(SCALER_FILE))

    return model, scaler


def load_feature_names() -> List[str]:
    with open(FEATURE_NAMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def predict_score(
    company,
    kg_features: Dict[str, float],
    model: Optional[xgb.XGBRegressor] = None,
    scaler: Optional[StandardScaler] = None
) -> float:
    if model is None or scaler is None:
        model, scaler = load_model()

    features = build_feature_vector(company, kg_features)
    X = feature_vector_to_array(features).reshape(1, -1)
    X_scaled = scaler.transform(X)

    score = model.predict(X_scaled)[0]
    return max(0.0, min(1000.0, float(score)))


def get_feature_importance(model: xgb.XGBRegressor) -> Dict[str, float]:
    importances = model.feature_importances_
    feature_names = load_feature_names()
    importance_dict = {}
    for name, imp in zip(feature_names, importances):
        importance_dict[name] = float(imp)
    return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
