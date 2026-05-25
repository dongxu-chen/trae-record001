"""
Statistical Analysis - 统计分析
对解析出的事务数据进行基本统计分析:
- 事务总数、提交率、回滚率
- 事务持续时间分布（P50/P95/P99/Max）
- 锁等待时间分布
- 行操作数分布
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import math

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class TxnStatistics:
    """事务统计结果"""
    total_txn_count: int = 0
    commit_count: int = 0
    rollback_count: int = 0
    in_progress_count: int = 0
    commit_rate: float = 0.0
    rollback_rate: float = 0.0

    # 持续时间 (ms)
    duration_min: float = 0.0
    duration_max: float = 0.0
    duration_mean: float = 0.0
    duration_median: float = 0.0
    duration_p95: float = 0.0
    duration_p99: float = 0.0

    # 锁等待 (ms)
    lock_wait_total: float = 0.0
    lock_wait_mean: float = 0.0
    lock_wait_p95: float = 0.0
    lock_wait_p99: float = 0.0

    # 行操作
    total_row_ops: int = 0
    row_ops_mean: float = 0.0
    row_ops_max: int = 0

    # 时间范围
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None

    # 按 schema 统计
    schema_stats: Dict[str, Dict] = field(default_factory=dict)

    # 分布数据 (用于直方图)
    duration_distribution: List[Dict] = field(default_factory=list)
    lock_wait_distribution: List[Dict] = field(default_factory=list)


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return d0 + d1


def _build_distribution(values: List[float], bins: int = 10) -> List[Dict]:
    """构建直方图分布数据"""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [{"range": f"{min_v:.0f}", "count": len(values)}]

    bin_size = (max_v - min_v) / bins
    result = []
    for i in range(bins):
        lo = min_v + i * bin_size
        hi = min_v + (i + 1) * bin_size
        count = sum(1 for v in values if (lo <= v < hi) or (i == bins - 1 and v <= hi))
        result.append({"range": f"{lo:.0f}-{hi:.0f}", "count": count})
    return result


def compute_statistics(txns: List[TxnRecord]) -> TxnStatistics:
    """计算事务统计数据"""
    stats = TxnStatistics()
    stats.total_txn_count = len(txns)
    if stats.total_txn_count == 0:
        return stats

    durations: List[float] = []
    lock_waits: List[float] = []
    row_ops_list: List[int] = []
    timestamps: List[datetime] = []

    for txn in txns:
        if txn.status == TxnStatus.COMMIT:
            stats.commit_count += 1
        elif txn.status == TxnStatus.ROLLBACK:
            stats.rollback_count += 1
        else:
            stats.in_progress_count += 1

        if txn.duration_ms > 0:
            durations.append(txn.duration_ms)

        lock_waits.append(txn.total_lock_wait_ms)
        row_ops_list.append(txn.row_ops_count)

        if txn.start_time:
            timestamps.append(txn.start_time)
        if txn.end_time:
            timestamps.append(txn.end_time)

        if txn.schema:
            if txn.schema not in stats.schema_stats:
                stats.schema_stats[txn.schema] = {
                    "count": 0, "total_duration_ms": 0.0,
                    "total_lock_wait_ms": 0.0, "total_row_ops": 0,
                }
            s = stats.schema_stats[txn.schema]
            s["count"] += 1
            s["total_duration_ms"] += txn.duration_ms
            s["total_lock_wait_ms"] += txn.total_lock_wait_ms
            s["total_row_ops"] += txn.row_ops_count

    # 计算比例
    stats.commit_rate = stats.commit_count / stats.total_txn_count if stats.total_txn_count > 0 else 0
    stats.rollback_rate = stats.rollback_count / stats.total_txn_count if stats.total_txn_count > 0 else 0

    # 持续时间统计
    if durations:
        durations.sort()
        stats.duration_min = durations[0]
        stats.duration_max = durations[-1]
        stats.duration_mean = sum(durations) / len(durations)
        stats.duration_median = _percentile(durations, 0.5)
        stats.duration_p95 = _percentile(durations, 0.95)
        stats.duration_p99 = _percentile(durations, 0.99)
        stats.duration_distribution = _build_distribution(durations, 10)

    # 锁等待统计
    if lock_waits:
        lock_waits.sort()
        stats.lock_wait_total = sum(lock_waits)
        stats.lock_wait_mean = stats.lock_wait_total / len(lock_waits)
        stats.lock_wait_p95 = _percentile(lock_waits, 0.95)
        stats.lock_wait_p99 = _percentile(lock_waits, 0.99)
        stats.lock_wait_distribution = _build_distribution(lock_waits, 10)

    # 行操作统计
    if row_ops_list:
        stats.total_row_ops = sum(row_ops_list)
        stats.row_ops_mean = stats.total_row_ops / len(row_ops_list)
        stats.row_ops_max = max(row_ops_list)

    # 时间范围
    if timestamps:
        stats.time_start = min(timestamps)
        stats.time_end = max(timestamps)

    return stats
