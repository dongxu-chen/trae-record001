import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from core.db_driver import DatabaseDriver
from core.validation_engine import CheckStatus, CheckResult

logger = logging.getLogger(__name__)


class DiffType(Enum):
    ROW_ADDED = "ROW_ADDED"
    ROW_REMOVED = "ROW_REMOVED"
    ROW_MODIFIED = "ROW_MODIFIED"
    TABLE_ADDED = "TABLE_ADDED"
    TABLE_REMOVED = "TABLE_REMOVED"
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_REMOVED = "COLUMN_REMOVED"
    COLUMN_TYPE_CHANGED = "COLUMN_TYPE_CHANGED"


@dataclass
class DiffItem:
    diff_type: DiffType
    table_name: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    primary_key: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'diff_type': self.diff_type.value,
            'table_name': self.table_name,
            'message': self.message,
            'details': self.details,
            'primary_key': str(self.primary_key) if self.primary_key else None
        }


@dataclass
class TableDiffResult:
    table_name: str
    schema_diff: List[DiffItem] = field(default_factory=list)
    data_diff: List[DiffItem] = field(default_factory=list)
    row_count_source: int = 0
    row_count_target: int = 0
    row_count_diff: int = 0

    @property
    def has_diffs(self) -> bool:
        return len(self.schema_diff) > 0 or len(self.data_diff) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'table_name': self.table_name,
            'schema_diff': [d.to_dict() for d in self.schema_diff],
            'data_diff': [d.to_dict() for d in self.data_diff],
            'row_count_source': self.row_count_source,
            'row_count_target': self.row_count_target,
            'row_count_diff': self.row_count_diff,
            'has_diffs': self.has_diffs
        }


@dataclass
class DiffReport:
    summary: Dict[str, Any] = field(default_factory=dict)
    table_diffs: List[TableDiffResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': self.summary,
            'table_diffs': [td.to_dict() for td in self.table_diffs],
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time,
            'end_time': self.end_time
        }


