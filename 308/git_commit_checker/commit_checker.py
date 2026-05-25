import re
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field


@dataclass
class ParsedCommit:
    types: List[str]
    scopes: List[str]
    subject: str
    body: Optional[str]
    footer: Optional[str]
    breaking: bool
    raw_message: str
    trailers: Dict[str, str] = field(default_factory=dict)


@dataclass
class CommitFormatResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    parsed: Optional[ParsedCommit] = None


class CommitMessageParser:
    HEADER_PATTERN = re.compile(
        r"^(?P<types>[a-zA-Z]+(?:[,/][a-zA-Z]+)*)"
        r"(?:\((?P<scopes>[^)]+)\))?"
        r"(?P<breaking>!)?"
        r":\s*(?P<subject>.+)$"
    )

    MULTILINE_HEADER_PATTERN = re.compile(
        r"^\s*(?P<types>[a-zA-Z]+(?:[,/][a-zA-Z]+)*)"
        r"(?:\((?P<scopes>[^)]+)\))?"
        r"(?P<breaking>!)?"
        r":\s*(?P<subject>.+?)\s*$",
        re.MULTILINE
    )

    TRAILER_PATTERN = re.compile(
        r"^(?P<key>[A-Za-z-]+):\s*(?P<value>.+)$",
        re.MULTILINE
    )

    BREAKING_CHANGE_PATTERN = re.compile(
        r"BREAKING[ -]CHANGE:\s*(.+)$",
        re.MULTILINE | re.IGNORECASE
    )

    TYPE_SEPARATORS = re.compile(r"[,/]")
    SCOPE_SEPARATORS = re.compile(r"[,/]")

    @classmethod
    def parse(cls, message: str) -> Optional[ParsedCommit]:
        if not message or not message.strip():
            return None

        lines = message.split("\n")
        header_line = cls._find_header_line(lines)

        if not header_line:
            return None

        header_match = cls.HEADER_PATTERN.match(header_line)
        if not header_match:
            return None

        types_str = header_match.group("types")
        scopes_str = header_match.group("scopes")
        breaking = header_match.group("breaking") is not None
        subject = header_match.group("subject").strip()

        types = cls._parse_types(types_str)
        scopes = cls._parse_scopes(scopes_str) if scopes_str else []

        body, footer, trailers = cls._parse_body_and_footer(message, header_line)

        if cls.BREAKING_CHANGE_PATTERN.search(message):
            breaking = True

        return ParsedCommit(
            types=types,
            scopes=scopes,
            subject=subject,
            body=body,
            footer=footer,
            breaking=breaking,
            raw_message=message,
            trailers=trailers
        )

    @classmethod
    def _find_header_line(cls, lines: List[str]) -> Optional[str]:
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped
        return None

    @classmethod
    def _parse_types(cls, types_str: str) -> List[str]:
        types = cls.TYPE_SEPARATORS.split(types_str)
        return [t.strip().lower() for t in types if t.strip()]

    @classmethod
    def _parse_scopes(cls, scopes_str: str) -> List[str]:
        scopes = cls.SCOPE_SEPARATORS.split(scopes_str)
        return [s.strip() for s in scopes if s.strip()]

    @classmethod
    def _parse_body_and_footer(
        cls, message: str, header_line: str
    ) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
        message_without_header = message.replace(header_line, "", 1).lstrip("\n")

        parts = re.split(r"\n\s*\n", message_without_header, maxsplit=2)

        body = None
        footer = None
        trailers: Dict[str, str] = {}

        if len(parts) >= 1 and parts[0].strip():
            body = parts[0].strip()

        if len(parts) >= 2 and parts[1].strip():
            footer = parts[1].strip()

            for match in cls.TRAILER_PATTERN.finditer(footer):
                key = match.group("key").strip()
                value = match.group("value").strip()
                trailers[key] = value

        return body, footer, trailers


