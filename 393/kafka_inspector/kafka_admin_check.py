import logging
import re
from typing import Dict, List, Any, Optional
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaConsumer
from kafka.errors import KafkaError, TopicAlreadyExistsError

logger = logging.getLogger(__name__)


class KafkaAdminChecker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bootstrap_servers = config['kafka']['bootstrap_servers']
        self.admin_client = None
        self.consumer = None
        self._isr_history = None
        try:
            from kafka_inspector.isr_history_monitor import ISRHistoryMonitor
            self._isr_history = ISRHistoryMonitor(config)
        except ImportError:
            logger.warning("ISRHistoryMonitor not available, ISR history tracking disabled")

    def _connect(self):
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                security_protocol=self.config['kafka'].get('security_protocol', 'PLAINTEXT'),
                sasl_mechanism=self.config['kafka'].get('sasl_mechanism'),
                sasl_plain_username=self.config['kafka'].get('sasl_username'),
                sasl_plain_password=self.config['kafka'].get('sasl_password'),
                ssl_cafile=self.config['kafka'].get('ssl_cafile'),
                ssl_certfile=self.config['kafka'].get('ssl_certfile'),
                ssl_keyfile=self.config['kafka'].get('ssl_keyfile'),
                client_id='kafka-inspector-admin'
            )
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                security_protocol=self.config['kafka'].get('security_protocol', 'PLAINTEXT'),
                sasl_mechanism=self.config['kafka'].get('sasl_mechanism'),
                sasl_plain_username=self.config['kafka'].get('sasl_username'),
                sasl_plain_password=self.config['kafka'].get('sasl_password'),
                ssl_cafile=self.config['kafka'].get('ssl_cafile'),
                ssl_certfile=self.config['kafka'].get('ssl_certfile'),
                ssl_keyfile=self.config['kafka'].get('ssl_keyfile'),
                group_id='kafka-inspector-consumer',
                enable_auto_commit=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            return False

    def _close(self):
        if self.admin_client:
            self.admin_client.close()
        if self.consumer:
            self.consumer.close()

    def check_broker_health(self) -> Dict[str, Any]:
        logger.info("Checking broker health...")
        result = {
            'status': 'UNKNOWN',
            'total_brokers': 0,
            'online_brokers': 0,
            'offline_brokers': 0,
            'brokers': [],
            'issues': []
        }

        if not self._connect():
            result['status'] = 'ERROR'
            result['issues'].append('Failed to connect to Kafka cluster')
            return result

        try:
            broker_metadata = self.admin_client.describe_cluster()
            brokers = broker_metadata.get('brokers', [])
            controller = broker_metadata.get('controller')

            result['total_brokers'] = len(brokers)
            result['controller_id'] = controller.id if controller else None

            for broker in brokers:
                broker_info = {
                    'id': broker.id,
                    'host': broker.host,
                    'port': broker.port,
                    'rack': broker.rack,
                    'status': 'ONLINE',
                    'is_controller': broker.id == controller.id if controller else False
                }
                result['brokers'].append(broker_info)
                result['online_brokers'] += 1

            offline_threshold = self.config['checks']['broker'].get('offline_threshold', 1)
            if result['offline_brokers'] >= offline_threshold:
                result['status'] = 'CRITICAL'
                result['issues'].append(f"Found {result['offline_brokers']} offline brokers")
            elif result['offline_brokers'] > 0:
                result['status'] = 'WARNING'
                result['issues'].append(f"Found {result['offline_brokers']} offline brokers")
            else:
                result['status'] = 'HEALTHY'

            logger.info(f"Broker check complete: {result['online_brokers']}/{result['total_brokers']} online")

        except Exception as e:
            logger.error(f"Error checking broker health: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Error checking broker health: {str(e)}")
        finally:
            self._close()

        return result

    def check_isr_status(self) -> Dict[str, Any]:
        logger.info("Checking ISR status...")
        result = {
            'status': 'UNKNOWN',
            'total_topics': 0,
            'total_partitions': 0,
            'under_replicated_partitions': 0,
            'topics_with_issues': [],
            'issues': []
        }

        if not self._connect():
            result['status'] = 'ERROR'
            result['issues'].append('Failed to connect to Kafka cluster')
            return result

        try:
            topics = self.admin_client.list_topics()
            result['total_topics'] = len(topics)

            topic_descriptions = self.admin_client.describe_topics(topics)
            threshold = self.config['checks']['isr'].get('under_replicated_threshold', 0)

            for topic_desc in topic_descriptions:
                topic_name = topic_desc.topic
                topic_issues = {
                    'topic': topic_name,
                    'partitions': [],
                    'under_replicated_count': 0
                }

                for partition in topic_desc.partitions:
                    partition_id = partition.partition
                    replicas = len(partition.replicas)
                    isr_count = len(partition.isr)
                    is_under_replicated = isr_count < replicas

                    partition_info = {
                        'partition': partition_id,
                        'leader': partition.leader.id if partition.leader else None,
                        'replicas': [r.id for r in partition.replicas],
                        'isr': [r.id for r in partition.isr],
                        'isr_count': isr_count,
                        'replica_count': replicas,
                        'under_replicated': is_under_replicated
                    }

                    result['total_partitions'] += 1

                    if is_under_replicated:
                        result['under_replicated_partitions'] += 1
                        topic_issues['under_replicated_count'] += 1
                        topic_issues['partitions'].append(partition_info)

                if topic_issues['under_replicated_count'] > threshold:
                    result['topics_with_issues'].append(topic_issues)

            if result['under_replicated_partitions'] > threshold:
                result['status'] = 'WARNING' if result['under_replicated_partitions'] < 10 else 'CRITICAL'
                result['issues'].append(
                    f"Found {result['under_replicated_partitions']} under-replicated partitions "
                    f"across {len(result['topics_with_issues'])} topics"
                )
            else:
                result['status'] = 'HEALTHY'

            logger.info(
                f"ISR check complete: {result['under_replicated_partitions']} under-replicated partitions "
                f"out of {result['total_partitions']} total"
            )

        except Exception as e:
            logger.error(f"Error checking ISR status: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Error checking ISR status: {str(e)}")
        finally:
            self._close()

        if self._isr_history:
            history_result = self._isr_history.record_isr_status(result)
            result['isr_history'] = history_result

        return result

    def _get_topic_priority(self, topic_name: str) -> Dict[str, Any]:
        lag_config = self.config.get('checks', {}).get('lag', {})
        priority_config = lag_config.get('topic_priority', {})

        if not priority_config.get('enabled', False):
            return {
                'priority': 'default',
                'lag_warning_threshold': lag_config.get('lag_warning_threshold', 1000),
                'lag_critical_threshold': lag_config.get('lag_critical_threshold', 10000)
            }

        for priority_level in ['high', 'medium', 'low']:
            level_config = priority_config.get(priority_level, {})
            patterns = level_config.get('topics', [])
            for pattern in patterns:
                try:
                    if re.match(pattern, topic_name, re.IGNORECASE):
                        return {
                            'priority': priority_level,
                            'lag_warning_threshold': level_config.get(
                                'lag_warning_threshold',
                                lag_config.get('lag_warning_threshold', 1000)
                            ),
                            'lag_critical_threshold': level_config.get(
                                'lag_critical_threshold',
                                lag_config.get('lag_critical_threshold', 10000)
                            )
                        }
                except re.error:
                    logger.warning(f"Invalid regex pattern for topic priority: {pattern}")

        return {
            'priority': 'default',
            'lag_warning_threshold': lag_config.get('lag_warning_threshold', 1000),
            'lag_critical_threshold': lag_config.get('lag_critical_threshold', 10000)
        }

    def check_consumer_lag(self) -> Dict[str, Any]:
        logger.info("Checking consumer lag...")
        result = {
            'status': 'UNKNOWN',
            'total_groups': 0,
            'groups_with_lag': 0,
            'total_lag': 0,
            'groups': [],
            'issues': []
        }

        if not self._connect():
            result['status'] = 'ERROR'
            result['issues'].append('Failed to connect to Kafka cluster')
            return result

        try:
            consumer_groups = self.admin_client.list_consumer_groups()
            group_ids = [group[0] for group in consumer_groups]
            result['total_groups'] = len(group_ids)

            warn_threshold = self.config['checks']['lag'].get('lag_warning_threshold', 1000)
            crit_threshold = self.config['checks']['lag'].get('lag_critical_threshold', 10000)

            for group_id in group_ids:
                try:
                    group_info = self.admin_client.describe_consumer_groups([group_id])
                    if not group_info:
                        continue

                    offsets = self.admin_client.list_consumer_group_offsets(group_id)
                    
                    group_result = {
                        'group_id': group_id,
                        'state': group_info[0].state.value if hasattr(group_info[0], 'state') else 'UNKNOWN',
                        'members': len(group_info[0].members) if hasattr(group_info[0], 'members') else 0,
                        'total_lag': 0,
                        'topic_lag': {},
                        'topic_priorities': {},
                        'status': 'HEALTHY'
                    }

                    for (topic, partition), offset_info in offsets.items():
                        try:
                            topic_partition = f"{topic}-{partition}"
                            end_offsets = self.consumer.end_offsets([(topic, partition)])
                            end_offset = end_offsets.get((topic, partition), 0)
                            current_offset = offset_info.offset

                            lag = max(0, end_offset - current_offset)
                            group_result['total_lag'] += lag
                            result['total_lag'] += lag

                            if topic not in group_result['topic_lag']:
                                group_result['topic_lag'][topic] = 0
                            group_result['topic_lag'][topic] += lag

                            priority_info = self._get_topic_priority(topic)
                            if topic not in group_result['topic_priorities']:
                                group_result['topic_priorities'][topic] = priority_info['priority']

                        except Exception as e:
                            logger.debug(f"Error getting lag for {topic}-{partition}: {str(e)}")

                    overall_priority = 'default'
                    warn_threshold = self.config['checks']['lag'].get('lag_warning_threshold', 1000)
                    crit_threshold = self.config['checks']['lag'].get('lag_critical_threshold', 10000)

                    topic_priorities_list = list(set(group_result['topic_priorities'].values()))
                    if 'high' in topic_priorities_list:
                        overall_priority = 'high'
                        priority_config = self.config['checks']['lag'].get('topic_priority', {}).get('high', {})
                        warn_threshold = priority_config.get('lag_warning_threshold', 100)
                        crit_threshold = priority_config.get('lag_critical_threshold', 1000)
                    elif 'medium' in topic_priorities_list:
                        overall_priority = 'medium'
                        priority_config = self.config['checks']['lag'].get('topic_priority', {}).get('medium', {})
                        warn_threshold = priority_config.get('lag_warning_threshold', 1000)
                        crit_threshold = priority_config.get('lag_critical_threshold', 10000)
                    elif 'low' in topic_priorities_list:
                        overall_priority = 'low'
                        priority_config = self.config['checks']['lag'].get('topic_priority', {}).get('low', {})
                        warn_threshold = priority_config.get('lag_warning_threshold', 10000)
                        crit_threshold = priority_config.get('lag_critical_threshold', 100000)

                    group_result['overall_priority'] = overall_priority
                    group_result['effective_warning_threshold'] = warn_threshold
                    group_result['effective_critical_threshold'] = crit_threshold

                    if group_result['total_lag'] >= crit_threshold:
                        group_result['status'] = 'CRITICAL'
                        result['groups_with_lag'] += 1
                    elif group_result['total_lag'] >= warn_threshold:
                        group_result['status'] = 'WARNING'
                        result['groups_with_lag'] += 1

                    result['groups'].append(group_result)

                except Exception as e:
                    logger.debug(f"Error checking group {group_id}: {str(e)}")

            critical_groups = [g for g in result['groups'] if g['status'] == 'CRITICAL']
            warning_groups = [g for g in result['groups'] if g['status'] == 'WARNING']

            if critical_groups:
                result['status'] = 'CRITICAL'
                result['issues'].append(f"{len(critical_groups)} groups have critical lag")
            elif warning_groups:
                result['status'] = 'WARNING'
                result['issues'].append(f"{len(warning_groups)} groups have warning lag")
            else:
                result['status'] = 'HEALTHY'

            logger.info(
                f"Consumer lag check complete: {result['groups_with_lag']}/{result['total_groups']} "
                f"groups with lag, total lag: {result['total_lag']}"
            )

        except Exception as e:
            logger.error(f"Error checking consumer lag: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Error checking consumer lag: {str(e)}")
        finally:
            self._close()

        return result

    def check_topic_partitions(self) -> Dict[str, Any]:
        logger.info("Checking topic partition distribution...")
        result = {
            'status': 'UNKNOWN',
            'total_topics': 0,
            'total_partitions': 0,
            'broker_partition_distribution': {},
            'topics': [],
            'issues': []
        }

        if not self._connect():
            result['status'] = 'ERROR'
            result['issues'].append('Failed to connect to Kafka cluster')
            return result

        try:
            topics = self.admin_client.list_topics()
            result['total_topics'] = len(topics)

            topic_descriptions = self.admin_client.describe_topics(topics)
            max_partitions_per_broker = self.config['checks']['topic_partition'].get('max_partitions_per_broker', 1000)

            for topic_desc in topic_descriptions:
                topic_name = topic_desc.topic
                topic_info = {
                    'topic': topic_name,
                    'partition_count': len(topic_desc.partitions),
                    'replication_factor': len(topic_desc.partitions[0].replicas) if topic_desc.partitions else 0,
                    'partitions': []
                }

                for partition in topic_desc.partitions:
                    topic_info['partitions'].append({
                        'partition': partition.partition,
                        'leader': partition.leader.id if partition.leader else None,
                        'replicas': [r.id for r in partition.replicas]
                    })

                    for replica in partition.replicas:
                        broker_id = replica.id
                        if broker_id not in result['broker_partition_distribution']:
                            result['broker_partition_distribution'][broker_id] = 0
                        result['broker_partition_distribution'][broker_id] += 1

                    result['total_partitions'] += 1

                result['topics'].append(topic_info)

            overloaded_brokers = []
            for broker_id, count in result['broker_partition_distribution'].items():
                if count > max_partitions_per_broker:
                    overloaded_brokers.append(f"Broker {broker_id}: {count} partitions")

            if overloaded_brokers:
                result['status'] = 'WARNING'
                result['issues'].append(f"Brokers exceeding partition limit: {', '.join(overloaded_brokers)}")
            else:
                result['status'] = 'HEALTHY'

            logger.info(
                f"Topic partition check complete: {result['total_topics']} topics, "
                f"{result['total_partitions']} total partitions"
            )

        except Exception as e:
            logger.error(f"Error checking topic partitions: {str(e)}")
            result['status'] = 'ERROR'
            result['issues'].append(f"Error checking topic partitions: {str(e)}")
        finally:
            self._close()

        return result

    def _analyze_rack_distribution(self, broker_health: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Analyzing rack distribution...")
        rack_config = self.config.get('checks', {}).get('topic_partition', {}).get('rack_aware', {})
        result = {
            'enabled': rack_config.get('enabled', False),
            'racks': {},
            'broker_rack_map': {},
            'single_rack_topics': [],
            'cross_rack_replication_score': 0.0,
            'issues': []
        }

        if not result['enabled']:
            return result

        brokers = broker_health.get('brokers', [])
        for broker in brokers:
            broker_id = broker.get('id')
            rack = broker.get('rack', f'rack-{broker_id}')
            result['broker_rack_map'][broker_id] = rack
            if rack not in result['racks']:
                result['racks'][rack] = []
            result['racks'][rack].append(broker_id)

        if self._connect():
            try:
                topics = self.admin_client.list_topics()
                topic_descriptions = self.admin_client.describe_topics(topics)
                min_racks = rack_config.get('min_racks_for_replication', 2)

                total_partitions = 0
                cross_rack_partitions = 0

                for topic_desc in topic_descriptions:
                    topic_name = topic_desc.topic
                    all_replicas_same_rack = True

                    for partition in topic_desc.partitions:
                        total_partitions += 1
                        replica_racks = set()
                        for replica in partition.replicas:
                            rack = result['broker_rack_map'].get(replica.id, 'unknown')
                            replica_racks.add(rack)

                        if len(replica_racks) >= min_racks:
                            cross_rack_partitions += 1
                        else:
                            all_replicas_same_rack = False

                    if all_replicas_same_rack and rack_config.get('warn_on_single_rack_topics', True):
                        result['single_rack_topics'].append({
                            'topic': topic_name,
                            'rack': result['broker_rack_map'].get(
                                topic_desc.partitions[0].leader.id, 'unknown'
                            ) if topic_desc.partitions else 'unknown'
                        })

                if total_partitions > 0:
                    result['cross_rack_replication_score'] = round(
                        cross_rack_partitions / total_partitions * 100, 1
                    )

                if result['single_rack_topics']:
                    result['issues'].append(
                        f"Found {len(result['single_rack_topics'])} topics with all replicas on the same rack"
                    )
                    result['status'] = 'WARNING'
                else:
                    result['status'] = 'HEALTHY'

            except Exception as e:
                logger.error(f"Error analyzing rack distribution: {e}")
                result['issues'].append(f"Error analyzing rack distribution: {e}")
                result['status'] = 'ERROR'
            finally:
                self._close()

        return result

    def run_all_checks(self) -> Dict[str, Any]:
        broker_health = self.check_broker_health()
        isr_status = self.check_isr_status()
        consumer_lag = self.check_consumer_lag()
        topic_partitions = self.check_topic_partitions()
        rack_distribution = self._analyze_rack_distribution(broker_health)

        return {
            'broker_health': broker_health,
            'isr_status': isr_status,
            'consumer_lag': consumer_lag,
            'topic_partitions': topic_partitions,
            'rack_distribution': rack_distribution
        }
