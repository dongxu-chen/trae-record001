from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import json
import hashlib
from pathlib import Path
import statistics
import logging

from db_connector import DatabaseConnector
from performance import QueryPerformance


class TrendDirection(Enum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class TrackingConfig:
    tracking_interval_minutes: int = 60
    retention_days: int = 30
    baseline_sample_size: int = 5
    alert_threshold_pct: float = 20.0
    enable_alerts: bool = True
    slow_query_threshold_ms: float = 1000.0


@dataclass
class PerformanceMetric:
    sql_hash: str
    sql_sample: str
    exec_time_ms: float
    rows_examined: int = 0
    rows_sent: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    execution_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_hash": self.sql_hash,
            "sql_sample": self.sql_sample,
            "exec_time_ms": self.exec_time_ms,
            "rows_examined": self.rows_examined,
            "rows_sent": self.rows_sent,
            "timestamp": self.timestamp.isoformat(),
            "execution_count": self.execution_count,
        }


@dataclass
class PerformanceSnapshot:
    sql_hash: str
    sql_text: str
    metrics: List[PerformanceMetric] = field(default_factory=list)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    baseline_avg_ms: Optional[float] = None
    is_optimized: bool = False
    original_sql_hash: Optional[str] = None
    optimization_notes: str = ""

    def add_metric(self, metric: PerformanceMetric):
        self.metrics.append(metric)
        self.last_seen = metric.timestamp
        if len(self.metrics) == 1:
            self.first_seen = metric.timestamp

    def get_avg_exec_time(self, last_n: Optional[int] = None) -> Optional[float]:
        if not self.metrics:
            return None
        metrics = self.metrics[-last_n:] if last_n else self.metrics
        times = [m.exec_time_ms for m in metrics if m.exec_time_ms > 0]
        return statistics.mean(times) if times else None

    def get_p95_exec_time(self, last_n: Optional[int] = None) -> Optional[float]:
        if not self.metrics:
            return None
        metrics = self.metrics[-last_n:] if last_n else self.metrics
        times = sorted([m.exec_time_ms for m in metrics if m.exec_time_ms > 0])
        if not times:
            return None
        p95_index = int(len(times) * 0.95)
        return times[min(p95_index, len(times) - 1)]

    def get_trend(self, window_size: int = 10) -> TrendDirection:
        if len(self.metrics) < window_size * 2:
            return TrendDirection.UNKNOWN

        recent = self.metrics[-window_size:]
        older = self.metrics[-window_size * 2 : -window_size]

        recent_avg = statistics.mean([m.exec_time_ms for m in recent])
        older_avg = statistics.mean([m.exec_time_ms for m in older])

        change_pct = (recent_avg - older_avg) / older_avg * 100 if older_avg > 0 else 0

        if abs(change_pct) < 5:
            return TrendDirection.STABLE
        elif change_pct < -5:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.DECLINING

    def get_improvement_since_baseline(self) -> Optional[float]:
        if self.baseline_avg_ms is None:
            return None
        current_avg = self.get_avg_exec_time()
        if current_avg is None or self.baseline_avg_ms == 0:
            return None
        return (self.baseline_avg_ms - current_avg) / self.baseline_avg_ms * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_hash": self.sql_hash,
            "sql_text": self.sql_text,
            "metric_count": len(self.metrics),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "baseline_avg_ms": self.baseline_avg_ms,
            "is_optimized": self.is_optimized,
            "original_sql_hash": self.original_sql_hash,
            "optimization_notes": self.optimization_notes,
            "avg_exec_time_ms": self.get_avg_exec_time(),
            "p95_exec_time_ms": self.get_p95_exec_time(),
            "trend": self.get_trend().value,
            "improvement_pct": self.get_improvement_since_baseline(),
        }


@dataclass
class PerformanceTrend:
    sql_hash: str
    sql_text: str
    direction: TrendDirection
    change_pct: float
    avg_before: float
    avg_after: float
    time_window_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql_hash": self.sql_hash,
            "sql_text": self.sql_text,
            "direction": self.direction.value,
            "change_pct": self.change_pct,
            "avg_before_ms": self.avg_before,
            "avg_after_ms": self.avg_after,
            "time_window_hours": self.time_window_hours,
        }


