import os
import json
import re
from typing import List, Optional

from .base import BaseLinter, LinterResult, LinterIssue
from ..git_utils import FileChange


class PylintLinter(BaseLinter):
    name = "pylint"
    extensions = [".py"]

    def is_available(self) -> bool:
        returncode, _, _ = self._run_command(["pylint", "--version"])
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

        cmd = self._build_command(filtered_files, repo_path)

        returncode, stdout, stderr = self._run_command(cmd, cwd=repo_path)
        result.stdout = stdout
        result.stderr = stderr

        if returncode < 0:
            result.success = False
            return result

        try:
            pylint_output = json.loads(stdout) if stdout else []
        except json.JSONDecodeError:
            result.success = False
            result.stderr = stderr or "Failed to parse Pylint output"
            return result

        issues, score = self._parse_output(pylint_output, stderr)
        result.issues = issues
        result.score = score

        if result.error_count > 0:
            result.success = False

        return result

    def _build_command(self, files: List[FileChange], repo_path: str) -> List[str]:
        cmd = ["pylint", "--output-format=json"]

        config_file = self._get_config_file_path(repo_path)
        if config_file:
            cmd.extend(["--rcfile", config_file])

        if self.config.args:
            cmd.extend(self.config.args)

        for f in files:
            cmd.append(f.abs_path)

        return cmd

    def _parse_output(
        self, pylint_output: List[dict], stderr: str
    ) -> tuple[List[LinterIssue], Optional[float]]:
        issues = []

        for message in pylint_output:
            severity_map = {
                "error": "error",
                "fatal": "error",
                "warning": "warning",
                "convention": "warning",
                "refactor": "warning",
                "info": "info",
            }

            msg_type = message.get("type", "").lower()
            severity = severity_map.get(msg_type, "warning")

            issue = LinterIssue(
                file=message.get("path", ""),
                line=message.get("line", 0),
                column=message.get("column", 0),
                severity=severity,
                rule=message.get("symbol", message.get("message-id", "unknown")),
                message=message.get("message", ""),
                fixable=False,
            )
            issues.append(issue)

        score = None
        score_match = re.search(r"Your code has been rated at ([\d.]+)/10", stderr)
        if score_match:
            try:
                score = float(score_match.group(1))
            except (ValueError, IndexError):
                pass

        return issues, score
