"""Git钩子集成模块"""
import os
import stat
from typing import List, Dict, Optional
from pathlib import Path
from git import Repo

class GitHookManager:
    """管理Git钩子"""
    
    HOOK_TYPES = ['pre-commit', 'pre-push', 'post-commit']
    
    def __init__(self, repo: Repo):
        self.repo = repo
        self.hooks_dir = os.path.join(repo.git_dir, 'hooks')
    
    def _get_hook_path(self, hook_name: str) -> str:
        """获取钩子文件路径"""
        return os.path.join(self.hooks_dir, hook_name)
    
    def hook_exists(self, hook_name: str) -> bool:
        """检查钩子是否存在"""
        return os.path.exists(self._get_hook_path(hook_name))
    
    def is_our_hook(self, hook_name: str) -> bool:
        """检查钩子是否是我们创建的"""
        hook_path = self._get_hook_path(hook_name)
        if not os.path.exists(hook_path):
            return False
        
        with open(hook_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return 'GIT_CLEANER_HOOK' in content
    
    def install_pre_push_hook(self, max_size_mb: int = 10, auto_block: bool = True) -> str:
        """安装pre-push钩子，检测并阻止大文件提交"""
        hook_path = self._get_hook_path('pre-push')
        
        hook_script = f'''#!/usr/bin/env python3
# GIT_CLEANER_HOOK
# Git仓库清理工具 - pre-push钩子
# 检测并阻止大文件推送

import sys
import os
import subprocess

MAX_SIZE_MB = {max_size_mb}
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024
AUTO_BLOCK = {str(auto_block).lower()}

def get_new_files():
    """获取即将推送的新文件"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True, text=True
        )
        return [f.strip() for f in result.stdout.strip().split('\\n') if f.strip()]
    except Exception:
        return []

def check_file_sizes(files):
    """检查文件大小"""
    large_files = []
    for f in files:
        try:
            if os.path.exists(f) and os.path.isfile(f):
                size = os.path.getsize(f)
                if size > MAX_SIZE_BYTES:
                    large_files.append({{
                        'path': f,
                        'size_mb': round(size / (1024 * 1024), 2)
                    }})
        except Exception:
            continue
    return large_files

def main():
    files = get_new_files()
    large_files = check_file_sizes(files)
    
    if large_files:
        print("\\n❌ [Git Cleanup Hook] 检测到大文件:")
        for lf in large_files:
            print(f"   - {{lf['path']}} ({{lf['size_mb']}} MB)")
        
        print(f"\\n   最大允许大小: {{MAX_SIZE_MB}} MB")
        print("   建议使用 Git LFS 管理大文件，或从提交中移除")
        
        if AUTO_BLOCK:
            print("\\n   推送已被阻止！")
            print("   如需强制推送，使用: git push --no-verify")
            return 1
        else:
            print("\\n   ⚠️  警告：建议移除大文件后再推送")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
'''
        
        if os.path.exists(hook_path) and not self.is_our_hook('pre-push'):
            backup_path = hook_path + '.backup'
            os.rename(hook_path, backup_path)
        
        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(hook_script)
        
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        return hook_path
    
    def install_pre_commit_hook(self, max_size_mb: int = 10) -> str:
        """安装pre-commit钩子，在提交前检测大文件"""
        hook_path = self._get_hook_path('pre-commit')
        
        hook_script = f'''#!/usr/bin/env python3
# GIT_CLEANER_HOOK
# Git仓库清理工具 - pre-commit钩子
# 提交前检测大文件

import sys
import os
import subprocess

MAX_SIZE_MB = {max_size_mb}
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

def get_staged_files():
    """获取暂存区的文件"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=AM'],
            capture_output=True, text=True
        )
        return [f.strip() for f in result.stdout.strip().split('\\n') if f.strip()]
    except Exception:
        return []

def check_file_sizes(files):
    """检查文件大小"""
    large_files = []
    for f in files:
        try:
            if os.path.exists(f) and os.path.isfile(f):
                size = os.path.getsize(f)
                if size > MAX_SIZE_BYTES:
                    large_files.append({{
                        'path': f,
                        'size_mb': round(size / (1024 * 1024), 2)
                    }})
        except Exception:
            continue
    return large_files

def main():
    files = get_staged_files()
    large_files = check_file_sizes(files)
    
    if large_files:
        print("\\n❌ [Git Cleanup Hook] 检测到大文件:")
        for lf in large_files:
            print(f"   - {{lf['path']}} ({{lf['size_mb']}} MB)")
        
        print(f"\\n   最大允许大小: {{MAX_SIZE_MB}} MB")
        print("   请从暂存区移除大文件后再提交:")
        print("   git reset HEAD <file>")
        
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
'''
        
        if os.path.exists(hook_path) and not self.is_our_hook('pre-commit'):
            backup_path = hook_path + '.backup'
            os.rename(hook_path, backup_path)
        
        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(hook_script)
        
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        
        return hook_path
    
    def uninstall_hook(self, hook_name: str) -> bool:
        """卸载钩子"""
        hook_path = self._get_hook_path(hook_name)
        
        if not os.path.exists(hook_path):
            return False
        
        if self.is_our_hook(hook_name):
            os.remove(hook_path)
            
            backup_path = hook_path + '.backup'
            if os.path.exists(backup_path):
                os.rename(backup_path, hook_path)
            return True
        
        return False
    
    def uninstall_all_hooks(self) -> Dict[str, bool]:
        """卸载所有我们创建的钩子"""
        results = {}
        for hook_name in self.HOOK_TYPES:
            results[hook_name] = self.uninstall_hook(hook_name)
        return results
    
    def list_hooks(self) -> Dict[str, Dict]:
        """列出所有钩子状态"""
        hooks = {}
        for hook_name in self.HOOK_TYPES:
            hook_path = self._get_hook_path(hook_name)
            exists = os.path.exists(hook_path)
            hooks[hook_name] = {
                'exists': exists,
                'is_ours': self.is_our_hook(hook_name) if exists else False,
                'path': hook_path,
            }
        return hooks
