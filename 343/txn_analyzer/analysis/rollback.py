"""
Rollback Pattern Analyzer - 回滚模式分析
识别高频回滚模式：按 schema / 表 / 查询特征 / 时间段聚类，
找出导致大量回滚的共性原因（死锁受害者、超时、应用错误等）。
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class RollbackPattern:
    """回滚模式聚类"""
    pattern_key: str           # 模式标识：schema 或 schema.table 或 query_signature
    pattern_type: str          # schema / table / query / time_bucket
    rollback_count: int = 0
    total_rollback_count: int = 0   # 所有回滚总数
    commit_count: int = 0
    total_txn_count: int = 0
    avg_duration_ms: float = 0.0
    avg_row_ops: float = 0.0
    avg_bytes_written: float = 0.0
    avg_lock_wait_ms: float = 0.0
    deadlock_victim_count: int = 0
    sample_xids: List[str] = field(default_factory=list)
    sample_queries: List[str] = field(default_factory=list)
    risk_level: str = "low"    # low / medium / high / critical

    @property
    def rollback_rate(self) -> float:
        denom = self.rollback_count + self.commit_count
        return self.rollback_count / denom if denom > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "pattern_key": self.pattern_key,
            "pattern_type": self.pattern_type,
            "rollback_count": self.rollback_count,
            "total_rollback_count": self.total_rollback_count,
            "commit_count": self.commit_count,
            "total_txn_count": self.total_txn_count,
            "rollback_rate": round(self.rollback_rate, 4),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "avg_row_ops": round(self.avg_row_ops, 2),
            "avg_bytes_written": round(self.avg_bytes_written, 2),
            "avg_lock_wait_ms": round(self.avg_lock_wait_ms, 2),
            "deadlock_victim_count": self.deadlock_victim_count,
            "sample_xids": self.sample_xids[:5],
            "sample_queries": self.sample_queries[:3],
            "risk_level": self.risk_level,
        }


@dataclass
class RollbackAnalysisResult:
    """回滚分析结果"""
    total_rollback_count: int = 0
    total_txn_count: int = 0
    overall_rollback_rate: float = 0.0
    deadlock_victim_total: int = 0
    schema_patterns: List[RollbackPattern] = field(default_factory=list)
    table_patterns: List[RollbackPattern] = field(default_factory=list)
    query_patterns: List[RollbackPattern] = field(default_factory=list)
    time_patterns: List[RollbackPattern] = field(default_factory=list)
    high_risk_patterns: List[RollbackPattern] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class RollbackPatternAnalyzer:
    """回滚模式分析器"""

    def __init__(
        self,
        min_rollback_count: int = 2,
        rollback_rate_threshold: float = 0.15,
        time_bucket_minutes: int = 15,
    ):
        self.min_rollback_count = min_rollback_count
        self.rollback_rate_threshold = rollback_rate_threshold
        self.time_bucket_minutes = time_bucket_minutes

    def analyze(self, txns: List[TxnRecord]) -> RollbackAnalysisResult:
        result = RollbackAnalysisResult()

        rollback_txns = [t for t in txns if t.status == TxnStatus.ROLLBACK]
        commit_txns = [t for t in txns if t.status == TxnStatus.COMMIT]

        result.total_rollback_count = len(rollback_txns)
        result.total_txn_count = len(txns)
        result.overall_rollback_rate = (
            result.total_rollback_count / result.total_txn_count
            if result.total_txn_count > 0 else 0.0
        )
        result.deadlock_victim_total = sum(1 for t in rollback_txns if t.deadlock_victim)

        result.schema_patterns = self._group_by(
            rollback_txns, commit_txns,
            key_fn=lambda t: t.schema or "unknown",
            pattern_type="schema",
            total_rollback_count=result.total_rollback_count,
        )

        def table_key(t: TxnRecord) -> List[str]:
            tables = list(t.table_ops.keys())
            if tables:
                return tables
            return [f"{t.schema or 'unknown'}.?"]

        result.table_patterns = self._group_by_multi(
            rollback_txns, commit_txns,
            key_fn=table_key,
            pattern_type="table",
            total_rollback_count=result.total_rollback_count,
        )

        result.query_patterns = self._group_by(
            rollback_txns, commit_txns,
            key_fn=lambda t: self._extract_query_signature(t),
            pattern_type="query",
            total_rollback_count=result.total_rollback_count,
        )

        result.time_patterns = self._group_by(
            rollback_txns, commit_txns,
            key_fn=lambda t: self._time_bucket(t.start_time),
            pattern_type="time_bucket",
            total_rollback_count=result.total_rollback_count,
        )

        all_patterns = (
            result.schema_patterns + result.table_patterns
            + result.query_patterns + result.time_patterns
        )
        for p in all_patterns:
            p.risk_level = self._assess_risk(p)
        result.high_risk_patterns = [
            p for p in all_patterns if p.risk_level in ("high", "critical")
        ]
        result.high_risk_patterns.sort(
            key=lambda p: (p.risk_level == "critical", p.rollback_count * p.rollback_rate),
            reverse=True,
        )

        result.summary = {
            "total_rollback": result.total_rollback_count,
            "total_txn": result.total_txn_count,
            "overall_rollback_rate": round(result.overall_rollback_rate, 4),
            "deadlock_victim": result.deadlock_victim_total,
            "schema_high_risk": sum(1 for p in result.schema_patterns if p.risk_level in ("high", "critical")),
            "table_high_risk": sum(1 for p in result.table_patterns if p.risk_level in ("high", "critical")),
            "query_high_risk": sum(1 for p in result.query_patterns if p.risk_level in ("high", "critical")),
            "time_high_risk": sum(1 for p in result.time_patterns if p.risk_level in ("high", "critical")),
            "total_high_risk_patterns": len(result.high_risk_patterns),
        }

        return result

    def _group_by(
        self,
        rollback_txns: List[TxnRecord],
        commit_txns: List[TxnRecord],
        key_fn,
        pattern_type: str,
        total_rollback_count: int,
    ) -> List[RollbackPattern]:
        rb_groups: Dict[str, List[TxnRecord]] = defaultdict(list)
        cm_groups: Dict[str, int] = defaultdict(int)

        for t in rollback_txns:
            rb_groups[key_fn(t)].append(t)
        for t in commit_txns:
            cm_groups[key_fn(t)] += 1

        patterns = []
        for key, rb_list in rb_groups.items():
            if len(rb_list) < self.min_rollback_count:
                continue
            commit_c = cm_groups.get(key, 0)
            p = RollbackPattern(
                pattern_key=str(key),
                pattern_type=pattern_type,
                rollback_count=len(rb_list),
                total_rollback_count=total_rollback_count,
                commit_count=commit_c,
                total_txn_count=len(rb_list) + commit_c,
                avg_duration_ms=sum(t.duration_ms for t in rb_list) / len(rb_list),
                avg_row_ops=sum(t.row_ops_count for t in rb_list) / len(rb_list),
                avg_bytes_written=sum(t.bytes_written for t in rb_list) / len(rb_list),
                avg_lock_wait_ms=sum(t.total_lock_wait_ms for t in rb_list) / len(rb_list),
                deadlock_victim_count=sum(1 for t in rb_list if t.deadlock_victim),
                sample_xids=[t.xid for t in rb_list[:5]],
                sample_queries=[q for t in rb_list[:3] for q in (t.queries or [])],
            )
            patterns.append(p)

        patterns.sort(key=lambda p: p.rollback_count * p.rollback_rate, reverse=True)
        return patterns

    def _group_by_multi(
        self,
        rollback_txns: List[TxnRecord],
        commit_txns: List[TxnRecord],
        key_fn,
        pattern_type: str,
        total_rollback_count: int,
    ) -> List[RollbackPattern]:
        rb_groups: Dict[str, List[TxnRecord]] = defaultdict(list)
        cm_groups: Dict[str, int] = defaultdict(int)

        for t in rollback_txns:
            for key in key_fn(t):
                rb_groups[key].append(t)
        for t in commit_txns:
            for key in key_fn(t):
                cm_groups[key] += 1

        patterns = []
        for key, rb_list in rb_groups.items():
            if len(rb_list) < self.min_rollback_count:
                continue
            commit_c = cm_groups.get(key, 0)
            p = RollbackPattern(
                pattern_key=key,
                pattern_type=pattern_type,
                rollback_count=len(rb_list),
                total_rollback_count=total_rollback_count,
                commit_count=commit_c,
                total_txn_count=len(rb_list) + commit_c,
                avg_duration_ms=sum(t.duration_ms for t in rb_list) / len(rb_list),
                avg_row_ops=sum(t.row_ops_count for t in rb_list) / len(rb_list),
                avg_bytes_written=sum(t.bytes_written for t in rb_list) / len(rb_list),
                avg_lock_wait_ms=sum(t.total_lock_wait_ms for t in rb_list) / len(rb_list),
                deadlock_victim_count=sum(1 for t in rb_list if t.deadlock_victim),
                sample_xids=[t.xid for t in rb_list[:5]],
                sample_queries=[q for t in rb_list[:3] for q in (t.queries or [])],
            )
            patterns.append(p)

        patterns.sort(key=lambda p: p.rollback_count * p.rollback_rate, reverse=True)
        return patterns

    def _extract_query_signature(self, txn: TxnRecord) -> str:
        """提取查询签名：归一化首条查询"""
        if not txn.queries:
            return "(no query)"
        q = txn.queries[0].strip().split(";")[0].strip()
        q = q.lower()
        import re
        q = re.sub(r"'[^']*'", "?", q)
        q = re.sub(r'"\s*[^"]*"', "?", q)
        q = re.sub(r"\b\d+\b", "?", q)
        q = re.sub(r"\s+", " ", q)
        return q[:120]

    def _time_bucket(self, ts: Optional[datetime]) -> str:
        if not ts:
            return "unknown"
        bucket = (ts.minute // self.time_bucket_minutes) * self.time_bucket_minutes
        return ts.strftime(f"%Y-%m-%d %H:") + f"{bucket:02d}"

    def _assess_risk(self, pattern: RollbackPattern) -> str:
        score = 0
        if pattern.rollback_rate >= 0.5:
            score += 4
        elif pattern.rollback_rate >= 0.3:
            score += 3
        elif pattern.rollback_rate >= self.rollback_rate_threshold:
            score += 2
        elif pattern.rollback_rate >= 0.05:
            score += 1

        if pattern.rollback_count >= 20:
            score += 4
        elif pattern.rollback_count >= 10:
            score += 3
        elif pattern.rollback_count >= 5:
            score += 2
        elif pattern.rollback_count >= self.min_rollback_count:
            score += 1

        if pattern.deadlock_victim_count > 0:
            score += 2

        if pattern.avg_lock_wait_ms >= 5000:
            score += 2
        elif pattern.avg_lock_wait_ms >= 1000:
            score += 1

        if score >= 8:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
