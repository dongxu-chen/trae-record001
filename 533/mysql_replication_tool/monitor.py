import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


@dataclass
class ReplicationMetrics:
    timestamp: datetime
    seconds_behind_master: float = 0.0
    slave_io_running: bool = False
    slave_sql_running: bool = False
    master_log_file: str = ""
    read_master_log_pos: int = 0
    relay_master_log_file: str = ""
    exec_master_log_pos: int = 0
    network_latency_ms: float = 0.0
    slave_cpu_usage: float = 0.0
    slave_memory_usage: float = 0.0
    slave_io_utilization: float = 0.0
    master_binlog_bytes: int = 0
    relay_log_bytes: int = 0
    transactions_per_second: float = 0.0
    latency_trend: str = "stable"


@dataclass
class Alert:
    timestamp: datetime
    level: str
    type: str
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)


class Monitor:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection, config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.metrics_history: List[ReplicationMetrics] = []
        self.alerts: List[Alert] = []
        self.max_history_points = config.get('prediction', {}).get('history_points', 100)
        self.warning_threshold = config.get('monitoring', {}).get('latency_threshold_warning', 5)
        self.critical_threshold = config.get('monitoring', {}).get('latency_threshold_critical', 30)

    def collect_metrics(self) -> ReplicationMetrics:
        logger.info("开始收集复制监控指标...")
        metrics = ReplicationMetrics(timestamp=datetime.now())

        slave_status = self.slave_conn.get_slave_status()
        if slave_status:
            metrics.seconds_behind_master = float(slave_status.get('seconds_behind_master', 0) or 0)
            metrics.slave_io_running = slave_status.get('slave_io_running') == 'Yes'
            metrics.slave_sql_running = slave_status.get('slave_sql_running') == 'Yes'
            metrics.master_log_file = slave_status.get('master_log_file', '')
            metrics.read_master_log_pos = int(slave_status.get('read_master_log_pos', 0) or 0)
            metrics.relay_master_log_file = slave_status.get('relay_master_log_file', '')
            metrics.exec_master_log_pos = int(slave_status.get('exec_master_log_pos', 0) or 0)

        network_ok, latency = self.slave_conn.ping()
        if network_ok:
            metrics.network_latency_ms = latency

        slave_status_global = self.slave_conn.get_global_status()
        master_status_global = self.master_conn.get_global_status()

        metrics.master_binlog_bytes = int(master_status_global.get('binlog_cache_disk_use', 0) or 0)
        metrics.relay_log_bytes = int(slave_status_global.get('relay_log_space', 0) or 0)

        com_commit = int(slave_status_global.get('com_commit', 0) or 0)
        com_rollback = int(slave_status_global.get('com_rollback', 0) or 0)
        uptime = int(slave_status_global.get('uptime', 1) or 1)
        metrics.transactions_per_second = (com_commit + com_rollback) / uptime

        self._add_metrics(metrics)
        self._check_thresholds(metrics)

        logger.info(f"收集完成，当前延迟: {metrics.seconds_behind_master}秒")
        return metrics

    def _add_metrics(self, metrics: ReplicationMetrics) -> None:
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history_points:
            self.metrics_history.pop(0)

    def _check_thresholds(self, metrics: ReplicationMetrics) -> None:
        if metrics.seconds_behind_master >= self.critical_threshold:
            alert = Alert(
                timestamp=datetime.now(),
                level="CRITICAL",
                type="REPLICATION_LATENCY",
                message=f"复制延迟严重: {metrics.seconds_behind_master}秒",
                metrics={"latency": metrics.seconds_behind_master}
            )
            self.alerts.append(alert)
            logger.critical(alert.message)
        elif metrics.seconds_behind_master >= self.warning_threshold:
            alert = Alert(
                timestamp=datetime.now(),
                level="WARNING",
                type="REPLICATION_LATENCY",
                message=f"复制延迟警告: {metrics.seconds_behind_master}秒",
                metrics={"latency": metrics.seconds_behind_master}
            )
            self.alerts.append(alert)
            logger.warning(alert.message)

        if not metrics.slave_io_running or not metrics.slave_sql_running:
            alert = Alert(
                timestamp=datetime.now(),
                level="CRITICAL",
                type="REPLICATION_STOPPED",
                message=f"复制进程已停止 IO:{metrics.slave_io_running} SQL:{metrics.slave_sql_running}",
                metrics={"io_running": metrics.slave_io_running, "sql_running": metrics.slave_sql_running}
            )
            self.alerts.append(alert)
            logger.critical(alert.message)

    def get_latest_metrics(self) -> Optional[ReplicationMetrics]:
        if self.metrics_history:
            return self.metrics_history[-1]
        return None

    def get_latency_history(self) -> List[float]:
        return [m.seconds_behind_master for m in self.metrics_history]

    def get_alerts(self, level: str = None) -> List[Alert]:
        if level:
            return [a for a in self.alerts if a.level == level]
        return self.alerts

    def clear_alerts(self) -> None:
        self.alerts.clear()

    def get_replication_status_summary(self) -> Dict[str, Any]:
        latest = self.get_latest_metrics()
        if not latest:
            return {"status": "NO_DATA"}

        return {
            "status": "HEALTHY" if latest.seconds_behind_master < self.warning_threshold else 
                      "WARNING" if latest.seconds_behind_master < self.critical_threshold else "CRITICAL",
            "seconds_behind_master": latest.seconds_behind_master,
            "slave_io_running": latest.slave_io_running,
            "slave_sql_running": latest.slave_sql_running,
            "network_latency_ms": latest.network_latency_ms,
            "history_points": len(self.metrics_history)
        }
