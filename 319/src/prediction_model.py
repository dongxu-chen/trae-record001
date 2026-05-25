import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import xgboost as xgb

from config import config
from src.redis_client import RedisClient


class FeatureExtractor:
    def __init__(self):
        self.feature_dim = config.model.feature_dim
        self.categorical_features = [
            "user_gender",
            "user_age_group",
            "user_city",
            "user_interest",
            "user_education",
            "user_occupation",
            "user_marital_status",
            "ad_category",
            "ad_creative_type",
            "ad_placement",
            "ad_position",
            "device_type",
            "os_type",
            "os_version",
            "time_slot",
            "hour_of_day",
            "day_of_week",
            "is_weekend",
            "is_holiday",
            "province",
            "city_tier",
            "network_type",
            "carrier",
            "app_category",
            "content_category",
            "weather",
            "temperature_level",
            "user_intent",
            "purchase_intent",
            "brand_preference",
        ]
        self.numerical_features = [
            "user_income",
            "user_active_days",
            "user_click_count",
            "user_conversion_count",
            "user_avg_session_duration",
            "user_pages_per_session",
            "user_last_visit_days",
            "user_cart_count",
            "user_wishlist_count",
            "user_order_count",
            "user_total_spend",
            "ad_ctr_history",
            "ad_cvr_history",
            "ad_impression_count",
            "ad_click_count",
            "ad_conversion_count",
            "ad_position_score",
            "hour",
            "minute",
            "day_of_month",
            "week_of_year",
            "days_since_purchase",
            "price_sensitivity",
            "brand_loyalty_score",
            "context_relevance_score",
            "user_ad_match_score",
            "time_decay_factor",
            "recency_score",
            "frequency_score",
            "monetary_score",
        ]
        self.redis_client = RedisClient()

    def _hash_feature(self, key: str, value: Any) -> int:
        hash_str = f"{key}:{value}"
        hash_val = int(hashlib.md5(hash_str.encode()).hexdigest(), 16)
        return hash_val % self.feature_dim

    def _extract_categorical_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        for feat in self.categorical_features:
            if feat in data and data[feat] is not None:
                idx = self._hash_feature(feat, data[feat])
                features[idx] = 1.0
        return features

    def _extract_numerical_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        for i, feat in enumerate(self.numerical_features):
            if feat in data and data[feat] is not None:
                idx = self.feature_dim - len(self.numerical_features) + i
                features[idx] = float(data[feat])
        return features

    def _extract_cross_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        cross_pairs = [
            ("user_interest", "ad_category"),
            ("user_gender", "ad_category"),
            ("user_age_group", "ad_category"),
            ("user_city", "ad_category"),
            ("time_slot", "ad_category"),
            ("day_of_week", "ad_category"),
            ("is_weekend", "ad_category"),
            ("device_type", "ad_position"),
            ("os_type", "ad_placement"),
            ("user_age_group", "time_slot"),
            ("user_gender", "time_slot"),
            ("user_city", "time_slot"),
            ("city_tier", "ad_category"),
            ("network_type", "ad_position"),
            ("user_intent", "ad_category"),
            ("purchase_intent", "ad_category"),
            ("weather", "ad_category"),
            ("content_category", "ad_category"),
            ("app_category", "ad_category"),
            ("brand_preference", "ad_category"),
            ("user_interest", "ad_position"),
            ("user_age_group", "ad_position"),
            ("time_slot", "ad_position"),
            ("hour_of_day", "ad_category"),
            ("province", "ad_category"),
            ("is_holiday", "ad_category"),
            ("user_education", "ad_category"),
            ("user_occupation", "ad_category"),
            ("temperature_level", "ad_category"),
            ("user_interest", "time_slot"),
            ("user_intent", "time_slot"),
            ("purchase_intent", "time_slot"),
            ("user_age_group", "ad_placement"),
            ("city_tier", "ad_position"),
            ("network_type", "ad_category"),
            ("carrier", "ad_category"),
        ]
        for feat1, feat2 in cross_pairs:
            if feat1 in data and feat2 in data:
                v1, v2 = data[feat1], data[feat2]
                if v1 is not None and v2 is not None:
                    idx = self._hash_feature(f"{feat1}_{feat2}", f"{v1}_{v2}")
                    features[idx] = 1.0
        return features

    def _extract_temporal_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        from datetime import datetime
        now = datetime.now()
        
        temporal_features = {
            "hour": now.hour,
            "minute": now.minute,
            "hour_of_day": f"h{now.hour}",
            "day_of_week": f"d{now.weekday()}",
            "day_of_month": now.day,
            "week_of_year": now.isocalendar()[1],
            "is_weekend": "yes" if now.weekday() >= 5 else "no",
            "time_slot": self._get_time_slot(now.hour),
        }
        
        if "timestamp" in data:
            ts = data["timestamp"]
            if isinstance(ts, (int, float)):
                ts_dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
                temporal_features.update({
                    "hour": ts_dt.hour,
                    "minute": ts_dt.minute,
                    "hour_of_day": f"h{ts_dt.hour}",
                    "day_of_week": f"d{ts_dt.weekday()}",
                    "day_of_month": ts_dt.day,
                    "week_of_year": ts_dt.isocalendar()[1],
                    "is_weekend": "yes" if ts_dt.weekday() >= 5 else "no",
                    "time_slot": self._get_time_slot(ts_dt.hour),
                })
        
        for key, value in temporal_features.items():
            if key in self.categorical_features:
                idx = self._hash_feature(key, str(value))
                features[idx] = 1.0
            elif key in self.numerical_features:
                idx = self.feature_dim - len(self.numerical_features) + self.numerical_features.index(key)
                features[idx] = float(value) if isinstance(value, (int, float)) else 0.0
        
        if "hour" in self.numerical_features:
            hour_val = temporal_features.get("hour", now.hour)
            hour_idx = self.feature_dim - len(self.numerical_features) + self.numerical_features.index("hour")
            features[hour_idx] = float(hour_val)
            sin_hour = np.sin(2 * np.pi * hour_val / 24)
            cos_hour = np.cos(2 * np.pi * hour_val / 24)
            sin_idx = self._hash_feature("hour_sin", str(sin_hour))
            cos_idx = self._hash_feature("hour_cos", str(cos_hour))
            features[sin_idx] = sin_hour
            features[cos_idx] = cos_hour
        
        if "day_of_week" in self.numerical_features or "d" in str(temporal_features.get("day_of_week", "")):
            dow = int(str(temporal_features.get("day_of_week", "d0")).replace("d", ""))
            sin_dow = np.sin(2 * np.pi * dow / 7)
            cos_dow = np.cos(2 * np.pi * dow / 7)
            sin_idx = self._hash_feature("dow_sin", str(sin_dow))
            cos_idx = self._hash_feature("dow_cos", str(cos_dow))
            features[sin_idx] = sin_dow
            features[cos_idx] = cos_dow
        
        return features

    def _get_time_slot(self, hour: int) -> str:
        if 6 <= hour < 9:
            return "morning_peak"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 14:
            return "noon"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening_peak"
        elif 22 <= hour < 24:
            return "night"
        else:
            return "late_night"

    def _extract_location_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        
        city_tier_mapping = {
            "beijing": "tier1", "shanghai": "tier1", "guangzhou": "tier1", "shenzhen": "tier1",
            "hangzhou": "tier2", "chengdu": "tier2", "wuhan": "tier2", "xian": "tier2", 
            "nanjing": "tier2", "chongqing": "tier2", "tianjin": "tier2", "suzhou": "tier2",
        }
        
        province_mapping = {
            "beijing": "beijing", "shanghai": "shanghai", "guangzhou": "guangdong", 
            "shenzhen": "guangdong", "hangzhou": "zhejiang", "chengdu": "sichuan",
            "wuhan": "hubei", "xian": "shaanxi", "nanjing": "jiangsu", "chongqing": "chongqing",
        }
        
        if "user_city" in data:
            city = data["user_city"]
            city_tier = city_tier_mapping.get(city, "tier3")
            province = province_mapping.get(city, "other")
            
            if "city_tier" in self.categorical_features:
                idx = self._hash_feature("city_tier", city_tier)
                features[idx] = 1.0
            if "province" in self.categorical_features:
                idx = self._hash_feature("province", province)
                features[idx] = 1.0
        
        return features

    def _extract_rfm_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = np.zeros(self.feature_dim, dtype=np.float32)
        
        recency = data.get("user_last_visit_days", 30)
        frequency = data.get("user_active_days", 1)
        monetary = data.get("user_total_spend", 0)
        
        recency_score = max(0, min(1, 1 - recency / 30))
        frequency_score = min(1, frequency / 365)
        monetary_score = min(1, monetary / 10000) if monetary > 0 else 0
        
        rfm_idx = self._hash_feature("rfm_segment", f"{recency_score:.2f}_{frequency_score:.2f}_{monetary_score:.2f}")
        features[rfm_idx] = (recency_score + frequency_score + monetary_score) / 3
        
        for feat_name, feat_val in [
            ("recency_score", recency_score),
            ("frequency_score", frequency_score),
            ("monetary_score", monetary_score),
        ]:
            if feat_name in self.numerical_features:
                idx = self.feature_dim - len(self.numerical_features) + self.numerical_features.index(feat_name)
                features[idx] = feat_val
        
        return features

    def extract_features(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any]) -> np.ndarray:
        combined = {**user_profile, **context, **ad_info}
        cat_features = self._extract_categorical_features(combined)
        num_features = self._extract_numerical_features(combined)
        cross_features = self._extract_cross_features(combined)
        temporal_features = self._extract_temporal_features(combined)
        location_features = self._extract_location_features(combined)
        rfm_features = self._extract_rfm_features(combined)
        features = cat_features + num_features + cross_features + temporal_features + location_features + rfm_features
        return features.reshape(1, -1)

    def extract_features_batch(self, batch: List[Tuple[Dict, Dict, Dict]]) -> np.ndarray:
        feature_list = []
        for user_profile, context, ad_info in batch:
            features = self.extract_features(user_profile, context, ad_info)
            feature_list.append(features)
        return np.vstack(feature_list)

    def get_feature_hash(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any]) -> str:
        combined = {**user_profile, **context, **ad_info}
        hash_str = str(sorted(combined.items()))
        return hashlib.md5(hash_str.encode()).hexdigest()[:16]


