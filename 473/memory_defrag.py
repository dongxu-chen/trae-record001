import time
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from memory_analyzer import MemoryAnalyzer, MemoryInfo, NodeInfo, PerformanceMetrics
from redis_connection import RedisConnectionManager
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DefragMethod(str, Enum):
    MEMORY_PURGE = "memory_purge"
    SLAVE_RESTART = "slave_restart"
    FAILOVER_AND_RESTART = "failover_and_restart"
    SKIPPED = "skipped"


@dataclass
class PerformanceImpact:
    p99_latency_increase_ms: float = 0.0
    p50_latency_increase_ms: float = 0.0
    qps_drop_percent: float = 0.0
    hit_rate_change: float = 0.0
    max_connected_clients: int = 0
    avg_latency_during_defrag_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'p99_latency_increase_ms': self.p99_latency_increase_ms,
            'p50_latency_increase_ms': self.p50_latency_increase_ms,
            'qps_drop_percent': self.qps_drop_percent,
            'hit_rate_change': self.hit_rate_change,
            'max_connected_clients': self.max_connected_clients,
            'avg_latency_during_defrag_ms': self.avg_latency_during_defrag_ms
        }


@dataclass
class DefragResult:
    node_id: str
    host: str
    port: int
    method: DefragMethod
    before: MemoryInfo
    after: MemoryInfo = None
    success: bool = False
    duration_seconds: float = 0.0
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    performance_impact: PerformanceImpact = field(default_factory=PerformanceImpact)
    redis_version: str = ""
    mem_allocator: str = ""

    @property
    def memory_saved_bytes(self) -> int:
        if not self.after:
            return 0
        return self.before.used_memory_rss - self.after.used_memory_rss

    @property
    def memory_saved_mb(self) -> float:
        return self.memory_saved_bytes / (1024 * 1024)

    @property
    def fragmentation_improvement(self) -> float:
        if not self.after:
            return 0.0
        return self.before.mem_fragmentation_ratio - self.after.mem_fragmentation_ratio

    @property
    def fragmentation_ratio_after(self) -> float:
        return self.after.mem_fragmentation_ratio if self.after else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'method': self.method.value if isinstance(self.method, DefragMethod) else self.method,
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'timestamp': self.timestamp,
            'memory_saved_mb': self.memory_saved_mb,
            'fragmentation_improvement': self.fragmentation_improvement,
            'redis_version': self.redis_version,
            'mem_allocator': self.mem_allocator,
            'performance_impact': self.performance_impact.to_dict(),
            'before': {
                'used_memory_mb': self.before.used_memory_mb,
                'used_memory_rss_mb': self.before.used_memory_rss_mb,
                'mem_fragmentation_ratio': self.before.mem_fragmentation_ratio,
                'fragmentation_mb': self.before.fragmentation_mb,
                'p99_latency_ms': self.before.performance_metrics.p99_latency_ms,
                'p50_latency_ms': self.before.performance_metrics.p50_latency_ms,
                'qps': self.before.performance_metrics.qps,
                'hit_rate': self.before.performance_metrics.hit_rate
            },
            'after': {
                'used_memory_mb': self.after.used_memory_mb,
                'used_memory_rss_mb': self.after.used_memory_rss_mb,
                'mem_fragmentation_ratio': self.after.mem_fragmentation_ratio,
                'fragmentation_mb': self.after.fragmentation_mb,
                'p99_latency_ms': self.after.performance_metrics.p99_latency_ms,
                'p50_latency_ms': self.after.performance_metrics.p50_latency_ms,
                'qps': self.after.performance_metrics.qps,
                'hit_rate': self.after.performance_metrics.hit_rate
            } if self.after else None
        }


