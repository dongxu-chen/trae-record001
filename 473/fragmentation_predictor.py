import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math
from statistics_analyzer import MemoryTrendAnalyzer, MemoryHistoryPoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionModel(str, Enum):
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    WEIGHTED_AVERAGE = "weighted_average"


@dataclass
class FragmentationPrediction:
    node_id: str
    host: str
    port: int
    current_fragmentation_ratio: float
    predicted_fragmentation_ratio: float
    prediction_hours: int
    prediction_model: PredictionModel
    will_exceed_threshold: bool
    threshold: float
    hours_to_threshold: Optional[float]
    confidence_score: float
    trend_direction: str
    trend_slope: float
    prediction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'current_fragmentation_ratio': self.current_fragmentation_ratio,
            'predicted_fragmentation_ratio': self.predicted_fragmentation_ratio,
            'prediction_hours': self.prediction_hours,
            'prediction_model': self.prediction_model.value,
            'will_exceed_threshold': self.will_exceed_threshold,
            'threshold': self.threshold,
            'hours_to_threshold': self.hours_to_threshold,
            'confidence_score': self.confidence_score,
            'trend_direction': self.trend_direction,
            'trend_slope': self.trend_slope,
            'prediction_timestamp': self.prediction_timestamp
        }


@dataclass
class CostBenefitAnalysis:
    node_id: str
    host: str
    port: int
    estimated_memory_saved_mb: float
    estimated_duration_seconds: float
    estimated_cpu_usage_percent: float
    estimated_p99_latency_increase_ms: float
    benefit_cost_ratio: float
    net_benefit_score: float
    recommendation: str
    should_defrag: bool
    priority_score: float
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'estimated_memory_saved_mb': self.estimated_memory_saved_mb,
            'estimated_duration_seconds': self.estimated_duration_seconds,
            'estimated_cpu_usage_percent': self.estimated_cpu_usage_percent,
            'estimated_p99_latency_increase_ms': self.estimated_p99_latency_increase_ms,
            'benefit_cost_ratio': self.benefit_cost_ratio,
            'net_benefit_score': self.net_benefit_score,
            'recommendation': self.recommendation,
            'should_defrag': self.should_defrag,
            'priority_score': self.priority_score,
            'analysis_timestamp': self.analysis_timestamp
        }


