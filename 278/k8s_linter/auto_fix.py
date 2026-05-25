import yaml
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from .detector import Issue, Severity, ContainerType


class FixAction:
    def __init__(self, rule_id: str, description: str):
        self.rule_id = rule_id
        self.description = description
        self.applied = False

    def apply(self, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def get_patch(self) -> Dict[str, Any]:
        raise NotImplementedError


class SecurityContextFix(FixAction):
    def __init__(self, rule_id: str, description: str, container_name: str,
                 field: str, value: Any, is_pod_level: bool = False):
        super().__init__(rule_id, description)
        self.container_name = container_name
        self.field = field
        self.value = value
        self.is_pod_level = is_pod_level

    def apply(self, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        pod_spec = self._get_pod_spec(resource)
        if not pod_spec:
            return False

        if self.is_pod_level:
            if 'securityContext' not in pod_spec:
                pod_spec['securityContext'] = {}
            pod_spec['securityContext'][self.field] = self.value
        else:
            container = self._find_container(pod_spec, self.container_name)
            if container:
                if 'securityContext' not in container:
                    container['securityContext'] = {}
                container['securityContext'][self.field] = self.value
            else:
                return False

        self.applied = True
        return True

    def _get_pod_spec(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = resource.get('kind', '')
        if kind == 'Pod':
            return resource.get('spec', {})
        elif kind == 'CronJob':
            return resource.get('spec', {}).get('jobTemplate', {}).get('spec', {}).get('template', {}).get('spec', {})
        else:
            return resource.get('spec', {}).get('template', {}).get('spec', {})

    def _find_container(self, pod_spec: Dict[str, Any], container_name: str) -> Optional[Dict[str, Any]]:
        for container_type in ['containers', 'initContainers', 'ephemeralContainers']:
            for container in pod_spec.get(container_type, []):
                if container.get('name') == container_name:
                    return container
        return None

    def get_patch(self) -> Dict[str, Any]:
        path = 'spec.securityContext' if self.is_pod_level else \
               f'spec.template.spec.containers[].securityContext.{self.field}'
        return {
            'op': 'add',
            'path': path,
            'value': self.value
        }


class ResourcesFix(FixAction):
    def __init__(self, rule_id: str, description: str, container_name: str,
                 resource_type: str, value: str):
        super().__init__(rule_id, description)
        self.container_name = container_name
        self.resource_type = resource_type
        self.value = value

    def apply(self, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        pod_spec = self._get_pod_spec(resource)
        if not pod_spec:
            return False

        container = self._find_container(pod_spec, self.container_name)
        if not container:
            return False

        if 'resources' not in container:
            container['resources'] = {}

        if self.resource_type in ['cpu_limit', 'memory_limit']:
            if 'limits' not in container['resources']:
                container['resources']['limits'] = {}
            key = 'cpu' if 'cpu' in self.resource_type else 'memory'
            container['resources']['limits'][key] = self.value
        else:
            if 'requests' not in container['resources']:
                container['resources']['requests'] = {}
            key = 'cpu' if 'cpu' in self.resource_type else 'memory'
            container['resources']['requests'][key] = self.value

        self.applied = True
        return True

    def _get_pod_spec(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = resource.get('kind', '')
        if kind == 'Pod':
            return resource.get('spec', {})
        elif kind == 'CronJob':
            return resource.get('spec', {}).get('jobTemplate', {}).get('spec', {}).get('template', {}).get('spec', {})
        else:
            return resource.get('spec', {}).get('template', {}).get('spec', {})

    def _find_container(self, pod_spec: Dict[str, Any], container_name: str) -> Optional[Dict[str, Any]]:
        for container_type in ['containers', 'initContainers', 'ephemeralContainers']:
            for container in pod_spec.get(container_type, []):
                if container.get('name') == container_name:
                    return container
        return None

    def get_patch(self) -> Dict[str, Any]:
        return {
            'op': 'add',
            'path': f'spec.template.spec.containers[].resources',
            'value': self.value
        }


class ImageTagFix(FixAction):
    def __init__(self, rule_id: str, description: str, container_name: str,
                 new_tag: str):
        super().__init__(rule_id, description)
        self.container_name = container_name
        self.new_tag = new_tag

    def apply(self, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        pod_spec = self._get_pod_spec(resource)
        if not pod_spec:
            return False

        container = self._find_container(pod_spec, self.container_name)
        if not container:
            return False

        image = container.get('image', '')
        if ':' in image:
            image_base = image.rsplit(':', 1)[0]
            container['image'] = f"{image_base}:{self.new_tag}"
        else:
            container['image'] = f"{image}:{self.new_tag}"

        self.applied = True
        return True

    def _get_pod_spec(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = resource.get('kind', '')
        if kind == 'Pod':
            return resource.get('spec', {})
        elif kind == 'CronJob':
            return resource.get('spec', {}).get('jobTemplate', {}).get('spec', {}).get('template', {}).get('spec', {})
        else:
            return resource.get('spec', {}).get('template', {}).get('spec', {})

    def _find_container(self, pod_spec: Dict[str, Any], container_name: str) -> Optional[Dict[str, Any]]:
        for container_type in ['containers', 'initContainers', 'ephemeralContainers']:
            for container in pod_spec.get(container_type, []):
                if container.get('name') == container_name:
                    return container
        return None

    def get_patch(self) -> Dict[str, Any]:
        return {
            'op': 'replace',
            'path': f'spec.template.spec.containers[].image',
            'value': self.new_tag
        }


class CapabilitiesFix(FixAction):
    def __init__(self, rule_id: str, description: str, container_name: str):
        super().__init__(rule_id, description)
        self.container_name = container_name

    def apply(self, resource: Dict[str, Any], context: Dict[str, Any]) -> bool:
        pod_spec = self._get_pod_spec(resource)
        if not pod_spec:
            return False

        container = self._find_container(pod_spec, self.container_name)
        if not container:
            return False

        if 'securityContext' not in container:
            container['securityContext'] = {}
        if 'capabilities' not in container['securityContext']:
            container['securityContext']['capabilities'] = {}
        
        capabilities = container['securityContext']['capabilities']
        if 'drop' not in capabilities:
            capabilities['drop'] = []
        if 'ALL' not in capabilities['drop']:
            capabilities['drop'].append('ALL')

        self.applied = True
        return True

    def _get_pod_spec(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = resource.get('kind', '')
        if kind == 'Pod':
            return resource.get('spec', {})
        elif kind == 'CronJob':
            return resource.get('spec', {}).get('jobTemplate', {}).get('spec', {}).get('template', {}).get('spec', {})
        else:
            return resource.get('spec', {}).get('template', {}).get('spec', {})

    def _find_container(self, pod_spec: Dict[str, Any], container_name: str) -> Optional[Dict[str, Any]]:
        for container_type in ['containers', 'initContainers', 'ephemeralContainers']:
            for container in pod_spec.get(container_type, []):
                if container.get('name') == container_name:
                    return container
        return None

    def get_patch(self) -> Dict[str, Any]:
        return {
            'op': 'add',
            'path': f'spec.template.spec.containers[].securityContext.capabilities.drop',
            'value': ['ALL']
        }


class AutoFixer:
    def __init__(self):
        self.fix_actions: List[FixAction] = []
        self.fixable_rules = {
            'cpu_limit_required': self._create_cpu_limit_fix,
            'cpu_request_required': self._create_cpu_request_fix,
            'memory_limit_required': self._create_memory_limit_fix,
            'memory_request_required': self._create_memory_request_fix,
            'privileged_container': self._create_privileged_fix,
            'read_only_root_filesystem': self._create_readonly_fix,
            'run_as_non_root': self._create_runasnonroot_fix,
            'allow_privilege_escalation': self._create_allow_priv_esc_fix,
            'capabilities_drop_all': self._create_capabilities_fix,
            'latest_tag': self._create_latest_tag_fix,
            'no_tag': self._create_no_tag_fix,
            'pod_run_as_non_root': self._create_pod_runasnonroot_fix,
            'pod_run_as_user': self._create_pod_runasuser_fix,
            'pod_seccomp_profile': self._create_pod_seccomp_fix,
            'pod_fs_group': self._create_pod_fsgroup_fix,
        }

    def generate_fixes(self, issues: List[Issue]) -> List[FixAction]:
        fixes = []
        for issue in issues:
            if issue.rule_id in self.fixable_rules:
                fix = self.fixable_rules[issue.rule_id](issue)
                if fix:
                    fixes.append(fix)
        self.fix_actions = fixes
        return fixes

    def apply_fixes(self, resource: Dict[str, Any], fixes: List[FixAction]) -> Dict[str, Any]:
        modified_resource = copy.deepcopy(resource)
        context = {}
        for fix in fixes:
            fix.apply(modified_resource, context)
        return modified_resource

    def apply_fixes_to_file(self, input_file: str, output_file: Optional[str] = None,
                            issues: Optional[List[Issue]] = None) -> Tuple[bool, str]:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        documents = list(yaml.safe_load_all(content))
        
        if issues:
            fixes = self.generate_fixes(issues)
        else:
            fixes = self.fix_actions

        modified_docs = []
        for doc in documents:
            if doc:
                modified_doc = self.apply_fixes(doc, fixes)
                modified_docs.append(modified_doc)
            else:
                modified_docs.append(doc)

        output_content = yaml.safe_dump_all(modified_docs, default_flow_style=False, sort_keys=False)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_content)
            return True, output_file
        else:
            return True, output_content

    def get_fix_summary(self, fixes: List[FixAction]) -> Dict[str, Any]:
        applied = [f for f in fixes if f.applied]
        return {
            'total': len(fixes),
            'applied': len(applied),
            'fixes': [
                {
                    'rule_id': f.rule_id,
                    'description': f.description,
                    'applied': f.applied
                }
                for f in fixes
            ]
        }

    def _create_cpu_limit_fix(self, issue: Issue) -> Optional[FixAction]:
        return ResourcesFix(
            issue.rule_id,
            '添加CPU限制',
            issue.container_name,
            'cpu_limit',
            '500m'
        )

    def _create_cpu_request_fix(self, issue: Issue) -> Optional[FixAction]:
        return ResourcesFix(
            issue.rule_id,
            '添加CPU请求',
            issue.container_name,
            'cpu_request',
            '250m'
        )

    def _create_memory_limit_fix(self, issue: Issue) -> Optional[FixAction]:
        return ResourcesFix(
            issue.rule_id,
            '添加内存限制',
            issue.container_name,
            'memory_limit',
            '512Mi'
        )

    def _create_memory_request_fix(self, issue: Issue) -> Optional[FixAction]:
        return ResourcesFix(
            issue.rule_id,
            '添加内存请求',
            issue.container_name,
            'memory_request',
            '256Mi'
        )

    def _create_privileged_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            '禁用特权模式',
            issue.container_name,
            'privileged',
            False
        )

    def _create_readonly_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            '启用只读根文件系统',
            issue.container_name,
            'readOnlyRootFilesystem',
            True
        )

    def _create_runasnonroot_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            '配置以非root用户运行',
            issue.container_name,
            'runAsNonRoot',
            True
        )

    def _create_allow_priv_esc_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            '禁用权限提升',
            issue.container_name,
            'allowPrivilegeEscalation',
            False
        )

    def _create_capabilities_fix(self, issue: Issue) -> Optional[FixAction]:
        return CapabilitiesFix(
            issue.rule_id,
            '丢弃所有Linux capabilities',
            issue.container_name
        )

    def _create_latest_tag_fix(self, issue: Issue) -> Optional[FixAction]:
        return ImageTagFix(
            issue.rule_id,
            '替换latest标签为稳定版本',
            issue.container_name,
            'stable'
        )

    def _create_no_tag_fix(self, issue: Issue) -> Optional[FixAction]:
        return ImageTagFix(
            issue.rule_id,
            '添加默认版本标签',
            issue.container_name,
            'latest'
        )

    def _create_pod_runasnonroot_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            'Pod级配置以非root用户运行',
            '',
            'runAsNonRoot',
            True,
            is_pod_level=True
        )

    def _create_pod_runasuser_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            'Pod级配置运行用户ID',
            '',
            'runAsUser',
            1000,
            is_pod_level=True
        )

    def _create_pod_seccomp_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            'Pod级配置seccomp',
            '',
            'seccompProfile',
            {'type': 'RuntimeDefault'},
            is_pod_level=True
        )

    def _create_pod_fsgroup_fix(self, issue: Issue) -> Optional[FixAction]:
        return SecurityContextFix(
            issue.rule_id,
            'Pod级配置文件系统组',
            '',
            'fsGroup',
            1000,
            is_pod_level=True
        )