class DataDiffAnalyzer:
    def __init__(
        self,
        source_driver: DatabaseDriver,
        target_driver: DatabaseDriver,
        config: Optional[Dict[str, Any]] = None
    ):
        self.source_driver = source_driver
        self.target_driver = target_driver
        self.config = config or {}
        self.max_data_diffs_per_table = self.config.get('max_data_diffs_per_table', 100)
        self.compare_row_values = self.config.get('compare_row_values', True)
        self.deep_compare = self.config.get('deep_compare', False)
        self.batch_size = self.config.get('batch_size', 1000)
        self.include_tables = self.config.get('tables')
        self.exclude_tables = self.config.get('exclude_tables', [])

    def _get_tables_to_compare(self) -> Tuple[List[str], List[str], List[str]]:
        source_tables = set(self.source_driver.get_tables())
        target_tables = set(self.target_driver.get_tables())

        common_tables = sorted(list(source_tables & target_tables))
        source_only = sorted(list(source_tables - target_tables))
        target_only = sorted(list(target_tables - source_tables))

        if self.include_tables:
            common_tables = [t for t in common_tables if t in self.include_tables]
            source_only = [t for t in source_only if t in self.include_tables]
            target_only = [t for t in target_only if t in self.include_tables]

        if self.exclude_tables:
            common_tables = [t for t in common_tables if t not in self.exclude_tables]
            source_only = [t for t in source_only if t not in self.exclude_tables]
            target_only = [t for t in target_only if t not in self.exclude_tables]

        return common_tables, source_only, target_only

    def compare_schema(self, table: str) -> List[DiffItem]:
        diffs = []
        source_cols = {col['name']: col for col in self.source_driver.get_table_columns(table)}
        target_cols = {col['name']: col for col in self.target_driver.get_table_columns(table)}

        source_col_names = set(source_cols.keys())
        target_col_names = set(target_cols.keys())

        for col in sorted(source_col_names - target_col_names):
            diffs.append(DiffItem(
                diff_type=DiffType.COLUMN_REMOVED,
                table_name=table,
                message=f"Column '{col}' exists in source but missing in target",
                details={'column': col, 'source_type': source_cols[col]['type']}
            ))

        for col in sorted(target_col_names - source_col_names):
            diffs.append(DiffItem(
                diff_type=DiffType.COLUMN_ADDED,
                table_name=table,
                message=f"Column '{col}' added in target but missing in source",
                details={'column': col, 'target_type': target_cols[col]['type']}
            ))

        for col in sorted(source_col_names & target_col_names):
            src_type = source_cols[col]['type'].lower()
            tgt_type = target_cols[col]['type'].lower()
            if src_type != tgt_type:
                diffs.append(DiffItem(
                    diff_type=DiffType.COLUMN_TYPE_CHANGED,
                    table_name=table,
                    message=f"Column '{col}' type changed from '{src_type}' to '{tgt_type}'",
                    details={'column': col, 'source_type': src_type, 'target_type': tgt_type}
                ))

        return diffs

    def compare_table_data(
        self,
        table: str,
        pk: Optional[str] = None
    ) -> List[DiffItem]:
        diffs = []

        if not pk:
            pk = self.source_driver.get_primary_key(table)

        if not pk:
            logger.warning(f"Cannot compare data for {table}: no primary key found")
            return diffs

        if not self.compare_row_values:
            return diffs

        try:
            src_min, src_max = self.source_driver.get_primary_key_range(table)
            tgt_min, tgt_max = self.target_driver.get_primary_key_range(table)

            if src_min is None or src_max is None:
                logger.warning(f"Cannot get primary key range for source table {table}")
                return diffs

            source_count = self.source_driver.get_row_count(table)
            target_count = self.target_driver.get_row_count(table)

            if source_count == 0 and target_count == 0:
                return diffs

            if source_count <= self.max_data_diffs_per_table and target_count <= self.max_data_diffs_per_table:
                return self._compare_all_rows(table, pk, diffs)

            if self.deep_compare:
                return self._compare_rows_by_pk_range(table, pk, src_min, src_max, diffs)
            else:
                return self._compare_rows_sampled(table, pk, diffs)

        except Exception as e:
            logger.error(f"Data comparison failed for {table}: {e}", exc_info=True)
            return diffs

    def _compare_all_rows(
        self,
        table: str,
        pk: str,
        diffs: List[DiffItem]
    ) -> List[DiffItem]:
        source_rows = self._get_all_rows_by_pk(self.source_driver, table, pk)
        target_rows = self._get_all_rows_by_pk(self.target_driver, table, pk)

        for pk_val in sorted(set(source_rows.keys()) - set(target_rows.keys())):
            if len(diffs) >= self.max_data_diffs_per_table:
                break
            diffs.append(DiffItem(
                diff_type=DiffType.ROW_REMOVED,
                table_name=table,
                message=f"Row with pk={pk_val} removed in target",
                primary_key=pk_val
            ))

        for pk_val in sorted(set(target_rows.keys()) - set(source_rows.keys())):
            if len(diffs) >= self.max_data_diffs_per_table:
                break
            diffs.append(DiffItem(
                diff_type=DiffType.ROW_ADDED,
                table_name=table,
                message=f"Row with pk={pk_val} added in target",
                primary_key=pk_val
            ))

        for pk_val in sorted(set(source_rows.keys()) & set(target_rows.keys())):
            if len(diffs) >= self.max_data_diffs_per_table:
                break
            src_row = source_rows[pk_val]
            tgt_row = target_rows[pk_val]
            col_diffs = self._compare_row_columns(src_row, tgt_row)
            if col_diffs:
                diffs.append(DiffItem(
                    diff_type=DiffType.ROW_MODIFIED,
                    table_name=table,
                    message=f"Row with pk={pk_val} has {len(col_diffs)} column(s) modified",
                    primary_key=pk_val,
                    details={'modified_columns': col_diffs}
                ))

        return diffs

    def _get_all_rows_by_pk(
        self,
        driver: DatabaseDriver,
        table: str,
        pk: str
    ) -> Dict[Any, Dict]:
        if driver.config.db_type == 'mysql':
            query = f"SELECT * FROM `{table}` ORDER BY `{pk}`"
        elif driver.config.db_type == 'postgresql':
            schema = driver.config.schema or 'public'
            query = f'SELECT * FROM "{schema}"."{table}" ORDER BY "{pk}"'
        else:
            return {}

        results = driver.execute_query(query)
        return {row[pk]: row for row in results}

    def _compare_rows_by_pk_range(
        self,
        table: str,
        pk: str,
        pk_min: Any,
        pk_max: Any,
        diffs: List[DiffItem]
    ) -> List[DiffItem]:
        try:
            min_val = float(pk_min)
            max_val = float(pk_max)
        except (TypeError, ValueError):
            logger.warning(f"PK values not numeric for {table}, using sampled comparison")
            return self._compare_rows_sampled(table, pk, diffs)

        total_range = max_val - min_val
        if total_range <= 0:
            return diffs

        num_batches = min(100, int(total_range / self.batch_size) + 1)
        batch_pks = max(1, self.max_data_diffs_per_table // num_batches)

        for i in range(num_batches):
            if len(diffs) >= self.max_data_diffs_per_table:
                break

            batch_start = min_val + i * (total_range / num_batches)
            batch_end = min_val + (i + 1) * (total_range / num_batches)

            batch_diffs = self._compare_batch(table, pk, batch_start, batch_end, batch_pks)
            diffs.extend(batch_diffs)

        return diffs

    def _compare_batch(
        self,
        table: str,
        pk: str,
        start: float,
        end: float,
        max_diffs: int
    ) -> List[DiffItem]:
        diffs = []

        if self.source_driver.config.db_type == 'mysql':
            src_query = f"SELECT * FROM `{table}` WHERE `{pk}` >= %s AND `{pk}` < %s ORDER BY `{pk}` LIMIT %s"
            tgt_query = f"SELECT * FROM `{table}` WHERE `{pk}` >= %s AND `{pk}` < %s ORDER BY `{pk}` LIMIT %s"
        elif self.source_driver.config.db_type == 'postgresql':
            schema = self.source_driver.config.schema or 'public'
            src_query = f'SELECT * FROM "{schema}"."{table}" WHERE "{pk}" >= %s AND "{pk}" < %s ORDER BY "{pk}" LIMIT %s'
            tgt_query = f'SELECT * FROM "{schema}"."{table}" WHERE "{pk}" >= %s AND "{pk}" < %s ORDER BY "{pk}" LIMIT %s'
        else:
            return diffs

        try:
            src_rows = {row[pk]: row for row in self.source_driver.execute_query(src_query, (start, end, max_diffs * 2))}
            tgt_rows = {row[pk]: row for row in self.target_driver.execute_query(tgt_query, (start, end, max_diffs * 2))}

            src_pks = set(src_rows.keys())
            tgt_pks = set(tgt_rows.keys())

            for pk_val in sorted(src_pks - tgt_pks)[:max_diffs]:
                diffs.append(DiffItem(
                    diff_type=DiffType.ROW_REMOVED,
                    table_name=table,
                    message=f"Row removed: pk={pk_val}",
                    primary_key=pk_val
                ))

            for pk_val in sorted(tgt_pks - src_pks)[:max_diffs]:
                diffs.append(DiffItem(
                    diff_type=DiffType.ROW_ADDED,
                    table_name=table,
                    message=f"Row added: pk={pk_val}",
                    primary_key=pk_val
                ))

            for pk_val in sorted(src_pks & tgt_pks)[:max_diffs]:
                col_diffs = self._compare_row_columns(src_rows[pk_val], tgt_rows[pk_val])
                if col_diffs:
                    diffs.append(DiffItem(
                        diff_type=DiffType.ROW_MODIFIED,
                        table_name=table,
                        message=f"Row modified: pk={pk_val}",
                        primary_key=pk_val,
                        details={'modified_columns': col_diffs}
                    ))

        except Exception as e:
            logger.warning(f"Batch comparison failed for {table} range [{start}, {end}]: {e}")

        return diffs

    def _compare_rows_sampled(
        self,
        table: str,
        pk: str,
        diffs: List[DiffItem]
    ) -> List[DiffItem]:
        source_count = self.source_driver.get_row_count(table)
        if source_count == 0:
            return diffs

        sample_size = min(self.max_data_diffs_per_table, max(100, int(source_count * 0.01)))

        if self.source_driver.config.db_type == 'mysql':
            src_query = f"SELECT * FROM `{table}` ORDER BY RAND() LIMIT %s"
            tgt_query = f"SELECT * FROM `{table}` WHERE `{pk}` IN ({', '.join(['%s'] * sample_size)})"
        elif self.source_driver.config.db_type == 'postgresql':
            schema = self.source_driver.config.schema or 'public'
            src_query = f'SELECT * FROM "{schema}"."{table}" ORDER BY RANDOM() LIMIT %s'
            tgt_query = f'SELECT * FROM "{schema}"."{table}" WHERE "{pk}" IN ({", ".join(["%s"] * sample_size)})'
        else:
            return diffs

        try:
            src_rows = self.source_driver.execute_query(src_query, (sample_size,))
            src_dict = {row[pk]: row for row in src_rows}
            src_pks = list(src_dict.keys())

            tgt_rows = self.target_driver.execute_query(tgt_query, tuple(src_pks))
            tgt_dict = {row[pk]: row for row in tgt_rows}

            for pk_val in src_pks:
                if len(diffs) >= self.max_data_diffs_per_table:
                    break

                if pk_val not in tgt_dict:
                    diffs.append(DiffItem(
                        diff_type=DiffType.ROW_REMOVED,
                        table_name=table,
                        message=f"Row removed: pk={pk_val}",
                        primary_key=pk_val
                    ))
                else:
                    col_diffs = self._compare_row_columns(src_dict[pk_val], tgt_dict[pk_val])
                    if col_diffs:
                        diffs.append(DiffItem(
                            diff_type=DiffType.ROW_MODIFIED,
                            table_name=table,
                            message=f"Row modified: pk={pk_val}",
                            primary_key=pk_val,
                            details={'modified_columns': col_diffs}
                        ))

        except Exception as e:
            logger.warning(f"Sampled comparison failed for {table}: {e}")

        return diffs

    def _compare_row_columns(self, src_row: Dict, tgt_row: Dict) -> List[Dict]:
        diffs = []
        all_cols = set(src_row.keys()) | set(tgt_row.keys())

        for col in all_cols:
            src_val = str(src_row.get(col, ''))
            tgt_val = str(tgt_row.get(col, ''))
            if src_val != tgt_val:
                diffs.append({
                    'column': col,
                    'source_value': src_val,
                    'target_value': tgt_val
                })

        return diffs

    def run_diff_analysis(self) -> DiffReport:
        report = DiffReport()
        report.start_time = time.time()

        logger.info("=" * 60)
        logger.info("Starting Data Diff Analysis")
        logger.info("=" * 60)

        common_tables, source_only, target_only = self._get_tables_to_compare()

        logger.info(f"Common tables: {len(common_tables)}, "
                    f"Source-only: {len(source_only)}, "
                    f"Target-only: {len(target_only)}")

        for table in source_only:
            report.table_diffs.append(TableDiffResult(
                table_name=table,
                schema_diff=[DiffItem(
                    diff_type=DiffType.TABLE_REMOVED,
                    table_name=table,
                    message=f"Table '{table}' exists in source but missing in target"
                )],
                row_count_source=self.source_driver.get_row_count(table),
                row_count_diff=self.source_driver.get_row_count(table)
            ))

        for table in target_only:
            report.table_diffs.append(TableDiffResult(
                table_name=table,
                schema_diff=[DiffItem(
                    diff_type=DiffType.TABLE_ADDED,
                    table_name=table,
                    message=f"Table '{table}' added in target but missing in source"
                )],
                row_count_target=self.target_driver.get_row_count(table),
                row_count_diff=-self.target_driver.get_row_count(table)
            ))

        for table in common_tables:
            logger.info(f"Comparing table: {table}")

            table_diff = TableDiffResult(table_name=table)
            table_diff.row_count_source = self.source_driver.get_row_count(table)
            table_diff.row_count_target = self.target_driver.get_row_count(table)
            table_diff.row_count_diff = table_diff.row_count_target - table_diff.row_count_source

            logger.info(f"  Row count: source={table_diff.row_count_source}, "
                        f"target={table_diff.row_count_target}, "
                        f"diff={table_diff.row_count_diff}")

            table_diff.schema_diff = self.compare_schema(table)
            logger.info(f"  Schema diffs: {len(table_diff.schema_diff)}")

            if not table_diff.schema_diff and self.compare_row_values:
                table_diff.data_diff = self.compare_table_data(table)
                logger.info(f"  Data diffs: {len(table_diff.data_diff)}")

            report.table_diffs.append(table_diff)

        report.end_time = time.time()
        report.duration_seconds = report.end_time - report.start_time

        total_schema_diffs = sum(len(td.schema_diff) for td in report.table_diffs)
        total_data_diffs = sum(len(td.data_diff) for td in report.table_diffs)
        tables_with_diffs = sum(1 for td in report.table_diffs if td.has_diffs)

        report.summary = {
            'total_tables': len(common_tables) + len(source_only) + len(target_only),
            'common_tables': len(common_tables),
            'tables_added': len(target_only),
            'tables_removed': len(source_only),
            'tables_with_diffs': tables_with_diffs,
            'total_schema_diffs': total_schema_diffs,
            'total_data_diffs': total_data_diffs,
            'overall_status': 'CLEAN' if tables_with_diffs == 0 else 'DIFFS_FOUND'
        }

        logger.info("=" * 60)
        logger.info(f"Diff Analysis Complete: {report.summary['overall_status']}")
        logger.info(f"  Tables with diffs: {tables_with_diffs}/{len(report.table_diffs)}")
        logger.info(f"  Schema diffs: {total_schema_diffs}, Data diffs: {total_data_diffs}")
        logger.info(f"  Duration: {report.duration_seconds:.2f}s")
        logger.info("=" * 60)

        return report
