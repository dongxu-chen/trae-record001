import subprocess
import uuid
from typing import Optional, Tuple, Dict
from datetime import datetime


class ConflictHandler:
    def __init__(self, repo_path: str, logger=None):
        self.repo_path = repo_path
        self.logger = logger
        self._stash_name: Optional[str] = None

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message)
        else:
            print(message)

    def _run_git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

    def has_uncommitted_changes(self) -> bool:
        result = self._run_git("status", "--porcelain")
        return bool(result.stdout.strip())

    def stash_changes(self, message: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        if not self.has_uncommitted_changes():
            self._log("没有需要暂存的变更")
            return True, None

        stash_id = f"auto-stash-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        stash_msg = message or f"临时暂存 - 冲突处理 {stash_id}"

        self._log(f"暂存本地变更: {stash_msg}")
        result = self._run_git("stash", "push", "-m", stash_msg, "-u")

        if result.returncode != 0:
            self._log(f"暂存失败: {result.stderr}", level="error")
            return False, result.stderr

        list_result = self._run_git("stash", "list", "--grep", stash_id)
        if list_result.stdout.strip():
            first_line = list_result.stdout.strip().split("\n")[0]
            self._stash_name = first_line.split(":")[0].strip()
        else:
            self._stash_name = "stash@{0}"

        self._log(f"已暂存，stash 引用: {self._stash_name}")
        return True, self._stash_name

    def stash_list(self) -> list:
        result = self._run_git("stash", "list")
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split("\n")
        return [line.strip() for line in lines if line.strip()]

    def stash_pop(self, stash_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        target_stash = stash_name or self._stash_name
        
        if not target_stash:
            self._log("没有需要恢复的暂存")
            return True, None

        self._log(f"恢复暂存: {target_stash}")
        result = self._run_git("stash", "pop", target_stash)

        if result.returncode != 0:
            self._log(f"恢复暂存时发生冲突: {result.stderr}", level="warning")
            return self._handle_pop_conflict(target_stash)

        self._log("暂存恢复成功")
        self._stash_name = None
        return True, result.stdout

    def _handle_pop_conflict(self, stash_name: str) -> Tuple[bool, Optional[str]]:
        self._log("检测到冲突，尝试自动解决...", level="warning")

        status = self._run_git("status", "--porcelain")
        conflict_files = []
        for line in status.stdout.strip().split("\n"):
            if line and (line.startswith("UU") or line.startswith("AA") or "CONFLICT" in line):
                conflict_files.append(line[3:].strip())

        if conflict_files:
            self._log(f"冲突文件: {', '.join(conflict_files)}", level="error")
            self._log("需要手动解决冲突后执行 git stash pop --continue", level="warning")
            return False, f"存在冲突文件: {', '.join(conflict_files)}"

        apply_result = self._run_git("stash", "apply", stash_name)
        if apply_result.returncode == 0:
            drop_result = self._run_git("stash", "drop", stash_name)
            if drop_result.returncode == 0:
                self._stash_name = None
                return True, "已应用暂存内容"

        return False, "无法自动解决冲突，请手动处理"

    def stash_drop(self, stash_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        target_stash = stash_name or self._stash_name
        
        if not target_stash:
            return True, None

        self._log(f"丢弃暂存: {target_stash}")
        result = self._run_git("stash", "drop", target_stash)

        if result.returncode != 0:
            self._log(f"丢弃暂存失败: {result.stderr}", level="warning")
            return False, result.stderr

        self._stash_name = None
        return True, result.stdout

    def fetch_and_pull(self, remote: str = "origin", branch: str = "main") -> Tuple[bool, Optional[str]]:
        self._log(f"拉取远程更新: {remote}/{branch}")
        
        fetch_result = self._run_git("fetch", remote, branch)
        if fetch_result.returncode != 0:
            self._log(f"fetch 失败: {fetch_result.stderr}", level="error")
            return False, fetch_result.stderr

        pull_result = self._run_git("pull", "--rebase", remote, branch)
        
        if pull_result.returncode != 0:
            self._log(f"pull 失败: {pull_result.stderr}", level="error")
            
            rebase_abort = self._run_git("rebase", "--abort")
            if rebase_abort.returncode == 0:
                self._log("已中止 rebase")
            
            return False, pull_result.stderr

        self._log("远程更新拉取成功")
        return True, pull_result.stdout

    def resolve_conflict_pipeline(
        self,
        remote: str = "origin",
        branch: str = "main"
    ) -> Dict[str, any]:
        self._log("开始冲突处理流程")
        
        result = {
            "stashed": False,
            "pulled": False,
            "popped": False,
            "error": None,
            "stash_name": None
        }

        stashed, stash_name = self.stash_changes()
        if not stashed:
            result["error"] = "暂存失败"
            return result
        
        result["stashed"] = True
        result["stash_name"] = stash_name

        pulled, _ = self.fetch_and_pull(remote, branch)
        if not pulled:
            result["error"] = "拉取远程更新失败"
            if stash_name:
                popped, _ = self.stash_pop(stash_name)
                result["popped"] = popped
            return result
        
        result["pulled"] = True

        if stash_name:
            popped, pop_error = self.stash_pop(stash_name)
            result["popped"] = popped
            if not popped:
                result["error"] = f"恢复暂存失败: {pop_error}"
                return result

        self._log("冲突处理流程完成")
        return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        handler = ConflictHandler(sys.argv[1])
        print(f"有未提交变更: {handler.has_uncommitted_changes()}")
        print(f"暂存列表: {handler.stash_list()}")
