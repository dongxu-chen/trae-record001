"""依赖漏洞检测与修复模块"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class VulnerableDependency:
    """有漏洞的依赖"""
    name: str
    current_version: str
    fixed_version: str
    severity: str
    vulnerability_id: str
    description: str
    language: str
    dependency_file: str


@dataclass
class DependencyFixResult:
    """依赖修复结果"""
    dependency_file: str
    fixed_count: int
    skipped_count: int
    fixed_dependencies: List[VulnerableDependency] = field(default_factory=list)
    backup_created: bool = False
    backup_path: str = ""
    error: str = ""


KNOWN_VULNERABLE_DEPENDENCIES = {
    "python": {
        "requests": {"<2.31.0": "2.31.0", "cve": "CVE-2023-32681"},
        "django": {"<3.2.19": "3.2.19", "cve": "CVE-2023-36053"},
        "flask": {"<2.2.5": "2.2.5", "cve": "CVE-2023-30861"},
        "jinja2": {"<3.1.3": "3.1.3", "cve": "CVE-2024-22195"},
        "pyyaml": {"<6.0.1": "6.0.1", "cve": "CVE-2023-43663"},
        "cryptography": {"<41.0.0": "41.0.0", "cve": "CVE-2023-23931"},
        "sqlalchemy": {"<2.0.19": "2.0.19", "cve": "CVE-2023-33950"},
        "werkzeug": {"<2.3.6": "2.3.6", "cve": "CVE-2023-25577"},
        "paramiko": {"<3.4.0": "3.4.0", "cve": "CVE-2023-48795"},
        "urllib3": {"<1.26.18": "1.26.18", "cve": "CVE-2023-45803"},
    },
    "java": {
        "log4j": {"<2.17.1": "2.17.1", "cve": "CVE-2021-44228"},
        "spring-core": {"<5.3.18": "5.3.18", "cve": "CVE-2022-22965"},
        "commons-collections": {"<3.2.2": "3.2.2", "cve": "CVE-2015-7501"},
        "struts2-core": {"<2.5.30": "2.5.30", "cve": "CVE-2023-50164"},
        "gson": {"<2.8.9": "2.8.9", "cve": "CVE-2022-25647"},
        "jackson-databind": {"<2.13.4": "2.13.4", "cve": "CVE-2022-42003"},
    },
    "javascript": {
        "lodash": {"<4.17.21": "4.17.21", "cve": "CVE-2021-23337"},
        "express": {"<4.17.3": "4.17.3", "cve": "CVE-2022-24999"},
        "axios": {"<0.21.2": "0.21.2", "cve": "CVE-2021-3749"},
        "minimist": {"<1.2.6": "1.2.6", "cve": "CVE-2021-44906"},
        "moment": {"<2.29.4": "2.29.4", "cve": "CVE-2022-31129"},
        "jsonwebtoken": {"<9.0.0": "9.0.0", "cve": "CVE-2022-23529"},
        "handlebars": {"<4.7.7": "4.7.7", "cve": "CVE-2022-0144"},
        "marked": {"<4.0.10": "4.0.10", "cve": "CVE-2022-21680"},
        "ejs": {"<3.1.7": "3.1.7", "cve": "CVE-2022-29078"},
        "shelljs": {"<0.8.5": "0.8.5", "cve": "CVE-2022-0144"},
    }
}


class DependencyChecker:
    """依赖漏洞检查器"""

    def __init__(self):
        self.vulnerable_deps_db = KNOWN_VULNERABLE_DEPENDENCIES

    def scan_directory(self, directory: str) -> List[VulnerableDependency]:
        """扫描目录下所有依赖文件"""
        dir_path = Path(directory)
        all_vulns = []

        dep_files = self._find_dependency_files(dir_path)

        for dep_file, lang in dep_files:
            vulns = self._scan_dependency_file(str(dep_file), lang)
            all_vulns.extend(vulns)

        return all_vulns

    def _find_dependency_files(self, dir_path: Path) -> List[Tuple[Path, str]]:
        """查找所有依赖文件"""
        dep_files = []

        patterns = [
            ("requirements.txt", "python"),
            ("requirements*.txt", "python"),
            ("Pipfile", "python"),
            ("pyproject.toml", "python"),
            ("setup.py", "python"),
            ("package.json", "javascript"),
            ("package-lock.json", "javascript"),
            ("yarn.lock", "javascript"),
            ("pom.xml", "java"),
            ("build.gradle", "java"),
            ("build.gradle.kts", "java"),
        ]

        for pattern, lang in patterns:
            matches = list(dir_path.rglob(pattern))
            for match in matches:
                if "node_modules" not in str(match) and ".git" not in str(match):
                    dep_files.append((match, lang))

        return dep_files

    def _scan_dependency_file(self, file_path: str, language: str) -> List[VulnerableDependency]:
        """扫描单个依赖文件"""
        vulns = []

        if language == "python":
            vulns = self._scan_python_deps(file_path)
        elif language == "javascript":
            vulns = self._scan_javascript_deps(file_path)
        elif language == "java":
            vulns = self._scan_java_deps(file_path)

        return vulns

    def _scan_python_deps(self, file_path: str) -> List[VulnerableDependency]:
        """扫描Python依赖"""
        vulns = []
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")

        python_vulns = self.vulnerable_deps_db.get("python", {})

        if path.name.startswith("requirements"):
            pattern = r'^([a-zA-Z0-9_-]+)\s*([<>=!~]+)\s*([0-9.]+.*)'
            for match in re.finditer(pattern, content, re.MULTILINE):
                pkg_name = match.group(1).lower()
                version = match.group(3).strip()

                if pkg_name in python_vulns:
                    vuln_info = python_vulns[pkg_name]
                    vuln = VulnerableDependency(
                        name=pkg_name,
                        current_version=version,
                        fixed_version=vuln_info.get(list(vuln_info.keys())[0], "latest"),
                        severity="high",
                        vulnerability_id=vuln_info.get("cve", "UNKNOWN"),
                        description=f"依赖 {pkg_name} {version} 存在已知漏洞",
                        language="python",
                        dependency_file=str(path)
                    )
                    vulns.append(vuln)

        elif path.name == "setup.py":
            install_requires = re.findall(r'install_requires\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if install_requires:
                for dep_str in re.findall(r'"([^"]+)"', install_requires[0]):
                    parts = dep_str.split(">=")
                    if len(parts) == 2:
                        pkg_name = parts[0].lower()
                        version = parts[1]
                        if pkg_name in python_vulns:
                            vuln_info = python_vulns[pkg_name]
                            vulns.append(VulnerableDependency(
                                name=pkg_name,
                                current_version=version,
                                fixed_version=vuln_info.get(list(vuln_info.keys())[0], "latest"),
                                severity="high",
                                vulnerability_id=vuln_info.get("cve", "UNKNOWN"),
                                description=f"依赖 {pkg_name} {version} 存在已知漏洞",
                                language="python",
                                dependency_file=str(path)
                            ))

        return vulns

    def _scan_javascript_deps(self, file_path: str) -> List[VulnerableDependency]:
        """扫描JavaScript依赖"""
        vulns = []
        path = Path(file_path)

        if path.name != "package.json":
            return vulns

        try:
            content = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            js_vulns = self.vulnerable_deps_db.get("javascript", {})

            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                deps = content.get(dep_type, {})
                for pkg_name, version in deps.items():
                    clean_name = pkg_name.lower()
                    clean_version = re.sub(r'[\^~>=<]', '', version)

                    if clean_name in js_vulns:
                        vuln_info = js_vulns[clean_name]
                        vulns.append(VulnerableDependency(
                            name=clean_name,
                            current_version=clean_version,
                            fixed_version=vuln_info.get(list(vuln_info.keys())[0], "latest"),
                            severity="high",
                            vulnerability_id=vuln_info.get("cve", "UNKNOWN"),
                            description=f"依赖 {clean_name} {clean_version} 存在已知漏洞",
                            language="javascript",
                            dependency_file=str(path)
                        ))
        except json.JSONDecodeError:
            pass

        return vulns

    def _scan_java_deps(self, file_path: str) -> List[VulnerableDependency]:
        """扫描Java依赖"""
        vulns = []
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        java_vulns = self.vulnerable_deps_db.get("java", {})

        if path.name == "pom.xml":
            pattern = r'<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>'
            for match in re.finditer(pattern, content):
                artifact_id = match.group(2).lower()
                version = match.group(3)

                if artifact_id in java_vulns:
                    vuln_info = java_vulns[artifact_id]
                    vulns.append(VulnerableDependency(
                        name=artifact_id,
                        current_version=version,
                        fixed_version=vuln_info.get(list(vuln_info.keys())[0], "latest"),
                        severity="critical",
                        vulnerability_id=vuln_info.get("cve", "UNKNOWN"),
                        description=f"依赖 {artifact_id} {version} 存在已知漏洞",
                        language="java",
                        dependency_file=str(path)
                    ))

        elif path.name.startswith("build.gradle"):
            pattern = r"([a-zA-Z0-9._-]+):([a-zA-Z0-9._-]+):([0-9.]+)"
            for match in re.finditer(pattern, content):
                artifact_id = match.group(2).lower()
                version = match.group(3)

                if artifact_id in java_vulns:
                    vuln_info = java_vulns[artifact_id]
                    vulns.append(VulnerableDependency(
                        name=artifact_id,
                        current_version=version,
                        fixed_version=vuln_info.get(list(vuln_info.keys())[0], "latest"),
                        severity="critical",
                        vulnerability_id=vuln_info.get("cve", "UNKNOWN"),
                        description=f"依赖 {artifact_id} {version} 存在已知漏洞",
                        language="java",
                        dependency_file=str(path)
                    ))

        return vulns


class DependencyFixer:
    """依赖漏洞修复器"""

    def __init__(self, backup: bool = True):
        self.backup = backup
        self.checker = DependencyChecker()

    def fix_vulnerable_dependencies(self, directory: str) -> Dict[str, DependencyFixResult]:
        """修复目录中所有有漏洞的依赖"""
        dir_path = Path(directory)
        dep_files = self.checker._find_dependency_files(dir_path)

        results = {}

        for dep_file, lang in dep_files:
            vulns = self.checker._scan_dependency_file(str(dep_file), lang)
            if vulns:
                result = self._fix_dependency_file(str(dep_file), vulns, lang)
                results[str(dep_file)] = result

        return results

    def _fix_dependency_file(self, file_path: str, vulns: List[VulnerableDependency], language: str) -> DependencyFixResult:
        """修复单个依赖文件"""
        path = Path(file_path)
        original_content = path.read_text(encoding="utf-8", errors="replace")
        modified_content = original_content
        fixed = []
        skipped = []

        backup_path = ""
        if self.backup:
            backup_path = str(path) + ".bak"
            Path(backup_path).write_text(original_content, encoding="utf-8")

        for vuln in vulns:
            try:
                if language == "python":
                    modified_content = self._fix_python_dep(modified_content, vuln)
                elif language == "javascript":
                    modified_content = self._fix_javascript_dep(modified_content, vuln)
                elif language == "java":
                    modified_content = self._fix_java_dep(modified_content, vuln)
                fixed.append(vuln)
            except Exception as e:
                skipped.append(vuln)

        path.write_text(modified_content, encoding="utf-8")

        return DependencyFixResult(
            dependency_file=str(path),
            fixed_count=len(fixed),
            skipped_count=len(skipped),
            fixed_dependencies=fixed,
            backup_created=self.backup,
            backup_path=backup_path
        )

    def _fix_python_dep(self, content: str, vuln: VulnerableDependency) -> str:
        """修复Python依赖"""
        old_pattern = rf'({re.escape(vuln.name)})\s*[<>=!~]+\s*{re.escape(vuln.current_version)}'
        replacement = f'{vuln.name}>={vuln.fixed_version}'
        return re.sub(old_pattern, replacement, content, flags=re.IGNORECASE)

    def _fix_javascript_dep(self, content: str, vuln: VulnerableDependency) -> str:
        """修复JavaScript依赖"""
        try:
            data = json.loads(content)
            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                if dep_type in data and vuln.name in data[dep_type]:
                    data[dep_type][vuln.name] = f"^{vuln.fixed_version}"
            return json.dumps(data, indent=2) + "\n"
        except json.JSONDecodeError:
            return content

    def _fix_java_dep(self, content: str, vuln: VulnerableDependency) -> str:
        """修复Java依赖"""
        pattern = rf'(<artifactId>{re.escape(vuln.name)}</artifactId>\s*<version>){re.escape(vuln.current_version)}(</version>)'
        replacement = rf'\1{vuln.fixed_version}\2'
        return re.sub(pattern, replacement, content, flags=re.IGNORECASE)
