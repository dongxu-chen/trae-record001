import os
import subprocess
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from ..git_utils import FileChange
from ..config import LinterConfig


@dataclass
class LinterIssue:
    file: str
    line: int
    column: int
    severity: str
    rule: str
    message: str
    fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "rule": self.rule,
            "message": self.message,
            "fixable": self.fixable,
        }


@dataclass
class LinterResult:
    linter_name: str
    success: bool
    issues: List[LinterIssue] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    score: Optional[float] = None
    files_checked: List[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity.lower() == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity.lower() == "warning")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "linter_name": self.linter_name,
            "success": self.success,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "score": self.score,
            "issues": [issue.to_dict() for issue in self.issues],
            "files_checked": self.files_checked,
        }


class BaseLinter(ABC):
    name: str = "base"
    extensions: List[str] = []

    def __init__(self, config: LinterConfig):
        self.config = config
        self.extensions = config.extensions or self.extensions

    @abstractmethod
    def check_files(
        self, files: List[FileChange], auto_fix: bool = False
    ) -> LinterResult:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    def _run_command(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> tuple[int, str, str]:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out after 300 seconds"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return -3, "", str(e)

    def _get_config_file_path(self, repo_path: str) -> Optional[str]:
        if not self.config.config_file:
            return None
        config_path = os.path.join(repo_path, self.config.config_file)
        if os.path.exists(config_path):
            return config_path
        return None

    def filter_files(self, files: List[FileChange]) -> List[FileChange]:
        return [f for f in files if f.path.lower().endswith(tuple(self.extensions))]
