from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set
import hashlib
import json

from db_connector import QueryResult


@dataclass
class ValidationResult:
    passed: bool
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    mismatches: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "mismatches": self.mismatches,
        }


@dataclass
class ResultSetMetadata:
    column_count: int
    column_names: List[str]
    column_types: List[str]
    row_count: int
    row_hash: str
    sample_rows: List[List[Any]]


class ResultSetValidator:
    def __init__(
        self,
        check_row_count: bool = True,
        check_columns: bool = True,
        check_data: bool = True,
        check_order: bool = False,
        max_rows_to_compare: int = 1000,
        tolerance: float = 1e-6,
    ):
        self.check_row_count = check_row_count
        self.check_columns = check_columns
        self.check_data = check_data
        self.check_order = check_order
        self.max_rows_to_compare = max_rows_to_compare
        self.tolerance = tolerance

    def validate(
        self,
        original: QueryResult,
        rewritten: QueryResult,
    ) -> ValidationResult:
        result = ValidationResult(passed=True)
        result.mismatches = []

        if not original.success:
            result.passed = False
            result.message = "Original query failed to execute"
            result.mismatches.append(f"Original error: {original.error}")
            return result

        if not rewritten.success:
            result.passed = False
            result.message = "Rewritten query failed to execute"
            result.mismatches.append(f"Rewritten error: {rewritten.error}")
            return result

        original_meta = self._extract_metadata(original)
        rewritten_meta = self._extract_metadata(rewritten)

        result.details = {
            "original": {
                "columns": original_meta.column_names,
                "row_count": original_meta.row_count,
                "sample_rows": original_meta.sample_rows[:5],
            },
            "rewritten": {
                "columns": rewritten_meta.column_names,
                "row_count": rewritten_meta.row_count,
                "sample_rows": rewritten_meta.sample_rows[:5],
            },
        }

        if self.check_row_count:
            row_count_ok, msg = self._check_row_count(original_meta, rewritten_meta)
            if not row_count_ok:
                result.passed = False
                result.mismatches.append(msg)

        if self.check_columns:
            cols_ok, msg = self._check_columns(original_meta, rewritten_meta)
            if not cols_ok:
                result.passed = False
                result.mismatches.append(msg)

        if self.check_data:
            data_ok, msg = self._check_data(original, rewritten)
            if not data_ok:
                result.passed = False
                result.mismatches.append(msg)

        if self.check_order:
            order_ok, msg = self._check_order(original, rewritten)
            if not order_ok:
                result.passed = False
                result.mismatches.append(msg)

        if result.passed:
            result.message = "Result sets are equivalent"
        else:
            result.message = f"Found {len(result.mismatches)} validation errors"

        return result

    def _extract_metadata(self, query_result: QueryResult) -> ResultSetMetadata:
        column_names = query_result.columns if hasattr(query_result, "columns") else []
        column_types = query_result.column_types if hasattr(query_result, "column_types") else []

        rows = query_result.rows or []
        row_count = len(rows)

        row_hash = self._compute_row_hash(rows[:self.max_rows_to_compare])

        return ResultSetMetadata(
            column_count=len(column_names),
            column_names=column_names,
            column_types=column_types,
            row_count=row_count,
            row_hash=row_hash,
            sample_rows=rows[:5],
        )

    def _compute_row_hash(self, rows: List[List[Any]]) -> str:
        sorted_rows = sorted(self._normalize_row(row) for row in rows)
        hash_input = json.dumps(sorted_rows, sort_keys=True, default=str)
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _normalize_row(self, row: List[Any]) -> Tuple[Any, ...]:
        normalized = []
        for val in row:
            if isinstance(val, float):
                normalized.append(round(val, 6))
            elif val is None:
                normalized.append(None)
            else:
                normalized.append(str(val))
        return tuple(normalized)

    def _check_row_count(
        self,
        original: ResultSetMetadata,
        rewritten: ResultSetMetadata,
    ) -> Tuple[bool, str]:
        if original.row_count != rewritten.row_count:
            return False, (
                f"Row count mismatch: original={original.row_count}, "
                f"rewritten={rewritten.row_count}"
            )
        return True, ""

    def _check_columns(
        self,
        original: ResultSetMetadata,
        rewritten: ResultSetMetadata,
    ) -> Tuple[bool, str]:
        if original.column_count != rewritten.column_count:
            return False, (
                f"Column count mismatch: original={original.column_count}, "
                f"rewritten={rewritten.column_count}"
            )

        orig_cols_lower = {c.lower() for c in original.column_names}
        rewrite_cols_lower = {c.lower() for c in rewritten.column_names}

        missing = orig_cols_lower - rewrite_cols_lower
        extra = rewrite_cols_lower - orig_cols_lower

        if missing:
            return False, f"Missing columns in rewritten query: {missing}"
        if extra:
            return False, f"Extra columns in rewritten query: {extra}"

        return True, ""

    def _check_data(
        self,
        original: QueryResult,
        rewritten: QueryResult,
    ) -> Tuple[bool, str]:
        orig_rows = original.rows or []
        rewrite_rows = rewritten.rows or []

        orig_normalized = {self._normalize_row(row) for row in orig_rows[:self.max_rows_to_compare]}
        rewrite_normalized = {self._normalize_row(row) for row in rewrite_rows[:self.max_rows_to_compare]}

        missing = orig_normalized - rewrite_normalized
        extra = rewrite_normalized - orig_normalized

        if missing:
            sample_missing = list(missing)[:3]
            return False, f"Missing rows in rewritten query (first {len(sample_missing)} shown): {sample_missing}"
        if extra:
            sample_extra = list(extra)[:3]
            return False, f"Extra rows in rewritten query (first {len(sample_extra)} shown): {sample_extra}"

        return True, ""

    def _check_order(
        self,
        original: QueryResult,
        rewritten: QueryResult,
    ) -> Tuple[bool, str]:
        orig_rows = original.rows or []
        rewrite_rows = rewritten.rows or []

        compare_count = min(len(orig_rows), len(rewrite_rows), self.max_rows_to_compare)

        for i in range(compare_count):
            orig_norm = self._normalize_row(orig_rows[i])
            rewrite_norm = self._normalize_row(rewrite_rows[i])

            if orig_norm != rewrite_norm:
                return False, (
                    f"Order mismatch at row {i}: "
                    f"original={orig_norm}, rewritten={rewrite_norm}"
                )

        return True, ""

    def validate_sql_equivalence(
        self,
        connector: Any,
        original_sql: str,
        rewritten_sql: str,
    ) -> ValidationResult:
        wrapped_original = f"""
        SELECT COUNT(*) as row_count, MD5(GROUP_CONCAT(row_hash)) as total_hash
        FROM (
            SELECT MD5(CONCAT_WS('|', *)) as row_hash
            FROM ({original_sql}) as orig
        ) as hashes
        """

        wrapped_rewritten = f"""
        SELECT COUNT(*) as row_count, MD5(GROUP_CONCAT(row_hash)) as total_hash
        FROM (
            SELECT MD5(CONCAT_WS('|', *)) as row_hash
            FROM ({rewritten_sql}) as rw
        ) as hashes
        """

        try:
            orig_result = connector.execute(wrapped_original)
            rewrite_result = connector.execute(wrapped_rewritten)

            return self.validate(orig_result, rewrite_result)
        except Exception as e:
            orig_result = connector.execute(original_sql)
            rewrite_result = connector.execute(rewritten_sql)
            return self.validate(orig_result, rewrite_result)
