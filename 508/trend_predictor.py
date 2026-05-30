import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

from es_collector import SlowQuery

logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    STABLE = "stable"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    VOLATILE = "volatile"
    SPIKING = "spiking"


class AlertLevel(Enum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TimeSeriesPoint:
    timestamp: float
    avg_response_ms: float
    query_count: int
    slow_query_count: int
    slow_ratio: float


@dataclass
class TrendPrediction:
    direction: TrendDirection
    predicted_avg_ms: float
    predicted_slow_count: int
    confidence: float
    alert_level: AlertLevel
    details: Dict[str, Any] = field(default_factory=dict)
    warning_message: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class QuerySourceStats:
    source_id: str
    query_count: int = 0
    slow_query_count: int = 0
    total_response_ms: float = 0.0
    avg_response_ms: float = 0.0
    last_seen: float = 0.0
    recent_slow_times: Deque[float] = field(default_factory=lambda: deque(maxlen=20))

    def record(self, response_ms: float, is_slow: bool):
        self.query_count += 1
        self.total_response_ms += response_ms
        self.avg_response_ms = self.total_response_ms / self.query_count
        self.last_seen = time.time()
        if is_slow:
            self.slow_query_count += 1
            self.recent_slow_times.append(response_ms)

    @property
    def slow_ratio(self) -> float:
        return self.slow_query_count / max(self.query_count, 1)


class TrendPredictor:
    def __init__(self,
                 history_window_minutes: int = 60,
                 prediction_window_minutes: int = 15,
                 slow_threshold_ms: float = 3000.0,
                 max_history_points: int = 120,
                 aggregation_interval_seconds: int = 60):
        self.history_window_minutes = history_window_minutes
        self.prediction_window_minutes = prediction_window_minutes
        self.slow_threshold_ms = slow_threshold_ms
        self.max_history_points = max_history_points
        self.aggregation_interval_seconds = aggregation_interval_seconds

        self.time_series: Deque[TimeSeriesPoint] = deque(maxlen=max_history_points)
        self.source_stats: Dict[str, QuerySourceStats] = {}
        self.current_window: List[SlowQuery] = []
        self.last_aggregation_time: float = time.time()
        self.index_stats: Dict[str, TimeSeriesPoint] = {}

    def record_query(self, slow_query: SlowQuery, source_id: str = "unknown"):
        self.current_window.append(slow_query)
        src_key = f"{slow_query.index_name}:{source_id}"
        if src_key not in self.source_stats:
            self.source_stats[src_key] = QuerySourceStats(source_id=src_key)
        self.source_stats[src_key].record(
            response_ms=slow_query.response_time_ms,
            is_slow=slow_query.response_time_ms > self.slow_threshold_ms,
        )

        if slow_query.index_name not in self.index_stats:
            self.index_stats[slow_query.index_name] = TimeSeriesPoint(
                timestamp=time.time(),
                avg_response_ms=0,
                query_count=0,
                slow_query_count=0,
                slow_ratio=0,
            )
        idx_stat = self.index_stats[slow_query.index_name]
        old_count = idx_stat.query_count
        idx_stat.avg_response_ms = (
            idx_stat.avg_response_ms * old_count + slow_query.response_time_ms
        ) / (old_count + 1)
        idx_stat.query_count += 1
        if slow_query.response_time_ms > self.slow_threshold_ms:
            idx_stat.slow_query_count += 1
        idx_stat.slow_ratio = idx_stat.slow_query_count / max(idx_stat.query_count, 1)

    def should_aggregate(self) -> bool:
        return (
            time.time() - self.last_aggregation_time
            >= self.aggregation_interval_seconds
        )

    def aggregate(self):
        if not self.current_window:
            point = TimeSeriesPoint(
                timestamp=time.time(),
                avg_response_ms=0,
                query_count=0,
                slow_query_count=0,
                slow_ratio=0,
            )
        else:
            total_ms = sum(q.response_time_ms for q in self.current_window)
            slow_count = sum(
                1 for q in self.current_window
                if q.response_time_ms > self.slow_threshold_ms
            )
            point = TimeSeriesPoint(
                timestamp=time.time(),
                avg_response_ms=total_ms / len(self.current_window),
                query_count=len(self.current_window),
                slow_query_count=slow_count,
                slow_ratio=slow_count / len(self.current_window),
            )
        self.time_series.append(point)
        self.current_window = []
        self.last_aggregation_time = time.time()
        logger.info(
            "Aggregated time series point: avg=%.1fms, count=%d, slow=%d, ratio=%.2f%%",
            point.avg_response_ms,
            point.query_count,
            point.slow_query_count,
            point.slow_ratio * 100,
        )
        return point

    def predict(self, index_name: Optional[str] = None) -> TrendPrediction:
        if self.should_aggregate():
            self.aggregate()

        data = self._get_data_for_prediction(index_name)
        if len(data) < 3:
            return TrendPrediction(
                direction=TrendDirection.STABLE,
                predicted_avg_ms=0,
                predicted_slow_count=0,
                confidence=0.0,
                alert_level=AlertLevel.NORMAL,
                warning_message="历史数据不足，无法进行趋势预测，至少需要 3 个时间窗口数据。",
                recommendations=[
                    "继续收集查询数据以建立历史基线",
                    "建议至少运行 5 个采集周期再进行预测分析",
                ],
            )

        (
            direction,
            predicted_avg,
            predicted_slow,
            confidence,
            details,
        ) = self._linear_regression_prediction(data)

        alert_level, warning, recommendations = self._assess_risk(
            direction, predicted_avg, predicted_slow, confidence, data
        )

        return TrendPrediction(
            direction=direction,
            predicted_avg_ms=predicted_avg,
            predicted_slow_count=predicted_slow,
            confidence=confidence,
            alert_level=alert_level,
            details=details,
            warning_message=warning,
            recommendations=recommendations,
        )

    def get_top_slow_sources(self, top_n: int = 10) -> List[Tuple[str, QuerySourceStats]]:
        sorted_sources = sorted(
            self.source_stats.items(),
            key=lambda x: (x[1].slow_ratio, x[1].avg_response_ms),
            reverse=True,
        )
        return sorted_sources[:top_n]

    def get_index_summaries(self) -> List[Dict[str, Any]]:
        summaries = []
        for idx, stats in self.index_stats.items():
            summaries.append({
                "index": idx,
                "total_queries": stats.query_count,
                "slow_queries": stats.slow_query_count,
                "slow_ratio": round(stats.slow_ratio * 100, 2),
                "avg_response_ms": round(stats.avg_response_ms, 2),
            })
        return sorted(summaries, key=lambda x: x["slow_ratio"], reverse=True)

    def generate_trend_report(self, index_name: Optional[str] = None) -> str:
        prediction = self.predict(index_name)
        target = index_name if index_name else "所有索引"

        alert_icons = {
            AlertLevel.NORMAL: "🟢",
            AlertLevel.WATCH: "🔵",
            AlertLevel.WARNING: "🟡",
            AlertLevel.CRITICAL: "🔴",
        }
        direction_labels = {
            TrendDirection.STABLE: "稳定",
            TrendDirection.INCREASING: "上升",
            TrendDirection.DECREASING: "下降",
            TrendDirection.VOLATILE: "波动",
            TrendDirection.SPIKING: "突增",
        }

        lines = [
            "=" * 70,
            f"📈 慢查询趋势预测报告 - {target}",
            "=" * 70,
            f"预警等级: {alert_icons.get(prediction.alert_level, '⚪')} "
            f"[{prediction.alert_level.value.upper()}]",
            f"趋势方向: {direction_labels.get(prediction.direction, '未知')}",
            f"置信度: {prediction.confidence * 100:.0f}%",
            "",
            f"未来 {self.prediction_window_minutes} 分钟预测:",
            f"  预测平均响应时间: {prediction.predicted_avg_ms:.1f}ms",
            f"  预测慢查询数量: {prediction.predicted_slow_count}",
            f"  慢查询阈值: {self.slow_threshold_ms}ms",
            "",
        ]

        if prediction.details:
            lines.append("历史数据统计:")
            for key, val in prediction.details.items():
                if isinstance(val, float):
                    lines.append(f"  {key}: {val:.2f}")
                else:
                    lines.append(f"  {key}: {val}")
            lines.append("")

        if prediction.warning_message:
            lines.append(f"⚠ {prediction.warning_message}")
            lines.append("")

        if prediction.recommendations:
            lines.append("💡 建议措施:")
            for i, rec in enumerate(prediction.recommendations, 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        top_sources = self.get_top_slow_sources(top_n=5)
        if top_sources:
            lines.append("🎯 慢查询来源 TOP 5 (慢查询比例):")
            for source_id, stats in top_sources:
                lines.append(
                    f"  - {source_id}: {stats.slow_ratio * 100:.1f}% "
                    f"(平均 {stats.avg_response_ms:.0f}ms, 共 {stats.slow_query_count} 次慢查询)"
                )
            lines.append("")

        idx_summaries = self.get_index_summaries()
        if idx_summaries:
            lines.append("📊 按索引汇总 (慢查询比例):")
            for s in idx_summaries[:5]:
                lines.append(
                    f"  - {s['index']}: {s['slow_ratio']}% "
                    f"({s['slow_queries']}/{s['total_queries']}, "
                    f"平均 {s['avg_response_ms']}ms)"
                )
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _get_data_for_prediction(self, index_name: Optional[str]) -> List[TimeSeriesPoint]:
        if index_name and index_name in self.index_stats:
            return [self.index_stats[index_name]]
        return list(self.time_series)

    def _linear_regression_prediction(
        self, data: List[TimeSeriesPoint]
    ) -> Tuple[TrendDirection, float, int, float, Dict[str, Any]]:
        n = len(data)
        if n < 2:
            return TrendDirection.STABLE, 0, 0, 0.0, {}

        xs = list(range(n))
        ys_rt = [p.avg_response_ms for p in data]
        ys_slow = [p.slow_query_count for p in data]

        slope_rt, intercept_rt, r2_rt = self._linreg(xs, ys_rt)
        slope_slow, intercept_slow, r2_slow = self._linreg(xs, ys_slow)

        predicted_x = n + self.prediction_window_minutes // max(
            self.aggregation_interval_seconds // 60, 1
        )
        predicted_avg = max(0, slope_rt * predicted_x + intercept_rt)
        predicted_slow = max(0, int(slope_slow * predicted_x + intercept_slow))

        avg_rt = sum(ys_rt) / n
        std_rt = math.sqrt(sum((y - avg_rt) ** 2 for y in ys_rt) / max(n - 1, 1))
        cv_rt = std_rt / max(avg_rt, 1)

        direction = TrendDirection.STABLE
        if slope_rt > self.slow_threshold_ms * 0.1:
            if cv_rt > 0.5:
                direction = TrendDirection.VOLATILE
            elif slope_rt > self.slow_threshold_ms * 0.3:
                direction = TrendDirection.SPIKING
            else:
                direction = TrendDirection.INCREASING
        elif slope_rt < -self.slow_threshold_ms * 0.05:
            direction = TrendDirection.DECREASING
        elif cv_rt > 0.3:
            direction = TrendDirection.VOLATILE

        confidence = (abs(r2_rt) + abs(r2_slow)) / 2
        confidence = max(0.0, min(1.0, confidence))

        details = {
            "historical_points": n,
            "historical_avg_ms": avg_rt,
            "historical_std_ms": std_rt,
            "coefficient_of_variation": cv_rt,
            "slope_response_ms": slope_rt,
            "slope_slow_count": slope_slow,
            "r_squared_response": r2_rt,
            "r_squared_slow_count": r2_slow,
            "historical_min_ms": min(ys_rt),
            "historical_max_ms": max(ys_rt),
            "historical_total_slow": sum(ys_slow),
        }

        return direction, predicted_avg, predicted_slow, confidence, details

    @staticmethod
    def _linreg(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
        n = len(xs)
        if n == 0:
            return 0.0, 0.0, 0.0

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        denominator = sum((x - mean_x) ** 2 for x in xs)

        if denominator == 0:
            return 0.0, mean_y, 0.0

        slope = numerator / denominator
        intercept = mean_y - slope * mean_x

        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
        ss_tot = sum((y - mean_y) ** 2 for y in ys)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0

        return slope, intercept, r_squared

    def _assess_risk(
        self,
        direction: TrendDirection,
        predicted_avg: float,
        predicted_slow: int,
        confidence: float,
        data: List[TimeSeriesPoint],
    ) -> Tuple[AlertLevel, str, List[str]]:
        threshold = self.slow_threshold_ms
        recommendations: List[str] = []
        warning = ""

        recent_data = data[-3:] if len(data) >= 3 else data
        recent_slow = sum(p.slow_query_count for p in recent_data)
        recent_avg = sum(p.avg_response_ms for p in recent_data) / max(len(recent_data), 1)

        if (
            direction == TrendDirection.SPIKING
            or (predicted_avg > threshold * 3 and confidence > 0.7)
            or recent_slow > 10
        ):
            alert_level = AlertLevel.CRITICAL
            warning = (
                f"检测到慢查询严重恶化趋势！"
                f"预测平均响应时间 {predicted_avg:.0f}ms (阈值 {threshold}ms)，"
                f"未来 {self.prediction_window_minutes} 分钟预计出现 {predicted_slow} 次慢查询。"
            )
            recommendations.extend([
                "立即介入排查，查看集群资源使用情况(CPU/内存/磁盘IO)",
                "启用自动限流保护，限制慢查询来源的请求速率",
                "检查热点索引和热点分片",
                "临时降低查询并发，或启用查询断路器",
                "立即开启 Elasticsearch Profile 分析慢查询详细原因",
            ])
        elif (
            direction == TrendDirection.INCREASING
            or (predicted_avg > threshold and confidence > 0.5)
            or recent_slow > 5
        ):
            alert_level = AlertLevel.WARNING
            warning = (
                f"慢查询呈上升趋势，需要关注。"
                f"预测平均响应时间 {predicted_avg:.0f}ms (阈值 {threshold}ms)。"
            )
            recommendations.extend([
                "分析慢查询来源，查看是否有新增的查询模式",
                "检查索引是否有数据量激增",
                "审查最近的索引变更（mapping 变更、分片调整）",
                "建议启用演练模式评估潜在的优化方案",
                "为高频查询考虑添加合适的缓存",
            ])
        elif direction == TrendDirection.VOLATILE or confidence < 0.5:
            alert_level = AlertLevel.WATCH
            warning = (
                f"查询性能波动较大或预测置信度较低({confidence * 100:.0f}%)，"
                f"建议持续观察。"
            )
            recommendations.extend([
                "增加监控频率，收集更多数据以提升预测置信度",
                "检查是否有周期性的查询模式（如定时任务）",
                "确认集群是否存在不稳定因素",
            ])
        elif direction == TrendDirection.DECREASING:
            alert_level = AlertLevel.NORMAL
            warning = "慢查询趋势下降，性能正在改善。"
            recommendations.extend([
                "继续保持监控",
                "分析优化措施的效果，总结可复用经验",
            ])
        else:
            alert_level = AlertLevel.NORMAL
            warning = "查询性能稳定，处于正常范围。"
            recommendations.extend([
                "保持正常监控",
                "定期 Review 查询模式和索引设计",
            ])

        if predicted_avg > threshold * 2:
            recommendations.append(
                f"预测响应时间 {predicted_avg:.0f}ms 超过阈值 {threshold}ms 的 2 倍，"
                f"建议排查是否存在: 深分页、脚本查询、模糊查询、高基数聚合等问题。"
            )

        if predicted_slow > 5:
            recommendations.append(
                f"预测慢查询数量 {predicted_slow} 较多，建议启动自动限流保护，"
                f"对慢查询来源 IP/应用进行请求速率限制。"
            )

        return alert_level, warning, recommendations
