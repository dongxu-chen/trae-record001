"""
Transaction Impact Predictor - 事务影响预测
基于统计数据预估变更涉及的热点表行数、写入量等影响指标，
为容量规划和变更评审提供参考。
"""
from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean, median
from typing import Dict, List, Optional

from ..parsers.base import TxnRecord, TxnStatus


@dataclass
class TableImpactPrediction:
    """单表影响预测"""
    table_name: str
    schema: str
    total_ops: int
    txn_count: int
    avg_rows_per_txn: float
    median_rows_per_txn: float
    p95_rows_per_txn: float
    estimated_rows_if_same_pattern: int
    avg_bytes_per_op: float
    estimated_bytes_total: int
    avg_lock_wait_ms: float
    risk_level: str  # low / medium / high / critical

    def to_dict(self) -> dict:
        return {
            "table_name": self.table_name,
            "schema": self.schema,
            "total_ops": self.total_ops,
            "txn_count": self.txn_count,
            "avg_rows_per_txn": round(self.avg_rows_per_txn, 2),
            "median_rows_per_txn": round(self.median_rows_per_txn, 2),
            "p95_rows_per_txn": round(self.p95_rows_per_txn, 2),
            "estimated_rows_if_same_pattern": self.estimated_rows_if_same_pattern,
            "avg_bytes_per_op": round(self.avg_bytes_per_op, 2),
            "estimated_bytes_total": self.estimated_bytes_total,
            "avg_lock_wait_ms": round(self.avg_lock_wait_ms, 2),
            "risk_level": self.risk_level,
        }


@dataclass
class TxnImpactPrediction:
    """整体事务影响预测"""
    total_txn_count: int
    commit_count: int
    rollback_count: int
    estimated_total_rows: int
    estimated_total_bytes: int
    estimated_total_lock_wait_ms: float
    top_affected_tables: List[TableImpactPrediction] = field(default_factory=list)
    hot_table_patterns: List[TableImpactPrediction] = field(default_factory=list)
    change_recommendation: str = ""
    summary: dict = field(default_factory=dict)


