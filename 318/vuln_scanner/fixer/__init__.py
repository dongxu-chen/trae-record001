"""
修复建议模块
提供版本升级建议和自动修复
"""
from .version_suggester import VersionSuggester
from .dependency_updater import DependencyUpdater

__all__ = [
    "VersionSuggester",
    "DependencyUpdater",
]
