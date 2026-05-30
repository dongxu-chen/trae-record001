import json
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    mean_squared_error,
    r2_score,
    accuracy_score,
    classification_report
)
from sklearn.cluster import KMeans
import joblib

from .utils import (
    detect_periodicity,
    calculate_redundancy_ratio,
    extract_endpoint_pattern,
    DATA_FRESHNESS_TAGS,
    classify_data_freshness,
    normalize_params,
    compute_content_hash
)

warnings.filterwarnings('ignore')


@dataclass
class PredictionResult:
    """预测结果数据类"""
    cache_hit_probability: float
    predicted_ttl_seconds: int
    confidence_score: float
    model_version: str
    features_used: Dict[str, Any]
    explanation: str
    freshness_tag: str = "dynamic"
    freshness_description: str = ""
    content_hash: str = ""
    normalized_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TTLRecommendation:
    """TTL推荐结果"""
    endpoint: str
    current_ttl: Optional[int]
    recommended_ttl: int
    expected_hit_rate_improvement: float
    expected_savings_percent: float
    reasoning: List[str]
    freshness_tag: str = "dynamic"
    freshness_description: str = ""
    min_allowed_ttl: int = 60
    max_allowed_ttl: int = 86400
    ttl_adjustment_factor: float = 1.0


class CachePredictor:
    """缓存命中率预测器"""
    
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.is_trained = False
        self.feature_importance = None
        self.model_accuracy = 0.0
        
        self.numeric_features = [
            'request_count',
            'avg_interval_seconds',
            'unique_users',
            'avg_response_size',
            'avg_response_time',
            'hour_of_day',
            'day_of_week',
            'request_rate_per_minute',
            'freshness_score'
        ]
        
        self.categorical_features = [
            'method',
            'endpoint_category',
            'is_peak_hour',
            'freshness_tag'
        ]
        
    def prepare_features(self, df: pd.DataFrame, 
                        duplication_stats: Optional[pd.DataFrame] = None,
                        time_patterns: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """准备训练特征"""
        features = df.copy()
        
        if features.empty:
            return features
        
        if 'timestamp' in features.columns and not features['timestamp'].isna().all():
            features['hour_of_day'] = features['timestamp'].dt.hour
            features['day_of_week'] = features['timestamp'].dt.dayofweek
            features['is_peak_hour'] = features['hour_of_day'].apply(
                lambda x: 1 if 9 <= x <= 18 else 0
            )
        else:
            features['hour_of_day'] = 12
            features['day_of_week'] = 3
            features['is_peak_hour'] = 1
        
        if duplication_stats is not None and not duplication_stats.empty:
            pattern_map = dict(zip(
                duplication_stats['pattern'],
                duplication_stats[['request_count', 'avg_interval_seconds', 
                                   'total_response_size', 'avg_response_time']].to_dict('records')
            ))
            
            def get_stats(pattern):
                stats = pattern_map.get(pattern, {})
                return pd.Series({
                    'request_count': stats.get('request_count', 1),
                    'avg_interval_seconds': stats.get('avg_interval_seconds', 3600),
                    'total_response_size': stats.get('total_response_size', 1000),
                    'avg_response_time': stats.get('avg_response_time', 100),
                })
            
            if 'pattern' in features.columns:
                stats_df = features['pattern'].apply(get_stats)
                features = pd.concat([features, stats_df], axis=1)
        
        if 'request_count' not in features.columns:
            pattern_counts = features['pattern'].value_counts().to_dict()
            features['request_count'] = features['pattern'].map(pattern_counts)
        
        if 'avg_interval_seconds' not in features.columns:
            features['avg_interval_seconds'] = 3600
        
        if 'unique_users' not in features.columns:
            features['unique_users'] = features['user_id'].fillna('anonymous').nunique()
        
        if 'avg_response_size' not in features.columns:
            features['avg_response_size'] = features['response_size'].mean()
        
        if 'avg_response_time' not in features.columns:
            features['avg_response_time'] = features['response_time_ms'].mean()
        
        features['endpoint_category'] = features['pattern'].apply(self._categorize_endpoint)
        features['request_rate_per_minute'] = features['request_count'] / 60
        
        if 'freshness_tag' not in features.columns or features['freshness_tag'].isna().all():
            features['freshness_tag'] = features['pattern'].apply(
                lambda x: classify_data_freshness(x).tag
            )
        features['freshness_score'] = features['freshness_tag'].apply(
            lambda tag: DATA_FRESHNESS_TAGS.get(tag, DATA_FRESHNESS_TAGS['dynamic']).freshness_score
        )
        
        if 'normalized_params' not in features.columns:
            features['normalized_params'] = '{}'
        if 'content_hash' not in features.columns:
            features['content_hash'] = ''
        
        for col in self.numeric_features:
            if col not in features.columns:
                features[col] = 0
        
        for col in self.categorical_features:
            if col not in features.columns:
                features[col] = 'unknown'
        
        features[self.numeric_features] = features[self.numeric_features].fillna(0)
        features[self.categorical_features] = features[self.categorical_features].fillna('unknown')
        
        return features
    
    @staticmethod
    def _categorize_endpoint(pattern: str) -> str:
        """将端点分类"""
        pattern = pattern.lower()
        
        categories = {
            'static': ['/static', '/css', '/js', '/img', '/assets', '/favicon'],
            'api_list': ['/list', '/search', '/query', '/find', '/all', '/items'],
            'api_detail': ['/detail', '/get', '/{id}', '/{uuid}'],
            'user': ['/user', '/profile', '/account', '/me'],
            'auth': ['/login', '/logout', '/register', '/token', '/auth'],
            'admin': ['/admin', '/manage', '/config'],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in pattern:
                    return category
        
        return 'other'
    
    def calculate_target(self, features_df: pd.DataFrame) -> pd.Series:
        """计算目标变量（是否会被缓存命中）"""
        pattern_counts = features_df['pattern'].value_counts()
        total = len(features_df)
        
        def get_hit_prob(pattern):
            count = pattern_counts.get(pattern, 0)
            if count <= 1:
                return 0.0
            return min(0.95, (count - 1) / count)
        
        hit_probs = features_df['pattern'].apply(get_hit_prob)
        
        return (hit_probs >= 0.5).astype(int)
    
    def train(self, features_df: pd.DataFrame, test_size: float = 0.2) -> Dict[str, Any]:
        """训练预测模型"""
        if features_df.empty:
            raise ValueError("特征数据为空，无法训练模型")
        
        for col in self.numeric_features:
            if col not in features_df.columns:
                features_df[col] = 0
        for col in self.categorical_features:
            if col not in features_df.columns:
                features_df[col] = 'unknown'
        
        X = features_df[self.numeric_features + self.categorical_features]
        y = self.calculate_target(features_df)
        
        if len(set(y)) < 2:
            y = pd.Series(np.random.randint(0, 2, size=len(y)))
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), self.numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), self.categorical_features)
            ])
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'
        )
        
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', self.model)
        ])
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        pipeline.fit(X_train, y_train)
        
        self.preprocessor = preprocessor
        self.is_trained = True
        
        y_pred = pipeline.predict(X_test)
        self.model_accuracy = accuracy_score(y_test, y_pred)
        
        try:
            importances = self.model.feature_importances_
            feature_names = (
                self.numeric_features +
                list(pipeline.named_steps['preprocessor']
                     .named_transformers_['cat']
                     .get_feature_names_out(self.categorical_features))
            )
            self.feature_importance = dict(zip(feature_names, importances))
        except Exception:
            self.feature_importance = {}
        
        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='accuracy')
        
        return {
            'accuracy': self.model_accuracy,
            'cv_accuracy_mean': cv_scores.mean(),
            'cv_accuracy_std': cv_scores.std(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }
    
    def predict(self, features_df: pd.DataFrame) -> List[PredictionResult]:
        """预测缓存命中概率"""
        if not self.is_trained:
            return self._fallback_predict(features_df)
        
        features_df = self.prepare_features(features_df)
        
        X = features_df[self.numeric_features + self.categorical_features]
        
        proba = self.model.predict_proba(self.preprocessor.transform(X))
        hit_probs = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
        
        results = []
        for i, (_, row) in enumerate(features_df.iterrows()):
            hit_prob = float(hit_probs[i])
            ttl = self._recommend_ttl(row, hit_prob)
            confidence = self._calculate_confidence(row, hit_prob)
            explanation = self._generate_explanation(row, hit_prob, ttl)
            
            freshness_tag = row.get('freshness_tag', 'dynamic')
            freshness_info = DATA_FRESHNESS_TAGS.get(
                freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
            )
            
            results.append(PredictionResult(
                cache_hit_probability=hit_prob,
                predicted_ttl_seconds=ttl,
                confidence_score=confidence,
                model_version="1.0.0",
                features_used=row[self.numeric_features + self.categorical_features].to_dict(),
                explanation=explanation,
                freshness_tag=freshness_tag,
                freshness_description=freshness_info.description,
                content_hash=row.get('content_hash', ''),
                normalized_params=json.loads(row.get('normalized_params', '{}'))
            ))
        
        return results
    
    def _fallback_predict(self, features_df: pd.DataFrame) -> List[PredictionResult]:
        """基于规则的回退预测"""
        results = []
        
        for _, row in features_df.iterrows():
            request_count = row.get('request_count', 1)
            avg_interval = row.get('avg_interval_seconds', 3600)
            avg_size = row.get('avg_response_size', 1000)
            
            hit_prob = 0.0
            if request_count >= 10:
                hit_prob = min(0.9, request_count / 100)
            elif request_count >= 5:
                hit_prob = 0.6
            elif request_count >= 2:
                hit_prob = 0.3
            
            if avg_interval < 60:
                hit_prob = min(0.95, hit_prob + 0.2)
            elif avg_interval < 300:
                hit_prob = min(0.9, hit_prob + 0.1)
            
            if avg_size > 10000:
                hit_prob = max(0.1, hit_prob - 0.1)
            
            ttl = self._recommend_ttl(row, hit_prob)
            confidence = min(0.8, request_count / 20)
            explanation = self._generate_explanation(row, hit_prob, ttl)
            
            freshness_tag = row.get('freshness_tag', 'dynamic')
            if freshness_tag == 'dynamic' or pd.isna(freshness_tag):
                freshness_tag = classify_data_freshness(
                    row.get('pattern', ''), 
                    request_params=row.get('normalized_params', {})
                ).tag
            freshness_info = DATA_FRESHNESS_TAGS.get(
                freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
            )
            
            results.append(PredictionResult(
                cache_hit_probability=hit_prob,
                predicted_ttl_seconds=ttl,
                confidence_score=confidence,
                model_version="rule-based-1.0",
                features_used=row[self.numeric_features + self.categorical_features].to_dict() if all(c in row.index for c in self.categorical_features) else {},
                explanation=explanation,
                freshness_tag=freshness_tag,
                freshness_description=freshness_info.description,
                content_hash=row.get('content_hash', ''),
                normalized_params=json.loads(row.get('normalized_params', '{}')) if isinstance(row.get('normalized_params', {}), str) else row.get('normalized_params', {})
            ))
        
        return results
    
    def _recommend_ttl(self, row: pd.Series, hit_prob: float) -> int:
        """推荐TTL值（结合数据时效性标签）"""
        avg_interval = row.get('avg_interval_seconds', 3600)
        request_count = row.get('request_count', 1)
        pattern = row.get('pattern', '')
        
        freshness_tag = row.get('freshness_tag', 'dynamic')
        freshness_info = DATA_FRESHNESS_TAGS.get(
            freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
        )
        
        base_ttl = freshness_info.default_ttl_seconds
        min_ttl = freshness_info.min_ttl_seconds
        max_ttl = freshness_info.max_ttl_seconds
        
        if avg_interval < 60:
            base_ttl = int(max(min_ttl, base_ttl * 0.8))
        elif avg_interval < 300:
            base_ttl = int(max(min_ttl, base_ttl * 0.9))
        elif avg_interval > 3600:
            base_ttl = int(min(max_ttl, base_ttl * 1.2))
        
        if hit_prob > 0.8:
            base_ttl = int(min(max_ttl, base_ttl * 1.3))
        elif hit_prob < 0.3:
            base_ttl = int(max(min_ttl, base_ttl * 0.7))
        
        if request_count > 100:
            base_ttl = int(min(max_ttl, base_ttl * 1.1))
        elif request_count < 5:
            base_ttl = int(max(min_ttl, base_ttl * 0.8))
        
        endpoint_type = self._categorize_endpoint(pattern)
        type_ttl_map = {
            'static': 86400,
            'api_list': 3600,
            'api_detail': 1800,
            'user': 600,
            'auth': 60,
            'admin': 300,
            'other': 300
        }
        
        type_based_ttl = type_ttl_map.get(endpoint_type, 300)
        base_ttl = max(base_ttl, int(type_based_ttl * 0.5))
        
        base_ttl = max(min_ttl, min(max_ttl, base_ttl))
        
        return base_ttl
    
    def _calculate_confidence(self, row: pd.Series, hit_prob: float) -> float:
        """计算预测置信度"""
        request_count = row.get('request_count', 0)
        data_quality = min(1.0, request_count / 50)
        
        pattern_certainty = 0.5
        if row.get('avg_interval_seconds', 0) > 0:
            interval_cv = row.get('avg_interval_seconds', 0) / 3600
            pattern_certainty = max(0.3, 1 - min(1.0, interval_cv))
        
        return (data_quality * 0.6 + pattern_certainty * 0.4)
    
    def _generate_explanation(self, row: pd.Series, hit_prob: float, ttl: int) -> str:
        """生成预测解释（含时效性标签说明）"""
        parts = []
        
        freshness_tag = row.get('freshness_tag', 'dynamic')
        freshness_info = DATA_FRESHNESS_TAGS.get(
            freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
        )
        parts.append(f"数据时效性: {freshness_tag} - {freshness_info.description}")
        
        request_count = row.get('request_count', 0)
        if request_count >= 10:
            parts.append(f"该端点已被请求 {request_count} 次，重复度较高")
        elif request_count >= 2:
            parts.append(f"该端点有 {request_count} 次重复请求")
        
        avg_interval = row.get('avg_interval_seconds', 0)
        if avg_interval < 60:
            parts.append("请求间隔很短（<1分钟）")
        elif avg_interval < 3600:
            parts.append("请求间隔适中")
        
        if hit_prob >= 0.7:
            parts.append(f"缓存命中概率较高 ({hit_prob:.1%})")
        elif hit_prob >= 0.3:
            parts.append(f"缓存命中概率中等 ({hit_prob:.1%})")
        else:
            parts.append(f"缓存命中概率较低 ({hit_prob:.1%})")
        
        parts.append(f"推荐TTL: {ttl}秒 (基于{freshness_tag}标签，范围{freshness_info.min_ttl_seconds}-{freshness_info.max_ttl_seconds}秒)")
        
        return "；".join(parts)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """获取特征重要性"""
        return self.feature_importance or {}
    
    def save_model(self, filepath: str) -> None:
        """保存模型"""
        joblib.dump({
            'model': self.model,
            'preprocessor': self.preprocessor,
            'is_trained': self.is_trained,
            'feature_importance': self.feature_importance,
            'model_accuracy': self.model_accuracy,
        }, filepath)
    
    def load_model(self, filepath: str) -> None:
        """加载模型"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.preprocessor = data['preprocessor']
        self.is_trained = data['is_trained']
        self.feature_importance = data['feature_importance']
        self.model_accuracy = data['model_accuracy']


class TTLOptimizer:
    """TTL优化器"""
    
    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """训练TTL优化模型"""
        if historical_data.empty or 'optimal_ttl' not in historical_data.columns:
            return {'status': 'not_enough_data'}
        
        features = [
            'request_count', 'avg_interval_seconds', 'unique_users',
            'avg_response_size', 'avg_response_time', 'hit_rate',
            'eviction_rate', 'last_accessed_hours_ago'
        ]
        
        available_features = [f for f in features if f in historical_data.columns]
        if len(available_features) < 3:
            return {'status': 'insufficient_features'}
        
        X = historical_data[available_features].fillna(0)
        y = historical_data['optimal_ttl'].fillna(300)
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        y_pred = self.model.predict(X_scaled)
        mse = mean_squared_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        
        return {
            'status': 'success',
            'mse': mse,
            'r2_score': r2,
            'features_used': available_features
        }
    
    def optimize(self, endpoint_pattern: str, current_metrics: Dict[str, Any]) -> TTLRecommendation:
        """优化特定端点的TTL"""
        if not self.is_trained:
            return self._rule_based_optimize(endpoint_pattern, current_metrics)
        
        features = pd.DataFrame([current_metrics])
        features_scaled = self.scaler.transform(features)
        
        recommended_ttl = int(self.model.predict(features_scaled)[0])
        
        hit_rate = current_metrics.get('hit_rate', 0.0)
        current_ttl = current_metrics.get('current_ttl')
        
        expected_improvement = max(0, 0.15 * (1 - hit_rate))
        expected_savings = min(0.5, recommended_ttl / 3600 * 0.3)
        
        reasoning = self._generate_ttl_reasoning(
            current_metrics, current_ttl, recommended_ttl, hit_rate
        )
        
        return TTLRecommendation(
            endpoint=endpoint_pattern,
            current_ttl=current_ttl,
            recommended_ttl=max(60, min(86400 * 7, recommended_ttl)),
            expected_hit_rate_improvement=expected_improvement,
            expected_savings_percent=expected_savings,
            reasoning=reasoning
        )
    
    def _rule_based_optimize(self, endpoint_pattern: str, 
                            current_metrics: Dict[str, Any]) -> TTLRecommendation:
        """基于规则的TTL优化（结合数据时效性标签）"""
        hit_rate = current_metrics.get('hit_rate', 0.0)
        request_count = current_metrics.get('request_count', 0)
        avg_interval = current_metrics.get('avg_interval_seconds', 3600)
        eviction_rate = current_metrics.get('eviction_rate', 0.0)
        current_ttl = current_metrics.get('current_ttl')
        
        freshness_tag = current_metrics.get(
            'freshness_tag',
            classify_data_freshness(endpoint_pattern).tag
        )
        freshness_info = DATA_FRESHNESS_TAGS.get(
            freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
        )
        
        recommended_ttl = freshness_info.default_ttl_seconds
        min_ttl = freshness_info.min_ttl_seconds
        max_ttl = freshness_info.max_ttl_seconds
        
        ttl_adjustment_factor = 1.0
        
        if hit_rate > 0.8 and eviction_rate < 0.1:
            ttl_adjustment_factor *= 1.3
        elif hit_rate < 0.3 or eviction_rate > 0.5:
            ttl_adjustment_factor *= 0.7
        
        if avg_interval < 60:
            ttl_adjustment_factor *= 0.8
        elif avg_interval < 300:
            ttl_adjustment_factor *= 0.9
        elif avg_interval > 3600:
            ttl_adjustment_factor *= 1.2
        
        if request_count > 1000:
            ttl_adjustment_factor *= 1.1
        elif request_count < 10:
            ttl_adjustment_factor *= 0.9
        
        recommended_ttl = int(freshness_info.default_ttl_seconds * ttl_adjustment_factor)
        recommended_ttl = max(min_ttl, min(max_ttl, recommended_ttl))
        
        expected_improvement = max(0, 0.1 * (1 - hit_rate) * (1 - freshness_info.freshness_score * 0.5))
        expected_savings = min(0.4, recommended_ttl / 3600 * 0.25 * ttl_adjustment_factor)
        
        reasoning = self._generate_ttl_reasoning(
            current_metrics, current_ttl, recommended_ttl, hit_rate,
            freshness_tag, freshness_info, ttl_adjustment_factor
        )
        
        return TTLRecommendation(
            endpoint=endpoint_pattern,
            current_ttl=current_ttl,
            recommended_ttl=recommended_ttl,
            expected_hit_rate_improvement=expected_improvement,
            expected_savings_percent=expected_savings,
            reasoning=reasoning,
            freshness_tag=freshness_tag,
            freshness_description=freshness_info.description,
            min_allowed_ttl=min_ttl,
            max_allowed_ttl=max_ttl,
            ttl_adjustment_factor=ttl_adjustment_factor
        )
    
    @staticmethod
    def _generate_ttl_reasoning(metrics: Dict[str, Any], current_ttl: Optional[int],
                               recommended_ttl: int, hit_rate: float,
                               freshness_tag: str = "dynamic",
                               freshness_info: Any = None,
                               adjustment_factor: float = 1.0) -> List[str]:
        """生成TTL调整理由（含时效性标签说明）"""
        reasoning = []
        
        if freshness_info:
            reasoning.append(
                f"数据时效性标签: {freshness_tag} - {freshness_info.description}"
            )
            reasoning.append(
                f"TTL允许范围: {freshness_info.min_ttl_seconds}秒 ~ {freshness_info.max_ttl_seconds}秒"
            )
            if adjustment_factor != 1.0:
                reasoning.append(
                    f"TTL调整因子: {adjustment_factor:.2f}x (基于访问模式)"
                )
        
        if hit_rate > 0.8:
            reasoning.append(f"当前命中率较高 ({hit_rate:.1%})，可以延长TTL以减少回源")
        elif hit_rate < 0.3:
            reasoning.append(f"当前命中率较低 ({hit_rate:.1%})，建议缩短TTL以保证数据新鲜度")
        
        interval = metrics.get('avg_interval_seconds', 3600)
        if interval < 60:
            reasoning.append(f"请求频率很高（平均每 {interval:.0f} 秒1次），适合短缓存")
        elif interval > 3600:
            reasoning.append(f"请求频率较低（平均每 {interval/3600:.1f} 小时1次），可以适当延长缓存")
        
        eviction = metrics.get('eviction_rate', 0)
        if eviction > 0.3:
            reasoning.append(f"缓存淘汰率较高 ({eviction:.1%})，可能需要增加缓存容量")
        
        if current_ttl:
            change = (recommended_ttl - current_ttl) / current_ttl * 100
            if abs(change) > 20:
                direction = "增加" if change > 0 else "减少"
                reasoning.append(f"建议将TTL从 {current_ttl}秒 {direction}至 {recommended_ttl}秒 ({change:+.1f}%)")
        
        return reasoning


class DuplicationPredictor:
    """重复请求预测器"""
    
    def __init__(self):
        self.kmeans = None
        self.cluster_labels = None
        self.is_trained = False
    
    def analyze_patterns(self, duplication_df: pd.DataFrame) -> Dict[str, Any]:
        """分析重复模式并聚类"""
        if duplication_df.empty or len(duplication_df) < 3:
            return {'status': 'insufficient_data'}
        
        feature_cols = [
            'request_count', 'avg_interval_seconds', 
            'total_response_size', 'avg_response_time'
        ]
        
        available_features = [f for f in feature_cols if f in duplication_df.columns]
        
        if len(available_features) < 2:
            return {'status': 'insufficient_features'}
        
        X = duplication_df[available_features].fillna(0).values
        X_scaled = StandardScaler().fit_transform(X)
        
        n_clusters = min(5, max(2, len(duplication_df) // 10))
        
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.cluster_labels = self.kmeans.fit_predict(X_scaled)
        self.is_trained = True
        
        duplication_df['cluster'] = self.cluster_labels
        
        cluster_analysis = []
        for cluster_id in range(n_clusters):
            cluster_data = duplication_df[duplication_df['cluster'] == cluster_id]
            
            profile = {
                'cluster_id': cluster_id,
                'size': len(cluster_data),
                'avg_request_count': cluster_data['request_count'].mean(),
                'avg_interval_seconds': cluster_data['avg_interval_seconds'].mean(),
                'cache_priority': self._calculate_priority(cluster_data),
                'recommendation': self._cluster_recommendation(cluster_data),
                'endpoints': cluster_data['pattern'].head(5).tolist(),
            }
            cluster_analysis.append(profile)
        
        return {
            'status': 'success',
            'clusters': cluster_analysis,
            'cluster_labels': self.cluster_labels,
            'centroids': self.kmeans.cluster_centers_,
            'features_used': available_features,
            'data_with_clusters': duplication_df
        }
    
    @staticmethod
    def _calculate_priority(cluster_data: pd.DataFrame) -> str:
        """计算缓存优先级"""
        avg_count = cluster_data['request_count'].mean()
        avg_interval = cluster_data['avg_interval_seconds'].mean()
        avg_size = cluster_data['total_response_size'].mean()
        
        score = 0
        if avg_count >= 50:
            score += 3
        elif avg_count >= 20:
            score += 2
        elif avg_count >= 5:
            score += 1
        
        if avg_interval < 300:
            score += 3
        elif avg_interval < 3600:
            score += 2
        elif avg_interval < 86400:
            score += 1
        
        if avg_size >= 100000:
            score += 3
        elif avg_size >= 10000:
            score += 2
        elif avg_size >= 1000:
            score += 1
        
        if score >= 7:
            return 'critical'
        elif score >= 5:
            return 'high'
        elif score >= 3:
            return 'medium'
        else:
            return 'low'
    
    @staticmethod
    def _cluster_recommendation(cluster_data: pd.DataFrame) -> str:
        """生成集群推荐"""
        priority = DuplicationPredictor._calculate_priority(cluster_data)
        
        recommendations = {
            'critical': '关键缓存对象：建议使用内存缓存，设置较长TTL，考虑预热',
            'high': '高优先级缓存：建议常规缓存，中等TTL',
            'medium': '中优先级缓存：可选缓存，根据资源情况决定',
            'low': '低优先级缓存：不建议缓存或设置非常短的TTL'
        }
        
        return recommendations.get(priority, '根据实际情况决定是否缓存')
    
    def predict_future_duplication(self, pattern: str, 
                                   historical_intervals: List[float]) -> Dict[str, Any]:
        """预测未来的重复模式"""
        if len(historical_intervals) < 3:
            return {
                'status': 'insufficient_data',
                'message': '需要至少3个历史时间间隔才能进行预测'
            }
        
        intervals = np.array(historical_intervals)
        
        periodicity = detect_periodicity(intervals.tolist())
        
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        cv = std_interval / mean_interval if mean_interval > 0 else float('inf')
        
        next_24h = int(24 * 3600 / mean_interval) if mean_interval > 0 else 0
        next_7d = int(7 * 24 * 3600 / mean_interval) if mean_interval > 0 else 0
        
        trend = 'stable'
        if len(intervals) >= 5:
            recent = intervals[-3:].mean()
            earlier = intervals[:3].mean()
            if recent < earlier * 0.8:
                trend = 'increasing'
            elif recent > earlier * 1.2:
                trend = 'decreasing'
        
        redundancy = calculate_redundancy_ratio(intervals.tolist())
        
        return {
            'status': 'success',
            'pattern': pattern,
            'periodicity_detected': periodicity,
            'mean_interval_seconds': mean_interval,
            'std_interval_seconds': std_interval,
            'coefficient_of_variation': cv,
            'trend': trend,
            'redundancy_ratio': redundancy,
            'predicted_requests_next_24h': next_24h,
            'predicted_requests_next_7d': next_7d,
            'cache_benefit_score': max(0, min(1, (1 - cv) * (1 + redundancy) / 2))
        }
