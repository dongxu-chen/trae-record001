import logging
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


class CheckStatus(Enum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    ERROR = "error"
    SKIPPED = "skipped"


class CheckMethod(Enum):
    COUNT = "count"
    CHECKSUM = "checksum"
    SAMPLE = "sample"
    GTID = "gtid"


@dataclass
class TableCheckResult:
    database: str
    table: str
    method: CheckMethod
    status: CheckStatus
    master_count: int = -1
    slave_count: int = -1
    master_checksum: str = ""
    slave_checksum: str = ""
    sample_mismatches: int = 0
    sample_total: int = 0
    check_duration_ms: float = 0.0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsistencyCheckResult:
    check_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    tables_checked: int = 0
    tables_consistent: int = 0
    tables_inconsistent: int = 0
    tables_error: int = 0
    tables_skipped: int = 0
    results: List[TableCheckResult] = field(default_factory=list)
    gtid_consistent: Optional[bool] = None
    recommendations: List[str] = field(default_factory=list)
    summary: str = ""


class ConsistencyChecker:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection,
                 config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.sample_size = config.get('consistency', {}).get('sample_size', 1000)
        self.check_methods = config.get('consistency', {}).get('check_methods', ['count', 'checksum', 'sample'])
        self.max_rows_for_checksum = config.get('consistency', {}).get('max_rows_for_checksum', 1000000)
        self.skip_databases = config.get('consistency', {}).get('skip_databases',
            ['information_schema', 'mysql', 'performance_schema', 'sys'])
        self.check_delay_threshold = config.get('consistency', {}).get('check_delay_threshold', 5)

    def run_full_check(self) -> ConsistencyCheckResult:
        check_id = f"check_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = ConsistencyCheckResult(
            check_id=check_id,
            start_time=datetime.now()
        )

        logger.info(f"开始一致性校验: {check_id}")

        current_delay = self._get_slave_delay()
        if current_delay > self.check_delay_threshold:
            logger.warning(f"当前延迟{current_delay}秒超过阈值{self.check_delay_threshold}秒，校验结果可能不准确")

        result.gtid_consistent = self._check_gtid_consistency()

        tables = self._get_tables_to_check()

        for db, table in tables:
            table_result = self._check_table(db, table)
            result.results.append(table_result)

            if table_result.status == CheckStatus.CONSISTENT:
                result.tables_consistent += 1
            elif table_result.status == CheckStatus.INCONSISTENT:
                result.tables_inconsistent += 1
            elif table_result.status == CheckStatus.ERROR:
                result.tables_error += 1
            else:
                result.tables_skipped += 1

        result.tables_checked = len(tables)
        result.end_time = datetime.now()
        result.total_duration_ms = (result.end_time - result.start_time).total_seconds() * 1000

        self._generate_recommendations(result)
        result.summary = self._generate_summary(result)

        logger.info(f"一致性校验完成: {result.tables_consistent}/{result.tables_checked} 一致, "
                   f"{result.tables_inconsistent} 不一致")
        return result

    def run_sample_check(self, database: str, table: str, sample_size: int = None) -> TableCheckResult:
        size = sample_size or self.sample_size
        return self._check_table_sample(database, table, size)

    def _get_slave_delay(self) -> float:
        try:
            slave_status = self.slave_conn.get_slave_status()
            return float(slave_status.get('seconds_behind_master', 0) or 0)
        except Exception:
            return -1

    def _check_gtid_consistency(self) -> Optional[bool]:
        try:
            master_vars = self.master_conn.get_global_variables()
            slave_vars = self.slave_conn.get_global_variables()

            master_gtid = master_vars.get('gtid_executed', '')
            slave_gtid = slave_vars.get('gtid_executed', '')

            if not master_gtid and not slave_gtid:
                logger.info("GTID未启用，跳过GTID一致性检查")
                return None

            is_consistent = self._compare_gtid_sets(master_gtid, slave_gtid)
            logger.info(f"GTID一致性: {'一致' if is_consistent else '不一致'}")
            return is_consistent
        except Exception as e:
            logger.warning(f"GTID一致性检查失败: {str(e)}")
            return None

    def _compare_gtid_sets(self, master_gtid: str, slave_gtid: str) -> bool:
        if not master_gtid:
            return True

        master_sets = self._parse_gtid_string(master_gtid)
        slave_sets = self._parse_gtid_string(slave_gtid)

        for uuid, intervals in master_sets.items():
            if uuid not in slave_sets:
                return False
            master_range = self._merge_intervals(intervals)
            slave_range = self._merge_intervals(slave_sets[uuid])

            if master_range[1] > slave_range[1]:
                return False

        return True

    def _parse_gtid_string(self, gtid_str: str) -> Dict[str, List[Tuple[int, int]]]:
        result = {}
        if not gtid_str:
            return result

        for part in gtid_str.split(','):
            part = part.strip()
            if ':' not in part:
                continue
            uuid, ranges = part.split(':', 1)
            if uuid not in result:
                result[uuid] = []
            for range_str in ranges.split(':'):
                if '-' in range_str:
                    start, end = range_str.split('-')
                    result[uuid].append((int(start), int(end)))
                else:
                    val = int(range_str)
                    result[uuid].append((val, val))
        return result

    def _merge_intervals(self, intervals: List[Tuple[int, int]]) -> Tuple[int, int]:
        if not intervals:
            return (0, 0)
        return (min(i[0] for i in intervals), max(i[1] for i in intervals))

    def _get_tables_to_check(self) -> List[Tuple[str, str]]:
        tables = []
        try:
            databases = self.master_conn.execute_query("SHOW DATABASES")
            for db_row in databases:
                db_name = list(db_row.values())[0]
                if db_name in self.skip_databases:
                    continue

                try:
                    table_results = self.master_conn.execute_query(
                        "SHOW TABLES FROM %s" % self._quote_identifier(db_name)
                    )
                    for table_row in table_results:
                        table_name = list(table_row.values())[0]
                        tables.append((db_name, table_name))
                except Exception as e:
                    logger.warning(f"获取数据库 {db_name} 的表列表失败: {str(e)}")

        except Exception as e:
            logger.error(f"获取数据库列表失败: {str(e)}")

        logger.info(f"共发现{len(tables)}个表需要校验")
        return tables

    def _quote_identifier(self, identifier: str) -> str:
        return f"`{identifier}`"

    def _check_table(self, database: str, table: str) -> TableCheckResult:
        start_time = time.time()

        for method_str in self.check_methods:
            method = CheckMethod(method_str)

            if method == CheckMethod.COUNT:
                result = self._check_table_count(database, table)
            elif method == CheckMethod.CHECKSUM:
                result = self._check_table_checksum(database, table)
            elif method == CheckMethod.SAMPLE:
                result = self._check_table_sample(database, table, self.sample_size)
            else:
                continue

            result.check_duration_ms = (time.time() - start_time) * 1000

            if result.status == CheckStatus.INCONSISTENT:
                return result

        if not self.check_methods:
            return TableCheckResult(
                database=database, table=table, method=CheckMethod.COUNT,
                status=CheckStatus.SKIPPED, check_duration_ms=(time.time() - start_time) * 1000
            )

        last_result = result
        last_result.check_duration_ms = (time.time() - start_time) * 1000
        return last_result

    def _check_table_count(self, database: str, table: str) -> TableCheckResult:
        db_q = self._quote_identifier(database)
        tb_q = self._quote_identifier(table)

        try:
            master_result = self.master_conn.execute_query(
                f"SELECT COUNT(*) as cnt FROM {db_q}.{tb_q}"
            )
            slave_result = self.slave_conn.execute_query(
                f"SELECT COUNT(*) as cnt FROM {db_q}.{tb_q}"
            )

            master_count = int(list(master_result[0].values())[0]) if master_result else 0
            slave_count = int(list(slave_result[0].values())[0]) if slave_result else 0

            status = CheckStatus.CONSISTENT if master_count == slave_count else CheckStatus.INCONSISTENT

            return TableCheckResult(
                database=database, table=table, method=CheckMethod.COUNT,
                status=status, master_count=master_count, slave_count=slave_count,
                details={"count_diff": master_count - slave_count}
            )
        except Exception as e:
            return TableCheckResult(
                database=database, table=table, method=CheckMethod.COUNT,
                status=CheckStatus.ERROR, error=str(e)
            )

    def _check_table_checksum(self, database: str, table: str) -> TableCheckResult:
        db_q = self._quote_identifier(database)
        tb_q = self._quote_identifier(table)

        try:
            count_result = self.master_conn.execute_query(
                f"SELECT TABLE_ROWS FROM information_schema.TABLES "
                f"WHERE TABLE_SCHEMA='{database}' AND TABLE_NAME='{table}'"
            )
            estimated_rows = int(list(count_result[0].values())[0]) if count_result else 0

            if estimated_rows > self.max_rows_for_checksum:
                return TableCheckResult(
                    database=database, table=table, method=CheckMethod.CHECKSUM,
                    status=CheckStatus.SKIPPED,
                    details={"reason": f"行数{estimated_rows}超过阈值{self.max_rows_for_checksum}"}
                )

            master_result = self.master_conn.execute_query(
                f"CHECKSUM TABLE {db_q}.{tb_q}"
            )
            slave_result = self.slave_conn.execute_query(
                f"CHECKSUM TABLE {db_q}.{tb_q}"
            )

            master_checksum = str(list(master_result[0].values())[-1]) if master_result else ""
            slave_checksum = str(list(slave_result[0].values())[-1]) if slave_result else ""

            status = CheckStatus.CONSISTENT if master_checksum == slave_checksum else CheckStatus.INCONSISTENT

            return TableCheckResult(
                database=database, table=table, method=CheckMethod.CHECKSUM,
                status=status, master_checksum=master_checksum, slave_checksum=slave_checksum
            )
        except Exception as e:
            return TableCheckResult(
                database=database, table=table, method=CheckMethod.CHECKSUM,
                status=CheckStatus.ERROR, error=str(e)
            )

    def _check_table_sample(self, database: str, table: str,
                             sample_size: int) -> TableCheckResult:
        db_q = self._quote_identifier(database)
        tb_q = self._quote_identifier(table)

        try:
            pk_columns = self._get_primary_key_columns(database, table)
            if not pk_columns:
                return TableCheckResult(
                    database=database, table=table, method=CheckMethod.SAMPLE,
                    status=CheckStatus.SKIPPED,
                    details={"reason": "无主键，跳过抽样校验"}
                )

            pk_col = pk_columns[0]
            pk_q = self._quote_identifier(pk_col)

            master_rows = self.master_conn.execute_query(
                f"SELECT * FROM {db_q}.{tb_q} ORDER BY {pk_q} LIMIT %s",
                (sample_size,)
            )
            slave_rows = self.slave_conn.execute_query(
                f"SELECT * FROM {db_q}.{tb_q} ORDER BY {pk_q} LIMIT %s",
                (sample_size,)
            )

            mismatches = 0
            total_compared = min(len(master_rows), len(slave_rows))

            master_map = {str(row.get(pk_col)): row for row in master_rows}
            slave_map = {str(row.get(pk_col)): row for row in slave_rows}

            for pk_val, master_row in master_map.items():
                if pk_val not in slave_map:
                    mismatches += 1
                    continue

                slave_row = slave_map[pk_val]
                master_hash = self._row_hash(master_row)
                slave_hash = self._row_hash(slave_row)

                if master_hash != slave_hash:
                    mismatches += 1

            missing_in_slave = len(master_map) - len(set(master_map.keys()) & set(slave_map.keys()))

            status = CheckStatus.CONSISTENT if mismatches == 0 and missing_in_slave == 0 else CheckStatus.INCONSISTENT

            return TableCheckResult(
                database=database, table=table, method=CheckMethod.SAMPLE,
                status=status, sample_mismatches=mismatches, sample_total=total_compared,
                details={
                    "missing_in_slave": missing_in_slave,
                    "mismatch_rate": f"{mismatches}/{total_compared}",
                    "pk_column": pk_col
                }
            )
        except Exception as e:
            return TableCheckResult(
                database=database, table=table, method=CheckMethod.SAMPLE,
                status=CheckStatus.ERROR, error=str(e)
            )

    def _get_primary_key_columns(self, database: str, table: str) -> List[str]:
        try:
            results = self.master_conn.execute_query(
                "SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY' "
                "ORDER BY ORDINAL_POSITION",
                (database, table)
            )
            return [str(r['COLUMN_NAME']) for r in results]
        except Exception:
            return []

    def _row_hash(self, row: Dict[str, Any]) -> str:
        sorted_items = sorted(row.items(), key=lambda x: x[0])
        serialized = json.dumps(sorted_items, default=str, ensure_ascii=False)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()

    def _generate_recommendations(self, result: ConsistencyCheckResult) -> None:
        if result.gtid_consistent is False:
            result.recommendations.append(
                "GTID集合不一致，可能存在数据丢失，建议使用pt-table-checksum详细检查"
            )

        if result.tables_inconsistent > 0:
            result.recommendations.append(
                f"发现{result.tables_inconsistent}个表数据不一致，建议使用pt-table-sync修复"
            )

        inconsistent_tables = [r for r in result.results if r.status == CheckStatus.INCONSISTENT]
        for t in inconsistent_tables[:5]:
            if t.method == CheckMethod.COUNT and t.master_count != t.slave_count:
                diff = t.master_count - t.slave_count
                direction = "主库多" if diff > 0 else "从库多"
                result.recommendations.append(
                    f"表 {t.database}.{t.table}: 行数差异 {abs(diff)} ({direction})"
                )
            elif t.method == CheckMethod.SAMPLE and t.sample_mismatches > 0:
                result.recommendations.append(
                    f"表 {t.database}.{t.table}: 抽样{t.sample_total}行中{t.sample_mismatches}行不匹配"
                )

        if result.tables_error > 0:
            result.recommendations.append(
                f"{result.tables_error}个表校验出错，建议检查权限或表结构"
            )

    def _generate_summary(self, result: ConsistencyCheckResult) -> str:
        lines = [
            f"校验ID: {result.check_id}",
            f"总表数: {result.tables_checked}",
            f"一致: {result.tables_consistent}",
            f"不一致: {result.tables_inconsistent}",
            f"错误: {result.tables_error}",
            f"跳过: {result.tables_skipped}",
            f"耗时: {result.total_duration_ms:.0f}ms",
        ]
        if result.gtid_consistent is not None:
            lines.append(f"GTID一致性: {'是' if result.gtid_consistent else '否'}")
        return "\n".join(lines)

    def get_check_report(self, result: ConsistencyCheckResult) -> Dict[str, Any]:
        inconsistent = [r for r in result.results if r.status == CheckStatus.INCONSISTENT]

        return {
            "check_id": result.check_id,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "total_duration_ms": result.total_duration_ms,
            "tables_checked": result.tables_checked,
            "tables_consistent": result.tables_consistent,
            "tables_inconsistent": result.tables_inconsistent,
            "tables_error": result.tables_error,
            "tables_skipped": result.tables_skipped,
            "gtid_consistent": result.gtid_consistent,
            "consistency_rate": result.tables_consistent / max(result.tables_checked, 1) * 100,
            "inconsistent_tables": [
                {
                    "database": r.database,
                    "table": r.table,
                    "method": r.method.value,
                    "master_count": r.master_count,
                    "slave_count": r.slave_count,
                    "sample_mismatches": r.sample_mismatches,
                    "sample_total": r.sample_total,
                    "details": r.details
                }
                for r in inconsistent
            ],
            "recommendations": result.recommendations,
            "summary": result.summary
        }
