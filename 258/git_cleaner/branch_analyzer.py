"""分支依赖分析模块"""
from typing import List, Dict, Set
from git import Repo, Head, RemoteReference
from collections import defaultdict

class BranchDependencyAnalyzer:
    """分析分支之间的依赖关系和影响范围"""
    
    def __init__(self, repo: Repo):
        self.repo = repo
    
    def get_all_branches(self) -> List[Dict]:
        """获取所有分支信息"""
        branches = []
        
        for head in self.repo.heads:
            branches.append({
                'name': head.name,
                'is_remote': False,
                'commit': head.commit.hexsha,
                'ref': head,
            })
        
        for remote in self.repo.remotes:
            for ref in remote.refs:
                if ref.remote_head == 'HEAD':
                    continue
                branches.append({
                    'name': ref.name,
                    'is_remote': True,
                    'remote_name': remote.name,
                    'commit': ref.commit.hexsha,
                    'ref': ref,
                })
        
        return branches
    
    def get_branch_ancestors(self, branch_name: str) -> Set[str]:
        """获取分支的所有祖先提交"""
        try:
            branch_ref = None
            for branch in self.repo.heads:
                if branch.name == branch_name:
                    branch_ref = branch
                    break
            
            if not branch_ref:
                for remote in self.repo.remotes:
                    for ref in remote.refs:
                        if ref.name == branch_name or ref.remote_head == branch_name:
                            branch_ref = ref
                            break
            
            if not branch_ref:
                return set()
            
            ancestors = set()
            for commit in self.repo.iter_commits(branch_ref.commit):
                ancestors.add(commit.hexsha)
            return ancestors
        except Exception:
            return set()
    
    def analyze_cleanup_impact(self, target_branches: List[str] = None) -> Dict:
        """分析重写历史的影响范围"""
        all_branches = self.get_all_branches()
        
        impact = {
            'all_branches': all_branches,
            'dependent_branches': [],
            'remote_branches': [b for b in all_branches if b['is_remote']],
            'warning': '',
        }
        
        remote_count = len(impact['remote_branches'])
        if remote_count > 0:
            impact['warning'] = (
                f"检测到 {remote_count} 个远程分支。"
                f"重写历史后需要使用 git push --force 推送所有受影响的分支。"
                f"这可能会影响其他协作者！"
            )
        
        return impact
    
    def get_merge_info(self) -> Dict:
        """获取分支合并信息"""
        merge_info = defaultdict(list)
        
        for branch in self.repo.heads:
            try:
                for other in self.repo.heads:
                    if branch.name == other.name:
                        continue
                    try:
                        base = self.repo.merge_base(branch.commit, other.commit)
                        if base and base[0].hexsha == other.commit.hexsha:
                            if branch.commit.hexsha != other.commit.hexsha:
                                merge_info[branch.name].append(other.name)
                    except Exception:
                        continue
            except Exception:
                continue
        
        return dict(merge_info)
    
    def generate_cleanup_warning(self) -> str:
        """生成清理前警告信息"""
        impact = self.analyze_cleanup_impact()
        warnings = []
        
        warnings.append("\n[bold red]⚠️  重写历史警告[/bold red]")
        warnings.append("")
        
        if impact['warning']:
            warnings.append(f"  [yellow]警告: {impact['warning']}[/yellow]")
            warnings.append("")
        
        warnings.append("  [bold]影响范围:[/bold]")
        warnings.append(f"    - 本地分支: {len([b for b in impact['all_branches'] if not b['is_remote']])}")
        warnings.append(f"    - 远程分支: {len(impact['remote_branches'])}")
        warnings.append("")
        
        warnings.append("  [bold]需要执行的后续操作:[/bold]")
        warnings.append("    1. 所有协作者需要重新克隆仓库或执行 git reset --hard")
        warnings.append("    2. 需要强制推送所有分支: git push --force --all")
        warnings.append("    3. 需要强制推送标签: git push --force --tags")
        warnings.append("")
        
        warnings.append("  [bold]受影响的远程分支:[/bold]")
        if impact['remote_branches']:
            for b in impact['remote_branches'][:10]:
                warnings.append(f"    - {b['name']}")
            if len(impact['remote_branches']) > 10:
                warnings.append(f"    ... 还有 {len(impact['remote_branches']) - 10} 个更多")
        else:
            warnings.append("    (无)")
        
        return "\n".join(warnings)
