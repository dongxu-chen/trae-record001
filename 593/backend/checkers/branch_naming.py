import re
import uuid
from typing import Dict
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class BranchNamingChecker(Checker):
    CATEGORY = 'branch_naming'
    DISPLAY_NAME = '分支命名规范检查'

    def _build_rules(self):
        pass

    def check(self, branch_name: str = None) -> CheckResult:
        if branch_name is None:
            branch_name = self.git_utils.get_current_branch()

        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={'branch_name': branch_name}
        )

        rules = self.config.get_branch_naming_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'bn-{uuid.uuid4().hex[:8]}',
                name='分支命名检查已跳过',
                description='分支命名检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Branch naming check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        patterns = rules.get('patterns', [])
        allow_custom = rules.get('allow_custom', False)
        default_severity = Severity(rules.get('severity', 'error'))

        matched = False
        matched_pattern = None
        failed_patterns = []

        for pattern_config in patterns:
            pattern = pattern_config.get('pattern', '')
            description = pattern_config.get('description', '')
            name = pattern_config.get('name', 'unknown')

            if re.match(pattern, branch_name):
                matched = True
                matched_pattern = name
                
                item = CheckItem(
                    id=f'bn-{uuid.uuid4().hex[:8]}',
                    name=f'分支类型: {name}',
                    description=description,
                    category=self.CATEGORY,
                    status=CheckStatus.PASS,
                    severity=default_severity,
                    message=f'分支名 "{branch_name}" 匹配 {name} 模式',
                    details={'pattern': pattern, 'matched': name},
                    documentation_url='https://your-team-docs.com/branch-naming'
                )
                check_result.items.append(item)
                break
            else:
                failed_patterns.append(name)

        if not matched:
            severity = default_severity
            if allow_custom:
                severity = Severity.WARNING
            
            suggestion = self.suggest_fix(branch_name)
            
            item = CheckItem(
                id=f'bn-{uuid.uuid4().hex[:8]}',
                name='分支命名不规范',
                description='分支名称不符合团队约定的命名规范',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'分支 "{branch_name}" 不符合任何允许的命名模式',
                details={
                    'branch_name': branch_name,
                    'failed_patterns': failed_patterns,
                    'allowed_patterns': [p.get('description', '') for p in patterns]
                },
                suggestion=f'建议命名为: {suggestion}',
                documentation_url='https://your-team-docs.com/branch-naming'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.FAIL
            check_result.metadata['suggested_name'] = suggestion

        check_result.metadata.update({
            'matched': matched,
            'matched_pattern': matched_pattern
        })

        return check_result

    def suggest_fix(self, branch_name: str) -> str:
        if branch_name.startswith('feature/'):
            if not re.match(r'^feature/[A-Z]+-\d+-.+$', branch_name):
                return f'feature/TICKET-001-{branch_name.replace("feature/", "")}'
        elif branch_name.startswith('bugfix/'):
            if not re.match(r'^bugfix/[A-Z]+-\d+-.+$', branch_name):
                return f'bugfix/TICKET-001-{branch_name.replace("bugfix/", "")}'
        elif branch_name.startswith('hotfix/'):
            if not re.match(r'^hotfix/.+$', branch_name):
                return f'hotfix/{branch_name.replace("hotfix/", "")}'
        elif branch_name.startswith('release/'):
            if not re.match(r'^release/v\d+\.\d+\.\d+$', branch_name):
                return 'release/v1.0.0'
        return branch_name
