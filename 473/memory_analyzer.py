import logging
import time
import statistics
import math
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
from redis_connection import RedisConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FragmentationCause(str, Enum):
    FREQUENT_DELETIONS = "frequent_deletions"
    LARGE_KEYS = "large_keys"
    EXPIRING_KEYS = "expiring_keys"
    UNEVEN_ALLOCATION = "uneven_allocation"
    HIGH_WRITE_THROUGHPUT = "high_write_throughput"
    LONG_TTL_KEYS = "long_ttl_keys"
    UNKNOWN = "unknown"


@dataclass
class KeyspaceStats:
    total_keys: int = 0
    expires_keys: int = 0
    expires_percent: float = 0.0
    avg_ttl_seconds: float = 0.0
    large_keys_count: int = 0
    large_keys_total_size: int = 0
    key_count_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class CommandStats:
    total_calls: int = 0
    delete_calls: int = 0
    expire_calls: int = 0
    write_calls: int = 0
    read_calls: int = 0
    delete_percent: float = 0.0
    expire_percent: float = 0.0
    write_to_read_ratio: float = 0.0


@dataclass
class FragmentationCauseAnalysis:
    node_id: str
    host: str
    port: int
    primary_causes: List[FragmentationCause] = field(default_factory=list)
    cause_confidence: Dict[FragmentationCause, float] = field(default_factory=dict)
    keyspace_stats: KeyspaceStats = field(default_factory=KeyspaceStats)
    command_stats: CommandStats = field(default_factory=CommandStats)
    recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_id': self.node_id,
            'host': self.host,
            'port': self.port,
            'primary_causes': [c.value for c in self.primary_causes],
            'cause_confidence': {k.value: v for k, v in self.cause_confidence.items()},
            'keyspace_stats': {
                'total_keys': self.keyspace_stats.total_keys,
                'expires_keys': self.keyspace_stats.expires_keys,
                'expires_percent': self.keyspace_stats.expires_percent,
                'avg_ttl_seconds': self.keyspace_stats.avg_ttl_seconds,
                'large_keys_count': self.keyspace_stats.large_keys_count,
                'large_keys_total_size': self.keyspace_stats.large_keys_total_size,
                'key_count_by_type': self.keyspace_stats.key_count_by_type
            },
            'command_stats': {
                'total_calls': self.command_stats.total_calls,
                'delete_calls': self.command_stats.delete_calls,
                'expire_calls': self.command_stats.expire_calls,
                'write_calls': self.command_stats.write_calls,
                'read_calls': self.command_stats.read_calls,
                'delete_percent': self.command_stats.delete_percent,
                'expire_percent': self.command_stats.expire_percent,
                'write_to_read_ratio': self.command_stats.write_to_read_ratio
            },
            'recommendations': self.recommendations,
            'analysis_timestamp': self.analysis_timestamp
        }


@dataclass
class PerformanceMetrics:
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    qps: float = 0.0
    instantaneous_ops_per_sec: int = 0
    total_commands_processed: int = 0
    rejected_connections: int = 0
    keyspace_hits: int = 0
    keyspace_misses: int = 0
    hit_rate: float = 0.0
    connected_clients: int = 0
    blocked_clients: int = 0


@dataclass
class RedisVersion:
    major: int
    minor: int
    patch: int
    raw: str
    
    def supports_memory_purge(self) -> bool:
        return self.major >= 4
    
    def __str__(self) -> str:
        return self.raw


@dataclass
class NodeInfo:
    node_id: str
    host: str
    port: int
    role: str
    version: RedisVersion
    mem_allocator: str
    is_master: bool
    is_slave: bool
    master_host: Optional[str] = None
    master_port: Optional[int] = None
    slave_priority: int = 0
    slave_read_only: bool = True
    
    def supports_memory_purge(self) -> bool:
        return self.version.supports_memory_purge() and self.mem_allocator == 'jemalloc'


