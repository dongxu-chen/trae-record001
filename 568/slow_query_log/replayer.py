from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import time
import pandas as pd

from .parser import SlowQueryEntry
from rewriter import SQLRewriter, RewriteResult
from db_connector import DatabaseConnector, QueryResult
from performance import PerformanceComparator, PerformanceComparisonResult


@dataclass
class ReplayResult:
    original_entry: SlowQueryEntry
    original_performance: Optional[PerformanceComparisonResult] = None
    rewrite_result: Optional[RewriteResult] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_entry": self.original_entry.to_dict(),
            "rewrite_result": self.rewrite_result.to_dict() if self.rewrite_result else None,
            "performance": self.original_performance.to_dict() if self.original_performance else None,
            "error": self.error,
        }


@dataclass
class ReplaySummary:
    total_queries: int = 0
    success_count: int = 0
    failed_count: int = 0
    rewritten_count: int = 0
    total_original_time: float = 0.0
    total_rewritten_time: float = 0.0
    results: List[ReplayResult] = field(default_factory=list)

    @property
    def improvement_rate(self) -> float:
        if self.total_original_time > 0:
            return (self.total_original_time - self.total_rewritten_time) / self.total_original_time * 100
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "rewritten_count": self.rewritten_count,
            "total_original_time": self.total_original_time,
            "total_rewritten_time": self.total_rewritten_time,
            "improvement_rate": self.improvement_rate,
            "results": [r.to_dict() for r in self.results],
        }

    def to_dataframe(self) -> pd.DataFrame:
        data = []
        for r in self.results:
            row = {
                "sql": r.original_entry.sql[:100] + "..." if len(r.original_entry.sql) > 100 else r.original_entry.sql,
                "original_time": r.original_entry.query_time,
                "rewritten": r.rewrite_result.is_rewritten if r.rewrite_result else False,
                "error": r.error,
            }
            if r.original_performance:
                row["benchmark_original"] = r.original_performance.original.execution_time_ms
                row["benchmark_rewritten"] = r.original_performance.rewritten.execution_time_ms if r.original_performance.rewritten else None
                row["improvement_pct"] = r.original_performance.improvement_percentage
            data.append(row)
        return pd.DataFrame(data)


class LogReplayer:
    def __init__(
        self,
        db_connector: DatabaseConnector,
        dialect: str = "mysql",
        comparator: Optional[PerformanceComparator] = None,
    ):
        self.db_connector = db_connector
        self.rewriter = SQLRewriter(dialect=dialect)
        self.comparator = comparator or PerformanceComparator(db_connector, dialect)

    def replay(
        self,
        entries: List[SlowQueryEntry],
        benchmark_iterations: int = 1,
        skip_errors: bool = True,
    ) -> ReplaySummary:
        summary = ReplaySummary()
        summary.total_queries = len(entries)

        for entry in entries:
            result = self._process_entry(entry, benchmark_iterations)
            summary.results.append(result)

            if result.error:
                summary.failed_count += 1
                if not skip_errors:
                    raise Exception(result.error)
            else:
                summary.success_count += 1
                if result.rewrite_result and result.rewrite_result.is_rewritten:
                    summary.rewritten_count += 1

                if result.original_performance:
                    summary.total_original_time += result.original_performance.original.execution_time_ms
                    if result.original_performance.rewritten:
                        summary.total_rewritten_time += result.original_performance.rewritten.execution_time_ms

        return summary

    def _process_entry(
        self,
        entry: SlowQueryEntry,
        iterations: int,
    ) -> ReplayResult:
        result = ReplayResult(original_entry=entry)

        try:
            result.rewrite_result = self.rewriter.rewrite(entry.sql)

            if result.rewrite_result.is_rewritten:
                result.original_performance = self.comparator.compare(
                    entry.sql,
                    result.rewrite_result.rewritten_sql,
                    iterations=iterations,
                )
        except Exception as e:
            result.error = str(e)

        return result

    def generate_report(self, summary: ReplaySummary) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("慢查询日志重放报告")
        lines.append("=" * 80)
        lines.append(f"总查询数: {summary.total_queries}")
        lines.append(f"成功处理: {summary.success_count}")
        lines.append(f"失败数量: {summary.failed_count}")
        lines.append(f"重写成功: {summary.rewritten_count}")
        lines.append("")
        lines.append(f"原始总时间: {summary.total_original_time:.2f} ms")
        lines.append(f"重写后总时间: {summary.total_rewritten_time:.2f} ms")
        lines.append(f"性能提升: {summary.improvement_rate:.1f}%")
        lines.append("")
        lines.append("-" * 80)
        lines.append("详细结果:")
        lines.append("-" * 80)

        for i, r in enumerate(summary.results, 1):
            lines.append(f"\n查询 #{i}:")
            lines.append(f"  SQL: {r.original_entry.sql[:80]}...")
            lines.append(f"  日志时间: {r.original_entry.query_time:.4f}s")
            if r.rewrite_result:
                lines.append(f"  重写: {'是' if r.rewrite_result.is_rewritten else '否'}")
                if r.rewrite_result.is_rewritten:
                    lines.append(f"  规则数: {r.rewrite_result.rules_applied}")
            if r.original_performance:
                lines.append(f"  原始执行: {r.original_performance.original.execution_time_ms:.2f}ms")
                if r.original_performance.rewritten:
                    lines.append(f"  重写执行: {r.original_performance.rewritten.execution_time_ms:.2f}ms")
                    lines.append(f"  提升: {r.original_performance.improvement_percentage:.1f}%")
            if r.error:
                lines.append(f"  错误: {r.error}")

        return "\n".join(lines)
