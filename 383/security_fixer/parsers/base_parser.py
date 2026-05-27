"""基础解析器和通用数据结构定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Language(Enum):
    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"


class VulnerabilityType(Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    UNSAFE_DESERIALIZATION = "unsafe_deserialization"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SourceSpan:
    """源代码位置信息"""
    file_path: str
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0


@dataclass
class Vulnerability:
    """漏洞信息"""
    vuln_type: VulnerabilityType
    severity: Severity
    message: str
    source_span: SourceSpan
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: str = ""
    confidence: float = 0.8
    auto_fixable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.vuln_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.source_span.file_path,
            "line": self.source_span.start_line,
            "end_line": self.source_span.end_line,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class ASTNode:
    """统一的AST节点表示"""
    node_type: str
    source_span: SourceSpan
    children: List["ASTNode"] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


class BaseParser(ABC):
    """所有语言解析器的基类"""

    language: Language

    @abstractmethod
    def parse(self, source_code: str, file_path: str) -> ASTNode:
        """将源代码解析为统一的AST表示"""
        ...

    @abstractmethod
    def extract_imports(self, ast_root: ASTNode) -> List[str]:
        """提取所有导入语句"""
        ...

    @abstractmethod
    def find_string_concatenations(self, ast_root: ASTNode) -> List[ASTNode]:
        """查找所有字符串拼接表达式"""
        ...

    @abstractmethod
    def find_function_calls(self, ast_root: ASTNode, function_names: List[str]) -> List[ASTNode]:
        """查找指定函数的调用"""
        ...

    @abstractmethod
    def get_node_text(self, node: ASTNode, source_code: str) -> str:
        """获取节点对应的源代码文本"""
        ...

    def read_file(self, file_path: str) -> str:
        """读取文件内容"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def parse_file(self, file_path: str) -> ASTNode:
        """解析文件并返回AST"""
        source = self.read_file(file_path)
        return self.parse(source, file_path)

    def get_supported_extensions(self) -> List[str]:
        """返回支持的文件扩展名"""
        ext_map = {
            Language.PYTHON: [".py"],
            Language.JAVA: [".java"],
            Language.JAVASCRIPT: [".js", ".jsx", ".ts", ".tsx"],
        }
        return ext_map.get(self.language, [])
