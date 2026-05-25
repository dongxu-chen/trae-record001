"""
依赖更新器
自动更新依赖文件中的版本
"""
import os
import re
from typing import List, Dict, Any, Optional
import shutil
import tempfile

from ..models import Dependency, FixSuggestion, PackageManager


class DependencyUpdater:
    """依赖文件更新器"""

    def __init__(self, project_path: str, backup: bool = True):
        self.project_path = project_path
        self.backup = backup
        self.changes_made: List[Dict[str, Any]] = []

    def update_dependency(
        self,
        suggestion: FixSuggestion,
    ) -> bool:
        """更新单个依赖版本"""
        dep = suggestion.dependency
        dep_file = dep.path or self._find_dependency_file(dep)

        if not dep_file or not os.path.exists(dep_file):
            return False

        if self.backup:
            self._backup_file(dep_file)

        success = False
        file_name = os.path.basename(dep_file)

        if file_name == "requirements.txt" or file_name.endswith(".txt"):
            success = self._update_requirements_txt(dep_file, dep, suggestion.suggested_version)
        elif file_name == "package.json":
            success = self._update_package_json(dep_file, dep, suggestion.suggested_version)
        elif file_name == "Pipfile":
            success = self._update_pipfile(dep_file, dep, suggestion.suggested_version)
        elif file_name == "pyproject.toml":
            success = self._update_pyproject_toml(dep_file, dep, suggestion.suggested_version)
        elif file_name == "pom.xml":
            success = self._update_pom_xml(dep_file, dep, suggestion.suggested_version)
        elif file_name in ["build.gradle", "build.gradle.kts"]:
            success = self._update_gradle(dep_file, dep, suggestion.suggested_version)
        elif file_name == "go.mod":
            success = self._update_go_mod(dep_file, dep, suggestion.suggested_version)
        elif file_name == "setup.py":
            success = self._update_setup_py(dep_file, dep, suggestion.suggested_version)

        if success:
            self.changes_made.append({
                "dependency": dep.full_name,
                "old_version": suggestion.current_version,
                "new_version": suggestion.suggested_version,
                "file": dep_file,
            })

        return success

    def update_dependencies(
        self,
        suggestions: List[FixSuggestion],
    ) -> List[Dict[str, Any]]:
        """批量更新依赖"""
        results = []
        for suggestion in suggestions:
            success = self.update_dependency(suggestion)
            results.append({
                "suggestion": suggestion,
                "success": success,
            })
        return results

    def _find_dependency_file(self, dependency: Dependency) -> str:
        """查找依赖文件"""
        files = {
            PackageManager.PIP: ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"],
            PackageManager.NPM: ["package.json"],
            PackageManager.MAVEN: ["pom.xml", "build.gradle", "build.gradle.kts"],
            PackageManager.GO: ["go.mod"],
        }

        for file_name in files.get(dependency.package_manager, []):
            full_path = os.path.join(self.project_path, file_name)
            if os.path.exists(full_path):
                return full_path

        return ""

    def _backup_file(self, file_path: str) -> None:
        """备份文件"""
        backup_path = f"{file_path}.bak"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)

    def _update_requirements_txt(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 requirements.txt"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            rf'(^{re.escape(dependency.name)}\s*)([=><!~]+[^,\n]*)',
            re.MULTILINE | re.IGNORECASE
        )

        new_content = pattern.sub(rf'\1=={new_version}', content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        return False

    def _update_package_json(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 package.json"""
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        updated = False
        for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
            if dep_type in data and dependency.name in data[dep_type]:
                old_version = data[dep_type][dependency.name]
                if old_version.startswith("^"):
                    data[dep_type][dependency.name] = f"^{new_version}"
                elif old_version.startswith("~"):
                    data[dep_type][dependency.name] = f"~{new_version}"
                else:
                    data[dep_type][dependency.name] = new_version
                updated = True

        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

        return updated

    def _update_pipfile(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 Pipfile"""
        import configparser

        config = configparser.ConfigParser()
        config.read(file_path)

        updated = False
        for section in ["packages", "dev-packages"]:
            if section in config and dependency.name.lower() in config[section]:
                current = config[section][dependency.name.lower()]
                if current.startswith("*"):
                    config[section][dependency.name.lower()] = f"=={new_version}"
                else:
                    config[section][dependency.name.lower()] = f"=={new_version}"
                updated = True

        if updated:
            with open(file_path, "w", encoding="utf-8") as f:
                config.write(f)

        return updated

    def _update_pyproject_toml(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 pyproject.toml"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            rf'("{re.escape(dependency.name)}")\s*=\s*"([^"]+)"',
            re.IGNORECASE
        )

        def replace(match):
            old_version = match.group(2)
            if "==" in old_version or ">=" in old_version:
                return f'{match.group(1)} = ">= {new_version}"'
            return f'{match.group(1)} = "== {new_version}"'

        new_content = pattern.sub(replace, content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        return False

    def _update_pom_xml(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 pom.xml"""
        import xml.etree.ElementTree as ET

        tree = ET.parse(file_path)
        root = tree.getroot()

        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        updated = False
        for dep in root.iter(f"{ns}dependency"):
            group_id_elem = dep.find(f"{ns}groupId")
            artifact_id_elem = dep.find(f"{ns}artifactId")
            version_elem = dep.find(f"{ns}version")

            if (
                group_id_elem is not None
                and artifact_id_elem is not None
                and version_elem is not None
                and group_id_elem.text == dependency.group_id
                and artifact_id_elem.text == dependency.name
            ):
                version_elem.text = new_version
                updated = True

        if updated:
            tree.write(file_path, encoding="utf-8", xml_declaration=True)

        return updated

    def _update_gradle(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 build.gradle"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if dependency.group_id:
            full_name = f"{dependency.group_id}:{dependency.name}"
            pattern = re.compile(
                rf'([\'"]){re.escape(full_name)}:([^\'"]+)([\'"])',
            )

            new_content = pattern.sub(rf'\1{full_name}:{new_version}\3', content)

            if new_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return True

        return False

    def _update_go_mod(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 go.mod"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            rf'(\s*)({re.escape(dependency.name)})\s+([^\s]+)',
        )

        new_content = pattern.sub(rf'\1\2 {new_version}', content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        return False

    def _update_setup_py(
        self, file_path: str, dependency: Dependency, new_version: str
    ) -> bool:
        """更新 setup.py"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = re.compile(
            rf'([\'"]){re.escape(dependency.name)}([=><!~]+[^,\'"]+)?([\'"])',
            re.IGNORECASE,
        )

        new_content = pattern.sub(rf'\1{dependency.name}=={new_version}\3', content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True

        return False

    def get_patch(self) -> str:
        """生成变更补丁"""
        return "\n".join(
            f"- {change['dependency']}: {change['old_version']} -> {change['new_version']}"
            for change in self.changes_made
        )

    def get_changes_summary(self) -> Dict[str, Any]:
        """获取变更摘要"""
        return {
            "total_changes": len(self.changes_made),
            "changes": self.changes_made,
        }
