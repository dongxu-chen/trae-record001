"""陈旧分支检测模块"""
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from git import Repo, Head, RemoteReference
from .config import Config

class StaleBranchDetector:
    """检测陈旧分支"""
    
    def __init__(self, repo: Repo, config: Config):
        self.repo = repo
        self.config = config
        self.cutoff_date = datetime.now(timezone.utc) - timedelta(days=config.stale_branch_days)
    
    def scan(self) -> List[Dict]:
        """扫描所有分支，找出陈旧分支"""
        stale_branches = []
        
        for branch in self.repo.heads:
            info = self._analyze_branch(branch, is_remote=False)
            if info and info['last_commit_date'] < self.cutoff_date:
                stale_branches.append(info)
        
        if self.config.include_remote_branches:
            for remote in self.repo.remotes:
                for ref in remote.refs:
                    if ref.remote_head == 'HEAD':
                        continue
                    info = self._analyze_branch(ref, is_remote=True, remote_name=remote.name)
                    if info and info['last_commit_date'] < self.cutoff_date:
                        stale_branches.append(info)
        
        stale_branches.sort(key=lambda x: x['last_commit_date'])
        return stale_branches
    
    def _analyze_branch(self, ref, is_remote: bool, remote_name: str = None) -> Dict:
        """分析分支信息"""
        try:
            commit = ref.commit
            return {
                'name': ref.name,
                'is_remote': is_remote,
                'remote_name': remote_name,
                'last_commit': commit.hexsha,
                'last_commit_message': commit.message.strip()[:100],
                'last_commit_date': commit.committed_datetime,
                'last_committer': commit.committer.name,
                'days_since_update': (datetime.now(timezone.utc) - commit.committed_datetime).days,
            }
        except Exception:
            return None
    
    def get_stale_branches_summary(self, stale_branches: List[Dict]) -> Dict:
        """生成陈旧分支汇总信息"""
        local_count = sum(1 for b in stale_branches if not b['is_remote'])
        remote_count = sum(1 for b in stale_branches if b['is_remote'])
        
        oldest = min(stale_branches, key=lambda x: x['days_since_update']) if stale_branches else None
        
        return {
            'total': len(stale_branches),
            'local': local_count,
            'remote': remote_count,
            'oldest_branch': oldest,
        }
