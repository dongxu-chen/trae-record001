import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from git import Repo, GitCommandError
from git.objects.commit import Commit


class GitUtils:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.repo = Repo(self.repo_path)

    def get_current_branch(self) -> str:
        return self.repo.active_branch.name

    def get_all_branches(self) -> List[str]:
        return [branch.name for branch in self.repo.branches]

    def get_branch_commits(self, branch_name: str, since: Optional[datetime] = None) -> List[Commit]:
        try:
            if since:
                commits = list(self.repo.iter_commits(branch_name, since=since))
            else:
                commits = list(self.repo.iter_commits(branch_name))
            return commits
        except GitCommandError:
            return []

    def get_commit_stats(self, commit: Commit) -> Dict:
        return {
            'hash': commit.hexsha,
            'author': commit.author.name,
            'email': commit.author.email,
            'date': datetime.fromtimestamp(commit.committed_date),
            'message': commit.message.strip(),
            'files_changed': len(commit.stats.files),
            'additions': commit.stats.total['insertions'],
            'deletions': commit.stats.total['deletions']
        }

    def get_branch_diff(self, source_branch: str, target_branch: str) -> Dict:
        try:
            base_commit = self.repo.merge_base(source_branch, target_branch)[0]
            diff_index = self.repo.diff(base_commit, source_branch)
            
            files_changed = []
            total_additions = 0
            total_deletions = 0
            
            for diff_item in diff_index:
                if diff_item.a_blob:
                    files_changed.append(diff_item.a_blob.path)
                elif diff_item.b_blob:
                    files_changed.append(diff_item.b_blob.path)
                
                if hasattr(diff_item, 'additions'):
                    total_additions += diff_item.additions
                    total_deletions += diff_item.deletions
            
            return {
                'files': list(set(files_changed)),
                'additions': total_additions,
                'deletions': total_deletions,
                'num_files': len(set(files_changed))
            }
        except Exception as e:
            return {
                'files': [],
                'additions': 0,
                'deletions': 0,
                'num_files': 0,
                'error': str(e)
            }

    def get_commits_between(self, source_branch: str, target_branch: str) -> List[Commit]:
        try:
            return list(self.repo.iter_commits(f'{target_branch}..{source_branch}'))
        except GitCommandError:
            return []

    def get_merge_base(self, branch1: str, branch2: str) -> Optional[str]:
        try:
            base = self.repo.merge_base(branch1, branch2)
            return base[0].hexsha if base else None
        except Exception:
            return None

    def rename_branch(self, old_name: str, new_name: str) -> bool:
        try:
            self.repo.git.branch('-m', old_name, new_name)
            return True
        except GitCommandError:
            return False

    def squash_commits(self, branch_name: str, num_commits: int, message: str = None) -> bool:
        try:
            current_commit = self.repo.head.commit
            commits = list(self.repo.iter_commits(branch_name, max_count=num_commits))
            
            if len(commits) < 2:
                return False
                
            self.repo.git.reset('--soft', f'HEAD~{len(commits) - 1}')
            if message:
                self.repo.git.commit('-m', message)
            else:
                self.repo.git.commit('--no-edit')
            return True
        except GitCommandError:
            return False

    def get_commit_history(self, branch: str, days: int = 7) -> List[Dict]:
        since = datetime.now() - timedelta(days=days)
        commits = self.get_branch_commits(branch, since=since)
        return [self.get_commit_stats(c) for c in commits]

    def detect_conflicts(self, source_branch: str, target_branch: str) -> Dict:
        try:
            base_commit = self.repo.merge_base(source_branch, target_branch)[0]
            
            source_commits = list(self.repo.iter_commits(f'{base_commit}..{source_branch}'))
            target_commits = list(self.repo.iter_commits(f'{base_commit}..{target_branch}'))
            
            source_files = set()
            target_files = set()
            
            for commit in source_commits:
                for f in commit.stats.files.keys():
                    source_files.add(f)
            
            for commit in target_commits:
                for f in commit.stats.files.keys():
                    target_files.add(f)
            
            common_files = source_files.intersection(target_files)
            
            conflicts = []
            conflict_files = []
            
            for file_path in common_files:
                try:
                    source_content = self.repo.git.show(f'{source_branch}:{file_path}')
                    target_content = self.repo.git.show(f'{target_branch}:{file_path}')
                    
                    if source_content != target_content:
                        conflicts.append({
                            'file': file_path,
                            'in_source': True,
                            'in_target': True,
                            'has_different_content': True
                        })
                        conflict_files.append(file_path)
                except Exception:
                    pass

            return {
                'has_conflicts': len(conflict_files) > 0,
                'conflict_count': len(conflict_files),
                'conflict_files': conflict_files,
                'conflicts': conflicts,
                'source_files_changed': len(source_files),
                'target_files_changed': len(target_files),
                'common_files_changed': len(common_files)
            }
        except Exception as e:
            return {
                'has_conflicts': False,
                'conflict_count': 0,
                'conflict_files': [],
                'conflicts': [],
                'error': str(e)
            }

    def try_merge(self, source_branch: str, target_branch: str) -> Dict:
        try:
            original_branch = self.get_current_branch()
            
            self.repo.git.checkout(target_branch)
            
            try:
                self.repo.git.merge(source_branch, '--no-commit', '--no-ff')
                has_conflicts = False
                conflict_files = []
                
                if self.repo.is_dirty():
                    for item in self.repo.index.diff(None):
                        if item.change_type == 'U':
                            has_conflicts = True
                            conflict_files.append(item.a_path)
                
                self.repo.git.merge('--abort')
                self.repo.git.checkout(original_branch)
                
                return {
                    'success': True,
                    'has_conflicts': has_conflicts,
                    'conflict_count': len(conflict_files),
                    'conflict_files': conflict_files,
                    'can_merge_cleanly': not has_conflicts
                }
            except Exception as merge_err:
                if 'CONFLICT' in str(merge_err):
                    self.repo.git.merge('--abort', with_exceptions=False)
                self.repo.git.checkout(original_branch, with_exceptions=False)
                
                conflict_files = []
                import re
                conflicts = re.findall(r'CONFLICT \([^)]+\): (.*?)(?:\n|$)', str(merge_err))
                for c in conflicts:
                    if ':' in c:
                        conflict_files.append(c.split(':')[-1].strip())
                    else:
                        conflict_files.append(c.strip())
                
                return {
                    'success': True,
                    'has_conflicts': len(conflict_files) > 0,
                    'conflict_count': len(conflict_files),
                    'conflict_files': list(set(conflict_files)),
                    'can_merge_cleanly': len(conflict_files) == 0,
                    'error_detail': str(merge_err)
                }
        except Exception as e:
            return {
                'success': False,
                'has_conflicts': False,
                'conflict_count': 0,
                'conflict_files': [],
                'can_merge_cleanly': False,
                'error': str(e)
            }

    def get_diff_by_module(self, source_branch: str, target_branch: str) -> Dict:
        diff = self.get_branch_diff(source_branch, target_branch)
        files = diff.get('files', [])
        
        module_diffs = {}
        all_additions = 0
        all_deletions = 0
        
        for file_path in files:
            try:
                base_commit = self.repo.merge_base(source_branch, target_branch)[0]
                file_diff = self.repo.diff(base_commit, source_branch, paths=file_path)[0]
                
                additions = getattr(file_diff, 'additions', 0)
                deletions = getattr(file_diff, 'deletions', 0)
                
                all_additions += additions
                all_deletions += deletions
                
                parts = file_path.split('/')
                module = 'other'
                if len(parts) >= 2:
                    module = '/'.join(parts[:2])
                
                if module not in module_diffs:
                    module_diffs[module] = {
                        'files': [],
                        'additions': 0,
                        'deletions': 0,
                        'num_files': 0
                    }
                
                module_diffs[module]['files'].append(file_path)
                module_diffs[module]['additions'] += additions
                module_diffs[module]['deletions'] += deletions
                module_diffs[module]['num_files'] += 1
            except Exception:
                continue

        return {
            'total': {
                'files': files,
                'additions': all_additions,
                'deletions': all_deletions,
                'num_files': len(files)
            },
            'by_module': module_diffs
        }
