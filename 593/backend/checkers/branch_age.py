import uuid
from datetime import datetime, timedelta
from typing import Dict, List
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class BranchAgeChecker(Checker):
    CATEGORY = 'branch_age'
    DISPLAY_NAME = '分支年龄检查'

    def _build_rules(self):
        pass

    def check(self, branch: str = None, target_branch: str = 'develop') -> CheckResult:
        if branch is None:
            branch = self.git_utils.get_current_branch()

        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={'branch': branch, 'target_branch': target_branch}
        )

        rules = self.config.get_branch_age_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'ba-{uuid.uuid4().hex[:8]}',
                name='分支年龄检查已跳过',
                description='分支年龄检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Branch age check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        warning_days = rules.get('warning_days', 30)
        critical_days = rules.get('critical_days', 60)
        stale_days = rules.get('stale_days', 90)
        exclude_branches = rules.get('exclude_branches', ['main', 'master', 'develop'])
        severity = Severity(rules.get('severity', 'warning'))

        try:
            merge_base = self.git_utils.repo.merge_base(branch, target_branch)
            if not merge_base:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name='无法计算分支年龄',
                    description='找不到两个分支的共同祖先',
                    category=self.CATEGORY,
                    status=CheckStatus.WARNING,
                    severity=Severity.WARNING,
                    message=f'分支 {branch} 与目标分支 {target_branch} 无共同祖先'
                )
                check_result.items.append(item)
                check_result.status = CheckStatus.WARNING
                return check_result

            base_commit = merge_base[0]
            base_date = datetime.fromtimestamp(base_commit.committed_date)
            now = datetime.now()
            age_days = (now - base_date).days

            branch_commits = list(self.git_utils.repo.iter_commits(f'{base_commit}..{branch}'))
            last_commit_date = datetime.fromtimestamp(branch_commits[0].committed_date) if branch_commits else base_date
            inactive_days = (now - last_commit_date).days

            check_result.metadata.update({
                'creation_date': base_date.isoformat(),
                'last_activity_date': last_commit_date.isoformat(),
                'age_days': age_days,
                'inactive_days': inactive_days,
                'commit_count': len(branch_commits)
            })

            has_errors = False
            has_warnings = False

            if age_days >= stale_days:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name=f'⚠️ 分支已过期 - {age_days}天',
                    description='分支创建时间过长，建议尽快合入或删除',
                    category=self.CATEGORY,
                    status=CheckStatus.FAIL,
                    severity=Severity.ERROR,
                    message=f'分支已存在 {age_days} 天（超过 {stale_days} 天阈值），可能已过时',
                    details={
                        'age_days': age_days,
                        'stale_threshold': stale_days,
                        'creation_date': base_date.strftime('%Y-%m-%d')
                    },
                    suggestion='建议：1) 尽快将此分支合入目标分支 2) 如不再需要请删除此分支 3) 如需继续开发，建议创建新分支',
                    documentation_url='https://your-team-docs.com/branch-lifecycle'
                )
                check_result.items.append(item)
                has_errors = True
            elif age_days >= critical_days:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name=f'分支年龄较大 - {age_days}天',
                    description='分支创建时间较长，建议尽快合入',
                    category=self.CATEGORY,
                    status=CheckStatus.FAIL,
                    severity=severity,
                    message=f'分支已存在 {age_days} 天（超过 {critical_days} 天阈值），建议尽快处理',
                    details={
                        'age_days': age_days,
                        'critical_threshold': critical_days,
                        'creation_date': base_date.strftime('%Y-%m-%d')
                    },
                    suggestion=f'请在本周内完成代码审查并将此分支合入 {target_branch}',
                    documentation_url='https://your-team-docs.com/branch-lifecycle'
                )
                check_result.items.append(item)
                has_errors = True
            elif age_days >= warning_days:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name=f'分支年龄提醒 - {age_days}天',
                    description='分支创建时间接近阈值，请注意',
                    category=self.CATEGORY,
                    status=CheckStatus.WARNING,
                    severity=Severity.WARNING,
                    message=f'分支已存在 {age_days} 天（建议不超过 {warning_days} 天）',
                    details={
                        'age_days': age_days,
                        'warning_threshold': warning_days,
                        'creation_date': base_date.strftime('%Y-%m-%d')
                    },
                    suggestion='建议加快开发进度，尽早创建PR进行代码审查',
                    documentation_url='https://your-team-docs.com/branch-lifecycle'
                )
                check_result.items.append(item)
                has_warnings = True

            if inactive_days >= critical_days:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name=f'分支长期无活动 - {inactive_days}天',
                    description='分支长时间未更新，可能已被废弃',
                    category=self.CATEGORY,
                    status=CheckStatus.FAIL,
                    severity=Severity.ERROR,
                    message=f'分支已 {inactive_days} 天无新提交，可能已被遗忘或废弃',
                    details={
                        'inactive_days': inactive_days,
                        'last_activity': last_commit_date.strftime('%Y-%m-%d')
                    },
                    suggestion='建议确认此分支是否仍在使用，如已废弃请及时删除以保持仓库整洁',
                    documentation_url='https://your-team-docs.com/branch-cleanup'
                )
                check_result.items.append(item)
                has_errors = True
            elif inactive_days >= warning_days and inactive_days < critical_days:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name=f'分支无活动提醒 - {inactive_days}天',
                    description='分支近期无更新',
                    category=self.CATEGORY,
                    status=CheckStatus.WARNING,
                    severity=Severity.WARNING,
                    message=f'分支已 {inactive_days} 天无新提交',
                    details={
                        'inactive_days': inactive_days,
                        'last_activity': last_commit_date.strftime('%Y-%m-%d')
                    },
                    suggestion='如仍在开发中，请保持规律的提交习惯；如已完成请尽快合入',
                    documentation_url='https://your-team-docs.com/branch-best-practices'
                )
                check_result.items.append(item)
                has_warnings = True

            if not has_errors and not has_warnings:
                item = CheckItem(
                    id=f'ba-{uuid.uuid4().hex[:8]}',
                    name='分支年龄正常',
                    description='分支生命周期在合理范围内',
                    category=self.CATEGORY,
                    status=CheckStatus.PASS,
                    severity=Severity.INFO,
                    message=f'分支已创建 {age_days} 天，最近活动 {inactive_days} 天前，共 {len(branch_commits)} 次提交',
                    details={
                        'age_days': age_days,
                        'inactive_days': inactive_days,
                        'commit_count': len(branch_commits),
                        'creation_date': base_date.strftime('%Y-%m-%d'),
                        'last_activity': last_commit_date.strftime('%Y-%m-%d')
                    }
                )
                check_result.items.append(item)
            else:
                check_result.status = CheckStatus.FAIL if has_errors else CheckStatus.WARNING

        except Exception as e:
            item = CheckItem(
                id=f'ba-{uuid.uuid4().hex[:8]}',
                name='分支年龄检查出错',
                description='检查分支年龄时发生错误',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'检查失败: {str(e)}'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.WARNING

        return check_result

    def check_all_branches(self, target_branch: str = 'develop') -> CheckResult:
        check_result = CheckResult(
            category=f'{self.CATEGORY}_all',
            display_name='全部分支年龄检查',
            status=CheckStatus.PASS,
            metadata={'target_branch': target_branch}
        )

        all_branches = self.git_utils.get_all_branches()
        rules = self.config.get_branch_age_rules()
        exclude_branches = rules.get('exclude_branches', ['main', 'master', 'develop'])
        stale_days = rules.get('stale_days', 90)

        branches_to_check = [b for b in all_branches if b not in exclude_branches]
        
        stale_branches = []
        warning_branches = []
        healthy_branches = []

        for branch in branches_to_check:
            try:
                branch_result = self.check(branch, target_branch)
                if branch_result.status == CheckStatus.FAIL:
                    stale_branches.append(branch)
                elif branch_result.status == CheckStatus.WARNING:
                    warning_branches.append(branch)
                else:
                    healthy_branches.append(branch)
            except Exception:
                continue

        check_result.metadata.update({
            'total_branches': len(branches_to_check),
            'stale_branches': stale_branches,
            'warning_branches': warning_branches,
            'healthy_branches': healthy_branches,
            'stale_count': len(stale_branches),
            'warning_count': len(warning_branches),
            'healthy_count': len(healthy_branches)
        })

        if stale_branches:
            item = CheckItem(
                id=f'ba-{uuid.uuid4().hex[:8]}',
                name=f'检测到 {len(stale_branches)} 个过期分支',
                description='部分分支已长期未合入',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=Severity.ERROR,
                message=f'有 {len(stale_branches)} 个分支超过 {stale_days} 天未合入',
                details={'branches': stale_branches},
                suggestion='请及时清理过期分支，保持仓库整洁',
                documentation_url='https://your-team-docs.com/branch-cleanup'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.FAIL

        if warning_branches and not stale_branches:
            item = CheckItem(
                id=f'ba-{uuid.uuid4().hex[:8]}',
                name=f'有 {len(warning_branches)} 个分支需要关注',
                description='部分分支年龄接近阈值',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'有 {len(warning_branches)} 个分支年龄较大，建议尽快合入',
                details={'branches': warning_branches}
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.WARNING

        if not stale_branches and not warning_branches:
            item = CheckItem(
                id=f'ba-{uuid.uuid4().hex[:8]}',
                name='全部分支状态良好',
                description='所有活跃分支的年龄都在合理范围内',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'共检查 {len(branches_to_check)} 个分支，全部状态良好'
            )
            check_result.items.append(item)

        return check_result
