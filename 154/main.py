#!/usr/bin/env python3
import os
import logging
import threading
import yaml
from dotenv import load_dotenv

from k8s_watcher import K8sWatcher
from slack_integration import SlackIntegration
from event_deduplicator import EventDeduplicator
from nlp_parser import NLPParser
from knowledge_base import KnowledgeBase
from health_checker import HealthChecker
from teams_integration import TeamsIntegration
from dingtalk_integration import DingTalkIntegration


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path='config.yaml'):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


class MultiChannelNotifier:
    def __init__(self):
        self.channels = []
    
    def add_channel(self, channel):
        self.channels.append(channel)
    
    def send_event(self, event, count=1):
        for channel in self.channels:
            try:
                if hasattr(channel, 'send_event'):
                    channel.send_event(event, count)
            except Exception as e:
                logger.error(f"Error sending event to channel: {e}")
    
    def send_diagnosis(self, diagnosis, pod_name=None):
        for channel in self.channels:
            try:
                if hasattr(channel, 'send_diagnosis'):
                    channel.send_diagnosis(diagnosis, pod_name)
            except Exception as e:
                logger.error(f"Error sending diagnosis to channel: {e}")
    
    def send_daily_report(self, report):
        for channel in self.channels:
            try:
                if hasattr(channel, 'send_daily_report'):
                    channel.send_daily_report(report)
            except Exception as e:
                logger.error(f"Error sending daily report to channel: {e}")


def event_handler(event, deduplicator, notifier, knowledge_base):
    is_new, count = deduplicator.add_event(event)
    
    if is_new:
        event_type = event.get('type', 'UNKNOWN')
        obj = event.get('object', {})
        reason = obj.get('reason', 'Unknown')
        name = obj.get('involvedObject', {}).get('name', '')
        if not name:
            name = obj.get('metadata', {}).get('name', 'unknown')
        
        logger.info(f"New event: {event_type} - {reason} - {name}")
        
        diagnosis = knowledge_base.diagnose(obj.get('message', ''), name)
        if diagnosis:
            logger.info(f"Diagnosed issue: {diagnosis['name']}")


def flush_event_handler(event, count, notifier, knowledge_base):
    event_type = event.get('type', 'UNKNOWN')
    obj = event.get('object', {})
    reason = obj.get('reason', 'Unknown')
    name = obj.get('involvedObject', {}).get('name', '')
    if not name:
        name = obj.get('metadata', {}).get('name', 'unknown')
    
    logger.info(f"Flushing aggregated event: {event_type} - {reason} - {name} (count: {count})")
    
    notifier.send_event(event, count)
    
    diagnosis = knowledge_base.diagnose(obj.get('message', ''), name)
    if diagnosis:
        notifier.send_diagnosis(diagnosis, name)


def daily_report_callback(report, notifier):
    logger.info(f"Sending daily report: {report['date']}")
    notifier.send_daily_report(report)


def handle_nlp_command(command: str, k8s_watcher: K8sWatcher, nlp_parser: NLPParser) -> dict:
    parsed = nlp_parser.parse(command)
    action = parsed['action']
    namespace = parsed['namespace']
    pod = parsed['pod']
    
    result = {
        'action': action,
        'namespace': namespace,
        'pod': pod,
        'success': False,
        'message': '',
        'data': {}
    }
    
    try:
        if action == 'restart':
            if not pod:
                result['message'] = 'Please specify the pod name to restart'
                return result
            success, msg = k8s_watcher.restart_pod(namespace, pod)
            result['success'] = success
            result['message'] = msg
        
        elif action == 'logs':
            if not pod:
                result['message'] = 'Please specify the pod name to view logs'
                return result
            success, logs = k8s_watcher.get_pod_logs(namespace, pod)
            result['success'] = success
            if success:
                result['data']['logs'] = logs
            else:
                result['message'] = logs
        
        elif action == 'status':
            if not pod:
                result['message'] = 'Please specify the pod name to check status'
                return result
            success, status = k8s_watcher.get_pod_status(namespace, pod)
            result['success'] = success
            if success:
                result['data'] = status
            else:
                result['message'] = status
        
        elif action == 'list_pods':
            success, pods = k8s_watcher.list_pods(namespace)
            result['success'] = success
            if success:
                result['data']['pods'] = pods
            else:
                result['message'] = pods
        
        elif action == 'help':
            result['success'] = True
        
        else:
            result['message'] = f"Unknown action: {action}"
    
    except Exception as e:
        logger.error(f"Error handling NLP command: {e}")
        result['message'] = str(e)
    
    return result


