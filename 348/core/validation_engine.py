import logging
import random
import yaml
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from config import ValidationConfig
from core.db_driver import DatabaseDriver

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    check_name: str
    status: CheckStatus
    table_name: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


class ValidationRule:
    def __init__(self, name: str, rule_type: str, config: Dict[str, Any]):
        self.name = name
        self.rule_type = rule_type
        self.config = config
        self.enabled = config.get('enabled', True)

    def execute(self, driver: DatabaseDriver, table: str) -> CheckResult:
        pass


class RowCountCheck(ValidationRule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__('row_count', 'row_count', config)
        self.tolerance = config.get('tolerance', 0.0)

    def execute(self, source_driver: DatabaseDriver, verify_driver: DatabaseDriver, table: str) -> CheckResult:
        start = time.time()
        try:
            source_count = source_driver.get_row_count(table)
            verify_count = verify_driver.get_row_count(table)

            if source_count == verify_count:
                status = CheckStatus.PASSED
                message = f"Row count matches: {source_count}"
            elif self.tolerance > 0:
                diff = abs(source_count - verify_count)
                diff_pct = (diff / source_count) * 100 if source_count > 0 else 0
                if diff_pct <= self.tolerance:
                    status = CheckStatus.PASSED
                    message = f"Row count within tolerance: source={source_count}, verify={verify_count}, diff={diff_pct:.2f}%"
                else:
                    status = CheckStatus.FAILED
                    message = f"Row count exceeds tolerance: source={source_count}, verify={verify_count}, diff={diff_pct:.2f}%"
            else:
                status = CheckStatus.FAILED
                message = f"Row count mismatch: source={source_count}, verify={verify_count}"

            return CheckResult(
                check_name='row_count',
                status=status,
                table_name=table,
                message=message,
                details={'source_count': source_count, 'verify_count': verify_count},
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


class SampleCheck(ValidationRule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__('sample_check', 'sample', config)
        self.sample_percentage = config.get('sample_percentage', 5.0)
        self.sample_min = config.get('sample_min_rows', 100)
        self.sample_max = config.get('sample_max_rows', 10000)
        self.stratified_sampling = config.get('stratified_sampling', True)
        self.num_strata = config.get('num_strata', 10)

    def _calculate_sample_size(self, total_rows: int) -> int:
        if total_rows == 0:
            return 0
        sample_size = int(total_rows * self.sample_percentage / 100)
        return max(self.sample_min, min(sample_size, self.sample_max, total_rows))

    def _get_stratified_primary_keys(
        self,
        driver: DatabaseDriver,
        table: str,
        sample_size: int
    ) -> List[Any]:
        pk = driver.get_primary_key(table)
        min_val, max_val = driver.get_primary_key_range(table)

        if pk is None or min_val is None or max_val is None:
            logger.warning(f"Cannot perform stratified sampling for {table}, falling back to random offset")
            return []

        logger.info(f"Stratified sampling for {table}: pk={pk}, range=[{min_val}, {max_val}]")

        num_strata = min(self.num_strata, sample_size)
        samples_per_stratum = max(1, sample_size // num_strata)
        actual_sample_size = num_strata * samples_per_stratum

        try:
            min_num = float(min_val) if isinstance(min_val, (int, float)) else 0
            max_num = float(max_val) if isinstance(max_val, (int, float)) else 0
        except (TypeError, ValueError):
            logger.warning(f"Primary key is not numeric for {table}, falling back to random offset")
            return []

        if max_num == min_num:
            logger.warning(f"Primary key range is zero for {table}, using single stratum")
            range_step = 0
        else:
            range_step = (max_num - min_num) / num_strata

        sampled_pks = []

        for stratum_idx in range(num_strata):
            stratum_start = min_num + stratum_idx * range_step
            stratum_end = min_num + (stratum_idx + 1) * range_step

            if range_step > 0:
                if driver.config.db_type == 'mysql':
                    query = f"""
                        SELECT `{pk}` FROM `{table}`
                        WHERE `{pk}` >= %s AND `{pk}` < %s
                        ORDER BY RAND()
                        LIMIT %s
                    """
                elif driver.config.db_type == 'postgresql':
                    schema = driver.config.schema or 'public'
                    query = f"""
                        SELECT "{pk}" FROM "{schema}"."{table}"
                        WHERE "{pk}" >= %s AND "{pk}" < %s
                        ORDER BY RANDOM()
                        LIMIT %s
                    """
                else:
                    query = None

                if query:
                    try:
                        params = (stratum_start, stratum_end, samples_per_stratum)
                        results = driver.execute_query(query, params)
                        for row in results:
                            sampled_pks.append(row[pk])
                    except Exception as e:
                        logger.warning(f"Stratum {stratum_idx} query failed: {e}")
            else:
                logger.warning(f"Range step is zero for stratum {stratum_idx}, skipping stratified sampling")

        while len(sampled_pks) < sample_size:
            logger.info(f"Filling remaining samples: {len(sampled_pks)}/{sample_size}")
            if driver.config.db_type == 'mysql':
                query = f"SELECT `{pk}` FROM `{table}` ORDER BY RAND() LIMIT %s"
            elif driver.config.db_type == 'postgresql':
                schema = driver.config.schema or 'public'
                query = f'SELECT "{pk}" FROM "{schema}"."{table}" ORDER BY RANDOM() LIMIT %s'
            else:
                break
            try:
                results = driver.execute_query(query, (sample_size - len(sampled_pks),))
                for row in results:
                    pk_val = row[pk]
                    if pk_val not in sampled_pks:
                        sampled_pks.append(pk_val)
            except Exception as e:
                logger.warning(f"Random fill query failed: {e}")
                break

        return sampled_pks[:sample_size]

    def _get_rows_by_primary_keys(
        self,
        driver: DatabaseDriver,
        table: str,
        pk: str,
        pk_values: List[Any]
    ) -> Dict[Any, Dict]:
        if not pk_values:
            return {}

        if driver.config.db_type == 'mysql':
            placeholders = ', '.join(['%s'] * len(pk_values))
            query = f"SELECT * FROM `{table}` WHERE `{pk}` IN ({placeholders})"
        elif driver.config.db_type == 'postgresql':
            schema = driver.config.schema or 'public'
            placeholders = ', '.join(['%s'] * len(pk_values))
            query = f'SELECT * FROM "{schema}"."{table}" WHERE "{pk}" IN ({placeholders})'
        else:
            return {}

        try:
            results = driver.execute_query(query, tuple(pk_values))
            return {row[pk]: row for row in results}
        except Exception as e:
            logger.error(f"Failed to fetch rows by PK: {e}")
            return {}

    def _get_random_offsets(self, total_rows: int, sample_size: int) -> List[int]:
        if total_rows <= sample_size:
            return list(range(total_rows))
        return sorted(random.sample(range(total_rows), sample_size))

    def execute(self, source_driver: DatabaseDriver, verify_driver: DatabaseDriver, table: str) -> CheckResult:
        start = time.time()
        try:
            source_count = source_driver.get_row_count(table)
            sample_size = self._calculate_sample_size(source_count)

            if sample_size == 0:
                return CheckResult(
                    check_name='sample_check',
                    status=CheckStatus.SKIPPED,
                    table_name=table,
                    message="Table is empty, skipping sample check"
                )

            pk = source_driver.get_primary_key(table)
            use_stratified = self.stratified_sampling and pk is not None

            sampled_pks = []
            source_rows = {}
            verify_rows = {}
            sampling_method = "stratified"

            if use_stratified:
                sampled_pks = self._get_stratified_primary_keys(source_driver, table, sample_size)
                if sampled_pks:
                    source_rows = self._get_rows_by_primary_keys(source_driver, table, pk, sampled_pks)
                    verify_rows = self._get_rows_by_primary_keys(verify_driver, table, pk, sampled_pks)
                else:
                    use_stratified = False
                    sampling_method = "random_offset"

            if not use_stratified:
                sampling_method = "random_offset"
                offsets = self._get_random_offsets(source_count, sample_size)
                for i, offset in enumerate(offsets):
                    source_row = source_driver.get_sample_data(table, 1, offset)
                    verify_row = verify_driver.get_sample_data(table, 1, offset)
                    if source_row:
                        source_rows[i] = source_row[0]
                    if verify_row:
                        verify_rows[i] = verify_row[0]
                sampled_pks = list(range(len(offsets)))

            match_count = 0
            mismatch_count = 0
            errors = []
            strata_info = []

            columns = source_driver.get_table_columns(table)
            col_names = [col['name'] for col in columns]

            for key in sampled_pks:
                source_row = source_rows.get(key)
                verify_row = verify_rows.get(key)

                if not source_row or not verify_row:
                    mismatch_count += 1
                    errors.append(f"Row at pk={key}: missing data (source={source_row is not None}, verify={verify_row is not None})")
                    continue

                row_match = True
                for col in col_names:
                    src_val = str(source_row.get(col, ''))
                    ver_val = str(verify_row.get(col, ''))
                    if src_val != ver_val:
                        row_match = False
                        errors.append(f"Row pk={key}, column {col}: source='{src_val}', verify='{ver_val}'")
                        break

                if row_match:
                    match_count += 1
                else:
                    mismatch_count += 1

            match_rate = (match_count / sample_size * 100) if sample_size > 0 else 100

            if match_rate == 100:
                status = CheckStatus.PASSED
                message = f"All {sample_size} sampled rows match ({sampling_method} sampling)"
            elif match_rate >= 95:
                status = CheckStatus.WARNING
                message = f"{match_count}/{sample_size} rows match ({match_rate:.1f}%, {sampling_method} sampling)"
            else:
                status = CheckStatus.FAILED
                message = f"Only {match_count}/{sample_size} rows match ({match_rate:.1f}%, {sampling_method} sampling)"

            return CheckResult(
                check_name='sample_check',
                status=status,
                table_name=table,
                message=message,
                details={
                    'sample_size': sample_size,
                    'match_count': match_count,
                    'mismatch_count': mismatch_count,
                    'match_rate': match_rate,
                    'sampling_method': sampling_method,
                    'primary_key': pk,
                    'stratified_enabled': self.stratified_sampling,
                    'errors': errors[:20]
                },
                duration_seconds=time.time() - start
            )

        except Exception as e:
            logger.exception(f"Sample check failed for {table}")
            return CheckResult(
                check_name='sample_check',
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )


class BusinessLogicCheck(ValidationRule):
    def __init__(self, rule_config: Dict[str, Any]):
        super().__init__(rule_config.get('name', 'business_logic'), 'business_logic', rule_config)
        self.query = rule_config.get('query', '')
        self.expected_result = rule_config.get('expected_result', {})
        self.comparison = rule_config.get('comparison', 'equals')
        self.description = rule_config.get('description', '')

    def _compare_results(self, actual: Any, expected: Any) -> Tuple[bool, str]:
        if self.comparison == 'equals':
            return actual == expected, f"Expected {expected}, got {actual}"
        elif self.comparison == 'not_equals':
            return actual != expected, f"Expected not {expected}, got {actual}"
        elif self.comparison == 'greater_than':
            return actual > expected, f"Expected > {expected}, got {actual}"
        elif self.comparison == 'less_than':
            return actual < expected, f"Expected < {expected}, got {actual}"
        elif self.comparison == 'greater_or_equal':
            return actual >= expected, f"Expected >= {expected}, got {actual}"
        elif self.comparison == 'less_or_equal':
            return actual <= expected, f"Expected <= {expected}, got {actual}"
        elif self.comparison == 'in':
            return actual in expected, f"Expected in {expected}, got {actual}"
        elif self.comparison == 'not_null':
            return actual is not None, f"Expected not null, got {actual}"
        elif self.comparison == 'is_null':
            return actual is None, f"Expected null, got {actual}"
        elif self.comparison == 'contains':
            return expected in str(actual), f"Expected contains '{expected}', got '{actual}'"
        else:
            return actual == expected, f"Default comparison: expected {expected}, got {actual}"

    def execute(self, driver: DatabaseDriver, table: str) -> CheckResult:
        start = time.time()
        try:
            if not self.query:
                return CheckResult(
                    check_name=self.name,
                    status=CheckStatus.SKIPPED,
                    table_name=table,
                    message="No query defined"
                )

            query = self.query.replace('{table}', table)
            result = driver.execute_query(query)

            if not result:
                return CheckResult(
                    check_name=self.name,
                    status=CheckStatus.WARNING,
                    table_name=table,
                    message="Query returned no results",
                    details={'query': query}
                )

            actual_value = list(result[0].values())[0]

            expected_key = list(self.expected_result.keys())[0] if self.expected_result else ''
            expected_value = self.expected_result.get(expected_key) if self.expected_result else None

            if expected_value is None and actual_value is None:
                status = CheckStatus.PASSED
                message = "Both null"
            elif expected_value is not None:
                is_match, msg = self._compare_results(actual_value, expected_value)
                status = CheckStatus.PASSED if is_match else CheckStatus.FAILED
                message = msg
            else:
                status = CheckStatus.PASSED
                message = f"Query executed successfully, value={actual_value}"

            return CheckResult(
                check_name=self.name,
                status=status,
                table_name=table,
                message=f"{self.description}: {message}" if self.description else message,
                details={
                    'query': query,
                    'actual_value': actual_value,
                    'expected_value': expected_value,
                    'raw_result': result
                },
                duration_seconds=time.time() - start
            )

        except Exception as e:
            return CheckResult(
                check_name=self.name,
                status=CheckStatus.ERROR,
                table_name=table,
                message=str(e),
                duration_seconds=time.time() - start
            )


class ValidationEngine:
    def __init__(self, config: ValidationConfig, source_driver: DatabaseDriver, verify_driver: DatabaseDriver):
        self.config = config
        self.source_driver = source_driver
        self.verify_driver = verify_driver
        self.results: List[CheckResult] = []
        self.business_rules: List[BusinessLogicCheck] = []
        self.custom_rules_config: Dict[str, Any] = {}
        self.row_count_config: Dict[str, Any] = {}
        self.sample_check_config: Dict[str, Any] = {}

        self._load_external_rules()

    def _load_external_rules(self):
        import os
        if not self.config.rules_file:
            logger.info("No external rules file specified, using default config")
            self.row_count_config = {
                'enabled': self.config.row_count_check,
                'tolerance': self.config.row_count_tolerance
            }
            self.sample_check_config = {
                'enabled': self.config.sample_check,
                'sample_percentage': self.config.sample_percentage,
                'sample_min_rows': self.config.sample_min_rows,
                'sample_max_rows': self.config.sample_max_rows,
                'stratified_sampling': True,
                'num_strata': 10
            }
            return

        if not os.path.exists(self.config.rules_file):
            logger.warning(f"Rules file not found: {self.config.rules_file}, using default config")
            self.row_count_config = {'enabled': self.config.row_count_check}
            self.sample_check_config = {'enabled': self.config.sample_check}
            return

        try:
            with open(self.config.rules_file, 'r', encoding='utf-8') as f:
                rules_data = yaml.safe_load(f)

            if not isinstance(rules_data, dict):
                logger.warning("Invalid rules file format, expected YAML object expected")
                return

            self.custom_rules_config = rules_data

            rc_config = rules_data.get('row_count_check', {})
            if isinstance(rc_config, dict):
                self.row_count_config = {
                    'enabled': rc_config.get('enabled', self.config.row_count_check),
                    'tolerance': rc_config.get('tolerance', self.config.row_count_tolerance),
                    'tables': rc_config.get('tables'),
                    'exclude_tables': rc_config.get('exclude_tables', [])
                }
            else:
                self.row_count_config = {'enabled': self.config.row_count_check}

            sc_config = rules_data.get('sample_check', {})
            if isinstance(sc_config, dict):
                self.sample_check_config = {
                    'enabled': sc_config.get('enabled', self.config.sample_check),
                    'sample_percentage': sc_config.get('sample_percentage', self.config.sample_percentage),
                    'sample_min_rows': sc_config.get('sample_min_rows', self.config.sample_min_rows),
                    'sample_max_rows': sc_config.get('sample_max_rows', self.config.sample_max_rows),
                    'stratified_sampling': sc_config.get('stratified_sampling', True),
                    'num_strata': sc_config.get('num_strata', 10),
                    'tables': sc_config.get('tables'),
                    'exclude_tables': sc_config.get('exclude_tables', [])
                }
            else:
                self.sample_check_config = {'enabled': self.config.sample_check}

            bl_config = rules_data.get('business_logic_check', {})
            if isinstance(bl_config, dict) and bl_config.get('enabled', self.config.business_logic_check):
                rules_list = bl_config.get('rules', [])
                for rule in rules_list:
                    if rule.get('enabled', True):
                        bl_check = BusinessLogicCheck(rule)
                        self.business_rules.append(bl_check)
                        logger.info(f"Loaded business rule: {bl_check.name}")

            logger.info(f"Loaded rules from {self.config.rules_file}: "
                        f"row_count={self.row_count_config['enabled']}, "
                        f"sample_check={self.sample_check_config['enabled']}, "
                        f"business_rules={len(self.business_rules)}")

        except Exception as e:
            logger.error(f"Failed to load external rules: {e}", exc_info=True)

    def _get_tables_to_validate(self) -> List[str]:
        all_tables = self.source_driver.get_tables()

        if self.config.tables_to_validate:
            tables = [t for t in all_tables if t in self.config.tables_to_validate]
        else:
            tables = all_tables

        if self.config.exclude_tables:
            tables = [t for t in tables if t not in self.config.exclude_tables]

        return tables

    def run_row_count_check(self, tables: List[str]) -> List[CheckResult]:
        if not self.row_count_config.get('enabled', False):
            logger.info("Row count check disabled, skipping")
            return []

        include_tables = self.row_count_config.get('tables')
        exclude_tables = self.row_count_config.get('exclude_tables', [])

        checker = RowCountCheck({
            'tolerance': self.row_count_config.get('tolerance', 0.0)
        })

        results = []
        for table in tables:
            if include_tables and table not in include_tables:
                continue
            if table in exclude_tables:
                continue
            logger.info(f"Running row count check for table: {table}")
            result = checker.execute(self.source_driver, self.verify_driver, table)
            results.append(result)
            self.results.append(result)

        return results

    def run_sample_check(self, tables: List[str]) -> List[CheckResult]:
        if not self.sample_check_config.get('enabled', False):
            logger.info("Sample check disabled, skipping")
            return []

        include_tables = self.sample_check_config.get('tables')
        exclude_tables = self.sample_check_config.get('exclude_tables', [])

        checker = SampleCheck(self.sample_check_config)

        results = []
        for table in tables:
            if include_tables and table not in include_tables:
                continue
            if table in exclude_tables:
                continue
            logger.info(f"Running sample check for table: {table}")
            result = checker.execute(self.source_driver, self.verify_driver, table)
            results.append(result)
            self.results.append(result)

        return results

    def run_business_logic_checks(self, tables: List[str]) -> List[CheckResult]:
        if not self.config.business_logic_check:
            logger.info("Business logic check disabled, skipping")
            return []

        if not self.business_rules:
            logger.info("No business rules to execute")
            return []

        results = []
        for table in tables:
            for rule in self.business_rules:
                rule_tables = rule.config.get('tables')
                rule_exclude = rule.config.get('exclude_tables', [])

                if rule_tables and table not in rule_tables:
                    continue
                if table in rule_exclude:
                    continue

                logger.info(f"Running business rule '{rule.name}' for table: {table}")
                result = rule.execute(self.verify_driver, table)
                results.append(result)
                self.results.append(result)

        return results

    def run_all_validations(self) -> Dict[str, Any]:
        logger.info("Starting validation engine...")
        tables = self._get_tables_to_validate()
        logger.info(f"Tables to validate: {tables}")

        self.results = []

        logger.info("--- Running Row Count Checks ---")
        self.run_row_count_check(tables)

        logger.info("--- Running Sample Checks ---")
        self.run_sample_check(tables)

        logger.info("--- Running Business Logic Checks ---")
        self.run_business_logic_checks(tables)

        return self._summarize_results()

    def _summarize_results(self) -> Dict[str, Any]:
        passed = [r for r in self.results if r.status == CheckStatus.PASSED]
        failed = [r for r in self.results if r.status == CheckStatus.FAILED]
        warnings = [r for r in self.results if r.status == CheckStatus.WARNING]
        errors = [r for r in self.results if r.status == CheckStatus.ERROR]
        skipped = [r for r in self.results if r.status == CheckStatus.SKIPPED]

        total = len(self.results)
        total_checks = total - len(skipped)
        pass_rate = (len(passed) / total_checks * 100) if total_checks > 0 else 100

        overall_status = CheckStatus.PASSED
        if len(failed) > 0 or len(errors) > 0:
            overall_status = CheckStatus.FAILED
        elif len(warnings) > 0:
            overall_status = CheckStatus.WARNING

        return {
            'overall_status': overall_status,
            'total_checks': total,
            'passed': len(passed),
            'failed': len(failed),
            'warnings': len(warnings),
            'errors': len(errors),
            'skipped': len(skipped),
            'pass_rate': pass_rate,
            'results': self.results
        }