class ConventionalCommitsChecker:
    def __init__(self, config: Any):
        self.config = config
        self.enabled = config.get("conventional_commits.enabled", True)
        self.weight = config.get("conventional_commits.weight", 35)
        self.valid_types = set(config.get("conventional_commits.types", [
            "feat", "fix", "docs", "style", "refactor",
            "perf", "test", "build", "ci", "chore", "revert"
        ]))
        self.require_scope = config.get("conventional_commits.require_scope", False)
        self.allow_empty_scope = config.get("conventional_commits.allow_empty_scope", True)
        self.max_subject_length = config.get("conventional_commits.max_subject_length", 72)
        self.require_body = config.get("conventional_commits.require_body", False)
        self.require_footer = config.get("conventional_commits.require_footer", False)
        self.allow_multiple_types = config.get("conventional_commits.allow_multiple_types", True)
        self.max_types = config.get("conventional_commits.max_types", 3)
        self.allow_multiple_scopes = config.get("conventional_commits.allow_multiple_scopes", True)
        self.max_scopes = config.get("conventional_commits.max_scopes", 3)
        self.parser = CommitMessageParser()

    def check(self, commit_message: str) -> CommitFormatResult:
        if not self.enabled:
            return CommitFormatResult(
                valid=True,
                score=self.weight,
                max_score=self.weight,
                issues=[],
                details={"skipped": True}
            )

        issues: List[str] = []
        score = self.weight
        max_score = self.weight
        details: Dict[str, Any] = {}

        lines = commit_message.split("\n")
        subject_line = self.parser._find_header_line(lines) or ""

        if not subject_line:
            issues.append("提交信息为空")
            score = 0
            return CommitFormatResult(valid=False, score=0, max_score=max_score, issues=issues, details=details)

        parsed = self.parser.parse(commit_message)
        if not parsed:
            issues.append(
                "提交信息格式不符合Conventional Commits规范。"
                "正确格式: <type>[optional scope]: <description>"
            )
            score *= 0.3
            details["format_valid"] = False
            details["parsed"] = None
        else:
            details["format_valid"] = True
            details["types"] = parsed.types
            details["scopes"] = parsed.scopes
            details["breaking"] = parsed.breaking
            details["subject"] = parsed.subject
            details["body"] = parsed.body
            details["footer"] = parsed.footer
            details["trailers"] = parsed.trailers
            details["has_body"] = parsed.body is not None and bool(parsed.body.strip())
            details["has_footer"] = parsed.footer is not None and bool(parsed.footer.strip())

            type_score, type_issues = self._check_types(parsed.types)
            score = score * type_score
            issues.extend(type_issues)

            scope_score, scope_issues = self._check_scopes(parsed.scopes)
            score = score * scope_score
            issues.extend(scope_issues)

            subject_score, subject_issues = self._check_subject(parsed.subject)
            score = score * subject_score
            issues.extend(subject_issues)

            body_score, body_issues = self._check_body(parsed.body)
            score = score * body_score
            issues.extend(body_issues)

            footer_score, footer_issues = self._check_footer(parsed.footer)
            score = score * footer_score
            issues.extend(footer_issues)

            if parsed.breaking:
                score = min(score * 1.05, self.weight)

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        details["subject_length"] = len(subject_line)
        details["total_lines"] = len(lines)
        details["subject_line"] = subject_line

        return CommitFormatResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details,
            parsed=parsed
        )

    def _check_types(self, types: List[str]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if not types:
            issues.append("提交信息缺少类型（type）")
            score = 0.3
            return score, issues

        if len(types) > 1 and not self.allow_multiple_types:
            issues.append(
                f"不允许多个类型，检测到 {len(types)} 个类型: {', '.join(types)}。"
                "请使用单个类型。"
            )
            score = 0.5
        elif len(types) > self.max_types:
            issues.append(
                f"类型数量过多: {len(types)} 个，最多允许 {self.max_types} 个。"
                f"检测到的类型: {', '.join(types)}"
            )
            score *= 0.8

        invalid_types = [t for t in types if t not in self.valid_types]
        if invalid_types:
            issues.append(
                f"未知的提交类型: {', '.join(invalid_types)}。"
                f"有效的类型包括: {', '.join(sorted(self.valid_types))}"
            )
            score *= 0.5 ** len(invalid_types)

        if len(types) > 1:
            issues.append(
                f"多类型提交: {', '.join(types)}。"
                "如果改动不相关，建议拆分提交。"
            )

        return score, issues

    def _check_scopes(self, scopes: List[str]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if self.require_scope and not scopes:
            issues.append(
                "提交信息缺少scope（范围）。格式应为 type(scope1,scope2): description"
            )
            score = 0.7

        if not self.allow_empty_scope and len(scopes) == 0:
            issues.append("不允许空的scope")
            score = 0.8

        if len(scopes) > 1 and not self.allow_multiple_scopes:
            issues.append(
                f"不允许多个scope，检测到 {len(scopes)} 个: {', '.join(scopes)}"
            )
            score = 0.6
        elif len(scopes) > self.max_scopes:
            issues.append(
                f"scope数量过多: {len(scopes)} 个，最多允许 {self.max_scopes} 个"
            )
            score *= 0.85

        for scope in scopes:
            if len(scope) > 30:
                issues.append(
                    f"scope过长: '{scope}' ({len(scope)}字符)，建议不超过30字符"
                )
                score *= 0.95

        if len(scopes) > 1:
            issues.append(
                f"多scope提交: {', '.join(scopes)}。"
                "请确认这些scope属于同一个逻辑变更。"
            )
            score *= 0.95

        return score, issues

    def _check_subject(self, subject: str) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        if not subject:
            issues.append("提交信息的描述部分为空")
            score = 0.3
            return score, issues

        if len(subject) > self.max_subject_length:
            issues.append(
                f"描述过长（{len(subject)}字符），建议不超过{self.max_subject_length}字符。"
                "考虑将详细信息放入body部分"
            )
            score *= 0.8

        if subject and subject[0].isupper():
            issues.append("描述部分不建议以大写字母开头")
            score *= 0.95

        if subject and subject.endswith("."):
            issues.append("描述部分不建议以句号结尾")
            score *= 0.95

        if len(subject) < 5:
            issues.append("描述过于简短，建议提供更有意义的提交说明")
            score *= 0.85

        return score, issues

    def _check_body(self, body: Optional[str]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        has_body = body is not None and bool(body.strip())

        if self.require_body and not has_body:
            issues.append("提交信息缺少详细说明（body部分）")
            score *= 0.7
        elif has_body:
            lines = body.split("\n")
            for i, line in enumerate(lines):
                if len(line) > 100:
                    issues.append(
                        f"body第{i+1}行过长（{len(line)}字符），建议不超过100字符"
                    )
                    score *= 0.95
                    break

            if len(lines) > 20:
                issues.append(
                    f"body过长（{len(lines)}行），建议保持简洁或使用外部文档"
                )
                score *= 0.9

        return score, issues

    def _check_footer(self, footer: Optional[str]) -> Tuple[float, List[str]]:
        issues: List[str] = []
        score = 1.0

        has_footer = footer is not None and bool(footer.strip())

        if self.require_footer and not has_footer:
            issues.append("提交信息缺少页脚（footer部分）")
            score *= 0.8

        return score, issues

    def get_primary_type(self, parsed: Optional[ParsedCommit]) -> Optional[str]:
        if not parsed or not parsed.types:
            return None
        return parsed.types[0]