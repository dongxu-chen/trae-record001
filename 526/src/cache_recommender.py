import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import numpy as np

from .log_analyzer import AccessLogAnalyzer, LogEntry
from .ml_predictor import CachePredictor, TTLOptimizer, DuplicationPredictor, PredictionResult
from .bloom_filter import CacheBloomFilter, PenetrationProtector, HotDataPreloader
from .utils import (
    format_size,
    generate_cache_key,
    extract_fields_from_response,
    calculate_size_bytes,
    serialize_fields,
    deserialize_fields,
    calculate_hotness_score,
    select_hot_fields,
    DATA_FRESHNESS_TAGS,
    classify_data_freshness,
    compute_content_hash,
    normalize_params,
    CacheMetrics,
    AdaptiveStrategyConfig,
    StrategyAdjustment,
    WarmupSimulationResult,
    CachePenetrationProtection,
    calculate_cache_metrics,
    recommend_strategy_adjustment,
    simulate_cache_warmup,
    identify_penetration_risks,
    generate_preload_plan
)


@dataclass
class CacheRecommendation:
    """缓存推荐结果"""
    endpoint: str
    cache_level: str
    recommended_action: str
    predicted_hit_rate: float
    recommended_ttl: int
    estimated_savings_bytes: int
    estimated_savings_percent: float
    fields_to_cache: List[str] = field(default_factory=list)
    fields_to_exclude: List[str] = field(default_factory=list)
    priority: str = "medium"
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)
    freshness_tag: str = "dynamic"
    freshness_description: str = ""
    content_hash: str = ""
    normalized_params: Dict[str, Any] = field(default_factory=dict)
    hot_fields: List[str] = field(default_factory=list)
    serialized_size_bytes: int = 0
    original_size_bytes: int = 0
    serialization_savings_percent: float = 0.0


@dataclass
class CacheBenefitAnalysis:
    """缓存收益分析"""
    total_requests: int
    cacheable_requests: int
    estimated_hit_rate: float
    estimated_savings_bytes: int
    estimated_savings_percent: float
    estimated_latency_reduction_ms: float
    top_endpoints: List[Dict[str, Any]]
    recommendations: List[CacheRecommendation]
    bloom_filter_stats: Dict[str, Any]
    content_hash_duplication: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldLevelCacheRecommendation:
    """字段级缓存推荐"""
    field_path: str
    redundancy_ratio: float
    unique_values: int
    total_values: int
    recommended_action: str
    estimated_savings_bytes: int
    hotness_score: float = 0.0
    combined_score: float = 0.0
    access_count: int = 0
    avg_access_interval_seconds: float = 0.0


