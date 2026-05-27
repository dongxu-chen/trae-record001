"""AST解析器包 - 支持Python、Java、JavaScript三种语言"""

from .base_parser import BaseParser, Language, Vulnerability, SourceSpan
from .python_parser import PythonParser
from .java_parser import JavaParser
from .javascript_parser import JavaScriptParser


def get_parser(language: Language) -> BaseParser:
    """根据语言类型获取对应的解析器"""
    parsers = {
        Language.PYTHON: PythonParser,
        Language.JAVA: JavaParser,
        Language.JAVASCRIPT: JavaScriptParser,
    }
    parser_class = parsers.get(language)
    if not parser_class:
        raise ValueError(f"不支持的语言: {language}")
    return parser_class()
