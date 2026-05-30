import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .mysql_connection import MySQLConnection

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class SlavePerformance:
    performance_level: PerformanceLevel
    performance_score: float
    cpu_core_count: int
    memory_size_mb: int
    io_capability: str
    buffer_pool_size_mb: int
    buffer_pool_hit_rate: float
    disk_io_utilization: float


@dataclass
class ParallelReplicationConfig:
    current_workers: int
    recommended_workers: int
    current_type: str
    recommended_type: str
    current_preserve_commit_order: bool
    recommended_preserve_commit_order: bool
    current_max_queued: int
    recommended_max_queued: int
    slave_performance: SlavePerformance
    configuration_changes: List[Dict[str, Any]] = field(default_factory=list)
    expected_improvement: float = 0.0


class ParallelReplicationOptimizer:
    def __init__(self, slave_conn: MySQLConnection, config: Dict[str, Any]):
        self.slave_conn = slave_conn
        self.config = config
        self.max_workers = config.get('parallel_replication', {}).get('max_workers', 32)
        self.min_workers = 4
        self.cpu_core_count = self._detect_cpu_cores()

    def _detect_cpu_cores(self) -> int:
        try:
            variables = self.slave_conn.get_global_variables()
            cpu_count = int(variables.get('innodb_read_io_threads', 4) or 4)
            return max(cpu_count, 4)
        except Exception as e:
            logger.warning(f"检测CPU核心数失败: {str(e)}，使用默认值4")
            return 4

    def _evaluate_slave_performance(self) -> SlavePerformance:
        slave_status = self.slave_conn.get_global_status()
        slave_variables = self.slave_conn.get_global_variables()

        cpu_cores = self.cpu_core_count
        score = 0.0

        buffer_pool_size = int(slave_variables.get('innodb_buffer_pool_size', 0) or 0)
        buffer_pool_size_mb = buffer_pool_size // (1024 * 1024)

        buffer_hit_rate = self._calculate_buffer_hit_rate(slave_status)

        cpu_user = int(slave_status.get('cpu_user', 0) or 0)
        cpu_system = int(slave_status.get('cpu_system', 0) or 0)
        uptime = int(slave_status.get('uptime', 1) or 1)
        cpu_usage = min((cpu_user + cpu_system) / uptime * 100, 100)

        threads_running = int(slave_status.get('threads_running', 0) or 0)

        if cpu_cores >= 32:
            score += 30
        elif cpu_cores >= 16:
            score += 25
        elif cpu_cores >= 8:
            score += 20
        elif cpu_cores >= 4:
            score += 10
        else:
            score += 5

        if buffer_pool_size_mb >= 32768:
            score += 30
        elif buffer_pool_size_mb >= 16384:
            score += 25
        elif buffer_pool_size_mb >= 8192:
            score += 20
        elif buffer_pool_size_mb >= 4096:
            score += 10
        else:
            score += 5

        if buffer_hit_rate >= 99:
            score += 20
        elif buffer_hit_rate >= 95:
            score += 15
        elif buffer_hit_rate >= 90:
            score += 10
        else:
            score += 5

        if cpu_usage < 30:
            score += 20
        elif cpu_usage < 50:
            score += 15
        elif cpu_usage < 70:
            score += 10
        else:
            score += 5

        if threads_running < 10:
            score += 10
        elif threads_running < 30:
            score += 5
        else:
            score += 2

        if score >= 80:
            level = PerformanceLevel.EXTREME
        elif score >= 60:
            level = PerformanceLevel.HIGH
        elif score >= 40:
            level = PerformanceLevel.MEDIUM
        else:
            level = PerformanceLevel.LOW

        return SlavePerformance(
            performance_level=level,
            performance_score=score,
            cpu_core_count=cpu_cores,
            memory_size_mb=buffer_pool_size_mb,
            io_capability="high" if buffer_hit_rate >= 95 else "medium",
            buffer_pool_size_mb=buffer_pool_size_mb,
            buffer_pool_hit_rate=buffer_hit_rate,
            disk_io_utilization=cpu_usage
        )

    def _calculate_buffer_hit_rate(self, status: Dict[str, Any]) -> float:
        try:
            reads = int(status.get('innodb_buffer_pool_reads', 0) or 0)
            requests = int(status.get('innodb_buffer_pool_read_requests', 0) or 0)
            if requests > 0:
                return (1 - reads / requests) * 100
            return 100.0
        except Exception:
            return 100.0

    def analyze_and_recommend(self) -> ParallelReplicationConfig:
        logger.info("开始分析并行复制配置...")

        slave_performance = self._evaluate_slave_performance()

        slave_variables = self.slave_conn.get_global_variables()
        slave_status = self.slave_conn.get_global_status()

        current_workers = int(slave_variables.get('slave_parallel_workers', 0) or 0)
        current_type = slave_variables.get('slave_parallel_type', 'DATABASE')
        current_preserve_commit = slave_variables.get('slave_preserve_commit_order', 'OFF') == 'ON'
        current_max_queued = int(slave_variables.get('slave_parallel_max_queued', 0) or 0)

        recommended_workers = self._calculate_optimal_workers_by_performance(
            slave_status, current_workers, slave_performance
        )
        recommended_type = self._recommend_parallel_type(slave_variables, slave_performance)
        recommended_preserve_commit = self._recommend_preserve_commit_order()
        recommended_max_queued = self._recommend_max_queued(current_max_queued, slave_performance)

        config_changes = self._generate_config_changes(
            current_workers, recommended_workers,
            current_type, recommended_type,
            current_preserve_commit, recommended_preserve_commit,
            current_max_queued, recommended_max_queued,
            slave_performance
        )

        expected_improvement = self._calculate_expected_improvement(slave_status, config_changes, slave_performance)

        result = ParallelReplicationConfig(
            current_workers=current_workers,
            recommended_workers=recommended_workers,
            current_type=current_type,
            recommended_type=recommended_type,
            current_preserve_commit_order=current_preserve_commit,
            recommended_preserve_commit_order=recommended_preserve_commit,
            current_max_queued=current_max_queued,
            recommended_max_queued=recommended_max_queued,
            slave_performance=slave_performance,
            configuration_changes=config_changes,
            expected_improvement=expected_improvement
        )

        logger.info(f"并行复制分析完成，从库性能等级: {slave_performance.performance_level.value}, "
                   f"推荐{recommended_workers}个worker，预期提升{expected_improvement:.1f}%")
        return result

    def _calculate_optimal_workers_by_performance(self, status: Dict[str, Any],
                                                   current_workers: int,
                                                   performance: SlavePerformance) -> int:
        cpu_cores = performance.cpu_core_count
        perf_level = performance.performance_level

        base_workers = {
            PerformanceLevel.EXTREME: min(cpu_cores, self.max_workers),
            PerformanceLevel.HIGH: min(int(cpu_cores * 0.75), self.max_workers),
            PerformanceLevel.MEDIUM: min(int(cpu_cores * 0.5), self.max_workers),
            PerformanceLevel.LOW: min(int(cpu_cores * 0.25), self.min_workers)
        }

        suggested_workers = base_workers.get(perf_level, self.min_workers)

        qps = int(status.get('queries', 0) or 0) / max(int(status.get('uptime', 1) or 1), 1)

        if qps > 2000 and perf_level in [PerformanceLevel.EXTREME, PerformanceLevel.HIGH]:
            suggested_workers = min(suggested_workers + 4, self.max_workers)
        elif qps > 1000:
            suggested_workers = min(suggested_workers + 2, self.max_workers)

        threads_running = int(status.get('threads_running', 0) or 0)
        if threads_running < 10 and perf_level in [PerformanceLevel.EXTREME, PerformanceLevel.HIGH]:
            suggested_workers = min(suggested_workers + 2, self.max_workers)

        return max(suggested_workers, self.min_workers)

    def _recommend_parallel_type(self, variables: Dict[str, Any], performance: SlavePerformance) -> str:
        binlog_format = variables.get('binlog_format', 'STATEMENT')
        gtid_mode = variables.get('gtid_mode', 'OFF')
        perf_level = performance.performance_level

        if binlog_format == 'ROW' and gtid_mode == 'ON':
            return 'LOGICAL_CLOCK'
        elif binlog_format == 'ROW' and perf_level in [PerformanceLevel.HIGH, PerformanceLevel.EXTREME]:
            return 'LOGICAL_CLOCK'
        elif binlog_format == 'ROW':
            return 'LOGICAL_CLOCK'
        else:
            return 'DATABASE'

    def _recommend_preserve_commit_order(self) -> bool:
        return True

    def _recommend_max_queued(self, current: int, performance: SlavePerformance) -> int:
        perf_level = performance.performance_level

        max_queued_by_level = {
            PerformanceLevel.EXTREME: 10000000,
            PerformanceLevel.HIGH: 5000000,
            PerformanceLevel.MEDIUM: 1000000,
            PerformanceLevel.LOW: 100000
        }

        recommended = max_queued_by_level.get(perf_level, 100000)
        return max(current, recommended)

    def _generate_config_changes(self,
                                  current_workers: int,
                                  recommended_workers: int,
                                  current_type: str,
                                  recommended_type: str,
                                  current_preserve_commit: bool,
                                  recommended_preserve_commit: bool,
                                  current_max_queued: int,
                                  recommended_max_queued: int,
                                  performance: SlavePerformance) -> List[Dict[str, Any]]:
        changes = []

        if current_workers != recommended_workers:
            perf_str = f"性能等级{performance.performance_level.value}({performance.performance_score:.0f}分)"
            changes.append({
                'parameter': 'slave_parallel_workers',
                'current_value': current_workers,
                'recommended_value': recommended_workers,
                'sql_command': f"SET GLOBAL slave_parallel_workers = {recommended_workers}",
                'mycnf_setting': f"slave_parallel_workers = {recommended_workers}",
                'reason': f"基于{perf_str}，从{current_workers}调整为{recommended_workers}以优化并行复制性能",
                'impact': 'MEDIUM'
            })

        if current_type != recommended_type:
            changes.append({
                'parameter': 'slave_parallel_type',
                'current_value': current_type,
                'recommended_value': recommended_type,
                'sql_command': f"SET GLOBAL slave_parallel_type = '{recommended_type}'",
                'mycnf_setting': f"slave_parallel_type = {recommended_type}",
                'reason': f"{recommended_type}提供更好的并行复制能力",
                'impact': 'HIGH'
            })

        if current_preserve_commit != recommended_preserve_commit:
            value_str = 'ON' if recommended_preserve_commit else 'OFF'
            changes.append({
                'parameter': 'slave_preserve_commit_order',
                'current_value': 'ON' if current_preserve_commit else 'OFF',
                'recommended_value': value_str,
                'sql_command': f"SET GLOBAL slave_preserve_commit_order = {value_str}",
                'mycnf_setting': f"slave_preserve_commit_order = {value_str}",
                'reason': '保证事务提交顺序与主库一致',
                'impact': 'LOW'
            })

        if current_max_queued != recommended_max_queued:
            changes.append({
                'parameter': 'slave_parallel_max_queued',
                'current_value': current_max_queued,
                'recommended_value': recommended_max_queued,
                'sql_command': f"SET GLOBAL slave_parallel_max_queued = {recommended_max_queued}",
                'mycnf_setting': f"slave_parallel_max_queued = {recommended_max_queued}",
                'reason': '增加队列大小提高并行复制吞吐量',
                'impact': 'LOW'
            })

        return changes

    def _calculate_expected_improvement(self, status: Dict[str, Any], changes: List[Dict[str, Any]],
                                         performance: SlavePerformance) -> float:
        if not changes:
            return 0.0

        improvement = 0.0
        perf_bonus = {
            PerformanceLevel.EXTREME: 1.2,
            PerformanceLevel.HIGH: 1.0,
            PerformanceLevel.MEDIUM: 0.8,
            PerformanceLevel.LOW: 0.5
        }.get(performance.performance_level, 1.0)

        for change in changes:
            if change['parameter'] == 'slave_parallel_workers':
                current = change['current_value']
                recommended = change['recommended_value']
                if current == 0:
                    improvement += 50.0 * perf_bonus
                elif recommended > current:
                    improvement += min((recommended - current) * 5 * perf_bonus, 30)

            elif change['parameter'] == 'slave_parallel_type':
                if change['recommended_value'] == 'LOGICAL_CLOCK':
                    improvement += 25.0 * perf_bonus

        return min(improvement, 90.0)

    def get_best_practices(self) -> List[str]:
        return [
            "确保主库binlog_format设置为ROW",
            "启用GTID模式 (gtid_mode=ON)",
            "设置slave_parallel_type=LOGICAL_CLOCK",
            "根据CPU核心数设置slave_parallel_workers (建议CPU核数的50%-75%)",
            "启用slave_preserve_commit_order=ON保证数据一致性",
            "适当调大slave_parallel_max_queued",
            "设置relay_log_recovery=ON避免中继日志损坏",
            "监控slave_transaction_retries避免事务重试"
        ]

    def generate_apply_commands(self, config: ParallelReplicationConfig) -> Dict[str, List[str]]:
        sql_commands = []
        mycnf_settings = []

        for change in config.configuration_changes:
            sql_commands.append(change['sql_command'])
            mycnf_settings.append(change['mycnf_setting'])

        return {
            'sql_commands': sql_commands,
            'mycnf_settings': mycnf_settings,
            'note': '修改配置后需要重启复制进程: STOP SLAVE; START SLAVE;'
        }
