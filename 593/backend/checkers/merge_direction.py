import uuid
from typing import Dict
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus, RuleEngine


class MergeDirectionChecker(Checker):
    CATEGORY = 'merge_direction'
    DISPLAY_NAME = '合并方向检查'

    def _build_rules(self):
        pass

    def check(self, source_branch: str, target_branch: str) -> CheckResult:
        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={
                'source_branch': source_branch,
                'target_branch': target_branch
            }
        )

        rules = self.config.get_merge_direction_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'md-{uuid.uuid4().hex[:8]}',
                name='合并方向检查已跳过',
                description='合并方向检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Merge direction check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        severity = Severity(rules.get('severity', 'error'))
        allowed_merges = rules.get('allowed_merges', [])
        blocked_merges = rules.get('blocked_merges', [])

        allowed = False
        blocked = False
        matching_rules = []

        for blocked_rule in blocked_merges:
            if self._matches_pattern(source_branch, blocked_rule['from']) and \
               self._matches_pattern(target_branch, blocked_rule['to']):
                blocked = True
                matching_rules.append(blocked_rule)
                break

        if blocked:
            item = CheckItem(
                id=f'md-{uuid.uuid4().hex[:8]}',
                name='合并方向被阻止',
                description='该合并方向在黑名单中',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'不允许从 "{source_branch}" 合并到 "{target_branch}"',
                details={
                    'source': source_branch,
                    'target': target_branch,
                    'blocked_by': matching_rules
                },
                suggestion='请检查合并方向是否正确，或联系管理员调整规则',
                documentation_url='https://your-team-docs.com/merge-strategy'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.FAIL
            check_result.metadata['allowed'] = False
            return check_result

        for allowed_rule in allowed_merges:
            if self._matches_pattern(source_branch, allowed_rule['from']) and \
               self._matches_pattern(target_branch, allowed_rule['to']):
                allowed = True
                matching_rules.append(allowed_rule)
                break

        if allowed:
            item = CheckItem(
                id=f'md-{uuid.uuid4().hex[:8]}',
                name='合并方向允许',
                description='该合并方向在白名单中',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=severity,
                message=f'允许从 "{source_branch}" 合并到 "{target_branch}"',
                details={'matched_rules': matching_rules},
                documentation_url='https://your-team-docs.com/merge-strategy'
            )
            check_result.items.append(item)
        else:
            item = CheckItem(
                id=f'md-{uuid.uuid4().hex[:8]}',
                name='合并方向未授权',
                description='该合并方向不在白名单中',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'从 "{source_branch}" 合并到 "{target_branch}" 未被授权',
                details={
                    'source': source_branch,
                    'target': target_branch,
                    'allowed_merges': allowed_merges,
                    'blocked_merges': blocked_merges
                },
                suggestion='请确认合并方向是否正确，或申请添加新的合并规则',
                documentation_url='https://your-team-docs.com/merge-strategy'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.FAIL

        check_result.metadata['allowed'] = allowed and not blocked
        return check_result

    def _matches_pattern(self, branch_name: str, pattern: str) -> bool:
        return RuleEngine.match_glob_pattern(branch_name, pattern)
