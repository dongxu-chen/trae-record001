"""
Large Transaction Detector - 大事务检测
检测大事务（回滚段使用量、持续时间、行操作数量），识别潜在风险。
"""
from dataclasses import dataclass, field
from typing import List, Optional

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class LargeTxnRecord:
    """大事务记录"""
    xid: str
    schema: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    duration_ms: float
    row_ops_count: int
    bytes_written: int
    total_lock_wait_ms: float
    status: str
    tables: List[str]
    queries: List[str]
    risk_level: str  # low / medium / high / critical

    def to_dict(self) -> dict:
        return {
            "xid": self.xid,
            "schema": self.schema or "N/A",
            "start_time": self.start_time or "N/A",
            "end_time": self.end_time or "N/A",
            "duration_ms": round(self.duration_ms, 2),
            "row_ops_count": self.row_ops_count,
            "bytes_written": self.bytes_written,
            "total_lock_wait_ms": round(self.total_lock_wait_ms, 2),
            "status": self.status,
            "tables": self.tables,
            "queries": self.queries[:3],
            "risk_level": self.risk_level,
        }


@dataclass
class LargeTxnResult:
    """大事务检测结果"""
    large_txns: List[LargeTxnRecord] = field(default_factory=list)
    long_running_txns: List[LargeTxnRecord] = field(default_factory=list)
    high_lock_wait_txns: List[LargeTxnRecord] = field(default_factory=list)
    rollback_txns: List[LargeTxnRecord] = field(default_factory=list)
    dual_threshold_txns: List[LargeTxnRecord] = field(default_factory=list)
    risk_summary: dict = field(default_factory=dict)


class LargeTxnDetector:
    """大事务检测器"""

    def __init__(
        self,
        bytes_threshold: int = 10 * 1024 * 1024,
        duration_threshold_ms: float = 5000,
        row_ops_threshold: int = 1000,
        lock_wait_threshold_ms: float = 1000,
        dual_threshold: bool = True,
    ):
        self.bytes_threshold = bytes_threshold
        self.duration_threshold = duration_threshold_ms
        self.row_ops_threshold = row_ops_threshold
        self.lock_wait_threshold = lock_wait_threshold_ms
        self.dual_threshold = dual_threshold

    def detect(self, txns: List[TxnRecord]) -> LargeTxnResult:
        """检测大事务"""
        result = LargeTxnResult()

        for txn in txns:
            bytes_large = txn.bytes_written >= self.bytes_threshold
            rows_large = txn.row_ops_count >= self.row_ops_threshold

            if self.dual_threshold:
                is_large = bytes_large and rows_large
            else:
                is_large = bytes_large or rows_large

            is_dual_large = bytes_large and rows_large
            is_long_running = txn.duration_ms >= self.duration_threshold
            has_high_lock = txn.total_lock_wait_ms >= self.lock_wait_threshold
            is_rollback = txn.status == TxnStatus.ROLLBACK

            if not any([is_large, is_dual_large, is_long_running, has_high_lock, is_rollback]):
                continue

            risk = self._assess_risk(txn, is_large, is_long_running, has_high_lock, is_rollback)

            record = LargeTxnRecord(
                xid=txn.xid,
                schema=txn.schema,
                start_time=txn.start_time.isoformat() if txn.start_time else None,
                end_time=txn.end_time.isoformat() if txn.end_time else None,
                duration_ms=txn.duration_ms,
                row_ops_count=txn.row_ops_count,
                bytes_written=txn.bytes_written,
                total_lock_wait_ms=txn.total_lock_wait_ms,
                status=txn.status.value,
                tables=list(txn.table_ops.keys()),
                queries=txn.queries,
                risk_level=risk,
            )

            if is_large:
                result.large_txns.append(record)
            if is_dual_large and self.dual_threshold:
                result.dual_threshold_txns.append(record)
            if is_long_running:
                result.long_running_txns.append(record)
            if has_high_lock:
                result.high_lock_wait_txns.append(record)
            if is_rollback:
                result.rollback_txns.append(record)

        # 排序
        result.large_txns.sort(key=lambda r: r.bytes_written, reverse=True)
        result.long_running_txns.sort(key=lambda r: r.duration_ms, reverse=True)
        result.high_lock_wait_txns.sort(key=lambda r: r.total_lock_wait_ms, reverse=True)
        result.rollback_txns.sort(key=lambda r: r.duration_ms, reverse=True)
        result.dual_threshold_txns.sort(key=lambda r: (r.bytes_written + r.row_ops_count), reverse=True)

        # 风险汇总
        result.risk_summary = {
            "total_large": len(result.large_txns),
            "total_long_running": len(result.long_running_txns),
            "total_high_lock": len(result.high_lock_wait_txns),
            "total_rollback": len(result.rollback_txns),
            "total_dual_threshold": len(result.dual_threshold_txns),
            "critical_count": sum(1 for t in result.large_txns if t.risk_level == "critical"),
            "high_count": sum(1 for t in result.large_txns if t.risk_level == "high"),
            "medium_count": sum(1 for t in result.large_txns if t.risk_level == "medium"),
            "low_count": sum(1 for t in result.large_txns if t.risk_level == "low"),
            "bytes_threshold": self.bytes_threshold,
            "row_ops_threshold": self.row_ops_threshold,
            "dual_threshold_mode": self.dual_threshold,
        }

        return result

    def _assess_risk(
        self, txn: TxnRecord, is_large: bool,
        is_long_running: bool, has_high_lock: bool,
        is_rollback: bool,
    ) -> str:
        """评估事务风险等级"""
        score = 0

        if txn.bytes_written >= 100 * 1024 * 1024:
            score += 4
        elif txn.bytes_written >= 50 * 1024 * 1024:
            score += 3
        elif txn.bytes_written >= 10 * 1024 * 1024:
            score += 2
        elif txn.bytes_written >= 1 * 1024 * 1024:
            score += 1

        if txn.duration_ms >= 60000:
            score += 4
        elif txn.duration_ms >= 30000:
            score += 3
        elif txn.duration_ms >= 5000:
            score += 2
        elif txn.duration_ms >= 1000:
            score += 1

        if txn.total_lock_wait_ms >= 10000:
            score += 4
        elif txn.total_lock_wait_ms >= 5000:
            score += 3
        elif txn.total_lock_wait_ms >= 1000:
            score += 2
        elif txn.total_lock_wait_ms >= 100:
            score += 1

        if is_rollback:
            score += 2

        if score >= 8:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
