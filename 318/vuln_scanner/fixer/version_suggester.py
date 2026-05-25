"""
版本建议器
提供修复版本建议
"""
import os
import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models import Dependency, Vulnerability, FixSuggestion, PackageManager
from ..scanner.version_utils import (
    parse_version,
    compare_versions,
    version_greater,
    version_greater_or_equal,
    get_version_type,
    has_breaking_changes,
)


class VersionSuggester:
    """版本建议器"""

    REGISTRY_URLS = {
        PackageManager.PIP: "https://pypi.org/pypi/{package}/json",
        PackageManager.NPM: "https://registry.npmjs.org/{package}",
        PackageManager.MAVEN: "https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}&rows=20&wt=json",
        PackageManager.GO: "https://proxy.golang.org/{package}/@v/list",
    }

    def __init__(self, use_remote: bool = True, cache_dir: Optional[str] = None):
        self.use_remote = use_remote
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".vuln_scanner", "version_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def suggest_fix(
        self,
        dependency: Dependency,
        vulnerabilities: List[Vulnerability],
    ) -> Optional[FixSuggestion]:
        """为依赖提供修复建议"""
        if not vulnerabilities:
            return None

        current_version = dependency.version
        fixed_versions = set()

        for vuln in vulnerabilities:
            for ver in vuln.fixed_versions:
                if version_greater_or_equal(ver, current_version):
                    fixed_versions.add(ver)

        if not fixed_versions and self.use_remote:
            available_versions = self._get_available_versions(dependency)
            for ver in available_versions:
                if version_greater(ver, current_version):
                    fixed_versions.add(ver)

        if not fixed_versions:
            return None

        best_version = self._select_best_version(
            current_version,
            list(fixed_versions),
            vulnerabilities,
        )

        if not best_version:
            return None

        upgrade_type = get_version_type(current_version, best_version)
        breaking = has_breaking_changes(current_version, best_version)

        return FixSuggestion(
            dependency=dependency,
            current_version=current_version,
            suggested_version=best_version,
            vulnerabilities=vulnerabilities,
            upgrade_type=upgrade_type,
            breaking_changes=breaking,
        )

    def suggest_fixes(
        self,
        vulnerabilities: List[Vulnerability],
        dependencies: List[Dependency],
    ) -> List[FixSuggestion]:
        """批量提供修复建议"""
        dep_vulns: Dict[str, List[Vulnerability]] = {}
        dep_map: Dict[str, Dependency] = {}

        for dep in dependencies:
            dep_map[dep.full_name] = dep
            dep_vulns[dep.full_name] = []

        for vuln in vulnerabilities:
            full_name = vuln.dependency.full_name
            if full_name in dep_vulns:
                dep_vulns[full_name].append(vuln)

        suggestions = []
        for full_name, vulns in dep_vulns.items():
            if vulns:
                dep = dep_map[full_name]
                suggestion = self.suggest_fix(dep, vulns)
                if suggestion:
                    suggestions.append(suggestion)

        suggestions.sort(key=lambda s: (
            -max(v.severity.order for v in s.vulnerabilities),
            s.upgrade_type != "patch",
            s.breaking_changes,
        ))

        return suggestions

    def _select_best_version(
        self,
        current_version: str,
        available_versions: List[str],
        vulnerabilities: List[Vulnerability],
    ) -> Optional[str]:
        """选择最佳修复版本"""
        if not available_versions:
            return None

        valid_versions = [
            v for v in available_versions
            if version_greater(v, current_version)
        ]

        if not valid_versions:
            return None

        valid_versions.sort(key=lambda v: parse_version(v), reverse=True)

        patch_versions = []
        minor_versions = []
        major_versions = []

        for ver in valid_versions:
            vtype = get_version_type(current_version, ver)
            if vtype == "patch":
                patch_versions.append(ver)
            elif vtype == "minor":
                minor_versions.append(ver)
            elif vtype == "major":
                major_versions.append(ver)

        if patch_versions:
            return patch_versions[0]

        if minor_versions:
            return minor_versions[0]

        if major_versions:
            return major_versions[0]

        return valid_versions[0]

    def _get_available_versions(self, dependency: Dependency) -> List[str]:
        """获取可用版本列表"""
        cache_file = os.path.join(
            self.cache_dir,
            f"{dependency.package_manager.value}_{dependency.full_name.replace('/', '_')}.json"
        )

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if datetime.now().timestamp() - cached.get("timestamp", 0) < 86400:
                        return cached.get("versions", [])
            except Exception:
                pass

        versions = []
        try:
            if dependency.package_manager == PackageManager.PIP:
                versions = self._get_pip_versions(dependency)
            elif dependency.package_manager == PackageManager.NPM:
                versions = self._get_npm_versions(dependency)
            elif dependency.package_manager == PackageManager.MAVEN:
                versions = self._get_maven_versions(dependency)
            elif dependency.package_manager == PackageManager.GO:
                versions = self._get_go_versions(dependency)
        except Exception:
            pass

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "versions": versions,
                    "timestamp": datetime.now().timestamp(),
                }, f)
        except Exception:
            pass

        return versions

    def _get_pip_versions(self, dependency: Dependency) -> List[str]:
        """获取 PyPI 包版本"""
        url = self.REGISTRY_URLS[PackageManager.PIP].format(package=dependency.name)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        versions = list(data.get("releases", {}).keys())
        versions.sort(key=lambda v: parse_version(v), reverse=True)
        return versions

    def _get_npm_versions(self, dependency: Dependency) -> List[str]:
        """获取 npm 包版本"""
        url = self.REGISTRY_URLS[PackageManager.NPM].format(package=dependency.name)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        versions = list(data.get("versions", {}).keys())
        versions.sort(key=lambda v: parse_version(v), reverse=True)
        return versions

    def _get_maven_versions(self, dependency: Dependency) -> List[str]:
        """获取 Maven 包版本"""
        group_id = dependency.group_id or ""
        artifact_id = dependency.name
        url = self.REGISTRY_URLS[PackageManager.MAVEN].format(
            group_id=group_id, artifact_id=artifact_id
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        docs = data.get("response", {}).get("docs", [])
        versions = [doc.get("v", "") for doc in docs if doc.get("v")]
        versions.sort(key=lambda v: parse_version(v), reverse=True)
        return versions

    def _get_go_versions(self, dependency: Dependency) -> List[str]:
        """获取 Go 模块版本"""
        package = dependency.name
        url = self.REGISTRY_URLS[PackageManager.GO].format(package=package)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.strip().split("\n")
        versions = [line.strip() for line in lines if line.strip()]
        versions.sort(key=lambda v: parse_version(v), reverse=True)
        return versions


import json
