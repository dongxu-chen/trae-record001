import os
import uuid
from typing import Dict, List
from .rule_engine import CheckItem, CheckResult, CheckStatus, Severity
from .checkers.branch_naming import BranchNamingChecker


class ConflictDetectionResult:
    def __init__(self):
        self.has_conflicts = False
        self.conflict_count = 0
        self.conflict_files = []
        self.can_merge_cleanly = False
        self.merge_hints = []
        self.suggestions = []


class AutoFix:
    def __init__(self, git_utils, config):
        self.git_utils = git_utils
        self.config = config
        self.branch_naming_checker = BranchNamingChecker(git_utils, config)

    def fix_branch_name(self, branch_name: str = None, dry_run: bool = True) -> Dict:
        if branch_name is None:
            branch_name = self.git_utils.get_current_branch()

        rules = self.config.get_auto_fix_rules()
        branch_rename_rules = rules.get('rules', {}).get('branch_rename', {})
        actual_dry_run = dry_run or branch_rename_rules.get('dry_run', True)

        check_result = self.branch_naming_checker.check(branch_name)
        
        if check_result.status == CheckStatus.PASS:
            return {
                'success': True,
                'branch_name': branch_name,
                'new_branch_name': branch_name,
                'message': 'Branch name already valid',
                'dry_run': actual_dry_run
            }

        suggested_name = self.branch_naming_checker.suggest_fix(branch_name)
        
        result = {
            'original_name': branch_name,
            'suggested_name': suggested_name,
            'dry_run': actual_dry_run
        }

        if actual_dry_run:
            result['success'] = True
            result['message'] = f'Dry run: Would rename "{branch_name}" to "{suggested_name}"'
        else:
            if self.git_utils.rename_branch(branch_name, suggested_name):
                result['success'] = True
                result['message'] = 'Renamed branch successfully'
            else:
                result['success'] = False
                result['message'] = 'Failed to rename branch'

        return result

    def fix_squash_commits(self, branch_name: str = None, num_commits: int = None, message: str = None) -> Dict:
        if branch_name is None:
            branch_name = self.git_utils.get_current_branch()

        rules = self.config.get_auto_fix_rules()
        commit_squash_rules = rules.get('rules', {}).get('commit_squash', {})
        max_commits = num_commits or commit_squash_rules.get('max_commits', 10)

        commits = self.git_utils.get_branch_commits(branch_name)
        
        if len(commits) < max_commits:
            return {
                'success': True,
                'branch_name': branch_name,
                'message': f'Only {len(commits)} commits, no squashing needed',
                'num_commits': len(commits)
            }

        success = self.git_utils.squash_commits(branch_name, max_commits, message)
        
        return {
            'success': success,
            'branch_name': branch_name,
            'num_squashed': max_commits - 1 if success else 0,
            'message': 'Commits squashed successfully' if success else 'Failed to squash commits'
        }

    def detect_conflicts(self, source_branch: str, target_branch: str) -> CheckResult:
        check_result = CheckResult(
            category='conflict_detection',
            display_name='合并冲突检测',
            status=CheckStatus.PASS,
            metadata={
                'source_branch': source_branch,
                'target_branch': target_branch
            }
        )

        rules = self.config.get_auto_fix_rules()
        conflict_rules = rules.get('rules', {}).get('conflict_detection', {})
        
        if not conflict_rules.get('enabled', True):
            item = CheckItem(
                id=f'cd-{uuid.uuid4().hex[:8]}',
                name='冲突检测已跳过',
                description='冲突检测在配置中被禁用',
                category='conflict_detection',
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='Conflict detection is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        severity = Severity(conflict_rules.get('severity', 'error'))
        auto_resolve = conflict_rules.get('auto_resolve', {})

        detection_result = self.git_utils.detect_conflicts(source_branch, target_branch)
        merge_result = self.git_utils.try_merge(source_branch, target_branch)

        check_result.metadata.update({
            'static_detection': detection_result,
            'merge_attempt': merge_result
        })

        has_conflicts = detection_result.get('has_conflicts', False) or merge_result.get('has_conflicts', False)
        conflict_files = list(set(
            detection_result.get('conflict_files', []) + 
            merge_result.get('conflict_files', [])
        ))
        conflict_count = len(conflict_files)

        if conflict_count > 0:
            check_result.status = CheckStatus.FAIL
            check_result.metadata['has_conflicts'] = True
            check_result.metadata['conflict_count'] = conflict_count
            check_result.metadata['conflict_files'] = conflict_files

            item = CheckItem(
                id=f'cd-{uuid.uuid4().hex[:8]}',
                name='检测到合并冲突',
                description='分支合并时存在冲突需要手动解决',
                category='conflict_detection',
                status=CheckStatus.FAIL,
                severity=severity,
                message=f'检测到 {conflict_count} 个文件存在冲突',
                details={
                    'conflict_files': conflict_files,
                    'source_branch': source_branch,
                    'target_branch': target_branch,
                    'common_files_changed': detection_result.get('common_files_changed', 0),
                    'can_merge_cleanly': merge_result.get('can_merge_cleanly', False)
                },
                suggestion=self._generate_conflict_suggestions(conflict_files, auto_resolve),
                documentation_url='https://your-team-docs.com/resolve-conflicts'
            )
            check_result.items.append(item)

            for file in conflict_files:
                hint = self._generate_file_conflict_hint(file, source_branch, target_branch)
                hint_item = CheckItem(
                    id=f'cd-{uuid.uuid4().hex[:8]}',
                    name=f'冲突文件: {file}',
                    description='该文件在两个分支都有修改',
                    category='conflict_detection',
                    status=CheckStatus.WARNING,
                    severity=Severity.WARNING,
                    message=hint,
                    details={'file': file},
                    suggestion=f'使用命令查看冲突: git diff {target_branch}...{source_branch} -- {file}',
                    documentation_url='https://your-team-docs.com/resolve-conflicts'
                )
                check_result.items.append(hint_item)

            if auto_resolve.get('enabled', False):
                strategies = auto_resolve.get('strategies', [])
                strategy_item = CheckItem(
                    id=f'cd-{uuid.uuid4().hex[:8]}',
                    name='自动解决策略',
                    description='可用于自动解决冲突的策略',
                    category='conflict_detection',
                    status=CheckStatus.WARNING,
                    severity=Severity.INFO,
                    message=f'可用自动解决策略: {", ".join(strategies)}',
                    details={'available_strategies': strategies},
                    suggestion=f'使用 git merge -X ours/theirs 进行自动解决，注意可能丢失数据',
                    documentation_url='https://your-team-docs.com/auto-resolve'
                )
                check_result.items.append(strategy_item)
        else:
            check_result.status = CheckStatus.PASS
            check_result.metadata['has_conflicts'] = False
            
            item = CheckItem(
                id=f'cd-{uuid.uuid4().hex[:8]}',
                name='无合并冲突',
                description='两个分支可以干净地合并',
                category='conflict_detection',
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'{source_branch} 可以干净地合并到 {target_branch}',
                details={
                    'source_files_changed': detection_result.get('source_files_changed', 0),
                    'target_files_changed': detection_result.get('target_files_changed', 0),
                    'common_files_changed': detection_result.get('common_files_changed', 0)
                }
            )
            check_result.items.append(item)

        return check_result

    def _generate_conflict_suggestions(self, conflict_files: List[str], auto_resolve: Dict) -> str:
        suggestions = [
            '请按以下步骤解决冲突:',
            '1. 切换到目标分支: git checkout <target_branch>',
            '2. 合并源分支: git merge <source_branch>',
            '3. 打开冲突文件，查找 <<<<<<< 标记',
            '4. 手动解决冲突后，git add <file>',
            '5. 完成合并: git commit'
        ]
        
        if auto_resolve.get('enabled', False):
            suggestions.append('')
            suggestions.append('⚠️  自动解决命令（可能丢失数据）:')
            if 'ours' in auto_resolve.get('strategies', []):
                suggestions.append('   - 保留目标分支: git merge -X ours <source_branch>')
            if 'theirs' in auto_resolve.get('strategies', []):
                suggestions.append('   - 保留源分支: git merge -X theirs <source_branch>')
        
        suggestions.append('')
        suggestions.append(f'冲突文件列表 ({len(conflict_files)}):')
        for f in conflict_files[:10]:
            suggestions.append(f'   - {f}')
        if len(conflict_files) > 10:
            suggestions.append(f'   ... 还有 {len(conflict_files) - 10} 个文件')
        
        return '\n'.join(suggestions)

    def _generate_file_conflict_hint(self, file_path: str, source_branch: str, target_branch: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        
        hints = {
            '.py': 'Python代码冲突，建议检查函数定义和导入语句',
            '.js': 'JavaScript代码冲突，建议检查函数和模块导出',
            '.ts': 'TypeScript代码冲突，建议检查类型定义',
            '.jsx': 'React组件冲突，建议检查组件状态和props',
            '.tsx': 'React组件冲突，建议检查组件状态和props',
            '.json': 'JSON配置冲突，建议手动合并配置项',
            '.yaml': 'YAML配置冲突，建议检查缩进和键值',
            '.yml': 'YAML配置冲突，建议检查缩进和键值',
            '.md': '文档冲突，建议对比版本内容',
            '.css': '样式冲突，建议检查CSS规则优先级',
            '.scss': '样式冲突，建议检查SCSS变量和混入',
        }
        
        base_hint = hints.get(ext, '该文件存在内容冲突，需要人工审查')
        
        return f'{file_path}: {base_hint}'

    def apply_all_fixes(self, branch_name: str = None) -> Dict:
        if branch_name is None:
            branch_name = self.git_utils.get_current_branch()

        results = {}

        results['branch_rename'] = self.fix_branch_name(branch_name)
        results['commit_squash'] = self.fix_squash_commits(branch_name)

        all_success = all(r.get('success', False) for r in results.values())

        return {
            'success': all_success,
            'branch_name': branch_name,
            'fixes': results
        }