class FragmentationPredictor:
    def __init__(self, trend_analyzer: MemoryTrendAnalyzer = None):
        self.trend_analyzer = trend_analyzer or MemoryTrendAnalyzer()
    
    def _linear_regression(self, x: List[float], y: List[float]) -> Tuple[float, float]:
        n = len(x)
        if n < 2:
            return 0.0, 0.0
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        denominator = n * sum_x2 - sum_x * sum_x
        
        if denominator == 0:
            return 0.0, sum_y / n if n > 0 else 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    def _exponential_smoothing(self, values: List[float], alpha: float = 0.3) -> float:
        if not values:
            return 0.0
        
        smoothed = values[0]
        for value in values[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        
        return smoothed
    
    def _weighted_average(self, values: List[float], weights: Optional[List[float]] = None) -> float:
        if not values:
            return 0.0
        
        if weights is None:
            weights = [i + 1 for i in range(len(values))]
        
        if len(weights) != len(values):
            weights = [i + 1 for i in range(len(values))]
        
        weighted_sum = sum(w * v for w, v in zip(weights, values))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def predict_fragmentation(self, node_id: str, hours: int = 24, 
                                threshold: float = 1.5,
                                model: PredictionModel = PredictionModel.LINEAR_REGRESSION,
                                min_data_points: int = 10) -> Optional[FragmentationPrediction]:
        logger.info(f"Predicting fragmentation for node {node_id} for {hours} hours")
        
        history = self.trend_analyzer.get_memory_history(node_id, hours=72)
        
        if len(history.fragmentation_ratios) < min_data_points:
            logger.warning(f"Insufficient data points ({len(history.fragmentation_ratios)}) for prediction")
            return None
        
        timestamps = [datetime.fromisoformat(ts) for ts in history.timestamps]
        ratios = history.fragmentation_ratios
        
        base_time = timestamps[0]
        x_hours = [(t - base_time).total_seconds() / 3600 for t in timestamps]
        
        current_ratio = ratios[-1]
        host = ''
        port = 0
        
        predicted_ratio = current_ratio
        slope = 0.0
        
        if model == PredictionModel.LINEAR_REGRESSION:
            slope, intercept = self._linear_regression(x_hours, ratios)
            predicted_ratio = slope * (x_hours[-1] + hours) + intercept
        
        elif model == PredictionModel.EXPONENTIAL_SMOOTHING:
            if len(ratios) >= 3:
                recent_ratios = ratios[-10:] if len(ratios) >= 10 else ratios
                last_smoothed = self._exponential_smoothing(recent_ratios)
                if len(ratios) >= 2:
                    time_diff = x_hours[-1] - x_hours[0] if x_hours[-1] != x_hours[0] else 1
                    slope = (recent_ratios[-1] - recent_ratios[0]) / time_diff
                predicted_ratio = last_smoothed + slope * hours
        
        elif model == PredictionModel.WEIGHTED_AVERAGE:
            if len(ratios) >= 5:
                recent_ratios = ratios[-20:] if len(ratios) >= 20 else ratios
                avg_change = []
                for i in range(1, len(recent_ratios)):
                    avg_change.append(recent_ratios[i] - recent_ratios[i - 1])
                avg_slope = sum(avg_change) / len(avg_change) if avg_change else 0
                slope = avg_slope
                predicted_ratio = recent_ratios[-1] + avg_slope * hours
        
        hours_to_threshold = None
        
        if slope > 0 and predicted_ratio > threshold:
            hours_to_threshold = (threshold - current_ratio) / slope if slope > 0 else float('inf')
        
        will_exceed = predicted_ratio >= threshold and slope > 0
        
        confidence = min(len(ratios) / 20.0, 1.0)
        
        trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
        
        return FragmentationPrediction(
            node_id=node_id,
            host=host,
            port=port,
            current_fragmentation_ratio=current_ratio,
            predicted_fragmentation_ratio=max(predicted_ratio, 1.0),
            prediction_hours=hours,
            prediction_model=model,
            will_exceed_threshold=will_exceed,
            threshold=threshold,
            hours_to_threshold=hours_to_threshold,
            confidence_score=confidence,
            trend_direction=trend_direction,
            trend_slope=slope
        )
    
    def predict_all_nodes(self, hours: int = 24, threshold: float = 1.5) -> List[FragmentationPrediction]:
        from redis_connection import RedisConnectionManager
        from memory_analyzer import MemoryAnalyzer
        
        conn_manager = RedisConnectionManager()
        nodes = conn_manager.get_all_nodes()
        
        predictions = []
        
        for node in nodes:
            try:
                prediction = self.predict_fragmentation(
                    node_id=node['id'], hours=hours, threshold=threshold
                )
                if prediction:
                    prediction.host = node['host']
                    prediction.port = node['port']
                    predictions.append(prediction)
            except Exception as e:
                logger.warning(f"Failed to predict for node {node['host']}:{node['port']}: {e}")
        
        return predictions
    
    def get_nodes_needing_defrag(self, hours: int = 24, threshold: float = 1.5) -> List[FragmentationPrediction]:
        predictions = self.predict_all_nodes(hours=hours, threshold=threshold)
        return [p for p in predictions if p.will_exceed_threshold]


class CostBenefitAnalyzer:
    def __init__(self, memory_saved_mb_per_hourly_cost: float = 0.01):
        self.memory_saved_mb_per_hourly_cost = memory_saved_mb_per_hourly_cost
    
    def analyze_cost_benefit(self, node_id: str, host: str, port: int,
                          current_fragmentation_mb: float,
                          current_qps: float,
                          current_p99_latency_ms: float = 0.0,
                          memory_price_per_gb_month: float = 0.02,
                          latency_sla_ms: float = 100.0) -> CostBenefitAnalysis:
        logger.info(f"Analyzing cost/benefit for node {host}:{port}")
        
        estimated_memory_saved_mb = max(current_fragmentation_mb * 0.6, 0)
        
        estimated_duration_seconds = estimated_memory_saved_mb * 0.1 + 30
        
        estimated_cpu_usage_percent = min(estimated_memory_saved_mb / 1000 * 5, 50.0)
        
        estimated_p99_latency_increase_ms = min(current_p99_latency_ms * 0.1 + 0.5, 10.0)
        
        memory_value_per_hour = (estimated_memory_saved_mb / 1024) * memory_price_per_gb_month / 730
        
        cpu_cost_per_hour = estimated_cpu_usage_percent / 100 * 0.5
        
        latency_cost_per_hour = (estimated_p99_latency_increase_ms / latency_sla_ms) * current_qps * 0.0001
        
        total_cost_per_hour = cpu_cost_per_hour + latency_cost_per_hour
        
        benefit_cost_ratio = memory_value_per_hour / max(total_cost_per_hour, 0.001)
        
        priority_score = estimated_memory_saved_mb * benefit_cost_ratio
        
        should_defrag = False
        recommendation = "No defragmentation"
        
        if estimated_memory_saved_mb < 100:
            recommendation = "Fragmentation too small, skip defragmentation"
        elif benefit_cost_ratio > 2.0 and estimated_p99_latency_increase_ms < 5.0:
            should_defrag = True
            recommendation = "Recommended to defragment"
        elif benefit_cost_ratio > 1.0:
            should_defrag = True
            recommendation = "Consider defragmentation"
        else:
            recommendation = "Monitor, benefit is low"
        
        return CostBenefitAnalysis(
            node_id=node_id,
            host=host,
            port=port,
            estimated_memory_saved_mb=estimated_memory_saved_mb,
            estimated_duration_seconds=estimated_duration_seconds,
            estimated_cpu_usage_percent=estimated_cpu_usage_percent,
            estimated_p99_latency_increase_ms=estimated_p99_latency_increase_ms,
            benefit_cost_ratio=benefit_cost_ratio,
            net_benefit_score=memory_value_per_hour - total_cost_per_hour,
            recommendation=recommendation,
            should_defrag=should_defrag,
            priority_score=priority_score
        )
    
    def analyze_all_nodes(self) -> List[CostBenefitAnalysis]:
        from redis_connection import RedisConnectionManager
        from memory_analyzer import MemoryAnalyzer
        
        conn_manager = RedisConnectionManager()
        analyzer = MemoryAnalyzer(conn_manager)
        memory_infos = analyzer.get_all_memory_info()
        
        analyses = []
        
        for mem_info in memory_infos:
            try:
                analysis = self.analyze_cost_benefit(
                    node_id=mem_info.node_id,
                    host=mem_info.host,
                    port=mem_info.port,
                    current_fragmentation_mb=mem_info.fragmentation_mb,
                    current_qps=mem_info.performance_metrics.qps,
                    current_p99_latency_ms=mem_info.performance_metrics.p99_latency_ms
                )
                analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze cost/benefit for {mem_info.host}:{mem_info.port}: {e}")
        
        return analyses
    
    def get_priority_defrag_list(self) -> List[CostBenefitAnalysis]:
        analyses = self.analyze_all_nodes()
        sorted_analyses = sorted(
            [a for a in analyses if a.should_defrag],
            key=lambda x: x.priority_score,
            reverse=True
        )
        return sorted_analyses