class PredictionModel:
    def __init__(self):
        self.ctr_model: Optional[xgb.Booster] = None
        self.cvr_model: Optional[xgb.Booster] = None
        self.feature_extractor = FeatureExtractor()
        self.redis_client = RedisClient()
        self._load_models()

    def _load_models(self):
        if os.path.exists(config.model.ctr_model_path):
            self.ctr_model = xgb.Booster()
            self.ctr_model.load_model(config.model.ctr_model_path)
        else:
            print(f"CTR model not found at {config.model.ctr_model_path}, will use mock model")
            self.ctr_model = self._create_mock_model()

        if os.path.exists(config.model.cvr_model_path):
            self.cvr_model = xgb.Booster()
            self.cvr_model.load_model(config.model.cvr_model_path)
        else:
            print(f"CVR model not found at {config.model.cvr_model_path}, will use mock model")
            self.cvr_model = self._create_mock_model()

    def _create_mock_model(self) -> xgb.Booster:
        params = {
            "objective": "binary:logistic",
            "max_depth": 6,
            "eta": 0.1,
            "silent": 1,
        }
        n_samples = 100
        n_features = config.model.feature_dim
        X = np.random.randn(n_samples, n_features)
        y = np.random.randint(0, 2, n_samples)
        dtrain = xgb.DMatrix(X, label=y)
        model = xgb.train(params, dtrain, num_boost_round=10)
        return model

    def train_ctr_model(self, X: np.ndarray, y: np.ndarray, save_path: Optional[str] = None) -> xgb.Booster:
        params = {
            "objective": "binary:logistic",
            "max_depth": 8,
            "eta": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 10,
            "gamma": 0.1,
            "eval_metric": "auc",
            "silent": 1,
        }
        if config.model.use_gpu:
            params.update({"tree_method": "gpu_hist", "predictor": "gpu_predictor"})

        dtrain = xgb.DMatrix(X, label=y)
        self.ctr_model = xgb.train(params, dtrain, num_boost_round=100)

        save_path = save_path or config.model.ctr_model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.ctr_model.save_model(save_path)
        return self.ctr_model

    def train_cvr_model(self, X: np.ndarray, y: np.ndarray, save_path: Optional[str] = None) -> xgb.Booster:
        params = {
            "objective": "binary:logistic",
            "max_depth": 6,
            "eta": 0.03,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "min_child_weight": 5,
            "gamma": 0.05,
            "eval_metric": "auc",
            "scale_pos_weight": 10,
            "silent": 1,
        }
        if config.model.use_gpu:
            params.update({"tree_method": "gpu_hist", "predictor": "gpu_predictor"})

        dtrain = xgb.DMatrix(X, label=y)
        self.cvr_model = xgb.train(params, dtrain, num_boost_round=150)

        save_path = save_path or config.model.cvr_model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.cvr_model.save_model(save_path)
        return self.cvr_model

    def predict_ctr(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any]) -> float:
        feature_hash = self.feature_extractor.get_feature_hash(user_profile, context, ad_info)
        cached = self.redis_client.get_cached_prediction(f"ctr:{feature_hash}")
        if cached is not None:
            return cached

        features = self.feature_extractor.extract_features(user_profile, context, ad_info)
        dmatrix = xgb.DMatrix(features)
        prediction = float(self.ctr_model.predict(dmatrix)[0])
        prediction = max(0.0, min(1.0, prediction))

        self.redis_client.cache_prediction(f"ctr:{feature_hash}", prediction, ttl=1800)
        return prediction

    def predict_cvr(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any]) -> float:
        feature_hash = self.feature_extractor.get_feature_hash(user_profile, context, ad_info)
        cached = self.redis_client.get_cached_prediction(f"cvr:{feature_hash}")
        if cached is not None:
            return cached

        features = self.feature_extractor.extract_features(user_profile, context, ad_info)
        dmatrix = xgb.DMatrix(features)
        prediction = float(self.cvr_model.predict(dmatrix)[0])
        prediction = max(0.0, min(1.0, prediction))

        self.redis_client.cache_prediction(f"cvr:{feature_hash}", prediction, ttl=1800)
        return prediction

    def predict_batch(self, batch: List[Tuple[Dict, Dict, Dict]]) -> Tuple[List[float], List[float]]:
        features = self.feature_extractor.extract_features_batch(batch)
        dmatrix = xgb.DMatrix(features)

        ctr_predictions = self.ctr_model.predict(dmatrix) if self.ctr_model else np.zeros(len(batch))
        cvr_predictions = self.cvr_model.predict(dmatrix) if self.cvr_model else np.zeros(len(batch))

        ctr_predictions = np.clip(ctr_predictions, 0.0, 1.0)
        cvr_predictions = np.clip(cvr_predictions, 0.0, 1.0)

        return list(ctr_predictions), list(cvr_predictions)

    def predict(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any]) -> Tuple[float, float]:
        ctr = self.predict_ctr(user_profile, context, ad_info)
        cvr = self.predict_cvr(user_profile, context, ad_info)
        return ctr, cvr

    def get_expected_value(self, user_profile: Dict[str, Any], context: Dict[str, Any], ad_info: Dict[str, Any], cpa_goal: float) -> float:
        ctr, cvr = self.predict(user_profile, context, ad_info)
        return ctr * cvr * cpa_goal

    def get_feature_importance(self, model_type: str = "ctr") -> Dict[str, float]:
        model = self.ctr_model if model_type == "ctr" else self.cvr_model
        if model is None:
            return {}
        importance = model.get_score(importance_type="gain")
        return {str(k): float(v) for k, v in importance.items()}

    def warm_up(self):
        dummy_profile = {"user_gender": "M", "user_age_group": "25-34"}
        dummy_context = {"device_type": "mobile"}
        dummy_ad = {"ad_category": "electronics"}
        self.predict(dummy_profile, dummy_context, dummy_ad)
        print("Model warm-up completed")