class PerformanceTracker:
    def __init__(
        self,
        db_connector: DatabaseConnector,
        config: Optional[TrackingConfig] = None,
        data_dir: str = "./monitoring/data",
    ):
        self.db_connector = db_connector
        self.config = config or TrackingConfig()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots: Dict[str, PerformanceSnapshot] = {}
        self._load_snapshots()

        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _get_sql_hash(self, sql: str) -> str:
        normalized = " ".join(sql.strip().lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def track_query(
        self,
        sql: str,
        performance: QueryPerformance,
        is_optimized: bool = False,
        original_sql: Optional[str] = None,
        optimization_notes: str = "",
    ) -> PerformanceSnapshot:
        sql_hash = self._get_sql_hash(sql)

        metric = PerformanceMetric(
            sql_hash=sql_hash,
            sql_sample=sql[:200] + "..." if len(sql) > 200 else sql,
            exec_time_ms=performance.exec_time_ms,
            rows_examined=performance.rows_examined,
            rows_sent=performance.rows_sent,
        )

        if sql_hash not in self.snapshots:
            snapshot = PerformanceSnapshot(
                sql_hash=sql_hash,
                sql_text=sql,
                is_optimized=is_optimized,
                optimization_notes=optimization_notes,
            )
            if original_sql:
                snapshot.original_sql_hash = self._get_sql_hash(original_sql)
            self.snapshots[sql_hash] = snapshot
        else:
            snapshot = self.snapshots[sql_hash]

        snapshot.add_metric(metric)

        if len(snapshot.metrics) == self.config.baseline_sample_size:
            snapshot.baseline_avg_ms = snapshot.get_avg_exec_time()

        self._save_snapshot(sql_hash)
        return snapshot

    def get_snapshot(self, sql: str) -> Optional[PerformanceSnapshot]:
        sql_hash = self._get_sql_hash(sql)
        return self.snapshots.get(sql_hash)

    def get_snapshot_by_hash(self, sql_hash: str) -> Optional[PerformanceSnapshot]:
        return self.snapshots.get(sql_hash)

    def get_all_snapshots(
        self,
        only_optimized: bool = False,
        only_slow: bool = False,
    ) -> List[PerformanceSnapshot]:
        snapshots = list(self.snapshots.values())

        if only_optimized:
            snapshots = [s for s in snapshots if s.is_optimized]

        if only_slow:
            snapshots = [
                s
                for s in snapshots
                if s.get_avg_exec_time() or 0 > self.config.slow_query_threshold_ms
            ]

        return sorted(snapshots, key=lambda s: s.last_seen, reverse=True)

    def get_optimization_impact_report(self) -> Dict[str, Any]:
        optimized_snapshots = [s for s in self.snapshots.values() if s.is_optimized]

        if not optimized_snapshots:
            return {
                "total_optimized_queries": 0,
                "total_improvement_pct": 0,
                "queries_improved": 0,
                "queries_regressed": 0,
                "details": [],
            }

        details = []
        total_improvement = 0.0
        improved_count = 0
        regressed_count = 0

        for snapshot in optimized_snapshots:
            improvement = snapshot.get_improvement_since_baseline()
            if improvement is not None:
                total_improvement += improvement
                if improvement > 0:
                    improved_count += 1
                elif improvement < 0:
                    regressed_count += 1

            details.append(
                {
                    "sql_hash": snapshot.sql_hash,
                    "sql_sample": snapshot.sql_text[:100] + "..."
                    if len(snapshot.sql_text) > 100
                    else snapshot.sql_text,
                    "baseline_ms": snapshot.baseline_avg_ms,
                    "current_ms": snapshot.get_avg_exec_time(),
                    "improvement_pct": improvement,
                    "trend": snapshot.get_trend().value,
                }
            )

        return {
            "total_optimized_queries": len(optimized_snapshots),
            "avg_improvement_pct": total_improvement / len(optimized_snapshots),
            "queries_improved": improved_count,
            "queries_regressed": regressed_count,
            "details": sorted(details, key=lambda x: x["improvement_pct"] or 0, reverse=True),
        }

    def detect_performance_trends(
        self,
        hours: int = 24,
        min_samples: int = 5,
    ) -> List[PerformanceTrend]:
        trends = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for snapshot in self.snapshots.values():
            recent_metrics = [
                m for m in snapshot.metrics if m.timestamp >= cutoff_time
            ]
            if len(recent_metrics) < min_samples:
                continue

            midpoint = len(recent_metrics) // 2
            first_half = recent_metrics[:midpoint]
            second_half = recent_metrics[midpoint:]

            first_avg = statistics.mean([m.exec_time_ms for m in first_half])
            second_avg = statistics.mean([m.exec_time_ms for m in second_half])

            if first_avg == 0:
                continue

            change_pct = (second_avg - first_avg) / first_avg * 100

            if abs(change_pct) < 5:
                direction = TrendDirection.STABLE
            elif change_pct < 0:
                direction = TrendDirection.IMPROVING
            else:
                direction = TrendDirection.DECLINING

            trends.append(
                PerformanceTrend(
                    sql_hash=snapshot.sql_hash,
                    sql_text=snapshot.sql_text,
                    direction=direction,
                    change_pct=change_pct,
                    avg_before=first_avg,
                    avg_after=second_avg,
                    time_window_hours=hours,
                )
            )

        return sorted(trends, key=lambda t: abs(t.change_pct), reverse=True)

    def get_alerts(self) -> List[Dict[str, Any]]:
        if not self.config.enable_alerts:
            return []

        alerts = []
        trends = self.detect_performance_trends()

        for trend in trends:
            if trend.direction == TrendDirection.DECLINING:
                if abs(trend.change_pct) >= self.config.alert_threshold_pct:
                    alerts.append(
                        {
                            "type": "performance_degradation",
                            "severity": "warning"
                            if abs(trend.change_pct) < 50
                            else "critical",
                            "sql_hash": trend.sql_hash,
                            "sql_text": trend.sql_text[:200]
                            + "..."
                            if len(trend.sql_text) > 200
                            else trend.sql_text,
                            "change_pct": trend.change_pct,
                            "avg_before_ms": trend.avg_before,
                            "avg_after_ms": trend.avg_after,
                            "message": f"Query performance degraded by {trend.change_pct:.1f}%",
                        }
                    )

        return alerts

    def get_summary_stats(self) -> Dict[str, Any]:
        all_snapshots = list(self.snapshots.values())
        total_executions = sum(len(s.metrics) for s in all_snapshots)
        optimized_count = sum(1 for s in all_snapshots if s.is_optimized)

        slow_queries = [
            s
            for s in all_snapshots
            if (s.get_avg_exec_time() or 0) > self.config.slow_query_threshold_ms
        ]

        report = self.get_optimization_impact_report()

        return {
            "total_unique_queries": len(all_snapshots),
            "total_executions": total_executions,
            "optimized_queries": optimized_count,
            "slow_queries": len(slow_queries),
            "avg_improvement_pct": report.get("avg_improvement_pct", 0),
            "active_alerts": len(self.get_alerts()),
            "last_updated": datetime.now().isoformat(),
        }

    def _save_snapshot(self, sql_hash: str):
        snapshot = self.snapshots.get(sql_hash)
        if not snapshot:
            return

        file_path = self.data_dir / f"{sql_hash}.json"
        data = {
            "sql_hash": snapshot.sql_hash,
            "sql_text": snapshot.sql_text,
            "metrics": [m.to_dict() for m in snapshot.metrics],
            "first_seen": snapshot.first_seen.isoformat(),
            "last_seen": snapshot.last_seen.isoformat(),
            "baseline_avg_ms": snapshot.baseline_avg_ms,
            "is_optimized": snapshot.is_optimized,
            "original_sql_hash": snapshot.original_sql_hash,
            "optimization_notes": snapshot.optimization_notes,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_snapshots(self):
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                snapshot = PerformanceSnapshot(
                    sql_hash=data["sql_hash"],
                    sql_text=data["sql_text"],
                    metrics=[],
                    first_seen=datetime.fromisoformat(data["first_seen"]),
                    last_seen=datetime.fromisoformat(data["last_seen"]),
                    baseline_avg_ms=data.get("baseline_avg_ms"),
                    is_optimized=data.get("is_optimized", False),
                    original_sql_hash=data.get("original_sql_hash"),
                    optimization_notes=data.get("optimization_notes", ""),
                )

                for m_data in data.get("metrics", []):
                    metric = PerformanceMetric(
                        sql_hash=m_data["sql_hash"],
                        sql_sample=m_data["sql_sample"],
                        exec_time_ms=m_data["exec_time_ms"],
                        rows_examined=m_data.get("rows_examined", 0),
                        rows_sent=m_data.get("rows_sent", 0),
                        timestamp=datetime.fromisoformat(m_data["timestamp"]),
                        execution_count=m_data.get("execution_count", 1),
                    )
                    snapshot.metrics.append(metric)

                self.snapshots[snapshot.sql_hash] = snapshot
            except Exception as e:
                self.logger.warning(f"Failed to load snapshot {file_path}: {e}")

    def cleanup_old_data(self):
        cutoff_time = datetime.now() - timedelta(days=self.config.retention_days)
        deleted_count = 0

        for snapshot in list(self.snapshots.values()):
            snapshot.metrics = [
                m for m in snapshot.metrics if m.timestamp >= cutoff_time
            ]
            if not snapshot.metrics:
                del self.snapshots[snapshot.sql_hash]
                file_path = self.data_dir / f"{snapshot.sql_hash}.json"
                if file_path.exists():
                    file_path.unlink()
                deleted_count += 1

        self.logger.info(
            f"Cleaned up {deleted_count} old snapshots and expired metrics"
        )
