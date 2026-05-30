import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


class ReplayType(Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    BATCH_INSERT = "BATCH_INSERT"
    BATCH_UPDATE = "BATCH_UPDATE"


@dataclass
class ReplayStatement:
    sql: str
    replay_type: ReplayType
    estimated_rows: int
    estimated_bytes: int
    target_table: str
    timestamp: Optional[datetime] = None


@dataclass
class ReplayResult:
    statement_index: int
    sql: str
    replay_type: str
    execution_time_ms: float
    rows_affected: int
    slave_delay_before: float
    slave_delay_after: float
    delay_increase: float
    binlog_bytes_generated: int
    success: bool
    error: Optional[str] = None


@dataclass
class ReplayAnalysisResult:
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    total_statements: int = 0
    successful_statements: int = 0
    failed_statements: int = 0
    max_delay_increase: float = 0.0
    avg_delay_increase: float = 0.0
    total_rows_affected: int = 0
    total_estimated_bytes: int = 0
    results: List[ReplayResult] = field(default_factory=list)
    delay_impact_curve: List[Tuple[int, float]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    bottleneck_analysis: Dict[str, Any] = field(default_factory=dict)


class ReplayAnalyzer:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection,
                 config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.max_allowed_delay = config.get('replay', {}).get('max_allowed_delay', 60)
        self.statement_delay_threshold = config.get('replay', {}).get('statement_delay_threshold', 10)
        self.collect_binlog_stats = config.get('replay', {}).get('collect_binlog_stats', True)

    def analyze_from_slow_log(self, limit: int = 50) -> List[ReplayStatement]:
        logger.info(f"从慢查询日志提取大事务, 限制{limit}条...")
        statements = []

        try:
            results = self.master_conn.execute_query("""
                SELECT
                    START_TIME,
                    SQL_TEXT,
                    QUERY_TIME,
                    ROWS_EXAMINED,
                    ROWS_AFFECTED
                FROM mysql.slow_log
                WHERE SQL_TEXT LIKE 'INSERT%' OR SQL_TEXT LIKE 'UPDATE%' OR SQL_TEXT LIKE 'DELETE%'
                ORDER BY QUERY_TIME DESC
                LIMIT %s
            """, (limit,))

            for row in results:
                sql_text = str(row.get('SQL_TEXT', ''))
                rows_affected = int(row.get('ROWS_AFFECTED', 0) or 0)
                rows_examined = int(row.get('ROWS_EXAMINED', 0) or 0)

                replay_type = self._classify_sql(sql_text)
                target_table = self._extract_table(sql_text)
                estimated_bytes = max(rows_affected, rows_examined) * 500

                statements.append(ReplayStatement(
                    sql=sql_text[:2000],
                    replay_type=replay_type,
                    estimated_rows=max(rows_affected, rows_examined),
                    estimated_bytes=estimated_bytes,
                    target_table=target_table,
                    timestamp=row.get('START_TIME')
                ))

        except Exception as e:
            logger.warning(f"从慢查询日志提取失败: {str(e)}")

        if not statements:
            statements = self._generate_simulated_statements()

        logger.info(f"提取到{len(statements)}条回放语句")
        return statements

    def analyze_from_binlog(self, limit: int = 20) -> List[ReplayStatement]:
        logger.info("从binlog提取大事务...")
        statements = []

        try:
            master_status = self.master_conn.get_master_status()
            if not master_status:
                return self._generate_simulated_statements()

            results = self.master_conn.execute_query(
                "SHOW BINLOG EVENTS IN %s LIMIT %s",
                (master_status.get('file', ''), limit)
            )

            for row in results:
                event_type = str(row.get('Event_type', ''))
                info = str(row.get('Info', ''))

                if event_type in ('Query', 'Write_rows', 'Update_rows', 'Delete_rows'):
                    replay_type = self._classify_event(event_type)
                    statements.append(ReplayStatement(
                        sql=info[:2000],
                        replay_type=replay_type,
                        estimated_rows=1000,
                        estimated_bytes=500000,
                        target_table=self._extract_table(info)
                    ))

        except Exception as e:
            logger.warning(f"从binlog提取失败: {str(e)}，使用模拟语句")
            statements = self._generate_simulated_statements()

        return statements

    def _generate_simulated_statements(self) -> List[ReplayStatement]:
        logger.info("生成模拟大事务语句...")
        simulated = [
            ReplayStatement(
                sql="INSERT INTO replay_test (data) SELECT REPEAT('x', 1000) FROM information_schema.columns A, information_schema.columns B LIMIT 50000",
                replay_type=ReplayType.BATCH_INSERT,
                estimated_rows=50000,
                estimated_bytes=50000 * 1000,
                target_table="replay_test"
            ),
            ReplayStatement(
                sql="UPDATE replay_test SET data = REPEAT('y', 1000) WHERE id BETWEEN 1 AND 20000",
                replay_type=ReplayType.BATCH_UPDATE,
                estimated_rows=20000,
                estimated_bytes=20000 * 2000,
                target_table="replay_test"
            ),
            ReplayStatement(
                sql="DELETE FROM replay_test WHERE id BETWEEN 40000 AND 50000",
                replay_type=ReplayType.DELETE,
                estimated_rows=10000,
                estimated_bytes=10000 * 100,
                target_table="replay_test"
            ),
        ]
        return simulated

    def replay_statements(self, statements: List[ReplayStatement],
                          dry_run: bool = True) -> ReplayAnalysisResult:
        result = ReplayAnalysisResult(start_time=datetime.now())

        logger.info(f"开始回放分析, 共{len(statements)}条语句, 模式: {'DRY-RUN' if dry_run else 'LIVE'}")

        if not dry_run:
            self._prepare_replay_table()

        for i, stmt in enumerate(statements):
            replay_result = self._execute_replay_statement(i, stmt, dry_run)
            result.results.append(replay_result)

            if replay_result.success:
                result.successful_statements += 1
                result.total_rows_affected += replay_result.rows_affected
            else:
                result.failed_statements += 1

            result.delay_impact_curve.append((i, replay_result.delay_increase))

            if replay_result.delay_increase > result.max_delay_increase:
                result.max_delay_increase = replay_result.delay_increase

            if replay_result.delay_increase > self.max_allowed_delay and not dry_run:
                logger.warning(f"延迟增长超过阈值({self.max_allowed_delay}秒), 中止回放")
                break

            time.sleep(0.5)

        result.total_statements = len(statements)

        if result.results:
            result.avg_delay_increase = sum(r.delay_increase for r in result.results) / len(result.results)
            result.total_estimated_bytes = sum(
                s.estimated_bytes for s in statements[:len(result.results)]
            )

        self._analyze_bottleneck(result)
        self._generate_recommendations(result)

        result.end_time = datetime.now()
        result.total_duration_ms = (result.end_time - result.start_time).total_seconds() * 1000

        logger.info(f"回放分析完成: {result.successful_statements}/{result.total_statements} 成功, "
                   f"最大延迟增长: {result.max_delay_increase:.2f}秒")

        if not dry_run:
            self._cleanup_replay_table()

        return result

    def _execute_replay_statement(self, index: int, stmt: ReplayStatement,
                                   dry_run: bool) -> ReplayResult:
        delay_before = self._get_slave_delay()

        if dry_run:
            estimated_time = stmt.estimated_rows * 0.01
            estimated_delay = stmt.estimated_rows * 0.001 + stmt.estimated_bytes / (1024 * 1024 * 10)

            return ReplayResult(
                statement_index=index,
                sql=stmt.sql[:200],
                replay_type=stmt.replay_type.value,
                execution_time_ms=estimated_time * 1000,
                rows_affected=stmt.estimated_rows,
                slave_delay_before=delay_before,
                slave_delay_after=delay_before + estimated_delay,
                delay_increase=estimated_delay,
                binlog_bytes_generated=stmt.estimated_bytes,
                success=True
            )

        try:
            start_time = time.time()
            affected = self.master_conn.execute_update(stmt.sql)
            execution_ms = (time.time() - start_time) * 1000

            time.sleep(2)
            delay_after = self._get_slave_delay()

            return ReplayResult(
                statement_index=index,
                sql=stmt.sql[:200],
                replay_type=stmt.replay_type.value,
                execution_time_ms=execution_ms,
                rows_affected=affected,
                slave_delay_before=delay_before,
                slave_delay_after=delay_after,
                delay_increase=max(0, delay_after - delay_before),
                binlog_bytes_generated=stmt.estimated_bytes,
                success=True
            )
        except Exception as e:
            delay_after = self._get_slave_delay()
            return ReplayResult(
                statement_index=index,
                sql=stmt.sql[:200],
                replay_type=stmt.replay_type.value,
                execution_time_ms=0,
                rows_affected=0,
                slave_delay_before=delay_before,
                slave_delay_after=delay_after,
                delay_increase=max(0, delay_after - delay_before),
                binlog_bytes_generated=0,
                success=False,
                error=str(e)
            )

    def _get_slave_delay(self) -> float:
        try:
            slave_status = self.slave_conn.get_slave_status()
            return float(slave_status.get('seconds_behind_master', 0) or 0)
        except Exception:
            return 0.0

    def _prepare_replay_table(self) -> None:
        try:
            self.master_conn.execute_update("""
                CREATE TABLE IF NOT EXISTS replay_test (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("回放测试表已创建")
        except Exception as e:
            logger.warning(f"创建回放测试表失败: {str(e)}")

    def _cleanup_replay_table(self) -> None:
        try:
            self.master_conn.execute_update("DROP TABLE IF EXISTS replay_test")
            logger.info("回放测试表已清理")
        except Exception as e:
            logger.warning(f"清理回放测试表失败: {str(e)}")

    def _analyze_bottleneck(self, result: ReplayAnalysisResult) -> None:
        if not result.results:
            return

        by_type = {}
        for r in result.results:
            if r.replay_type not in by_type:
                by_type[r.replay_type] = {"count": 0, "total_delay": 0.0, "total_time": 0.0}
            by_type[r.replay_type]["count"] += 1
            by_type[r.replay_type]["total_delay"] += r.delay_increase
            by_type[r.replay_type]["total_time"] += r.execution_time_ms

        worst_type = max(by_type.items(), key=lambda x: x[1]["total_delay"]) if by_type else None

        result.bottleneck_analysis = {
            "by_type": by_type,
            "worst_type": worst_type[0] if worst_type else None,
            "worst_type_delay": worst_type[1]["total_delay"] if worst_type else 0,
            "peak_delay_statement": max(result.results, key=lambda r: r.delay_increase).statement_index if result.results else None
        }

    def _generate_recommendations(self, result: ReplayAnalysisResult) -> None:
        if result.max_delay_increase > 30:
            result.recommendations.append(
                f"最大延迟增长{result.max_delay_increase:.1f}秒，建议拆分大事务为小批次执行"
            )

        if result.avg_delay_increase > 10:
            result.recommendations.append(
                "平均延迟增长较高，建议在低峰期执行大事务"
            )

        bottleneck = result.bottleneck_analysis
        if bottleneck.get("worst_type"):
            result.recommendations.append(
                f"{bottleneck['worst_type']}类型事务产生最多延迟，优先优化"
            )

        if result.total_estimated_bytes > 100 * 1024 * 1024:
            result.recommendations.append(
                "总数据量超过100MB，建议启用并行复制并设置binlog_row_image=MINIMAL"
            )

    def _classify_sql(self, sql: str) -> ReplayType:
        sql_upper = sql.upper().strip()
        if sql_upper.startswith("INSERT"):
            return ReplayType.BATCH_INSERT if "LIMIT" in sql_upper or "SELECT" in sql_upper else ReplayType.INSERT
        elif sql_upper.startswith("UPDATE"):
            return ReplayType.BATCH_UPDATE if "WHERE" in sql_upper else ReplayType.UPDATE
        elif sql_upper.startswith("DELETE"):
            return ReplayType.DELETE
        return ReplayType.INSERT

    def _classify_event(self, event_type: str) -> ReplayType:
        mapping = {
            'Write_rows': ReplayType.INSERT,
            'Update_rows': ReplayType.UPDATE,
            'Delete_rows': ReplayType.DELETE,
            'Query': ReplayType.BATCH_INSERT
        }
        return mapping.get(event_type, ReplayType.INSERT)

    def _extract_table(self, sql: str) -> str:
        try:
            sql_upper = sql.upper().strip()
            if sql_upper.startswith("INSERT"):
                parts = sql_upper.split("INTO")
                if len(parts) > 1:
                    table = parts[1].strip().split()[0].strip('`').strip("'")
                    return table
            elif sql_upper.startswith("UPDATE"):
                parts = sql_upper.split()
                if len(parts) > 1:
                    return parts[1].strip('`').strip("'")
            elif sql_upper.startswith("DELETE"):
                parts = sql_upper.split("FROM")
                if len(parts) > 1:
                    table = parts[1].strip().split()[0].strip('`').strip("'")
                    return table
        except Exception:
            pass
        return "unknown"

    def get_replay_report(self, result: ReplayAnalysisResult) -> Dict[str, Any]:
        return {
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "total_duration_ms": result.total_duration_ms,
            "total_statements": result.total_statements,
            "successful_statements": result.successful_statements,
            "failed_statements": result.failed_statements,
            "max_delay_increase_sec": result.max_delay_increase,
            "avg_delay_increase_sec": result.avg_delay_increase,
            "total_rows_affected": result.total_rows_affected,
            "total_estimated_bytes": result.total_estimated_bytes,
            "delay_impact_curve": result.delay_impact_curve[:20],
            "bottleneck_analysis": result.bottleneck_analysis,
            "recommendations": result.recommendations,
            "statement_results": [
                {
                    "index": r.statement_index,
                    "type": r.replay_type,
                    "time_ms": r.execution_time_ms,
                    "rows": r.rows_affected,
                    "delay_before": r.slave_delay_before,
                    "delay_after": r.slave_delay_after,
                    "delay_increase": r.delay_increase,
                    "success": r.success,
                    "error": r.error
                }
                for r in result.results
            ]
        }
