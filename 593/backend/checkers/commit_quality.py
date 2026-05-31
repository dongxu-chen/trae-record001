import uuid
import re
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class CommitQualityChecker(Checker):
    CATEGORY = 'commit_quality'
    DISPLAY_NAME = '提交质量分析'

    def _build_rules(self):
        pass

    def check(self, branch: str = None, days: int = 30) -> CheckResult:
        if branch is None:
            branch = self.git_utils.get_current_branch()

        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={'branch': branch, 'days': days}
        )

        rules = self.config.get_commit_quality_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name='提交质量检查已跳过',
                description='提交质量检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Commit quality check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        min_length = rules.get('min_length', 10)
        max_length = rules.get('max_length', 100)
        required_prefixes = rules.get('required_prefixes', ['feat:', 'fix:', 'docs:', 'style:', 'refactor:', 'test:', 'chore:'])
        forbidden_words = rules.get('forbidden_words', ['wip', 'fix', 'update', 'temp', 'tmp', 'debug'])
        check_imperative = rules.get('check_imperative', True)
        severity = Severity(rules.get('severity', 'warning'))

        commit_history = self.git_utils.get_commit_history(branch, days=days)

        if not commit_history:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name='无提交记录',
                description=f'{days}天内该分支无提交记录',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message=f'最近 {days} 天内没有找到提交记录'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        issues_by_type = defaultdict(list)
        good_commits = []

        for commit in commit_history:
            message = commit['message'].split('\n')[0].strip()
            issues = self._check_single_commit(
                message, min_length, max_length,
                required_prefixes, forbidden_words, check_imperative
            )
            
            if issues:
                for issue in issues:
                    issues_by_type[issue['type']].append({
                        'hash': commit['hash'][:7],
                        'message': message,
                        'author': commit['author'],
                        'date': commit['date'].strftime('%Y-%m-%d'),
                        'detail': issue['detail']
                    })
            else:
                good_commits.append({
                    'hash': commit['hash'][:7],
                    'message': message,
                    'author': commit['author']
                })

        total_commits = len(commit_history)
        total_issues = sum(len(v) for v in issues_by_type.values())
        compliance_rate = ((total_commits - len(issues_by_type)) / total_commits * 100) if total_commits > 0 else 100

        check_result.metadata.update({
            'total_commits': total_commits,
            'total_issues': total_issues,
            'compliance_rate': round(compliance_rate, 2),
            'issues_by_type': dict(issues_by_type),
            'good_commits': good_commits[:10],
            'good_commits_count': len(good_commits)
        })

        has_errors = False
        has_warnings = False

        if 'too_short' in issues_by_type:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'提交信息过短 - {len(issues_by_type["too_short"])}个',
                description='部分提交信息长度不足，无法明确表达变更内容',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=severity,
                message=f'有 {len(issues_by_type["too_short"])} 个提交信息长度不足 {min_length} 字符',
                details={'count': len(issues_by_type['too_short']), 'examples': issues_by_type['too_short'][:5]},
                suggestion=f'请完善提交信息，描述清楚变更内容，建议至少 {min_length} 个字符',
                documentation_url='https://your-team-docs.com/commit-message-guide'
            )
            check_result.items.append(item)
            has_warnings = True

        if 'too_long' in issues_by_type:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'提交信息过长 - {len(issues_by_type["too_long"])}个',
                description='部分提交信息过长，建议拆分为多行',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'有 {len(issues_by_type["too_long"])} 个提交信息超过 {max_length} 字符',
                details={'count': len(issues_by_type['too_long']), 'examples': issues_by_type['too_long'][:5]},
                suggestion=f'标题建议不超过 {max_length} 字符，详细描述请放在正文部分（空行后）',
                documentation_url='https://your-team-docs.com/commit-message-guide'
            )
            check_result.items.append(item)
            has_warnings = True

        if 'missing_prefix' in issues_by_type:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'缺少类型前缀 - {len(issues_by_type["missing_prefix"])}个',
                description='提交信息应使用标准前缀标识变更类型',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'有 {len(issues_by_type["missing_prefix"])} 个提交缺少类型前缀',
                details={
                    'count': len(issues_by_type['missing_prefix']),
                    'required_prefixes': required_prefixes,
                    'examples': issues_by_type['missing_prefix'][:5]
                },
                suggestion=f'请使用以下前缀之一: {", ".join(required_prefixes)}',
                documentation_url='https://your-team-docs.com/commit-convention'
            )
            check_result.items.append(item)
            has_errors = True

        if 'forbidden_word' in issues_by_type:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'禁用词检查 - {len(issues_by_type["forbidden_word"])}个',
                description='提交信息包含不规范的描述词',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'有 {len(issues_by_type["forbidden_word"])} 个提交包含禁用词汇',
                details={
                    'count': len(issues_by_type['forbidden_word']),
                    'forbidden_words': forbidden_words,
                    'examples': issues_by_type['forbidden_word'][:5]
                },
                suggestion='请使用更具体的描述词，避免使用模糊的词汇如 fix/update/temp 等',
                documentation_url='https://your-team-docs.com/commit-message-guide'
            )
            check_result.items.append(item)
            has_warnings = True

        if 'not_imperative' in issues_by_type:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'祈使语气检查 - {len(issues_by_type["not_imperative"])}个',
                description='提交信息建议使用祈使语气（动词原形开头）',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.INFO,
                message=f'有 {len(issues_by_type["not_imperative"])} 个提交可能未使用祈使语气',
                details={'count': len(issues_by_type['not_imperative']), 'examples': issues_by_type['not_imperative'][:5]},
                suggestion='提交信息标题建议使用祈使语气，如 "Add feature" 而非 "Added feature" 或 "Adding feature"',
                documentation_url='https://your-team-docs.com/commit-message-guide'
            )
            check_result.items.append(item)
            has_warnings = True

        if compliance_rate < 70:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name=f'规范遵守率偏低 - {compliance_rate:.1f}%',
                description='整体提交规范遵守率低于70%',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=Severity.ERROR,
                message=f'最近 {days} 天的提交规范遵守率仅为 {compliance_rate:.1f}%，需要改进',
                details={
                    'compliance_rate': compliance_rate,
                    'threshold': 70,
                    'total_commits': total_commits,
                    'issue_commits': len(issues_by_type)
                },
                suggestion='请团队成员学习提交规范，提高代码审查时的提交信息质量要求',
                documentation_url='https://your-team-docs.com/commit-convention'
            )
            check_result.items.append(item)
            has_errors = True

        if not has_errors and not has_warnings:
            item = CheckItem(
                id=f'cq-{uuid.uuid4().hex[:8]}',
                name='提交质量良好',
                description='所有提交信息都符合规范要求',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'最近 {days} 天共 {total_commits} 次提交，规范遵守率 {compliance_rate:.1f}%，质量良好',
                details={
                    'total_commits': total_commits,
                    'compliance_rate': compliance_rate,
                    'good_examples': good_commits[:5]
                }
            )
            check_result.items.append(item)
        else:
            check_result.status = CheckStatus.FAIL if has_errors else CheckStatus.WARNING

        return check_result

    def _check_single_commit(self, message: str, min_length: int, max_length: int,
                            required_prefixes: List[str], forbidden_words: List[str],
                            check_imperative: bool) -> List[Dict]:
        issues = []
        message_lower = message.lower()

        if len(message) < min_length:
            issues.append({
                'type': 'too_short',
                'detail': f'长度: {len(message)} 字符'
            })

        if len(message) > max_length:
            issues.append({
                'type': 'too_long',
                'detail': f'长度: {len(message)} 字符'
            })

        has_prefix = any(message.startswith(prefix) for prefix in required_prefixes)
        if not has_prefix:
            issues.append({
                'type': 'missing_prefix',
                'detail': f'未使用标准前缀'
            })

        for word in forbidden_words:
            if re.search(r'\b' + re.escape(word) + r'\b', message_lower):
                issues.append({
                    'type': 'forbidden_word',
                    'detail': f'包含禁用词: {word}'
                })
                break

        if check_imperative and len(message) > 0:
            first_word = message.split()[0] if message.split() else ''
            if first_word.endswith(('ed', 'ing', 's')) and not first_word.endswith(('ss', 'es')):
                issues.append({
                    'type': 'not_imperative',
                    'detail': f'首词: {first_word}'
                })

        return issues
