#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评论趋势监控模块
监控评论质量变化，质量突降时告警
"""

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    QUALITY_DROP = "quality_drop"
    SPAM_SURGE = "spam_surge"
    FAKE_REVIEW_SURGE = "fake_review_surge"
    RATING_MANIPULATION = "rating_manipulation"
    SENTIMENT_SHIFT = "sentiment_shift"
    VOLUME_ANOMALY = "volume_anomaly"
    COMPETITOR_ATTACK = "competitor_attack"


@dataclass
class QualityDataPoint:
    timestamp: datetime
    quality_score: float
    review_count: int
    avg_rating: float
    fake_review_count: int
    fake_review_ratio: float
    avg_usefulness: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAlert:
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    timestamp: datetime
    description: str
    product_id: str
    metric_name: str
    current_value: float
    expected_value: float
    change_percent: float
    threshold: float
    historical_context: Dict[str, Any] = field(default_factory=dict)
    is_handled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'description': self.description,
            'product_id': self.product_id,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'expected_value': self.expected_value,
            'change_percent': self.change_percent,
            'threshold': self.threshold,
            'is_handled': self.is_handled
        }


@dataclass
class TrendAnalysisResult:
    product_id: str
    time_span: Dict[str, datetime]
    overall_trend: str
    trend_slope: float
    alerts: List[TrendAlert]
    statistics: Dict[str, Any]
    quality_forecast: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'time_span': {
                'start': self.time_span['start'].isoformat(),
                'end': self.time_span['end'].isoformat()
            },
            'overall_trend': self.overall_trend,
            'trend_slope': self.trend_slope,
            'alerts': [a.to_dict() for a in self.alerts],
            'statistics': self.statistics,
            'quality_forecast': self.quality_forecast
        }


@dataclass
class MonitorConfig:
    window_size_hours: int = 24
    min_data_points: int = 10
    quality_drop_threshold: float = 0.15
    quality_warning_threshold: float = 0.10
    rating_drop_threshold: float = 0.5
    fake_review_surge_threshold: float = 0.20
    volume_surge_threshold: float = 2.0
    sentiment_shift_threshold: float = 0.20
    cusum_threshold: float = 3.0
    min_reviews_for_alert: int = 5
    alert_cooldown_hours: int = 6


class CommentTrendMonitor:
    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.data_store: Dict[str, List[QualityDataPoint]] = defaultdict(list)
        self.alerts: Dict[str, List[TrendAlert]] = defaultdict(list)
        self.alert_timestamps: Dict[str, datetime] = {}
        self.sliding_windows: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )

    def add_quality_data(
        self,
        product_id: str,
        quality_score: float,
        timestamp: Optional[datetime] = None,
        avg_rating: float = 0.0,
        fake_review_count: int = 0,
        fake_review_ratio: float = 0.0,
        avg_usefulness: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        timestamp = timestamp or datetime.now()
        metadata = metadata or {}

        data_point = QualityDataPoint(
            timestamp=timestamp,
            quality_score=quality_score,
            review_count=metadata.get('review_count', 1),
            avg_rating=avg_rating,
            fake_review_count=fake_review_count,
            fake_review_ratio=fake_review_ratio,
            avg_usefulness=avg_usefulness,
            metadata=metadata
        )

        self.data_store[product_id].append(data_point)
        self.sliding_windows[product_id].append(data_point)
        self.data_store[product_id].sort(key=lambda x: x.timestamp)

    def analyze_trends(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ) -> TrendAnalysisResult:
        window_hours = time_window_hours or self.config.window_size_hours
        data = self._get_recent_data(product_id, window_hours)

        if len(data) < self.config.min_data_points:
            return TrendAnalysisResult(
                product_id=product_id,
                time_span={'start': datetime.now(), 'end': datetime.now()},
                overall_trend='insufficient_data',
                trend_slope=0.0,
                alerts=[],
                statistics={'data_points': len(data)}
            )

        alerts = []

        quality_scores = [d.quality_score for d in data]
        avg_ratings = [d.avg_rating for d in data]
        fake_ratios = [d.fake_review_ratio for d in data]
        review_counts = [d.review_count for d in data]

        quality_trend, quality_slope = self._calculate_trend(quality_scores)

        quality_drop_alert = self._detect_quality_drop(product_id, data, quality_scores)
        if quality_drop_alert:
            alerts.append(quality_drop_alert)

        rating_alert = self._detect_rating_manipulation(product_id, data, avg_ratings)
        if rating_alert:
            alerts.append(rating_alert)

        fake_surge_alert = self._detect_fake_review_surge(product_id, data, fake_ratios)
        if fake_surge_alert:
            alerts.append(fake_surge_alert)

        volume_alert = self._detect_volume_anomaly(product_id, data, review_counts)
        if volume_alert:
            alerts.append(volume_alert)

        sentiment_alert = self._detect_sentiment_shift(product_id, data, quality_scores)
        if sentiment_alert:
            alerts.append(sentiment_alert)

        competitor_alert = self._detect_competitor_attack(product_id, data)
        if competitor_alert:
            alerts.append(competitor_alert)

        cusum_alert = self._detect_cusum_change(product_id, data, quality_scores)
        if cusum_alert:
            alerts.append(cusum_alert)

        for alert in alerts:
            if self._should_issue_alert(product_id, alert):
                self.alerts[product_id].append(alert)
                self.alert_timestamps[f"{product_id}_{alert.alert_type.value}"] = alert.timestamp

        statistics = self._calculate_statistics(data)
        quality_forecast = self._forecast_next_value(quality_scores, quality_slope)
        overall_trend = self._classify_trend(quality_slope)

        return TrendAnalysisResult(
            product_id=product_id,
            time_span={
                'start': data[0].timestamp,
                'end': data[-1].timestamp
            },
            overall_trend=overall_trend,
            trend_slope=quality_slope,
            alerts=alerts,
            statistics=statistics,
            quality_forecast=quality_forecast
        )

    def _get_recent_data(
        self,
        product_id: str,
        window_hours: int
    ) -> List[QualityDataPoint]:
        now = datetime.now()
        cutoff = now - timedelta(hours=window_hours)
        return [
            d for d in self.data_store.get(product_id, [])
            if d.timestamp >= cutoff
        ]

    def _calculate_trend(self, values: List[float]) -> Tuple[str, float]:
        if len(values) < 2:
            return 'stable', 0.0

        n = len(values)
        x = list(range(n))
        y = values

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denominator = sum((xi - mean_x) ** 2 for xi in x)

        if denominator == 0:
            return 'stable', 0.0

        slope = numerator / denominator

        if abs(slope) < 0.001:
            trend = 'stable'
        elif slope > 0:
            trend = 'improving'
        else:
            trend = 'declining'

        return trend, slope

    def _classify_trend(self, slope: float) -> str:
        if abs(slope) < 0.005:
            return 'stable'
        elif slope > 0.02:
            return 'strongly_improving'
        elif slope > 0:
            return 'improving'
        elif slope < -0.02:
            return 'strongly_declining'
        else:
            return 'declining'

    def _detect_quality_drop(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        quality_scores: List[float]
    ) -> Optional[TrendAlert]:
        if len(quality_scores) < 5:
            return None

        mid = len(quality_scores) // 2
        first_half = quality_scores[:mid]
        second_half = quality_scores[mid:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        drop = avg_first - avg_second
        drop_percent = drop / max(avg_first, 0.001)

        total_reviews = sum(d.review_count for d in data[mid:])
        if total_reviews < self.config.min_reviews_for_alert:
            return None

        if drop >= self.config.quality_drop_threshold:
            severity = AlertSeverity.CRITICAL
        elif drop >= self.config.quality_warning_threshold:
            severity = AlertSeverity.WARNING
        else:
            return None

        alert_id = f"quality_drop_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return TrendAlert(
            alert_id=alert_id,
            alert_type=AlertType.QUALITY_DROP,
            severity=severity,
            timestamp=datetime.now(),
            description=f"评论质量从 {avg_first:.4f} 骤降至 {avg_second:.4f}，下降 {drop_percent:.1%}",
            product_id=product_id,
            metric_name='quality_score',
            current_value=avg_second,
            expected_value=avg_first,
            change_percent=-drop_percent,
            threshold=self.config.quality_drop_threshold,
            historical_context={
                'previous_average': avg_first,
                'recent_average': avg_second,
                'absolute_drop': drop,
                'drop_percent': drop_percent,
                'data_points': len(quality_scores),
                'time_span_hours': (data[-1].timestamp - data[0].timestamp).total_seconds() / 3600
            }
        )

    def _detect_rating_manipulation(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        avg_ratings: List[float]
    ) -> Optional[TrendAlert]:
        if len(avg_ratings) < 6:
            return None

        recent_window = min(6, len(avg_ratings) // 4)
        recent = avg_ratings[-recent_window:]
        historical = avg_ratings[:-recent_window]

        if not historical:
            return None

        avg_historical = sum(historical) / len(historical)
        avg_recent = sum(recent) / len(recent)
        change = avg_recent - avg_historical
        change_percent = change / max(avg_historical, 0.001)

        is_significant = (abs(change) >= self.config.rating_drop_threshold and 
                         abs(change_percent) >= 0.15) or abs(change) >= 1.0

        if is_significant:
            direction = "下降" if change < 0 else "上升"
            severity = AlertSeverity.CRITICAL if abs(change) >= 1.0 else AlertSeverity.WARNING
            alert_id = f"rating_manipulation_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return TrendAlert(
                alert_id=alert_id,
                alert_type=AlertType.RATING_MANIPULATION,
                severity=severity,
                timestamp=datetime.now(),
                description=f"平均评分{direction}，从 {avg_historical:.2f} 变为 {avg_recent:.2f}，变化 {change:+.2f} ({change_percent:+.1%})",
                product_id=product_id,
                metric_name='avg_rating',
                current_value=avg_recent,
                expected_value=avg_historical,
                change_percent=change_percent,
                threshold=self.config.rating_drop_threshold,
                historical_context={
                    'historical_average': avg_historical,
                    'recent_average': avg_recent,
                    'absolute_change': change,
                    'change_percent': change_percent,
                    'review_count_in_recent': sum(d.review_count for d in data[-recent_window:])
                }
            )
        return None

    def _detect_fake_review_surge(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        fake_ratios: List[float]
    ) -> Optional[TrendAlert]:
        if len(fake_ratios) < 6:
            return None

        recent_window = min(6, len(fake_ratios) // 3)
        recent = fake_ratios[-recent_window:]
        historical = fake_ratios[:-recent_window]

        if not historical:
            return None

        avg_historical = sum(historical) / len(historical)
        avg_recent = sum(recent) / len(recent)

        ratio_multiplier = avg_recent / max(avg_historical, 0.001)
        absolute_increase = avg_recent - avg_historical

        has_surge = (avg_recent >= self.config.fake_review_surge_threshold and 
                     ratio_multiplier >= 1.5) or absolute_increase >= 0.15

        if has_surge:
            severity = AlertSeverity.CRITICAL if ratio_multiplier >= 2.5 or absolute_increase >= 0.25 else AlertSeverity.WARNING
            alert_id = f"fake_surge_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return TrendAlert(
                alert_id=alert_id,
                alert_type=AlertType.FAKE_REVIEW_SURGE,
                severity=severity,
                timestamp=datetime.now(),
                description=f"虚假评论比例从 {avg_historical:.1%} 升至 {avg_recent:.1%}，激增 {ratio_multiplier:.1f}倍",
                product_id=product_id,
                metric_name='fake_review_ratio',
                current_value=avg_recent,
                expected_value=avg_historical,
                change_percent=(avg_recent - avg_historical) / max(avg_historical, 0.001),
                threshold=self.config.fake_review_surge_threshold,
                historical_context={
                    'historical_average': avg_historical,
                    'recent_average': avg_recent,
                    'ratio_multiplier': ratio_multiplier,
                    'absolute_increase': absolute_increase
                }
            )
        return None

    def _detect_volume_anomaly(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        review_counts: List[int]
    ) -> Optional[TrendAlert]:
        if len(review_counts) < 6:
            return None

        recent_window = min(5, len(review_counts) // 4)
        recent = review_counts[-recent_window:]
        historical = review_counts[:-recent_window]

        if not historical:
            return None

        avg_historical = sum(historical) / len(historical)
        avg_recent = sum(recent) / len(recent)

        if avg_historical == 0:
            return None

        ratio = avg_recent / avg_historical
        absolute_increase = avg_recent - avg_historical

        has_anomaly = ratio >= self.config.volume_surge_threshold or absolute_increase >= 20

        if has_anomaly:
            severity = AlertSeverity.CRITICAL if ratio >= 3.0 or absolute_increase >= 40 else AlertSeverity.WARNING
            alert_id = f"volume_anomaly_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return TrendAlert(
                alert_id=alert_id,
                alert_type=AlertType.VOLUME_ANOMALY,
                severity=severity,
                timestamp=datetime.now(),
                description=f"评论量异常，从 {avg_historical:.1f} 增至 {avg_recent:.1f}，激增 {ratio:.1f}倍",
                product_id=product_id,
                metric_name='review_volume',
                current_value=avg_recent,
                expected_value=avg_historical,
                change_percent=ratio - 1,
                threshold=self.config.volume_surge_threshold,
                historical_context={
                    'historical_average': avg_historical,
                    'recent_average': avg_recent,
                    'surge_ratio': ratio,
                    'absolute_increase': absolute_increase
                }
            )
        return None

    def _detect_sentiment_shift(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        quality_scores: List[float]
    ) -> Optional[TrendAlert]:
        if len(quality_scores) < 6:
            return None

        mid = len(quality_scores) // 2
        first_half = quality_scores[:mid]
        second_half = quality_scores[mid:]

        std_first = statistics.stdev(first_half) if len(first_half) > 1 else 0
        std_second = statistics.stdev(second_half) if len(second_half) > 1 else 0

        variance_increase = std_second - std_first

        if variance_increase >= self.config.sentiment_shift_threshold:
            alert_id = f"sentiment_shift_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return TrendAlert(
                alert_id=alert_id,
                alert_type=AlertType.SENTIMENT_SHIFT,
                severity=AlertSeverity.WARNING,
                timestamp=datetime.now(),
                description=f"评论情感波动从 {std_first:.4f} 增至 {std_second:.4f}，方差增大 {variance_increase:.4f}",
                product_id=product_id,
                metric_name='sentiment_variance',
                current_value=std_second,
                expected_value=std_first,
                change_percent=variance_increase / max(std_first, 0.001),
                threshold=self.config.sentiment_shift_threshold,
                historical_context={
                    'first_half_std': std_first,
                    'second_half_std': std_second,
                    'variance_increase': variance_increase
                }
            )
        return None

    def _detect_competitor_attack(
        self,
        product_id: str,
        data: List[QualityDataPoint]
    ) -> Optional[TrendAlert]:
        recent_data = data[-5:] if len(data) >= 5 else data

        low_quality_count = sum(
            1 for d in recent_data
            if d.quality_score < 0.4 and d.fake_review_ratio > 0.3
        )

        if low_quality_count >= 3 and len(recent_data) >= 3:
            ratio = low_quality_count / len(recent_data)
            if ratio >= 0.5:
                alert_id = f"competitor_attack_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                return TrendAlert(
                    alert_id=alert_id,
                    alert_type=AlertType.COMPETITOR_ATTACK,
                    severity=AlertSeverity.CRITICAL,
                    timestamp=datetime.now(),
                    description=f"疑似竞品恶意攻击：近期 {low_quality_count}/{len(recent_data)} 条低质量虚假评论",
                    product_id=product_id,
                    metric_name='competitor_attack_ratio',
                    current_value=ratio,
                    expected_value=0.1,
                    change_percent=ratio - 0.1,
                    threshold=0.5,
                    historical_context={
                        'low_quality_count': low_quality_count,
                        'total_recent': len(recent_data),
                        'ratio': ratio
                    }
                )
        return None

    def _detect_cusum_change(
        self,
        product_id: str,
        data: List[QualityDataPoint],
        quality_scores: List[float]
    ) -> Optional[TrendAlert]:
        if len(quality_scores) < 10:
            return None

        target_mean = statistics.mean(quality_scores[:5])
        target_std = statistics.stdev(quality_scores[:5]) if len(quality_scores[:5]) > 1 else 0.1

        cusum_positive = 0.0
        cusum_negative = 0.0
        threshold = self.config.cusum_threshold * target_std
        drift = 0.5 * target_std

        for i, score in enumerate(quality_scores[5:]):
            deviation = score - target_mean

            cusum_positive = max(0, cusum_positive + deviation - drift)
            cusum_negative = max(0, cusum_negative - deviation - drift)

            if cusum_positive > threshold or cusum_negative > threshold:
                alert_id = f"cusum_change_{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                direction = "上升" if cusum_positive > threshold else "下降"
                change_magnitude = max(cusum_positive, cusum_negative)

                return TrendAlert(
                    alert_id=alert_id,
                    alert_type=AlertType.QUALITY_DROP if direction == "下降" else AlertType.SENTIMENT_SHIFT,
                    severity=AlertSeverity.WARNING,
                    timestamp=datetime.now(),
                    description=f"CUSUM检测到质量{direction}突变，检测点 {i + 5}，累积和 {change_magnitude:.3f}",
                    product_id=product_id,
                    metric_name='cusum_change',
                    current_value=score,
                    expected_value=target_mean,
                    change_percent=(score - target_mean) / max(target_mean, 0.001),
                    threshold=threshold,
                    historical_context={
                        'target_mean': target_mean,
                        'target_std': target_std,
                        'cusum_positive': cusum_positive,
                        'cusum_negative': cusum_negative,
                        'detection_point': i + 5
                    }
                )

        return None

    def _calculate_statistics(self, data: List[QualityDataPoint]) -> Dict[str, Any]:
        quality_scores = [d.quality_score for d in data]
        avg_ratings = [d.avg_rating for d in data]
        fake_ratios = [d.fake_review_ratio for d in data]
        review_counts = [d.review_count for d in data]

        return {
            'total_data_points': len(data),
            'avg_quality_score': statistics.mean(quality_scores),
            'quality_std': statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
            'quality_min': min(quality_scores),
            'quality_max': max(quality_scores),
            'avg_rating': statistics.mean(avg_ratings),
            'avg_fake_ratio': statistics.mean(fake_ratios),
            'total_reviews': sum(review_counts),
            'avg_reviews_per_point': statistics.mean(review_counts),
            'quality_trend': self._calculate_trend(quality_scores)[0]
        }

    def _forecast_next_value(self, values: List[float], slope: float) -> float:
        if len(values) < 2:
            return values[-1] if values else 0.5
        return values[-1] + slope

    def _should_issue_alert(self, product_id: str, alert: TrendAlert) -> bool:
        key = f"{product_id}_{alert.alert_type.value}"
        last_alert_time = self.alert_timestamps.get(key)

        if last_alert_time is None:
            return True

        time_since_last = (alert.timestamp - last_alert_time).total_seconds() / 3600
        return time_since_last >= self.config.alert_cooldown_hours

    def get_active_alerts(
        self,
        product_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        only_unhandled: bool = True
    ) -> List[TrendAlert]:
        alerts = []

        if product_id:
            product_ids = [product_id]
        else:
            product_ids = list(self.alerts.keys())

        for pid in product_ids:
            for alert in self.alerts.get(pid, []):
                if severity and alert.severity != severity:
                    continue
                if only_unhandled and alert.is_handled:
                    continue
                alerts.append(alert)

        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return alerts

    def mark_alert_handled(self, alert_id: str) -> bool:
        for product_alerts in self.alerts.values():
            for alert in product_alerts:
                if alert.alert_id == alert_id:
                    alert.is_handled = True
                    return True
        return False

    def get_trend_summary(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        analysis = self.analyze_trends(product_id, time_window_hours)
        data = self._get_recent_data(product_id, time_window_hours or self.config.window_size_hours)

        if not data:
            return {'error': 'no_data'}

        quality_scores = [d.quality_score for d in data]

        return {
            'product_id': product_id,
            'data_points': len(data),
            'time_span_hours': (data[-1].timestamp - data[0].timestamp).total_seconds() / 3600,
            'current_quality': quality_scores[-1],
            'average_quality': statistics.mean(quality_scores),
            'quality_trend': analysis.overall_trend,
            'quality_slope': analysis.trend_slope,
            'active_alerts': len([a for a in analysis.alerts]),
            'critical_alerts': len([a for a in analysis.alerts if a.severity == AlertSeverity.CRITICAL]),
            'warning_alerts': len([a for a in analysis.alerts if a.severity == AlertSeverity.WARNING]),
            'forecast_quality': analysis.quality_forecast
        }

    def print_trend_report(
        self,
        product_id: str,
        time_window_hours: Optional[int] = None
    ) -> None:
        summary = self.get_trend_summary(product_id, time_window_hours)
        analysis = self.analyze_trends(product_id, time_window_hours)

        print("=" * 80)
        print(f"{'评论质量趋势监控报告':^80}")
        print("=" * 80)
        print(f"商品ID: {product_id}")
        print(f"数据点数: {summary.get('data_points', 0)} | 时间跨度: {summary.get('time_span_hours', 0):.1f}小时")
        print()

        print("📊 质量指标概览")
        print("-" * 80)
        print(f"  当前质量: {summary.get('current_quality', 0):.4f} | 平均质量: {summary.get('average_quality', 0):.4f}")
        print(f"  趋势方向: {self._trend_to_chinese(summary.get('quality_trend', 'unknown'))}")
        print(f"  趋势斜率: {summary.get('quality_slope', 0):.6f}")
        if summary.get('forecast_quality') is not None:
            print(f"  预测下一期: {summary.get('forecast_quality', 0):.4f}")
        print()

        print("⚠️  告警信息")
        print("-" * 80)
        print(f"  活跃告警: {summary.get('active_alerts', 0)} 个")
        print(f"    - 严重: {summary.get('critical_alerts', 0)} | 警告: {summary.get('warning_alerts', 0)}")
        print()

        if analysis.alerts:
            print("📋 告警详情")
            print("-" * 80)
            for idx, alert in enumerate(analysis.alerts, 1):
                severity_icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡"

                print(f"  {idx}. {severity_icon} [{alert.timestamp.strftime('%Y-%m-%d %H:%M')}]")
                print(f"     类型: {self._alert_type_to_chinese(alert.alert_type)}")
                print(f"     描述: {alert.description}")
                print(f"     指标: {alert.metric_name} = {alert.current_value:.4f} (预期: {alert.expected_value:.4f})")
                print(f"     变化: {alert.change_percent:+.1%} | 阈值: {alert.threshold:.4f}")
                print()

        print("=" * 80)

    @staticmethod
    def _trend_to_chinese(trend: str) -> str:
        mapping = {
            'stable': '⬅️ 稳定',
            'improving': '↗️ 上升',
            'declining': '↘️ 下降',
            'strongly_improving': '⬆️ 显著上升',
            'strongly_declining': '⬇️ 显著下降',
            'insufficient_data': '❓ 数据不足'
        }
        return mapping.get(trend, trend)

    @staticmethod
    def _alert_type_to_chinese(alert_type: AlertType) -> str:
        mapping = {
            AlertType.QUALITY_DROP: '质量突降',
            AlertType.SPAM_SURGE: '垃圾评论激增',
            AlertType.FAKE_REVIEW_SURGE: '虚假评论激增',
            AlertType.RATING_MANIPULATION: '评分操纵',
            AlertType.SENTIMENT_SHIFT: '情感突变',
            AlertType.VOLUME_ANOMALY: '评论量异常',
            AlertType.COMPETITOR_ATTACK: '竞品攻击'
        }
        return mapping.get(alert_type, alert_type.value)
