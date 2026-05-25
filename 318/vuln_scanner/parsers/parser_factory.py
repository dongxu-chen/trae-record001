"""
解析器工厂
"""
from typing import List, Optional, Type

from .base_parser import BaseParser
from .maven_parser import MavenParser
from .npm_parser import NpmParser
from .pip_parser import PipParser
from .go_parser import GoParser
from ..models import PackageManager


class ParserFactory:
    """解析器工厂类"""

    _parsers: dict = {
        PackageManager.MAVEN: MavenParser,
        PackageManager.NPM: NpmParser,
        PackageManager.PIP: PipParser,
        PackageManager.GO: GoParser,
    }

    @classmethod
    def get_parser(cls, package_manager: PackageManager, project_path: str) -> Optional[BaseParser]:
        """根据包管理器类型获取解析器"""
        parser_class = cls._parsers.get(package_manager)
        if parser_class:
            return parser_class(project_path)
        return None

    @classmethod
    def detect_parser(cls, project_path: str) -> Optional[BaseParser]:
        """自动检测项目类型并返回合适的解析器"""
        parsers_order = [
            PackageManager.NPM,
            PackageManager.PIP,
            PackageManager.MAVEN,
            PackageManager.GO,
        ]

        for pm in parsers_order:
            parser_class = cls._parsers.get(pm)
            if parser_class:
                parser = parser_class(project_path)
                if parser.is_supported():
                    return parser

        return None

    @classmethod
    def get_all_parsers(cls, project_path: str) -> List[BaseParser]:
        """获取所有支持的解析器"""
        parsers = []
        for parser_class in cls._parsers.values():
            parser = parser_class(project_path)
            if parser.is_supported():
                parsers.append(parser)
        return parsers

    @classmethod
    def register_parser(cls, package_manager: PackageManager, parser_class: Type[BaseParser]) -> None:
        """注册自定义解析器"""
        cls._parsers[package_manager] = parser_class
