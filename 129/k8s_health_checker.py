#!/usr/bin/env python3
import os
import re
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import urllib.request
import urllib.parse

import yaml
from jinja2 import Template
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('k8s_health_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kubernetes 健康巡检报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header .timestamp { opacity: 0.9; font-size: 14px; }
        .summary { display: grid; grid-template-columns: repeat(6, 1fr); gap: 15px; padding: 20px; background: #f8f9fa; }
        .summary-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .summary-card .number { font-size: 32px; font-weight: bold; }
        .summary-card .label { font-size: 13px; color: #666; margin-top: 5px; }
        .summary-card.critical .number { color: #e74c3c; }
        .summary-card.warning .number { color: #f39c12; }
        .summary-card.success .number { color: #27ae60; }
        .summary-card.info .number { color: #3498db; }
        .section { padding: 20px 30px; }
        .section-title { font-size: 20px; font-weight: 600; color: #2c3e50; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e0e0e0; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-critical { background: #ffebee; color: #c62828; }
        .status-warning { background: #fff3e0; color: #ef6c00; }
        .status-success { background: #e8f5e9; color: #2e7d32; }
        .status-info { background: #e3f2fd; color: #1565c0; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f8f9fa; font-weight: 600; color: #555; }
        tr:hover { background: #f8f9fa; }
        .action-btn { display: inline-block; padding: 6px 12px; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; text-decoration: none; margin-right: 5px; transition: all 0.2s; }
        .action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .btn-restart { background: #3498db; color: white; }
        .btn-drain { background: #e67e22; color: white; }
        .btn-fix { background: #9b59b6; color: white; }
        .btn-alert { background: #e74c3c; color: white; }
        .log-entry { background: #f8f9fa; padding: 10px 15px; border-radius: 6px; margin-bottom: 8px; font-family: monospace; font-size: 12px; border-left: 4px solid; }
        .log-error { border-left-color: #e74c3c; }
        .log-warning { border-left-color: #f39c12; }
        .log-info { border-left-color: #3498db; }
        .empty-state { text-align: center; padding: 40px; color: #999; }
        .pod-phase { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .phase-running { background: #d4edda; color: #155724; }
        .phase-pending { background: #fff3cd; color: #856404; }
        .phase-failed { background: #f8d7da; color: #721c24; }
        .severity-high { background: #fee; color: #c33; }
        .severity-medium { background: #fff8e1; color: #f57c00; }
        .severity-low { background: #e3f2fd; color: #1976d2; }
        .event-group { background: #fafafa; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 4px solid; }
        .event-group.critical { border-left-color: #e74c3c; }
        .event-group.warning { border-left-color: #f39c12; }
        .event-group.normal { border-left-color: #3498db; }
        .quota-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
        .quota-fill { height: 100%; background: linear-gradient(90deg, #27ae60, #f39c12, #e74c3c); }
        .recommendation-box { background: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 8px; padding: 12px; margin-top: 8px; }
        .security-alert { background: #ffebee; border: 1px solid #ef9a9a; border-radius: 8px; padding: 12px; margin-top: 8px; }
        .footer { text-align: center; padding: 20px; color: #999; font-size: 13px; background: #f8f9fa; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Kubernetes 健康巡检报告</h1>
            <div class="timestamp">生成时间: {{ report.timestamp }}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card {% if report.unhealthy_pods_count > 0 %}critical{% else %}success{% endif %}">
                <div class="number">{{ report.unhealthy_pods_count }}</div>
                <div class="label">异常 Pod</div>
            </div>
            <div class="summary-card {% if report.unhealthy_nodes_count > 0 %}critical{% else %}success{% endif %}">
                <div class="number">{{ report.unhealthy_nodes_count }}</div>
                <div class="label">异常 Node</div>
            </div>
            <div class="summary-card warning">
                <div class="number">{{ report.quota_recommendations_count }}</div>
                <div class="label">配额建议</div>
            </div>
            <div class="summary-card {% if report.image_security_issues_count > 0 %}critical{% else %}info{% endif %}">
                <div class="number">{{ report.image_security_issues_count }}</div>
                <div class="label">镜像安全</div>
            </div>
            <div class="summary-card {% if report.aggregated_events_count > 0 %}warning{% else %}success{% endif %}">
                <div class="number">{{ report.aggregated_events_count }}</div>
                <div class="label">事件告警</div>
            </div>
            <div class="summary-card info">
                <div class="number">{{ report.evicted_count }}</div>
                <div class="label">已驱逐节点</div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📦 异常 Pod 列表</div>
            {% if report.unhealthy_pods %}
            <table>
                <thead>
                    <tr>
                        <th>命名空间</th>
                        <th>Pod 名称</th>
                        <th>状态</th>
                        <th>容器</th>
                        <th>重启次数</th>
                        <th>原因</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {% for pod in report.unhealthy_pods %}
                    <tr>
                        <td><code>{{ pod.namespace }}</code></td>
                        <td>{{ pod.name }}</td>
                        <td><span class="pod-phase phase-{{ pod.phase|lower }}">{{ pod.phase }}</span></td>
                        <td>{{ pod.container|default('-', true) }}</td>
                        <td>{{ pod.restart_count|default(0, true) }}</td>
                        <td><span class="status-badge status-critical">{{ pod.reason }}</span></td>
                        <td>
                            <button class="action-btn btn-restart" onclick="alert('重启 Pod: {{ pod.namespace }}/{{ pod.name }}')">🔄 重启</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state"><p>🎉 所有 Pod 运行正常！</p></div>
            {% endif %}
        </div>
        
        <div class="section">
            <div class="section-title">💡 资源配额建议</div>
            {% if report.quota_recommendations %}
            <table>
                <thead>
                    <tr>
                        <th>命名空间</th>
                        <th>Pod/工作负载</th>
                        <th>资源类型</th>
                        <th>当前配置</th>
                        <th>使用率</th>
                        <th>建议配置</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rec in report.quota_recommendations %}
                    <tr>
                        <td><code>{{ rec.namespace }}</code></td>
                        <td>{{ rec.name }}</td>
                        <td>{{ rec.resource_type }}</td>
                        <td>{{ rec.current }}</td>
                        <td>
                            <div class="quota-bar">
                                <div class="quota-fill" style="width: {{ rec.usage_percent }}%"></div>
                            </div>
                            <small>{{ rec.usage_percent }}%</small>
                        </td>
                        <td>
                            <div class="recommendation-box">
                                <strong>{{ rec.recommended }}</strong>
                                <br><small>{{ rec.reason }}</small>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state"><p>✨ 当前资源配置合理，无需调整</p></div>
            {% endif %}
        </div>
        
        <div class="section">
            <div class="section-title">🔒 镜像安全分析</div>
            {% if report.image_security_issues %}
            <table>
                <thead>
                    <tr>
                        <th>命名空间</th>
                        <th>Pod</th>
                        <th>镜像</th>
                        <th>严重程度</th>
                        <th>问题描述</th>
                        <th>安全建议</th>
                    </tr>
                </thead>
                <tbody>
                    {% for issue in report.image_security_issues %}
                    <tr>
                        <td><code>{{ issue.namespace }}</code></td>
                        <td>{{ issue.pod_name }}</td>
                        <td><code>{{ issue.image }}</code></td>
                        <td><span class="status-badge severity-{{ issue.severity }}">{{ issue.severity|upper }}</span></td>
                        <td>{{ issue.description }}</td>
                        <td>
                            <div class="security-alert">
                                <strong>推荐:</strong> {{ issue.recommendation }}
                                {% if issue.safe_version %}
                                <br><strong>安全版本:</strong> <code>{{ issue.safe_version }}</code>
                                {% endif %}
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div class="empty-state"><p>🔐 所有镜像安全检查通过！</p></div>
            {% endif %}
        </div>
        
        <div class="section">
            <div class="section-title">⚠️ 聚合事件告警</div>
            {% if report.aggregated_events %}
                {% for event_type, events in report.aggregated_events.items() %}
                <div class="event-group {{ events.severity }}">
                    <h4>{{ event_type }} ({{ events.count }} 次)</h4>
                    <p><strong>涉及对象:</strong> {{ events.objects|join(', ') }}</p>
                    <p><strong>消息示例:</strong> {{ events.sample_message }}</p>
                    <p><strong>首次出现:</strong> {{ events.first_seen }}</p>
                    <p><strong>最后出现:</strong> {{ events.last_seen }}</p>
                </div>
                {% endfor %}
            {% else %}
            <div class="empty-state"><p>✅ 近期无异常事件！</p></div>
            {% endif %}
        </div>
        
        {% if report.warnings or report.errors %}
        <div class="section">
            <div class="section-title">📋 其他警告与错误</div>
            {% for warning in report.warnings %}
            <div class="log-entry log-warning">⚠️ {{ warning }}</div>
            {% endfor %}
            {% for error in report.errors %}
            <div class="log-entry log-error">❌ {{ error }}</div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Kubernetes Health Checker v2.0 | 自动巡检工具</p>
        </div>
    </div>
</body>
</html>
"""


@dataclass
class RestartBackoff:
    pod_key: str
    restart_count: int = 0
    last_restart_time: Optional[datetime] = None
    next_allowed_time: Optional[datetime] = None
    
    def calculate_backoff(self) -> timedelta:
        base_delay = 10
        max_delay = 300
        delay = min(base_delay * (2 ** self.restart_count), max_delay)
        return timedelta(seconds=delay)
    
    def can_restart_now(self) -> bool:
        if not self.next_allowed_time:
            return True
        return datetime.now() >= self.next_allowed_time
    
    def record_restart(self):
        self.restart_count += 1
        self.last_restart_time = datetime.now()
        self.next_allowed_time = datetime.now() + self.calculate_backoff()


@dataclass
class HealthReport:
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    unhealthy_pods: List[Dict] = field(default_factory=list)
    unhealthy_nodes: List[Dict] = field(default_factory=list)
    restarted_containers: List[Dict] = field(default_factory=list)
    evicted_nodes: List[Dict] = field(default_factory=list)
    quota_recommendations: List[Dict] = field(default_factory=list)
    image_security_issues: List[Dict] = field(default_factory=list)
    aggregated_events: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def unhealthy_pods_count(self) -> int:
        return len(self.unhealthy_pods)
    
    @property
    def unhealthy_nodes_count(self) -> int:
        return len(self.unhealthy_nodes)
    
    @property
    def restarted_count(self) -> int:
        return len(self.restarted_containers)
    
    @property
    def evicted_count(self) -> int:
        return len(self.evicted_nodes)
    
    @property
    def errors_count(self) -> int:
        return len(self.errors)
    
    @property
    def quota_recommendations_count(self) -> int:
        return len(self.quota_recommendations)
    
    @property
    def image_security_issues_count(self) -> int:
        return len(self.image_security_issues)
    
    @property
    def aggregated_events_count(self) -> int:
        return sum(v['count'] for v in self.aggregated_events.values())


class K8sResourceCache:
    def __init__(self):
        self.pods: Dict[str, client.V1Pod] = {}
        self.nodes: Dict[str, client.V1Node] = {}
        self.pdbs: Dict[str, client.V1PodDisruptionBudget] = {}
        self.events: List[client.V1Event] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._watch_threads: List[threading.Thread] = []
    
    def add_pod(self, pod: client.V1Pod):
        key = f"{pod.metadata.namespace}/{pod.metadata.name}"
        with self._lock:
            self.pods[key] = pod
    
    def remove_pod(self, namespace: str, name: str):
        key = f"{namespace}/{name}"
        with self._lock:
            self.pods.pop(key, None)
    
    def get_all_pods(self) -> List[client.V1Pod]:
        with self._lock:
            return list(self.pods.values())
    
    def add_node(self, node: client.V1Node):
        key = node.metadata.name
        with self._lock:
            self.nodes[key] = node
    
    def remove_node(self, name: str):
        with self._lock:
            self.nodes.pop(name, None)
    
    def get_all_nodes(self) -> List[client.V1Node]:
        with self._lock:
            return list(self.nodes.values())
    
    def add_pdb(self, pdb: client.V1PodDisruptionBudget):
        key = f"{pdb.metadata.namespace}/{pdb.metadata.name}"
        with self._lock:
            self.pdbs[key] = pdb
    
    def remove_pdb(self, namespace: str, name: str):
        key = f"{namespace}/{name}"
        with self._lock:
            self.pdbs.pop(key, None)
    
    def get_all_pdbs(self) -> List[client.V1PodDisruptionBudget]:
        with self._lock:
            return list(self.pdbs.values())
    
    def add_event(self, event: client.V1Event):
        with self._lock:
            self.events.append(event)
            if len(self.events) > 1000:
                self.events = self.events[-500:]
    
    def get_all_events(self) -> List[client.V1Event]:
        with self._lock:
            return list(self.events)
    
    def stop(self):
        self._stop_event.set()
        for t in self._watch_threads:
            t.join(timeout=5)


class AlertRouter:
    def __init__(self, webhook_configs: Dict[str, str] = None):
        self.webhooks = webhook_configs or {}
    
    def send_dingtalk(self, title: str, message: str) -> bool:
        if 'dingtalk' not in self.webhooks:
            return False
        
        webhook_url = self.webhooks['dingtalk']
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\\n\\n{message}"
            }
        }
        
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"DingTalk alert failed: {e}")
            return False
    
    def send_wework(self, title: str, message: str) -> bool:
        if 'wework' not in self.webhooks:
            return False
        
        webhook_url = self.webhooks['wework']
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\\n\\n{message}"
            }
        }
        
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return result.get('errcode') == 0
        except Exception as e:
            logger.error(f"WeWork alert failed: {e}")
            return False
    
    def send_alert(self, title: str, message: str, channels: List[str] = None) -> Dict[str, bool]:
        results = {}
        channels = channels or ['dingtalk', 'wework']
        
        if 'dingtalk' in channels:
            results['dingtalk'] = self.send_dingtalk(title, message)
        if 'wework' in channels:
            results['wework'] = self.send_wework(title, message)
        
        return results


class ImageSecurityAnalyzer:
    LATEST_TAG_PATTERN = re.compile(r':latest$|:[^/]+$')
    DIGEST_PATTERN = re.compile(r'@sha256:[a-f0-9]{64}$')
    
    VULNERABLE_VERSIONS = {
        'nginx': {'1.19': '1.25.3-alpine', '1.20': '1.25.3-alpine'},
        'node': {'14': '20.9.0-alpine', '16': '20.9.0-alpine'},
        'python': {'3.8': '3.12.0-slim', '3.9': '3.12.0-slim'},
        'mysql': {'5.7': '8.2.0', '8.0': '8.2.0'},
        'redis': {'6': '7.2.3-alpine', '6.2': '7.2.3-alpine'},
    }
    
    @classmethod
    def analyze_image(cls, image: str) -> Tuple[bool, List[Dict]]:
        issues = []
        
        if ':latest' in image:
            issues.append({
                'severity': 'medium',
                'description': '使用 latest 标签，版本不可控',
                'recommendation': '使用固定版本标签',
                'safe_version': None
            })
        
        if '@sha256:' not in image:
            issues.append({
                'severity': 'low',
                'description': '未使用摘要固定镜像',
                'recommendation': '使用 @sha256 摘要固定镜像版本',
                'safe_version': None
            })
        
        for base_image, versions in cls.VULNERABLE_VERSIONS.items():
            if base_image in image.lower():
                for old_ver, safe_ver in versions.items():
                    if old_ver in image:
                        issues.append({
                            'severity': 'high',
                            'description': f'使用存在已知漏洞的 {base_image}:{old_ver} 版本',
                            'recommendation': '升级到安全版本',
                            'safe_version': safe_ver
                        })
        
        if 'alpine' not in image.lower() and 'slim' not in image.lower():
            if not any(x in image.lower() for x in ['distroless', 'scratch']):
                issues.append({
                    'severity': 'low',
                    'description': '基础镜像体积较大，攻击面可能较大',
                    'recommendation': '考虑使用 alpine、slim 或 distroless 变体',
                    'safe_version': None
                })
        
        return len(issues) == 0, issues


class K8sHealthChecker:
    def __init__(self, config_path: Optional[str] = None, in_cluster: bool = False, 
                 use_watch: bool = True, alert_webhooks: Dict[str, str] = None):
        self.core_v1 = None
        self.apps_v1 = None
        self.policy_v1 = None
        self.custom_objects_api = None
        self.report = HealthReport()
        self.backoff_tracker: Dict[str, RestartBackoff] = {}
        self.cache = K8sResourceCache()
        self.use_watch = use_watch
        self.alert_router = AlertRouter(alert_webhooks)
        
        self._init_k8s_client(config_path, in_cluster)
        
        if use_watch:
            self._start_watchers()
    
    def _init_k8s_client(self, config_path: Optional[str], in_cluster: bool):
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config(config_file=config_path)
            
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.policy_v1 = client.PolicyV1Api()
            self.custom_objects_api = client.CustomObjectsApi()
            
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise
    
    def _start_watchers(self):
        logger.info("Starting watch threads for cache synchronization")
        
        def watch_pods():
            w = watch.Watch()
            try:
                for event in w.stream(self.core_v1.list_pod_for_all_namespaces):
                    if self.cache._stop_event.is_set():
                        break
                    pod = event['object']
                    if event['type'] == 'DELETED':
                        self.cache.remove_pod(pod.metadata.namespace, pod.metadata.name)
                    else:
                        self.cache.add_pod(pod)
            except Exception as e:
                logger.error(f"Pod watch error: {e}")
        
        def watch_nodes():
            w = watch.Watch()
            try:
                for event in w.stream(self.core_v1.list_node):
                    if self.cache._stop_event.is_set():
                        break
                    node = event['object']
                    if event['type'] == 'DELETED':
                        self.cache.remove_node(node.metadata.name)
                    else:
                        self.cache.add_node(node)
            except Exception as e:
                logger.error(f"Node watch error: {e}")
        
        def watch_events():
            w = watch.Watch()
            try:
                for event in w.stream(self.core_v1.list_event_for_all_namespaces):
                    if self.cache._stop_event.is_set():
                        break
                    self.cache.add_event(event['object'])
            except Exception as e:
                logger.error(f"Event watch error: {e}")
        
        self._initial_sync()
        
        threads = [
            threading.Thread(target=watch_pods, daemon=True),
            threading.Thread(target=watch_nodes, daemon=True),
            threading.Thread(target=watch_events, daemon=True)
        ]
        
        for t in threads:
            t.start()
        
        self.cache._watch_threads.extend(threads)
        logger.info("All watch threads started")
    
    def _initial_sync(self):
        logger.info("Performing initial resource sync")
        try:
            pods = self.core_v1.list_pod_for_all_namespaces(watch=False)
            for pod in pods.items:
                self.cache.add_pod(pod)
            
            nodes = self.core_v1.list_node(watch=False)
            for node in nodes.items:
                self.cache.add_node(node)
            
            events = self.core_v1.list_event_for_all_namespaces(watch=False)
            for event in events.items:
                self.cache.add_event(event)
            
            logger.info(f"Initial sync: {len(self.cache.pods)} pods, {len(self.cache.nodes)} nodes, {len(self.cache.events)} events")
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
    
    def _get_pods(self, namespace: str = "all") -> List[client.V1Pod]:
        if self.use_watch:
            pods = self.cache.get_all_pods()
            if namespace != "all":
                pods = [p for p in pods if p.metadata.namespace == namespace]
            return pods
        else:
            if namespace == "all":
                return self.core_v1.list_pod_for_all_namespaces(watch=False).items
            else:
                return self.core_v1.list_namespaced_pod(namespace, watch=False).items
    
    def _get_nodes(self) -> List[client.V1Node]:
        if self.use_watch:
            return self.cache.get_all_nodes()
        else:
            return self.core_v1.list_node(watch=False).items
    
    def analyze_resource_quotas(self) -> List[Dict]:
        logger.info("Analyzing resource usage and generating quota recommendations")
        recommendations = []
        
        try:
            pods = self._get_pods()
            
            for pod in pods:
                namespace = pod.metadata.namespace
                pod_name = pod.metadata.name
                
                for container in pod.spec.containers:
                    resources = container.resources or client.V1ResourceRequirements()
                    limits = resources.limits or {}
                    requests = resources.requests or {}
                    
                    cpu_request = self._parse_cpu(requests.get('cpu', '0'))
                    cpu_limit = self._parse_cpu(limits.get('cpu', '0'))
                    mem_request = self._parse_memory(requests.get('memory', '0'))
                    mem_limit = self._parse_memory(limits.get('memory', '0'))
                    
                    if cpu_request == 0 and cpu_limit == 0:
                        recommendations.append({
                            'namespace': namespace,
                            'name': f"{pod_name}/{container.name}",
                            'resource_type': 'CPU',
                            'current': '未设置',
                            'usage_percent': 100,
                            'recommended': 'requests: 100m, limits: 500m',
                            'reason': '未设置CPU资源限制，存在资源耗尽风险'
                        })
                    
                    if mem_request == 0 and mem_limit == 0:
                        recommendations.append({
                            'namespace': namespace,
                            'name': f"{pod_name}/{container.name}",
                            'resource_type': 'Memory',
                            'current': '未设置',
                            'usage_percent': 100,
                            'recommended': 'requests: 256Mi, limits: 1Gi',
                            'reason': '未设置内存资源限制，存在OOM风险'
                        })
                    
                    if cpu_request > 0 and cpu_limit / cpu_request > 5:
                        recommendations.append({
                            'namespace': namespace,
                            'name': f"{pod_name}/{container.name}",
                            'resource_type': 'CPU',
                            'current': f"req: {requests.get('cpu')}, lim: {limits.get('cpu')}",
                            'usage_percent': 80,
                            'recommended': f"将 limit 调整为 request 的 2-3 倍，建议: {cpu_request * 3}m",
                            'reason': 'CPU limit/request 比值过大，QoS保障不足'
                        })
                    
                    if mem_request > 0 and mem_limit / mem_request > 2:
                        recommendations.append({
                            'namespace': namespace,
                            'name': f"{pod_name}/{container.name}",
                            'resource_type': 'Memory',
                            'current': f"req: {requests.get('memory')}, lim: {limits.get('memory')}",
                            'usage_percent': 85,
                            'recommended': f"将 limit 调整为 request 的 1.5 倍，建议: {int(mem_request * 1.5)}Mi",
                            'reason': 'Memory limit/request 比值过大'
                        })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Resource quota analysis failed: {e}")
            return []
    
    @staticmethod
    def _parse_cpu(value: str) -> int:
        if not value:
            return 0
        value = str(value)
        if value.endswith('m'):
            return int(value[:-1])
        if value.endswith('n'):
            return int(value[:-1]) // 1000000
        try:
            return int(float(value) * 1000)
        except:
            return 0
    
    @staticmethod
    def _parse_memory(value: str) -> int:
        if not value:
            return 0
        value = str(value)
        units = {'Ki': 1, 'Mi': 1024, 'Gi': 1024*1024, 'Ti': 1024*1024*1024}
        for unit, multiplier in units.items():
            if value.endswith(unit):
                try:
                    return int(float(value[:-len(unit)]) * multiplier)
                except:
                    return 0
        try:
            return int(value) // (1024 * 1024)
        except:
            return 0
    
    def analyze_image_security(self) -> List[Dict]:
        logger.info("Analyzing image security")
        issues = []
        
        try:
            pods = self._get_pods()
            
            for pod in pods:
                namespace = pod.metadata.namespace
                pod_name = pod.metadata.name
                
                for container in pod.spec.containers:
                    image = container.image
                    ok, image_issues = ImageSecurityAnalyzer.analyze_image(image)
                    
                    for issue in image_issues:
                        issues.append({
                            'namespace': namespace,
                            'pod_name': pod_name,
                            'container_name': container.name,
                            'image': image,
                            **issue
                        })
            
            self.report.image_security_issues = issues
            return issues
            
        except Exception as e:
            logger.error(f"Image security analysis failed: {e}")
            return []
    
    def aggregate_events(self, time_window_hours: int = 24) -> Dict[str, Any]:
        logger.info("Aggregating events")
        aggregated = defaultdict(lambda: {
            'count': 0,
            'severity': 'normal',
            'objects': set(),
            'sample_message': '',
            'first_seen': None,
            'last_seen': None
        })
        
        try:
            events = self.cache.get_all_events()
            cutoff_time = datetime.now(datetime.timezone.utc) - timedelta(hours=time_window_hours)
            
            for event in events:
                event_time = event.last_timestamp or event.event_time
                if event_time and event_time < cutoff_time:
                    continue
                
                event_type = event.reason or 'Unknown'
                event_type_key = f"{event.type or 'Normal'}: {event_type}"
                
                agg = aggregated[event_type_key]
                agg['count'] += 1
                
                obj_ref = event.involved_object
                if obj_ref:
                    obj_desc = f"{obj_ref.kind or 'Unknown'}/{obj_ref.name or 'Unknown'}"
                    agg['objects'].add(obj_desc)
                
                if not agg['sample_message']:
                    agg['sample_message'] = event.message or ''
                
                if event_time:
                    event_time_str = event_time.strftime('%Y-%m-%d %H:%M:%S')
                    if not agg['first_seen'] or event_time_str < agg['first_seen']:
                        agg['first_seen'] = event_time_str
                    if not agg['last_seen'] or event_time_str > agg['last_seen']:
                        agg['last_seen'] = event_time_str
                
                if event.type == 'Warning':
                    agg['severity'] = 'warning'
                if event.type == 'Normal' and agg['severity'] == 'normal':
                    agg['severity'] = 'normal'
            
            for key in aggregated:
                aggregated[key]['objects'] = list(aggregated[key]['objects'])[:10]
            
            result = dict(sorted(aggregated.items(), key=lambda x: x[1]['count'], reverse=True))
            self.report.aggregated_events = result
            
            return result
            
        except Exception as e:
            logger.error(f"Event aggregation failed: {e}")
            return {}
    
    def send_alerts(self, channels: List[str] = None) -> Dict[str, bool]:
        logger.info("Sending alerts")
        
        critical_count = len(self.report.unhealthy_pods) + len(self.report.unhealthy_nodes)
        high_severity_images = sum(1 for i in self.report.image_security_issues if i['severity'] == 'high')
        
        if critical_count == 0 and high_severity_images == 0:
            logger.info("No critical issues to alert")
            return {}
        
        title = "🚨 Kubernetes 巡检告警"
        lines = [f"**巡检时间:** {self.report.timestamp}", ""]
        
        if self.report.unhealthy_pods:
            lines.append(f"**异常 Pod:** {len(self.report.unhealthy_pods)} 个")
            for pod in self.report.unhealthy_pods[:5]:
                lines.append(f"- `{pod['namespace']}/{pod['name']}`: {pod['reason']}")
            lines.append("")
        
        if self.report.unhealthy_nodes:
            lines.append(f"**异常 Node:** {len(self.report.unhealthy_nodes)} 个")
            for node in self.report.unhealthy_nodes[:3]:
                lines.append(f"- {node['name']}: {node['reason']}")
            lines.append("")
        
        if high_severity_images > 0:
            lines.append(f"**高危镜像:** {high_severity_images} 个")
        
        message = "\\n".join(lines)
        
        return self.alert_router.send_alert(title, message, channels)
    
    def check_pods(self, namespace: str = "all") -> List[Dict]:
        logger.info(f"Checking Pod status in namespace: {namespace}")
        unhealthy_pods = []
        
        try:
            pods = self._get_pods(namespace)
            
            for pod in pods:
                pod_status = self._analyze_pod_status(pod)
                if pod_status:
                    unhealthy_pods.append(pod_status)
                    logger.warning(f"Unhealthy Pod: {pod.metadata.namespace}/{pod.metadata.name} - {pod_status['reason']}")
            
            self.report.unhealthy_pods = unhealthy_pods
            return unhealthy_pods
            
        except ApiException as e:
            error_msg = f"API error checking pods: {e}"
            logger.error(error_msg)
            self.report.errors.append(error_msg)
            return []
    
    def _analyze_pod_status(self, pod: client.V1Pod) -> Optional[Dict]:
        phase = pod.status.phase
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        
        if phase in ["Succeeded", "Running"]:
            for container_status in pod.status.container_statuses or []:
                if not container_status.ready:
                    state = container_status.state
                    reason = "Unknown"
                    is_crashloop = False
                    
                    if state.waiting:
                        reason = f"Waiting: {state.waiting.reason}"
                        is_crashloop = "CrashLoopBackOff" in state.waiting.reason
                    elif state.terminated:
                        reason = f"Terminated: {state.terminated.reason}"
                        is_crashloop = "Error" in state.terminated.reason
                    
                    if is_crashloop or not container_status.ready:
                        return {
                            "namespace": namespace,
                            "name": pod_name,
                            "phase": phase,
                            "reason": reason,
                            "container": container_status.name,
                            "restart_count": container_status.restart_count,
                            "is_crashloop": is_crashloop
                        }
            return None
        
        if phase != "Running":
            return {
                "namespace": namespace,
                "name": pod_name,
                "phase": phase,
                "reason": f"Pod in {phase} state"
            }
        
        return None
    
    def check_nodes(self) -> List[Dict]:
        logger.info("Checking Node status")
        unhealthy_nodes = []
        
        try:
            nodes = self._get_nodes()
            
            for node in nodes:
                node_status = self._analyze_node_status(node)
                if node_status:
                    unhealthy_nodes.append(node_status)
                    logger.warning(f"Unhealthy Node: {node.metadata.name} - {node_status['reason']}")
            
            self.report.unhealthy_nodes = unhealthy_nodes
            return unhealthy_nodes
            
        except ApiException as e:
            error_msg = f"API error checking nodes: {e}"
            logger.error(error_msg)
            self.report.errors.append(error_msg)
            return []
    
    def _analyze_node_status(self, node: client.V1Node) -> Optional[Dict]:
        node_name = node.metadata.name
        conditions = node.status.conditions
        
        for condition in conditions:
            if condition.type == "Ready":
                if condition.status != "True":
                    return {
                        "name": node_name,
                        "ready": False,
                        "unschedulable": node.spec.unschedulable,
                        "reason": condition.reason or "Unknown",
                        "message": condition.message
                    }
                break
        
        if node.spec.unschedulable:
            return {
                "name": node_name,
                "ready": True,
                "unschedulable": True,
                "reason": "Node is marked unschedulable"
            }
        
        return None
    
    def _get_backoff(self, pod_key: str) -> RestartBackoff:
        if pod_key not in self.backoff_tracker:
            self.backoff_tracker[pod_key] = RestartBackoff(pod_key=pod_key)
        return self.backoff_tracker[pod_key]
    
    def restart_crashing_containers(self, max_restarts: int = 5, dry_run: bool = False) -> List[Dict]:
        logger.info(f"Restarting crashing containers with backoff (max_restarts: {max_restarts}, dry_run: {dry_run})")
        restarted = []
        
        for pod_info in self.report.unhealthy_pods:
            pod_key = f"{pod_info['namespace']}/{pod_info['name']}"
            
            if "is_crashloop" in pod_info and pod_info["is_crashloop"]:
                backoff = self._get_backoff(pod_key)
                
                if backoff.restart_count >= max_restarts:
                    warning_msg = f"Skipping {pod_key}: reached max restarts ({max_restarts})"
                    logger.warning(warning_msg)
                    self.report.warnings.append(warning_msg)
                    continue
                
                if not backoff.can_restart_now():
                    wait_seconds = (backoff.next_allowed_time - datetime.now()).total_seconds()
                    warning_msg = f"Skipping {pod_key}: backoff active, next allowed in {wait_seconds:.1f}s"
                    logger.warning(warning_msg)
                    self.report.warnings.append(warning_msg)
                    continue
                
                try:
                    if not dry_run:
                        self.core_v1.delete_namespaced_pod(
                            name=pod_info["name"],
                            namespace=pod_info["namespace"],
                            body=client.V1DeleteOptions(grace_period_seconds=0)
                        )
                    
                    backoff.record_restart()
                    backoff_delay = backoff.calculate_backoff().total_seconds()
                    
                    restart_info = {
                        "timestamp": datetime.now().isoformat(),
                        "namespace": pod_info["namespace"],
                        "pod_name": pod_info["name"],
                        "container": pod_info.get("container", "unknown"),
                        "restart_count": pod_info.get("restart_count", 0),
                        "backoff_restart_count": backoff.restart_count,
                        "next_backoff_delay": backoff_delay,
                        "dry_run": dry_run
                    }
                    restarted.append(restart_info)
                    logger.info(f"{'Would restart' if dry_run else 'Restarted'} container: {pod_key}, next backoff: {backoff_delay}s")
                    
                except ApiException as e:
                    error_msg = f"Failed to restart pod {pod_key}: {e}"
                    logger.error(error_msg)
                    self.report.errors.append(error_msg)
        
        self.report.restarted_containers = restarted
        return restarted
    
    def check_pdb_for_node(self, node_name: str) -> Tuple[bool, List[str]]:
        logger.info(f"Checking PDB minAvailable for node: {node_name}")
        pdb_violations = []
        
        try:
            pdbs = self.policy_v1.list_pod_disruption_budget_for_all_namespaces(watch=False).items
            all_pods = self._get_pods()
            
            pods_on_node = [p for p in all_pods if p.spec.node_name == node_name]
            
            for pdb in pdbs:
                pdb_namespace = pdb.metadata.namespace
                pdb_name = pdb.metadata.name
                
                selector = pdb.spec.selector
                if not selector:
                    continue
                
                match_labels = selector.match_labels or {}
                if not match_labels:
                    continue
                
                affected_pods = []
                for pod in pods_on_node:
                    if pod.metadata.namespace != pdb_namespace:
                        continue
                    pod_labels = pod.metadata.labels or {}
                    match = True
                    for k, v in match_labels.items():
                        if pod_labels.get(k) != v:
                            match = False
                            break
                    if match:
                        affected_pods.append(pod)
                
                if not affected_pods:
                    continue
                
                min_available = pdb.spec.min_available
                if min_available is None:
                    continue
                
                if isinstance(min_available, str) and '%' in min_available:
                    percentage = int(min_available.replace('%', ''))
                    total_matching_pods = [
                        p for p in all_pods
                        if p.metadata.namespace == pdb_namespace
                        and all(p.metadata.labels.get(k) == v for k, v in match_labels.items())
                    ]
                    min_count = int(len(total_matching_pods) * percentage / 100)
                else:
                    min_count = int(min_available)
                
                current_available = pdb.status.current_healthy or 0
                pods_to_evict_count = len(affected_pods)
                
                if current_available - pods_to_evict_count < min_count:
                    violation = (
                        f"PDB {pdb_namespace}/{pdb_name}: minAvailable={min_count}, "
                        f"current_healthy={current_available}, "
                        f"pods_to_evict={pods_to_evict_count} -> "
                        f"After eviction: {current_available - pods_to_evict_count} < {min_count}"
                    )
                    pdb_violations.append(violation)
                    logger.warning(f"PDB Violation: {violation}")
            
            return len(pdb_violations) == 0, pdb_violations
            
        except ApiException as e:
            error_msg = f"API error checking PDB: {e}"
            logger.error(error_msg)
            self.report.errors.append(error_msg)
            return False, [error_msg]
    
    def drain_node(self, node_name: str, dry_run: bool = False, ignore_pdb: bool = False) -> bool:
        logger.info(f"Draining node: {node_name} (dry_run: {dry_run}, ignore_pdb: {ignore_pdb})")
        
        if not ignore_pdb:
            pdb_ok, violations = self.check_pdb_for_node(node_name)
            if not pdb_ok:
                for violation in violations:
                    self.report.warnings.append(violation)
                logger.error(f"Cannot drain node {node_name} due to PDB violations")
                return False
        
        try:
            if not dry_run:
                body = {"spec": {"unschedulable": True}}
                self.core_v1.patch_node(node_name, body)
                logger.info(f"Node {node_name} marked as unschedulable")
            
            all_pods = self._get_pods()
            pods_on_node = [p for p in all_pods if p.spec.node_name == node_name]
            
            evicted = []
            for pod in pods_on_node:
                if pod.metadata.namespace != "kube-system":
                    try:
                        if not dry_run:
                            self.core_v1.create_namespaced_pod_eviction(
                                name=pod.metadata.name,
                                namespace=pod.metadata.namespace,
                                body=client.V1Eviction(
                                    metadata=client.V1ObjectMeta(name=pod.metadata.name)
                                )
                            )
                        evicted.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
                        logger.info(f"{'Would evict' if dry_run else 'Evicted'} pod: {pod.metadata.namespace}/{pod.metadata.name}")
                    except ApiException as e:
                        error_msg = f"Failed to evict pod {pod.metadata.namespace}/{pod.metadata.name}: {e}"
                        logger.warning(error_msg)
                        self.report.warnings.append(error_msg)
            
            self.report.evicted_nodes.append({
                "node_name": node_name,
                "evicted_pods": evicted,
                "dry_run": dry_run
            })
            
            return True
            
        except ApiException as e:
            error_msg = f"Failed to drain node {node_name}: {e}"
            logger.error(error_msg)
            self.report.errors.append(error_msg)
            return False
    
    def generate_report(self, output_format: str = "html") -> str:
        logger.info(f"Generating health report in {output_format} format")
        
        if output_format == "yaml":
            report_dict = {
                'timestamp': self.report.timestamp,
                'unhealthy_pods': self.report.unhealthy_pods,
                'unhealthy_nodes': self.report.unhealthy_nodes,
                'quota_recommendations': self.report.quota_recommendations,
                'image_security_issues': self.report.image_security_issues,
                'aggregated_events': self.report.aggregated_events,
                'warnings': self.report.warnings,
                'errors': self.report.errors
            }
            return yaml.dump(report_dict, default_flow_style=False, indent=2, allow_unicode=True)
        
        if output_format == "html":
            template = Template(HTML_REPORT_TEMPLATE)
            return template.render(report=self.report)
        
        lines = [
            "=" * 80,
            f"KUBERNETES HEALTH CHECK REPORT - {self.report.timestamp}",
            "=" * 80,
            "",
            f"UNHEALTHY PODS ({len(self.report.unhealthy_pods)}):",
            "-" * 40
        ]
        
        for pod in self.report.unhealthy_pods:
            lines.append(f"  - {pod['namespace']}/{pod['name']}: {pod['reason']}")
        
        lines.extend([
            "",
            f"RESOURCE QUOTA RECOMMENDATIONS ({len(self.report.quota_recommendations)}):",
            "-" * 40
        ])
        
        for rec in self.report.quota_recommendations:
            lines.append(f"  - {rec['namespace']}/{rec['name']} ({rec['resource_type']}):")
            lines.append(f"    Current: {rec['current']}")
            lines.append(f"    Recommended: {rec['recommended']}")
            lines.append(f"    Reason: {rec['reason']}")
        
        lines.extend([
            "",
            f"IMAGE SECURITY ISSUES ({len(self.report.image_security_issues)}):",
            "-" * 40
        ])
        
        for issue in self.report.image_security_issues:
            lines.append(f"  - [{issue['severity'].upper()}] {issue['namespace']}/{issue['pod_name']}:")
            lines.append(f"    Image: {issue['image']}")
            lines.append(f"    {issue['description']}")
            lines.append(f"    Recommendation: {issue['recommendation']}")
        
        lines.extend([
            "",
            f"AGGREGATED EVENTS ({len(self.report.aggregated_events)} types):",
            "-" * 40
        ])
        
        for event_type, events in self.report.aggregated_events.items():
            lines.append(f"  - {event_type}: {events['count']} occurrences")
        
        lines.extend([
            "",
            f"WARNINGS ({len(self.report.warnings)}):",
            "-" * 40
        ])
        
        for warning in self.report.warnings:
            lines.append(f"  ! {warning}")
        
        lines.extend([
            "",
            f"ERRORS ({len(self.report.errors)}):",
            "-" * 40
        ])
        
        for error in self.report.errors:
            lines.append(f"  X {error}")
        
        lines.extend(["", "=" * 80])
        
        return "\n".join(lines)
    
    def run_full_check(self, namespace: str = "all", 
                      auto_restart: bool = False, 
                      max_restarts: int = 5,
                      dry_run: bool = False,
                      send_alerts: bool = False,
                      alert_channels: List[str] = None) -> HealthReport:
        logger.info("Starting full Kubernetes health check")
        
        self.report = HealthReport()
        
        self.check_pods(namespace)
        self.check_nodes()
        self.report.quota_recommendations = self.analyze_resource_quotas()
        self.analyze_image_security()
        self.aggregate_events()
        
        if auto_restart:
            self.restart_crashing_containers(max_restarts=max_restarts, dry_run=dry_run)
        
        if send_alerts:
            self.send_alerts(alert_channels)
        
        logger.info("Full health check completed")
        return self.report
    
    def stop(self):
        if self.use_watch:
            self.cache.stop()
            logger.info("Watchers stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Kubernetes Resource Health Checker v2.0")
    parser.add_argument("--namespace", default="all", help="Namespace to check (default: all)")
    parser.add_argument("--auto-restart", action="store_true", help="Auto restart crashing containers")
    parser.add_argument("--max-restarts", type=int, default=5, help="Max restarts per container")
    parser.add_argument("--drain-node", help="Node name to drain")
    parser.add_argument("--ignore-pdb", action="store_true", help="Ignore PDB when draining node")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--in-cluster", action="store_true", help="Run in-cluster mode")
    parser.add_argument("--no-watch", action="store_true", help="Disable watch cache")
    parser.add_argument("--output", choices=["text", "yaml", "html"], default="html", help="Output format")
    parser.add_argument("--output-file", default="k8s_health_report.html", help="Save report to file")
    parser.add_argument("--send-alerts", action="store_true", help="Send alerts via configured channels")
    parser.add_argument("--alert-channels", default="dingtalk,wework", help="Alert channels (comma-separated)")
    parser.add_argument("--dingtalk-webhook", help="DingTalk webhook URL")
    parser.add_argument("--wework-webhook", help="WeCom webhook URL")
    
    args = parser.parse_args()
    
    webhooks = {}
    if args.dingtalk_webhook:
        webhooks['dingtalk'] = args.dingtalk_webhook
    if args.wework_webhook:
        webhooks['wework'] = args.wework_webhook
    
    alert_channels = [c.strip() for c in args.alert_channels.split(',')] if args.alert_channels else None
    
    checker = K8sHealthChecker(
        in_cluster=args.in_cluster, 
        use_watch=not args.no_watch,
        alert_webhooks=webhooks
    )
    
    checker.run_full_check(
        namespace=args.namespace,
        auto_restart=args.auto_restart,
        max_restarts=args.max_restarts,
        dry_run=args.dry_run,
        send_alerts=args.send_alerts,
        alert_channels=alert_channels
    )
    
    if args.drain_node:
        checker.drain_node(
            node_name=args.drain_node,
            dry_run=args.dry_run,
            ignore_pdb=args.ignore_pdb
        )
    
    report = checker.generate_report(output_format=args.output)
    
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to: {args.output_file}")
    else:
        print(report)
    
    checker.stop()


if __name__ == "__main__":
    main()
