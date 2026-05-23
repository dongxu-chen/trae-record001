import os
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .base import BaseLinter, LinterResult, LinterIssue
from ..git_utils import FileChange


@dataclass
class CustomRule:
    name: str
    pattern: str
    message: str
    severity: str = "warning"
    extensions: List[str] = None
    exclude_patterns: List[str] = None
    case_sensitive: bool = True
    fixable: bool = False

    def __post_init__(self):
        if self.extensions is None:
            self.extensions = []
        if self.exclude_patterns is None:
            self.exclude_patterns = []

        flags = 0
        if not self.case_sensitive:
            flags |= re.IGNORECASE
        self._regex = re.compile(self.pattern, flags)

    def matches_file(self, file_path: str) -> bool:
        if self.extensions:
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in [e.lower() for e in self.extensions]:
                return False

        for pattern in self.exclude_patterns:
            if re.search(pattern, file_path):
                return False

        return True

    def check_content(self, content: str) -> List[tuple]:
        matches = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for match in self._regex.finditer(line):
                matches.append((line_num, match.start() + 1, match.group()))

        return matches


class CustomRuleLinter(BaseLinter):
    name = "custom"
    extensions = []

    def __init__(self, config, rules_config: Optional[List[Dict[str, Any]]] = None):
        super().__init__(config)
        self.rules: List[CustomRule] = []
        if rules_config:
            self._load_rules(rules_config)

    def _load_rules(self, rules_config: List[Dict[str, Any]]):
        for rule_data in rules_config:
            try:
                rule = CustomRule(
                    name=rule_data.get("name", "unknown_rule"),
                    pattern=rule_data.get("pattern", ""),
                    message=rule_data.get("message", ""),
                    severity=rule_data.get("severity", "warning"),
                    extensions=rule_data.get("extensions", []),
                    exclude_patterns=rule_data.get("exclude_patterns", []),
                    case_sensitive=rule_data.get("case_sensitive", True),
                    fixable=rule_data.get("fixable", False),
                )
                self.rules.append(rule)
                all_exts = [e.lower() for e in rule.extensions]
                for ext in all_exts:
                    if ext not in self.extensions:
                        self.extensions.append(ext)
            except Exception as e:
                print(f"Warning: Failed to load custom rule '{rule_data.get('name', 'unknown')}': {e}")

    def is_available(self) -> bool:
        return True

    def check_files(
        self, files: List[FileChange], auto_fix: bool = False
    ) -> LinterResult:
        result = LinterResult(linter_name=self.name, success=True)
        filtered_files = self.filter_files(files)

        if not filtered_files or not self.rules:
            return result

        result.files_checked = [f.path for f in filtered_files]
        issues: List[LinterIssue] = []

        for file_change in filtered_files:
            file_issues = self._check_file(file_change)
            issues.extend(file_issues)

        result.issues = issues
        result.success = len(issues) == 0

        return result

    def _check_file(self, file_change: FileChange) -> List[LinterIssue]:
        issues: List[LinterIssue] = []

        try:
            with open(file_change.abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            issues.append(
                LinterIssue(
                    file=file_change.path,
                    line=0,
                    column=0,
                    severity="error",
                    rule="file_read_error",
                    message=f"Failed to read file: {e}",
                    fixable=False,
                )
            )
            return issues

        for rule in self.rules:
            if not rule.matches_file(file_change.path):
                continue

            matches = rule.check_content(content)
            for line_num, col_num, match_str in matches:
                issue = LinterIssue(
                    file=file_change.path,
                    line=line_num,
                    column=col_num,
                    severity=rule.severity,
                    rule=rule.name,
                    message=rule.message.format(match=match_str) if "{match}" in rule.message else rule.message,
                    fixable=rule.fixable,
                )
                issues.append(issue)

        return issues

    def filter_files(self, files: List[FileChange]) -> List[FileChange]:
        if not self.extensions:
            return files
        return super().filter_files(files)
