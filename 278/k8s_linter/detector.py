import yaml
import re
import ast
import operator
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def order(self):
        return {
            "critical": 4,
            "error": 3,
            "warning": 2,
            "info": 1
        }[self.value]


class ContainerType(Enum):
    REGULAR = "regular"
    INIT = "init"
    EPHEMERAL = "ephemeral"


@dataclass
class Issue:
    rule_id: str
    severity: Severity
    message: str
    suggestion: str
    file_path: str
    resource_type: str = ""
    resource_name: str = ""
    container_name: str = ""
    container_type: str = ""
    line: Optional[int] = None


class Report:
    def __init__(self):
        self.issues: List[Issue] = []

    def add_issue(self, issue: Issue):
        self.issues.append(issue)

    def get_issues_by_severity(self, severity: Severity) -> List[Issue]:
        return [i for i in self.issues if i.severity == severity]

    def get_issues_by_container_type(self, container_type: ContainerType) -> List[Issue]:
        return [i for i in self.issues if i.container_type == container_type.value]

    @property
    def has_errors(self) -> bool:
        return any(i.severity in (Severity.CRITICAL, Severity.ERROR) for i in self.issues)

    @property
    def critical_count(self) -> int:
        return len(self.get_issues_by_severity(Severity.CRITICAL))

    @property
    def error_count(self) -> int:
        return len(self.get_issues_by_severity(Severity.ERROR))

    @property
    def warning_count(self) -> int:
        return len(self.get_issues_by_severity(Severity.WARNING))

    @property
    def info_count(self) -> int:
        return len(self.get_issues_by_severity(Severity.INFO))


class ExpressionEvaluator:
    def __init__(self):
        self.operators = {
            ast.And: operator.and_,
            ast.Or: operator.or_,
            ast.Not: operator.not_,
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
        }

    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body, context)
        except (SyntaxError, ValueError, TypeError):
            return False

    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(v, context) for v in node.values]
            op = self.operators[type(node.op)]
            if isinstance(node.op, ast.And):
                result = True
                for v in values:
                    result = op(result, v)
                return result
            elif isinstance(node.op, ast.Or):
                result = False
                for v in values:
                    result = op(result, v)
                return result
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval_node(node.operand, context)
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_func = self.operators.get(type(op))
                if op_func and not op_func(left, right):
                    return False
            return True
        elif isinstance(node, ast.Name):
            return context.get(node.id, False)
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Attribute):
            obj = self._eval_node(node.value, context)
            if isinstance(obj, dict):
                return obj.get(node.attr, False)
            return getattr(obj, node.attr, False)
        elif isinstance(node, ast.Subscript):
            obj = self._eval_node(node.value, context)
            key = self._eval_node(node.slice, context)
            if isinstance(obj, dict):
                return obj.get(key, False)
            return False
        elif isinstance(node, ast.Call):
            func = self._eval_node(node.func, context)
            if callable(func):
                args = [self._eval_node(arg, context) for arg in node.args]
                return func(*args)
            return False
        return False


class RuleEngine:
    def __init__(self, rules_config: Dict[str, Any]):
        self.rules = rules_config
        self.evaluator = ExpressionEvaluator()

    def is_rule_enabled(self, category: str, rule_id: str, context: Dict[str, Any]) -> bool:
        rule_config = self.rules.get(category, {}).get(rule_id, {})
        
        if not rule_config.get('enabled', True):
            return False

        condition = rule_config.get('condition')
        if condition:
            return self.evaluator.evaluate(condition, context)

        return True

    def get_rule_config(self, category: str, rule_id: str) -> Dict[str, Any]:
        return self.rules.get(category, {}).get(rule_id, {})


