"""
pip 依赖解析器
"""
import os
import re
from typing import List
import configparser

from .base_parser import BaseParser
from ..models import Dependency, PackageManager


class PipParser(BaseParser):
    """Python pip 依赖解析器"""

    package_manager = PackageManager.PIP
    dependency_files = [
        "requirements.txt",
        "Pipfile",
        "pyproject.toml",
        "setup.py",
        "requirements-dev.txt",
    ]

    def parse(self) -> List[Dependency]:
        """解析 pip 项目依赖"""
        dependencies = []
        seen = set()

        dep_file = self.find_dependency_file()
        if not dep_file:
            return dependencies

        file_name = os.path.basename(dep_file)

        if file_name == "requirements.txt" or file_name.endswith(".txt"):
            dependencies.extend(self._parse_requirements_txt(dep_file))
        elif file_name == "Pipfile":
            dependencies.extend(self._parse_pipfile(dep_file))
        elif file_name == "pyproject.toml":
            dependencies.extend(self._parse_pyproject_toml(dep_file))
        elif file_name == "setup.py":
            dependencies.extend(self._parse_setup_py(dep_file))

        unique_deps = []
        for dep in dependencies:
            key = f"{dep.name.lower()}"
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps

    def _parse_requirements_txt(self, file_path: str) -> List[Dependency]:
        """解析 requirements.txt 文件"""
        dependencies = []
        pattern = re.compile(r"^([a-zA-Z0-9_\-\.]+)\s*([=><!~]+[^,\s]+)?")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue

                match = pattern.match(line)
                if match:
                    name = match.group(1).strip()
                    version = match.group(2) or "0.0.0"
                    version = self._normalize_version(version)

                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            package_manager=self.package_manager,
                            path=file_path,
                        )
                    )

        return dependencies

    def _parse_pipfile(self, file_path: str) -> List[Dependency]:
        """解析 Pipfile 文件"""
        dependencies = []
        config = configparser.ConfigParser()
        config.read(file_path)

        for section in ["packages", "dev-packages"]:
            if section in config:
                for name, version in config[section].items():
                    version = version.strip('"').strip("'")
                    version = self._normalize_version(version)
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            package_manager=self.package_manager,
                            path=file_path,
                            extras={"section": section},
                        )
                    )

        return dependencies

    def _parse_pyproject_toml(self, file_path: str) -> List[Dependency]:
        """解析 pyproject.toml 文件"""
        dependencies = []
        try:
            import tomllib
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
        except ImportError:
            try:
                import tomli as tomllib
                with open(file_path, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                return self._parse_pyproject_toml_simple(file_path)

        project = data.get("project", {})
        for dep in project.get("dependencies", []):
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)", dep)
            if match:
                name = match.group(1)
                version = match.group(2).strip()
                version = self._normalize_version(version) if version else "0.0.0"
                dependencies.append(
                    Dependency(
                        name=name,
                        version=version,
                        package_manager=self.package_manager,
                        path=file_path,
                    )
                )

        optional_deps = project.get("optional-dependencies", {})
        for group, deps in optional_deps.items():
            for dep in deps:
                match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)", dep)
                if match:
                    name = match.group(1)
                    version = match.group(2).strip()
                    version = self._normalize_version(version) if version else "0.0.0"
                    dependencies.append(
                        Dependency(
                            name=name,
                            version=version,
                            package_manager=self.package_manager,
                            path=file_path,
                            extras={"group": group},
                        )
                    )

        return dependencies

    def _parse_pyproject_toml_simple(self, file_path: str) -> List[Dependency]:
        """简单解析 pyproject.toml（无第三方库）"""
        dependencies = []
        pattern = re.compile(r'"([a-zA-Z0-9_\-\.]+)(>=|==|<=|!=|~=)?([^"]*)"')

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if "dependencies" in stripped and "=" in stripped:
                    in_deps = True
                    continue
                if in_deps:
                    if stripped.startswith("]") or stripped.startswith("[["):
                        in_deps = False
                        continue
                    match = pattern.search(stripped)
                    if match:
                        name = match.group(1)
                        version = match.group(3) if match.group(3) else "0.0.0"
                        version = self._normalize_version(version)
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version,
                                package_manager=self.package_manager,
                                path=file_path,
                            )
                        )

        return dependencies

    def _parse_setup_py(self, file_path: str) -> List[Dependency]:
        """解析 setup.py 文件"""
        dependencies = []
        pattern = re.compile(r"install_requires\s*=\s*\[([^\]]+)\]", re.DOTALL)

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            match = pattern.search(content)
            if match:
                deps_content = match.group(1)
                dep_pattern = re.compile(r"'([^']+)'|\"([^\"]+)\"")
                for dep_match in dep_pattern.finditer(deps_content):
                    dep_str = dep_match.group(1) or dep_match.group(2)
                    pkg_match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)", dep_str)
                    if pkg_match:
                        name = pkg_match.group(1)
                        version = pkg_match.group(2).strip()
                        version = self._normalize_version(version) if version else "0.0.0"
                        dependencies.append(
                            Dependency(
                                name=name,
                                version=version,
                                package_manager=self.package_manager,
                                path=file_path,
                            )
                        )

        return dependencies
