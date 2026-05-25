"""
Idle Transaction Detector - 空闲事务检测
识别长时间未提交的事务（IN_PROGRESS 状态或持续时间超长的事务），
按连接 / 线程 / schema 聚合，生成告警列表。
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class IdleTxnAlert:
    """空闲事务告警"""
    xid: str
    thread_id: Optional[int]
    user: str
    host: str
    schema: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    duration_ms: float
    idle_ms: float
    row_ops_count: int
    total_lock_wait_ms: float
    tables: List[str]
    source_binlog_file: str
    alert_level: str    # warning / critical
    reason: str         # 告警原因描述

    def to_dict(self) -> dict:
        return {
            "xid": self.xid,
            "thread_id": self.thread_id,
            "user": self.user or "N/A",
            "host": self.host or "N/A",
            "schema": self.schema or "N/A",
            "start_time": self.start_time or "N/A",
            "end_time": self.end_time or "N/A",
            "duration_ms": round(self.duration_ms, 2),
            "idle_ms": round(self.idle_ms, 2),
            "row_ops_count": self.row_ops_count,
            "total_lock_wait_ms": round(self.total_lock_wait_ms, 2),
            "tables": self.tables,
            "source_binlog_file": self.source_binlog_file,
            "alert_level": self.alert_level,
            "reason": self.reason,
        }


@dataclass
class IdleTxnResult:
    """空闲事务检测结果"""
    total_in_progress: int = 0
    total_long_idle: int = 0
    total_critical: int = 0
    alerts: List[IdleTxnAlert] = field(default_factory=list)
    connection_stats: List[dict] = field(default_factory=list)
    schema_stats: List[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class IdleTxnDetector:
    """空闲事务检测器"""

    def __init__(
        self,
        idle_threshold_ms: float = 60000,     # 空闲 60 秒以上
        critical_threshold_ms: float = 300000,  # 空闲 5 分钟以上视为严重
        in_progress_only: bool = False,
    ):
        self.idle_threshold_ms = idle_threshold_ms
        self.critical_threshold_ms = critical_threshold_ms
        self.in_progress_only = in_progress_only

    def detect(self, txns: List[TxnRecord]) -> IdleTxnResult:
        result = IdleTxnResult()

        now = datetime.now(timezone.utc)

        for txn in txns:
            if self.in_progress_only and txn.status != TxnStatus.IN_PROGRESS:
                continue

            if txn.status == TxnStatus.IN_PROGRESS:
                result.total_in_progress += 1

            end_ts = txn.end_time
            if end_ts is None:
                if txn.start_time:
                    idle_ms = (now - txn.start_time).total_seconds() * 1000
                else:
                    continue
            else:
                idle_ms = txn.duration_ms

            if idle_ms < self.idle_threshold_ms:
                continue

            alert_level = "critical" if idle_ms >= self.critical_threshold_ms else "warning"

            if txn.status == TxnStatus.IN_PROGRESS:
                reason = f"事务仍处于 IN_PROGRESS 状态，已空闲 {idle_ms / 1000:.0f}s"
            else:
                reason = f"事务持续时间超长：{idle_ms / 1000:.0f}s"

            if txn.total_lock_wait_ms > idle_ms * 0.5:
                reason += f"，其中锁等待占比 {txn.total_lock_wait_ms / idle_ms * 100:.0f}%"
            if txn.row_ops_count > 0 and idle_ms > 10000:
                idle_rate = (idle_ms - txn.total_lock_wait_ms) / idle_ms * 100
                if idle_rate > 70:
                    reason += f"，空闲占比 {idle_rate:.0f}%（可能为应用层等待）"

            alert = IdleTxnAlert(
                xid=txn.xid,
                thread_id=txn.thread_id,
                user=txn.user,
                host=txn.host,
                schema=txn.schema,
                start_time=txn.start_time.isoformat() if txn.start_time else None,
                end_time=txn.end_time.isoformat() if txn.end_time else None,
                duration_ms=txn.duration_ms,
                idle_ms=idle_ms,
                row_ops_count=txn.row_ops_count,
                total_lock_wait_ms=txn.total_lock_wait_ms,
                tables=list(txn.table_ops.keys()),
                source_binlog_file=txn.source_binlog_file,
                alert_level=alert_level,
                reason=reason,
            )
            result.alerts.append(alert)
            result.total_long_idle += 1
            if alert_level == "critical":
                result.total_critical += 1

        result.alerts.sort(key=lambda a: a.idle_ms, reverse=True)

        result.connection_stats = self._aggregate_by(
            result.alerts, key_fn=lambda a: f"{a.user}@{a.host}"
        )
        result.schema_stats = self._aggregate_by(
            result.alerts, key_fn=lambda a: a.schema or "unknown"
        )

        result.summary = {
            "total_in_progress": result.total_in_progress,
            "total_long_idle": result.total_long_idle,
            "total_critical": result.total_critical,
            "idle_threshold_ms": self.idle_threshold_ms,
            "critical_threshold_ms": self.critical_threshold_ms,
            "affected_connections": len(result.connection_stats),
            "affected_schemas": len(result.schema_stats),
        }

        return result

    def _aggregate_by(
        self, alerts: List[IdleTxnAlert], key_fn
    ) -> List[dict]:
        groups: Dict[str, List[IdleTxnAlert]] = defaultdict(list)
        for a in alerts:
            groups[key_fn(a)].append(a)

        stats = []
        for key, group in groups.items():
            critical_count = sum(1 for a in group if a.alert_level == "critical")
            stats.append({
                "key": key,
                "alert_count": len(group),
                "critical_count": critical_count,
                "max_idle_ms": max(a.idle_ms for a in group),
                "avg_idle_ms": sum(a.idle_ms for a in group) / len(group),
                "sample_xids": [a.xid for a in group[:3]],
            })
        stats.sort(key=lambda s: s["alert_count"], reverse=True)
        return stats
