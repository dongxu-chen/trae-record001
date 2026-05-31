from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import time
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import AppConfig, DatabaseConfig
from db_connector import DatabaseConnector, MySQLConnector, PostgreSQLConnector, QueryResult
from execution_plan import (
    ExecutionPlanAnalyzer,
    MySQLExecutionPlanAnalyzer,
    PostgreSQLExecutionPlanAnalyzer,
    PlanAnalysis,
)
from rewriter import RewriteResult
from .result_validator import ResultSetValidator, ValidationResult


@dataclass
class QueryPerformance:
    sql: str
    execution_time_ms: float = 0.0
    execution_times: List[float] = field(default_factory=list)
    avg_time_ms: float = 0.0
    min_time_ms: float = 0.0
    max_time_ms: float = 0.0
    rows_returned: int = 0
    success: bool = False
    error: Optional[str] = None
    plan_analysis: Optional[PlanAnalysis] = None
    raw_plan: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "execution_time_ms": self.execution_time_ms,
            "execution_times": self.execution_times,
            "avg_time_ms": self.avg_time_ms,
            "min_time_ms": self.min_time_ms,
            "max_time_ms": self.max_time_ms,
            "rows_returned": self.rows_returned,
            "success": self.success,
            "error": self.error,
            "plan_analysis": self.plan_analysis.to_dict() if self.plan_analysis else None,
        }


@dataclass
class PerformanceComparisonResult:
    original: QueryPerformance
    rewritten: QueryPerformance
    improvement_percent: float = 0.0
    time_diff_ms: float = 0.0
    cost_diff: float = 0.0
    is_rewritten: bool = False
    rewrite_result: Optional[RewriteResult] = None
    validation_passed: bool = False
    validation_message: str = ""
    validation_result: Optional[ValidationResult] = None
    original_result: Optional[QueryResult] = None
    rewritten_result: Optional[QueryResult] = None

    @property
    def is_faster(self) -> bool:
        return self.rewritten.avg_time_ms < self.original.avg_time_ms and self.rewritten.success

    @property
    def improvement(self) -> float:
        if self.original.avg_time_ms == 0:
            return 0.0
        return ((self.original.avg_time_ms - self.rewritten.avg_time_ms) / self.original.avg_time_ms) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original.to_dict(),
            "rewritten": self.rewritten.to_dict(),
            "improvement_percent": self.improvement,
            "time_diff_ms": self.time_diff_ms,
            "cost_diff": self.cost_diff,
            "is_rewritten": self.is_rewritten,
            "is_faster": self.is_faster,
            "validation_passed": self.validation_passed,
            "validation_message": self.validation_message,
            "validation_result": self.validation_result.to_dict() if self.validation_result else None,
        }


