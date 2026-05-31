from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import time
import pandas as pd
from config import DatabaseConfig


@dataclass
class QueryResult:
    sql: str
    success: bool = False
    rows: List[Tuple] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    affected_rows: int = 0
    error: Optional[str] = None
    query_plan: Optional[Any] = None

    def to_dataframe(self) -> pd.DataFrame:
        if not self.rows or not self.columns:
            return pd.DataFrame()
        return pd.DataFrame(self.rows, columns=self.columns)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sql": self.sql,
            "success": self.success,
            "columns": self.columns,
            "row_count": len(self.rows),
            "execution_time_ms": self.execution_time_ms,
            "affected_rows": self.affected_rows,
            "error": self.error,
        }


class DatabaseConnector(ABC):
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._cursor = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def _get_explain_sql(self, sql: str) -> str:
        pass

    @abstractmethod
    def _execute_query(self, sql: str, params: Optional[List[Any]] = None) -> QueryResult:
        pass

    def execute(self, sql: str, params: Optional[List[Any]] = None, timeout: int = 30) -> QueryResult:
        result = QueryResult(sql=sql)

        if not self.is_connected():
            if not self.connect():
                result.error = "Failed to connect to database"
                return result

        try:
            start_time = time.time()
            query_result = self._execute_query(sql, params)
            end_time = time.time()

            result.success = query_result.success
            result.rows = query_result.rows
            result.columns = query_result.columns
            result.affected_rows = query_result.affected_rows
            result.error = query_result.error
            result.execution_time_ms = (end_time - start_time) * 1000

        except Exception as e:
            result.error = str(e)

        return result

    def explain(self, sql: str, analyze: bool = True) -> QueryResult:
        explain_sql = self._get_explain_sql(sql)
        return self.execute(explain_sql)

    def benchmark_query(
        self,
        sql: str,
        iterations: int = 3,
        warmup: bool = True,
    ) -> Dict[str, Any]:
        times = []
        results = []

        if warmup:
            try:
                self.execute(sql)
            except Exception:
                pass

        for i in range(iterations):
            result = self.execute(sql)
            results.append(result)
            if result.success:
                times.append(result.execution_time_ms)

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
        else:
            avg_time = min_time = max_time = 0.0

        return {
            "sql": sql,
            "iterations": iterations,
            "execution_times": times,
            "avg_time_ms": avg_time,
            "min_time_ms": min_time,
            "max_time_ms": max_time,
            "success": all(r.success for r in results),
            "error": results[0].error if not results[0].success else None,
        }

    def execute_with_plan(self, sql: str) -> Tuple[QueryResult, Optional[Any]]:
        query_result = self.execute(sql)
        plan_result = self.explain(sql)

        if plan_result.success and plan_result.rows:
            return query_result, plan_result.rows

        return query_result, None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