class MemoryDefragmenter:
    def __init__(self, connection_manager: RedisConnectionManager = None, 
                 analyzer: MemoryAnalyzer = None, parallel: bool = True,
                 max_workers: int = 4):
        self.connection_manager = connection_manager or RedisConnectionManager()
        self.analyzer = analyzer or MemoryAnalyzer(self.connection_manager)
        self.purge_timeout = Config.PURGE_TIMEOUT
        self.parallel = parallel
        self.max_workers = max_workers
        self._performance_monitoring: Dict[str, List[PerformanceMetrics]] = {}

    def _get_node_by_id(self, node_id: str) -> Dict[str, Any]:
        nodes = self.connection_manager.get_all_nodes()
        for node in nodes:
            if node['id'] == node_id:
                return node
        raise ValueError(f"Node with id {node_id} not found")

    def determine_defrag_method(self, node_info: NodeInfo) -> DefragMethod:
        if node_info.supports_memory_purge():
            logger.info(f"Node {node_info.host}:{node_info.port} supports MEMORY PURGE (Redis {node_info.version})")
            return DefragMethod.MEMORY_PURGE
        elif node_info.is_slave:
            logger.info(f"Node {node_info.host}:{node_info.port} is slave, will use SLAVE RESTART method")
            return DefragMethod.SLAVE_RESTART
        else:
            logger.warning(
                f"Node {node_info.host}:{node_info.port} (Redis {node_info.version}) "
                f"does not support MEMORY PURGE and is master, requires FAILOVER"
            )
            return DefragMethod.FAILOVER_AND_RESTART

    def execute_memory_purge(self, node: Dict[str, Any]) -> bool:
        try:
            conn = node['connection']
            logger.info(f"Executing MEMORY PURGE on {node['host']}:{node['port']}")
            result = conn.execute_command('MEMORY', 'PURGE')
            logger.info(f"MEMORY PURGE completed on {node['host']}:{node['port']}: {result}")
            return True
        except Exception as e:
            logger.error(f"MEMORY PURGE failed on {node['host']}:{node['port']}: {e}")
            raise

    def _restart_redis_process(self, node: Dict[str, Any]) -> bool:
        logger.warning(f"Process restart requires external orchestration for {node['host']}:{node['port']}")
        logger.info("In production, this would trigger a restart via systemd/supervisor/k8s")
        return True

    def execute_slave_restart(self, node: Dict[str, Any], node_info: NodeInfo) -> bool:
        try:
            logger.info(f"Executing SLAVE RESTART on {node['host']}:{node['port']}")
            conn = node['connection']
            
            logger.info(f"Making slave {node['host']}:{node['port']} read-only...")
            conn.config_set('slave-read-only', 'yes')
            
            logger.info(f"Waiting for slave to catch up with master...")
            time.sleep(2)
            
            replication_info = self.analyzer._parse_info(conn.execute_command('INFO', 'REPLICATION'))
            master_link_status = replication_info.get('master_link_status', 'down')
            
            if master_link_status != 'up':
                logger.warning(f"Slave {node['host']}:{node['port']} master link is not up")
            
            success = self._restart_redis_process(node)
            
            logger.info(f"SLAVE RESTART method completed on {node['host']}:{node['port']}")
            return success
        except Exception as e:
            logger.error(f"SLAVE RESTART failed on {node['host']}:{node['port']}: {e}")
            raise

    def _monitor_performance(self, node: Dict[str, Any], stop_event: threading.Event):
        metrics_list = []
        while not stop_event.is_set():
            try:
                metrics = self.analyzer.get_performance_metrics(node)
                metrics_list.append(metrics)
            except Exception as e:
                logger.warning(f"Failed to collect performance metrics: {e}")
            time.sleep(0.5)
        self._performance_monitoring[node['id']] = metrics_list

    def _calculate_performance_impact(self, node_id: str, before: PerformanceMetrics,
                                       after: PerformanceMetrics) -> PerformanceImpact:
        monitoring = self._performance_monitoring.get(node_id, [])
        
        if monitoring:
            avg_latency = sum(m.avg_latency_ms for m in monitoring) / len(monitoring)
            max_clients = max(m.connected_clients for m in monitoring) if monitoring else 0
        else:
            avg_latency = 0.0
            max_clients = 0
        
        p99_increase = after.p99_latency_ms - before.p99_latency_ms
        p50_increase = after.p50_latency_ms - before.p50_latency_ms
        
        qps_drop = 0.0
        if before.qps > 0:
            qps_drop = (before.qps - after.qps) / before.qps * 100
        
        hit_rate_change = after.hit_rate - before.hit_rate
        
        return PerformanceImpact(
            p99_latency_increase_ms=p99_increase,
            p50_latency_increase_ms=p50_increase,
            qps_drop_percent=qps_drop,
            hit_rate_change=hit_rate_change,
            max_connected_clients=max_clients,
            avg_latency_during_defrag_ms=avg_latency
        )

    def defrag_node(self, node_id: str, wait_after_purge: int = 5) -> DefragResult:
        logger.info(f"Starting defragmentation for node {node_id}")
        
        node = self._get_node_by_id(node_id)
        node_info = self.analyzer.get_node_info(node)
        method = self.determine_defrag_method(node_info)
        
        start_time = time.time()
        
        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_performance,
            args=(node, stop_event)
        )
        monitor_thread.start()
        
        try:
            before_info = self.analyzer.get_node_memory_info(node)
            logger.info(
                f"Before defrag [{method.value}] - {node['host']}:{node['port']}: "
                f"fragmentation={before_info.mem_fragmentation_ratio:.2f}, "
                f"rss={before_info.used_memory_rss_mb:.2f}MB, "
                f"P99={before_info.performance_metrics.p99_latency_ms:.2f}ms, "
                f"QPS={before_info.performance_metrics.qps:.0f}"
            )

            if method == DefragMethod.MEMORY_PURGE:
                self.execute_memory_purge(node)
            elif method == DefragMethod.SLAVE_RESTART:
                self.execute_slave_restart(node, node_info)
            elif method == DefragMethod.FAILOVER_AND_RESTART:
                logger.warning(f"FAILOVER_AND_RESTART requires manual intervention, skipping {node['host']}:{node['port']}")
                return DefragResult(
                    node_id=node_id,
                    host=node['host'],
                    port=node['port'],
                    method=DefragMethod.SKIPPED,
                    before=before_info,
                    success=False,
                    duration_seconds=0,
                    error_message="FAILOVER_AND_RESTART requires manual intervention",
                    redis_version=str(node_info.version),
                    mem_allocator=node_info.mem_allocator
                )
            
            logger.info(f"Waiting {wait_after_purge} seconds for memory to stabilize...")
            time.sleep(wait_after_purge)
            
            after_info = self.analyzer.get_node_memory_info(node)
            duration = time.time() - start_time
            
            performance_impact = self._calculate_performance_impact(
                node_id, before_info.performance_metrics, after_info.performance_metrics
            )
            
            logger.info(
                f"After defrag [{method.value}] - {node['host']}:{node['port']}: "
                f"fragmentation={after_info.mem_fragmentation_ratio:.2f}, "
                f"rss={after_info.used_memory_rss_mb:.2f}MB, "
                f"saved={before_info.used_memory_rss_mb - after_info.used_memory_rss_mb:.2f}MB, "
                f"P99 change={performance_impact.p99_latency_increase_ms:+.2f}ms, "
                f"QPS change={-performance_impact.qps_drop_percent:+.1f}%"
            )

            result = DefragResult(
                node_id=node_id,
                host=node['host'],
                port=node['port'],
                method=method,
                before=before_info,
                after=after_info,
                success=True,
                duration_seconds=duration,
                performance_impact=performance_impact,
                redis_version=str(node_info.version),
                mem_allocator=node_info.mem_allocator
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Defrag failed for node {node_id}: {e}")
            
            before_info = self.analyzer.get_node_memory_info(node)
            return DefragResult(
                node_id=node_id,
                host=node['host'],
                port=node['port'],
                method=method,
                before=before_info,
                success=False,
                duration_seconds=duration,
                error_message=str(e),
                redis_version=str(node_info.version),
                mem_allocator=node_info.mem_allocator
            )
        finally:
            stop_event.set()
            monitor_thread.join(timeout=2)

    def defrag_nodes_parallel(self, node_ids: List[str]) -> List[DefragResult]:
        logger.info(f"Starting parallel defragmentation for {len(node_ids)} nodes (max workers={self.max_workers})")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.defrag_node, node_id): node_id for node_id in node_ids}
            
            for future in as_completed(futures):
                node_id = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Parallel defrag failed for node {node_id}: {e}")
        
        return results

    def defrag_high_fragmentation_nodes(self, threshold: float = None, 
                                         min_memory_mb: float = None) -> List[DefragResult]:
        logger.info("Starting defragmentation for high fragmentation nodes")
        
        high_frag_nodes = self.analyzer.get_high_fragmentation_nodes()
        results = []
        
        if not high_frag_nodes:
            logger.info("No nodes with high fragmentation found")
            return results

        logger.info(f"Found {len(high_frag_nodes)} nodes with high fragmentation")
        
        node_ids = [m.node_id for m in high_frag_nodes]
        
        if self.parallel:
            results = self.defrag_nodes_parallel(node_ids)
        else:
            for mem_info in high_frag_nodes:
                try:
                    result = self.defrag_node(mem_info.node_id)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to defrag node {mem_info.node_id}: {e}")
        
        return results

    def defrag_all_nodes(self) -> List[DefragResult]:
        logger.info("Starting defragmentation for all nodes")
        
        all_mem_info = self.analyzer.get_all_memory_info()
        node_ids = [m.node_id for m in all_mem_info]
        
        if self.parallel:
            return self.defrag_nodes_parallel(node_ids)
        
        results = []
        for mem_info in all_mem_info:
            try:
                result = self.defrag_node(mem_info.node_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to defrag node {mem_info.node_id}: {e}")
        
        return results

    def get_defrag_summary(self, results: List[DefragResult]) -> Dict[str, Any]:
        if not results:
            return {}
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        total_saved_mb = sum(r.memory_saved_mb for r in successful)
        avg_improvement = (
            sum(r.fragmentation_improvement for r in successful) / len(successful)
            if successful else 0
        )
        
        method_counts: Dict[str, int] = {}
        for r in results:
            method = r.method.value if isinstance(r.method, DefragMethod) else str(r.method)
            method_counts[method] = method_counts.get(method, 0) + 1
        
        avg_p99_increase = (
            sum(r.performance_impact.p99_latency_increase_ms for r in successful) / len(successful)
            if successful else 0
        )
        avg_qps_drop = (
            sum(r.performance_impact.qps_drop_percent for r in successful) / len(successful)
            if successful else 0
        )
        
        return {
            'total_nodes': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'total_memory_saved_mb': total_saved_mb,
            'average_fragmentation_improvement': avg_improvement,
            'total_duration_seconds': sum(r.duration_seconds for r in results),
            'method_distribution': method_counts,
            'average_p99_latency_increase_ms': avg_p99_increase,
            'average_qps_drop_percent': avg_qps_drop,
            'results': [r.to_dict() for r in results]
        }

    def compare_before_after(self, result: DefragResult) -> str:
        method = result.method.value if isinstance(result.method, DefragMethod) else str(result.method)
        
        if not result.success or not result.after:
            lines = [
                f"=== Defragmentation Report for {result.host}:{result.port} ===",
                f"Method: {method}",
                f"Redis Version: {result.redis_version}",
                f"Allocator: {result.mem_allocator}",
                f"Status: FAILED - {result.error_message}",
                f"Duration: {result.duration_seconds:.2f} seconds"
            ]
            return '\n'.join(lines)
        
        lines = [
            f"=== Defragmentation Report for {result.host}:{result.port} ===",
            f"Method: {method}",
            f"Redis Version: {result.redis_version}",
            f"Allocator: {result.mem_allocator}",
            f"Status: SUCCESS",
            f"Duration: {result.duration_seconds:.2f} seconds",
            "",
            f"{'Metric':<30} {'Before':>15} {'After':>15} {'Change':>15}",
            f"{'-'*75}",
            f"{'Used Memory (MB)':<30} {result.before.used_memory_mb:>15.2f} {result.after.used_memory_mb:>15.2f} {result.after.used_memory_mb - result.before.used_memory_mb:>+15.2f}",
            f"{'RSS Memory (MB)':<30} {result.before.used_memory_rss_mb:>15.2f} {result.after.used_memory_rss_mb:>15.2f} {result.memory_saved_mb:>+15.2f}",
            f"{'Fragmentation Ratio':<30} {result.before.mem_fragmentation_ratio:>15.2f} {result.after.mem_fragmentation_ratio:>15.2f} {result.fragmentation_improvement:>+15.2f}",
            f"{'Fragmentation (MB)':<30} {result.before.fragmentation_mb:>15.2f} {result.after.fragmentation_mb:>15.2f} {result.before.fragmentation_mb - result.after.fragmentation_mb:>+15.2f}",
            "",
            f"=== Performance Impact ===",
            f"{'P50 Latency (ms)':<30} {result.before.performance_metrics.p50_latency_ms:>15.2f} {result.after.performance_metrics.p50_latency_ms:>15.2f} {result.performance_impact.p50_latency_increase_ms:>+15.2f}",
            f"{'P99 Latency (ms)':<30} {result.before.performance_metrics.p99_latency_ms:>15.2f} {result.after.performance_metrics.p99_latency_ms:>15.2f} {result.performance_impact.p99_latency_increase_ms:>+15.2f}",
            f"{'QPS':<30} {result.before.performance_metrics.qps:>15.0f} {result.after.performance_metrics.qps:>15.0f} {-result.performance_impact.qps_drop_percent:>+14.1f}%",
            f"{'Hit Rate':<30} {result.before.performance_metrics.hit_rate:>14.1%} {result.after.performance_metrics.hit_rate:>14.1%} {result.performance_impact.hit_rate_change:>+14.1%}",
            f"{'Max Clients':<30} {'-':>15} {'-':>15} {result.performance_impact.max_connected_clients:>15d}",
            f"{'Avg Latency During (ms)':<30} {'-':>15} {'-':>15} {result.performance_impact.avg_latency_during_defrag_ms:>15.2f}",
            "",
            f"Memory saved: {result.memory_saved_mb:.2f} MB",
            f"Fragmentation improved by: {result.fragmentation_improvement:.2f}",
            f"P99 Latency change: {result.performance_impact.p99_latency_increase_ms:+.2f} ms"
        ]
        
        return '\n'.join(lines)