class PerformanceComparator:
    def __init__(self, db_config: DatabaseConfig, app_config: Optional[AppConfig] = None):
        self.db_config = db_config
        self.app_config = app_config or AppConfig()
        self.connector = self._create_connector()
        self.plan_analyzer = self._create_plan_analyzer()
        self.result_validator = ResultSetValidator(
            check_row_count=True,
            check_columns=True,
            check_data=True,
            check_order=False,
            max_rows_to_compare=1000,
        )

    def _create_connector(self) -> DatabaseConnector:
        db_type = self.db_config.db_type.lower()
        if db_type in ["mysql", "mariadb"]:
            return MySQLConnector(self.db_config)
        elif db_type in ["postgresql", "postgres", "pg"]:
            return PostgreSQLConnector(self.db_config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def _create_plan_analyzer(self) -> ExecutionPlanAnalyzer:
        db_type = self.db_config.db_type.lower()
        if db_type in ["mysql", "mariadb"]:
            return MySQLExecutionPlanAnalyzer()
        elif db_type in ["postgresql", "postgres", "pg"]:
            return PostgreSQLExecutionPlanAnalyzer()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def benchmark_query(
        self,
        sql: str,
        iterations: int = 3,
        warmup: bool = True,
        get_plan: bool = True,
        capture_result: bool = True,
    ) -> tuple[QueryPerformance, Optional[QueryResult]]:
        perf = QueryPerformance(sql=sql)
        query_result = None

        try:
            if not self.connector.is_connected():
                if not self.connector.connect():
                    perf.error = "Failed to connect to database"
                    return perf, None

            if warmup:
                try:
                    self.connector.execute(sql)
                except Exception:
                    pass

            times = []
            last_result = None

            for i in range(iterations):
                result = self.connector.execute(sql)
                if result.success:
                    times.append(result.execution_time_ms)
                    last_result = result
                else:
                    perf.error = result.error
                    perf.success = False
                    return perf, None

            if times:
                perf.execution_times = times
                perf.avg_time_ms = sum(times) / len(times)
                perf.min_time_ms = min(times)
                perf.max_time_ms = max(times)
                perf.execution_time_ms = perf.avg_time_ms

            if last_result:
                perf.rows_returned = len(last_result.rows)
                perf.success = True
                if capture_result:
                    query_result = last_result

            if get_plan and perf.success:
                try:
                    plan_result = self.connector.explain(sql)
                    if plan_result.success and plan_result.rows:
                        perf.raw_plan = plan_result.rows
                        perf.plan_analysis = self.plan_analyzer.parse_plan(plan_result.rows)
                except Exception as e:
                    pass

        except Exception as e:
            perf.error = str(e)

        return perf, query_result

    def compare(
        self,
        original_sql: str,
        rewritten_sql: str,
        rewrite_result: Optional[RewriteResult] = None,
        iterations: int = 3,
        validate_results: bool = True,
    ) -> PerformanceComparisonResult:
        original_perf, original_result = self.benchmark_query(original_sql, iterations, capture_result=validate_results)
        rewritten_perf, rewritten_result = self.benchmark_query(rewritten_sql, iterations, capture_result=validate_results)

        result = PerformanceComparisonResult(
            original=original_perf,
            rewritten=rewritten_perf,
            is_rewritten=original_sql != rewritten_sql,
            rewrite_result=rewrite_result,
            original_result=original_result,
            rewritten_result=rewritten_result,
        )

        result.time_diff_ms = original_perf.avg_time_ms - rewritten_perf.avg_time_ms

        if original_perf.plan_analysis and rewritten_perf.plan_analysis:
            result.cost_diff = original_perf.plan_analysis.total_cost - rewritten_perf.plan_analysis.total_cost

        result.improvement_percent = result.improvement

        if validate_results and original_result and rewritten_result:
            validation_result = self.result_validator.validate(original_result, rewritten_result)
            result.validation_result = validation_result
            result.validation_passed = validation_result.passed
            result.validation_message = validation_result.message
        else:
            result.validation_passed, result.validation_message = self._validate_basic(
                original_perf, rewritten_perf
            )

        return result

    def _validate_basic(
        self,
        original: QueryPerformance,
        rewritten: QueryPerformance,
    ) -> Tuple[bool, str]:
        if not original.success:
            return False, "Original query failed to execute"

        if not rewritten.success:
            return False, f"Rewritten query failed: {rewritten.error}"

        if original.rows_returned != rewritten.rows_returned:
            return False, (
                f"Row count mismatch: original returned {original.rows_returned} rows, "
                f"rewritten returned {rewritten.rows_returned} rows"
            )

        return True, "Results validated (row count only)"

    def validate_results_detailed(
        self,
        original_sql: str,
        rewritten_sql: str,
    ) -> ValidationResult:
        original_result = self.connector.execute(original_sql)
        rewritten_result = self.connector.execute(rewritten_sql)
        return self.result_validator.validate(original_result, rewritten_result)

    def generate_comparison_chart(
        self,
        comparison: PerformanceComparisonResult,
        chart_type: str = "bar",
    ) -> go.Figure:
        if chart_type == "bar":
            return self._generate_bar_chart(comparison)
        elif chart_type == "radar":
            return self._generate_radar_chart(comparison)
        elif chart_type == "gauge":
            return self._generate_gauge_chart(comparison)
        else:
            return self._generate_bar_chart(comparison)

    def _generate_bar_chart(self, comparison: PerformanceComparisonResult) -> go.Figure:
        fig = go.Figure()

        categories = ["Avg Time", "Min Time", "Max Time"]
        original_values = [
            comparison.original.avg_time_ms,
            comparison.original.min_time_ms,
            comparison.original.max_time_ms,
        ]
        rewritten_values = [
            comparison.rewritten.avg_time_ms,
            comparison.rewritten.min_time_ms,
            comparison.rewritten.max_time_ms,
        ]

        fig.add_trace(go.Bar(
            name="Original",
            x=categories,
            y=original_values,
            marker_color="#ef4444",
            text=[f"{v:.2f} ms" for v in original_values],
            textposition="auto",
        ))

        fig.add_trace(go.Bar(
            name="Rewritten",
            x=categories,
            y=rewritten_values,
            marker_color="#22c55e",
            text=[f"{v:.2f} ms" for v in rewritten_values],
            textposition="auto",
        ))

        fig.update_layout(
            title="Execution Time Comparison (ms)",
            barmode="group",
            yaxis_title="Time (ms)",
            template="plotly_white",
            height=400,
        )

        return fig

    def _generate_radar_chart(self, comparison: PerformanceComparisonResult) -> go.Figure:
        categories = ["Execution Time", "Query Cost", "Rows Scanned"]

        original_vals = []
        rewritten_vals = []

        max_time = max(comparison.original.avg_time_ms, comparison.rewritten.avg_time_ms, 1)
        original_vals.append(100 - (comparison.original.avg_time_ms / max_time * 100))
        rewritten_vals.append(100 - (comparison.rewritten.avg_time_ms / max_time * 100))

        if comparison.original.plan_analysis and comparison.rewritten.plan_analysis:
            max_cost = max(comparison.original.plan_analysis.total_cost, comparison.rewritten.plan_analysis.total_cost, 1)
            original_vals.append(100 - (comparison.original.plan_analysis.total_cost / max_cost * 100))
            rewritten_vals.append(100 - (comparison.rewritten.plan_analysis.total_cost / max_cost * 100))

            max_rows = max(comparison.original.plan_analysis.estimated_rows, comparison.rewritten.plan_analysis.estimated_rows, 1)
            original_vals.append(100 - (comparison.original.plan_analysis.estimated_rows / max_rows * 100))
            rewritten_vals.append(100 - (comparison.rewritten.plan_analysis.estimated_rows / max_rows * 100))
        else:
            original_vals.extend([50, 50])
            rewritten_vals.extend([50, 50])

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=original_vals,
            theta=categories,
            fill="toself",
            name="Original",
            marker_color="#ef4444",
        ))

        fig.add_trace(go.Scatterpolar(
            r=rewritten_vals,
            theta=categories,
            fill="toself",
            name="Rewritten",
            marker_color="#22c55e",
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticktext=["Worse", "", "", "", "", "Better"],
                    tickvals=[0, 20, 40, 60, 80, 100],
                )
            ),
            showlegend=True,
            title="Performance Score (Higher is Better)",
            height=400,
        )

        return fig

    def _generate_gauge_chart(self, comparison: PerformanceComparisonResult) -> go.Figure:
        improvement = max(min(comparison.improvement, 100), 0)

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=improvement,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Performance Improvement (%)"},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue"},
                "bar": {"color": "#22c55e"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, 20], "color": "#fef2f2"},
                    {"range": [20, 50], "color": "#fef9c3"},
                    {"range": [50, 80], "color": "#dcfce7"},
                    {"range": [80, 100], "color": "#bbf7d0"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
            number={"suffix": "%"},
        ))

        fig.update_layout(height=300)

        return fig

    def generate_comparison_table(
        self,
        comparison: PerformanceComparisonResult,
    ) -> pd.DataFrame:
        data = {
            "Metric": [
                "Average Time (ms)",
                "Min Time (ms)",
                "Max Time (ms)",
                "Rows Returned",
                "Estimated Cost",
                "Full Table Scans",
                "Using Filesort",
                "Using Temporary",
            ],
            "Original": [
                f"{comparison.original.avg_time_ms:.2f}",
                f"{comparison.original.min_time_ms:.2f}",
                f"{comparison.original.max_time_ms:.2f}",
                comparison.original.rows_returned,
                f"{comparison.original.plan_analysis.total_cost:.2f}" if comparison.original.plan_analysis else "N/A",
                "Yes" if (comparison.original.plan_analysis and comparison.original.plan_analysis.has_full_table_scan) else "No",
                "Yes" if (comparison.original.plan_analysis and comparison.original.plan_analysis.has_using_filesort) else "No",
                "Yes" if (comparison.original.plan_analysis and comparison.original.plan_analysis.has_using_temporary) else "No",
            ],
            "Rewritten": [
                f"{comparison.rewritten.avg_time_ms:.2f}",
                f"{comparison.rewritten.min_time_ms:.2f}",
                f"{comparison.rewritten.max_time_ms:.2f}",
                comparison.rewritten.rows_returned,
                f"{comparison.rewritten.plan_analysis.total_cost:.2f}" if comparison.rewritten.plan_analysis else "N/A",
                "Yes" if (comparison.rewritten.plan_analysis and comparison.rewritten.plan_analysis.has_full_table_scan) else "No",
                "Yes" if (comparison.rewritten.plan_analysis and comparison.rewritten.plan_analysis.has_using_filesort) else "No",
                "Yes" if (comparison.rewritten.plan_analysis and comparison.rewritten.plan_analysis.has_using_temporary) else "No",
            ],
            "Improvement": [
                f"{comparison.improvement_percent:.1f}%",
                f"{((comparison.original.min_time_ms - comparison.rewritten.min_time_ms) / max(comparison.original.min_time_ms, 1) * 100):.1f}%" if comparison.original.min_time_ms > 0 else "N/A",
                f"{((comparison.original.max_time_ms - comparison.rewritten.max_time_ms) / max(comparison.original.max_time_ms, 1) * 100):.1f}%" if comparison.original.max_time_ms > 0 else "N/A",
                "-",
                f"{((comparison.original.plan_analysis.total_cost - comparison.rewritten.plan_analysis.total_cost) / max(comparison.original.plan_analysis.total_cost, 1) * 100):.1f}%" if (comparison.original.plan_analysis and comparison.rewritten.plan_analysis and comparison.original.plan_analysis.total_cost > 0) else "N/A",
                "-",
                "-",
                "-",
            ],
        }

        return pd.DataFrame(data)

    def close(self):
        self.connector.disconnect()

    def __enter__(self):
        self.connector.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
