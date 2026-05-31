import re
import uuid
from typing import Dict, List, Optional
from ..rule_engine import Checker, Severity, CheckItem, CheckResult, CheckStatus


class PRSizeChecker(Checker):
    CATEGORY = 'pr_size'
    DISPLAY_NAME = 'PR大小检查'

    def _build_rules(self):
        pass

    def check(self, source_branch: str, target_branch: str = 'develop') -> CheckResult:
        check_result = CheckResult(
            category=self.CATEGORY,
            display_name=self.DISPLAY_NAME,
            status=CheckStatus.PASS,
            metadata={
                'source_branch': source_branch,
                'target_branch': target_branch
            }
        )

        rules = self.config.get_pr_size_rules()
        if not rules.get('enabled', True):
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name='PR大小检查已跳过',
                description='PR大小检查在配置中被禁用',
                category=self.CATEGORY,
                status=CheckStatus.SKIP,
                severity=Severity.INFO,
                message='PR size check is disabled in configuration'
            )
            check_result.items.append(item)
            check_result.status = CheckStatus.SKIP
            return check_result

        diff_by_module = self.git_utils.get_diff_by_module(source_branch, target_branch)
        total_diff = diff_by_module.get('total', {})
        module_diffs = diff_by_module.get('by_module', {})

        check_result.metadata.update({
            'diff': total_diff,
            'diff_by_module': module_diffs
        })

        default_severity = Severity(rules.get('severity', 'warning'))
        max_files = rules.get('max_files', 20)
        max_additions = rules.get('max_additions', 500)
        max_deletions = rules.get('max_deletions', 500)
        warn_files = rules.get('warn_files', 10)
        warn_additions = rules.get('warn_additions', 200)
        warn_deletions = rules.get('warn_deletions', 200)

        modules = rules.get('modules', [])

        num_files = total_diff.get('num_files', 0)
        additions = total_diff.get('additions', 0)
        deletions = total_diff.get('deletions', 0)

        self._add_size_check_items(
            check_result=check_result,
            module_name='overall',
            display_name='整体',
            num_files=num_files,
            additions=additions,
            deletions=deletions,
            max_files=max_files,
            max_additions=max_additions,
            max_deletions=max_deletions,
            warn_files=warn_files,
            warn_additions=warn_additions,
            warn_deletions=warn_deletions,
            severity=default_severity
        )

        for module_config in modules:
            module_name = module_config.get('name')
            path_pattern = module_config.get('path_pattern', '')
            module_severity = Severity(module_config.get('severity', 'warning'))
            
            max_files_mod = module_config.get('max_files', max_files)
            max_additions_mod = module_config.get('max_additions', max_additions)
            max_deletions_mod = module_config.get('max_deletions', max_deletions)
            warn_files_mod = module_config.get('warn_files', warn_files)
            warn_additions_mod = module_config.get('warn_additions', warn_additions)
            warn_deletions_mod = module_config.get('warn_deletions', warn_deletions)

            matching_files = []
            for file_path in total_diff.get('files', []):
                if re.match(path_pattern, file_path):
                    matching_files.append(file_path)

            if matching_files:
                module_additions = 0
                module_deletions = 0
                module_num_files = len(matching_files)
                
                for file_path in matching_files:
                    for module_key, module_data in module_diffs.items():
                        if file_path in module_data.get('files', []):
                            for idx, f in enumerate(module_data.get('files', [])):
                                if f == file_path:
                                    pass
                    
                    module_additions += self._estimate_file_changes(file_path, source_branch, target_branch)[0]
                    module_deletions += self._estimate_file_changes(file_path, source_branch, target_branch)[1]

                self._add_size_check_items(
                    check_result=check_result,
                    module_name=module_name,
                    display_name=f'模块: {module_name}',
                    num_files=module_num_files,
                    additions=module_additions,
                    deletions=module_deletions,
                    max_files=max_files_mod,
                    max_additions=max_additions_mod,
                    max_deletions=max_deletions_mod,
                    warn_files=warn_files_mod,
                    warn_additions=warn_additions_mod,
                    warn_deletions=warn_deletions_mod,
                    severity=module_severity,
                    path_pattern=path_pattern,
                    files=matching_files
                )

        all_pass = all(
            item.status == CheckStatus.PASS 
            for item in check_result.items
        )
        if not all_pass:
            has_error = any(
                item.status == CheckStatus.FAIL and item.severity == Severity.ERROR
                for item in check_result.items
            )
            check_result.status = CheckStatus.FAIL if has_error else CheckStatus.WARNING

        return check_result

    def _add_size_check_items(
        self,
        check_result: CheckResult,
        module_name: str,
        display_name: str,
        num_files: int,
        additions: int,
        deletions: int,
        max_files: int,
        max_additions: int,
        max_deletions: int,
        warn_files: int,
        warn_additions: int,
        warn_deletions: int,
        severity: Severity,
        path_pattern: str = None,
        files: List[str] = None
    ):
        common_details = {
            'module': module_name,
            'num_files': num_files,
            'additions': additions,
            'deletions': deletions,
            'thresholds': {
                'warn': {'files': warn_files, 'additions': warn_additions, 'deletions': warn_deletions},
                'error': {'files': max_files, 'additions': max_additions, 'deletions': max_deletions}
            }
        }
        if path_pattern:
            common_details['path_pattern'] = path_pattern
        if files:
            common_details['files'] = files

        if num_files > max_files:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 文件数超限',
                description=f'{display_name}变更文件数超过最大限制',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=Severity.ERROR if severity == Severity.ERROR else Severity.ERROR,
                message=f'{display_name}变更文件数过多: {num_files} (最大: {max_files})',
                details=common_details,
                suggestion='建议拆分PR，分批提交。考虑创建多个小的PR而不是一个大PR。',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        elif num_files > warn_files:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 文件数警告',
                description=f'{display_name}变更文件数较多',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'{display_name}变更文件数较多: {num_files} (警告阈值: {warn_files})',
                details=common_details,
                suggestion='考虑是否可以拆分，或确保本次变更逻辑内聚',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        else:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 文件数',
                description=f'{display_name}变更文件数正常',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'{display_name}变更文件数: {num_files}',
                details=common_details
            )
            check_result.items.append(item)

        if additions > max_additions:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 新增行数超限',
                description=f'{display_name}新增代码行数超过最大限制',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=Severity.ERROR if severity == Severity.ERROR else Severity.ERROR,
                message=f'{display_name}新增代码行数过多: {additions} (最大: {max_additions})',
                details=common_details,
                suggestion='建议拆分PR，或删除不必要的代码',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        elif additions > warn_additions:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 新增行数警告',
                description=f'{display_name}新增代码行数较多',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'{display_name}新增代码行数较多: {additions} (警告阈值: {warn_additions})',
                details=common_details,
                suggestion='检查是否有可复用的代码，或是否包含不必要的变更',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        else:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 新增行数',
                description=f'{display_name}新增代码行数正常',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'{display_name}新增代码行数: {additions}',
                details=common_details
            )
            check_result.items.append(item)

        if deletions > max_deletions:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 删除行数超限',
                description=f'{display_name}删除代码行数超过最大限制',
                category=self.CATEGORY,
                status=CheckStatus.FAIL,
                severity=Severity.ERROR if severity == Severity.ERROR else Severity.ERROR,
                message=f'{display_name}删除代码行数过多: {deletions} (最大: {max_deletions})',
                details=common_details,
                suggestion='大量删除建议分批次提交，并在PR描述中说明原因',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        elif deletions > warn_deletions:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 删除行数警告',
                description=f'{display_name}删除代码行数较多',
                category=self.CATEGORY,
                status=CheckStatus.WARNING,
                severity=Severity.WARNING,
                message=f'{display_name}删除代码行数较多: {deletions} (警告阈值: {warn_deletions})',
                details=common_details,
                suggestion='确认删除的代码是否确实不再需要',
                documentation_url='https://your-team-docs.com/pr-size'
            )
            check_result.items.append(item)
        else:
            item = CheckItem(
                id=f'pr-{uuid.uuid4().hex[:8]}',
                name=f'{display_name} - 删除行数',
                description=f'{display_name}删除代码行数正常',
                category=self.CATEGORY,
                status=CheckStatus.PASS,
                severity=Severity.INFO,
                message=f'{display_name}删除代码行数: {deletions}',
                details=common_details
            )
            check_result.items.append(item)

    def _estimate_file_changes(self, file_path: str, source_branch: str, target_branch: str):
        try:
            base_commit = self.git_utils.repo.merge_base(source_branch, target_branch)[0]
            file_diff = self.git_utils.repo.diff(base_commit, source_branch, paths=file_path)[0]
            return (
                getattr(file_diff, 'additions', 0),
                getattr(file_diff, 'deletions', 0)
            )
        except Exception:
            return (0, 0)
