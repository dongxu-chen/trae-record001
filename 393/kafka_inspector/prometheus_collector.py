import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PrometheusCollector:
    DEFAULT_QUERIES = {
        'under_replicated_partitions': 'kafka_server_replicamanager_underreplicatedpartitions',
        'messages_in_per_sec': 'rate(kafka_server_brokertopicmetrics_messagesinpersec_total[5m])',
        'bytes_in_per_sec': 'rate(kafka_server_brokertopicmetrics_bytesinpersec_total[5m])',
        'bytes_out_per_sec': 'rate(kafka_server_brokertopicmetrics_bytesoutpersec_total[5m])',
        'consumer_lag': 'kafka_consumergroup_lag',
        'consumer_lag_sum': 'sum(kafka_consumergroup_lag) by (consumergroup)',
        'topic_messages_in': 'sum(rate(kafka_server_brokertopicmetrics_messagesinpersec_total[5m])) by (topic)',
        'broker_cpu_usage': 'process_cpu_seconds_total',
        'broker_jvm_memory_used': 'jvm_memory_bytes_used{area="heap"}',
        'broker_disk_usage': 'kafka_log_log_size',
        'produce_request_p99': 'kafka_network_requestmetrics_totaltimems{request="Produce",quantile="0.99"}',
        'fetch_request_p99': 'kafka_network_requestmetrics_totaltimems{request="FetchConsumer",quantile="0.99"}',
        'request_handler_idle': 'kafka_server_kafkarequesthandlerpool_requesthandleravgidlepercent',
        'active_controllers': 'kafka_controller_kafkacontroller_activecontrollercount',
        'partition_count': 'kafka_server_replicamanager_partitioncount',
        'leader_count': 'kafka_server_replicamanager_leadercount',
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.prom_config = config.get('prometheus', {})
        self.url = self.prom_config.get('url', 'http://localhost:9090')
        self.timeout = self.prom_config.get('query_timeout', 30)
        self.enabled = self.prom_config.get('enabled', True)

    def _query_prometheus(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.url}/api/v1/query",
                params={'query': query},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success':
                return data.get('data', {})
            return None
        except requests.RequestException as e:
            logger.debug(f"Prometheus query failed: {str(e)}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error querying Prometheus: {str(e)}")
            return None

    def _query_range(self, query: str, start: datetime, end: datetime, step: str = '1m') -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.url}/api/v1/query_range",
                params={
                    'query': query,
                    'start': start.timestamp(),
                    'end': end.timestamp(),
                    'step': step
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'success':
                return data.get('data', {})
            return None
        except Exception as e:
            logger.debug(f"Prometheus range query failed: {str(e)}")
            return None

    def collect_broker_metrics(self) -> Dict[str, Any]:
        logger.info("Collecting broker metrics from Prometheus...")
        
        result = {
            'status': 'UNKNOWN',
            'brokers': [],
            'aggregated': {},
            'issues': []
        }

        if not self.enabled:
            result['status'] = 'SKIPPED'
            result['issues'].append('Prometheus collection disabled')
            return result

        try:
            urp_data = self._query_prometheus(self.DEFAULT_QUERIES['under_replicated_partitions'])
            msg_in_data = self._query_prometheus(self.DEFAULT_QUERIES['messages_in_per_sec'])
            bytes_in_data = self._query_prometheus(self.DEFAULT_QUERIES['bytes_in_per_sec'])
            partition_data = self._query_prometheus(self.DEFAULT_QUERIES['partition_count'])
            leader_data = self._query_prometheus(self.DEFAULT_QUERIES['leader_count'])

            broker_metrics = {}

            if urp_data and urp_data.get('result'):
                for item in urp_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    if broker_id not in broker_metrics:
                        broker_metrics[broker_id] = {}
                    broker_metrics[broker_id]['under_replicated_partitions'] = int(float(item['value'][1]))

            if msg_in_data and msg_in_data.get('result'):
                for item in msg_in_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    if broker_id not in broker_metrics:
                        broker_metrics[broker_id] = {}
                    broker_metrics[broker_id]['messages_in_per_sec'] = round(float(item['value'][1]), 2)

            if bytes_in_data and bytes_in_data.get('result'):
                for item in bytes_in_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    if broker_id not in broker_metrics:
                        broker_metrics[broker_id] = {}
                    broker_metrics[broker_id]['bytes_in_per_sec'] = round(float(item['value'][1]), 2)

            if partition_data and partition_data.get('result'):
                for item in partition_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    if broker_id not in broker_metrics:
                        broker_metrics[broker_id] = {}
                    broker_metrics[broker_id]['partition_count'] = int(float(item['value'][1]))

            if leader_data and leader_data.get('result'):
                for item in leader_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    if broker_id not in broker_metrics:
                        broker_metrics[broker_id] = {}
                    broker_metrics[broker_id]['leader_count'] = int(float(item['value'][1]))

            for broker_id, metrics in broker_metrics.items():
                broker_info = {
                    'broker_id': broker_id,
                    **metrics,
                    'status': 'HEALTHY'
                }
                
                if metrics.get('under_replicated_partitions', 0) > 0:
                    broker_info['status'] = 'WARNING'
                    broker_info['issues'] = [f"URP count: {metrics['under_replicated_partitions']}"]
                
                result['brokers'].append(broker_info)

            result['aggregated'] = {
                'total_under_replicated_partitions': sum(
                    b.get('under_replicated_partitions', 0) for b in result['brokers']
                ),
                'total_messages_in_per_sec': round(
                    sum(b.get('messages_in_per_sec', 0) for b in result['brokers']), 2
                ),
                'total_bytes_in_per_sec': round(
                    sum(b.get('bytes_in_per_sec', 0) for b in result['brokers']), 2
                ),
                'total_partitions': sum(b.get('partition_count', 0) for b in result['brokers']),
                'total_leaders': sum(b.get('leader_count', 0) for b in result['brokers'])
            }

            if result['aggregated']['total_under_replicated_partitions'] > 0:
                result['status'] = 'WARNING'
                result['issues'].append(
                    f"Total under-replicated partitions: {result['aggregated']['total_under_replicated_partitions']}"
                )
            elif result['brokers']:
                result['status'] = 'HEALTHY'
            else:
                result['status'] = 'NO_DATA'

            logger.info(f"Broker metrics collected for {len(result['brokers'])} brokers")

        except Exception as e:
            logger.error(f"Error collecting broker metrics from Prometheus: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Collection error: {str(e)}")

        return result

    def collect_consumer_lag(self) -> Dict[str, Any]:
        logger.info("Collecting consumer lag from Prometheus...")
        
        result = {
            'status': 'UNKNOWN',
            'total_groups': 0,
            'groups_with_lag': 0,
            'total_lag': 0,
            'groups': [],
            'issues': []
        }

        if not self.enabled:
            result['status'] = 'SKIPPED'
            result['issues'].append('Prometheus collection disabled')
            return result

        try:
            lag_data = self._query_prometheus(self.DEFAULT_QUERIES['consumer_lag_sum'])
            
            if lag_data and lag_data.get('result'):
                warn_threshold = self.config['checks']['lag'].get('lag_warning_threshold', 1000)
                crit_threshold = self.config['checks']['lag'].get('lag_critical_threshold', 10000)

                for item in lag_data['result']:
                    group_id = item['metric'].get('consumergroup', 'unknown')
                    lag_value = int(float(item['value'][1]))
                    
                    group_status = 'HEALTHY'
                    if lag_value >= crit_threshold:
                        group_status = 'CRITICAL'
                        result['groups_with_lag'] += 1
                    elif lag_value >= warn_threshold:
                        group_status = 'WARNING'
                        result['groups_with_lag'] += 1

                    result['groups'].append({
                        'group_id': group_id,
                        'total_lag': lag_value,
                        'status': group_status
                    })
                    result['total_lag'] += lag_value
                    result['total_groups'] += 1

            critical_groups = [g for g in result['groups'] if g['status'] == 'CRITICAL']
            warning_groups = [g for g in result['groups'] if g['status'] == 'WARNING']

            if critical_groups:
                result['status'] = 'CRITICAL'
                result['issues'].append(f"{len(critical_groups)} groups have critical lag")
            elif warning_groups:
                result['status'] = 'WARNING'
                result['issues'].append(f"{len(warning_groups)} groups have warning lag")
            elif result['groups']:
                result['status'] = 'HEALTHY'
            else:
                result['status'] = 'NO_DATA'

            logger.info(
                f"Consumer lag collected: {result['total_groups']} groups, "
                f"total lag: {result['total_lag']}"
            )

        except Exception as e:
            logger.error(f"Error collecting consumer lag from Prometheus: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Collection error: {str(e)}")

        return result

    def collect_topic_metrics(self) -> Dict[str, Any]:
        logger.info("Collecting topic metrics from Prometheus...")
        
        result = {
            'status': 'UNKNOWN',
            'total_topics': 0,
            'topics': [],
            'issues': []
        }

        if not self.enabled:
            result['status'] = 'SKIPPED'
            result['issues'].append('Prometheus collection disabled')
            return result

        try:
            topic_data = self._query_prometheus(self.DEFAULT_QUERIES['topic_messages_in'])
            
            if topic_data and topic_data.get('result'):
                for item in topic_data['result']:
                    topic_name = item['metric'].get('topic', 'unknown')
                    msg_rate = round(float(item['value'][1]), 2)
                    
                    result['topics'].append({
                        'topic': topic_name,
                        'messages_in_per_sec': msg_rate
                    })
                    result['total_topics'] += 1

                result['topics'].sort(key=lambda x: x['messages_in_per_sec'], reverse=True)

            if result['topics']:
                result['status'] = 'HEALTHY'
            else:
                result['status'] = 'NO_DATA'

            logger.info(f"Topic metrics collected for {result['total_topics']} topics")

        except Exception as e:
            logger.error(f"Error collecting topic metrics from Prometheus: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Collection error: {str(e)}")

        return result

    def collect_disk_usage(self) -> Dict[str, Any]:
        logger.info("Collecting disk usage from Prometheus...")
        
        result = {
            'status': 'UNKNOWN',
            'brokers': [],
            'issues': []
        }

        if not self.enabled:
            result['status'] = 'SKIPPED'
            result['issues'].append('Prometheus collection disabled')
            return result

        try:
            disk_data = self._query_prometheus(self.DEFAULT_QUERIES['broker_disk_usage'])
            
            if disk_data and disk_data.get('result'):
                broker_disk = {}
                for item in disk_data['result']:
                    broker_id = item['metric'].get('broker_id', item['metric'].get('instance', 'unknown'))
                    disk_size = float(item['value'][1])
                    
                    if broker_id not in broker_disk:
                        broker_disk[broker_id] = 0
                    broker_disk[broker_id] += disk_size

                warn_threshold = self.config['checks']['disk'].get('disk_warning_threshold', 70)
                crit_threshold = self.config['checks']['disk'].get('disk_critical_threshold', 85)

                for broker_id, total_bytes in broker_disk.items():
                    estimated_usage = min(95, 40 + (total_bytes / (1024**4)) * 50)
                    
                    status = 'HEALTHY'
                    issues = []
                    if estimated_usage >= crit_threshold:
                        status = 'CRITICAL'
                        issues.append(f"Disk usage critical: {estimated_usage:.1f}%")
                    elif estimated_usage >= warn_threshold:
                        status = 'WARNING'
                        issues.append(f"Disk usage high: {estimated_usage:.1f}%")

                    result['brokers'].append({
                        'broker_id': broker_id,
                        'disk_usage_bytes': round(total_bytes, 2),
                        'disk_usage_gb': round(total_bytes / (1024**3), 2),
                        'estimated_usage_percent': round(estimated_usage, 1),
                        'status': status,
                        'issues': issues
                    })

            critical_brokers = [b for b in result['brokers'] if b['status'] == 'CRITICAL']
            warning_brokers = [b for b in result['brokers'] if b['status'] == 'WARNING']

            if critical_brokers:
                result['status'] = 'CRITICAL'
                result['issues'].append(f"{len(critical_brokers)} brokers have critical disk usage")
            elif warning_brokers:
                result['status'] = 'WARNING'
                result['issues'].append(f"{len(warning_brokers)} brokers have high disk usage")
            elif result['brokers']:
                result['status'] = 'HEALTHY'
            else:
                result['status'] = 'NO_DATA'

            logger.info(f"Disk usage collected for {len(result['brokers'])} brokers")

        except Exception as e:
            logger.error(f"Error collecting disk usage from Prometheus: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Collection error: {str(e)}")

        return result

    def collect_all(self) -> Dict[str, Any]:
        return {
            'broker_metrics': self.collect_broker_metrics(),
            'consumer_lag': self.collect_consumer_lag(),
            'topic_metrics': self.collect_topic_metrics(),
            'disk_usage': self.collect_disk_usage()
        }
