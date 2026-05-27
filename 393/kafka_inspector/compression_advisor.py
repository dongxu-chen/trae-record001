import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class CompressionAdvisor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        compression_config = config.get('checks', {}).get('compression', {})

        self.enabled = compression_config.get('enabled', True)
        self.min_topic_size_gb = compression_config.get(
            'min_topic_size_gb', 10
        )
        self.min_compression_savings_percent = compression_config.get(
            'min_compression_savings_percent', 20
        )
        self.recommended_compression_types = compression_config.get(
            'recommended_compression_types', ['zstd', 'lz4', 'snappy', 'gzip']
        )

        self.compression_profiles = {
            'zstd': {
                'description': '高压缩率，CPU开销适中（推荐）',
                'compression_ratio_range': (2.5, 5.0),
                'cpu_usage': 'medium',
                'latency_ms': 5
            },
            'lz4': {
                'description': '低延迟，中等压缩率',
                'compression_ratio_range': (2.0, 3.5),
                'cpu_usage': 'low',
                'latency_ms': 2
            },
            'snappy': {
                'description': '快速压缩，低CPU开销',
                'compression_ratio_range': (1.5, 3.0),
                'cpu_usage': 'low',
                'latency_ms': 3
            },
            'gzip': {
                'description': '最高压缩率，高CPU开销',
                'compression_ratio_range': (3.0, 6.0),
                'cpu_usage': 'high',
                'latency_ms': 10
            },
            'none': {
                'description': '不压缩',
                'compression_ratio_range': (1.0, 1.0),
                'cpu_usage': 'none',
                'latency_ms': 0
            }
        }

    def analyze_compression_opportunities(
        self,
        topic_partitions: Dict[str, Any],
        prometheus_data: Dict[str, Any],
        jmx_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {'status': 'DISABLED'}

        logger.info("Analyzing compression opportunities...")

        result = {
            'status': 'HEALTHY',
            'topics_analyzed': 0,
            'compression_candidates': [],
            'uncompressed_topics': [],
            'already_compressed_topics': [],
            'total_potential_savings_gb': 0,
            'cluster_compression_summary': {},
            'issues': []
        }

        topic_metrics = prometheus_data.get('topic_metrics', {})
        topics = topic_metrics.get('topics', [])
        result['topics_analyzed'] = len(topics)

        total_current_size = 0
        total_estimated_savings = 0

        for topic_data in topics:
            topic_name = topic_data.get('topic')
            bytes_rate = topic_data.get('bytes_in_per_sec', 0)
            avg_msg_size = topic_data.get('avg_message_size', 0)
            retention_days = topic_data.get('retention_days', 7)
            current_compression = topic_data.get('compression_type', 'none')

            if bytes_rate == 0:
                continue

            partition_info = self._get_topic_partition_info(
                topic_name, topic_partitions
            )
            partition_count = partition_info.get('partition_count', 1)
            replication_factor = partition_info.get('replication_factor', 1)

            estimated_size_gb = self._estimate_topic_size(
                bytes_rate, retention_days, replication_factor
            )
            total_current_size += estimated_size_gb

            topic_analysis = {
                'topic': topic_name,
                'bytes_in_per_sec': round(bytes_rate, 2),
                'avg_message_size_bytes': round(avg_msg_size, 2),
                'retention_days': retention_days,
                'partition_count': partition_count,
                'replication_factor': replication_factor,
                'current_compression': current_compression,
                'estimated_size_gb': round(estimated_size_gb, 2)
            }

            if current_compression == 'none' or current_compression is None:
                result['uncompressed_topics'].append(topic_name)

                if estimated_size_gb >= self.min_topic_size_gb:
                    recommendation = self._generate_compression_recommendation(
                        bytes_rate, avg_msg_size, estimated_size_gb, jmx_data
                    )
                    topic_analysis.update(recommendation)

                    if recommendation['estimated_savings_gb'] > 0:
                        total_estimated_savings += recommendation['estimated_savings_gb']
                        result['compression_candidates'].append(topic_analysis)
            else:
                topic_analysis['compression_effectiveness'] = self._evaluate_compression_effectiveness(
                    current_compression, bytes_rate, avg_msg_size
                )
                result['already_compressed_topics'].append(topic_analysis)

        result['total_potential_savings_gb'] = round(total_estimated_savings, 2)

        result['cluster_compression_summary'] = {
            'total_topics': len(topics),
            'uncompressed_topics_count': len(result['uncompressed_topics']),
            'compressed_topics_count': len(result['already_compressed_topics']),
            'candidates_count': len(result['compression_candidates']),
            'total_estimated_size_gb': round(total_current_size, 2),
            'total_potential_savings_gb': round(total_estimated_savings, 2),
            'compression_adoption_rate': round(
                len(result['already_compressed_topics']) / max(1, len(topics)) * 100, 1
            )
        }

        if result['compression_candidates']:
            result['status'] = 'WARNING'
            result['issues'].append(
                f"发现 {len(result['compression_candidates'])} 个Topic可以通过压缩节省磁盘空间"
            )
            savings_percent = total_estimated_savings / max(1, total_current_size) * 100
            if savings_percent >= self.min_compression_savings_percent:
                result['issues'].append(
                    f"压缩可节省约 {total_estimated_savings:.1f} GB 磁盘空间 ({savings_percent:.1f}%)"
                )

        return result

    def _estimate_topic_size(
        self,
        bytes_rate: float,
        retention_days: int,
        replication_factor: int
    ) -> float:
        bytes_per_day = bytes_rate * 86400
        total_bytes = bytes_per_day * retention_days * replication_factor
        return total_bytes / (1024 * 1024 * 1024)

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

    def _generate_compression_recommendation(
        self,
        bytes_rate: float,
        avg_msg_size: float,
        estimated_size_gb: float,
        jmx_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        broker_metrics = jmx_data.get('brokers', [])

        avg_cpu = 0
        if broker_metrics:
            cpu_values = [b.get('cpu_usage', 0) for b in broker_metrics if b.get('cpu_usage')]
            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)

        if avg_cpu >= 70:
            recommended_type = 'lz4'
            reason = 'CPU负载较高，推荐低CPU开销的LZ4压缩'
        elif avg_msg_size >= 1024:
            recommended_type = 'zstd'
            reason = '消息体较大，推荐高压缩率的ZSTD压缩'
        elif bytes_rate >= 100 * 1024 * 1024:
            recommended_type = 'snappy'
            reason = '高流量场景，推荐快速压缩的Snappy'
        else:
            recommended_type = 'zstd'
            reason = '推荐默认使用ZSTD，平衡压缩率和CPU开销'

        profile = self.compression_profiles.get(recommended_type, {})
        ratio_min, ratio_max = profile.get('compression_ratio_range', (2.0, 3.0))
        avg_ratio = (ratio_min + ratio_max) / 2

        compressed_size_gb = estimated_size_gb / avg_ratio
        savings_gb = estimated_size_gb - compressed_size_gb

        return {
            'recommended_compression': recommended_type,
            'recommendation_reason': reason,
            'compression_profile': profile,
            'estimated_compressed_size_gb': round(compressed_size_gb, 2),
            'estimated_savings_gb': round(savings_gb, 2),
            'savings_percent': round(savings_gb / max(1, estimated_size_gb) * 100, 1),
            'current_cluster_cpu_percent': round(avg_cpu, 1)
        }

    def _evaluate_compression_effectiveness(
        self,
        compression_type: str,
        bytes_rate: float,
        avg_msg_size: float
    ) -> Dict[str, Any]:
        profile = self.compression_profiles.get(compression_type, {})
        ratio_min, ratio_max = profile.get('compression_ratio_range', (1.0, 1.0))
        avg_ratio = (ratio_min + ratio_max) / 2

        effectiveness = 'GOOD'
        notes = []

        if compression_type == 'gzip' and bytes_rate > 50 * 1024 * 1024:
            effectiveness = 'SUBOPTIMAL'
            notes.append('高流量场景下使用GZIP可能导致CPU过高')

        if compression_type == 'snappy' and avg_msg_size > 4096:
            effectiveness = 'SUBOPTIMAL'
            notes.append('大消息体场景下Snappy压缩率不如ZSTD')

        return {
            'effectiveness': effectiveness,
            'compression_ratio_range': f"{ratio_min}-{ratio_max}x",
            'notes': notes
        }

    def get_compression_config_suggestions(
        self,
        analysis_result: Dict[str, Any]
    ) -> List[str]:
        suggestions = []

        summary = analysis_result.get('cluster_compression_summary', {})
        if summary.get('uncompressed_topics_count', 0) > 0:
            suggestions.append(
                f"集群中有 {summary.get('uncompressed_topics_count', 0)} 个Topic未启用压缩，"
                f"建议为大流量Topic启用压缩"
            )

        candidates = analysis_result.get('compression_candidates', [])
        for candidate in candidates[:5]:
            suggestions.append(
                f"Topic [{candidate['topic']}]: 建议启用 {candidate['recommended_compression'].upper()} 压缩，"
                f"预计节省 {candidate['estimated_savings_gb']:.1f} GB ({candidate['savings_percent']:.1f}%)"
            )
            suggestions.append(f"  原因: {candidate['recommendation_reason']}")
            suggestions.append(
                f"  配置: compression.type={candidate['recommended_compression']}"
            )

        for topic_info in analysis_result.get('already_compressed_topics', []):
            effectiveness = topic_info.get('compression_effectiveness', {})
            if effectiveness.get('effectiveness') == 'SUBOPTIMAL':
                for note in effectiveness.get('notes', []):
                    suggestions.append(
                        f"Topic [{topic_info['topic']}] (当前: {topic_info['current_compression']}): {note}"
                    )

        if not suggestions:
            suggestions.append('所有Topic的压缩配置合理，无需调整')

        return suggestions