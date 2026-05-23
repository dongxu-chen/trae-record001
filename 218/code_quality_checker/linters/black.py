import os
import subprocess
from typing import List, Optional

from .base import BaseLinter, LinterResult, LinterIssue
from ..git_utils import FileChange


class BlackLinter(BaseLinter):
    name = "black"
    extensions = [".py", ".pyi"]

    def is_available(self) -> bool:
        returncode, _, _ = self._run_command(["black", "--version"])
        return returncode == 0

    def check_files(
        self, files: List[FileChange], auto_fix: bool = False
    ) -> LinterResult:
        result = LinterResult(linter_name=self.name, success=True)
        filtered_files = self.filter_files(files)

        if not filtered_files:
            return result

        result.files_checked = [f.path for f in filtered_files]

        repo_path = os.path.dirname(filtered_files[0].abs_path)
        while not os.path.exists(os.path.join(repo_path, ".git")) and os.path.dirname(repo_path) != repo_path:
            repo_path = os.path.dirname(repo_path)

        if auto_fix and self.config.auto_fix:
            issues = self._run_black_format(filtered_files, repo_path)
            result.issues = issues
            result.success = len(issues) == 0
        else:
            issues = self._run_black_check(filtered_files, repo_path)
            result.issues = issues
            result.success = len(issues) == 0

        return result

    def _run_black_format(
        self, files: List[FileChange], repo_path: str
    ) -> List[LinterIssue]:
        cmd = ["black", "--safe", "--quiet"]

        config_file = self._get_config_file_path(repo_path)
        if config_file:
            cmd.extend(["--config", config_file])

        if self.config.args:
            cmd.extend(self.config.args)

        for f in files:
            cmd.append(f.abs_path)

        returncode, stdout, stderr = self._run_command(cmd, cwd=repo_path)

        issues = self._parse_black_output(files, returncode, stdout, stderr, formatted=True)
        return issues

    def _run_black_check(
        self, files: List[FileChange], repo_path: str
    ) -> List[LinterIssue]:
        cmd = ["black", "--check", "--diff", "--safe"]

        config_file = self._get_config_file_path(repo_path)
        if config_file:
            cmd.extend(["--config", config_file])

        if self.config.args:
            cmd.extend(self.config.args)

        for f in files:
            cmd.append(f.abs_path)

        returncode, stdout, stderr = self._run_command(cmd, cwd=repo_path)

        issues = self._parse_black_output(files, returncode, stdout, stderr, formatted=False)
        return issues

    def _parse_black_output(
        self,
        files: List[FileChange],
        returncode: int,
        stdout: str,
        stderr: str,
        formatted: bool,
    ) -> List[LinterIssue]:
        issues: List[LinterIssue] = []

        file_path_map = {f.abs_path: f.path for f in files}

        if returncode == 0:
            return issues

        if returncode == 123:
            for line in stderr.split("\n"):
                line = line.strip()
                if line.startswith("would reformat") or line.startswith("reformat"):
                    parts = line.split()
                    if len(parts) >= 3:
                        abs_path = parts[-1]
                        rel_path = file_path_map.get(abs_path, os.path.basename(abs_path))
                        issue = LinterIssue(
                            file=rel_path,
                            line=0,
                            column=0,
                            severity="warning",
                            rule="black-format",
                            message="Code needs formatting" if not formatted else "Code was reformatted",
                            fixable=not formatted,
                        )
                        issues.append(issue)

        if returncode < 0:
            for f in files:
                issue = LinterIssue(
                    file=f.path,
                    line=0,
                    column=0,
                    severity="error",
                    rule="black-error",
                    message=f"Black failed: {stderr}",
                    fixable=False,
                )
                issues.append(issue)

        return issues
