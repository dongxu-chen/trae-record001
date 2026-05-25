"""
Maven 依赖解析器
"""
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

from .base_parser import BaseParser
from ..models import Dependency, PackageManager


class MavenParser(BaseParser):
    """Java Maven 依赖解析器"""

    package_manager = PackageManager.MAVEN
    dependency_files = [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ]

    def parse(self) -> List[Dependency]:
        """解析 Maven 项目依赖"""
        dependencies = []
        seen = set()

        dep_file = self.find_dependency_file()
        if not dep_file:
            return dependencies

        file_name = os.path.basename(dep_file)

        if file_name == "pom.xml":
            dependencies.extend(self._parse_pom_xml(dep_file))
        elif file_name in ["build.gradle", "build.gradle.kts"]:
            dependencies.extend(self._parse_gradle(dep_file))

        unique_deps = []
        for dep in dependencies:
            key = f"{dep.group_id}:{dep.name}".lower()
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        return unique_deps

    def _parse_pom_xml(self, file_path: str) -> List[Dependency]:
        """解析 pom.xml 文件"""
        dependencies = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            properties = self._extract_properties(root, ns)

            for dep in root.iter(f"{ns}dependency"):
                group_id_elem = dep.find(f"{ns}groupId")
                artifact_id_elem = dep.find(f"{ns}artifactId")
                version_elem = dep.find(f"{ns}version")
                scope_elem = dep.find(f"{ns}scope")

                if group_id_elem is None or artifact_id_elem is None:
                    continue

                group_id = group_id_elem.text.strip() if group_id_elem.text else ""
                artifact_id = artifact_id_elem.text.strip() if artifact_id_elem.text else ""
                version = "0.0.0"
                if version_elem is not None and version_elem.text:
                    version = version_elem.text.strip()
                    version = self._resolve_property(version, properties)

                scope = scope_elem.text.strip() if scope_elem is not None and scope_elem.text else "compile"

                if group_id and artifact_id:
                    dependencies.append(
                        Dependency(
                            name=artifact_id,
                            version=self._normalize_version(version),
                            package_manager=self.package_manager,
                            group_id=group_id,
                            path=file_path,
                            extras={"scope": scope},
                        )
                    )

            for dep in root.iter(f"{ns}plugin"):
                group_id_elem = dep.find(f"{ns}groupId")
                artifact_id_elem = dep.find(f"{ns}artifactId")
                version_elem = dep.find(f"{ns}version")

                if group_id_elem is not None and artifact_id_elem is not None:
                    group_id = group_id_elem.text.strip() if group_id_elem.text else ""
                    artifact_id = artifact_id_elem.text.strip() if artifact_id_elem.text else ""
                    version = "0.0.0"
                    if version_elem is not None and version_elem.text:
                        version = version_elem.text.strip()
                        version = self._resolve_property(version, properties)

                    if group_id and artifact_id:
                        dependencies.append(
                            Dependency(
                                name=artifact_id,
                                version=self._normalize_version(version),
                                package_manager=self.package_manager,
                                group_id=group_id,
                                path=file_path,
                                extras={"type": "plugin"},
                            )
                        )

        except Exception as e:
            pass

        return dependencies

    def _extract_properties(self, root: ET.Element, ns: str) -> Dict[str, str]:
        """提取 pom.xml 中的属性"""
        properties = {}
        props_elem = root.find(f"{ns}properties")
        if props_elem is not None:
            for prop in props_elem:
                prop_name = prop.tag.replace(ns, "")
                if prop.text:
                    properties[prop_name] = prop.text.strip()
        return properties

    def _resolve_property(self, value: str, properties: Dict[str, str]) -> str:
        """解析属性引用"""
        pattern = re.compile(r"\$\{([^}]+)\}")
        match = pattern.search(value)
        while match:
            prop_name = match.group(1)
            if prop_name in properties:
                value = value.replace(match.group(0), properties[prop_name])
            elif prop_name.startswith("project."):
                value = value.replace(match.group(0), "0.0.0")
            else:
                break
            match = pattern.search(value)
        return value

    def _parse_gradle(self, file_path: str) -> List[Dependency]:
        """解析 build.gradle 或 build.gradle.kts"""
        dependencies = []
        is_kts = file_path.endswith(".kts")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        patterns = [
            r'(?:implementation|api|compile|compileOnly|runtimeOnly|testImplementation|testCompile)\s*[\(]?\s*[\'\"]([^:\'\"]+:([^:\'\"]+):([^\'\"]+)[\'\"]',
            r'(?:implementation|api|compile|compileOnly|runtimeOnly|testImplementation|testCompile)\s+[\'\"]([^:\'\"]+):([^:\'\"]+):([^\'\"]+)[\'\"]',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                if len(match.groups()) == 3:
                    group_id = match.group(1)
                    artifact_id = match.group(2)
                    version = match.group(3)
                else:
                    group_id = match.group(1)
                    artifact_id = match.group(2)
                    version = "0.0.0"

                if group_id and artifact_id:
                    dependencies.append(
                        Dependency(
                            name=artifact_id,
                            version=self._normalize_version(version),
                            package_manager=self.package_manager,
                            group_id=group_id,
                            path=file_path,
                        )
                    )

        return dependencies
