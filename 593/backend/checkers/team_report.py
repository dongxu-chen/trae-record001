import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class TeamReportChecker(Checker):
    CATEGORY = 'team_report'
    DISPLAY_NAME = '团队简报统计'

    def _build_rules(self):
        pass

    def check(self, branch: str = None, days: int = 30) -> CheckResult:
        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={'days': days, 'report_date': datetime.now().isoformat()}
        )

        rules = self.config.get_team_report_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'tr-{uuid.uuid4().hex[:8]}',
                name='团队简报统计已跳过',
                description='团队简报统计在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Team report is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        all_branches = self.git_utils.get_all_branches()
        exclude_branches = rules.get('exclude_branches', ['main', 'master', 'develop'])
        branches_to_analyze = [b for b in all_branches if b not in exclude_branches]

        all_commits = []
        for br in branches_to_analyze:
            try:
                commits = self.git_utils.get_commit_history(br, days=days)
                all_commits.extend(commits)
            except Exception:
                continue

        if not all_commits:
            item = CheckItem(
                id=f'tr-{uuid.uuid4().hex[:8]}',
                name='无团队活动数据',
                description=f'{days}天内无团队提交记录',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message=f'最近 {days} 天内没有找到团队提交记录'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        author_stats = self._calculate_author_stats(all_commits, rules)
        branch_stats = self._calculate_branch_stats(all_commits)
        overall_stats = self._calculate_overall_stats(all_commits, author_stats)

        check_result.metadata.update({
            'total_commits': len(all_commits),
            'total_authors': len(author_stats),
            'overall': overall_stats,
            'author_stats': author_stats,
            'branch_stats': branch_stats,
            'analysis_period': f'{days}天'
        })

        excellent_members = [a for a, s in author_stats.items() if s['compliance_rate'] >= 90]
        needs_improvement = [a for a, s in author_stats.items() if s['compliance_rate'] < 70]

        if excellent_members:
            item = CheckItem(
                id=f'tr-{uuid.uuid4().hex[:8]}',
                name=f'🌟 优秀成员 - {len(excellent_members)}人',
                description='规范遵守率达到90%以上的成员',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'有 {len(excellent_members)} 位成员提交规范遵守率优秀（≥90%）',
                details={
                    'members': [
                        {
                            'name': m,
                            'commits': author_stats[m]['total_commits'],
                            'compliance_rate': author_stats[m]['compliance_rate']
                        } for m in excellent_members
                    ]
                }
            )
            check_result.items.append(item)

        if needs_improvement:
            item = CheckItem(
                id=f'tr-{uuid.uuid4().hex[:8]}',
                name=f'📈 需要改进 - {len(needs_improvement)}人',
                description='规范遵守率低于70%的成员',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'有 {len(needs_improvement)} 位成员提交规范遵守率需要改进（<70%）',
                details={
                    'members': [
                        {
                            'name': m,
                            'commits': author_stats[m]['total_commits'],
                            'compliance_rate': author_stats[m]['compliance_rate'],
                            'top_issues': author_stats[m]['issue_summary']
                        } for m in needs_improvement
                    ]
                },
                suggestion='建议这些成员学习团队提交规范，或在提交前使用钩子检查工具',
                documentation_url='https://your-team-docs.com/commit-convention'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.WARNING

        inactive_members = [a for a, s in author_stats.items() if s.get('inactive_days', 0) > 14]
        if inactive_members:
            item = CheckItem(
                id=f'tr-{uuid.uuid4().hex[:8]}',
                name=f'💤 近期不活跃成员 - {len(inactive_members)}人',
                description='超过14天未提交代码的成员',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.INFO,
                message=f'有 {len(inactive_members)} 位成员超过14天未提交代码',
                details={
                    'members': [
                        {
                            'name': m,
                            'inactive_days': author_stats[m]['inactive_days'],
                            'last_commit': author_stats[m]['last_commit']
                        } for m in inactive_members
                    ]
                }
            )
            check_result.items.append(item)

        item = CheckItem(
            id=f'tr-{uuid.uuid4().hex[:8]}',
            name='团队整体统计',
            description=f'{days}天团队活动概览',
            category=self.CATEGORY,
            status=CheckStatus.PASS,
            severity=Severity.INFO,
            message=f'{days}天内：{len(all_commits)}次提交 | {len(author_stats)}位活跃成员 | 整体规范遵守率 {overall_stats["avg_compliance_rate"]:.1f}%',
            details={
                'period_days': days,
                'total_commits': len(all_commits),
                'active_members': len(author_stats),
                'avg_compliance_rate': overall_stats['avg_compliance_rate'],
                'avg_commits_per_member': overall_stats['avg_commits_per_member']
            }
        )
        check_result.items.append(item)

        return check_result

    def _calculate_author_stats(self, commits: List[Dict], rules: Dict) -> Dict:
        author_commits = defaultdict(list)
        for c in commits:
            author_commits[c['author']].append(c)

        quality_rules = self.config.get_commit_quality_rules()
        min_length = quality_rules.get('min_length', 10)
        max_length = quality_rules.get('max_length', 100)
        required_prefixes = quality_rules.get('required_prefixes', ['feat:', 'fix:', 'docs:'])
        forbidden_words = quality_rules.get('forbidden_words', ['wip', 'fix', 'update'])
        check_imperative = quality_rules.get('check_imperative', True)

        from .commit_quality import CommitQualityChecker
        quality_checker = CommitQualityChecker(self.git_utils, self.config)

        author_stats = {}
        now = datetime.now()

        for author, author_commit_list in author_commits.items():
            issues_by_type = defaultdict(int)
            good_commits = 0

            for commit in author_commit_list:
                message = commit['message'].split('\n')[0].strip()
                issues = quality_checker._check_single_commit(
                    message, min_length, max_length,
                    required_prefixes, forbidden_words, check_imperative
                )
                if issues:
                    for issue in issues:
                        issues_by_type[issue['type']] += 1
                else:
                    good_commits += 1

            total_commits = len(author_commit_list)
            compliance_rate = (good_commits / total_commits * 100) if total_commits > 0 else 100

            sorted_issues = sorted(issues_by_type.items(), key=lambda x: -x[1])
            issue_summary = [{'type': k, 'count': v} for k, v in sorted_issues[:3]]

            last_commit_date = max(c['date'] for c in author_commit_list)
            inactive_days = (now - last_commit_date).days

            author_stats[author] = {
                'total_commits': total_commits,
                'good_commits': good_commits,
                'compliance_rate': round(compliance_rate, 1),
                'issues_by_type': dict(issues_by_type),
                'issue_summary': issue_summary,
                'first_commit': min(c['date'] for c in author_commit_list).strftime('%Y-%m-%d'),
                'last_commit': last_commit_date.strftime('%Y-%m-%d'),
                'inactive_days': inactive_days,
                'files_changed': sum(c.get('files_changed', 0) for c in author_commit_list),
                'additions': sum(c.get('additions', 0) for c in author_commit_list),
                'deletions': sum(c.get('deletions', 0) for c in author_commit_list)
            }

        return author_stats

    def _calculate_branch_stats(self, commits: List[Dict]) -> Dict:
        branch_commits = defaultdict(list)
        for c in commits:
            branch_commits[c.get('branch', 'unknown')].append(c)

        branch_stats = {}
        for branch, branch_commit_list in branch_commits.items():
            branch_stats[branch] = {
                'commits': len(branch_commit_list),
                'authors': len(set(c['author'] for c in branch_commit_list)),
                'last_activity': max(c['date'] for c in branch_commit_list).strftime('%Y-%m-%d')
            }

        return branch_stats

    def _calculate_overall_stats(self, commits: List[Dict], author_stats: Dict) -> Dict:
        total_authors = len(author_stats)
        total_commits = len(commits)

        avg_compliance = sum(s['compliance_rate'] for s in author_stats.values()) / total_authors if total_authors > 0 else 0
        avg_commits = total_commits / total_authors if total_authors > 0 else 0

        issue_distribution = defaultdict(int)
        for stats in author_stats.values():
            for issue_type, count in stats['issues_by_type'].items():
                issue_distribution[issue_type] += count

        return {
            'avg_compliance_rate': round(avg_compliance, 1),
            'avg_commits_per_member': round(avg_commits, 1),
            'issue_distribution': dict(issue_distribution),
            'top_issue_types': sorted(issue_distribution.items(), key=lambda x: -x[1])[:5],
            'total_additions': sum(c.get('additions', 0) for c in commits),
            'total_deletions': sum(c.get('deletions', 0) for c in commits),
            'total_files_changed': sum(c.get('files_changed', 0) for c in commits)
        }
