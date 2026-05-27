import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConsumerLagAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        lag_config = config.get('checks', {}).get('lag', {})
        analysis_config = lag_config.get('delay_analysis', {})
        
        self.enabled = analysis_config.get('enabled', True)
        self.slow_consumer_threshold = analysis_config.get(
            'slow_consumer_threshold', 0.5
        )
        self.lag_growth_rate_threshold = analysis_config.get(
            'lag_growth_rate_threshold', 100
        )
        self.eta_critical_hours = analysis_config.get(
            'eta_critical_hours', 24
        )
        self.eta_warning_hours = analysis_config.get(
            'eta_warning_hours', 72
        )
        self.history_file = analysis_config.get(
            'history_file', './data/consumer_lag_history.json'
        )

    def analyze_lag_trend(
        self,
        current_lag_data: Dict[str, Any],
        prometheus_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {'status': 'DISABLED'}

        logger.info("Analyzing consumer lag trends...")

        result = {
            'status': 'HEALTHY',
            'total_groups_analyzed': 0,
            'slow_consumers': [],
            'growing_lag_groups': [],
            'critical_eta_groups': [],
            'group_details': {},
            'issues': []
        }

        groups = current_lag_data.get('groups', [])
        result['total_groups_analyzed'] = len(groups)

        for group in groups:
            group_id = group.get('group_id')
            total_lag = group.get('total_lag', 0)
            status = group.get('status', 'HEALTHY')

            if total_lag == 0:
                result['group_details'][group_id] = {
                    'status': 'HEALTHY',
                    'total_lag': 0,
                    'analysis': 'No lag detected'
                }
                continue

            analysis = self._analyze_single_group(
                group,
                prometheus_data
            )

            result['group_details'][group_id] = analysis

            if analysis.get('is_slow_consumer', False):
                result['slow_consumers'].append({
                    'group_id': group_id,
                    'consume_rate': analysis.get('consume_rate', 0),
                    'produce_rate': analysis.get('produce_rate', 0),
                    'consumption_ratio': analysis.get('consumption_ratio', 0)
                })

            if analysis.get('is_growing', False):
                result['growing_lag_groups'].append({
                    'group_id': group_id,
                    'growth_rate': analysis.get('growth_rate', 0)
                })

            if analysis.get('eta_hours') is not None:
                eta = analysis['eta_hours']
                if eta <= self.eta_critical_hours:
                    result['critical_eta_groups'].append({
                        'group_id': group_id,
                        'eta_hours': eta,
                        'severity': 'CRITICAL'
                    })
                elif eta <= self.eta_warning_hours:
                    result['critical_eta_groups'].append({
                        'group_id': group_id,
                        'eta_hours': eta,
                        'severity': 'WARNING'
                    })

        if result['slow_consumers'] or result['growing_lag_groups'] or result['critical_eta_groups']:
            result['status'] = 'WARNING'

        if result['slow_consumers']:
            result['issues'].append(
                f"发现 {len(result['slow_consumers'])} 个消费速度较慢的消费组"
            )
        if result['growing_lag_groups']:
            result['issues'].append(
                f"发现 {len(result['growing_lag_groups'])} 个消费组积压在持续增长"
            )
        if result['critical_eta_groups']:
            result['issues'].append(
                f"发现 {len(result['critical_eta_groups'])} 个消费组预计无法在 {self.eta_warning_hours} 小时内消化完积压"
            )

        return result

    def _analyze_single_group(
        self,
        group_data: Dict[str, Any],
        prometheus_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        group_id = group_data.get('group_id')
        total_lag = group_data.get('total_lag', 0)
        topic_lag = group_data.get('topic_lag', {})

        analysis = {
            'total_lag': total_lag,
            'consume_rate': 0.0,
            'produce_rate': 0.0,
            'consumption_ratio': 1.0,
            'growth_rate': 0.0,
            'eta_hours': None,
            'is_slow_consumer': False,
            'is_growing': False,
            'topic_analysis': {}
        }

        if total_lag == 0:
            return analysis

        topic_metrics = prometheus_data.get('topic_metrics', {})
        prom_topics = topic_metrics.get('topics', [])

        total_produce_rate = 0.0
        total_consume_rate = 0.0

        for topic_name, lag in topic_lag.items():
            topic_produce_rate = self._get_topic_produce_rate(topic_name, prom_topics)
            topic_consume_rate = self._estimate_consume_rate(
                topic_name, group_id, lag, topic_produce_rate, prometheus_data
            )

            total_produce_rate += topic_produce_rate
            total_consume_rate += topic_consume_rate

            if lag > 0:
                topic_ratio = topic_consume_rate / topic_produce_rate if topic_produce_rate > 0 else 1.0
                analysis['topic_analysis'][topic_name] = {
                    'lag': lag,
                    'produce_rate': topic_produce_rate,
                    'consume_rate': topic_consume_rate,
                    'consumption_ratio': round(topic_ratio, 4)
                }

        analysis['produce_rate'] = round(total_produce_rate, 2)
        analysis['consume_rate'] = round(total_consume_rate, 2)

        if total_produce_rate > 0:
            consumption_ratio = total_consume_rate / total_produce_rate
            analysis['consumption_ratio'] = round(consumption_ratio, 4)

            if consumption_ratio < self.slow_consumer_threshold:
                analysis['is_slow_consumer'] = True

            analysis['growth_rate'] = round(total_produce_rate - total_consume_rate, 2)
            if analysis['growth_rate'] > self.lag_growth_rate_threshold:
                analysis['is_growing'] = True

            if total_consume_rate > total_produce_rate:
                catchup_rate = total_consume_rate - total_produce_rate
                if catchup_rate > 0:
                    seconds_to_catchup = total_lag / catchup_rate
                    analysis['eta_hours'] = round(seconds_to_catchup / 3600, 2)
            else:
                analysis['eta_hours'] = float('inf')

        return analysis

    def _get_topic_produce_rate(
        self,
        topic_name: str,
        prom_topics: List[Dict[str, Any]]
    ) -> float:
        for topic_data in prom_topics:
            if topic_data.get('topic') == topic_name:
                return topic_data.get('messages_in_per_sec', 0)
        return 0.0

    def _estimate_consume_rate(
        self,
        topic_name: str,
        group_id: str,
        current_lag: int,
        produce_rate: float,
        prometheus_data: Dict[str, Any]
    ) -> float:
        consumer_metrics = prometheus_data.get('consumer_lag', {})
        groups = consumer_metrics.get('groups', [])

        for group in groups:
            if group.get('group_id') == group_id:
                topic_metrics = group.get('topics', [])
                for tm in topic_metrics:
                    if tm.get('topic') == topic_name:
                        lag_rate = tm.get('lag_rate', 0)
                        if produce_rate > 0:
                            return max(0.1, produce_rate - lag_rate)

        if produce_rate > 0:
            return max(0.1, produce_rate * 0.9)

        return 0.1

    def get_slow_consumer_recommendations(
        self,
        analysis_result: Dict[str, Any]
    ) -> List[str]:
        recommendations = []

        for slow in analysis_result.get('slow_consumers', []):
            group_id = slow['group_id']
            ratio = slow.get('consumption_ratio', 0)
            recommendations.append(
                f"消费组 [{group_id}] 消费速度仅为生产速度的 {ratio*100:.1f}%，"
                f"建议增加消费者实例或优化消费逻辑"
            )

        for growing in analysis_result.get('growing_lag_groups', []):
            group_id = growing['group_id']
            growth_rate = growing['growth_rate']
            recommendations.append(
                f"消费组 [{group_id}] 积压以 {growth_rate:.0f} 条/秒的速度增长，"
                f"消费速度跟不上生产速度"
            )

        for eta_info in analysis_result.get('critical_eta_groups', []):
            group_id = eta_info['group_id']
            eta = eta_info['eta_hours']
            severity = eta_info['severity']
            if eta == float('inf'):
                recommendations.append(
                    f"消费组 [{group_id}] 消费速度小于等于生产速度，积压将持续存在，需紧急处理"
                )
            else:
                recommendations.append(
                    f"消费组 [{group_id}] 预计需要 {eta:.1f} 小时才能消化完当前积压"
                )

        return recommendations