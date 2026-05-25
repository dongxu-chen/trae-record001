"""
升级兼容性检测模块
语义化版本对比 + 破坏性变更提示 + API 变更分析
"""
import os
import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from packaging.version import Version, InvalidVersion

from ..models import (
    Dependency,
    FixSuggestion,
    CompatibilityInfo,
    PackageManager,
)
from ..scanner.version_utils import parse_version


class CompatibilityChecker:
    """升级兼容性检测器"""

    def __init__(self, project_path: str = "", use_remote: bool = True):
        self.project_path = project_path
        self.use_remote = use_remote
        self._changelog_cache: Dict[str, Any] = {}
        self._usage_analysis_cache: Dict[str, Any] = {}

    def check_all(
        self,
        suggestions: List[FixSuggestion],
    ) -> List[FixSuggestion]:
        """检查所有修复建议的兼容性"""
        print("   ↳ Checking upgrade compatibility...")

        for suggestion in suggestions:
            try:
                compatibility = self._check_compatibility(suggestion)
                suggestion.compatibility = compatibility
                suggestion.breaking_changes = compatibility.breaking_change_risk in ["high", "medium"]
            except Exception as e:
                suggestion.compatibility = CompatibilityInfo(
                    dependency=suggestion.dependency,
                    from_version=suggestion.current_version,
                    to_version=suggestion.suggested_version,
                    is_compatible=True,
                    breaking_change_risk="unknown",
                    compatibility_score=70.0,
                    estimated_migration_effort="unknown",
                    breaking_changes=[f"Compatibility check error: {str(e)}"],
                )

        incompatible_count = sum(
            1 for s in suggestions
            if s.compatibility and s.compatibility.breaking_change_risk in ["high", "medium"]
        )
        print(f"   ↳ {incompatible_count}/{len(suggestions)} upgrades have potential breaking changes")

        return suggestions

    def _check_compatibility(
        self,
        suggestion: FixSuggestion,
    ) -> CompatibilityInfo:
        """检查单个升级的兼容性"""
        dep = suggestion.dependency
        from_ver = suggestion.current_version
        to_ver = suggestion.suggested_version

        info = CompatibilityInfo(
            dependency=dep,
            from_version=from_ver,
            to_version=to_ver,
        )

        upgrade_type = self._get_upgrade_type(from_ver, to_ver)
        suggestion.upgrade_type = upgrade_type

        base_score = 100.0

        if upgrade_type == "major":
            base_score -= 50
            risk = "high"
            effort = "high"
            info.breaking_changes.append(
                "⚠️  MAJOR version upgrade! This likely contains breaking API changes."
            )
        elif upgrade_type == "minor":
            base_score -= 20
            risk = "medium"
            effort = "medium"
            info.breaking_changes.append(
                "⚠️  MINOR version upgrade. New features added, check for deprecated APIs."
            )
        else:
            risk = "low"
            effort = "low"
            info.breaking_changes.append(
                "✅ PATCH version upgrade. Only bug fixes, unlikely to break anything."
            )

        info.breaking_change_risk = risk
        info.estimated_migration_effort = effort

        changelog_info = self._get_changelog_breaking_changes(dep, from_ver, to_ver)
        if changelog_info["breaking_changes"]:
            info.breaking_changes.extend(changelog_info["breaking_changes"])
            base_score -= len(changelog_info["breaking_changes"]) * 5
            info.changelog_url = changelog_info.get("changelog_url")

        if changelog_info.get("deprecated_features"):
            info.deprecated_features = changelog_info["deprecated_features"]
            base_score -= len(info.deprecated_features) * 3

        api_changes = self._analyze_api_changes(dep, from_ver, to_ver)
        if api_changes:
            info.api_changes = api_changes

        usage_impact = self._analyze_usage_impact(dep, info)
        if usage_impact["affected_interfaces"]:
            info.affected_interfaces = usage_impact["affected_interfaces"]
            base_score -= len(info.affected_interfaces) * 3

        if usage_impact.get("migration_guide"):
            info.migration_guide = usage_impact["migration_guide"]

        base_score = max(0, min(100, base_score))
        info.compatibility_score = round(base_score, 1)

        if info.compatibility_score >= 70:
            info.is_compatible = True
        elif info.compatibility_score >= 40:
            info.is_compatible = True
        else:
            info.is_compatible = False

        return info

    def _get_upgrade_type(self, from_ver: str, to_ver: str) -> str:
        """判断升级类型 (major/minor/patch)"""
        try:
            from_v = parse_version(from_ver)
            to_v = parse_version(to_ver)

            if from_v and to_v:
                from_major = from_v[0] if len(from_v) > 0 else 0
                from_minor = from_v[1] if len(from_v) > 1 else 0
                to_major = to_v[0] if len(to_v) > 0 else 0
                to_minor = to_v[1] if len(to_v) > 1 else 0

                if to_major > from_major:
                    return "major"
                elif to_minor > from_minor:
                    return "minor"
        except Exception:
            pass

        from_parts = from_ver.split(".")
        to_parts = to_ver.split(".")

        if len(from_parts) >= 3 and len(to_parts) >= 3:
            if to_parts[0] != from_parts[0]:
                return "major"
            elif to_parts[1] != from_parts[1]:
                return "minor"

        return "patch"

    def _get_changelog_breaking_changes(
        self,
        dep: Dependency,
        from_ver: str,
        to_ver: str,
    ) -> Dict[str, Any]:
        """从 Changelog 中获取破坏性变更"""
        result: Dict[str, Any] = {
            "breaking_changes": [],
            "deprecated_features": [],
            "changelog_url": None,
        }

        if not self.use_remote:
            return result

        cache_key = f"{dep.package_manager.value}:{dep.full_name}:{from_ver}:{to_ver}"
        if cache_key in self._changelog_cache:
            return self._changelog_cache[cache_key]

        try:
            if dep.package_manager == PackageManager.PIP:
                result = self._get_pypi_changelog(dep, from_ver, to_ver)
            elif dep.package_manager == PackageManager.NPM:
                result = self._get_npm_changelog(dep, from_ver, to_ver)
            elif dep.package_manager == PackageManager.MAVEN:
                result = self._get_maven_changelog(dep, from_ver, to_ver)
            elif dep.package_manager == PackageManager.GO:
                result = self._get_go_changelog(dep, from_ver, to_ver)
        except Exception:
            pass

        result = self._apply_known_breaking_changes(dep, from_ver, to_ver, result)

        self._changelog_cache[cache_key] = result
        return result

    def _get_pypi_changelog(
        self, dep: Dependency, from_ver: str, to_ver: str
    ) -> Dict[str, Any]:
        """从 PyPI 获取 changelog"""
        result: Dict[str, Any] = {
            "breaking_changes": [],
            "deprecated_features": [],
            "changelog_url": None,
        }

        try:
            url = f"https://pypi.org/pypi/{dep.name}/json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})

                project_urls = info.get("project_urls", {}) or {}
                for url_type, url_val in project_urls.items():
                    if "changelog" in url_type.lower() or "change" in url_type.lower():
                        result["changelog_url"] = url_val
                        break

                if not result["changelog_url"]:
                    home_page = info.get("home_page") or info.get("project_url")
                    if home_page:
                        if "github.com" in home_page:
                            result["changelog_url"] = f"{home_page.rstrip('/')}/blob/main/CHANGELOG.md"

        except Exception:
            pass

        return result

    def _get_npm_changelog(
        self, dep: Dependency, from_ver: str, to_ver: str
    ) -> Dict[str, Any]:
        """从 npm 获取 changelog"""
        result: Dict[str, Any] = {
            "breaking_changes": [],
            "deprecated_features": [],
            "changelog_url": None,
        }

        try:
            url = f"https://registry.npmjs.org/{dep.name}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                repository = data.get("repository", {})
                if isinstance(repository, dict):
                    repo_url = repository.get("url", "")
                    if "github.com" in repo_url:
                        clean_url = repo_url.replace("git+", "").replace(".git", "")
                        result["changelog_url"] = f"{clean_url.rstrip('/')}/blob/main/CHANGELOG.md"

                versions = data.get("versions", {})
                for version, ver_info in versions.items():
                    try:
                        if self._version_between(version, from_ver, to_ver):
                            if "deprecated" in ver_info and ver_info["deprecated"]:
                                result["deprecated_features"].append(
                                    f"Version {version} is deprecated: {ver_info['deprecated']}"
                                )
                    except Exception:
                        continue

        except Exception:
            pass

        return result

    def _get_maven_changelog(
        self, dep: Dependency, from_ver: str, to_ver: str
    ) -> Dict[str, Any]:
        """从 Maven 获取 changelog"""
        return {
            "breaking_changes": [],
            "deprecated_features": [],
            "changelog_url": None,
        }

    def _get_go_changelog(
        self, dep: Dependency, from_ver: str, to_ver: str
    ) -> Dict[str, Any]:
        """从 Go 模块获取 changelog"""
        result: Dict[str, Any] = {
            "breaking_changes": [],
            "deprecated_features": [],
            "changelog_url": None,
        }

        if "github.com" in dep.name:
            parts = dep.name.split("/")
            if len(parts) >= 3:
                result["changelog_url"] = f"https://{parts[0]}/{parts[1]}/{parts[2]}/blob/main/CHANGELOG.md"

        return result

    def _version_between(self, version: str, from_ver: str, to_ver: str) -> bool:
        """检查版本是否在范围内"""
        from ..scanner.version_utils import version_greater_or_equal, version_less

        return version_greater_or_equal(version, from_ver) and version_less(version, to_ver)

    def _apply_known_breaking_changes(
        self,
        dep: Dependency,
        from_ver: str,
        to_ver: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """应用已知的破坏性变更信息"""
        known_breaking_changes = {
            "django": {
                "2.x->3.x": [
                    "Python 2 support dropped",
                    "URL routing syntax changes (path() replaces url())",
                    "MIDDLEWARE_CLASSES renamed to MIDDLEWARE",
                    "Database query API changes",
                ],
                "3.x->4.x": [
                    "Python 3.6 support dropped",
                    "PostgreSQL 9.6 and 10 support dropped",
                    "CSRF protection changes",
                    "Template engine changes",
                ],
                "4.x->5.x": [
                    "Python 3.8, 3.9, 3.10 support dropped",
                    "Django Forms API changes",
                    "Authentication backend changes",
                ],
            },
            "flask": {
                "1.x->2.x": [
                    "Python 2.7 and 3.5 support dropped",
                    "Werkzeug 2.x required",
                    "Some deprecated features removed",
                    "JSON encoder changes",
                ],
                "2.x->3.x": [
                    "Python 3.7+ required",
                    "App context behavior changes",
                    "Blueprint registration changes",
                ],
            },
            "requests": {
                "2.x->3.x": [
                    "Python 2 support dropped",
                    "SSL/TLS configuration changes",
                    "Session API changes",
                ],
            },
            "lodash": {
                "4.x->5.x": [
                    "Support for IE 11 and older browsers dropped",
                    "Some deprecated methods removed",
                    "Bundle size optimization changes",
                ],
            },
            "react": {
                "17.x->18.x": [
                    "New concurrent rendering features",
                    "Automatic batching changes",
                    "React DOM API changes",
                    "Server-side rendering changes",
                ],
            },
            "spring-core": {
                "5.x->6.x": [
                    "Java 17+ required",
                    "Jakarta EE 9+ migration (javax -> jakarta)",
                    "Spring MVC API changes",
                    "AOT compilation support",
                ],
            },
            "log4j": {
                "1.x->2.x": [
                    "Complete API rewrite, not backward compatible",
                    "Configuration format changes (XML/JSON/YAML)",
                    "Logger API signature changes",
                ],
            },
            "gin": {
                "1.x->2.x": [
                    "Go 1.18+ generics support",
                    "Middleware API changes",
                    "Route group changes",
                ],
            },
            "express": {
                "4.x->5.x": [
                    "Promise-based error handling",
                    "Router API changes",
                    "Body parser changes",
                    "Content negotiation changes",
                ],
            },
        }

        name_lower = dep.name.lower()
        if name_lower in known_breaking_changes:
            from_major = from_ver.split(".")[0]
            to_major = to_ver.split(".")[0]
            key = f"{from_major}.x->{to_major}.x"

            if key in known_breaking_changes[name_lower]:
                result["breaking_changes"].extend(known_breaking_changes[name_lower][key])
                result["breaking_changes"].append(
                    f"📚 See official migration guide for {dep.name} {from_major}.x -> {to_major}.x"
                )

        return result

    def _analyze_api_changes(
        self, dep: Dependency, from_ver: str, to_ver: str
    ) -> List[str]:
        """分析 API 变更"""
        changes = []

        upgrade_type = self._get_upgrade_type(from_ver, to_ver)

        if upgrade_type == "major":
            changes.append("🔴 Major version: Public API changes likely")
            changes.append("   - Check for renamed/removed functions")
            changes.append("   - Check for changed method signatures")
            changes.append("   - Check for configuration format changes")
        elif upgrade_type == "minor":
            changes.append("🟡 Minor version: New APIs may be added")
            changes.append("   - Some deprecated APIs may issue warnings")
            changes.append("   - Check for new required parameters")
        else:
            changes.append("🟢 Patch version: No API changes expected")

        return changes

    def _analyze_usage_impact(
        self, dep: Dependency, info: CompatibilityInfo
    ) -> Dict[str, Any]:
        """分析项目中依赖的使用情况，判断升级影响"""
        result: Dict[str, Any] = {
            "affected_interfaces": [],
            "migration_guide": None,
        }

        if not self.project_path:
            return result

        cache_key = f"{dep.full_name}"
        if cache_key in self._usage_analysis_cache:
            return self._usage_analysis_cache[cache_key]

        try:
            usage = self._find_dependency_usage(dep)
            result["affected_interfaces"] = usage

            if info.breaking_change_risk == "high" and usage:
                if len(usage) >= 10:
                    result["migration_guide"] = (
                        f"⚠️  HIGH IMPACT: {dep.full_name} is used at {len(usage)} locations. "
                        "Consider staged migration or extensive testing."
                    )
                elif len(usage) >= 3:
                    result["migration_guide"] = (
                        f"⚠️  MEDIUM IMPACT: {dep.full_name} is used at {len(usage)} locations. "
                        "Review each usage for compatibility."
                    )
                else:
                    result["migration_guide"] = (
                        f"ℹ️  LOW IMPACT: {dep.full_name} is used at {len(usage)} locations. "
                        "Upgrade should be straightforward."
                    )
        except Exception:
            pass

        self._usage_analysis_cache[cache_key] = result
        return result

    def _find_dependency_usage(self, dep: Dependency) -> List[str]:
        """查找项目中依赖的使用位置"""
        usage_locations: List[str] = []

        file_patterns = {
            PackageManager.PIP: [".py"],
            PackageManager.NPM: [".js", ".jsx", ".ts", ".tsx"],
            PackageManager.MAVEN: [".java", ".kt", ".scala"],
            PackageManager.GO: [".go"],
        }

        extensions = file_patterns.get(dep.package_manager, [])
        if not extensions:
            return usage_locations

        search_names = self._get_search_names(dep)

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in ["node_modules", "target", "dist", "build", ".git", "venv", "__pycache__"]]

            for filename in files:
                if not any(filename.endswith(ext) for ext in extensions):
                    continue

                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        for name in search_names:
                            if name in line:
                                rel_path = os.path.relpath(filepath, self.project_path)
                                usage_locations.append(f"{rel_path}:{line_num}")
                                break
                except Exception:
                    pass

                if len(usage_locations) >= 20:
                    return usage_locations

        return usage_locations

    def _get_search_names(self, dep: Dependency) -> List[str]:
        """获取搜索名称列表"""
        names = [dep.name, dep.full_name]

        if dep.package_manager == PackageManager.PIP:
            names.append(dep.name.replace("-", "_"))
            names.append(dep.name.replace("_", "-"))

        return list(set(names))

    def get_compatibility_summary(
        self, suggestions: List[FixSuggestion]
    ) -> Dict[str, Any]:
        """获取兼容性摘要"""
        total = len(suggestions)
        high_risk = sum(
            1 for s in suggestions
            if s.compatibility and s.compatibility.breaking_change_risk == "high"
        )
        medium_risk = sum(
            1 for s in suggestions
            if s.compatibility and s.compatibility.breaking_change_risk == "medium"
        )
        low_risk = sum(
            1 for s in suggestions
            if s.compatibility and s.compatibility.breaking_change_risk == "low"
        )

        avg_score = 0.0
        compatible = [s for s in suggestions if s.compatibility]
        if compatible:
            avg_score = sum(s.compatibility.compatibility_score for s in compatible) / len(compatible)
            avg_score = round(avg_score, 1)

        total_effort = "low"
        if high_risk > 0:
            total_effort = "high"
        elif medium_risk > 0:
            total_effort = "medium"

        return {
            "total_suggestions": total,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "avg_compatibility_score": avg_score,
            "total_migration_effort": total_effort,
            "recommendations": self._generate_summary_recommendations(
                high_risk, medium_risk, avg_score
            ),
        }

    def _generate_summary_recommendations(
        self, high_risk: int, medium_risk: int, avg_score: float
    ) -> List[str]:
        """生成兼容性摘要建议"""
        recommendations = []

        if high_risk > 0:
            recommendations.append(
                f"🔴 {high_risk} high-risk upgrades with major breaking changes."
            )
            recommendations.append("   Recommendation: Test extensively in staging first.")
            recommendations.append("   Consider incremental upgrades or feature flags.")

        if medium_risk > 0:
            recommendations.append(
                f"🟡 {medium_risk} medium-risk upgrades with potential API changes."
            )
            recommendations.append("   Recommendation: Review changelogs and deprecated APIs.")

        if avg_score >= 80:
            recommendations.append("✅ Overall compatibility is good.")
        elif avg_score >= 60:
            recommendations.append("⚠️  Moderate compatibility concerns.")
        else:
            recommendations.append("🔴 Significant compatibility issues expected.")

        return recommendations
