import os
import json
import time
import threading
import requests
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Callable


class AlertRule:
    def __init__(self, rule_data: Dict[str, Any]):
        self.id = rule_data['id']
        self.name = rule_data['name']
        self.enabled = rule_data.get('enabled', True)
        self.type = rule_data['type']
        self.params = rule_data.get('params', {})
        self.severity = rule_data.get('severity', 'warning')
        self.webhook_urls = rule_data.get('webhook_urls', [])
        self.last_triggered = 0
        self.trigger_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'enabled': self.enabled,
            'type': self.type,
            'params': self.params,
            'severity': self.severity,
            'webhook_urls': self.webhook_urls,
            'last_triggered': self.last_triggered,
            'trigger_count': self.trigger_count
        }


class AlertHistory:
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.alerts = deque(maxlen=max_history)
        self._lock = threading.RLock()

    def add(self, alert: Dict[str, Any]):
        with self._lock:
            self.alerts.appendleft(alert)

    def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.alerts)[:limit]

    def clear(self):
        with self._lock:
            self.alerts.clear()


class WebhookNotifier:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def send(self, webhook_url: str, alert_data: Dict[str, Any]) -> bool:
        try:
            payload = {
                'alert_id': alert_data['rule_id'],
                'alert_name': alert_data['rule_name'],
                'severity': alert_data['severity'],
                'timestamp': alert_data['timestamp'],
                'message': alert_data['message'],
                'details': alert_data.get('details', {})
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Nginx-Log-Analyzer-Alert'
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            return 200 <= response.status_code < 300
        except Exception as e:
            print(f"Webhook notification failed for {webhook_url}: {e}")
            return False


class AlertDetector:
    @staticmethod
    def detect_error_spike(log_parser, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        status_range = params.get('status_code_range', '5xx')
        threshold = params.get('threshold', 5)
        window_minutes = params.get('window_minutes', 5)
        compare_to = params.get('compare_to', 'absolute')
        baseline_multiplier = params.get('baseline_multiplier', 3.0)
        baseline_minutes = params.get('baseline_minutes', 60)

        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        baseline_start = now - timedelta(minutes=baseline_minutes)

        window_logs = log_parser.filter_logs(log_parser.access_logs, start_time=window_start)
        baseline_logs = log_parser.filter_logs(
            log_parser.access_logs,
            start_time=baseline_start,
            end_time=window_start
        )

        def count_errors(logs):
            count = 0
            for log in logs:
                status = log['status']
                if status_range == '5xx' and 500 <= status < 600:
                    count += 1
                elif status_range == '4xx' and 400 <= status < 500:
                    count += 1
                elif status_range == '4xx+5xx' and status >= 400:
                    count += 1
            return count

        window_errors = count_errors(window_logs)
        baseline_errors = count_errors(baseline_logs)

        if compare_to == 'absolute':
            if window_errors >= threshold:
                return {
                    'triggered': True,
                    'message': f'{status_range}错误数量达到 {window_errors}，超过阈值 {threshold}',
                    'details': {
                        'window_errors': window_errors,
                        'threshold': threshold,
                        'window_minutes': window_minutes
                    }
                }
        elif compare_to == 'baseline':
            baseline_avg = baseline_errors / max(baseline_minutes / window_minutes, 1)
            if baseline_avg > 0 and window_errors >= baseline_avg * baseline_multiplier:
                return {
                    'triggered': True,
                    'message': f'{status_range}错误突增到 {window_errors}，是基线 {baseline_avg:.1f} 的 {window_errors/baseline_avg:.1f} 倍',
                    'details': {
                        'window_errors': window_errors,
                        'baseline_avg': baseline_avg,
                        'multiplier': window_errors / baseline_avg,
                        'threshold_multiplier': baseline_multiplier
                    }
                }

        return {'triggered': False}

    @staticmethod
    def detect_log_missing(log_parser, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        no_logs_minutes = params.get('no_logs_minutes', 10)
        min_expected_logs = params.get('min_expected_logs', 1)

        now = datetime.now()
        check_start = now - timedelta(minutes=no_logs_minutes)

        access_logs = log_parser.filter_logs(log_parser.access_logs, start_time=check_start)
        error_logs = log_parser.filter_logs(log_parser.error_logs, start_time=check_start)

        total_logs = len(access_logs) + len(error_logs)

        if total_logs < min_expected_logs:
            return {
                'triggered': True,
                'message': f'过去 {no_logs_minutes} 分钟内只有 {total_logs} 条日志，低于预期的 {min_expected_logs} 条',
                'details': {
                    'total_logs': total_logs,
                    'access_logs': len(access_logs),
                    'error_logs': len(error_logs),
                    'min_expected': min_expected_logs,
                    'check_window_minutes': no_logs_minutes
                }
            }

        return {'triggered': False}

    @staticmethod
    def detect_traffic_anomaly(log_parser, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        window_minutes = params.get('window_minutes', 5)
        baseline_minutes = params.get('baseline_minutes', 60)
        spike_multiplier = params.get('spike_multiplier', 5.0)
        drop_multiplier = params.get('drop_multiplier', 0.2)

        now = datetime.now()
        window_start = now - timedelta(minutes=window_minutes)
        baseline_start = now - timedelta(minutes=baseline_minutes)

        window_logs = log_parser.filter_logs(log_parser.access_logs, start_time=window_start)
        baseline_logs = log_parser.filter_logs(
            log_parser.access_logs,
            start_time=baseline_start,
            end_time=window_start
        )

        window_rate = len(window_logs) / window_minutes
        baseline_rate = len(baseline_logs) / max(baseline_minutes, 1)

        if baseline_rate > 0:
            ratio = window_rate / baseline_rate

            if ratio >= spike_multiplier:
                return {
                    'triggered': True,
                    'message': f'流量突增：当前 {window_rate:.1f} 条/分钟，是基线 {baseline_rate:.1f} 的 {ratio:.1f} 倍',
                    'details': {
                        'window_rate': window_rate,
                        'baseline_rate': baseline_rate,
                        'ratio': ratio,
                        'type': 'spike',
                        'threshold': spike_multiplier
                    }
                }
            elif ratio <= drop_multiplier:
                return {
                    'triggered': True,
                    'message': f'流量骤降：当前 {window_rate:.1f} 条/分钟，只有基线 {baseline_rate:.1f} 的 {ratio*100:.0f}%',
                    'details': {
                        'window_rate': window_rate,
                        'baseline_rate': baseline_rate,
                        'ratio': ratio,
                        'type': 'drop',
                        'threshold': drop_multiplier
                    }
                }

        return {'triggered': False}


class AlertEngine:
    def __init__(self, config, log_parser):
        self.config = config
        self.log_parser = log_parser
        self.enabled = config.ENABLE_ALERT_ENGINE
        self.check_interval = config.ALERT_CHECK_INTERVAL
        self.cooldown_period = config.ALERT_COOLDOWN_PERIOD

        self.rules: Dict[str, AlertRule] = {}
        for rule_data in config.DEFAULT_ALERT_RULES:
            self.rules[rule_data['id']] = AlertRule(rule_data)

        self.global_webhooks = config.DEFAULT_WEBHOOKS

        self.history = AlertHistory(config.MAX_ALERT_HISTORY)
        self.webhook_notifier = WebhookNotifier()
        self.detector = AlertDetector()

        self._stop_event = threading.Event()
        self._check_thread = None
        self._lock = threading.RLock()

    def start(self):
        if not self.enabled:
            print("Alert engine is disabled")
            return False

        if self._check_thread and self._check_thread.is_alive():
            return True

        self._stop_event.clear()
        self._check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self._check_thread.start()
        print(f"Alert engine started, checking every {self.check_interval} seconds")
        return True

    def stop(self):
        self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=5)
            self._check_thread = None
        print("Alert engine stopped")

    def _check_loop(self):
        while not self._stop_event.is_set():
            try:
                self.check_rules()
            except Exception as e:
                print(f"Error in alert check loop: {e}")
            
            self._stop_event.wait(self.check_interval)

    def check_rules(self) -> List[Dict[str, Any]]:
        triggered_alerts = []

        with self._lock:
            for rule_id, rule in self.rules.items():
                if not rule.enabled:
                    continue

                now = time.time()
                if now - rule.last_triggered < self.cooldown_period:
                    continue

                result = self._check_single_rule(rule)
                if result and result.get('triggered'):
                    rule.last_triggered = now
                    rule.trigger_count += 1

                    alert = {
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'severity': rule.severity,
                        'timestamp': datetime.now().isoformat(),
                        'timestamp_epoch': int(now),
                        'message': result.get('message', ''),
                        'details': result.get('details', {})
                    }

                    triggered_alerts.append(alert)
                    self.history.add(alert)
                    self._send_notifications(rule, alert)

        return triggered_alerts

    def _check_single_rule(self, rule: AlertRule) -> Optional[Dict[str, Any]]:
        try:
            if rule.type == 'error_spike':
                return self.detector.detect_error_spike(self.log_parser, rule.params)
            elif rule.type == 'log_missing':
                return self.detector.detect_log_missing(self.log_parser, rule.params)
            elif rule.type == 'traffic_anomaly':
                return self.detector.detect_traffic_anomaly(self.log_parser, rule.params)
            else:
                print(f"Unknown alert rule type: {rule.type}")
                return None
        except Exception as e:
            print(f"Error checking rule {rule.id}: {e}")
            return None

    def _send_notifications(self, rule: AlertRule, alert: Dict[str, Any]):
        webhook_urls = list(rule.webhook_urls) + list(self.global_webhooks)

        for url in webhook_urls:
            threading.Thread(
                target=self.webhook_notifier.send,
                args=(url, alert),
                daemon=True
            ).start()

    def get_rules(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [rule.to_dict() for rule in self.rules.values()]

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rule = self.rules.get(rule_id)
            return rule.to_dict() if rule else None

    def add_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if 'id' not in rule_data:
                rule_data['id'] = f"rule_{int(time.time())}"
            
            rule = AlertRule(rule_data)
            self.rules[rule.id] = rule
            return rule.to_dict()

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            rule = self.rules.get(rule_id)
            if not rule:
                return None

            for key, value in updates.items():
                if hasattr(rule, key) and key != 'id':
                    setattr(rule, key, value)

            return rule.to_dict()

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                return True
            return False

    def toggle_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rule = self.rules.get(rule_id)
            if not rule:
                return None
            rule.enabled = not rule.enabled
            return rule.to_dict()

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history.get_all(limit)

    def clear_alerts(self):
        self.history.clear()

    def test_rule(self, rule_id: str) -> Dict[str, Any]:
        with self._lock:
            rule = self.rules.get(rule_id)
            if not rule:
                return {'error': 'Rule not found'}

            result = self._check_single_rule(rule)
            return {
                'rule_id': rule_id,
                'rule_name': rule.name,
                'would_trigger': result.get('triggered', False) if result else False,
                'result': result
            }

    def send_test_webhook(self, webhook_url: str) -> bool:
        test_alert = {
            'rule_id': 'test',
            'rule_name': '测试告警',
            'severity': 'info',
            'timestamp': datetime.now().isoformat(),
            'timestamp_epoch': int(time.time()),
            'message': '这是一条测试告警消息',
            'details': {'test': True}
        }
        return self.webhook_notifier.send(webhook_url, test_alert)

    def get_global_webhooks(self) -> List[str]:
        return list(self.global_webhooks)

    def add_global_webhook(self, url: str) -> bool:
        with self._lock:
            if url not in self.global_webhooks:
                self.global_webhooks.append(url)
                return True
            return False

    def remove_global_webhook(self, url: str) -> bool:
        with self._lock:
            if url in self.global_webhooks:
                self.global_webhooks.remove(url)
                return True
            return False
