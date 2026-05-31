import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class CommitFrequencyChecker(Checker):
    CATEGORY = 'commit_frequency'
    DISPLAY_NAME = '提交频率检查'

    def _build_rules(self):
        pass

    def check(self, branch: str = None, days: int = 7) -> CheckResult:
        if branch is None:
            branch = self.git_utils.get_current_branch()

        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={'branch': branch, 'days': days}
        )

        rules = self.config.get_commit_frequency_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'cf-{uuid.uuid4().hex[:8]}',
                name='提交频率检查已跳过',
                description='提交频率检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Commit frequency check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        severity = Severity(rules.get('severity', 'warning'))
        max_commits_per_day = rules.get('max_commits_per_day', 20)
        min_commits_per_week = rules.get('min_commits_per_week', 1)
        check_authors = rules.get('check_authors', True)

        commit_history = self.git_utils.get_commit_history(branch, days=days)
        
        commits_by_day = defaultdict(list)
        commits_by_author = defaultdict(list)

        for commit in commit_history:
            commit_date = commit['date'].date()
            commits_by_day[commit_date].append(commit)
            commits_by_author[commit['author']].append(commit)

        total_commits = len(commit_history)
        avg_commits_per_day = total_commits / days if days > 0 else 0

        check_result.metadata.update({
            'total_commits': total_commits,
            'avg_per_day': avg_commits_per_day,
            'commits_by_day': {str(k): len(v) for k, v in commits_by_day.items()},
            'commits_by_author': {k: len(v) for k, v in commits_by_author.items()},
            'commits': commit_history
        })

        has_errors = False
        has_warnings = False

        for date, day_commits in commits_by_day.items():
            if len(day_commits) > max_commits_per_day:
                item = CheckItem(
                    id=f'cf-{uuid.uuid4().hex[:8]}',
                    name=f'日提交数超限 - {date}',
                    description='单日提交数超过最大限制',
                    category=self.CATEGORY,
                    status=CheckStatus.FAIL,
                    severity=severity,
                    message=f'{date} 提交数过多: {len(day_commits)} (最大: {max_commits_per_day})',
                    details={
                        'date': str(date),
                        'commits': len(day_commits),
                        'max': max_commits_per_day,
                        'commit_hashes': [c['hash'][:7] for c in day_commits]
                    },
                    suggestion='考虑将多个提交压缩（squash），或分多天提交',
                    documentation_url='https://your-team-docs.com/commit-best-practices'
                )
                check_result.items.append(item)
                has_errors = True

        if total_commits < min_commits_per_week:
            item = CheckItem(
                id=f'cf-{uuid.uuid4().hex[:8]}',
                name='周提交数不足',
                description='检查周期内提交数少于最小值',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'{days}天内提交数不足: {total_commits} (最小: {min_commits_per_week})',
                details={
                    'commits': total_commits,
                    'min': min_commits_per_week,
                    'days': days
                },
                suggestion='请保持规律的提交习惯，至少每周提交一次',
                documentation_url='https://your-team-docs.com/commit-best-practices'
            )
            check_result.items.append(item)
            has_errors = True

        if check_authors:
            for author, author_commits in commits_by_author.items():
                avg_per_day = len(author_commits) / days
                if avg_per_day > max_commits_per_day:
                    item = CheckItem(
                        id=f'cf-{uuid.uuid4().hex[:8]}',
                        name=f'提交者高频 - {author}',
                        description='单个开发者提交频率过高',
                        category=self.CATEGORY,
                        status=CheckStatus.WARNING,
                        severity=Severity.WARNING,
                        message=f'开发者 {author} 提交频率较高: {avg_per_day:.1f}次/天',
                        details={
                            'author': author,
                            'commits': len(author_commits),
                            'avg_per_day': avg_per_day
                        },
                        suggestion='建议检查是否有过多的细碎提交，考虑合并相关提交',
                        documentation_url='https://your-team-docs.com/commit-best-practices'
                    )
                    check_result.items.append(item)
                    has_warnings = True

        if not has_errors and not has_warnings:
            item = CheckItem(
                id=f'cf-{uuid.uuid4().hex[:8]}',
                name='提交频率正常',
                description='提交频率在合理范围内',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'{days}天内共 {total_commits} 次提交，日均 {avg_commits_per_day:.1f} 次',
                details={
                    'total_commits': total_commits,
                    'avg_per_day': avg_commits_per_day,
                    'num_authors': len(commits_by_author)
                }
            )
            check_result.items.append(item)
        else:
            check_result.status = CheckStatus.FAIL if has_errors else CheckStatus.WARNING

        return check_result
