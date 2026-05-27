import logging
import subprocess
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JMXMetrics:
    broker_id: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in_bytes: float
    network_out_bytes: float
    messages_in_per_sec: float
    bytes_in_per_sec: float
    bytes_out_per_sec: float
    under_replicated_partitions: int
    request_handler_avg_idle_percent: float
    produce_request_p99_latency: float
    fetch_request_p99_latency: float


class JMXCollector:
    JMX_QUERIES = {
        'cpu_usage': 'java.lang:type=OperatingSystem/ProcessCpuLoad',
        'system_cpu_usage': 'java.lang:type=OperatingSystem/SystemCpuLoad',
        'memory_used': 'java.lang:type=Memory/HeapMemoryUsage',
        'memory_committed': 'java.lang:type=Memory/HeapMemoryUsage',
        'messages_in_per_sec': 'kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec/OneMinuteRate',
        'bytes_in_per_sec': 'kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec/OneMinuteRate',
        'bytes_out_per_sec': 'kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec/OneMinuteRate',
        'under_replicated_partitions': 'kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions/Value',
        'request_handler_avg_idle': 'kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent/OneMinuteRate',
        'produce_p99_latency': 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce/p99th',
        'fetch_p99_latency': 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer/p99th',
        'network_in': 'kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec/OneMinuteRate',
        'network_out': 'kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec/OneMinuteRate',
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.jmx_config = config.get('jmx', {})
        self.jmx_hosts = self.jmx_config.get('jmx_hosts', [])
        self.username = self.jmx_config.get('username')
        self.password = self.jmx_config.get('password')

    def _query_jmx_jmxterm(self, host: str, bean_name: str, attribute: str) -> Optional[Any]:
        try:
            host_parts = host.split(':')
            jmx_host = host_parts[0]
            jmx_port = host_parts[1] if len(host_parts) > 1 else '9999'

            cmd = f'echo "get -s {bean_name} {attribute}" | jmxterm -l service:jmx:rmi:///jndi/rmi://{jmx_host}:{jmx_port}/jmxrmi -n'
            
            if self.username and self.password:
                cmd = f'echo "open -u {self.username} -p {self.password} service:jmx:rmi:///jndi/rmi://{jmx_host}:{jmx_port}/jmxrmi; get -s {bean_name} {attribute}" | jmxterm -n'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if '=' in line and not line.startswith('#'):
                        value = line.split('=', 1)[1].strip()
                        try:
                            if value.endswith('L'):
                                value = value[:-1]
                            return float(value) if '.' in value else int(value)
                        except ValueError:
                            return value
            return None
        except Exception as e:
            logger.debug(f"JMX query failed for {host} {bean_name}: {str(e)}")
            return None

    def _collect_broker_metrics(self, host: str) -> Dict[str, Any]:
        logger.info(f"Collecting JMX metrics from {host}...")
        
        metrics = {
            'host': host,
            'status': 'UNKNOWN',
            'cpu_usage': None,
            'memory_usage_percent': None,
            'disk_usage_percent': None,
            'messages_in_per_sec': None,
            'bytes_in_per_sec': None,
            'bytes_out_per_sec': None,
            'under_replicated_partitions': None,
            'request_handler_avg_idle_percent': None,
            'produce_request_p99_latency_ms': None,
            'fetch_request_p99_latency_ms': None,
            'network_in_bytes_per_sec': None,
            'network_out_bytes_per_sec': None,
            'issues': []
        }

        try:
            cpu_load = self._query_jmx_jmxterm(host, 'java.lang:type=OperatingSystem', 'ProcessCpuLoad')
            if cpu_load is not None:
                metrics['cpu_usage'] = round(float(cpu_load) * 100, 2)

            heap_used = self._query_jmx_jmxterm(host, 'java.lang:type=Memory', 'HeapMemoryUsage')
            if heap_used and isinstance(heap_used, str):
                try:
                    parts = heap_used.split(',')
                    for p in parts:
                        if 'used=' in p:
                            used = int(p.split('used=')[1].split('}')[0])
                        if 'max=' in p:
                            max_val = int(p.split('max=')[1].split('}')[0])
                    if max_val and max_val > 0:
                        metrics['memory_usage_percent'] = round((used / max_val) * 100, 2)
                except:
                    pass

            metrics['messages_in_per_sec'] = self._query_jmx_jmxterm(
                host, 'kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec', 'OneMinuteRate'
            )
            metrics['bytes_in_per_sec'] = self._query_jmx_jmxterm(
                host, 'kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec', 'OneMinuteRate'
            )
            metrics['bytes_out_per_sec'] = self._query_jmx_jmxterm(
                host, 'kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec', 'OneMinuteRate'
            )
            metrics['under_replicated_partitions'] = self._query_jmx_jmxterm(
                host, 'kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions', 'Value'
            )
            metrics['request_handler_avg_idle_percent'] = self._query_jmx_jmxterm(
                host, 'kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent', 'OneMinuteRate'
            )
            metrics['produce_request_p99_latency_ms'] = self._query_jmx_jmxterm(
                host, 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce', 'p99th'
            )
            metrics['fetch_request_p99_latency_ms'] = self._query_jmx_jmxterm(
                host, 'kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer', 'p99th'
            )
            metrics['network_in_bytes_per_sec'] = metrics['bytes_in_per_sec']
            metrics['network_out_bytes_per_sec'] = metrics['bytes_out_per_sec']

            metrics['status'] = 'HEALTHY'

            warn_threshold = self.config['checks']['disk'].get('disk_warning_threshold', 70)
            crit_threshold = self.config['checks']['disk'].get('disk_critical_threshold', 85)

            if metrics['cpu_usage'] and metrics['cpu_usage'] > 80:
                metrics['issues'].append(f"High CPU usage: {metrics['cpu_usage']}%")
                metrics['status'] = 'WARNING' if metrics['cpu_usage'] < 90 else 'CRITICAL'

            if metrics['memory_usage_percent'] and metrics['memory_usage_percent'] > warn_threshold:
                metrics['issues'].append(f"High memory usage: {metrics['memory_usage_percent']}%")
                if metrics['memory_usage_percent'] > crit_threshold:
                    metrics['status'] = 'CRITICAL'
                elif metrics['status'] == 'HEALTHY':
                    metrics['status'] = 'WARNING'

            if metrics['under_replicated_partitions'] and metrics['under_replicated_partitions'] > 0:
                metrics['issues'].append(f"Under-replicated partitions: {metrics['under_replicated_partitions']}")
                metrics['status'] = 'WARNING'

            logger.info(f"JMX metrics collected from {host}, status: {metrics['status']}")

        except Exception as e:
            logger.error(f"Error collecting JMX metrics from {host}: {str(e)}")
            metrics['status'] = 'ERROR'
            metrics['issues'].append(f"Collection error: {str(e)}")

        return metrics

    def _estimate_disk_usage(self, host: str) -> Optional[float]:
        try:
            bytes_in = self._query_jmx_jmxterm(
                host, 'kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec', 'OneMinuteRate'
            )
            if bytes_in:
                return min(85.0, 50.0 + (float(bytes_in) / (100 * 1024 * 1024)) * 35)
        except:
            pass
        return None

    def collect_all(self) -> Dict[str, Any]:
        logger.info("Starting JMX metrics collection...")
        
        result = {
            'status': 'UNKNOWN',
            'total_brokers': len(self.jmx_hosts),
            'healthy_brokers': 0,
            'warning_brokers': 0,
            'critical_brokers': 0,
            'error_brokers': 0,
            'brokers': [],
            'aggregated_metrics': {},
            'issues': []
        }

        if not self.jmx_hosts:
            result['status'] = 'WARNING'
            result['issues'].append('No JMX hosts configured')
            return result

        for host in self.jmx_hosts:
            broker_metrics = self._collect_broker_metrics(host)
            result['brokers'].append(broker_metrics)

            if broker_metrics['status'] == 'HEALTHY':
                result['healthy_brokers'] += 1
            elif broker_metrics['status'] == 'WARNING':
                result['warning_brokers'] += 1
            elif broker_metrics['status'] == 'CRITICAL':
                result['critical_brokers'] += 1
            else:
                result['error_brokers'] += 1

        if result['brokers']:
            cpu_usages = [b['cpu_usage'] for b in result['brokers'] if b['cpu_usage'] is not None]
            memory_usages = [b['memory_usage_percent'] for b in result['brokers'] if b['memory_usage_percent'] is not None]
            messages_in = [b['messages_in_per_sec'] for b in result['brokers'] if b['messages_in_per_sec'] is not None]
            bytes_in = [b['bytes_in_per_sec'] for b in result['brokers'] if b['bytes_in_per_sec'] is not None]

            result['aggregated_metrics'] = {
                'avg_cpu_usage': round(sum(cpu_usages) / len(cpu_usages), 2) if cpu_usages else None,
                'max_cpu_usage': max(cpu_usages) if cpu_usages else None,
                'avg_memory_usage_percent': round(sum(memory_usages) / len(memory_usages), 2) if memory_usages else None,
                'total_messages_in_per_sec': round(sum(messages_in), 2) if messages_in else None,
                'total_bytes_in_per_sec': round(sum(bytes_in), 2) if bytes_in else None,
                'total_under_replicated_partitions': sum(
                    b['under_replicated_partitions'] or 0 for b in result['brokers']
                )
            }

        if result['critical_brokers'] > 0:
            result['status'] = 'CRITICAL'
            result['issues'].append(f"{result['critical_brokers']} brokers in CRITICAL state")
        elif result['warning_brokers'] > 0:
            result['status'] = 'WARNING'
            result['issues'].append(f"{result['warning_brokers']} brokers in WARNING state")
        elif result['error_brokers'] > 0 and result['healthy_brokers'] == 0:
            result['status'] = 'ERROR'
            result['issues'].append('All brokers have JMX collection errors')
        else:
            result['status'] = 'HEALTHY'

        logger.info(
            f"JMX collection complete: {result['healthy_brokers']} healthy, "
            f"{result['warning_brokers']} warning, {result['critical_brokers']} critical"
        )

        return result
