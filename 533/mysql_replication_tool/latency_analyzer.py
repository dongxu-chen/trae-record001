import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .mysql_connection import MySQLConnection
from .monitor import ReplicationMetrics

logger = logging.getLogger(__name__)


class LatencyCause(Enum):
    NETWORK = "network"
    LARGE_TRANSACTION = "large_transaction"
    SLAVE_LOAD = "slave_load"
    LOCK_WAIT = "lock_wait"
    BINLOG_FORMAT = "binlog_format"
    PARALLEL_CONFIG = "parallel_config"
    HARDWARE = "hardware"
    UNKNOWN = "unknown"


@dataclass
class LatencyAnalysis:
    timestamp: float
    primary_cause: LatencyCause
    confidence: float
    causes: Dict[LatencyCause, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class LatencyAnalyzer:
    def __init__(self, master_conn: MySQLConnection, slave_conn: MySQLConnection, config: Dict[str, Any]):
        self.master_conn = master_conn
        self.slave_conn = slave_conn
        self.config = config
        self.network_latency_threshold = config.get('monitoring', {}).get('network_latency_threshold_ms', 100)
        self.cpu_threshold = config.get('monitoring', {}).get('cpu_threshold', 80)
        self.io_threshold = config.get('monitoring', {}).get('io_threshold', 90)

    def analyze(self, metrics: ReplicationMetrics) -> LatencyAnalysis:
        logger.info("开始分析延迟原因...")
        analysis = LatencyAnalysis(
            timestamp=metrics.timestamp.timestamp(),
            primary_cause=LatencyCause.UNKNOWN,
            confidence=0.0
        )

        causes = {}

        network_score = self._analyze_network(metrics, analysis)
        if network_score > 0:
            causes[LatencyCause.NETWORK] = network_score

        load_score = self._analyze_slave_load(metrics, analysis)
        if load_score > 0:
            causes[LatencyCause.SLAVE_LOAD] = load_score

        lock_score = self._analyze_lock_waits(analysis)
        if lock_score > 0:
            causes[LatencyCause.LOCK_WAIT] = lock_score

        binlog_score = self._analyze_binlog_config(analysis)
        if binlog_score > 0:
            causes[LatencyCause.BINLOG_FORMAT] = binlog_score

        parallel_score = self._analyze_parallel_config(analysis)
        if parallel_score > 0:
            causes[LatencyCause.PARALLEL_CONFIG] = parallel_score

        analysis.causes = causes

        if causes:
            sorted_causes = sorted(causes.items(), key=lambda x: x[1], reverse=True)
            analysis.primary_cause = sorted_causes[0][0]
            total_score = sum(causes.values())
            analysis.confidence = sorted_causes[0][1] / total_score if total_score > 0 else 0.0

        logger.info(f"延迟分析完成: 主要原因={analysis.primary_cause.value}, 置信度={analysis.confidence:.2f}")
        return analysis

    def _analyze_network(self, metrics: ReplicationMetrics, analysis: LatencyAnalysis) -> float:
        score = 0.0
        details = {}

        if metrics.network_latency_ms > self.network_latency_threshold:
            score += 0.4
            details["network_latency"] = f"{metrics.network_latency_ms:.2f}ms"
            analysis.recommendations.append(
                f"网络延迟较高 ({metrics.network_latency_ms:.2f}ms), 建议检查网络连接或优化网络配置"
            )

        if metrics.master_log_file != metrics.relay_master_log_file:
            score += 0.3
            details["log_file_mismatch"] = True
            analysis.recommendations.append("IO线程读取落后，可能存在网络传输问题")

        pos_diff = metrics.read_master_log_pos - metrics.exec_master_log_pos
        if pos_diff > 100000000:
            score += 0.3
            details["position_diff"] = pos_diff
            analysis.recommendations.append(f"执行位置落后较多 ({pos_diff} bytes), 网络传输可能存在瓶颈")

        analysis.details["network"] = details
        return score

    def _analyze_slave_load(self, metrics: ReplicationMetrics, analysis: LatencyAnalysis) -> float:
        score = 0.0
        details = {}

        slave_status = self.slave_conn.get_global_status()
        slave_variables = self.slave_conn.get_global_variables()

        threads_running = int(slave_status.get('threads_running', 0) or 0)
        threads_connected = int(slave_status.get('threads_connected', 0) or 0)

        if threads_running > 50:
            score += 0.3
            details["threads_running"] = threads_running
            analysis.recommendations.append(f"从库活跃线程数较高 ({threads_running}), 可能存在负载压力")

        cpu_time = int(slave_status.get('cpu_user', 0) or 0) + int(slave_status.get('cpu_system', 0) or 0)
        uptime = int(slave_status.get('uptime', 1) or 1)
        cpu_usage_percent = min((cpu_time / uptime) * 100, 100) if uptime > 0 else 0

        if cpu_usage_percent > self.cpu_threshold:
            score += 0.35
            details["cpu_usage"] = f"{cpu_usage_percent:.1f}%"
            analysis.recommendations.append(f"从库CPU使用率较高 ({cpu_usage_percent:.1f}%), 建议优化查询或升级硬件")

        innodb_buffer_hit_rate = self._calculate_buffer_hit_rate(slave_status)
        if innodb_buffer_hit_rate < 95:
            score += 0.25
            details["buffer_hit_rate"] = f"{innodb_buffer_hit_rate:.2f}%"
            analysis.recommendations.append(
                f"InnoDB缓冲池命中率较低 ({innodb_buffer_hit_rate:.2f}%), 建议增加innodb_buffer_pool_size"
            )

        slow_queries = int(slave_status.get('slow_queries', 0) or 0)
        if slow_queries > 100:
            score += 0.1
            details["slow_queries"] = slow_queries
            analysis.recommendations.append(f"慢查询较多 ({slow_queries}), 建议优化慢查询")

        analysis.details["slave_load"] = details
        return score

    def _calculate_buffer_hit_rate(self, status: Dict[str, Any]) -> float:
        try:
            reads = int(status.get('innodb_buffer_pool_reads', 0) or 0)
            requests = int(status.get('innodb_buffer_pool_read_requests', 0) or 0)
            if requests > 0:
                return (1 - reads / requests) * 100
            return 100.0
        except Exception:
            return 100.0

    def _analyze_lock_waits(self, analysis: LatencyAnalysis) -> float:
        score = 0.0
        details = {}

        try:
            innodb_status = self.slave_conn.get_innodb_status()

            if "LOCK WAIT" in innodb_status:
                score += 0.5
                details["lock_waits_detected"] = True
                analysis.recommendations.append("检测到锁等待，建议检查长时间运行的事务")

            slave_status = self.slave_conn.get_global_status()
            innodb_row_lock_waits = int(slave_status.get('innodb_row_lock_waits', 0) or 0)
            innodb_row_lock_time_avg = int(slave_status.get('innodb_row_lock_time_avg', 0) or 0)

            if innodb_row_lock_waits > 100:
                score += 0.3
                details["row_lock_waits"] = innodb_row_lock_waits
                analysis.recommendations.append(f"行锁等待较多 ({innodb_row_lock_waits}次), 可能存在锁竞争")

            if innodb_row_lock_time_avg > 100:
                score += 0.2
                details["avg_lock_time"] = f"{innodb_row_lock_time_avg}ms"
                analysis.recommendations.append(f"平均行锁等待时间较长 ({innodb_row_lock_time_avg}ms)")

            processlist = self.slave_conn.get_processlist()
            long_running = [p for p in processlist if p.get('Time', 0) and int(p['Time']) > 30 and p.get('Command') == 'Query']
            if long_running:
                score += 0.3
                details["long_running_queries"] = len(long_running)
                analysis.recommendations.append(f"检测到{len(long_running)}个长时间运行的查询(>30秒)")

        except Exception as e:
            logger.warning(f"分析锁等待时出错: {str(e)}")

        analysis.details["lock_waits"] = details
        return score

    def _analyze_binlog_format(self, analysis: LatencyAnalysis) -> float:
        score = 0.0
        details = {}

        master_variables = self.master_conn.get_global_variables()
        slave_variables = self.slave_conn.get_global_variables()

        binlog_format = master_variables.get('binlog_format', 'STATEMENT')
        binlog_row_image = master_variables.get('binlog_row_image', 'FULL')

        if binlog_format == 'STATEMENT':
            score += 0.4
            details["binlog_format"] = 'STATEMENT'
            analysis.recommendations.append("建议将binlog_format从STATEMENT改为ROW以支持并行复制")

        if binlog_format == 'ROW' and binlog_row_image != 'MINIMAL':
            score += 0.1
            details["binlog_row_image"] = binlog_row_image
            analysis.recommendations.append("建议将binlog_row_image设置为MINIMAL以减少binlog大小")

        slave_parallel_type = slave_variables.get('slave_parallel_type', 'DATABASE')
        if slave_parallel_type == 'DATABASE':
            score += 0.2
            details["slave_parallel_type"] = 'DATABASE'
            analysis.recommendations.append("建议将slave_parallel_type设置为LOGICAL_CLOCK以启用更好的并行复制")

        analysis.details["binlog_config"] = details
        return score

    def _analyze_parallel_config(self, analysis: LatencyAnalysis) -> float:
        score = 0.0
        details = {}

        slave_variables = self.slave_conn.get_global_variables()

        slave_parallel_workers = int(slave_variables.get('slave_parallel_workers', 0) or 0)
        if slave_parallel_workers == 0:
            score += 0.5
            details["slave_parallel_workers"] = 0
            analysis.recommendations.append("并行复制未启用，建议设置slave_parallel_workers > 0")

        slave_preserve_commit_order = slave_variables.get('slave_preserve_commit_order', 'OFF')
        if slave_preserve_commit_order == 'OFF' and slave_parallel_workers > 0:
            score += 0.1
            details["slave_preserve_commit_order"] = 'OFF'
            analysis.recommendations.append("建议启用slave_preserve_commit_order保证事务顺序")

        slave_parallel_max_queued = int(slave_variables.get('slave_parallel_max_queued', 0) or 0)
        if slave_parallel_workers > 0 and slave_parallel_max_queued < 100000:
            score += 0.1
            analysis.recommendations.append("建议增加slave_parallel_max_queued提高并行复制吞吐量")

        analysis.details["parallel_config"] = details
        return score

    def get_detailed_diagnosis(self, analysis: LatencyAnalysis) -> Dict[str, Any]:
        return {
            "timestamp": analysis.timestamp,
            "primary_cause": analysis.primary_cause.value,
            "confidence": analysis.confidence,
            "all_causes": {k.value: v for k, v in analysis.causes.items()},
            "recommendations": analysis.recommendations,
            "details": analysis.details
        }
