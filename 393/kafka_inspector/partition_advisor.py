import logging
from typing import Dict, List, Any
from collections import defaultdict
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class PartitionAdvisor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.check_config = config.get('checks', {})

    def _analyze_partition_distribution(self, topic_partitions: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Analyzing partition distribution...")
        
        distribution = topic_partitions.get('broker_partition_distribution', {})
        topics = topic_partitions.get('topics', [])
        
        result = {
            'imbalanced_brokers': [],
            'imbalanced_topics': [],
            'overall_imbalance_score': 0.0
        }
        
        if not distribution:
            return result
        
        partition_counts = list(distribution.values())
        if len(partition_counts) < 2:
            return result
        
        avg_partitions = mean(partition_counts)
        max_partitions = max(partition_counts)
        min_partitions = min(partition_counts)
        
        imbalance_ratio = max_partitions / avg_partitions if avg_partitions > 0 else 1
        result['overall_imbalance_score'] = round(imbalance_ratio, 2)
        
        for broker_id, count in distribution.items():
            deviation = (count - avg_partitions) / avg_partitions * 100 if avg_partitions > 0 else 0
            if abs(deviation) > 20:
                result['imbalanced_brokers'].append({
                    'broker_id': broker_id,
                    'partition_count': count,
                    'deviation_percent': round(deviation, 1)
                })
        
        for topic in topics:
            topic_name = topic.get('topic')
            partitions = topic.get('partitions', [])
            
            if not partitions:
                continue
            
            leader_dist = {}
            for p in partitions:
                leader = p.get('leader')
                if leader is not None:
                    leader_dist[leader] = leader_dist.get(leader, 0) + 1
            
            if leader_dist:
                leader_counts = list(leader_dist.values())
                avg_leaders = mean(leader_counts)
                max_leaders = max(leader_counts)
                leader_imbalance = max_leaders / avg_leaders if avg_leaders > 0 else 1
                
                if leader_imbalance > 1.5:
                    result['imbalanced_topics'].append({
                        'topic': topic_name,
                        'partition_count': topic.get('partition_count'),
                        'leader_imbalance_ratio': round(leader_imbalance, 2)
                    })
        
        return result

    def _calculate_optimal_partitions(self, topic_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        msg_rate = metrics.get('messages_in_per_sec', 0)
        avg_msg_size = 1024
        
        throughput = msg_rate * avg_msg_size
        
        max_throughput_per_partition = 10 * 1024 * 1024
        partitions_for_throughput = max(1, int(throughput / max_throughput_per_partition) + 1)
        
        target_latency = 100
        partitions_for_latency = max(1, int(msg_rate / 1000) + 1)
        
        optimal_partitions = max(partitions_for_throughput, partitions_for_latency)
        
        return {
            'topic': topic_name,
            'current_partitions': metrics.get('current_partitions', 0),
            'recommended_partitions': optimal_partitions,
            'message_rate': msg_rate,
            'estimated_throughput_mbs': round(throughput / (1024 * 1024), 2)
        }

    def _generate_partition_reassignment_plan(
        self, 
        topic_name: str, 
        current_partitions: List[Dict[str, Any]],
        available_brokers: List[int],
        broker_rack_map: Dict[int, str] = None
    ) -> Dict[str, Any]:
        logger.info(f"Generating reassignment plan for {topic_name}...")
        
        if not available_brokers or not current_partitions:
            return None

        rack_config = self.check_config.get('topic_partition', {}).get('rack_aware', {})
        rack_aware = rack_config.get('enabled', False) and broker_rack_map is not None
        
        broker_load = {b: 0 for b in available_brokers}
        
        if rack_aware:
            rack_brokers = defaultdict(list)
            for broker_id in available_brokers:
                rack = broker_rack_map.get(broker_id, f'rack-{broker_id}')
                rack_brokers[rack].append(broker_id)
            
            rack_load = {rack: 0 for rack in rack_brokers}
        else:
            rack_brokers = {}
            rack_load = {}
        
        reassignment = []
        sorted_partitions = sorted(current_partitions, key=lambda x: x.get('partition', 0))
        
        for partition in sorted_partitions:
            partition_id = partition.get('partition')
            current_replicas = partition.get('replicas', [])
            new_replicas = []
            
            if rack_aware and rack_brokers:
                sorted_racks = sorted(rack_load.keys(), key=lambda r: rack_load[r])
                
                for rack in sorted_racks:
                    brokers_in_rack = sorted(
                        rack_brokers[rack], key=lambda b: broker_load[b]
                    )
                    for broker in brokers_in_rack:
                        if broker not in new_replicas:
                            new_replicas.append(broker)
                            broker_load[broker] += 1
                            rack_load[rack] += 1
                            break
                    
                    if len(new_replicas) >= len(current_replicas):
                        break
                
                while len(new_replicas) < len(current_replicas):
                    sorted_brokers = sorted(
                        available_brokers, key=lambda b: broker_load[b]
                    )
                    for broker in sorted_brokers:
                        if broker not in new_replicas:
                            new_replicas.append(broker)
                            broker_load[broker] += 1
                            rack = broker_rack_map.get(broker, 'unknown')
                            if rack in rack_load:
                                rack_load[rack] += 1
                            break
                    else:
                        break
            else:
                sorted_brokers = sorted(broker_load.keys(), key=lambda b: broker_load[b])
                for i in range(min(len(current_replicas), len(sorted_brokers))):
                    new_broker = sorted_brokers[i]
                    new_replicas.append(new_broker)
                    broker_load[new_broker] += 1
            
            reassignment.append({
                'partition': partition_id,
                'current_replicas': current_replicas,
                'proposed_replicas': new_replicas,
                'needs_reassignment': current_replicas != new_replicas
            })
        
        changes_count = sum(1 for r in reassignment if r['needs_reassignment'])
        
        return {
            'topic': topic_name,
            'partitions': reassignment,
            'total_changes_needed': changes_count,
            'broker_load_after': broker_load,
            'rack_aware': rack_aware
        }

    def _get_rebalance_suggestions(
        self, 
        distribution: Dict[str, Any],
        imbalance_analysis: Dict[str, Any]
    ) -> List[str]:
        suggestions = []
        
        imbalance_score = imbalance_analysis.get('overall_imbalance_score', 0)
        if imbalance_score > 1.3:
            suggestions.append(
                f"集群分区分布不平衡，不平衡系数为 {imbalance_score}，建议进行分区重分配"
            )
        
        imbalanced_brokers = imbalance_analysis.get('imbalanced_brokers', [])
        if imbalanced_brokers:
            overloaded = [b for b in imbalanced_brokers if b['deviation_percent'] > 0]
            underloaded = [b for b in imbalanced_brokers if b['deviation_percent'] < 0]
            
            if overloaded:
                overload_str = ', '.join([
                    f"Broker{b['broker_id']}({b['deviation_percent']:.1f}%)" 
                    for b in overloaded[:3]
                ])
                suggestions.append(f"以下Broker分区数过多: {overload_str}")
            if underloaded:
                underload_str = ', '.join([
                    f"Broker{b['broker_id']}({b['deviation_percent']:.1f}%)" 
                    for b in underloaded[:3]
                ])
                suggestions.append(f"以下Broker分区数过少: {underload_str}")
        
        return suggestions

    def _get_topic_optimization_suggestions(
        self,
        topics: List[Dict[str, Any]],
        topic_metrics: Dict[str, Any],
        imbalance_analysis: Dict[str, Any]
    ) -> List[str]:
        suggestions = []
        
        imbalanced_topics = imbalance_analysis.get('imbalanced_topics', [])
        for topic in imbalanced_topics[:5]:
            suggestions.append(
                f"Topic [{topic['topic']}] Leader分布不平衡，建议重新选举或重分配分区"
            )
        
        high_traffic_topics = sorted(
            topic_metrics.get('topics', []),
            key=lambda x: x.get('messages_in_per_sec', 0),
            reverse=True
        )[:5]
        
        for topic in high_traffic_topics:
            msg_rate = topic.get('messages_in_per_sec', 0)
            if msg_rate > 10000:
                suggestions.append(
                    f"Topic [{topic['topic']}] 消息流速较高 ({msg_rate:.0f} msg/s)，建议关注分区数是否足够"
                )
        
        for topic in topics:
            partition_count = topic.get('partition_count', 0)
            replication_factor = topic.get('replication_factor', 0)
            
            if replication_factor == 1:
                suggestions.append(
                    f"Topic [{topic['topic']}] 副本数为1，存在数据丢失风险，建议增加副本数"
                )
            
            if partition_count == 1:
                suggestions.append(
                    f"Topic [{topic['topic']}] 只有1个分区，无法水平扩展消费能力"
                )
        
        return suggestions

    def _get_scaling_suggestions(
        self,
        broker_health: Dict[str, Any],
        jmx_metrics: Dict[str, Any],
        partition_metrics: Dict[str, Any]
    ) -> List[str]:
        suggestions = []
        
        total_brokers = broker_health.get('total_brokers', 0)
        total_partitions = partition_metrics.get('total_partitions', 0)
        
        if total_brokers > 0:
            avg_partitions_per_broker = total_partitions / total_brokers
            max_recommended = self.check_config.get('topic_partition', {}).get('max_partitions_per_broker', 1000)
            
            if avg_partitions_per_broker > max_recommended * 0.8:
                suggestions.append(
                    f"平均每Broker分区数达到 {avg_partitions_per_broker:.0f}，接近上限 {max_recommended}，建议扩容Broker"
                )
        
        aggregated = jmx_metrics.get('aggregated_metrics', {})
        avg_cpu = aggregated.get('avg_cpu_usage', 0)
        if avg_cpu and avg_cpu > 60:
            suggestions.append(
                f"集群平均CPU使用率为 {avg_cpu}%，负载较高，考虑增加Broker数量或优化消息处理"
            )
        
        return suggestions

    def _get_rack_aware_suggestions(
        self,
        broker_health: Dict[str, Any],
        rack_distribution: Dict[str, Any]
    ) -> List[str]:
        suggestions = []

        if not rack_distribution or not rack_distribution.get('enabled'):
            return suggestions

        racks = rack_distribution.get('racks', {})
        single_rack_topics = rack_distribution.get('single_rack_topics', [])
        cross_rack_score = rack_distribution.get('cross_rack_replication_score', 0)

        if len(racks) < 2:
            suggestions.append(
                "集群仅在一个机架上运行，建议部署到多机架环境以提升容灾能力"
            )

        if single_rack_topics:
            suggestions.append(
                f"发现 {len(single_rack_topics)} 个Topic的所有副本在同一机架上，"
                f"存在单机架故障导致数据丢失的风险"
            )
            for topic_info in single_rack_topics[:5]:
                suggestions.append(
                    f"  - Topic [{topic_info['topic']}] 所有副本在机架 {topic_info['rack']}"
                )

        if cross_rack_score < 80 and len(racks) >= 2:
            suggestions.append(
                f"跨机架副本分布率仅为 {cross_rack_score}%，建议重分配分区以提升机架容灾能力"
            )

        if len(racks) >= 2:
            rack_broker_counts = {rack: len(brokers) for rack, brokers in racks.items()}
            if len(set(rack_broker_counts.values())) > 1:
                suggestions.append("各机架Broker数量不均，建议均衡机架间Broker分布")

        return suggestions

    def generate_suggestions(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Generating partition optimization suggestions...")
        
        kafka_admin = all_results.get('kafka_admin', {})
        prom_data = all_results.get('prometheus', {})
        jmx_data = all_results.get('jmx', {})
        
        topic_partitions = kafka_admin.get('topic_partitions', {})
        broker_health = kafka_admin.get('broker_health', {})
        topic_metrics = prom_data.get('topic_metrics', {})
        rack_distribution = kafka_admin.get('rack_distribution', {})
        
        suggestions = []
        
        imbalance_analysis = self._analyze_partition_distribution(topic_partitions)
        
        suggestions.extend(self._get_rebalance_suggestions(
            topic_partitions.get('broker_partition_distribution', {}),
            imbalance_analysis
        ))
        
        suggestions.extend(self._get_topic_optimization_suggestions(
            topic_partitions.get('topics', []),
            topic_metrics,
            imbalance_analysis
        ))
        
        suggestions.extend(self._get_scaling_suggestions(
            broker_health,
            jmx_data,
            topic_partitions
        ))

        suggestions.extend(self._get_rack_aware_suggestions(
            broker_health,
            rack_distribution
        ))
        
        broker_ids = [b.get('id') for b in broker_health.get('brokers', []) if b.get('status') == 'ONLINE']
        
        broker_rack_map = {}
        if rack_distribution and rack_distribution.get('enabled'):
            broker_rack_map = rack_distribution.get('broker_rack_map', {})

        reassignment_plans = []
        
        for topic in imbalance_analysis.get('imbalanced_topics', [])[:3]:
            topic_name = topic.get('topic')
            topic_data = next(
                (t for t in topic_partitions.get('topics', []) if t.get('topic') == topic_name),
                None
            )
            
            if topic_data:
                plan = self._generate_partition_reassignment_plan(
                    topic_name,
                    topic_data.get('partitions', []),
                    broker_ids,
                    broker_rack_map if broker_rack_map else None
                )
                if plan:
                    reassignment_plans.append(plan)

        if rack_distribution and rack_distribution.get('enabled') and rack_distribution.get('single_rack_topics'):
            for topic_info in rack_distribution['single_rack_topics'][:3]:
                topic_name = topic_info.get('topic')
                topic_data = next(
                    (t for t in topic_partitions.get('topics', []) if t.get('topic') == topic_name),
                    None
                )
                if topic_data:
                    plan = self._generate_partition_reassignment_plan(
                        topic_name,
                        topic_data.get('partitions', []),
                        broker_ids,
                        broker_rack_map if broker_rack_map else None
                    )
                    if plan:
                        reassignment_plans.append(plan)
        
        suggestions.extend([
            "最佳实践建议：",
            "- Topic分区数建议设置为Broker数量的整数倍",
            "- 副本数建议设置为3（至少2个副本保证数据可靠性）",
            "- 单分区吞吐量建议不超过10MB/s",
            "- 定期执行分区重分配以平衡负载",
            "- 新Topic创建时考虑预估的消息流速来确定分区数",
            "- 多机架部署时确保分区副本跨机架分布以提升容灾能力"
        ])
        
        result = {
            'imbalance_analysis': imbalance_analysis,
            'imbalanced_topics': imbalance_analysis.get('imbalanced_topics', []),
            'imbalanced_brokers': imbalance_analysis.get('imbalanced_brokers', []),
            'reassignment_plans': reassignment_plans,
            'rack_distribution': rack_distribution,
            'suggestions': suggestions
        }
        
        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        
        return result

    def suggest_partition_count(
        self, 
        expected_msg_rate: float, 
        expected_msg_size: int = 1024,
        num_consumers: int = 1
    ) -> Dict[str, Any]:
        max_msg_per_partition = 10000
        max_throughput_per_partition = 10 * 1024 * 1024
        
        throughput = expected_msg_rate * expected_msg_size
        partitions_for_throughput = max(1, int(throughput / max_throughput_per_partition) + 1)
        partitions_for_rate = max(1, int(expected_msg_rate / max_msg_per_partition) + 1)
        partitions_for_consumers = max(1, num_consumers)
        
        recommended_partitions = max(partitions_for_throughput, partitions_for_rate, partitions_for_consumers)
        
        recommended_partitions = self._next_power_of_two(recommended_partitions)
        
        return {
            'expected_msg_rate': expected_msg_rate,
            'expected_msg_size': expected_msg_size,
            'num_consumers': num_consumers,
            'recommended_partitions': recommended_partitions,
            'recommended_replicas': 3,
            'estimated_max_throughput_mbs': round(
                recommended_partitions * max_throughput_per_partition / (1024 * 1024), 2
            )
        }

    def _next_power_of_two(self, n: int) -> int:
        if n <= 1:
            return 1
        return 1 << (n - 1).bit_length()
