"""
Go 依赖解析器
"""
import os
import re
from typing import List

from .base_parser import BaseParser
from ..models import Dependency, PackageManager


class GoParser(BaseParser):
    """Go Modules 依赖解析器"""

    package_manager = PackageManager.GO
    dependency_files = [
        "go.mod",
        "go.sum",
    ]

    def parse(self) -> List[Dependency]:
        """解析 Go 项目依赖"""
        dependencies = []
        seen = set()

        go_mod = os.path.join(self.project_path, "go.mod")
        if not os.path.exists(go_mod):
            return dependencies

        with open(go_mod, "r", encoding="utf-8") as f:
            content = f.read()

        in_require = False
        for line in content.split("\n"):
            stripped = line.strip()

            if stripped.startswith("require"):
                if "(" in stripped:
                    in_require = True
                else:
                    match = re.match(r'require\s+([^\s]+)\s+([^\s]+)', stripped)
                    if match:
                        name = match.group(1)
                        version = match.group(2)
                        key = name.lower()
                        if key not in seen and "// indirect" not in stripped.lower():
                            seen.add(key)
                            dependencies.append(
                                Dependency(
                                    name=name,
                                    version=self._normalize_version(version),
                                    package_manager=self.package_manager,
                                    path=go_mod,
                                    extras={"indirect": "indirect"},
                                )
                            )
                continue

            if in_require:
                if stripped.startswith(")"):
                    in_require = False
                    continue

                if stripped and not stripped.startswith("//"):
                    indirect = "// indirect" in stripped.lower()
                    match = re.match(r'([^\s]+)\s+([^\s]+)', stripped)
                    if match:
                        name = match.group(1)
                        version = match.group(2)
                        key = name.lower()
                        if key not in seen:
                            seen.add(key)
                            dependencies.append(
                                Dependency(
                                    name=name,
                                    version=self._normalize_version(version),
                                    package_manager=self.package_manager,
                                    path=go_mod,
                                    extras={"indirect": indirect},
                                )
                            )

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("replace"):
                continue

        return dependencies

    def _parse_go_sum(self, go_sum_path: str) -> dict:
        """解析 go.sum 获取版本信息（可选）"""
        versions = {}
        if os.path.exists(go_sum_path):
            with open(go_sum_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        name = parts[0]
                        version = parts[1]
                        if "/go.mod" not in version:
                            versions[name] = version.split("/go.mod")[0] if "/go.mod" in version else version
        return versions