@dataclass
class MemoryInfo:
    node_id: str
    host: str
    port: int
    used_memory: int
    used_memory_rss: int
    used_memory_peak: int
    used_memory_lua: int
    mem_fragmentation_ratio: float
    mem_allocator: str
    total_system_memory: int
    maxmemory: int
    maxmemory_policy: str
    timestamp: str
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)

    @property
    def used_memory_mb(self) -> float:
        return self.used_memory / (1024 * 1024)

    @property
    def used_memory_rss_mb(self) -> float:
        return self.used_memory_rss / (1024 * 1024)

    @property
    def fragmentation_bytes(self) -> int:
        return self.used_memory_rss - self.used_memory

    @property
    def fragmentation_mb(self) -> float:
        return self.fragmentation_bytes / (1024 * 1024)


class MemoryAnalyzer:
    def __init__(self, connection_manager: RedisConnectionManager = None):
        self.connection_manager = connection_manager or RedisConnectionManager()
        self._node_info_cache: Dict[str, NodeInfo] = {}

    def _parse_info(self, info_raw: str) -> Dict[str, str]:
        lines = info_raw.strip().split('\r\n')
        info = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                info[key] = value
        return info

    def get_redis_version(self, node: Dict[str, Any]) -> RedisVersion:
        try:
            conn = node['connection']
            info_raw = conn.execute_command('INFO', 'SERVER')
            info = self._parse_info(info_raw)
            version_str = info.get('redis_version', '0.0.0')
            parts = version_str.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return RedisVersion(major=major, minor=minor, patch=patch, raw=version_str)
        except Exception as e:
            logger.error(f"Failed to get version for {node['host']}:{node['port']}: {e}")
            return RedisVersion(major=0, minor=0, patch=0, raw='unknown')

    def get_node_info(self, node: Dict[str, Any]) -> NodeInfo:
        node_id = node['id']
        if node_id in self._node_info_cache:
            return self._node_info_cache[node_id]
        
        try:
            conn = node['connection']
            version = self.get_redis_version(node)
            
            memory_info_raw = conn.execute_command('INFO', 'MEMORY')
            memory_info = self._parse_info(memory_info_raw)
            mem_allocator = memory_info.get('mem_allocator', 'unknown')
            
            replication_raw = conn.execute_command('INFO', 'REPLICATION')
            replication_info = self._parse_info(replication_raw)
            role = replication_info.get('role', 'master')
            is_master = role == 'master'
            is_slave = role == 'slave'
            
            master_host = replication_info.get('master_host') if is_slave else None
            master_port = int(replication_info.get('master_port', 0)) if is_slave else None
            slave_priority = int(replication_info.get('slave_priority', 100))
            slave_read_only = replication_info.get('slave_read_only', '1') == '1'
            
            node_info = NodeInfo(
                node_id=node_id,
                host=node['host'],
                port=node['port'],
                role=role,
                version=version,
                mem_allocator=mem_allocator,
                is_master=is_master,
                is_slave=is_slave,
                master_host=master_host,
                master_port=master_port,
                slave_priority=slave_priority,
                slave_read_only=slave_read_only
            )
            
            self._node_info_cache[node_id] = node_info
            return node_info
        except Exception as e:
            logger.error(f"Failed to get node info for {node['host']}:{node['port']}: {e}")
            raise

    def measure_latency(self, node: Dict[str, Any], samples: int = 100) -> Tuple[float, float, float]:
        try:
            conn = node['connection']
            latencies = []
            for _ in range(samples):
                start = time.perf_counter()
                conn.ping()
                end = time.perf_counter()
                latencies.append((end - start) * 1000)
            
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            p99 = latencies[int(len(latencies) * 0.99)]
            avg = sum(latencies) / len(latencies)
            
            return p50, p99, avg
        except Exception as e:
            logger.warning(f"Failed to measure latency for {node['host']}:{node['port']}: {e}")
            return 0.0, 0.0, 0.0

    def get_performance_metrics(self, node: Dict[str, Any]) -> PerformanceMetrics:
        try:
            conn = node['connection']
            
            stats_raw = conn.execute_command('INFO', 'STATS')
            stats_info = self._parse_info(stats_raw)
            
            clients_raw = conn.execute_command('INFO', 'CLIENTS')
            clients_info = self._parse_info(clients_raw)
            
            instantaneous_ops = int(stats_info.get('instantaneous_ops_per_sec', 0))
            total_commands = int(stats_info.get('total_commands_processed', 0))
            rejected = int(stats_info.get('rejected_connections', 0))
            keyspace_hits = int(stats_info.get('keyspace_hits', 0))
            keyspace_misses = int(stats_info.get('keyspace_misses', 0))
            connected_clients = int(clients_info.get('connected_clients', 0))
            blocked_clients = int(clients_info.get('blocked_clients', 0))
            
            hit_rate = 0.0
            if keyspace_hits + keyspace_misses > 0:
                hit_rate = keyspace_hits / (keyspace_hits + keyspace_misses)
            
            p50, p99, avg = self.measure_latency(node, samples=50)
            
            return PerformanceMetrics(
                p50_latency_ms=p50,
                p99_latency_ms=p99,
                avg_latency_ms=avg,
                qps=float(instantaneous_ops),
                instantaneous_ops_per_sec=instantaneous_ops,
                total_commands_processed=total_commands,
                rejected_connections=rejected,
                keyspace_hits=keyspace_hits,
                keyspace_misses=keyspace_misses,
                hit_rate=hit_rate,
                connected_clients=connected_clients,
                blocked_clients=blocked_clients
            )
        except Exception as e:
            logger.warning(f"Failed to get performance metrics for {node['host']}:{node['port']}: {e}")
            return PerformanceMetrics()

    def _parse_memory_info(self, info_raw: str, node: Dict[str, Any]) -> MemoryInfo:
        info = self._parse_info(info_raw)

        def safe_int(key: str, default: int = 0) -> int:
            try:
                return int(float(info.get(key, default)))
            except (ValueError, TypeError):
                return default

        def safe_float(key: str, default: float = 0.0) -> float:
            try:
                return float(info.get(key, default))
            except (ValueError, TypeError):
                return default

        performance_metrics = self.get_performance_metrics(node)
        
        return MemoryInfo(
            node_id=node['id'],
            host=node['host'],
            port=node['port'],
            used_memory=safe_int('used_memory'),
            used_memory_rss=safe_int('used_memory_rss'),
            used_memory_peak=safe_int('used_memory_peak'),
            used_memory_lua=safe_int('used_memory_lua'),
            mem_fragmentation_ratio=safe_float('mem_fragmentation_ratio', 1.0),
            mem_allocator=info.get('mem_allocator', 'unknown'),
            total_system_memory=safe_int('total_system_memory'),
            maxmemory=safe_int('maxmemory'),
            maxmemory_policy=info.get('maxmemory_policy', 'unknown'),
            timestamp=datetime.now().isoformat(),
            performance_metrics=performance_metrics
        )

    def get_node_memory_info(self, node: Dict[str, Any]) -> MemoryInfo:
        try:
            conn = node['connection']
            info_raw = conn.execute_command('INFO', 'MEMORY')
            return self._parse_memory_info(info_raw, node)
        except Exception as e:
            logger.error(f"Failed to get memory info for node {node['host']}:{node['port']}: {e}")
            raise

    def get_all_memory_info(self) -> List[MemoryInfo]:
        nodes = self.connection_manager.get_all_nodes()
        memory_infos = []
        for node in nodes:
            try:
                mem_info = self.get_node_memory_info(node)
                memory_infos.append(mem_info)
                logger.info(
                    f"Node {mem_info.host}:{mem_info.port} - "
                    f"Fragmentation: {mem_info.mem_fragmentation_ratio:.2f}, "
                    f"Used: {mem_info.used_memory_mb:.2f}MB, "
                    f"RSS: {mem_info.used_memory_rss_mb:.2f}MB"
                )
            except Exception as e:
                logger.warning(f"Skipping node {node['host']}:{node['port']} due to error: {e}")
        return memory_infos

    def calculate_fragmentation_ratio(self, mem_info: MemoryInfo) -> float:
        if mem_info.used_memory > 0:
            return mem_info.used_memory_rss / mem_info.used_memory
        return 1.0

    def is_fragmentation_high(self, mem_info: MemoryInfo, threshold: float = None, 
                              min_memory_mb: float = None) -> bool:
        from config import Config
        threshold = threshold or Config.FRAGMENTATION_THRESHOLD
        min_memory_mb = min_memory_mb or Config.MIN_MEMORY_MB
        
        if mem_info.used_memory_mb < min_memory_mb:
            logger.info(
                f"Node {mem_info.host}:{mem_info.port} memory usage {mem_info.used_memory_mb:.2f}MB "
                f"below threshold {min_memory_mb}MB, skipping"
            )
            return False
        
        actual_ratio = self.calculate_fragmentation_ratio(mem_info)
        is_high = actual_ratio >= threshold
        
        if is_high:
            logger.warning(
                f"Node {mem_info.host}:{mem_info.port} fragmentation {actual_ratio:.2f} "
                f"exceeds threshold {threshold}"
            )
        else:
            logger.info(
                f"Node {mem_info.host}:{mem_info.port} fragmentation {actual_ratio:.2f} "
                f"within normal range"
            )
        
        return is_high

    def get_high_fragmentation_nodes(self) -> List[MemoryInfo]:
        all_memory_info = self.get_all_memory_info()
        return [
            mem_info for mem_info in all_memory_info
            if self.is_fragmentation_high(mem_info)
        ]

    def get_cluster_fragmentation_summary(self) -> Dict[str, Any]:
        memory_infos = self.get_all_memory_info()
        if not memory_infos:
            return {}
        
        ratios = [m.mem_fragmentation_ratio for m in memory_infos]
        used_mems = [m.used_memory_mb for m in memory_infos]
        rss_mems = [m.used_memory_rss_mb for m in memory_infos]
        
        return {
            'node_count': len(memory_infos),
            'avg_fragmentation_ratio': sum(ratios) / len(ratios),
            'max_fragmentation_ratio': max(ratios),
            'min_fragmentation_ratio': min(ratios),
            'total_used_memory_mb': sum(used_mems),
            'total_rss_memory_mb': sum(rss_mems),
            'total_fragmentation_mb': sum(rss_mems) - sum(used_mems),
            'high_fragmentation_count': len([r for r in ratios if r >= 1.5]),
            'nodes': [
                {
                    'node_id': m.node_id,
                    'host': m.host,
                    'port': m.port,
                    'fragmentation_ratio': m.mem_fragmentation_ratio,
                    'used_memory_mb': m.used_memory_mb,
                    'fragmentation_mb': m.fragmentation_mb
                }
                for m in memory_infos
            ]
        }

    def get_keyspace_stats(self, node: Dict[str, Any], sample_size: int = 1000) -> KeyspaceStats:
        try:
            conn = node['connection']
            keyspace_stats = KeyspaceStats()
            
            keyspace_info_raw = conn.execute_command('INFO', 'KEYSPACE')
            keyspace_info = self._parse_info(keyspace_info_raw)
            
            total_keys = 0
            expires_keys = 0
            
            for db_name, db_info in keyspace_info.items():
                if db_name.startswith('db'):
                    parts = db_info.split(',')
                    for part in parts:
                        k, v = part.split('=')
                        if k == 'keys':
                            total_keys += int(v)
                        elif k == 'expires':
                            expires_keys += int(v)
            
            keyspace_stats.total_keys = total_keys
            keyspace_stats.expires_keys = expires_keys
            if total_keys > 0:
                keyspace_stats.expires_percent = (expires_keys / total_keys) * 100
            
            try:
                cursor = 0
                sampled = 0
                large_keys_count = 0
                large_keys_size = 0
                key_types = defaultdict(int)
                ttl_sum = 0
                ttl_count = 0
                
                while sampled < sample_size:
                    cursor, keys = conn.scan(cursor=cursor, count=min(100, sample_size - sampled))
                    for key in keys:
                        try:
                            key_type = conn.type(key)
                            key_types[key_type] += 1
                            
                            try:
                                mem_usage = conn.memory_usage(key, samples=5)
                                if mem_usage and mem_usage > 1024 * 1024:
                                    large_keys_count += 1
                                    large_keys_size += mem_usage
                            except:
                                pass
                            
                            ttl = conn.ttl(key)
                            if ttl > 0:
                                ttl_sum += ttl
                                ttl_count += 1
                        except:
                            pass
                    
                    sampled += len(keys)
                    if cursor == 0:
                        break
                
                keyspace_stats.large_keys_count = large_keys_count
                keyspace_stats.large_keys_total_size = large_keys_size
                keyspace_stats.key_count_by_type = dict(key_types)
                if ttl_count > 0:
                    keyspace_stats.avg_ttl_seconds = ttl_sum / ttl_count
                
            except Exception as e:
                logger.warning(f"Failed to sample keys for {node['host']}:{node['port']}: {e}")
            
            return keyspace_stats
        except Exception as e:
            logger.error(f"Failed to get keyspace stats for {node['host']}:{node['port']}: {e}")
            return KeyspaceStats()

    def get_command_stats(self, node: Dict[str, Any]) -> CommandStats:
        try:
            conn = node['connection']
            cmd_stats_raw = conn.execute_command('INFO', 'COMMANDSTATS')
            cmd_stats_info = self._parse_info(cmd_stats_raw)
            
            cmd_stats = CommandStats()
            
            write_commands = {'set', 'setex', 'setnx', 'hset', 'hmset', 'lpush', 'rpush', 
                             'sadd', 'zadd', 'incr', 'decr', 'incrby', 'decrby', 'append',
                             'mset', 'msetnx', 'getset', 'setrange'}
            read_commands = {'get', 'mget', 'hget', 'hmget', 'hgetall', 'lrange', 'smembers',
                            'sismember', 'zrange', 'zscore', 'exists', 'type', 'strlen',
                            'hlen', 'llen', 'scard', 'zcard'}
            delete_commands = {'del', 'unlink', 'hdel', 'lrem', 'srem', 'zrem'}
            expire_commands = {'expire', 'expireat', 'pexpire', 'pexpireat'}
            
            for key, value in cmd_stats_info.items():
                if key.startswith('cmdstat_'):
                    cmd_name = key.replace('cmdstat_', '').lower()
                    parts = value.split(',')
                    calls = 0
                    for part in parts:
                        if part.startswith('calls='):
                            calls = int(part.split('=')[1])
                            break
                    
                    cmd_stats.total_calls += calls
                    
                    if cmd_name in delete_commands:
                        cmd_stats.delete_calls += calls
                    if cmd_name in expire_commands:
                        cmd_stats.expire_calls += calls
                    if cmd_name in write_commands:
                        cmd_stats.write_calls += calls
                    if cmd_name in read_commands:
                        cmd_stats.read_calls += calls
            
            if cmd_stats.total_calls > 0:
                cmd_stats.delete_percent = (cmd_stats.delete_calls / cmd_stats.total_calls) * 100
                cmd_stats.expire_percent = (cmd_stats.expire_calls / cmd_stats.total_calls) * 100
            if cmd_stats.read_calls > 0:
                cmd_stats.write_to_read_ratio = cmd_stats.write_calls / cmd_stats.read_calls
            
            return cmd_stats
        except Exception as e:
            logger.warning(f"Failed to get command stats for {node['host']}:{node['port']}: {e}")
            return CommandStats()

    def analyze_fragmentation_cause(self, node: Dict[str, Any], 
                                     mem_info: MemoryInfo = None) -> FragmentationCauseAnalysis:
        logger.info(f"Analyzing fragmentation cause for {node['host']}:{node['port']}")
        
        if mem_info is None:
            mem_info = self.get_node_memory_info(node)
        
        analysis = FragmentationCauseAnalysis(
            node_id=node['id'],
            host=node['host'],
            port=node['port']
        )
        
        try:
            keyspace_stats = self.get_keyspace_stats(node, sample_size=500)
            command_stats = self.get_command_stats(node)
            
            analysis.keyspace_stats = keyspace_stats
            analysis.command_stats = command_stats
            
            confidence_scores = {}
            
            if command_stats.delete_percent > 15:
                confidence = min(command_stats.delete_percent / 30, 1.0)
                confidence_scores[FragmentationCause.FREQUENT_DELETIONS] = confidence
                analysis.recommendations.append(
                    f"High delete rate ({command_stats.delete_percent:.1f}%), consider using UNLINK or batch deletes"
                )
            
            if command_stats.expire_percent > 10 or keyspace_stats.expires_percent > 30:
                confidence = max(command_stats.expire_percent / 25, keyspace_stats.expires_percent / 50)
                confidence = min(confidence, 1.0)
                confidence_scores[FragmentationCause.EXPIRING_KEYS] = confidence
                analysis.recommendations.append(
                    f"High expiring keys ({keyspace_stats.expires_percent:.1f}%), consider eviction policy optimization"
                )
            
            if keyspace_stats.large_keys_count > 0:
                large_key_percent = (keyspace_stats.large_keys_count / max(keyspace_stats.total_keys, 1)) * 100
                confidence = min(large_key_percent * 10, 1.0)
                confidence_scores[FragmentationCause.LARGE_KEYS] = confidence
                analysis.recommendations.append(
                    f"Found {keyspace_stats.large_keys_count} large keys (>1MB), consider splitting large objects"
                )
            
            if command_stats.write_to_read_ratio > 1.0:
                confidence = min(command_stats.write_to_read_ratio / 3, 1.0)
                confidence_scores[FragmentationCause.HIGH_WRITE_THROUGHPUT] = confidence
                analysis.recommendations.append(
                    f"High write/read ratio ({command_stats.write_to_read_ratio:.2f}), consider write optimization"
                )
            
            if keyspace_stats.avg_ttl_seconds > 7 * 24 * 3600:
                confidence = min(keyspace_stats.avg_ttl_seconds / (30 * 24 * 3600), 1.0)
                confidence_scores[FragmentationCause.LONG_TTL_KEYS] = confidence
                analysis.recommendations.append(
                    f"Long average TTL ({keyspace_stats.avg_ttl_seconds / 3600:.1f}h), review TTL strategy"
                )
            
            sorted_causes = sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True)
            analysis.primary_causes = [cause for cause, conf in sorted_causes if conf >= 0.3]
            analysis.cause_confidence = dict(confidence_scores)
            
            if not analysis.primary_causes:
                analysis.primary_causes = [FragmentationCause.UNKNOWN]
                analysis.recommendations.append(
                    "No clear cause identified, may be due to long-term allocation patterns"
                )
            
            logger.info(
                f"Analysis complete for {node['host']}:{node['port']} - "
                f"Primary causes: {[c.value for c in analysis.primary_causes]}"
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze fragmentation cause: {e}")
            analysis.primary_causes = [FragmentationCause.UNKNOWN]
            analysis.recommendations.append(f"Analysis failed: {str(e)}")
        
        return analysis

    def analyze_all_fragmentation_causes(self) -> List[FragmentationCauseAnalysis]:
        nodes = self.connection_manager.get_all_nodes()
        analyses = []
        
        for node in nodes:
            try:
                mem_info = self.get_node_memory_info(node)
                if mem_info.mem_fragmentation_ratio >= 1.3:
                    analysis = self.analyze_fragmentation_cause(node, mem_info)
                    analyses.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze node {node['host']}:{node['port']}: {e}")
        
        return analyses