class CacheStrategyEngine:
    """缓存策略推荐引擎"""
    
    def __init__(self):
        self.analyzer = AccessLogAnalyzer()
        self.cache_predictor = CachePredictor()
        self.ttl_optimizer = TTLOptimizer()
        self.duplication_predictor = DuplicationPredictor()
        self.bloom_filter = CacheBloomFilter()
        
        self.cache_levels = ['response', 'field', 'none']
        self.priority_levels = ['critical', 'high', 'medium', 'low']
    
    def load_logs(self, filepath: str) -> int:
        """加载日志文件"""
        count = self.analyzer.load_logs(filepath)
        self._populate_bloom_filter()
        return count
    
    def load_entries(self, entries: List[LogEntry]) -> int:
        """加载日志条目"""
        count = self.analyzer.load_entries(entries)
        self._populate_bloom_filter()
        return count
    
    def _populate_bloom_filter(self) -> None:
        """用日志数据填充布隆过滤器"""
        entries = self.analyzer.get_entries()
        for entry in entries:
            fields = None
            if entry.response_body:
                fields = extract_fields_from_response(entry.response_body)
            self.bloom_filter.record_request(entry.endpoint, fields)
    
    def train_models(self) -> Dict[str, Any]:
        """训练所有模型"""
        df = self.analyzer.get_requests_dataframe()
        if df is None or df.empty:
            return {'error': 'no_data'}
        
        duplication_stats = self.analyzer.analyze_duplication_patterns()
        features_df = self.cache_predictor.prepare_features(
            df, 
            duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
        )
        
        training_results = {}
        
        try:
            training_results['cache_predictor'] = self.cache_predictor.train(features_df)
        except Exception as e:
            training_results['cache_predictor'] = {'error': str(e)}
        
        dup_stats = duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
        if not dup_stats.empty:
            try:
                training_results['duplication'] = self.duplication_predictor.analyze_patterns(dup_stats)
            except Exception as e:
                training_results['duplication'] = {'error': str(e)}
        
        return training_results
    
    def analyze_cache_benefit(self) -> CacheBenefitAnalysis:
        """分析缓存收益（含内容哈希重复识别和按需序列化）"""
        basic_stats = self.analyzer.get_basic_stats()
        if not basic_stats:
            return CacheBenefitAnalysis(
                total_requests=0,
                cacheable_requests=0,
                estimated_hit_rate=0.0,
                estimated_savings_bytes=0,
                estimated_savings_percent=0.0,
                estimated_latency_reduction_ms=0.0,
                top_endpoints=[],
                recommendations=[],
                bloom_filter_stats={}
            )
        
        df = self.analyzer.get_requests_dataframe()
        duplication_stats = self.analyzer.analyze_duplication_patterns()
        similarity_analysis = self.analyzer.analyze_response_similarity()
        content_hash_dup = self.analyzer.analyze_content_hash_duplication()
        
        features_df = self.cache_predictor.prepare_features(
            df, 
            duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
        )
        
        predictions = self.cache_predictor.predict(features_df)
        
        recommendations = self._generate_recommendations(
            features_df,
            predictions,
            duplication_stats,
            similarity_analysis,
            content_hash_dup
        )
        
        cacheable_requests = sum(
            1 for r in recommendations if r.cache_level in ['response', 'field']
        )
        
        total_savings = sum(r.estimated_savings_bytes for r in recommendations)
        total_savings += content_hash_dup.get('potential_savings_bytes', 0)
        avg_hit_rate = np.mean([r.predicted_hit_rate for r in recommendations]) if recommendations else 0.0
        
        latency_reduction = self._estimate_latency_reduction(
            recommendations, basic_stats
        )
        
        top_endpoints = self._get_top_cacheable_endpoints(
            duplication_stats, basic_stats
        )
        
        return CacheBenefitAnalysis(
            total_requests=basic_stats['total_requests'],
            cacheable_requests=cacheable_requests,
            estimated_hit_rate=avg_hit_rate,
            estimated_savings_bytes=total_savings,
            estimated_savings_percent=(total_savings / basic_stats['total_response_size']) 
                if basic_stats['total_response_size'] > 0 else 0,
            estimated_latency_reduction_ms=latency_reduction,
            top_endpoints=top_endpoints,
            recommendations=recommendations,
            bloom_filter_stats=self.bloom_filter.get_stats(),
            content_hash_duplication=content_hash_dup
        )
    
    def _generate_recommendations(self, features_df: pd.DataFrame,
                                  predictions: List[PredictionResult],
                                  duplication_stats: Dict[str, Any],
                                  similarity_analysis: Dict[str, Any],
                                  content_hash_dup: Dict[str, Any] = None) -> List[CacheRecommendation]:
        """生成缓存推荐（含按需序列化和热点字段缓存）"""
        recommendations = []
        
        unique_patterns = features_df['pattern'].unique()
        
        for i, pattern in enumerate(unique_patterns):
            pattern_data = features_df[features_df['pattern'] == pattern]
            if pattern_data.empty:
                continue
            
            prediction = predictions[min(i, len(predictions) - 1)]
            
            dup_stat = None
            dup_df = duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
            if not dup_df.empty and pattern in dup_df['pattern'].values:
                dup_stat = dup_df[dup_df['pattern'] == pattern].iloc[0]
            
            request_count = len(pattern_data)
            avg_response_size = pattern_data['response_size'].mean()
            avg_response_time = pattern_data['response_time_ms'].mean()
            
            avg_interval = pattern_data.get('avg_interval_seconds', 3600)
            if isinstance(avg_interval, pd.Series):
                avg_interval = avg_interval.mean()
            
            field_recommendations = self._get_field_level_recommendations(
                pattern, similarity_analysis, request_count, avg_interval
            )
            
            field_stats = [{
                'field_path': f.field_path,
                'request_count': f.access_count,
                'avg_interval_seconds': f.avg_access_interval_seconds,
                'redundancy_ratio': f.redundancy_ratio
            } for f in field_recommendations]
            
            hot_fields = select_hot_fields(field_stats, hotness_threshold=0.3, max_fields=20)
            
            cache_level, fields_to_cache, fields_to_exclude = self._determine_cache_level(
                pattern, request_count, prediction.cache_hit_probability,
                similarity_analysis, pattern_data, field_recommendations, hot_fields
            )
            
            priority = self._determine_priority(
                request_count, avg_response_size, prediction.cache_hit_probability
            )
            
            estimated_savings = self._calculate_savings(
                request_count, avg_response_size, prediction.cache_hit_probability,
                cache_level, fields_to_cache, pattern_data
            )
            
            sample_response = None
            entries = self.analyzer.get_entries()
            pattern_entries = [e for e in entries if e.endpoint.startswith(pattern.split('/{')[0])]
            if pattern_entries and pattern_entries[0].response_body:
                sample_response = pattern_entries[0].response_body
            
            original_size = calculate_size_bytes(sample_response) if sample_response else int(avg_response_size)
            serialized_data = serialize_fields(sample_response, fields_to_cache) if cache_level == 'field' else {}
            serialized_size = calculate_size_bytes(serialized_data)
            serialization_savings = (1 - serialized_size / original_size) if original_size > 0 else 0
            
            reasoning = self._generate_reasoning(
                pattern, request_count, prediction, cache_level,
                fields_to_cache, priority, dup_stat, field_recommendations, hot_fields
            )
            
            content_hash = ""
            normalized_params = {}
            if not pattern_data.empty:
                first_row = pattern_data.iloc[0]
                content_hash = first_row.get('content_hash', '')
                norm_params_str = first_row.get('normalized_params', '{}')
                if isinstance(norm_params_str, str):
                    normalized_params = json.loads(norm_params_str)
            
            recommendation = CacheRecommendation(
                endpoint=pattern,
                cache_level=cache_level,
                recommended_action=self._get_recommended_action(cache_level, priority),
                predicted_hit_rate=prediction.cache_hit_probability,
                recommended_ttl=prediction.predicted_ttl_seconds,
                estimated_savings_bytes=estimated_savings,
                estimated_savings_percent=(estimated_savings / (request_count * avg_response_size)) 
                    if (request_count * avg_response_size) > 0 else 0,
                fields_to_cache=fields_to_cache,
                fields_to_exclude=fields_to_exclude,
                priority=priority,
                confidence=prediction.confidence_score,
                reasoning=reasoning,
                freshness_tag=prediction.freshness_tag,
                freshness_description=prediction.freshness_description,
                content_hash=content_hash,
                normalized_params=normalized_params,
                hot_fields=hot_fields,
                serialized_size_bytes=serialized_size,
                original_size_bytes=original_size,
                serialization_savings_percent=serialization_savings
            )
            
            recommendations.append(recommendation)
        
        recommendations.sort(key=lambda x: x.estimated_savings_bytes, reverse=True)
        
        return recommendations
    
    def _determine_cache_level(self, pattern: str, request_count: int,
                               hit_probability: float,
                               similarity_analysis: Dict[str, Any],
                               pattern_data: pd.DataFrame,
                               field_recommendations: List = None,
                               hot_fields: List[str] = None) -> Tuple[str, List[str], List[str]]:
        """确定缓存级别（结合热点字段和按需序列化）"""
        if request_count < 2 or hit_probability < 0.1:
            return 'none', [], []
        
        if field_recommendations is None:
            avg_interval = pattern_data.get('avg_interval_seconds', 3600)
            if isinstance(avg_interval, pd.Series):
                avg_interval = avg_interval.mean()
            field_recommendations = self._get_field_level_recommendations(
                pattern, similarity_analysis, request_count, avg_interval
            )
        
        if hot_fields is None:
            field_stats = [{
                'field_path': f.field_path,
                'request_count': f.access_count,
                'avg_interval_seconds': f.avg_access_interval_seconds,
                'redundancy_ratio': f.redundancy_ratio
            } for f in field_recommendations]
            hot_fields = select_hot_fields(field_stats, hotness_threshold=0.3, max_fields=20)
        
        high_redundancy_fields = [
            f for f in field_recommendations 
            if f.recommended_action == 'cache' and f.redundancy_ratio > 0.7
        ]
        
        hot_high_redundancy = [
            f for f in high_redundancy_fields
            if f.field_path in hot_fields
        ]
        
        partial_redundancy_fields = [
            f for f in field_recommendations
            if 0.3 <= f.redundancy_ratio <= 0.7
        ]
        
        hot_partial_redundancy = [
            f for f in partial_redundancy_fields
            if f.field_path in hot_fields
        ]
        
        low_redundancy_fields = [
            f for f in field_recommendations
            if f.redundancy_ratio < 0.3
        ]
        
        non_hot_fields = [
            f for f in field_recommendations
            if f.field_path not in hot_fields
        ]
        
        freshness_tag = pattern_data['freshness_tag'].iloc[0] if 'freshness_tag' in pattern_data.columns else 'dynamic'
        freshness_info = DATA_FRESHNESS_TAGS.get(freshness_tag, DATA_FRESHNESS_TAGS['dynamic'])
        
        if freshness_tag in ['realtime', 'near_realtime']:
            if hot_high_redundancy and len(hot_high_redundancy) >= 2:
                return (
                    'field',
                    [f.field_path for f in hot_high_redundancy],
                    [f.field_path for f in low_redundancy_fields + non_hot_fields]
                )
            else:
                return 'none', [], []
        
        if hit_probability >= 0.7 and request_count >= 10:
            if hot_fields and len(hot_fields) >= 5:
                return (
                    'field',
                    hot_fields,
                    [f.field_path for f in low_redundancy_fields + non_hot_fields]
                )
            return 'response', [], []
        
        elif hot_high_redundancy and len(hot_high_redundancy) >= 2:
            return (
                'field',
                [f.field_path for f in hot_high_redundancy],
                [f.field_path for f in low_redundancy_fields + non_hot_fields]
            )
        elif hot_partial_redundancy and hit_probability >= 0.3:
            return (
                'field',
                [f.field_path for f in hot_partial_redundancy if f.redundancy_ratio > 0.5],
                [f.field_path for f in low_redundancy_fields + non_hot_fields]
            )
        elif hit_probability >= 0.5:
            return 'response', [], []
        else:
            return 'none', [], []
    
    def _get_field_level_recommendations(self, pattern: str,
                                         similarity_analysis: Dict[str, Any],
                                         endpoint_request_count: int = 0,
                                         endpoint_avg_interval: float = 3600
                                         ) -> List[FieldLevelCacheRecommendation]:
        """获取字段级缓存推荐（含热度评分）"""
        recommendations = []
        
        sim_details = similarity_analysis.get('similarity_details', pd.DataFrame())
        if sim_details.empty or pattern not in sim_details['pattern'].values:
            return recommendations
        
        pattern_row = sim_details[sim_details['pattern'] == pattern].iloc[0]
        field_redundancy = pattern_row.get('field_redundancy', {})
        
        for field_path, data in field_redundancy.items():
            redundancy = data.get('redundancy_ratio', 0)
            total_values = data.get('values_count', 0)
            unique_values = data.get('unique_values', 0)
            
            if redundancy >= 0.7:
                action = 'cache'
            elif redundancy >= 0.3:
                action = 'consider'
            else:
                action = 'exclude'
            
            field_access_count = int(endpoint_request_count * (redundancy + 0.1))
            field_avg_interval = endpoint_avg_interval / (redundancy + 0.5)
            
            hotness = calculate_hotness_score(field_access_count, field_avg_interval)
            combined_score = hotness * 0.7 + redundancy * 0.3
            
            estimated_savings = int(
                total_values * 100 * redundancy * (1 + hotness * 0.5)
            )
            
            recommendations.append(FieldLevelCacheRecommendation(
                field_path=field_path,
                redundancy_ratio=redundancy,
                unique_values=unique_values,
                total_values=total_values,
                recommended_action=action,
                estimated_savings_bytes=estimated_savings,
                hotness_score=hotness,
                combined_score=combined_score,
                access_count=field_access_count,
                avg_access_interval_seconds=field_avg_interval
            ))
        
        recommendations.sort(key=lambda x: x.redundancy_ratio, reverse=True)
        return recommendations
    
    def _determine_priority(self, request_count: int, avg_size: float,
                            hit_probability: float) -> str:
        """确定缓存优先级"""
        score = 0
        
        if request_count >= 100:
            score += 3
        elif request_count >= 50:
            score += 2
        elif request_count >= 10:
            score += 1
        
        if avg_size >= 100000:
            score += 3
        elif avg_size >= 10000:
            score += 2
        elif avg_size >= 1000:
            score += 1
        
        if hit_probability >= 0.8:
            score += 3
        elif hit_probability >= 0.5:
            score += 2
        elif hit_probability >= 0.3:
            score += 1
        
        if score >= 7:
            return 'critical'
        elif score >= 5:
            return 'high'
        elif score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_savings(self, request_count: int, avg_size: float,
                           hit_probability: float, cache_level: str,
                           fields_to_cache: List[str],
                           pattern_data: pd.DataFrame) -> int:
        """计算预期节省量"""
        if cache_level == 'none':
            return 0
        
        hit_count = int(request_count * hit_probability)
        
        if cache_level == 'response':
            saving_per_hit = avg_size
        elif cache_level == 'field' and fields_to_cache:
            field_ratio = min(0.8, len(fields_to_cache) / max(1, len(fields_to_cache) + 5))
            saving_per_hit = avg_size * field_ratio
        else:
            saving_per_hit = avg_size * 0.5
        
        return int(hit_count * saving_per_hit)
    
    def _generate_reasoning(self, pattern: str, request_count: int,
                            prediction: PredictionResult, cache_level: str,
                            fields_to_cache: List[str], priority: str,
                            dup_stat: Optional[pd.Series],
                            field_recommendations: List = None,
                            hot_fields: List[str] = None) -> List[str]:
        """生成推荐理由（含热点字段、序列化、时效性标签说明）"""
        reasoning = []
        
        reasoning.append(f"该端点共有 {request_count} 次请求")
        
        if prediction.freshness_tag:
            freshness_info = DATA_FRESHNESS_TAGS.get(
                prediction.freshness_tag, DATA_FRESHNESS_TAGS['dynamic']
            )
            reasoning.append(
                f"数据时效性: {prediction.freshness_tag} - {freshness_info.description}"
            )
            reasoning.append(
                f"TTL范围约束: {freshness_info.min_ttl_seconds}秒 ~ {freshness_info.max_ttl_seconds}秒"
            )
        
        if prediction.cache_hit_probability >= 0.7:
            reasoning.append(f"预测缓存命中率较高 ({prediction.cache_hit_probability:.1%})")
        elif prediction.cache_hit_probability >= 0.3:
            reasoning.append(f"预测缓存命中率中等 ({prediction.cache_hit_probability:.1%})")
        else:
            reasoning.append(f"预测缓存命中率较低 ({prediction.cache_hit_probability:.1%})")
        
        if cache_level == 'response':
            reasoning.append("建议使用响应级缓存，缓存整个响应体")
        elif cache_level == 'field':
            if fields_to_cache:
                hot_count = len([f for f in fields_to_cache if f in (hot_fields or [])])
                reasoning.append(
                    f"建议使用字段级缓存，缓存 {len(fields_to_cache)} 个字段"
                    f"（其中 {hot_count} 个为热点字段）"
                )
                reasoning.append(f"缓存字段包括: {', '.join(fields_to_cache[:3])}" + 
                               ("..." if len(fields_to_cache) > 3 else ""))
                
                if hot_fields:
                    reasoning.append(
                        f"识别到 {len(hot_fields)} 个热点字段，优先缓存以最大化收益"
                    )
        else:
            if prediction.freshness_tag in ['realtime', 'near_realtime']:
                reasoning.append("不建议缓存：数据时效性要求高，缓存可能导致数据过期")
            else:
                reasoning.append("不建议缓存，重复度不足或命中率过低")
        
        if priority == 'critical':
            reasoning.append("优先级：关键 - 应立即实施缓存")
        elif priority == 'high':
            reasoning.append("优先级：高 - 建议尽快实施缓存")
        elif priority == 'medium':
            reasoning.append("优先级：中 - 可根据资源情况实施")
        else:
            reasoning.append("优先级：低 - 可暂不实施")
        
        if dup_stat is not None:
            avg_interval = dup_stat.get('avg_interval_seconds', 0)
            if avg_interval < 60:
                reasoning.append(f"请求频率很高（平均每 {avg_interval:.0f} 秒1次）")
            elif avg_interval < 3600:
                reasoning.append(f"请求频率中等（平均每 {avg_interval/60:.0f} 分钟1次）")
        
        reasoning.append(f"推荐TTL: {prediction.predicted_ttl_seconds}秒")
        reasoning.append(f"置信度: {prediction.confidence_score:.1%}")
        
        if prediction.content_hash:
            reasoning.append(f"内容哈希: {prediction.content_hash[:16]}...")
        
        return reasoning
    
    @staticmethod
    def _get_recommended_action(cache_level: str, priority: str) -> str:
        """获取推荐动作"""
        if cache_level == 'none':
            return 'do_not_cache'
        
        actions = {
            'critical': 'cache_immediately',
            'high': 'cache_soon',
            'medium': 'cache_when_possible',
            'low': 'evaluate_later'
        }
        
        return actions.get(priority, 'evaluate_later')
    
    def _estimate_latency_reduction(self, recommendations: List[CacheRecommendation],
                                    basic_stats: Dict[str, Any]) -> float:
        """估计延迟减少量"""
        if not recommendations:
            return 0.0
        
        total_latency_saved = 0.0
        total_requests = basic_stats.get('total_requests', 0)
        
        for rec in recommendations:
            if rec.cache_level in ['response', 'field']:
                hit_count = total_requests * rec.predicted_hit_rate
                avg_latency = basic_stats.get('avg_response_time_ms', 100)
                
                cache_hit_latency = avg_latency * 0.1
                latency_saved_per_hit = avg_latency - cache_hit_latency
                
                total_latency_saved += hit_count * latency_saved_per_hit
        
        return total_latency_saved / total_requests if total_requests > 0 else 0.0
    
    def _get_top_cacheable_endpoints(self, duplication_stats: Dict[str, Any],
                                     basic_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取Top可缓存端点"""
        dup_df = duplication_stats.get('endpoint_duplication_stats', pd.DataFrame())
        if dup_df.empty:
            return []
        
        top = dup_df.head(10).copy()
        
        results = []
        for _, row in top.iterrows():
            saving_potential = row['total_response_size'] * 0.7
            
            results.append({
                'pattern': row['pattern'],
                'request_count': int(row['request_count']),
                'total_response_size': int(row['total_response_size']),
                'avg_interval_seconds': float(row.get('avg_interval_seconds', 0)),
                'saving_potential': int(saving_potential),
                'saving_potential_formatted': format_size(int(saving_potential))
            })
        
        return results
    
    def optimize_ttl_for_endpoint(self, pattern: str, 
                                  current_metrics: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """为特定端点优化TTL"""
        df = self.analyzer.get_requests_dataframe()
        if df is None or df.empty:
            return None
        
        pattern_data = df[df['pattern'] == pattern]
        if pattern_data.empty:
            return None
        
        dup_stats = self.analyzer.analyze_duplication_patterns()
        dup_df = dup_stats.get('endpoint_duplication_stats', pd.DataFrame())
        
        dup_stat = None
        if not dup_df.empty and pattern in dup_df['pattern'].values:
            dup_stat = dup_df[dup_df['pattern'] == pattern].iloc[0]
        
        if current_metrics is None:
            current_metrics = {
                'request_count': len(pattern_data),
                'avg_interval_seconds': float(dup_stat.get('avg_interval_seconds', 3600)) if dup_stat is not None else 3600,
                'unique_users': pattern_data['user_id'].nunique(),
                'avg_response_size': pattern_data['response_size'].mean(),
                'avg_response_time': pattern_data['response_time_ms'].mean(),
                'hit_rate': 0.5,
                'eviction_rate': 0.1,
                'current_ttl': 300,
            }
        
        ttl_recommendation = self.ttl_optimizer.optimize(pattern, current_metrics)
        
        return {
            'endpoint': pattern,
            'current_ttl': ttl_recommendation.current_ttl,
            'recommended_ttl': ttl_recommendation.recommended_ttl,
            'recommended_ttl_formatted': self._format_ttl(ttl_recommendation.recommended_ttl),
            'expected_hit_rate_improvement': ttl_recommendation.expected_hit_rate_improvement,
            'expected_savings_percent': ttl_recommendation.expected_savings_percent,
            'reasoning': ttl_recommendation.reasoning,
            'current_metrics': current_metrics,
        }
    
    @staticmethod
    def _format_ttl(seconds: int) -> str:
        """格式化TTL显示"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时{seconds % 3600 // 60}分钟"
        else:
            return f"{seconds // 86400}天{seconds % 86400 // 3600}小时"
    
    def get_field_level_analysis(self, pattern: str) -> List[FieldLevelCacheRecommendation]:
        """获取特定端点的字段级分析"""
        similarity = self.analyzer.analyze_response_similarity()
        return self._get_field_level_recommendations(pattern, similarity)
    
    def check_cache_exists(self, endpoint: str) -> Dict[str, Any]:
        """使用布隆过滤器检查缓存是否可能存在"""
        return self.bloom_filter.check_endpoint_cache(endpoint)
    
    def export_recommendations(self, filepath: str) -> None:
        """导出推荐结果到JSON文件"""
        analysis = self.analyze_cache_benefit()
        
        export_data = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_requests': analysis.total_requests,
                'cacheable_requests': analysis.cacheable_requests,
                'estimated_hit_rate': analysis.estimated_hit_rate,
                'estimated_savings_bytes': analysis.estimated_savings_bytes,
                'estimated_savings_formatted': format_size(analysis.estimated_savings_bytes),
                'estimated_savings_percent': analysis.estimated_savings_percent,
                'estimated_latency_reduction_ms': analysis.estimated_latency_reduction_ms,
            },
            'recommendations': [
                {
                    'endpoint': r.endpoint,
                    'cache_level': r.cache_level,
                    'recommended_action': r.recommended_action,
                    'predicted_hit_rate': r.predicted_hit_rate,
                    'recommended_ttl': r.recommended_ttl,
                    'recommended_ttl_formatted': self._format_ttl(r.recommended_ttl),
                    'estimated_savings_bytes': r.estimated_savings_bytes,
                    'estimated_savings_formatted': format_size(r.estimated_savings_bytes),
                    'estimated_savings_percent': r.estimated_savings_percent,
                    'fields_to_cache': r.fields_to_cache,
                    'fields_to_exclude': r.fields_to_exclude,
                    'priority': r.priority,
                    'confidence': r.confidence,
                    'reasoning': r.reasoning,
                }
                for r in analysis.recommendations
            ],
            'bloom_filter_stats': analysis.bloom_filter_stats,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)


