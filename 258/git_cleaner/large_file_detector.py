"""大文件检测模块"""
import os
from typing import List, Dict, Tuple
from git import Repo, Commit, Blob
from .config import Config

class LargeFileDetector:
    """检测Git历史中的大文件"""
    
    def __init__(self, repo: Repo, config: Config):
        self.repo = repo
        self.config = config
        self.gitignore_patterns = self._load_gitignore()
    
    def _load_gitignore(self) -> List[str]:
        """加载.gitignore文件中的模式"""
        patterns = []
        gitignore_path = os.path.join(self.repo.working_dir, '.gitignore')
        
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        
        return patterns
    
    def _should_exclude(self, path: str) -> bool:
        """检查路径是否应该被排除"""
        if self.config.is_path_excluded(path):
            return True
        
        if self.config.respect_gitignore and self.gitignore_patterns:
            import fnmatch
            for pattern in self.gitignore_patterns:
                if pattern.endswith('/'):
                    dir_pattern = pattern.rstrip('/')
                    if path.startswith(dir_pattern) or f'/{dir_pattern}/' in f'/{path}/':
                        return True
                else:
                    if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                        return True
                    if pattern.startswith('/') and path == pattern.lstrip('/'):
                        return True
                    if path.startswith(pattern.lstrip('/')):
                        return True
        
        return False
    
    def scan(self) -> List[Dict]:
        """扫描仓库历史中的大文件"""
        large_files = []
        seen = set()
        excluded_count = 0
        
        for commit in self.repo.iter_commits():
            try:
                for blob in commit.tree.traverse():
                    if not isinstance(blob, Blob):
                        continue
                    
                    blob_id = blob.hexsha
                    if blob_id in seen:
                        continue
                    
                    seen.add(blob_id)
                    
                    if self._should_exclude(blob.path):
                        excluded_count += 1
                        continue
                    
                    if blob.size > self.config.large_file_threshold:
                        large_files.append({
                            'path': blob.path,
                            'size': blob.size,
                            'size_mb': round(blob.size / (1024 * 1024), 2),
                            'blob_id': blob_id,
                            'commit': commit.hexsha,
                            'commit_message': commit.message.strip()[:100],
                            'commit_date': commit.committed_datetime.isoformat(),
                        })
            except Exception as e:
                continue
        
        large_files.sort(key=lambda x: x['size'], reverse=True)
        if excluded_count > 0:
            import logging
            logging.info(f"已排除 {excluded_count} 个匹配排除规则的文件")
        
        return large_files
    
    def get_excluded_patterns(self) -> Dict[str, List[str]]:
        """获取所有排除模式"""
        return {
            'builtin': self.config.exclude_patterns,
            'gitignore': self.gitignore_patterns,
        }
    
    def get_large_file_extensions(self, large_files: List[Dict]) -> Dict[str, int]:
        """统计大文件的扩展名分布"""
        ext_count = {}
        for f in large_files:
            _, ext = os.path.splitext(f['path'])
            ext = ext.lower() or 'no_extension'
            ext_count[ext] = ext_count.get(ext, 0) + 1
        return dict(sorted(ext_count.items(), key=lambda x: x[1], reverse=True))
