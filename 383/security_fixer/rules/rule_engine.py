"""安全规则引擎 - 核心调度和规则注册"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..parsers.base_parser import (
    ASTNode,
    BaseParser,
    Language,
    Severity,
    SourceSpan,
    Vulnerability,
    VulnerabilityType,
)
from ..parsers import get_parser


@dataclass
class ScanResult:
    """扫描结果"""
    file_path: str
    language: Language
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    ast_root: Optional[ASTNode] = None
    source_code: str = ""
    parse_error: Optional[str] = None

    @property
    def has_vulnerabilities(self) -> bool:
        return len(self.vulnerabilities) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "language": self.language.value,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "error": self.parse_error,
        }


class BaseRule(ABC):
    """安全规则基类"""

    rule_name: str = "base"
    description: str = ""
    vuln_type: VulnerabilityType = VulnerabilityType.SQL_INJECTION
    severity: Severity = Severity.HIGH
    supported_languages: List[Language] = []

    @abstractmethod
    def detect(self, ast_root: ASTNode, source_code: str, file_path: str) -> List[Vulnerability]:
        """检测漏洞，返回漏洞列表"""
        ...

    def supports_language(self, language: Language) -> bool:
        """检查规则是否支持指定语言"""
        return language in self.supported_languages

    def _create_vulnerability(
        self,
        message: str,
        source_span: SourceSpan,
        context: Optional[Dict[str, Any]] = None,
        suggested_fix: str = "",
        confidence: float = 0.8,
        auto_fixable: bool = True,
    ) -> Vulnerability:
        return Vulnerability(
            vuln_type=self.vuln_type,
            severity=self.severity,
            message=message,
            source_span=source_span,
            context=context or {},
            suggested_fix=suggested_fix,
            confidence=confidence,
            auto_fixable=auto_fixable,
        )


class RuleEngine:
    """安全规则引擎，管理所有规则并执行扫描"""

    def __init__(self):
        self._rules: List[BaseRule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """注册内置安全规则"""
        from .sql_injection_rule import SQLInjectionRule
        from .xss_rule import XSSRule
        from .path_traversal_rule import PathTraversalRule
        from .command_injection_rule import CommandInjectionRule

        self.register_rule(SQLInjectionRule())
        self.register_rule(XSSRule())
        self.register_rule(PathTraversalRule())
        self.register_rule(CommandInjectionRule())

    def register_rule(self, rule: BaseRule):
        """注册一个安全规则"""
        self._rules.append(rule)

    def get_rules(self) -> List[BaseRule]:
        return list(self._rules)

    def scan_file(self, file_path: str, language: Optional[Language] = None) -> ScanResult:
        """扫描单个文件"""
        file_path = str(Path(file_path).resolve())

        if language is None:
            language = self._detect_language(file_path)

        if language is None:
            return ScanResult(
                file_path=file_path,
                language=Language.PYTHON,
                parse_error=f"无法识别文件类型: {file_path}",
            )

        try:
            parser = get_parser(language)
        except ValueError as e:
            return ScanResult(
                file_path=file_path,
                language=language,
                parse_error=str(e),
            )

        try:
            source_code = parser.read_file(file_path)
            ast_root = parser.parse(source_code, file_path)
        except Exception as e:
            return ScanResult(
                file_path=file_path,
                language=language,
                parse_error=str(e),
            )

        vulnerabilities: List[Vulnerability] = []
        for rule in self._rules:
            if rule.supports_language(language):
                try:
                    vulns = rule.detect(ast_root, source_code, file_path)
                    vulnerabilities.extend(vulns)
                except Exception as e:
                    print(f"[警告] 规则 {rule.rule_name} 扫描 {file_path} 时出错: {e}")

        return ScanResult(
            file_path=file_path,
            language=language,
            vulnerabilities=vulnerabilities,
            ast_root=ast_root,
            source_code=source_code,
        )

    def scan_directory(self, directory: str, file_patterns: Optional[List[str]] = None) -> List[ScanResult]:
        """扫描目录中的所有支持文件"""
        directory = Path(directory).resolve()
        if not directory.is_dir():
            raise ValueError(f"不是有效目录: {directory}")

        if file_patterns is None:
            file_patterns = ["*.py", "*.java", "*.js", "*.jsx", "*.ts", "*.tsx"]

        results: List[ScanResult] = []
        files: List[Path] = []

        for pattern in file_patterns:
            files.extend(directory.rglob(pattern))

        files = [f for f in files if f.is_file()]
        for file_path in sorted(set(files)):
            language = self._detect_language(str(file_path))
            if language is not None:
                result = self.scan_file(str(file_path), language)
                results.append(result)

        return results

    def scan_directory_filtered(
        self,
        directory: str,
        exclude_patterns: Optional[List[str]] = None,
        file_patterns: Optional[List[str]] = None,
    ) -> List[ScanResult]:
        """扫描目录并排除指定模式的文件"""
        exclude_patterns = exclude_patterns or [
            "*/node_modules/*",
            "*/.git/*",
            "*/__pycache__/*",
            "*/venv/*",
            "*/.venv/*",
            "*/dist/*",
            "*/build/*",
            "*/test/*",
            "*/tests/*",
            "*/spec/*",
        ]

        results = self.scan_directory(directory, file_patterns)

        filtered: List[ScanResult] = []
        for result in results:
            should_exclude = False
            for pattern in exclude_patterns:
                import fnmatch
                if fnmatch.fnmatch(result.file_path, pattern):
                    should_exclude = True
                    break
            if not should_exclude:
                filtered.append(result)

        return filtered

    def _detect_language(self, file_path: str) -> Optional[Language]:
        """根据文件扩展名检测语言"""
        ext = Path(file_path).suffix.lower()
        ext_map = {
            ".py": Language.PYTHON,
            ".java": Language.JAVA,
            ".js": Language.JAVASCRIPT,
            ".jsx": Language.JAVASCRIPT,
            ".ts": Language.JAVASCRIPT,
            ".tsx": Language.JAVASCRIPT,
        }
        return ext_map.get(ext)

    def get_vulnerability_summary(self, results: List[ScanResult]) -> Dict[str, Any]:
        """生成漏洞汇总报告"""
        total_files = len(results)
        files_with_vulns = sum(1 for r in results if r.has_vulnerabilities)
        total_vulns = sum(len(r.vulnerabilities) for r in results)

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_file: List[Dict[str, Any]] = []

        for result in results:
            if result.has_vulnerabilities:
                file_entry = {
                    "file": result.file_path,
                    "count": len(result.vulnerabilities),
                    "vulnerabilities": [v.to_dict() for v in result.vulnerabilities],
                }
                by_file.append(file_entry)

            for v in result.vulnerabilities:
                by_type[v.vuln_type.value] = by_type.get(v.vuln_type.value, 0) + 1
                by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1

        return {
            "summary": {
                "total_files_scanned": total_files,
                "files_with_vulnerabilities": files_with_vulns,
                "total_vulnerabilities": total_vulns,
                "by_type": by_type,
                "by_severity": by_severity,
            },
            "details": by_file,
        }
