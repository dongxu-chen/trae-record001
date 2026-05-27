import os
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import yaml
from .data_models import ClickFeatures


class AnomalyDetector:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.model_config = self.config['model']['isolation_forest']
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self._init_model()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_model(self):
        self.model = IsolationForest(
            n_estimators=self.model_config['n_estimators'],
            max_samples=self.model_config['max_samples'],
            contamination=self.model_config['contamination'],
            random_state=self.model_config['random_state'],
            n_jobs=-1
        )
        self.scaler = StandardScaler()

    def train(self, features_list: List[ClickFeatures]) -> None:
        X = self._prepare_features(features_list)
        if len(X) < 10:
            raise ValueError("至少需要10个样本进行训练")
        
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

    def predict(self, features: ClickFeatures) -> Tuple[bool, float, Dict]:
        if not self.is_trained:
            raise RuntimeError("模型未训练，请先调用train()方法")
        
        X = self._prepare_features([features])
        X_scaled = self.scaler.transform(X)
        
        is_anomaly = self.model.predict(X_scaled)[0] == -1
        raw_score = self.model.decision_function(X_scaled)[0]
        anomaly_score = self._normalize_score(raw_score)
        
        feature_contributions = self._get_feature_contributions(features)
        
        return is_anomaly, anomaly_score, feature_contributions

    def predict_batch(self, features_list: List[ClickFeatures]) -> List[Tuple[bool, float, Dict]]:
        if not self.is_trained:
            raise RuntimeError("模型未训练，请先调用train()方法")
        
        results = []
        for features in features_list:
            results.append(self.predict(features))
        return results

    def _prepare_features(self, features_list: List[ClickFeatures]) -> np.ndarray:
        X = []
        for features in features_list:
            feature_vector = features.to_feature_vector()
            X.append(feature_vector)
        return np.array(X, dtype=np.float64)

    def _normalize_score(self, raw_score: float) -> float:
        min_score = -0.5
        max_score = 0.5
        normalized = (raw_score - min_score) / (max_score - min_score)
        return 1.0 - np.clip(normalized, 0.0, 1.0)

    def _get_feature_contributions(self, features: ClickFeatures) -> Dict[str, float]:
        feature_names = features.get_feature_names()
        feature_values = features.to_feature_vector()
        
        contributions = {}
        for name, value in zip(feature_names, feature_values):
            if self.scaler is not None:
                idx = feature_names.index(name)
                mean = self.scaler.mean_[idx] if hasattr(self.scaler, 'mean_') else 0
                std = self.scaler.scale_[idx] if hasattr(self.scaler, 'scale_') else 1
                normalized = (value - mean) / std if std > 0 else 0
                contributions[name] = float(abs(normalized))
            else:
                contributions[name] = float(value)
        
        return contributions

    def get_top_anomaly_features(self, features: ClickFeatures, top_k: int = 5) -> List[Tuple[str, float]]:
        contributions = self._get_feature_contributions(features)
        sorted_features = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        return sorted_features[:top_k]

    def save_model(self, model_path: Optional[str] = None) -> None:
        if model_path is None:
            model_path = self.model_config['model_path']
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'is_trained': self.is_trained,
            'config': self.model_config
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, model_path: Optional[str] = None) -> None:
        if model_path is None:
            model_path = self.model_config['model_path']
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.is_trained = model_data['is_trained']

    def generate_training_data(self, n_samples: int = 1000, fraud_ratio: float = 0.1) -> List[ClickFeatures]:
        np.random.seed(42)
        features_list = []
        
        n_fraud = int(n_samples * fraud_ratio)
        n_normal = n_samples - n_fraud
        
        for i in range(n_normal):
            features = self._generate_normal_features(f'normal_{i}')
            features_list.append(features)
        
        for i in range(n_fraud):
            features = self._generate_fraud_features(f'fraud_{i}')
            features_list.append(features)
        
        return features_list

    def _generate_normal_features(self, click_id: str) -> ClickFeatures:
        return ClickFeatures(
            click_id=click_id,
            timestamp=np.random.uniform(0, 86400),
            ip_click_count_1min=np.random.poisson(2),
            ip_click_count_5min=np.random.poisson(8),
            ip_click_count_1h=np.random.poisson(50),
            device_click_count_1min=np.random.poisson(1),
            device_click_count_5min=np.random.poisson(4),
            device_click_count_1h=np.random.poisson(25),
            session_click_count=np.random.poisson(3),
            time_since_last_click_ip=np.random.exponential(30),
            time_since_last_click_device=np.random.exponential(60),
            click_interval_std_ip=np.random.uniform(0, 10),
            click_interval_std_device=np.random.uniform(0, 15),
            unique_publishers_per_ip=np.random.randint(1, 5),
            unique_ads_per_ip=np.random.randint(1, 10),
            hour_of_day=np.random.randint(0, 24),
            day_of_week=np.random.randint(0, 7),
            is_weekend=np.random.choice([True, False]),
            ip_entropy=np.random.uniform(2, 5),
            publisher_click_ratio=np.random.uniform(0, 0.3)
        )

    def _generate_fraud_features(self, click_id: str) -> ClickFeatures:
        fraud_type = np.random.choice(['high_freq', 'fixed_interval', 'bot'])
        
        if fraud_type == 'high_freq':
            return ClickFeatures(
                click_id=click_id,
                timestamp=np.random.uniform(0, 86400),
                ip_click_count_1min=np.random.randint(30, 100),
                ip_click_count_5min=np.random.randint(100, 500),
                ip_click_count_1h=np.random.randint(500, 2000),
                device_click_count_1min=np.random.randint(20, 80),
                device_click_count_5min=np.random.randint(80, 400),
                device_click_count_1h=np.random.randint(400, 1500),
                session_click_count=np.random.randint(50, 200),
                time_since_last_click_ip=np.random.uniform(0, 1),
                time_since_last_click_device=np.random.uniform(0, 1),
                click_interval_std_ip=np.random.uniform(0, 1),
                click_interval_std_device=np.random.uniform(0, 1),
                unique_publishers_per_ip=1,
                unique_ads_per_ip=1,
                hour_of_day=np.random.randint(0, 24),
                day_of_week=np.random.randint(0, 7),
                is_weekend=np.random.choice([True, False]),
                ip_entropy=np.random.uniform(0, 1),
                publisher_click_ratio=np.random.uniform(0.6, 1.0)
            )
        elif fraud_type == 'fixed_interval':
            return ClickFeatures(
                click_id=click_id,
                timestamp=np.random.uniform(0, 86400),
                ip_click_count_1min=np.random.randint(10, 30),
                ip_click_count_5min=np.random.randint(50, 150),
                ip_click_count_1h=np.random.randint(200, 600),
                device_click_count_1min=np.random.randint(8, 25),
                device_click_count_5min=np.random.randint(40, 120),
                device_click_count_1h=np.random.randint(150, 500),
                session_click_count=np.random.randint(20, 80),
                time_since_last_click_ip=np.random.uniform(1, 3),
                time_since_last_click_device=np.random.uniform(1, 3),
                click_interval_std_ip=np.random.uniform(0, 0.2),
                click_interval_std_device=np.random.uniform(0, 0.2),
                unique_publishers_per_ip=np.random.randint(1, 3),
                unique_ads_per_ip=np.random.randint(1, 5),
                hour_of_day=np.random.randint(0, 24),
                day_of_week=np.random.randint(0, 7),
                is_weekend=np.random.choice([True, False]),
                ip_entropy=np.random.uniform(0.5, 2),
                publisher_click_ratio=np.random.uniform(0.3, 0.8)
            )
        else:
            return ClickFeatures(
                click_id=click_id,
                timestamp=np.random.uniform(0, 86400),
                ip_click_count_1min=np.random.randint(5, 20),
                ip_click_count_5min=np.random.randint(20, 60),
                ip_click_count_1h=np.random.randint(100, 300),
                device_click_count_1min=np.random.randint(3, 15),
                device_click_count_5min=np.random.randint(15, 50),
                device_click_count_1h=np.random.randint(80, 250),
                session_click_count=np.random.randint(10, 50),
                time_since_last_click_ip=np.random.exponential(10),
                time_since_last_click_device=np.random.exponential(15),
                click_interval_std_ip=np.random.uniform(0, 5),
                click_interval_std_device=np.random.uniform(0, 8),
                unique_publishers_per_ip=np.random.randint(1, 2),
                unique_ads_per_ip=np.random.randint(1, 3),
                hour_of_day=np.random.randint(0, 24),
                day_of_week=np.random.randint(0, 7),
                is_weekend=np.random.choice([True, False]),
                ip_entropy=np.random.uniform(0, 1.5),
                publisher_click_ratio=np.random.uniform(0.4, 0.9)
            )
