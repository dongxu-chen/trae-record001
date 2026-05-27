import logging
from typing import Dict, List, Any
from statistics import mean

logger = logging.getLogger(__name__)


class AutoRebalancer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        rebalance_config = config.get('checks', {}).get('auto_rebalance', {})

        self.enabled = rebalance_config.get('enabled', True)
        self.hot_topic_threshold = rebalance_config.get(
            'hot_topic_threshold_msgs_per_sec', 5000
        )
        self.hot_partition_threshold = rebalance_config.get(
            'hot_partition_threshold_percent', 30
        )
        self.cpu_usage_threshold = rebalance_config.get(
            'cpu_usage_high_threshold', 70
        )
        self.network_in_threshold = rebalance_config.get(
            'network_in_high_threshold_mbs', 50
        )
        self.bytes_in_per_partition_limit = rebalance_config.get(
            'bytes_in_per_partition_limit_mbs', 10
        )
        self.recommended_partition_growth_factor = rebalance_config.get(
            'recommended_partition_growth_factor', 1.5
        )

    def analyze_hot_topics(
        self,
        topic_partitions: Dict[str, Any],
        prometheus_data: Dict[str, Any],
        jmx_data: Dict[str, Any],
        consumer_lag: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {'status': 'DISABLED'}

        logger.info("Analyzing hot topics for auto-rebalance...")

        result = {
            'status': 'HEALTHY',
            'hot_topics': [],
            'rebalance_candidates': [],
            'scale_up_suggestions': [],
            'cluster_load_status': {},
            'issues': []
        }

        topic_metrics = prometheus_data.get('topic_metrics', {})
        topics = topic_metrics.get('topics', [])
        broker_metrics = jmx_data.get('brokers', [])

        cluster_load = self._analyze_cluster_load(broker_metrics)
        result['cluster_load_status'] = cluster_load

        for topic_data in topics:
            topic_name = topic_data.get('topic')
            msg_rate = topic_data.get('messages_in_per_sec', 0)
            bytes_rate = topic_data.get('bytes_in_per_sec', 0)
            bytes_per_msg = topic_data.get('avg_message_size', 0)

            partition_info = self._get_topic_partition_info(
                topic_name, topic_partitions
            )
            partition_count = partition_info.get('partition_count', 1)
            replication_factor = partition_info.get('replication_factor', 1)

            if partition_count == 0:
                continue

            bytes_per_partition = bytes_rate / partition_count / (1024 * 1024)
            msgs_per_partition = msg_rate / partition_count

            topic_analysis = {
                'topic': topic_name,
                'messages_in_per_sec': round(msg_rate, 2),
                'bytes_in_per_sec_mbs': round(bytes_rate / (1024 * 1024), 2),
                'avg_message_size_bytes': round(bytes_per_msg, 2),
                'partition_count': partition_count,
                'replication_factor': replication_factor,
                'msgs_per_partition': round(msgs_per_partition, 2),
                'bytes_per_partition_mbs': round(bytes_per_partition, 2),
                'is_hot_topic': False,
                'hot_reason': [],
                'recommended_partitions': None,
                'estimated_improvement': None
            }

            if msg_rate >= self.hot_topic_threshold:
                topic_analysis['is_hot_topic'] = True
                topic_analysis['hot_reason'].append(
                    f"消息流速 {msg_rate:.0f} msg/s 超过阈值 {self.hot_topic_threshold} msg/s"
                )

            if bytes_per_partition >= self.bytes_in_per_partition_limit:
                topic_analysis['is_hot_topic'] = True
                topic_analysis['hot_reason'].append(
                    f"单分区流量 {bytes_per_partition:.2f} MB/s 超过阈值 {self.bytes_in_per_partition_limit} MB/s"
                )

            if cluster_load.get('is_cpu_heavy', False):
                topic_analysis['hot_reason'].append(
                    f"集群CPU负载过高 ({cluster_load.get('avg_cpu_usage', 0)}%)"
                )

            if topic_analysis['is_hot_topic']:
                recommended = self._calculate_recommended_partitions(
                    msg_rate, bytes_rate, partition_count, cluster_load
                )
                topic_analysis['recommended_partitions'] = recommended

                if recommended > partition_count:
                    improvement = self._estimate_improvement(
                        msg_rate, bytes_rate, partition_count, recommended
                    )
                    topic_analysis['estimated_improvement'] = improvement
                    result['rebalance_candidates'].append(topic_analysis)

                    scale_suggestion = self._generate_scale_suggestion(
                        topic_name, partition_count, recommended, bytes_rate
                    )
                    result['scale_up_suggestions'].append(scale_suggestion)

                result['hot_topics'].append(topic_analysis)

        if result['hot_topics']:
            result['status'] = 'WARNING' if len(result['hot_topics']) < 3 else 'CRITICAL'
            result['issues'].append(
                f"检测到 {len(result['hot_topics'])} 个热点Topic"
            )

        return result

    def _analyze_cluster_load(
        self, broker_metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not broker_metrics:
            return {'is_cpu_heavy': False, 'is_network_heavy': False}

        cpu_usages = [
            b.get('cpu_usage', 0)
            for b in broker_metrics
            if b.get('cpu_usage') is not None
        ]
        network_ins = [
            b.get('network_in_mbs', 0)
            for b in broker_metrics
            if b.get('network_in_mbs') is not None
        ]

        avg_cpu = mean(cpu_usages) if cpu_usages else 0
        avg_network = mean(network_ins) if network_ins else 0

        return {
            'avg_cpu_usage': round(avg_cpu, 1),
            'avg_network_in_mbs': round(avg_network, 2),
            'is_cpu_heavy': avg_cpu >= self.cpu_usage_threshold,
            'is_network_heavy': avg_network >= self.network_in_threshold
        }

    def _get_topic_partition_info(
        self, topic_name: str, topic_partitions: Dict[str, Any]
    ) -> Dict[str, Any]:
        topics = topic_partitions.get('topics', [])
        for topic in topics:
            if topic.get('topic') == topic_name:
                return {
                    'partition_count': topic.get('partition_count', 1),
                    'replication_factor': topic.get('replication_factor', 1)
                }
        return {'partition_count': 1, 'replication_factor': 1}

    def _calculate_recommended_partitions(
        self,
        msg_rate: float,
        bytes_rate: float,
        current_partitions: int,
        cluster_load: Dict[str, Any]
    ) -> int:
        target_msgs_per_partition = self.hot_topic_threshold * 0.8
        partitions_for_msgs = int(msg_rate / target_msgs_per_partition) + 1

        target_bytes_per_partition = self.bytes_in_per_partition_limit * 0.8 * 1024 * 1024
        partitions_for_bytes = int(bytes_rate / target_bytes_per_partition) + 1

        base_recommended = max(partitions_for_msgs, partitions_for_bytes)

        if cluster_load.get('is_cpu_heavy', False):
            base_recommended = int(base_recommended * 1.2)

        if cluster_load.get('is_network_heavy', False):
            base_recommended = int(base_recommended * 1.1)

        growth_factor = self.recommended_partition_growth_factor
        base_recommended = int(base_recommended * growth_factor)

        recommended = max(current_partitions, base_recommended)

        return self._next_power_of_two(recommended)

    def _next_power_of_two(self, n: int) -> int:
        if n <= 1:
            return 1
        return 1 << (n - 1).bit_length()

    def _estimate_improvement(
        self,
        msg_rate: float,
        bytes_rate: float,
        current_partitions: int,
        new_partitions: int
    ) -> Dict[str, Any]:
        if current_partitions >= new_partitions:
            return {}

        current_msgs_per_partition = msg_rate / current_partitions
        new_msgs_per_partition = msg_rate / new_partitions

        current_bytes_per_partition = bytes_rate / current_partitions
        new_bytes_per_partition = bytes_rate / new_partitions

        msg_improvement = (current_msgs_per_partition - new_msgs_per_partition) / current_msgs_per_partition * 100
        bytes_improvement = (current_bytes_per_partition - new_bytes_per_partition) / current_bytes_per_partition * 100

        return {
            'current_msgs_per_partition': round(current_msgs_per_partition, 2),
            'new_msgs_per_partition': round(new_msgs_per_partition, 2),
            'current_bytes_per_partition_mbs': round(current_bytes_per_partition / (1024 * 1024), 2),
            'new_bytes_per_partition_mbs': round(new_bytes_per_partition / (1024 * 1024), 2),
            'msg_load_reduction_percent': round(msg_improvement, 1),
            'bytes_load_reduction_percent': round(bytes_improvement, 1)
        }

    def _generate_scale_suggestion(
        self,
        topic_name: str,
        current_partitions: int,
        recommended_partitions: int,
        bytes_rate: float
    ) -> Dict[str, Any]:
        return {
            'topic': topic_name,
            'current_partitions': current_partitions,
            'recommended_partitions': recommended_partitions,
            'increase_percent': round((recommended_partitions - current_partitions) / current_partitions * 100, 1),
            'estimated_impact': f"扩容到 {recommended_partitions} 个分区后，单分区负载预计降低约 "
                               f"{((1 - current_partitions/recommended_partitions) * 100):.0f}%",
            'action': f"ALTER TOPIC {topic_name} PARTITIONS {recommended_partitions}"
        }