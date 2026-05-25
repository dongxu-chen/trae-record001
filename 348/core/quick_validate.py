import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from core.db_driver import DatabaseDriver
from core.validation_engine import CheckStatus, CheckResult

logger = logging.getLogger(__name__)


@dataclass
class QuickValidationResult:
    table_name: str
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'table_name': self.table_name,
            'passed': self.passed,
            'checks': [{
                'name': c.check_name,
                'status': c.status.value,
                'message': c.message
            } for c in self.checks],
            'metadata': self.metadata,
            'duration_seconds': self.duration_seconds
        }


@dataclass
class QuickValidationReport:
    summary: Dict[str, Any] = field(default_factory=dict)
    table_results: List[QuickValidationResult] = field(default_factory=list)
    duration_seconds: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'summary': self.summary,
            'table_results': [tr.to_dict() for tr in self.table_results],
            'duration_seconds': self.duration_seconds,
            'start_time': self.start_time,
            'end_time': self.end_time
        }


class QuickValidator:
    """快速验证模式 - 只校验元数据和主键范围，快速筛查问题"""

    def __init__(
        self,
        source_driver: DatabaseDriver,
        target_driver: DatabaseDriver,
        config: Optional[Dict[str, Any]] = None
    ):
        self.source_driver = source_driver
        self.target_driver = target_driver
        self.config = config or {}

        self.check_pk_exists = self.config.get('check_primary_key', True)
        self.check_pk_range = self.config.get('check_pk_range', True)
        self.check_row_count = self.config.get('check_row_count', True)
        self.check_metadata = self.config.get('check_metadata', True)
        self.check_table_exists = self.config.get('check_table_exists', True)

        self.row_count_tolerance = self.config.get('row_count_tolerance', 0.0)
        self.include_tables = self.config.get('tables')
        self.exclude_tables = self.config.get('exclude_tables', [])

    def _get_tables_to_validate(self) -> List[str]:
        source_tables = set(self.source_driver.get_tables())

        if self.include_tables:
            tables = [t for t in source_tables if t in self.include_tables]
        else:
            tables = list(source_tables)

        if self.exclude_tables:
            tables = [t for t in tables if t not in self.exclude_tables]

        return sorted(tables)

    def _check_table_exists(
        self,
        table: str,
        target_tables: set
    ) -> CheckResult:
        start = time.time()
        if table in target_tables:
            return CheckResult(
                check_name='table_exists',
                status=CheckStatus.PASSED,
                table_name=table,
                message=f"Table '{table}' exists in target database",
                duration_seconds=time.time() - start
            )
        else:
            return CheckResult(
                check_name='table_exists',
                status=CheckStatus.FAILED,
                table_name=table,
                message=f"Table '{table}' is missing from target database",
                duration_seconds=time.time() - start
            )

    def _check_primary_key(
        self,
        table: str
    ) -> CheckResult:
        start = time.time()
        try:
            src_pk = self.source_driver.get_primary_key(table)
            tgt_pk = self.target_driver.get_primary_key(table)

            if not src_pk and not tgt_pk:
                return CheckResult(
                    check_name='primary_key',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message="No primary key defined in both source and target",
                    duration_seconds=time.time() - start
                )
            elif not src_pk:
                return CheckResult(
                    check_name='primary_key',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message="Source table has no primary key",
                    duration_seconds=time.time() - start
                )
            elif not tgt_pk:
                return CheckResult(
                    check_name='primary_key',
                    status=CheckStatus.FAILED,
                    table_name=table,
                    message=f"Target table missing primary key '{src_pk}'",
                    duration_seconds=time.time() - start
                )
            elif src_pk != tgt_pk:
                return CheckResult(
                    check_name='primary_key',
                    status=CheckStatus.FAILED,
                    table_name=table,
                    message=f"Primary key mismatch: source='{src_pk}', target='{tgt_pk}'",
                    duration_seconds=time.time() - start
                )
            else:
                return CheckResult(
                    check_name='primary_key',
                    status=CheckStatus.PASSED,
                    table_name=table,
                    message=f"Primary key '{src_pk}' matches",
                    details={'primary_key': src_pk},
                    duration_seconds=time.time() - start
                )
        except Exception as e:
            return CheckResult(
                check_name='primary_key',
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )

    def _check_pk_range(
        self,
        table: str
    ) -> CheckResult:
        start = time.time()
        try:
            src_min, src_max = self.source_driver.get_primary_key_range(table)
            tgt_min, tgt_max = self.target_driver.get_primary_key_range(table)

            pk = self.source_driver.get_primary_key(table) or 'PRIMARY'

            if src_min is None or src_max is None:
                return CheckResult(
                    check_name='pk_range',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message="Source table is empty, cannot check PK range",
                    duration_seconds=time.time() - start
                )

            if tgt_min is None or tgt_max is None:
                return CheckResult(
                    check_name='pk_range',
                    status=CheckStatus.FAILED,
                    table_name=table,
                    message="Target table is empty",
                    details={
                        'source_range': [src_min, src_max],
                        'target_range': None
                    },
                    duration_seconds=time.time() - start
                )

            try:
                src_min_f = float(src_min)
                src_max_f = float(src_max)
                tgt_min_f = float(tgt_min)
                tgt_max_f = float(tgt_max)

                if tgt_min_f > src_min_f:
                    return CheckResult(
                        check_name='pk_range',
                        status=CheckStatus.WARNING,
                        table_name=table,
                        message=f"Target PK start ({tgt_min}) is greater than source ({src_min}) - data may be missing at beginning",
                        details={
                            'source_range': [src_min, src_max],
                            'target_range': [tgt_min, tgt_max]
                        },
                        duration_seconds=time.time() - start
                    )

                if tgt_max_f < src_max_f:
                    coverage = ((tgt_max_f - tgt_min_f) / (src_max_f - src_min_f) * 100) if src_max_f > src_min_f else 0
                    return CheckResult(
                        check_name='pk_range',
                        status=CheckStatus.FAILED,
                        table_name=table,
                        message=f"Target PK range only covers {coverage:.1f}% of source range. Target max ({tgt_max}) < source max ({src_max})",
                        details={
                            'source_range': [src_min, src_max],
                            'target_range': [tgt_min, tgt_max],
                            'coverage_percent': coverage
                        },
                        duration_seconds=time.time() - start
                    )

                return CheckResult(
                    check_name='pk_range',
                    status=CheckStatus.PASSED,
                    table_name=table,
                    message=f"PK range fully covered: source=[{src_min}, {src_max}], target=[{tgt_min}, {tgt_max}]",
                    details={
                        'source_range': [src_min, src_max],
                        'target_range': [tgt_min, tgt_max],
                        'primary_key': pk
                    },
                    duration_seconds=time.time() - start
                )

            except (TypeError, ValueError):
                return CheckResult(
                    check_name='pk_range',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message=f"PK values are non-numeric, skipping range comparison: src=[{src_min}, {src_max}], tgt=[{tgt_min}, {tgt_max}]",
                    duration_seconds=time.time() - start
                )

        except Exception as e:
            return CheckResult(
                check_name='pk_range',
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )

    def _check_row_count(
        self,
        table: str
    ) -> CheckResult:
        start = time.time()
        try:
            src_count = self.source_driver.get_row_count(table)
            tgt_count = self.target_driver.get_row_count(table)

            if src_count == tgt_count:
                return CheckResult(
                    check_name='row_count',
                    status=CheckStatus.PASSED,
                    table_name=table,
                    message=f"Row count matches exactly: {src_count}",
                    details={'source_count': src_count, 'target_count': tgt_count},
                    duration_seconds=time.time() - start
                )

            if src_count == 0:
                return CheckResult(
                    check_name='row_count',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message=f"Source table is empty, target has {tgt_count} rows",
                    details={'source_count': src_count, 'target_count': tgt_count},
                    duration_seconds=time.time() - start
                )

            diff = abs(src_count - tgt_count)
            diff_pct = (diff / src_count) * 100

            if diff_pct <= self.row_count_tolerance:
                return CheckResult(
                    check_name='row_count',
                    status=CheckStatus.PASSED,
                    table_name=table,
                    message=f"Row count within tolerance ({diff_pct:.2f}%): source={src_count}, target={tgt_count}",
                    details={
                        'source_count': src_count,
                        'target_count': tgt_count,
                        'diff_percent': diff_pct,
                        'tolerance': self.row_count_tolerance
                    },
                    duration_seconds=time.time() - start
                )
            else:
                return CheckResult(
                    check_name='row_count',
                    status=CheckStatus.FAILED,
                    table_name=table,
                    message=f"Row count exceeds tolerance: diff={diff_pct:.2f}%, source={src_count}, target={tgt_count}",
                    details={
                        'source_count': src_count,
                        'target_count': tgt_count,
                        'diff_percent': diff_pct,
                        'tolerance': self.row_count_tolerance
                    },
                    duration_seconds=time.time() - start
                )

        except Exception as e:
            return CheckResult(
                check_name='row_count',
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )

    def _check_metadata(
        self,
        table: str
    ) -> CheckResult:
        start = time.time()
        try:
            src_cols = self.source_driver.get_table_columns(table)
            tgt_cols = self.target_driver.get_table_columns(table)

            src_col_names = {col['name'] for col in src_cols}
            tgt_col_names = {col['name'] for col in tgt_cols}

            missing_cols = src_col_names - tgt_col_names
            extra_cols = tgt_col_names - src_col_names

            if missing_cols:
                return CheckResult(
                    check_name='metadata',
                    status=CheckStatus.FAILED,
                    table_name=table,
                    message=f"Target missing {len(missing_cols)} column(s): {', '.join(sorted(missing_cols))}",
                    details={
                        'source_columns': [c['name'] for c in src_cols],
                        'target_columns': [c['name'] for c in tgt_cols],
                        'missing_columns': sorted(list(missing_cols)),
                        'extra_columns': sorted(list(extra_cols))
                    },
                    duration_seconds=time.time() - start
                )

            if extra_cols:
                return CheckResult(
                    check_name='metadata',
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message=f"Target has {len(extra_cols)} extra column(s): {', '.join(sorted(extra_cols))}",
                    details={
                        'extra_columns': sorted(list(extra_cols))
                    },
                    duration_seconds=time.time() - start
                )

            return CheckResult(
                check_name='metadata',
                status=CheckStatus.PASSED,
                table_name=table,
                message=f"All {len(src_cols)} columns match",
                details={
                    'column_count': len(src_cols),
                    'columns': [c['name'] for c in src_cols]
                },
                duration_seconds=time.time() - start
            )

        except Exception as e:
            return CheckResult(
                check_name='metadata',
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )

    def _validate_table(self, table: str, target_tables: set) -> QuickValidationResult:
        start = time.time()
        checks: List[CheckResult] = []
        metadata: Dict[str, Any] = {}

        if self.check_table_exists:
            table_check = self._check_table_exists(table, target_tables)
            checks.append(table_check)
            if table_check.status in (CheckStatus.FAILED, CheckStatus.ERROR):
                return QuickValidationResult(
                    table_name=table,
                    passed=False,
                    checks=checks,
                    duration_seconds=time.time() - start
                )

        if self.check_primary_key:
            pk_check = self._check_primary_key(table)
            checks.append(pk_check)
            if pk_check.details and 'primary_key' in pk_check.details:
                metadata['primary_key'] = pk_check.details['primary_key']

        if self.check_pk_range:
            range_check = self._check_pk_range(table)
            checks.append(range_check)
            if range_check.details:
                if 'source_range' in range_check.details:
                    metadata['source_pk_range'] = range_check.details['source_range']
                if 'target_range' in range_check.details:
                    metadata['target_pk_range'] = range_check.details['target_range']
                if 'coverage_percent' in range_check.details:
                    metadata['coverage_percent'] = range_check.details['coverage_percent']

        if self.check_row_count:
            count_check = self._check_row_count(table)
            checks.append(count_check)
            if count_check.details:
                metadata['source_row_count'] = count_check.details.get('source_count')
                metadata['target_row_count'] = count_check.details.get('target_count')

        if self.check_metadata:
            meta_check = self._check_metadata(table)
            checks.append(meta_check)
            if meta_check.details and 'column_count' in meta_check.details:
                metadata['column_count'] = meta_check.details['column_count']

        passed = all(
            c.status in (CheckStatus.PASSED, CheckStatus.WARNING)
            for c in checks
        )

        return QuickValidationResult(
            table_name=table,
            passed=passed,
            checks=checks,
            metadata=metadata,
            duration_seconds=time.time() - start
        )

    def run_quick_validation(self) -> QuickValidationReport:
        report = QuickValidationReport()
        report.start_time = time.time()

        logger.info("=" * 60)
        logger.info("Starting Quick Validation Mode")
        logger.info("=" * 60)
        logger.info(f"Checks enabled: PK exists={self.check_pk_exists}, "
                    f"PK range={self.check_pk_range}, "
                    f"Row count={self.check_row_count}, "
                    f"Metadata={self.check_metadata}")

        tables = self._get_tables_to_validate()
        target_tables = set(self.target_driver.get_tables())

        logger.info(f"Tables to validate: {len(tables)}")

        for table in tables:
            logger.info(f"Validating table: {table}")
            result = self._validate_table(table, target_tables)
            report.table_results.append(result)

            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  {status}: {len(result.checks)} checks in {result.duration_seconds:.3f}s")

        report.end_time = time.time()
        report.duration_seconds = report.end_time - report.start_time

        passed_tables = sum(1 for tr in report.table_results if tr.passed)
        failed_tables = len(report.table_results) - passed_tables

        total_checks = sum(len(tr.checks) for tr in report.table_results)
        passed_checks = sum(
            1 for tr in report.table_results
            for c in tr.checks
            if c.status in (CheckStatus.PASSED, CheckStatus.WARNING)
        )
        failed_checks = total_checks - passed_checks

        warnings = sum(
            1 for tr in report.table_results
            for c in tr.checks
            if c.status == CheckStatus.WARNING
        )

        report.summary = {
            'total_tables': len(report.table_results),
            'passed_tables': passed_tables,
            'failed_tables': failed_tables,
            'total_checks': total_checks,
            'passed_checks': passed_checks,
            'failed_checks': failed_checks,
            'warnings': warnings,
            'overall_status': 'PASSED' if failed_tables == 0 else 'FAILED',
            'pass_rate': (passed_checks / total_checks * 100) if total_checks > 0 else 100
        }

        logger.info("=" * 60)
        logger.info(f"Quick Validation Complete: {report.summary['overall_status']}")
        logger.info(f"  Tables: {passed_tables}/{len(report.table_results)} passed")
        logger.info(f"  Checks: {passed_checks}/{total_checks} passed, {warnings} warnings")
        logger.info(f"  Duration: {report.duration_seconds:.2f}s")
        logger.info("=" * 60)

        return report
