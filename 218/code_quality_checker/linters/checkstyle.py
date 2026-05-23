import os
import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import BaseLinter, LinterResult, LinterIssue
from ..git_utils import FileChange


class CheckstyleLinter(BaseLinter):
    name = "checkstyle"
    extensions = [".java"]

    def is_available(self) -> bool:
        if self.config.jar_path and os.path.exists(self.config.jar_path):
            return True
        returncode, _, _ = self._run_command(["java", "-version"])
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

        output_file = os.path.join(repo_path, ".checkstyle-result.xml")
        cmd = self._build_command(filtered_files, repo_path, output_file)

        returncode, stdout, stderr = self._run_command(cmd, cwd=repo_path)
        result.stdout = stdout
        result.stderr = stderr

        if returncode < 0:
            result.success = False
            return result

        issues = []
        if os.path.exists(output_file):
            try:
                issues = self._parse_xml_output(output_file, repo_path)
            except Exception as e:
                result.stderr = result.stderr or f"Failed to parse Checkstyle output: {e}"
            finally:
                try:
                    os.remove(output_file)
                except:
                    pass

        result.issues = issues

        if result.error_count > 0:
            result.success = False

        return result

    def _build_command(
        self, files: List[FileChange], repo_path: str, output_file: str
    ) -> List[str]:
        jar_path = self.config.jar_path or "checkstyle.jar"
        if not os.path.isabs(jar_path):
            jar_path = os.path.join(repo_path, jar_path)

        cmd = ["java", "-jar", jar_path]

        config_file = self._get_config_file_path(repo_path)
        if config_file:
            cmd.extend(["-c", config_file])
        else:
            cmd.extend(["-c", "/google_checks.xml"])

        cmd.extend(["-f", "xml", "-o", output_file])

        if self.config.args:
            cmd.extend(self.config.args)

        for f in files:
            cmd.append(f.abs_path)

        return cmd

    def _parse_xml_output(self, xml_file: str, repo_path: str) -> List[LinterIssue]:
        issues = []
        tree = ET.parse(xml_file)
        root = tree.getroot()

        severity_map = {
            "error": "error",
            "warning": "warning",
            "info": "info",
        }

        for file_elem in root.findall("file"):
            file_name = file_elem.get("name", "")
            rel_path = os.path.relpath(file_name, repo_path)

            for error_elem in file_elem.findall("error"):
                severity = error_elem.get("severity", "warning").lower()
                severity = severity_map.get(severity, "warning")

                line_str = error_elem.get("line", "0")
                column_str = error_elem.get("column", "0")

                try:
                    line = int(line_str)
                except ValueError:
                    line = 0

                try:
                    column = int(column_str)
                except ValueError:
                    column = 0

                issue = LinterIssue(
                    file=rel_path,
                    line=line,
                    column=column,
                    severity=severity,
                    rule=error_elem.get("source", "unknown"),
                    message=error_elem.get("message", ""),
                    fixable=False,
                )
                issues.append(issue)

        return issues
