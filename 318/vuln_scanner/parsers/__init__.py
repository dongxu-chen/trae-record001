"""
依赖解析器模块
支持 Maven, npm, pip, Go 等包管理器
"""
from .base_parser import BaseParser
from .maven_parser import MavenParser
from .npm_parser import NpmParser
from .pip_parser import PipParser
from .go_parser import GoParser
from .parser_factory import ParserFactory
from .dependency_tree import (
    DependencyTree,
    DependencyTreeResolver,
    PipDependencyTreeResolver,
    NpmDependencyTreeResolver,
    MavenDependencyTreeResolver,
    GoDependencyTreeResolver,
    DependencyTreeResolverFactory,
)

__all__ = [
    "BaseParser",
    "MavenParser",
    "NpmParser",
    "PipParser",
    "GoParser",
    "ParserFactory",
    "DependencyTree",
    "DependencyTreeResolver",
    "PipDependencyTreeResolver",
    "NpmDependencyTreeResolver",
    "MavenDependencyTreeResolver",
    "GoDependencyTreeResolver",
    "DependencyTreeResolverFactory",
]