class TxnImpactPredictor:
    """事务影响预测器"""

    def __init__(
        self,
        top_n_tables: int = 10,
        hot_table_ops_threshold: int = 50,
    ):
        self.top_n_tables = top_n_tables
        self.hot_table_ops_threshold = hot_table_ops_threshold

    def predict(self, txns: List[TxnRecord]) -> TxnImpactPrediction:
        if not txns:
            return TxnImpactPrediction(
                total_txn_count=0, commit_count=0, rollback_count=0,
                estimated_total_rows=0, estimated_total_bytes=0,
                estimated_total_lock_wait_ms=0.0,
            )

        commit_txns = [t for t in txns if t.status == TxnStatus.COMMIT]

        total_rows = sum(t.row_ops_count for t in commit_txns)
        total_bytes = sum(t.bytes_written for t in commit_txns)
        total_lock_wait = sum(t.total_lock_wait_ms for t in commit_txns)

        table_ops: Dict[str, List[int]] = defaultdict(list)
        table_bytes: Dict[str, List[int]] = defaultdict(list)
        table_lock_wait: Dict[str, List[float]] = defaultdict(list)
        table_txn_count: Dict[str, int] = defaultdict(int)

        for t in commit_txns:
            for tbl, ops in t.table_ops.items():
                table_ops[tbl].append(ops)
                table_txn_count[tbl] += 1
                if t.bytes_written > 0 and ops > 0:
                    table_bytes[tbl].append(t.bytes_written // max(ops, 1))
                if t.total_lock_wait_ms > 0:
                    table_lock_wait[tbl].append(t.total_lock_wait_ms)

        table_predictions: List[TableImpactPrediction] = []
        for tbl in table_ops.keys():
            ops_list = table_ops[tbl]
            schema = tbl.split(".")[0] if "." in tbl else "unknown"
            avg_ops = mean(ops_list)
            med_ops = median(ops_list)
            sorted_ops = sorted(ops_list)
            p95_idx = int(len(sorted_ops) * 0.95) - 1
            p95_ops = sorted_ops[max(p95_idx, 0)] if sorted_ops else 0

            avg_bytes_per_op = mean(table_bytes[tbl]) if table_bytes[tbl] else 0
            avg_lock = mean(table_lock_wait[tbl]) if table_lock_wait[tbl] else 0

            total_ops = sum(ops_list)

            prediction = TableImpactPrediction(
                table_name=tbl,
                schema=schema,
                total_ops=total_ops,
                txn_count=table_txn_count[tbl],
                avg_rows_per_txn=avg_ops,
                median_rows_per_txn=med_ops,
                p95_rows_per_txn=p95_ops,
                estimated_rows_if_same_pattern=total_ops,
                avg_bytes_per_op=avg_bytes_per_op,
                estimated_bytes_total=int(total_ops * avg_bytes_per_op),
                avg_lock_wait_ms=avg_lock,
                risk_level=self._assess_risk(total_ops, avg_lock, table_txn_count[tbl]),
            )
            table_predictions.append(prediction)

        table_predictions.sort(key=lambda p: p.total_ops, reverse=True)

        top_tables = table_predictions[:self.top_n_tables]
        hot_tables = [
            p for p in table_predictions
            if p.total_ops >= self.hot_table_ops_threshold
        ]

        recommendation = self._generate_recommendation(
            table_predictions, total_rows, total_bytes, total_lock_wait,
            len(commit_txns),
        )

        result = TxnImpactPrediction(
            total_txn_count=len(txns),
            commit_count=len(commit_txns),
            rollback_count=len(txns) - len(commit_txns),
            estimated_total_rows=total_rows,
            estimated_total_bytes=total_bytes,
            estimated_total_lock_wait_ms=total_lock_wait,
            top_affected_tables=top_tables,
            hot_table_patterns=hot_tables,
            change_recommendation=recommendation,
            summary={
                "total_txn": len(txns),
                "commit": len(commit_txns),
                "rollback": len(txns) - len(commit_txns),
                "total_rows_estimated": total_rows,
                "total_bytes_estimated": total_bytes,
                "total_lock_wait_ms": round(total_lock_wait, 2),
                "affected_table_count": len(table_predictions),
                "hot_table_count": len(hot_tables),
                "top_table": table_predictions[0].table_name if table_predictions else "",
                "top_table_ops": table_predictions[0].total_ops if table_predictions else 0,
            },
        )

        return result

    def _assess_risk(
        self, total_ops: int, avg_lock_ms: float, txn_count: int
    ) -> str:
        score = 0
        if total_ops >= 10000:
            score += 4
        elif total_ops >= 5000:
            score += 3
        elif total_ops >= 1000:
            score += 2
        elif total_ops >= self.hot_table_ops_threshold:
            score += 1

        if avg_lock_ms >= 5000:
            score += 4
        elif avg_lock_ms >= 1000:
            score += 3
        elif avg_lock_ms >= 100:
            score += 2
        elif avg_lock_ms >= 10:
            score += 1

        if txn_count >= 100:
            score += 2
        elif txn_count >= 50:
            score += 1

        if score >= 8:
            return "critical"
        elif score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        table_predictions: List[TableImpactPrediction],
        total_rows: int,
        total_bytes: int,
        total_lock_wait: float,
        commit_count: int,
    ) -> str:
        if not table_predictions:
            return "无数据"

        rec_parts = []
        top = table_predictions[0]
        rec_parts.append(
            f"热点表 {top.table_name} 预计影响 {top.total_ops} 行，"
            f"约占总操作的 {top.total_ops / max(total_rows, 1) * 100:.1f}%"
        )

        if total_bytes >= 100 * 1024 * 1024:
            rec_parts.append(
                f"预计写入量 {total_bytes / 1024 / 1024:.0f}MB，"
                f"建议分批提交或使用离线处理"
            )
        elif total_bytes >= 10 * 1024 * 1024:
            rec_parts.append(
                f"预计写入量 {total_bytes / 1024 / 1024:.1f}MB，"
                f"需关注 binlog 增长"
            )

        avg_lock_per_txn = total_lock_wait / max(commit_count, 1)
        if avg_lock_per_txn >= 5000:
            rec_parts.append(
                f"平均锁等待 {avg_lock_per_txn:.0f}ms，"
                f"建议优化查询或调整隔离级别"
            )
        elif avg_lock_per_txn >= 500:
            rec_parts.append(
                f"平均锁等待 {avg_lock_per_txn:.0f}ms，"
                f"需关注锁竞争"
            )

        hot_count = sum(1 for p in table_predictions if p.risk_level in ("high", "critical"))
        if hot_count >= 5:
            rec_parts.append(
                f"{hot_count} 个表存在高风险，建议拆分变更并评估顺序"
            )

        return "；".join(rec_parts)