@dataclass
class AdaptiveStrategyResult:
    """自适应策略结果"""
    endpoint: str
    current_metrics: CacheMetrics
    recommended_adjustments: List[StrategyAdjustment]
    suggested_config: AdaptiveStrategyConfig
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    trend_analysis: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WarmupSimulationReport:
    """预热模拟报告"""
    overall_result: Dict[str, Any]
    endpoint_results: List[WarmupSimulationResult]
    preload_plan: List[Dict[str, Any]]
    total_estimated_memory_bytes: int
    total_estimated_hit_rate_improvement: float
    total_estimated_latency_improvement_ms: float


@dataclass
class PenetrationProtectionReport:
    """穿透防护报告"""
    protection_config: CachePenetrationProtection
    detected_risks: List[Dict[str, Any]]
    hot_data_preload_plan: List[Dict[str, Any]]
    bloom_filter_coverage: float
    null_value_cache_stats: Dict[str, Any]
    overall_risk_level: str = "low"


class AdaptiveCacheStrategyEngine:
    """自适应缓存策略引擎"""
    
    def __init__(self, base_engine: CacheStrategyEngine):
        self.base_engine = base_engine
        self.config = AdaptiveStrategyConfig()
        self.history_metrics: List[Dict[str, Any]] = []
        self.penetration_protector = PenetrationProtector()
        self.preloader = HotDataPreloader()
        
    def analyze_current_state(self) -> Dict[str, Any]:
        """分析当前缓存状态"""
        basic_stats = self.base_engine.analyzer.get_basic_stats()
        df = self.base_engine.analyzer.get_requests_dataframe()
        
        if df is None or df.empty:
            return {'error': 'no_data'}
        
        request_patterns = df.to_dict('records')
        
        simulated_history = []
        for _, row in df.iterrows():
            simulated_history.append({
                'endpoint': row.get('endpoint', ''),
                'cache_hit': row.get('hit_rate', 0.5) > 0.5,
                'latency_ms': row.get('response_time_ms', 100),
                'timestamp': row.get('timestamp', datetime.now())
            })
        
        metrics = calculate_cache_metrics(simulated_history)
        metrics.memory_usage_bytes = basic_stats.get('total_response_size', 0)
        metrics.memory_limit_bytes = 1024 * 1024 * 1024
        
        self.history_metrics.append({
            'timestamp': datetime.now(),
            **metrics.__dict__
        })
        
        if len(self.history_metrics) > 100:
            self.history_metrics = self.history_metrics[-100:]
        
        return {
            'current_metrics': metrics,
            'history_count': len(self.history_metrics),
            'basic_stats': basic_stats
        }
    
    def generate_adaptive_recommendations(self, 
                                            endpoint: str = None
                                            ) -> List[AdaptiveStrategyResult]:
        """生成自适应策略建议"""
        state = self.analyze_current_state()
        if 'error' in state:
            return []
        
        current_metrics = state['current_metrics']
        df = self.base_engine.analyzer.get_requests_dataframe()
        
        if endpoint:
            endpoints = [endpoint]
        else:
            endpoints = df['endpoint'].unique()[:10]
        
        results = []
        for ep in endpoints:
            ep_data = df[df['endpoint'] == ep]
            if ep_data.empty:
                continue
            
            endpoint_stats = {
                'endpoint': ep,
                'current_ttl': int(ep_data.get('recommended_ttl', 300).iloc[0] 
                                  if 'recommended_ttl' in ep_data.columns else 300),
                'hot_field_count': len(ep_data.columns),
                'cached_field_count': int(len(ep_data.columns) * 0.6),
                'request_count': len(ep_data)
            }
            
            adjustments = recommend_strategy_adjustment(
                current_metrics, self.config, endpoint_stats
            )
            
            trend_analysis = self._analyze_trends(ep)
            
            results.append(AdaptiveStrategyResult(
                endpoint=ep,
                current_metrics=current_metrics,
                recommended_adjustments=adjustments,
                suggested_config=self.config,
                trend_analysis=trend_analysis
            ))
        
        return results
    
    def _analyze_trends(self, endpoint: str) -> Dict[str, Any]:
        """分析趋势"""
        if len(self.history_metrics) < 3:
            return {'insufficient_data': True}
        
        recent = self.history_metrics[-3:]
        hit_rates = [m.get('hit_rate', 0) for m in recent]
        
        trend = 'stable'
        if hit_rates[-1] > hit_rates[0] * 1.1:
            trend = 'rising'
        elif hit_rates[-1] < hit_rates[0] * 0.9:
            trend = 'falling'
        
        return {
            'hit_rate_trend': trend,
            'hit_rate_change': hit_rates[-1] - hit_rates[0] if hit_rates else 0,
            'data_points': len(hit_rates)
        }
    
    def apply_adjustment(self, adjustment: StrategyAdjustment) -> bool:
        """应用策略调整"""
        if adjustment.adjustment_type == 'ttl_increase':
            self.config.min_ttl_seconds = max(
                self.config.min_ttl_seconds,
                int(adjustment.new_value * 0.8)
            )
            return True
        elif adjustment.adjustment_type == 'ttl_decrease':
            self.config.max_ttl_seconds = min(
                self.config.max_ttl_seconds,
                int(adjustment.new_value * 1.2)
            )
            return True
        
        return False
    
    def simulate_warmup(self, warmup_duration_minutes: int = 30
                        ) -> WarmupSimulationReport:
        """模拟缓存预热效果"""
        benefit = self.base_engine.analyze_cache_benefit()
        df = self.base_engine.analyzer.get_requests_dataframe()
        
        hot_data = []
        for rec in benefit.recommendations:
            if rec.cache_level != 'none':
                hot_data.append({
                    'endpoint': rec.endpoint,
                    'hotness': rec.confidence,
                    'hot_fields': rec.hot_fields,
                    'size_bytes': rec.original_size_bytes,
                    'request_count': len(df[df['endpoint'] == rec.endpoint]) 
                                     if df is not None else 0,
                    'recommended_ttl': rec.recommended_ttl
                })
        
        request_patterns = []
        if df is not None:
            for _, row in df.iterrows():
                request_patterns.append({
                    'endpoint': row.get('endpoint', ''),
                    'cache_hit': False,
                    'latency_ms': row.get('response_time_ms', 100)
                })
        
        overall_simulation = simulate_cache_warmup(
            request_patterns, hot_data, warmup_duration_minutes
        )
        
        endpoint_results = []
        for data in hot_data[:10]:
            ep_patterns = [r for r in request_patterns 
                          if r['endpoint'] == data['endpoint']]
            if ep_patterns:
                ep_result = simulate_cache_warmup(
                    ep_patterns, [data], warmup_duration_minutes
                )
                endpoint_results.append(ep_result)
        
        preload_plan = generate_preload_plan(hot_data, max_preload_count=50)
        
        total_memory = sum(d['size_bytes'] for d in hot_data)
        total_hit_rate_improvement = sum(
            r.hit_rate_improvement for r in endpoint_results
        ) / len(endpoint_results) if endpoint_results else 0
        total_latency_improvement = sum(
            r.latency_improvement_ms for r in endpoint_results
        ) / len(endpoint_results) if endpoint_results else 0
        
        return WarmupSimulationReport(
            overall_result={
                'original_hit_rate': overall_simulation.original_hit_rate,
                'warmed_hit_rate': overall_simulation.warmed_hit_rate,
                'hit_rate_improvement': overall_simulation.hit_rate_improvement
            },
            endpoint_results=endpoint_results,
            preload_plan=preload_plan,
            total_estimated_memory_bytes=total_memory,
            total_estimated_hit_rate_improvement=total_hit_rate_improvement,
            total_estimated_latency_improvement_ms=total_latency_improvement
        )
    
    def analyze_penetration_risks(self) -> PenetrationProtectionReport:
        """分析穿透风险"""
        df = self.base_engine.analyzer.get_requests_dataframe()
        benefit = self.base_engine.analyze_cache_benefit()
        
        request_history = []
        if df is not None:
            for _, row in df.iterrows():
                endpoint = row.get('endpoint', '')
                self.penetration_protector.record_key_access(endpoint, exists=True)
                request_history.append(endpoint)
        
        hot_data = []
        for rec in benefit.recommendations:
            if rec.cache_level != 'none':
                hot_data.append({
                    'endpoint': rec.endpoint,
                    'hotness': rec.confidence,
                    'hot_fields': rec.hot_fields,
                    'size_bytes': rec.original_size_bytes,
                    'request_count': len(df[df['endpoint'] == rec.endpoint]) 
                                     if df is not None else 0,
                    'recommended_ttl': rec.recommended_ttl
                })
        
        for data in hot_data:
            self.preloader.add_to_preload_queue(
                data['endpoint'],
                priority='high' if data['hotness'] > 0.7 else 'normal',
                estimated_load_time_ms=100
            )
        
        protection_config = CachePenetrationProtection()
        risks = identify_penetration_risks(
            [{'endpoint': k, 'cache_hit': True} for k in request_history],
            protection_config
        )
        
        stats = self.penetration_protector.get_stats()
        bloom_coverage = min(1.0, stats['hot_data_count'] / max(1, len(hot_data)))
        
        risk_level = 'low'
        high_risk_count = sum(1 for r in risks if r.get('risk_level') == 'high')
        if high_risk_count >= 3:
            risk_level = 'high'
        elif high_risk_count >= 1:
            risk_level = 'medium'
        
        preload_plan = self.preloader.simulate_preload(
            {d['endpoint']: 100 for d in hot_data},
            duration_minutes=30
        )
        
        return PenetrationProtectionReport(
            protection_config=protection_config,
            detected_risks=risks,
            hot_data_preload_plan=preload_plan.get('preloaded_keys', []),
            bloom_filter_coverage=bloom_coverage,
            null_value_cache_stats={
                'cached_count': stats['null_value_cache_size'],
                'ttl_seconds': protection_config.null_value_ttl_seconds
            },
            overall_risk_level=risk_level
        )
    
    def generate_hot_data_preload_plan(self, top_n: int = 100
                                      ) -> List[Dict[str, Any]]:
        """生成热点数据预加载计划"""
        benefit = self.base_engine.analyze_cache_benefit()
        df = self.base_engine.analyzer.get_requests_dataframe()
        
        hot_data = []
        for rec in benefit.recommendations:
            if rec.cache_level != 'none':
                hot_data.append({
                    'endpoint': rec.endpoint,
                    'hotness': rec.confidence,
                    'hot_fields': rec.hot_fields,
                    'size_bytes': rec.original_size_bytes,
                    'request_count': len(df[df['endpoint'] == rec.endpoint]) 
                                     if df is not None else 0,
                    'recommended_ttl': rec.recommended_ttl,
                    'priority': rec.priority,
                    'predicted_hit_rate': rec.predicted_hit_rate
                })
        
        return generate_preload_plan(hot_data, max_preload_count=top_n)
