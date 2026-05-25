"""
npm 依赖解析器
"""
import os
import json
import re
from typing import List, Dict, Any

from .base_parser import BaseParser
from ..models import Dependency, PackageManager


class NpmParser(BaseParser):
    """npm/yarn/pnpm 依赖解析器"""

    package_manager = PackageManager.NPM
    dependency_files = [
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    ]

    def parse(self) -> List[Dependency]:
        """解析 npm 项目依赖"""
        dependencies = []
        seen = set()

        package_json = os.path.join(self.project_path, "package.json")
        if not os.path.exists(package_json):
            return dependencies

        with open(package_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
            deps = data.get(dep_type, {})
            if isinstance(deps, dict):
                for name, version in deps.items():
                    if isinstance(version, str):
                        normalized_version = self._normalize_version(version)
                        key = f"{name.lower()}"
                        if key not in seen:
                            seen.add(key)
                            dependencies.append(
                                Dependency(
                                    name=name,
                                    version=normalized_version,
                                    package_manager=self.package_manager,
                                    path=package_json,
                                    extras={"dep_type": dep_type},
                                )
                            )

        lock_file = self._find_lock_file()
        if lock_file:
            lock_versions = self._parse_lock_file(lock_file)
            for dep in dependencies:
                if dep.name in lock_versions:
                    dep.version = lock_versions[dep.name]

        return dependencies

    def _find_lock_file(self) -> str:
        """查找 lock 文件"""
        for lock_file in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]:
            full_path = os.path.join(self.project_path, lock_file)
            if os.path.exists(full_path):
                return full_path
        return ""

    def _parse_lock_file(self, lock_file: str) -> Dict[str, str]:
        """解析 lock 文件获取精确版本"""
        versions = {}
        file_name = os.path.basename(lock_file)

        try:
            if file_name == "package-lock.json":
                with open(lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    packages = data.get("packages", {})
                    for pkg_path, pkg_info in packages.items():
                        if pkg_path and "node_modules/" in pkg_path:
                            name = pkg_path.split("node_modules/")[-1]
                            version = pkg_info.get("version", "")
                            if version:
                                versions[name] = version
                        elif pkg_path == "":
                            continue
            elif file_name == "yarn.lock":
                versions = self._parse_yarn_lock(lock_file)
            elif file_name == "pnpm-lock.yaml":
                versions = self._parse_pnpm_lock(lock_file)
        except Exception:
            pass

        return versions

    def _parse_yarn_lock(self, lock_file: str) -> Dict[str, str]:
        """解析 yarn.lock"""
        versions = {}
        with open(lock_file, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.split(r"\n(?=\S)", content)
        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue

            header = lines[0].strip()
            pkg_match = re.match(r'"?([^"@]+)(?:@[^"]*)"?', header)
            if pkg_match:
                name = pkg_match.group(1)
                for line in lines[1:]:
                    ver_match = re.match(r'\s*version\s+"([^"]+)"', line)
                    if ver_match:
                        versions[name] = ver_match.group(1)
                        break

        return versions

    def _parse_pnpm_lock(self, lock_file: str) -> Dict[str, str]:
        """解析 pnpm-lock.yaml"""
        versions = {}
        with open(lock_file, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(r'(/[^/]+?/[^/]+?):\n\s+resolution:.*?version:\s*([^\s]+)', re.DOTALL)
        for match in pattern.finditer(content):
            pkg_path = match.group(1)
            version = match.group(2).strip("'\"")
            parts = pkg_path.strip("/").split("/")
            if len(parts) >= 2:
                if parts[0].startswith("@"):
                    name = f"{parts[0]}/{parts[1]}"
                else:
                    name = parts[0]
                versions[name] = version

        return versions
