import yaml
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class DiffType(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    DRIFT = "drift"


@dataclass
class ConfigDiff:
    diff_type: DiffType
    path: str
    expected_value: Any = None
    actual_value: Any = None
    severity: str = "info"


@dataclass
class DriftReport:
    resource_type: str
    resource_name: str
    namespace: str
    diffs: List[ConfigDiff]
    has_drift: bool


class ClusterConfigComparer:
    def __init__(self):
        self.kubectl_available = shutil.which('kubectl') is not None
        self.ignored_fields = [
            'metadata.creationTimestamp',
            'metadata.resourceVersion',
            'metadata.uid',
            'metadata.selfLink',
            'metadata.generation',
            'metadata.managedFields',
            'status',
            'spec.replicas',
        ]

    def is_available(self) -> bool:
        return self.kubectl_available

    def get_cluster_resource(self, kind: str, name: str, namespace: str = 'default') -> Optional[Dict[str, Any]]:
        if not self.kubectl_available:
            return None

        try:
            cmd = ['kubectl', 'get', kind.lower(), name, '-n', namespace, '-o', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception:
            pass
        return None

    def list_resources(self, kind: str, namespace: str = 'default') -> List[str]:
        if not self.kubectl_available:
            return []

        try:
            cmd = ['kubectl', 'get', kind.lower(), '-n', namespace, '-o', 'jsonpath={.items[*].metadata.name}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split(' ')
        except Exception:
            pass
        return []

    def load_yaml_resource(self, file_path: str) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        documents = list(yaml.safe_load_all(content))
        return [doc for doc in documents if doc]

    def compare_resource(self, expected: Dict[str, Any], 
                         actual: Optional[Dict[str, Any]]) -> DriftReport:
        kind = expected.get('kind', 'Unknown')
        name = expected.get('metadata', {}).get('name', 'unknown')
        namespace = expected.get('metadata', {}).get('namespace', 'default')

        diffs = []

        if actual is None:
            diffs.append(ConfigDiff(
                diff_type=DiffType.REMOVED,
                path='.',
                expected_value=name,
                actual_value=None,
                severity='warning'
            ))
            return DriftReport(kind, name, namespace, diffs, True)

        expected_spec = self._normalize_spec(expected)
        actual_spec = self._normalize_spec(actual)

        self._deep_compare(
            expected_spec, 
            actual_spec, 
            '', 
            diffs
        )

        has_drift = len(diffs) > 0
        return DriftReport(kind, name, namespace, diffs, has_drift)

    def _normalize_spec(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        if 'spec' in resource:
            result['spec'] = resource['spec'].copy()
        if 'metadata' in resource:
            result['metadata'] = {
                'labels': resource['metadata'].get('labels', {}),
                'annotations': {
                    k: v for k, v in resource['metadata'].get('annotations', {}).items()
                    if not k.startswith('kubectl.kubernetes.io/')
                }
            }
        return result

    def _deep_compare(self, expected: Any, actual: Any, path: str, 
                       diffs: List[ConfigDiff]):
        if path and self._should_ignore(path):
            return

        if isinstance(expected, dict) and isinstance(actual, dict):
            all_keys = set(expected.keys()) | set(actual.keys())
            for key in all_keys:
                new_path = f"{path}.{key}" if path else key
                if key not in actual:
                    diffs.append(ConfigDiff(
                        diff_type=DiffType.DRIFT,
                        path=new_path,
                        expected_value=expected[key],
                        actual_value=None,
                        severity='warning'
                    ))
                elif key not in expected:
                    diffs.append(ConfigDiff(
                        diff_type=DiffType.DRIFT,
                        path=new_path,
                        expected_value=None,
                        actual_value=actual[key],
                        severity='info'
                    ))
                else:
                    self._deep_compare(expected[key], actual[key], new_path, diffs)
        elif isinstance(expected, list) and isinstance(actual, list):
            if len(expected) != len(actual):
                diffs.append(ConfigDiff(
                    diff_type=DiffType.DRIFT,
                    path=path,
                    expected_value=len(expected),
                    actual_value=len(actual),
                    severity='warning'
                ))
            else:
                for i, (e, a) in enumerate(zip(expected, actual)):
                    new_path = f"{path}[{i}]"
                    self._deep_compare(e, a, new_path, diffs)
        elif expected != actual:
            diffs.append(ConfigDiff(
                diff_type=DiffType.DRIFT,
                path=path,
                expected_value=expected,
                actual_value=actual,
                severity='warning'
            ))

    def _should_ignore(self, path: str) -> bool:
        for ignored in self.ignored_fields:
            if path.startswith(ignored) or path == ignored:
                return True
        return False

    def compare_file_with_cluster(self, yaml_file: str) -> List[DriftReport]:
        yaml_resources = self.load_yaml_resource(yaml_file)
        reports = []

        for resource in yaml_resources:
            kind = resource.get('kind', '')
            name = resource.get('metadata', {}).get('name', '')
            namespace = resource.get('metadata', {}).get('namespace', 'default')

            if kind and name:
                cluster_resource = self.get_cluster_resource(kind, name, namespace)
                report = self.compare_resource(resource, cluster_resource)
                reports.append(report)

        return reports

    def compare_directory_with_cluster(self, dir_path: str) -> List[DriftReport]:
        reports = []
        dir_path = Path(dir_path)

        for yaml_file in list(dir_path.rglob("*.yaml")) + list(dir_path.rglob("*.yml")):
            if yaml_file.is_file():
                file_reports = self.compare_file_with_cluster(str(yaml_file))
                reports.extend(file_reports)

        return reports

    def generate_diff_report(self, reports: List[DriftReport], 
                              output_format: str = 'console') -> str:
        if output_format == 'json':
            return self._format_json(reports)
        elif output_format == 'summary':
            return self._format_summary(reports)
        else:
            return self._format_console(reports)

    def _format_console(self, reports: List[DriftReport]) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("Kubernetes 配置漂移检测报告")
        lines.append("=" * 80)

        drift_count = sum(1 for r in reports if r.has_drift)
        total_count = len(reports)

        lines.append(f"\n总计检查 {total_count} 个资源，发现 {drift_count} 个有配置漂移")
        lines.append("")

        for report in reports:
            if report.has_drift:
                lines.append(f"\n[漂移] {report.resource_type}/{report.resource_name} (namespace: {report.namespace})")
                lines.append("-" * 80)
                for diff in report.diffs:
                    marker = {
                        'added': '+',
                        'removed': '-',
                        'modified': '~',
                        'drift': '!'
                    }.get(diff.diff_type.value, '?')
                    
                    lines.append(f"  {marker} {diff.path}")
                    if diff.expected_value is not None:
                        lines.append(f"      期望: {self._truncate_value(diff.expected_value)}")
                    if diff.actual_value is not None:
                        lines.append(f"      实际: {self._truncate_value(diff.actual_value)}")
            else:
                lines.append(f"\n[一致] {report.resource_type}/{report.resource_name} (namespace: {report.namespace})")

        return '\n'.join(lines)

    def _format_summary(self, reports: List[DriftReport]) -> str:
        drift_count = sum(1 for r in reports if r.has_drift)
        total_diffs = sum(len(r.diffs) for r in reports)
        
        lines = []
        lines.append("配置漂移检测摘要:")
        lines.append(f"  总资源数: {len(reports)}")
        lines.append(f"  有漂移资源: {drift_count}")
        lines.append(f"  总差异数: {total_diffs}")
        
        drift_resources = [r for r in reports if r.has_drift]
        if drift_resources:
            lines.append("\n有漂移的资源:")
            for r in drift_resources:
                lines.append(f"  - {r.resource_type}/{r.resource_name} ({len(r.diffs)} 差异)")
        
        return '\n'.join(lines)

    def _format_json(self, reports: List[DriftReport]) -> str:
        result = {
            'summary': {
                'total_resources': len(reports),
                'resources_with_drift': sum(1 for r in reports if r.has_drift),
                'total_differences': sum(len(r.diffs) for r in reports)
            },
            'resources': [
                {
                    'type': report.resource_type,
                    'name': report.resource_name,
                    'namespace': report.namespace,
                    'has_drift': report.has_drift,
                    'differences': [
                        {
                            'type': diff.diff_type.value,
                            'path': diff.path,
                            'expected': diff.expected_value,
                            'actual': diff.actual_value,
                            'severity': diff.severity
                        }
                        for diff in report.diffs
                    ]
                }
                for report in reports
            ]
        }
        return json.dumps(result, indent=2, default=str, ensure_ascii=False)

    def _truncate_value(self, value: Any, max_len: int = 60) -> str:
        s = str(value)
        if len(s) > max_len:
            return s[:max_len] + '...'
        return s
