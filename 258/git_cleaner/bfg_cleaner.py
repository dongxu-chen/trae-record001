"""BFG Repo-Cleaner 集成模块"""
import os
import subprocess
import tempfile
from typing import List, Dict, Optional
from pathlib import Path
from git import Repo

class BFGCleaner:
    """BFG Repo-Cleaner 封装"""
    
    def __init__(self, repo: Repo, bfg_jar_path: str = "bfg.jar"):
        self.repo = repo
        self.bfg_jar_path = bfg_jar_path
        self._verify_bfg()
    
    def _verify_bfg(self):
        """验证BFG是否可用"""
        if not os.path.exists(self.bfg_jar_path):
            raise FileNotFoundError(
                f"BFG JAR file not found at {self.bfg_jar_path}. "
                f"Download from https://rtyley.github.io/bfg-repo-cleaner/"
            )
    
    def run_command(self, args: List[str], dry_run: bool = False) -> Optional[str]:
        """运行BFG命令"""
        cmd = ["java", "-jar", self.bfg_jar_path] + args
        
        if dry_run:
            return f"[DRY-RUN] Would execute: {' '.join(cmd)}"
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.repo.working_dir,
                check=True
            )
            return result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"BFG execution failed: {e.stderr}")
    
    def clean_large_files(self, max_size_mb: int = 10, dry_run: bool = False) -> str:
        """清理大于指定大小的文件"""
        args = [f"--strip-blobs-bigger-than-{max_size_mb}M", self.repo.working_dir]
        return self.run_command(args, dry_run)
    
    def clean_files_by_name(self, file_patterns: List[str], dry_run: bool = False) -> str:
        """按文件名模式清理文件"""
        if not file_patterns:
            return "No patterns specified"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for pattern in file_patterns:
                f.write(pattern + '\n')
            temp_file = f.name
        
        try:
            args = ["--delete-files", temp_file, self.repo.working_dir]
            return self.run_command(args, dry_run)
        finally:
            if not dry_run:
                os.unlink(temp_file)
    
    def clean_sensitive_text(self, text_patterns: List[str], dry_run: bool = False) -> str:
        """清理敏感文本内容"""
        if not text_patterns:
            return "No patterns specified"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for pattern in text_patterns:
                f.write(pattern + '\n')
            temp_file = f.name
        
        try:
            args = ["--replace-text", temp_file, self.repo.working_dir]
            return self.run_command(args, dry_run)
        finally:
            if not dry_run:
                os.unlink(temp_file)
    
    def clean_passwords(self, dry_run: bool = False) -> str:
        """使用BFG内置密码替换功能"""
        args = ["--replace-passwords", self.repo.working_dir]
        return self.run_command(args, dry_run)
    
    def get_cleanup_report(self) -> Dict:
        """获取清理报告"""
        report_dir = os.path.join(self.repo.working_dir, "bfg-report")
        if not os.path.exists(report_dir):
            return {"error": "No BFG report found"}
        
        report_files = list(Path(report_dir).glob("*.txt"))
        reports = {}
        for rf in report_files:
            with open(rf, 'r', encoding='utf-8', errors='ignore') as f:
                reports[rf.name] = f.read()[:2000]
        
        return reports
    
    def finalize_cleanup(self, dry_run: bool = False) -> str:
        """完成清理，执行过期ref日志清理和垃圾回收"""
        if dry_run:
            return "[DRY-RUN] Would run: git reflog expire --expire=now --all && git gc --prune=now --aggressive"
        
        try:
            self.repo.git.reflog('expire', '--expire=now', '--all')
            result = self.repo.git.gc('--prune=now', '--aggressive')
            return f"Cleanup finalized successfully. {result}"
        except Exception as e:
            raise RuntimeError(f"Finalization failed: {e}")
