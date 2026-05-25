"""
基础依赖解析器
"""
from abc import ABC, abstractmethod
from typing import List
import os

from ..models import Dependency, PackageManager


class BaseParser(ABC):
    """依赖解析器抽象基类"""

    package_manager: PackageManager = PackageManager.UNKNOWN
    dependency_files: List[str] = []

    def __init__(self, project_path: str):
        self.project_path = project_path

    @abstractmethod
    def parse(self) -> List[Dependency]:
        """解析项目依赖"""
        pass

    def find_dependency_file(self) -> str:
        """查找依赖文件"""
        for dep_file in self.dependency_files:
            full_path = os.path.join(self.project_path, dep_file)
            if os.path.exists(full_path):
                return full_path
        return ""

    def is_supported(self) -> bool:
        """检查项目是否支持该包管理器"""
        return bool(self.find_dependency_file())

    @staticmethod
    def _normalize_version(version: str) -> str:
        """标准化版本号"""
        if not version:
            return "0.0.0"
        version = version.strip()
        version = version.lstrip("^~>=<!")
        version = version.split(";")[0].strip()
        version = version.split("+")[0].strip()
        return version
