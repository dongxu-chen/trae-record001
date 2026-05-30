import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


class FailoverStep(Enum):
    PRE_CHECK = "pre_check"
    STOP_SLAVE = "stop_slave"
    WAIT_DRAIN = "wait_drain"
    PROMOTE_SLAVE = "promote_slave"
    UPDATE_ROUTING = "update_routing"
    VERIFY_NEW_MASTER = "verify_new_master"
    REBUILD_REPLICATION = "rebuild_replication"
    VERIFY_REPLICATION = "verify_replication"
    CLEANUP = "cleanup"


class DrillStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DrillStepResult:
    step: FailoverStep
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class DrillResult:
    drill_id: str
    status: DrillStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    steps: List[DrillStepResult] = field(default_factory=list)
    original_master: Dict[str, Any] = field(default_factory=dict)
    original_slave: Dict[str, Any] = field(default_factory=dict)
    can_rollback: bool = True
    summary: str = ""


@dataclass
class PreCheckResult:
    passed: bool
    checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class FailoverDrill:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection,
                 config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.dry_run = config.get('failover', {}).get('dry_run', True)
        self.drain_timeout = config.get('failover', {}).get('drain_timeout', 30)
        self.verify_timeout = config.get('failover', {}).get('verify_timeout', 60)
        self.drain_check_interval = config.get('failover', {}).get('drain_check_interval', 1)

    def run_drill(self) -> DrillResult:
        drill_id = f"drill_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = DrillResult(
            drill_id=drill_id,
            status=DrillStatus.RUNNING,
            start_time=datetime.now()
        )

        logger.info(f"开始切换演练: {drill_id}, 模式: {'DRY-RUN' if self.dry_run else 'LIVE'}")

        self._save_original_state(result)

        steps = [
            (FailoverStep.PRE_CHECK, self._step_pre_check),
            (FailoverStep.STOP_SLAVE, self._step_stop_slave),
            (FailoverStep.WAIT_DRAIN, self._step_wait_drain),
            (FailoverStep.PROMOTE_SLAVE, self._step_promote_slave),
            (FailoverStep.VERIFY_NEW_MASTER, self._step_verify_new_master),
            (FailoverStep.REBUILD_REPLICATION, self._step_rebuild_replication),
            (FailoverStep.VERIFY_REPLICATION, self._step_verify_replication),
            (FailoverStep.CLEANUP, self._step_cleanup),
        ]

        for step_enum, step_fn in steps:
            step_result = DrillStepResult(
                step=step_enum,
                status="running",
                start_time=datetime.now()
            )

            try:
                step_fn(result, step_result)
                step_result.status = "success"
            except Exception as e:
                step_result.status = "failed"
                step_result.error = str(e)
                logger.error(f"演练步骤 {step_enum.value} 失败: {str(e)}")

                result.status = DrillStatus.FAILED
                result.steps.append(step_result)

                self._rollback(result)
                break

            step_result.end_time = datetime.now()
            step_result.duration_ms = (step_result.end_time - step_result.start_time).total_seconds() * 1000
            result.steps.append(step_result)

            logger.info(f"步骤 {step_enum.value} 完成, 耗时: {step_result.duration_ms:.0f}ms")

        if result.status == DrillStatus.RUNNING:
            result.status = DrillStatus.SUCCESS

        result.end_time = datetime.now()
        result.total_duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
        result.summary = self._generate_summary(result)

        logger.info(f"切换演练完成: {drill_id}, 状态: {result.status.value}, 耗时: {result.total_duration_ms:.0f}ms")
        return result

    def _save_original_state(self, result: DrillResult) -> None:
        try:
            master_status = self.master_conn.get_master_status()
            slave_status = self.slave_conn.get_slave_status()
            master_vars = self.master_conn.get_global_variables()
            slave_vars = self.slave_conn.get_global_variables()

            result.original_master = {
                "host": self.master_conn.host,
                "port": self.master_conn.port,
                "log_file": master_status.get('file', ''),
                "log_pos": master_status.get('position', 0),
                "gtid_executed": master_vars.get('gtid_executed', ''),
                "read_only": master_vars.get('read_only', 'OFF')
            }
            result.original_slave = {
                "host": self.slave_conn.host,
                "port": self.slave_conn.port,
                "log_file": slave_status.get('relay_master_log_file', ''),
                "log_pos": slave_status.get('exec_master_log_pos', 0),
                "gtid_executed": slave_vars.get('gtid_executed', ''),
                "read_only": slave_vars.get('read_only', 'OFF'),
                "seconds_behind": slave_status.get('seconds_behind_master', 0)
            }
        except Exception as e:
            logger.warning(f"保存原始状态失败: {str(e)}")

    def _step_pre_check(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("执行预检查...")
        check_result = self._run_pre_checks()
        step_result.details = {
            "checks": check_result.checks,
            "all_passed": check_result.passed
        }

        if not check_result.passed:
            failed_checks = [k for k, v in check_result.checks.items() if not v.get('passed', False)]
            raise RuntimeError(f"预检查未通过: {', '.join(failed_checks)}")

        logger.info("预检查全部通过")

    def _run_pre_checks(self) -> PreCheckResult:
        checks = {}

        slave_status = self.slave_conn.get_slave_status()
        io_running = slave_status.get('slave_io_running') == 'Yes'
        sql_running = slave_status.get('slave_sql_running') == 'Yes'
        checks["replication_running"] = {
            "passed": io_running and sql_running,
            "message": f"IO: {io_running}, SQL: {sql_running}"
        }

        seconds_behind = float(slave_status.get('seconds_behind_master', -1) or -1)
        checks["no_significant_lag"] = {
            "passed": 0 <= seconds_behind <= 5,
            "message": f"延迟: {seconds_behind}秒"
        }

        slave_vars = self.slave_conn.get_global_variables()
        gtid_mode = slave_vars.get('gtid_mode', 'OFF')
        checks["gtid_enabled"] = {
            "passed": gtid_mode == 'ON',
            "message": f"GTID模式: {gtid_mode}"
        }

        binlog_format = slave_vars.get('binlog_format', 'STATEMENT')
        checks["binlog_format_row"] = {
            "passed": binlog_format == 'ROW',
            "message": f"Binlog格式: {binlog_format}"
        }

        log_bin = slave_vars.get('log_bin', 'OFF')
        checks["slave_log_bin"] = {
            "passed": log_bin == 'ON',
            "message": f"从库log_bin: {log_bin}"
        }

        slave_global_status = self.slave_conn.get_global_status()
        threads_running = int(slave_global_status.get('threads_running', 0) or 0)
        checks["slave_not_overloaded"] = {
            "passed": threads_running < 100,
            "message": f"从库活跃线程: {threads_running}"
        }

        try:
            processlist = self.master_conn.get_processlist()
            long_queries = [p for p in processlist if p.get('Time', 0) and int(p['Time']) > 10]
            checks["no_long_queries_on_master"] = {
                "passed": len(long_queries) == 0,
                "message": f"主库长查询: {len(long_queries)}"
            }
        except Exception:
            checks["no_long_queries_on_master"] = {"passed": True, "message": "无法检查"}

        all_passed = all(v.get('passed', False) for v in checks.values())
        return PreCheckResult(passed=all_passed, checks=checks)

    def _step_stop_slave(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("停止从库复制IO线程...")

        if self.dry_run:
            logger.info("[DRY-RUN] 跳过实际执行 STOP SLAVE IO_THREAD")
            step_result.details = {"dry_run": True, "action": "STOP SLAVE IO_THREAD"}
            return

        self.slave_conn.execute_update("STOP SLAVE IO_THREAD")
        time.sleep(1)

        slave_status = self.slave_conn.get_slave_status()
        step_result.details = {
            "io_running": slave_status.get('slave_io_running'),
            "sql_running": slave_status.get('slave_sql_running')
        }

    def _step_wait_drain(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("等待从库回放完成...")

        start = time.time()
        elapsed = 0
        last_behind = -1

        while elapsed < self.drain_timeout:
            slave_status = self.slave_conn.get_slave_status()
            seconds_behind = float(slave_status.get('seconds_behind_master', -1) or -1)
            last_behind = seconds_behind

            if seconds_behind == 0:
                logger.info("从库回放完成，延迟为0")
                break

            time.sleep(self.drain_check_interval)
            elapsed = time.time() - start

        step_result.details = {
            "wait_time_sec": round(elapsed, 2),
            "final_seconds_behind": last_behind,
            "drain_timeout": self.drain_timeout,
            "drained": last_behind == 0
        }

        if last_behind > 0 and not self.dry_run:
            logger.warning(f"回放未完成，剩余延迟: {last_behind}秒")

    def _step_promote_slave(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("提升从库为新主库...")

        if self.dry_run:
            logger.info("[DRY-RUN] 跳过实际提升从库")
            step_result.details = {
                "dry_run": True,
                "action": "STOP SLAVE; SET GLOBAL read_only=OFF; SET GLOBAL super_read_only=OFF"
            }
            return

        self.slave_conn.execute_update("STOP SLAVE")
        self.slave_conn.execute_update("SET GLOBAL read_only = OFF")
        self.slave_conn.execute_update("SET GLOBAL super_read_only = OFF")

        new_master_status = self.slave_conn.get_master_status()
        step_result.details = {
            "new_master_log_file": new_master_status.get('file', ''),
            "new_master_log_pos": new_master_status.get('position', 0),
            "read_only": "OFF"
        }

    def _step_verify_new_master(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("验证新主库可用性...")

        ok, latency = self.slave_conn.ping()
        step_result.details = {
            "ping_ok": ok,
            "latency_ms": latency if ok else -1
        }

        if not ok and not self.dry_run:
            raise RuntimeError("新主库不可达")

        try:
            slave_vars = self.slave_conn.get_global_variables()
            read_only = slave_vars.get('read_only', 'ON')
            step_result.details["read_only"] = read_only

            if read_only == 'ON' and not self.dry_run:
                raise RuntimeError("新主库仍处于只读状态")
        except Exception as e:
            if not self.dry_run:
                raise

        logger.info("新主库验证通过")

    def _step_rebuild_replication(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("重建复制关系（原主库指向新主库）...")

        if self.dry_run:
            new_master_status = self.slave_conn.get_master_status()
            step_result.details = {
                "dry_run": True,
                "action": "CHANGE MASTER TO new_master",
                "new_master_host": self.slave_conn.host,
                "new_master_port": self.slave_conn.port,
                "new_master_log_file": new_master_status.get('file', ''),
                "new_master_log_pos": new_master_status.get('position', 0)
            }
            return

        new_master_status = self.slave_conn.get_master_status()
        new_log_file = new_master_status.get('file', '')
        new_log_pos = new_master_status.get('position', 0)

        self.master_conn.execute_update("SET GLOBAL read_only = ON")
        self.master_conn.execute_update("SET GLOBAL super_read_only = ON")

        change_master_sql = (
            f"CHANGE MASTER TO "
            f"MASTER_HOST='{self.slave_conn.host}', "
            f"MASTER_PORT={self.slave_conn.port}, "
            f"MASTER_USER='{self.master_conn.user}', "
            f"MASTER_PASSWORD='{self.master_conn.password}', "
            f"MASTER_LOG_FILE='{new_log_file}', "
            f"MASTER_LOG_POS={new_log_pos}"
        )
        self.master_conn.execute_update(change_master_sql)
        self.master_conn.execute_update("START SLAVE")

        step_result.details = {
            "new_master_host": self.slave_conn.host,
            "new_master_port": self.slave_conn.port,
            "new_master_log_file": new_log_file,
            "new_master_log_pos": new_log_pos
        }

    def _step_verify_replication(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("验证新复制关系...")

        if self.dry_run:
            step_result.details = {"dry_run": True, "action": "SHOW SLAVE STATUS"}
            return

        start = time.time()
        while (time.time() - start) < self.verify_timeout:
            slave_status = self.master_conn.get_slave_status()
            io_running = slave_status.get('slave_io_running') == 'Yes'
            sql_running = slave_status.get('slave_sql_running') == 'Yes'

            if io_running and sql_running:
                step_result.details = {
                    "io_running": True,
                    "sql_running": True,
                    "seconds_behind": slave_status.get('seconds_behind_master', 0)
                }
                logger.info("新复制关系验证通过")
                return

            time.sleep(2)

        raise RuntimeError("新复制关系验证超时")

    def _step_cleanup(self, result: DrillResult, step_result: DrillStepResult) -> None:
        logger.info("执行清理...")

        if self.dry_run:
            step_result.details = {"dry_run": True, "action": "rollback to original state"}
            return

        if result.status == DrillStatus.SUCCESS:
            step_result.details = {"action": "no_cleanup_needed", "status": "success"}
            return

        self._rollback(result)
        step_result.details = {"action": "rollback_executed"}

    def _rollback(self, result: DrillResult) -> None:
        logger.warning("执行回滚操作...")

        if self.dry_run:
            logger.info("[DRY-RUN] 跳过实际回滚")
            result.status = DrillStatus.ROLLED_BACK
            return

        try:
            slave_vars = self.slave_conn.get_global_variables()
            if slave_vars.get('read_only') == 'OFF':
                original_readonly = result.original_slave.get('read_only', 'ON')
                if original_readonly == 'ON':
                    self.slave_conn.execute_update("SET GLOBAL read_only = ON")
                    self.slave_conn.execute_update("SET GLOBAL super_read_only = ON")

            slave_status = self.slave_conn.get_slave_status()
            if not (slave_status.get('slave_io_running') == 'Yes' and
                    slave_status.get('slave_sql_running') == 'Yes'):
                self.slave_conn.execute_update("START SLAVE")

            result.status = DrillStatus.ROLLED_BACK
            logger.info("回滚完成")
        except Exception as e:
            logger.error(f"回滚失败: {str(e)}")
            result.can_rollback = False

    def _generate_summary(self, result: DrillResult) -> str:
        success_steps = sum(1 for s in result.steps if s.status == "success")
        total_steps = len(result.steps)
        failed_step = next((s for s in result.steps if s.status == "failed"), None)

        lines = [
            f"演练ID: {result.drill_id}",
            f"状态: {result.status.value}",
            f"总耗时: {result.total_duration_ms:.0f}ms",
            f"步骤: {success_steps}/{total_steps} 成功",
        ]

        if failed_step:
            lines.append(f"失败步骤: {failed_step.step.value} - {failed_step.error}")
        else:
            lines.append("所有步骤执行成功")

        slowest = max(result.steps, key=lambda s: s.duration_ms) if result.steps else None
        if slowest:
            lines.append(f"最慢步骤: {slowest.step.value} ({slowest.duration_ms:.0f}ms)")

        return "\n".join(lines)

    def get_drill_report(self, result: DrillResult) -> Dict[str, Any]:
        return {
            "drill_id": result.drill_id,
            "status": result.status.value,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "total_duration_ms": result.total_duration_ms,
            "dry_run": self.dry_run,
            "steps": [
                {
                    "step": s.step.value,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "details": s.details,
                    "error": s.error
                }
                for s in result.steps
            ],
            "original_master": result.original_master,
            "original_slave": result.original_slave,
            "can_rollback": result.can_rollback,
            "summary": result.summary
        }
