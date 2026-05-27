"""自动修复基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..parsers.base_parser import Language, Vulnerability, VulnerabilityType


@dataclass
class FixAction:
    """单个修复操作"""
    action_type: str
    description: str
    old_text: str
    new_text: str
    line: int = 0
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_type,
            "description": self.description,
            "old": self.old_text[:100],
            "new": self.new_text[:100],
            "line": self.line,
            "confidence": self.confidence,
        }


@dataclass
class FixResult:
    """修复结果"""
    file_path: str
    language: Language
    original_source: str
    fixed_source: str
    actions: List[FixAction] = field(default_factory=list)
    vulnerabilities_fixed: List[Vulnerability] = field(default_factory=list)
    vulnerabilities_skipped: List[Vulnerability] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def is_changed(self) -> bool:
        return self.original_source != self.fixed_source

    @property
    def success_count(self) -> int:
        return len(self.vulnerabilities_fixed)

    @property
    def skipped_count(self) -> int:
        return len(self.vulnerabilities_skipped)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "language": self.language.value,
            "changed": self.is_changed,
            "fixed_count": self.success_count,
            "skipped_count": self.skipped_count,
            "actions": [a.to_dict() for a in self.actions],
            "error": self.error,
        }


class BaseFixer(ABC):
    """修复器基类"""

    vuln_type: VulnerabilityType = VulnerabilityType.SQL_INJECTION
    supported_languages: List[Language] = []

    @abstractmethod
    def fix(
        self,
        source_code: str,
        vulnerabilities: List[Vulnerability],
        language: Language,
    ) -> FixResult:
        """对源代码应用修复"""
        ...

    def supports_language(self, language: Language) -> bool:
        return language in self.supported_languages

    def _apply_line_replacements(
        self, source_code: str, replacements: List[FixAction]
    ) -> str:
        """应用行级别的替换"""
        lines = source_code.splitlines(keepends=True)

        for action in sorted(replacements, key=lambda a: a.line, reverse=True):
            if action.line > 0 and action.line <= len(lines):
                old_line = lines[action.line - 1]
                if action.old_text in old_line:
                    lines[action.line - 1] = old_line.replace(
                        action.old_text, action.new_text
                    )

        return "".join(lines)

    def _apply_full_replacements(
        self, source_code: str, replacements: List[FixAction]
    ) -> str:
        """应用全文替换"""
        result = source_code
        for action in replacements:
            result = result.replace(action.old_text, action.new_text)
        return result

    def _indent_of(self, line: str) -> str:
        """获取行的缩进"""
        return line[:len(line) - len(line.lstrip())]

    def _create_fix_action(
        self,
        action_type: str,
        description: str,
        old_text: str,
        new_text: str,
        line: int = 0,
        confidence: float = 0.8,
    ) -> FixAction:
        return FixAction(
            action_type=action_type,
            description=description,
            old_text=old_text,
            new_text=new_text,
            line=line,
            confidence=confidence,
        )
