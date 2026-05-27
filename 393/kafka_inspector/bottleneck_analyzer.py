import logging
from typing import Dict, List, Any
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class BottleneckAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = {
            'cpu_high': 70,
            'cpu_critical': 85,
            'memory_high': 70,
            'memory_critical': 85,
            'disk_high': 70,
            'disk_critical': 85,
            'network_high': 80,
            'request_handler_idle_low': 0.3,
            'produce_latency_high_ms': 100,
            'produce_latency_critical_ms': 500,
            'fetch_latency_high_ms': 200,
            'fetch_latency_critical_ms': 1000,
            'urp_threshold': 10,
            'lag_warning': 1000,
            'lag_critical': 10000
        }

    def _analyze_broker_cpu(self, jmx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        brokers = jmx_data.get('brokers', [])
        
        for broker in brokers:
            cpu_usage = broker.get('cpu_usage')
            if cpu_usage is None:
                continue
                
            if cpu_usage >= self.thresholds['cpu_critical']:
                bottlenecks.append({
                    'type': 'CPU过载',
                    'severity': 'CRITICAL',
                    'broker': broker.get('host'),
                    'value': cpu_usage,
                    'description': f"Broker {broker.get('host')} CPU使用率达到 {cpu_usage}%",
                    'impact': '可能导致消息处理延迟、请求超时、ISR收缩'
                })
            elif cpu_usage >= self.thresholds['cpu_high']:
                bottlenecks.append({
                    'type': 'CPU偏高',
                    'severity': 'WARNING',
                    'broker': broker.get('host'),
                    'value': cpu_usage,
                    'description': f"Broker {broker.get('host')} CPU使用率达到 {cpu_usage}%",
                    'impact': '可能影响吞吐量，高峰期可能出现性能下降'
                })
        
        return bottlenecks

    def _analyze_broker_memory(self, jmx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        brokers = jmx_data.get('brokers', [])
        
        for broker in brokers:
            memory_usage = broker.get('memory_usage_percent')
            if memory_usage is None:
                continue
                
            if memory_usage >= self.thresholds['memory_critical']:
                bottlenecks.append({
                    'type': '内存过载',
                    'severity': 'CRITICAL',
                    'broker': broker.get('host'),
                    'value': memory_usage,
                    'description': f"Broker {broker.get('host')} 内存使用率达到 {memory_usage}%",
                    'impact': '可能导致频繁GC、OOM异常、Broker崩溃'
                })
            elif memory_usage >= self.thresholds['memory_high']:
                bottlenecks.append({
                    'type': '内存偏高',
                    'severity': 'WARNING',
                    'broker': broker.get('host'),
                    'value': memory_usage,
                    'description': f"Broker {broker.get('host')} 内存使用率达到 {memory_usage}%",
                    'impact': 'GC压力增大，可能影响性能'
                })
        
        return bottlenecks

    def _analyze_disk_usage(self, prom_data: Dict[str, Any], jmx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        disk_data = prom_data.get('disk_usage', {})
        for broker in disk_data.get('brokers', []):
            usage = broker.get('estimated_usage_percent')
            if usage is None:
                continue
                
            if usage >= self.thresholds['disk_critical']:
                bottlenecks.append({
                    'type': '磁盘空间不足',
                    'severity': 'CRITICAL',
                    'broker': broker.get('broker_id'),
                    'value': usage,
                    'description': f"Broker {broker.get('broker_id')} 磁盘使用率达到 {usage}%",
                    'impact': '可能导致消息写入失败、数据丢失'
                })
            elif usage >= self.thresholds['disk_high']:
                bottlenecks.append({
                    'type': '磁盘空间紧张',
                    'severity': 'WARNING',
                    'broker': broker.get('broker_id'),
                    'value': usage,
                    'description': f"Broker {broker.get('broker_id')} 磁盘使用率达到 {usage}%",
                    'impact': '需要考虑清理旧数据或扩容存储'
                })
        
        return bottlenecks

    def _analyze_request_handler(self, jmx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        brokers = jmx_data.get('brokers', [])
        
        for broker in brokers:
            idle_percent = broker.get('request_handler_avg_idle_percent')
            if idle_percent is None:
                continue
                
            if idle_percent < self.thresholds['request_handler_idle_low']:
                bottlenecks.append({
                    'type': '请求处理线程不足',
                    'severity': 'WARNING' if idle_percent > 0.1 else 'CRITICAL',
                    'broker': broker.get('host'),
                    'value': idle_percent,
                    'description': f"Broker {broker.get('host')} 请求处理线程空闲率仅为 {idle_percent:.2%}",
                    'impact': '请求排队增加，延迟上升，可能导致请求处理超时'
                })
        
        return bottlenecks

    def _analyze_latency(self, jmx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        brokers = jmx_data.get('brokers', [])
        
        for broker in brokers:
            produce_latency = broker.get('produce_request_p99_latency_ms')
            if produce_latency is not None:
                if produce_latency >= self.thresholds['produce_latency_critical_ms']:
                    bottlenecks.append({
                        'type': '生产请求延迟过高',
                        'severity': 'CRITICAL',
                        'broker': broker.get('host'),
                        'value': produce_latency,
                        'description': f"Broker {broker.get('host')} 生产请求P99延迟达到 {produce_latency}ms",
                        'impact': '生产者客户端延迟增加，可能导致生产端超时'
                    })
                elif produce_latency >= self.thresholds['produce_latency_high_ms']:
                    bottlenecks.append({
                        'type': '生产请求延迟偏高',
                        'severity': 'WARNING',
                        'broker': broker.get('host'),
                        'value': produce_latency,
                        'description': f"Broker {broker.get('host')} 生产请求P99延迟达到 {produce_latency}ms",
                        'impact': '建议检查磁盘IO或网络状况'
                    })
            
            fetch_latency = broker.get('fetch_request_p99_latency_ms')
            if fetch_latency is not None:
                if fetch_latency >= self.thresholds['fetch_latency_critical_ms']:
                    bottlenecks.append({
                        'type': '消费请求延迟过高',
                        'severity': 'CRITICAL',
                        'broker': broker.get('host'),
                        'value': fetch_latency,
                        'description': f"Broker {broker.get('host')} 消费请求P99延迟达到 {fetch_latency}ms",
                        'impact': '消费端延迟增加，可能导致消费积压'
                    })
                elif fetch_latency >= self.thresholds['fetch_latency_high_ms']:
                    bottlenecks.append({
                        'type': '消费请求延迟偏高',
                        'severity': 'WARNING',
                        'broker': broker.get('host'),
                        'value': fetch_latency,
                        'description': f"Broker {broker.get('host')} 消费请求P99延迟达到 {fetch_latency}ms",
                        'impact': '建议检查磁盘IO或网络状况'
                    })
        
        return bottlenecks

    def _analyze_under_replicated_partitions(self, kafka_admin: Dict[str, Any], prom_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        isr_status = kafka_admin.get('isr_status', {})
        urp_count = isr_status.get('under_replicated_partitions', 0)
        
        if urp_count >= self.thresholds['urp_threshold']:
            bottlenecks.append({
                'type': '大量副本不足分区',
                'severity': 'CRITICAL',
                'value': urp_count,
                'description': f"集群存在 {urp_count} 个副本不足的分区",
                'impact': '数据可靠性降低，Broker故障可能导致数据丢失'
            })
        elif urp_count > 0:
            bottlenecks.append({
                'type': '存在副本不足分区',
                'severity': 'WARNING',
                'value': urp_count,
                'description': f"集群存在 {urp_count} 个副本不足的分区",
                'impact': '可能是临时网络波动或Broker负载过高导致'
            })
        
        return bottlenecks

    def _analyze_consumer_lag(self, kafka_admin: Dict[str, Any], prom_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        consumer_lag = kafka_admin.get('consumer_lag', {})
        groups = consumer_lag.get('groups', [])
        
        critical_groups = [g for g in groups if g.get('status') == 'CRITICAL']
        warning_groups = [g for g in groups if g.get('status') == 'WARNING']
        
        if critical_groups:
            for group in critical_groups[:3]:
                bottlenecks.append({
                    'type': '消费组严重积压',
                    'severity': 'CRITICAL',
                    'group': group.get('group_id'),
                    'value': group.get('total_lag'),
                    'description': f"消费组 {group.get('group_id')} 积压消息数达到 {group.get('total_lag'):,}",
                    'impact': '数据处理延迟增大，实时性受影响'
                })
        
        if warning_groups:
            if not critical_groups:
                for group in warning_groups[:2]:
                    bottlenecks.append({
                        'type': '消费组积压',
                        'severity': 'WARNING',
                        'group': group.get('group_id'),
                        'value': group.get('total_lag'),
                        'description': f"消费组 {group.get('group_id')} 积压消息数达到 {group.get('total_lag'):,}",
                        'impact': '需要关注消费速度是否满足要求'
                    })
        
        return bottlenecks

    def _analyze_partition_imbalance(self, kafka_admin: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        topic_partitions = kafka_admin.get('topic_partitions', {})
        distribution = topic_partitions.get('broker_partition_distribution', {})
        
        if not distribution:
            return bottlenecks
        
        partition_counts = list(distribution.values())
        if len(partition_counts) < 2:
            return bottlenecks
        
        avg_partitions = mean(partition_counts)
        max_partitions = max(partition_counts)
        min_partitions = min(partition_counts)
        
        imbalance_ratio = max_partitions / avg_partitions if avg_partitions > 0 else 1
        
        if imbalance_ratio > 1.5:
            bottlenecks.append({
                'type': '分区分布不均',
                'severity': 'WARNING',
                'value': imbalance_ratio,
                'description': f"分区分布不平衡，最多{max_partitions} vs 最少{min_partitions}，比率{imbalance_ratio:.2f}",
                'impact': '导致部分Broker负载过高，资源利用不均'
            })
        
        return bottlenecks

    def _analyze_broker_availability(self, kafka_admin: Dict[str, Any]) -> List[Dict[str, Any]]:
        bottlenecks = []
        
        broker_health = kafka_admin.get('broker_health', {})
        offline_count = broker_health.get('offline_brokers', 0)
        total_count = broker_health.get('total_brokers', 0)
        
        if offline_count > 0:
            severity = 'CRITICAL' if offline_count >= total_count / 2 else 'WARNING'
            bottlenecks.append({
                'type': 'Broker离线',
                'severity': severity,
                'value': offline_count,
                'description': f"{offline_count}/{total_count} 个Broker离线",
                'impact': '集群可用性降低，数据冗余度下降'
            })
        
        return bottlenecks

    def analyze(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Starting bottleneck analysis...")
        
        kafka_admin = all_results.get('kafka_admin', {})
        jmx_data = all_results.get('jmx', {})
        prom_data = all_results.get('prometheus', {})
        
        bottlenecks = []
        
        bottlenecks.extend(self._analyze_broker_availability(kafka_admin))
        bottlenecks.extend(self._analyze_broker_cpu(jmx_data))
        bottlenecks.extend(self._analyze_broker_memory(jmx_data))
        bottlenecks.extend(self._analyze_disk_usage(prom_data, jmx_data))
        bottlenecks.extend(self._analyze_request_handler(jmx_data))
        bottlenecks.extend(self._analyze_latency(jmx_data))
        bottlenecks.extend(self._analyze_under_replicated_partitions(kafka_admin, prom_data))
        bottlenecks.extend(self._analyze_consumer_lag(kafka_admin, prom_data))
        bottlenecks.extend(self._analyze_partition_imbalance(kafka_admin))
        
        critical_count = len([b for b in bottlenecks if b['severity'] == 'CRITICAL'])
        warning_count = len([b for b in bottlenecks if b['severity'] == 'WARNING'])
        
        if critical_count > 0:
            overall_rating = 'CRITICAL'
        elif warning_count > 0:
            overall_rating = 'WARNING'
        else:
            overall_rating = 'HEALTHY'
        
        analysis_result = {
            'overall_rating': overall_rating,
            'bottleneck_count': len(bottlenecks),
            'critical_count': critical_count,
            'warning_count': warning_count,
            'bottlenecks': bottlenecks,
            'recommendations': self._generate_recommendations(bottlenecks)
        }
        
        logger.info(
            f"Bottleneck analysis complete: {critical_count} critical, "
            f"{warning_count} warning, overall rating: {overall_rating}"
        )
        
        return analysis_result

    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        recommendations = []
        
        has_cpu_issue = any('CPU' in b.get('type', '') for b in bottlenecks)
        has_memory_issue = any('内存' in b.get('type', '') for b in bottlenecks)
        has_disk_issue = any('磁盘' in b.get('type', '') for b in bottlenecks)
        has_urp_issue = any('副本' in b.get('type', '') for b in bottlenecks)
        has_lag_issue = any('消费组' in b.get('type', '') for b in bottlenecks)
        has_latency_issue = any('延迟' in b.get('type', '') for b in bottlenecks)
        has_imbalance_issue = any('分布不均' in b.get('type', '') for b in bottlenecks)
        has_thread_issue = any('线程' in b.get('type', '') for b in bottlenecks)
        
        if has_cpu_issue:
            recommendations.append('CPU使用率过高：考虑扩容Broker数量、优化消费逻辑、检查是否有大量计算型消息处理')
        
        if has_memory_issue:
            recommendations.append('内存使用率过高：检查JVM堆内存配置是否合理，考虑增加Broker内存或减少分区数量')
        
        if has_disk_issue:
            recommendations.append('磁盘空间紧张：调整消息保留时间(retention.ms)、清理无用Topic、考虑扩容存储')
        
        if has_thread_issue:
            recommendations.append('请求处理线程紧张：增加num.network.threads和num.io.threads配置')
        
        if has_latency_issue:
            recommendations.append('请求延迟偏高：检查磁盘IO性能、网络带宽，考虑使用SSD或优化batch.size配置')
        
        if has_urp_issue:
            recommendations.append('副本不足：检查Broker间网络连通性，确保所有Broker正常运行，考虑增加副本数')
        
        if has_lag_issue:
            recommendations.append('消费积压：增加消费组的消费者实例数量、优化消费逻辑、检查是否有消费阻塞')
        
        if has_imbalance_issue:
            recommendations.append('分区分布不均：使用kafka-reassign-partitions.sh进行分区重分配，平衡负载')
        
        if not bottlenecks:
            recommendations.append('集群运行状况良好，建议继续保持定期巡检')
        
        return recommendations
