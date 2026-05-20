import logging
import re
from typing import Dict, List, Optional


class KnowledgeBase:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.knowledge = self._init_knowledge()

    def _init_knowledge(self) -> List[Dict]:
        return [
            {
                'id': 'OOMKilled',
                'name': '内存溢出',
                'patterns': ['OOMKilled', 'Out of memory', '内存溢出', 'OOM'],
                'severity': 'high',
                'description': 'Pod因内存不足被系统杀死',
                'causes': [
                    'Pod配置的内存限制太小',
                    '应用程序存在内存泄漏',
                    '业务流量突增导致内存使用超标'
                ],
                'solutions': [
                    '增加 Pod 的 memory limit',
                    '检查并修复应用程序内存泄漏',
                    '考虑增加副本数量分担流量',
                    '监控内存使用趋势，提前扩容'
                ],
                'commands': [
                    'kubectl describe pod <pod-name>',
                    'kubectl logs <pod-name> --previous'
                ]
            },
            {
                'id': 'CrashLoopBackOff',
                'name': '启动循环崩溃',
                'patterns': ['CrashLoopBackOff', 'CrashLoop', '启动失败', '重启循环'],
                'severity': 'high',
                'description': 'Pod启动后立即崩溃，反复重启',
                'causes': [
                    '应用程序配置错误',
                    '依赖服务不可用',
                    '权限不足',
                    '端口被占用'
                ],
                'solutions': [
                    '查看 Pod 日志定位错误原因',
                    '检查配置文件和环境变量',
                    '验证依赖服务是否正常',
                    '检查 RBAC 权限配置'
                ],
                'commands': [
                    'kubectl logs <pod-name>',
                    'kubectl describe pod <pod-name>'
                ]
            },
            {
                'id': 'ImagePullBackOff',
                'name': '镜像拉取失败',
                'patterns': ['ImagePullBackOff', 'ErrImagePull', '镜像拉取失败', '拉取镜像'],
                'severity': 'medium',
                'description': '无法拉取容器镜像',
                'causes': [
                    '镜像名称或标签错误',
                    '私有镜像仓库认证失败',
                    '网络连接问题',
                    '镜像不存在'
                ],
                'solutions': [
                    '检查镜像名称和标签是否正确',
                    '验证 ImagePullSecret 配置',
                    '检查节点网络连接',
                    '确认镜像仓库可访问'
                ],
                'commands': [
                    'kubectl describe pod <pod-name>',
                    'docker pull <image>'
                ]
            },
            {
                'id': 'Pending',
                'name': '调度失败',
                'patterns': ['Pending', '调度失败', '无法调度'],
                'severity': 'medium',
                'description': 'Pod无法被调度到任何节点',
                'causes': [
                    '节点资源不足',
                    '节点亲和性/反亲和性不满足',
                    '节点被污点标记',
                    'PVC 无法绑定'
                ],
                'solutions': [
                    '检查节点资源使用情况',
                    '验证节点选择器和亲和性配置',
                    '检查污点和容忍设置',
                    '确认 PVC 状态'
                ],
                'commands': [
                    'kubectl describe pod <pod-name>',
                    'kubectl get nodes',
                    'kubectl describe pvc <pvc-name>'
                ]
            },
            {
                'id': 'ReadinessProbeFailed',
                'name': '就绪检查失败',
                'patterns': ['Readiness probe failed', '就绪检查失败', 'readiness'],
                'severity': 'medium',
                'description': 'Pod就绪探针检查失败',
                'causes': [
                    '应用启动时间过长',
                    '探针配置不合理',
                    '应用健康检查接口异常'
                ],
                'solutions': [
                    '增加 initialDelaySeconds',
                    '调整 periodSeconds 和 timeoutSeconds',
                    '检查应用健康检查接口'
                ],
                'commands': [
                    'kubectl describe pod <pod-name>',
                    'kubectl logs <pod-name>'
                ]
            },
            {
                'id': 'LivenessProbeFailed',
                'name': '存活检查失败',
                'patterns': ['Liveness probe failed', '存活检查失败', 'liveness'],
                'severity': 'high',
                'description': 'Pod存活探针检查失败，Pod被重启',
                'causes': [
                    '应用程序死锁或无响应',
                    '探针配置过于严格',
                    '应用负载过高'
                ],
                'solutions': [
                    '检查应用程序状态',
                    '调整探针阈值和超时时间',
                    '考虑资源扩容'
                ],
                'commands': [
                    'kubectl describe pod <pod-name>',
                    'kubectl logs <pod-name>'
                ]
            },
            {
                'id': 'Evicted',
                'name': 'Pod被驱逐',
                'patterns': ['Evicted', '驱逐', 'eviction'],
                'severity': 'high',
                'description': 'Pod被节点资源不足被驱逐',
                'causes': [
                    '节点内存或磁盘压力',
                    'Pod QoS 级别较低',
                    '资源超配严重'
                ],
                'solutions': [
                    '清理节点磁盘空间',
                    '调整 Pod 的资源请求和限制',
                    '考虑设置更高的 QoS 级别',
                    '增加节点或扩容集群'
                ],
                'commands': [
                    'kubectl describe node <node-name>',
                    'kubectl get pods -o wide'
                ]
            },
            {
                'id': 'ConnectionRefused',
                'name': '连接被拒绝',
                'patterns': ['Connection refused', '连接被拒绝', 'connection refused'],
                'severity': 'medium',
                'description': '服务连接被拒绝',
                'causes': [
                    '服务未启动',
                    '端口配置错误',
                    '网络策略限制',
                    '防火墙拦截'
                ],
                'solutions': [
                    '确认服务正常运行',
                    '检查端口配置',
                    '验证网络策略',
                    '检查防火墙规则'
                ],
                'commands': [
                    'kubectl get svc',
                    'kubectl get endpoints',
                    'kubectl describe networkpolicy'
                ]
            },
            {
                'id': 'Timeout',
                'name': '请求超时',
                'patterns': ['Timeout', '超时', 'timed out'],
                'severity': 'medium',
                'description': '请求处理超时',
                'causes': [
                    '应用性能问题',
                    '数据库连接慢',
                    '网络延迟高',
                    '请求量过大'
                ],
                'solutions': [
                    '优化应用性能',
                    '检查数据库连接池',
                    '增加 Pod 副本数',
                    '考虑使用缓存'
                ],
                'commands': [
                    'kubectl top pods',
                    'kubectl logs <pod-name>'
                ]
            },
            {
                'id': 'ConfigError',
                'name': '配置错误',
                'patterns': ['ConfigMap', 'Secret', '配置错误', 'config error'],
                'severity': 'medium',
                'description': '配置相关错误',
                'causes': [
                    'ConfigMap 不存在',
                    'Secret 不存在',
                    '配置键名错误',
                    '配置格式错误'
                ],
                'solutions': [
                    '确认 ConfigMap/Secret 存在',
                    '检查配置键名拼写',
                    '验证配置格式正确性',
                    '检查挂载路径配置'
                ],
                'commands': [
                    'kubectl get configmap',
                    'kubectl get secret',
                    'kubectl describe pod <pod-name>'
                ]
            }
        ]

    def diagnose(self, event_message: str, pod_name: str = None) -> Optional[Dict]:
        for knowledge in self.knowledge:
            for pattern in knowledge['patterns']:
                if re.search(pattern, event_message, re.IGNORECASE):
                    self.logger.info(f"Diagnosed issue: {knowledge['id']}")
                    return knowledge
        return None

    def format_diagnosis(self, diagnosis: Dict, pod_name: str = None) -> str:
        if not diagnosis:
            return ":mag: 未识别到已知故障模式"
        
        severity_emoji = {
            'high': ':red_circle:',
            'medium': ':orange_circle:',
            'low': ':yellow_circle:'
        }.get(diagnosis['severity'], ':white_circle:')
        
        message = f"{severity_emoji} *故障诊断: {diagnosis['name']}*\n\n"
        message += f"*描述:* {diagnosis['description']}\n\n"
        
        message += "*可能原因:*\n"
        for i, cause in enumerate(diagnosis['causes'], 1):
            message += f"  {i}. {cause}\n"
        
        message += "\n*建议解决方案:*\n"
        for i, solution in enumerate(diagnosis['solutions'], 1):
            message += f"  {i}. {solution}\n"
        
        message += "\n*排查命令:*\n"
        for cmd in diagnosis['commands']:
            if pod_name:
                cmd = cmd.replace('<pod-name>', pod_name)
            message += f"  `{cmd}`\n"
        
        return message

    def get_all_knowledge(self) -> List[Dict]:
        return self.knowledge

    def search_knowledge(self, keyword: str) -> List[Dict]:
        results = []
        for knowledge in self.knowledge:
            if re.search(keyword, knowledge['name'], re.IGNORECASE) or \
               re.search(keyword, knowledge['description'], re.IGNORECASE):
                results.append(knowledge)
        return results
