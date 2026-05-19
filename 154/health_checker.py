import logging
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional


class HealthChecker:
    def __init__(self, k8s_watcher, namespaces=None, check_interval=300):
        self.k8s_watcher = k8s_watcher
        self.namespaces = namespaces or ['default']
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.checker_thread = None
        self.daily_report_thread = None
        self.daily_report_hour = 9
        
        self.event_history = defaultdict(list)
        self.check_results = defaultdict(list)

    def start(self):
        self.running = True
        self.checker_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.checker_thread.start()
        
        self.daily_report_thread = threading.Thread(target=self._daily_report_loop, daemon=True)
        self.daily_report_thread.start()
        
        self.logger.info("Health checker started")

    def stop(self):
        self.running = False
        self.logger.info("Health checker stopped")

    def _check_loop(self):
        while self.running:
            try:
                self._perform_check()
            except Exception as e:
                self.logger.error(f"Error during health check: {e}")
            time.sleep(self.check_interval)

    def _perform_check(self) -> Dict:
        result = {
            'timestamp': datetime.now().isoformat(),
            'namespaces': {},
            'issues': []
        }
        
        for namespace in self.namespaces:
            ns_result = self._check_namespace(namespace)
            result['namespaces'][namespace] = ns_result
            result['issues'].extend(ns_result.get('issues', []))
        
        self.check_results[datetime.now().date()].append(result)
        return result

    def _check_namespace(self, namespace: str) -> Dict:
        result = {
            'pods': {
                'total': 0,
                'running': 0,
                'pending': 0,
                'failed': 0,
                'succeeded': 0,
                'unknown': 0
            },
            'issues': []
        }
        
        try:
            pods = self.k8s_watcher.core_v1.list_namespaced_pod(namespace=namespace)
            result['pods']['total'] = len(pods.items)
            
            for pod in pods.items:
                phase = pod.status.phase.lower()
                if phase == 'running':
                    result['pods']['running'] += 1
                elif phase == 'pending':
                    result['pods']['pending'] += 1
                    result['issues'].append({
                        'type': 'pending',
                        'pod': pod.metadata.name,
                        'message': 'Pod is in Pending state'
                    })
                elif phase == 'failed':
                    result['pods']['failed'] += 1
                    result['issues'].append({
                        'type': 'failed',
                        'pod': pod.metadata.name,
                        'message': f'Pod failed with reason: {pod.status.reason}'
                    })
                elif phase == 'succeeded':
                    result['pods']['succeeded'] += 1
                else:
                    result['pods']['unknown'] += 1
                
                for container_status in pod.status.container_statuses or []:
                    if not container_status.ready:
                        if container_status.state.waiting:
                            reason = container_status.state.waiting.reason
                            if reason not in ['ContainerCreating', 'PodInitializing']:
                                result['issues'].append({
                                    'type': 'container_issue',
                                    'pod': pod.metadata.name,
                                    'container': container_status.name,
                                    'reason': reason,
                                    'message': f'Container not ready: {reason}'
                                })
            
            self.logger.info(f"Checked namespace {namespace}: {result['pods']['running']}/{result['pods']['total']} pods running")
            
        except Exception as e:
            self.logger.error(f"Error checking namespace {namespace}: {e}")
        
        return result

    def _daily_report_loop(self):
        while self.running:
            try:
                now = datetime.now()
                next_report = datetime(now.year, now.month, now.day, self.daily_report_hour, 0, 0)
                if now >= next_report:
                    next_report += timedelta(days=1)
                
                sleep_seconds = (next_report - now).total_seconds()
                self.logger.info(f"Next daily report scheduled at {next_report} (in {sleep_seconds:.0f}s)")
                
                time.sleep(sleep_seconds)
                
                if self.running:
                    report = self.generate_daily_report()
                    self._send_daily_report(report)
                    
            except Exception as e:
                self.logger.error(f"Error in daily report loop: {e}")
                time.sleep(3600)

    def generate_daily_report(self) -> Dict:
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        report = {
            'date': today.isoformat(),
            'period': f"{yesterday} 09:00 - {today} 09:00",
            'namespaces': {},
            'summary': {
                'total_events': 0,
                'critical_events': 0,
                'warning_events': 0,
                'pod_restarts': 0
            },
            'top_issues': []
        }
        
        for namespace in self.namespaces:
            ns_report = self._generate_namespace_report(namespace, yesterday, today)
            report['namespaces'][namespace] = ns_report
            report['summary']['total_events'] += ns_report['events']['total']
            report['summary']['critical_events'] += ns_report['events']['critical']
            report['summary']['warning_events'] += ns_report['events']['warning']
            report['summary']['pod_restarts'] += ns_report['pod_restarts']
        
        return report

    def _generate_namespace_report(self, namespace: str, start_date, end_date) -> Dict:
        report = {
            'pods': {},
            'events': {
                'total': 0,
                'critical': 0,
                'warning': 0,
                'normal': 0
            },
            'pod_restarts': 0,
            'issues': []
        }
        
        try:
            pods = self.k8s_watcher.core_v1.list_namespaced_pod(namespace=namespace)
            
            report['pods']['total'] = len(pods.items)
            report['pods']['running'] = sum(1 for p in pods.items if p.status.phase == 'Running')
            report['pods']['failed'] = sum(1 for p in pods.items if p.status.phase == 'Failed')
            report['pods']['pending'] = sum(1 for p in pods.items if p.status.phase == 'Pending')
            
            for pod in pods.items:
                restarts = 0
                for cs in pod.status.container_statuses or []:
                    restarts += cs.restart_count
                report['pod_restarts'] += restarts
                
                if restarts > 5:
                    report['issues'].append({
                        'pod': pod.metadata.name,
                        'type': 'high_restarts',
                        'message': f'Pod restarted {restarts} times'
                    })
        
        except Exception as e:
            self.logger.error(f"Error generating namespace report for {namespace}: {e}")
        
        return report

    def _send_daily_report(self, report: Dict):
        self.logger.info(f"Daily report generated: {report}")

    def format_report_for_slack(self, report: Dict) -> str:
        message = f"""
:calendar: *Kubernetes 每日健康报告 - {report['date']}*

*统计周期:* {report['period']}

*总体摘要:*
• 总事件数: {report['summary']['total_events']}
• 严重事件: {report['summary']['critical_events']}
• 警告事件: {report['summary']['warning_events']}
• Pod 重启次数: {report['summary']['pod_restarts']}

*各命名空间详情:*
"""
        for namespace, ns_report in report['namespaces'].items():
            message += f"\n*{namespace}:*\n"
            message += f"  • Pods: {ns_report['pods']['running']}/{ns_report['pods']['total']} 运行中\n"
            message += f"  • 重启次数: {ns_report['pod_restarts']}\n"
            
            if ns_report['issues']:
                message += f"  • 问题:\n"
                for issue in ns_report['issues']:
                    message += f"    - {issue['pod']}: {issue['message']}\n"
        
        message += "\n*提示*: 发现问题请及时处理！"
        
        return message.strip()

    def run_immediate_check(self) -> Dict:
        return self._perform_check()

    def get_latest_status(self) -> Dict:
        if self.check_results:
            latest_date = max(self.check_results.keys())
            if self.check_results[latest_date]:
                return self.check_results[latest_date][-1]
        return self._perform_check()
