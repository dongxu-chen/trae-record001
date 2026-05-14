import time
import subprocess
import re
import os
import sys
from typing import Callable, Optional, Tuple, List, Dict
from pathlib import Path


NON_RETRYABLE_ERROR_PATTERNS = [
    r"authentication",
    r"permission denied",
    r"could not read from remote repository",
    r"bad credentials",
    r"403 forbidden",
    r"repository not found",
    r"access denied",
    r"fatal: unable to access",
    r"ssl certificate problem",
    r"host key verification failed",
    r"git: 'credential' is not a git command",
    r"fatal: not a git repository",
]


class SSHKeyManager:
    def __init__(self, logger=None):
        self.logger = logger
        self._original_ssh_key = os.environ.get("GIT_SSH_COMMAND", None)

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message)
        else:
            print(message)

    def _get_ssh_key_path(self, key_name: str) -> Optional[str]:
        ssh_dir = Path.home() / ".ssh"
        possible_paths = [
            ssh_dir / key_name,
            ssh_dir / f"id_{key_name}",
            ssh_dir / f"{key_name}",
            Path(key_name) if Path(key_name).is_absolute() else None,
        ]
        
        for path in possible_paths:
            if path and path.exists():
                return str(path)
        return None

    def configure_ssh_key(
        self,
        key_path: Optional[str] = None,
        strict_host_key_checking: bool = True
    ) -> bool:
        if not key_path:
            return True

        if not Path(key_path).exists():
            self._log(f"SSH key 不存在: {key_path}", level="error")
            return False

        strict_value = "yes" if strict_host_key_checking else "no"
        ssh_command = (
            f"ssh -i \"{key_path}\" "
            f"-o StrictHostKeyChecking={strict_value} "
            f"-o UserKnownHostsFile=/dev/null"
        )
        
        os.environ["GIT_SSH_COMMAND"] = ssh_command
        self._log(f"已配置 SSH key: {key_path}")
        self._log(f"GIT_SSH_COMMAND = {ssh_command}", level="debug")
        return True

    def configure_ssh_key_by_host(
        self,
        host: str,
        keys_config: Dict[str, str],
        strict_host_key_checking: bool = True
    ) -> bool:
        if host in keys_config:
            return self.configure_ssh_key(
                keys_config[host],
                strict_host_key_checking
            )
        
        if "default" in keys_config:
            return self.configure_ssh_key(
                keys_config["default"],
                strict_host_key_checking
            )
        
        self._log(f"未找到主机 {host} 的 SSH key 配置", level="warning")
        return False

    def restore_default(self):
        if self._original_ssh_key:
            os.environ["GIT_SSH_COMMAND"] = self._original_ssh_key
        else:
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]
        self._log("已恢复默认 SSH 配置")

    def test_ssh_connection(self, host: str = "github.com") -> bool:
        try:
            result = subprocess.run(
                ["ssh", "-T", f"git@{host}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stderr.lower()
            success_phrases = ["successfully authenticated", "you've successfully authenticated"]
            
            for phrase in success_phrases:
                if phrase in output:
                    self._log(f"SSH 连接测试成功: {host}")
                    return True
            
            self._log(f"SSH 连接测试失败: {result.stderr}", level="warning")
            return False
        except subprocess.TimeoutExpired:
            self._log(f"SSH 连接超时: {host}", level="error")
            return False
        except Exception as e:
            self._log(f"SSH 连接测试出错: {e}", level="error")
            return False


class PushRetry:
    def __init__(self, max_retries: int = 3, retry_delay: int = 5, logger=None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger

    def _log(self, message: str, level: str = "info"):
        if self.logger:
            log_method = getattr(self.logger, level, self.logger.info)
            log_method(message)
        else:
            print(message)

    def _is_non_retryable_error(self, error_message: str) -> bool:
        if not error_message:
            return False
        error_lower = error_message.lower()
        for pattern in NON_RETRYABLE_ERROR_PATTERNS:
            if re.search(pattern, error_lower, re.IGNORECASE):
                return True
        return False

    def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "操作",
        is_non_retryable: Callable[[str], bool] = None
    ) -> Tuple[bool, Optional[str]]:
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                self._log(f"第 {attempt}/{self.max_retries} 次尝试执行 {operation_name}")
                result = operation()
                self._log(f"{operation_name} 执行成功")
                return True, result
            except Exception as e:
                last_error = str(e)
                self._log(f"第 {attempt} 次尝试失败: {last_error}", level="warning")
                
                is_non_retryable_check = is_non_retryable or self._is_non_retryable_error
                if is_non_retryable_check(last_error):
                    self._log(
                        f"检测到不可重试的错误，停止重试: {last_error}",
                        level="error"
                    )
                    return False, last_error
                
                if attempt < self.max_retries:
                    self._log(f"等待 {self.retry_delay} 秒后重试...", level="info")
                    time.sleep(self.retry_delay)
        
        self._log(f"{operation_name} 在 {self.max_retries} 次尝试后仍然失败: {last_error}", level="error")
        return False, last_error

    def git_push(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: str = "main"
    ) -> Tuple[bool, Optional[str]]:
        def push_operation():
            result = subprocess.run(
                ["git", "push", remote, branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout

        return self.execute_with_retry(push_operation, f"git push {remote} {branch}")


if __name__ == "__main__":
    import os
    
    retry = PushRetry(max_retries=2, retry_delay=2)
    
    def test_operation():
        print("执行测试操作...")
        return "成功"
    
    success, result = retry.execute_with_retry(test_operation, "测试操作")
    print(f"结果: {success}, {result}")