def run_k8s_watcher(k8s_watcher, deduplicator, notifier, knowledge_base):
    def callback(event):
        event_handler(event, deduplicator, notifier, knowledge_base)
    
    logger.info("Starting Kubernetes event watcher...")
    k8s_watcher.watch_events(callback)


def main():
    load_dotenv()
    
    config = load_config()
    
    namespaces = config.get('event', {}).get('namespaces', ['default'])
    dedup_ttl = config.get('event', {}).get('dedup_ttl', 300)
    
    try:
        k8s_watcher = K8sWatcher(namespaces=namespaces, kubeconfig_path=os.getenv('KUBECONFIG_PATH'))
    except Exception as e:
        logger.error(f"Failed to initialize K8s watcher: {e}")
        return
    
    notifier = MultiChannelNotifier()
    
    slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
    slack_signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    slack_channel_id = os.getenv('SLACK_CHANNEL_ID')
    
    if slack_bot_token and slack_signing_secret and slack_channel_id:
        slack_config = config.get('slack', {})
        slack_integration = SlackIntegration(
            bot_token=slack_bot_token,
            signing_secret=slack_signing_secret,
            channel_id=slack_channel_id,
            bot_name=slack_config.get('bot_name', 'K8s Event Bot'),
            bot_icon=slack_config.get('bot_icon', ':kubernetes:'),
            button_timeout=30
        )
        slack_integration.set_k8s_watcher(k8s_watcher)
        slack_integration.set_config(config)
        notifier.add_channel(slack_integration)
        logger.info("Slack integration enabled")
    
    teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
    if teams_webhook:
        teams_integration = TeamsIntegration(teams_webhook)
        notifier.add_channel(teams_integration)
        logger.info("Teams integration enabled")
    
    dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK_URL')
    dingtalk_secret = os.getenv('DINGTALK_SECRET')
    if dingtalk_webhook:
        dingtalk_integration = DingTalkIntegration(dingtalk_webhook, dingtalk_secret)
        notifier.add_channel(dingtalk_integration)
        logger.info("DingTalk integration enabled")
    
    nlp_parser = NLPParser()
    knowledge_base = KnowledgeBase()
    
    deduplicator = EventDeduplicator(window_seconds=dedup_ttl)
    deduplicator.set_flush_callback(lambda e, c: flush_event_handler(e, c, notifier, knowledge_base))
    deduplicator.start_flush_worker()
    
    health_checker = HealthChecker(k8s_watcher, namespaces)
    health_checker._send_daily_report = lambda r: daily_report_callback(r, notifier)
    health_checker.start()
    
    watcher_thread = threading.Thread(
        target=run_k8s_watcher,
        args=(k8s_watcher, deduplicator, notifier, knowledge_base),
        daemon=True
    )
    watcher_thread.start()
    
    logger.info("Starting notification bot...")
    try:
        if slack_bot_token and slack_signing_secret and slack_channel_id:
            slack_app_token = os.getenv('SLACK_APP_TOKEN')
            slack_integration.start(app_token=slack_app_token)
        else:
            logger.info("No Slack configuration found, running in headless mode")
            while True:
                import time
                time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        deduplicator.stop()
        health_checker.stop()
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        deduplicator.stop()
        health_checker.stop()


if __name__ == '__main__':
    main()