class K8sConfigDetector:
    def __init__(self, rules_config_path: Optional[str] = None):
        self.rules = self._load_rules(rules_config_path)
        self.rule_engine = RuleEngine(self.rules)

    def _load_rules(self, config_path: Optional[str]) -> Dict[str, Any]:
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "rules.yaml"

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('rules', {})

    def scan_file(self, file_path: str) -> Report:
        report = Report()

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            report.add_issue(Issue(
                rule_id="yaml_parse_error",
                severity=Severity.ERROR,
                message=f"YAML解析错误: {str(e)}",
                suggestion="检查YAML语法是否正确",
                file_path=file_path
            ))
            return report

        for doc in documents:
            if doc is None:
                continue
            self._scan_resource(doc, file_path, report)

        return report

    def scan_directory(self, dir_path: str) -> Report:
        report = Report()
        dir_path = Path(dir_path)

        for yaml_file in dir_path.rglob("*.yaml"):
            if yaml_file.is_file():
                file_report = self.scan_file(str(yaml_file))
                report.issues.extend(file_report.issues)

        for yml_file in dir_path.rglob("*.yml"):
            if yml_file.is_file():
                file_report = self.scan_file(str(yml_file))
                report.issues.extend(file_report.issues)

        return report

    def _get_pod_spec(self, resource: Dict[str, Any], kind: str) -> Dict[str, Any]:
        if kind == 'CronJob':
            return resource.get('spec', {}).get('jobTemplate', {}).get('spec', {}).get('template', {}).get('spec', {})
        elif kind == 'Pod':
            return resource.get('spec', {})
        else:
            return resource.get('spec', {}).get('template', {}).get('spec', {})

    def _get_all_containers(self, pod_spec: Dict[str, Any]) -> List[tuple]:
        containers = []
        
        for container in pod_spec.get('containers', []):
            containers.append((container, ContainerType.REGULAR))
        
        for container in pod_spec.get('initContainers', []):
            containers.append((container, ContainerType.INIT))
        
        for container in pod_spec.get('ephemeralContainers', []):
            containers.append((container, ContainerType.EPHEMERAL))
        
        return containers

    def _scan_resource(self, resource: Dict[str, Any], file_path: str, report: Report):
        kind = resource.get('kind', 'Unknown')
        metadata = resource.get('metadata', {})
        name = metadata.get('name', 'Unknown')
        labels = metadata.get('labels', {})

        pod_workloads = ['Deployment', 'StatefulSet', 'DaemonSet', 'Job', 'CronJob', 'Pod']

        if kind in pod_workloads:
            pod_spec = self._get_pod_spec(resource, kind)
            
            context = {
                'kind': kind,
                'name': name,
                'labels': labels,
                'has_init_containers': len(pod_spec.get('initContainers', [])) > 0,
                'has_ephemeral_containers': len(pod_spec.get('ephemeralContainers', [])) > 0,
                'container_count': len(pod_spec.get('containers', [])),
                'replicas': resource.get('spec', {}).get('replicas', 1) if kind != 'Pod' else 1
            }

            self._check_pod_security_context(pod_spec, kind, name, file_path, report, context)

            all_containers = self._get_all_containers(pod_spec)
            for container, container_type in all_containers:
                container_context = dict(context)
                container_context['container_type'] = container_type.value
                container_context['container_name'] = container.get('name', '')
                container_context['is_init_container'] = container_type == ContainerType.INIT
                container_context['is_ephemeral_container'] = container_type == ContainerType.EPHEMERAL
                container_context['is_regular_container'] = container_type == ContainerType.REGULAR

                self._check_resources(container, kind, name, file_path, report, container_context, container_type)
                self._check_security_context(container, kind, name, file_path, report, container_context, container_type)
                self._check_image_tag(container, kind, name, file_path, report, container_context, container_type)
                self._check_probes(container, kind, name, file_path, report, container_context, container_type)

    def _check_pod_security_context(self, pod_spec: Dict[str, Any], kind: str, name: str,
                                     file_path: str, report: Report, context: Dict[str, Any]):
        pod_security_context = pod_spec.get('securityContext', {})

        if self.rule_engine.is_rule_enabled('security', 'pod_run_as_non_root', context):
            rule = self.rule_engine.get_rule_config('security', 'pod_run_as_non_root')
            if not pod_security_context.get('runAsNonRoot', False):
                report.add_issue(Issue(
                    rule_id="pod_run_as_non_root",
                    severity=Severity(rule.get('severity', 'error')),
                    message=rule.get('message', 'Pod级未配置以非root用户运行'),
                    suggestion=rule.get('suggestion', '设置 spec.securityContext.runAsNonRoot: true'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name
                ))

        if self.rule_engine.is_rule_enabled('security', 'pod_run_as_user', context):
            rule = self.rule_engine.get_rule_config('security', 'pod_run_as_user')
            if pod_security_context.get('runAsUser', 0) == 0:
                report.add_issue(Issue(
                    rule_id="pod_run_as_user",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', 'Pod级未指定非root用户ID'),
                    suggestion=rule.get('suggestion', '设置 spec.securityContext.runAsUser 为非0值'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name
                ))

        if self.rule_engine.is_rule_enabled('security', 'pod_fs_group', context):
            rule = self.rule_engine.get_rule_config('security', 'pod_fs_group')
            if 'fsGroup' not in pod_security_context:
                report.add_issue(Issue(
                    rule_id="pod_fs_group",
                    severity=Severity(rule.get('severity', 'info')),
                    message=rule.get('message', 'Pod级未配置文件系统组'),
                    suggestion=rule.get('suggestion', '设置 spec.securityContext.fsGroup'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name
                ))

        if self.rule_engine.is_rule_enabled('security', 'pod_seccomp_profile', context):
            rule = self.rule_engine.get_rule_config('security', 'pod_seccomp_profile')
            seccomp_profile = pod_security_context.get('seccompProfile', {})
            if not seccomp_profile or seccomp_profile.get('type') not in ['RuntimeDefault', 'Localhost']:
                report.add_issue(Issue(
                    rule_id="pod_seccomp_profile",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', 'Pod级未配置seccomp安全配置'),
                    suggestion=rule.get('suggestion', '设置 spec.securityContext.seccompProfile.type'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name
                ))

        if self.rule_engine.is_rule_enabled('security', 'pod_supplemental_groups', context):
            rule = self.rule_engine.get_rule_config('security', 'pod_supplemental_groups')
            if 'supplementalGroups' not in pod_security_context:
                report.add_issue(Issue(
                    rule_id="pod_supplemental_groups",
                    severity=Severity(rule.get('severity', 'info')),
                    message=rule.get('message', 'Pod级未配置补充组'),
                    suggestion=rule.get('suggestion', '设置 spec.securityContext.supplementalGroups'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name
                ))

    def _check_resources(self, container: Dict[str, Any], kind: str, name: str,
                          file_path: str, report: Report, context: Dict[str, Any],
                          container_type: ContainerType):
        container_name = container.get('name', 'unknown')
        resources = container.get('resources', {})
        limits = resources.get('limits', {})
        requests = resources.get('requests', {})

        if self.rule_engine.is_rule_enabled('resources', 'cpu_limit_required', context):
            rule = self.rule_engine.get_rule_config('resources', 'cpu_limit_required')
            if 'cpu' not in limits:
                report.add_issue(Issue(
                    rule_id="cpu_limit_required",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', 'CPU限制未配置'),
                    suggestion=rule.get('suggestion', '添加 resources.limits.cpu'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('resources', 'cpu_request_required', context):
            rule = self.rule_engine.get_rule_config('resources', 'cpu_request_required')
            if 'cpu' not in requests:
                report.add_issue(Issue(
                    rule_id="cpu_request_required",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', 'CPU请求未配置'),
                    suggestion=rule.get('suggestion', '添加 resources.requests.cpu'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('resources', 'memory_limit_required', context):
            rule = self.rule_engine.get_rule_config('resources', 'memory_limit_required')
            if 'memory' not in limits:
                report.add_issue(Issue(
                    rule_id="memory_limit_required",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', '内存限制未配置'),
                    suggestion=rule.get('suggestion', '添加 resources.limits.memory'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('resources', 'memory_request_required', context):
            rule = self.rule_engine.get_rule_config('resources', 'memory_request_required')
            if 'memory' not in requests:
                report.add_issue(Issue(
                    rule_id="memory_request_required",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', '内存请求未配置'),
                    suggestion=rule.get('suggestion', '添加 resources.requests.memory'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

    def _check_security_context(self, container: Dict[str, Any], kind: str, name: str,
                                 file_path: str, report: Report, context: Dict[str, Any],
                                 container_type: ContainerType):
        container_name = container.get('name', 'unknown')
        security_context = container.get('securityContext', {})

        if self.rule_engine.is_rule_enabled('security', 'privileged_container', context):
            rule = self.rule_engine.get_rule_config('security', 'privileged_container')
            if security_context.get('privileged', False):
                report.add_issue(Issue(
                    rule_id="privileged_container",
                    severity=Severity(rule.get('severity', 'critical')),
                    message=rule.get('message', '容器配置为特权模式'),
                    suggestion=rule.get('suggestion', '设置 securityContext.privileged: false'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('security', 'read_only_root_filesystem', context):
            rule = self.rule_engine.get_rule_config('security', 'read_only_root_filesystem')
            if not security_context.get('readOnlyRootFilesystem', False):
                report.add_issue(Issue(
                    rule_id="read_only_root_filesystem",
                    severity=Severity(rule.get('severity', 'error')),
                    message=rule.get('message', '根文件系统未设置为只读'),
                    suggestion=rule.get('suggestion', '设置 securityContext.readOnlyRootFilesystem: true'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('security', 'run_as_non_root', context):
            rule = self.rule_engine.get_rule_config('security', 'run_as_non_root')
            if not security_context.get('runAsNonRoot', False):
                report.add_issue(Issue(
                    rule_id="run_as_non_root",
                    severity=Severity(rule.get('severity', 'error')),
                    message=rule.get('message', '未配置以非root用户运行'),
                    suggestion=rule.get('suggestion', '设置 securityContext.runAsNonRoot: true'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('security', 'allow_privilege_escalation', context):
            rule = self.rule_engine.get_rule_config('security', 'allow_privilege_escalation')
            if security_context.get('allowPrivilegeEscalation', True):
                report.add_issue(Issue(
                    rule_id="allow_privilege_escalation",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', '允许权限提升'),
                    suggestion=rule.get('suggestion', '设置 securityContext.allowPrivilegeEscalation: false'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('security', 'capabilities_drop_all', context):
            rule = self.rule_engine.get_rule_config('security', 'capabilities_drop_all')
            capabilities = security_context.get('capabilities', {})
            drop = capabilities.get('drop', [])
            if 'ALL' not in drop and 'all' not in drop:
                report.add_issue(Issue(
                    rule_id="capabilities_drop_all",
                    severity=Severity(rule.get('severity', 'warning')),
                    message=rule.get('message', '未丢弃所有Linux capabilities'),
                    suggestion=rule.get('suggestion', '设置 securityContext.capabilities.drop: ["ALL"]'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

    def _check_image_tag(self, container: Dict[str, Any], kind: str, name: str,
                          file_path: str, report: Report, context: Dict[str, Any],
                          container_type: ContainerType):
        container_name = container.get('name', 'unknown')
        image = container.get('image', '')

        if not image:
            return

        if self.rule_engine.is_rule_enabled('image', 'no_tag', context):
            rule = self.rule_engine.get_rule_config('image', 'no_tag')
            if ':' not in image:
                report.add_issue(Issue(
                    rule_id="no_tag",
                    severity=Severity(rule.get('severity', 'error')),
                    message=rule.get('message', '镜像未指定标签'),
                    suggestion=rule.get('suggestion', '为镜像指定明确的版本标签'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))
            else:
                tag = image.split(':')[-1]
                if self.rule_engine.is_rule_enabled('image', 'latest_tag', context):
                    rule_latest = self.rule_engine.get_rule_config('image', 'latest_tag')
                    if tag == 'latest':
                        report.add_issue(Issue(
                            rule_id="latest_tag",
                            severity=Severity(rule_latest.get('severity', 'warning')),
                            message=rule_latest.get('message', '镜像使用latest标签'),
                            suggestion=rule_latest.get('suggestion', '使用具体的镜像版本标签'),
                            file_path=file_path,
                            resource_type=kind,
                            resource_name=name,
                            container_name=container_name,
                            container_type=container_type.value
                        ))

    def _check_probes(self, container: Dict[str, Any], kind: str, name: str,
                       file_path: str, report: Report, context: Dict[str, Any],
                       container_type: ContainerType):
        container_name = container.get('name', 'unknown')

        if self.rule_engine.is_rule_enabled('best_practices', 'liveness_probe_missing', context):
            rule = self.rule_engine.get_rule_config('best_practices', 'liveness_probe_missing')
            if 'livenessProbe' not in container:
                report.add_issue(Issue(
                    rule_id="liveness_probe_missing",
                    severity=Severity(rule.get('severity', 'info')),
                    message=rule.get('message', '未配置存活探针'),
                    suggestion=rule.get('suggestion', '添加 livenessProbe 配置'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))

        if self.rule_engine.is_rule_enabled('best_practices', 'readiness_probe_missing', context):
            rule = self.rule_engine.get_rule_config('best_practices', 'readiness_probe_missing')
            if 'readinessProbe' not in container:
                report.add_issue(Issue(
                    rule_id="readiness_probe_missing",
                    severity=Severity(rule.get('severity', 'info')),
                    message=rule.get('message', '未配置就绪探针'),
                    suggestion=rule.get('suggestion', '添加 readinessProbe 配置'),
                    file_path=file_path,
                    resource_type=kind,
                    resource_name=name,
                    container_name=container_name,
                    container_type=container_type.value
                ))
