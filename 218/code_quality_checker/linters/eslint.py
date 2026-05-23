import os
import json
from typing import List, Optional

from .base import BaseLinter, LinterResult, LinterIssue
from ..git_utils import FileChange


class ESLintLinter(BaseLinter):
    name = "eslint"
    extensions = [".js", ".jsx", ".ts", ".tsx", ".vue"]

    def is_available(self) -> bool:
        returncode, _, _ = self._run_command(["npx", "eslint", "--version"])
        if returncode == 0:
            return True
        returncode, _, _ = self._run_command(["eslint", "--version"])
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

        cmd = self._build_command(filtered_files, repo_path, auto_fix)

        returncode, stdout, stderr = self._run_command(cmd, cwd=repo_path)
        result.stdout = stdout
        result.stderr = stderr

        if returncode < 0:
            result.success = False
            return result

        try:
            eslint_output = json.loads(stdout) if stdout else []
        except json.JSONDecodeError:
            result.success = False
            result.stderr = stderr or "Failed to parse ESLint output"
            return result

        issues = self._parse_output(eslint_output)
        result.issues = issues

        if result.error_count > 0:
            result.success = False

        return result

    def _build_command(
        self, files: List[FileChange], repo_path: str, auto_fix: bool
    ) -> List[str]:
        cmd = ["npx", "eslint", "--format", "json"]

        if auto_fix and self.config.auto_fix:
            cmd.append("--fix")
            cmd.extend(["--fix-type", "problem"])
            cmd.extend(["--fix-type", "layout"])
            cmd.extend(["--fix-type", "suggestion"])

        config_file = self._get_config_file_path(repo_path)
        if config_file:
            cmd.extend(["--config", config_file])

        if self.config.args:
            cmd.extend(self.config.args)

        for f in files:
            cmd.append(f.abs_path)

        return cmd

    def _parse_output(self, eslint_output: List[dict]) -> List[LinterIssue]:
        issues = []

        for file_result in eslint_output:
            file_path = file_result.get("filePath", "")
            rel_path = os.path.basename(file_path)

            for message in file_result.get("messages", []):
                severity = message.get("severity", 1)
                severity_str = "error" if severity == 2 else "warning"

                issue = LinterIssue(
                    file=rel_path,
                    line=message.get("line", 0),
                    column=message.get("column", 0),
                    severity=severity_str,
                    rule=message.get("ruleId", "unknown"),
                    message=message.get("message", ""),
                    fixable=message.get("fix") is not None,
                )
                issues.append(issue)

        return issues
