"""
依赖健康评分模块
综合漏洞、更新频率、维护状态等多维度对依赖进行健康度打分
"""
import os
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..models import (
    Dependency,
    DependencyHealthScore,
    Vulnerability,
    SeverityLevel,
    PackageManager,
)


class DependencyHealthScorer:
    """依赖健康评分器"""

    def __init__(self, project_path: str = "", use_remote: bool = True):
        self.project_path = project_path
        self.use_remote = use_remote
        self._package_info_cache: Dict[str, Any] = {}

    def score_all(
        self,
        dependencies: List[Dependency],
        vulnerabilities: Optional[List[Vulnerability]] = None,
    ) -> List[DependencyHealthScore]:
        """为所有依赖计算健康评分"""
        print("   ↳ Calculating dependency health scores...")

        scores = []
        vuln_map = self._build_vulnerability_map(vulnerabilities or [])

        for dep in dependencies:
            try:
                score = self._score_dependency(dep, vuln_map.get(dep.full_name, []))
                scores.append(score)
            except Exception as e:
                score = DependencyHealthScore(
                    dependency=dep,
                    overall_score=50.0,
                    recommendations=[f"Score calculation error: {str(e)}"],
                )
                scores.append(score)

        scores.sort(key=lambda s: s.overall_score)

        excellent = sum(1 for s in scores if s.health_level == "EXCELLENT")
        good = sum(1 for s in scores if s.health_level == "GOOD")
        fair = sum(1 for s in scores if s.health_level == "FAIR")
        poor = sum(1 for s in scores if s.health_level == "POOR")
        critical = sum(1 for s in scores if s.health_level == "CRITICAL")

        print(f"   ↳ Health distribution: EXCELLENT={excellent}, GOOD={good}, FAIR={fair}, POOR={poor}, CRITICAL={critical}")

        return scores

    def _build_vulnerability_map(
        self, vulnerabilities: List[Vulnerability]
    ) -> Dict[str, List[Vulnerability]]:
        """构建依赖到漏洞的映射"""
        vuln_map: Dict[str, List[Vulnerability]] = {}
        for vuln in vulnerabilities:
            name = vuln.dependency.full_name
            if name not in vuln_map:
                vuln_map[name] = []
            vuln_map[name].append(vuln)
        return vuln_map

    def _score_dependency(
        self,
        dep: Dependency,
        vulnerabilities: List[Vulnerability],
    ) -> DependencyHealthScore:
        """为单个依赖计算健康评分"""
        score = DependencyHealthScore(dependency=dep)

        security_score = self._calculate_security_score(dep, vulnerabilities)
        maintenance_score, maintenance_info = self._calculate_maintenance_score(dep)
        activity_score, activity_info = self._calculate_activity_score(dep)
        community_score = self._calculate_community_score(dep)

        score.security_score = security_score
        score.maintenance_score = maintenance_score
        score.activity_score = activity_score
        score.community_score = community_score

        weights = {
            "security": 0.35,
            "maintenance": 0.30,
            "activity": 0.20,
            "community": 0.15,
        }

        overall_score = (
            security_score * weights["security"]
            + maintenance_score * weights["maintenance"]
            + activity_score * weights["activity"]
            + community_score * weights["community"]
        )

        score.overall_score = round(overall_score, 1)

        score.last_release_date = maintenance_info.get("last_release_date")
        score.release_frequency = activity_info.get("release_frequency")
        score.days_since_last_release = maintenance_info.get("days_since_last_release")
        score.open_issues_count = community_info.get("open_issues_count")
        score.maintainer_count = community_info.get("maintainer_count")
        score.download_trend = activity_info.get("download_trend")

        score.recommendations = self._generate_recommendations(
            dep, score, vulnerabilities, maintenance_info, activity_info
        )

        return score

    def _calculate_security_score(
        self, dep: Dependency, vulnerabilities: List[Vulnerability]
    ) -> float:
        """计算安全评分 (0-100)"""
        if not vulnerabilities:
            return 100.0

        score = 100.0
        severity_penalties = {
            SeverityLevel.CRITICAL: 40,
            SeverityLevel.HIGH: 20,
            SeverityLevel.MEDIUM: 10,
            SeverityLevel.LOW: 3,
        }

        seen_cves = set()
        for vuln in vulnerabilities:
            if vuln.cve_id in seen_cves:
                continue
            seen_cves.add(vuln.cve_id)

            penalty = severity_penalties.get(vuln.severity, 5)

            if vuln.reachability:
                if vuln.reachability.is_reachable:
                    penalty *= 1.2
                else:
                    penalty *= 0.5

            if vuln.fixed_versions:
                penalty *= 0.8

            score = max(0, score - penalty)

        return round(score, 1)

    def _calculate_maintenance_score(
        self, dep: Dependency
    ) -> Tuple[float, Dict[str, Any]]:
        """计算维护评分 (0-100)"""
        info: Dict[str, Any] = {}

        package_info = self._get_package_info(dep)

        last_release_date = package_info.get("last_release_date")
        if last_release_date:
            try:
                if isinstance(last_release_date, str):
                    last_release = datetime.fromisoformat(last_release_date.replace("Z", "+00:00"))
                else:
                    last_release = last_release_date

                days_since = (datetime.now() - last_release).days
                info["days_since_last_release"] = days_since
                info["last_release_date"] = last_release.isoformat()

                if days_since <= 30:
                    maintenance_score = 95
                elif days_since <= 90:
                    maintenance_score = 85
                elif days_since <= 180:
                    maintenance_score = 70
                elif days_since <= 365:
                    maintenance_score = 50
                elif days_since <= 730:
                    maintenance_score = 30
                else:
                    maintenance_score = 15

                if days_since > 730:
                    info["is_archived"] = True

            except Exception:
                maintenance_score = 60
        else:
            maintenance_score = 60

        is_deprecated = package_info.get("is_deprecated", False)
        info["is_deprecated"] = is_deprecated
        if is_deprecated:
            maintenance_score = min(maintenance_score, 20)

        has_security_policy = package_info.get("has_security_policy", False)
        info["has_security_policy"] = has_security_policy
        if has_security_policy:
            maintenance_score = min(100, maintenance_score + 5)

        return round(maintenance_score, 1), info

    def _calculate_activity_score(
        self, dep: Dependency
    ) -> Tuple[float, Dict[str, Any]]:
        """计算活跃度评分 (0-100)"""
        info: Dict[str, Any] = {}

        package_info = self._get_package_info(dep)
        release_count = package_info.get("release_count_last_year", 0)

        if release_count >= 24:
            activity_score = 95
            info["release_frequency"] = "very_frequent"
        elif release_count >= 12:
            activity_score = 85
            info["release_frequency"] = "frequent"
        elif release_count >= 6:
            activity_score = 70
            info["release_frequency"] = "moderate"
        elif release_count >= 3:
            activity_score = 55
            info["release_frequency"] = "infrequent"
        elif release_count >= 1:
            activity_score = 40
            info["release_frequency"] = "rare"
        else:
            activity_score = 25
            info["release_frequency"] = "stagnant"

        downloads = package_info.get("downloads_last_month")
        if downloads:
            if downloads >= 1000000:
                info["download_trend"] = "very_high"
                activity_score = min(100, activity_score + 5)
            elif downloads >= 100000:
                info["download_trend"] = "high"
                activity_score = min(100, activity_score + 3)
            elif downloads >= 10000:
                info["download_trend"] = "medium"
            else:
                info["download_trend"] = "low"

        recent_commits = package_info.get("commits_last_month", 0)
        if recent_commits >= 20:
            activity_score = min(100, activity_score + 5)
        elif recent_commits >= 5:
            activity_score = min(100, activity_score + 2)

        return round(activity_score, 1), info

    def _calculate_community_score(self, dep: Dependency) -> float:
        """计算社区评分 (0-100)"""
        package_info = self._get_package_info(dep)

        maintainer_count = package_info.get("maintainer_count", 0)
        open_issues = package_info.get("open_issues_count")
        stars = package_info.get("stars")

        score = 50.0

        if maintainer_count >= 10:
            score += 25
        elif maintainer_count >= 5:
            score += 20
        elif maintainer_count >= 3:
            score += 15
        elif maintainer_count >= 1:
            score += 10

        if open_issues is not None:
            if open_issues <= 10:
                score += 10
            elif open_issues <= 50:
                score += 5
            elif open_issues >= 500:
                score = max(0, score - 10)

        if stars:
            if stars >= 10000:
                score = min(100, score + 10)
            elif stars >= 1000:
                score = min(100, score + 5)

        score = max(0, min(100, score))

        return round(score, 1)

    def _generate_recommendations(
        self,
        dep: Dependency,
        score: DependencyHealthScore,
        vulnerabilities: List[Vulnerability],
        maintenance_info: Dict[str, Any],
        activity_info: Dict[str, Any],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if score.security_score < 60:
            recommendations.append(
                f"⚠️  High security risk ({score.security_score}/100). {len(vulnerabilities)} vulnerabilities detected."
            )

            for vuln in vulnerabilities[:3]:
                fixed_versions = ", ".join(vuln.fixed_versions) if vuln.fixed_versions else "none"
                recommendations.append(
                    f"   - {vuln.cve_id} [{vuln.severity.value}]: Upgrade to {fixed_versions}"
                )

        if score.maintenance_score < 50:
            if maintenance_info.get("is_deprecated"):
                recommendations.append("❌ Package is deprecated. Consider migrating to an alternative.")
            if maintenance_info.get("is_archived"):
                recommendations.append("❌ Package appears to be archived. Look for actively maintained alternatives.")

            days = maintenance_info.get("days_since_last_release")
            if days and days > 365:
                recommendations.append(
                    f"⚠️  Package not updated for {days} days. Maintenance status is uncertain."
                )

        if score.activity_score < 50:
            freq = activity_info.get("release_frequency", "unknown")
            recommendations.append(
                f"⚠️  Low release activity ({freq}). This may indicate slowing development."
            )

        if score.community_score < 40:
            recommendations.append(
                "⚠️  Small community. Limited support and slower issue resolution."
            )

        if score.overall_score >= 80:
            recommendations.append("✅ Excellent package health. Keep using this dependency.")
        elif score.overall_score >= 60:
            recommendations.append("✅ Good package health. Monitor for any issues.")
        elif score.overall_score < 30:
            recommendations.append("🔴 Critical health issues. Consider finding alternatives.")

        return recommendations

    def _get_package_info(self, dep: Dependency) -> Dict[str, Any]:
        """获取包的元信息（带缓存）"""
        cache_key = f"{dep.package_manager.value}:{dep.full_name}"
        if cache_key in self._package_info_cache:
            return self._package_info_cache[cache_key]

        info: Dict[str, Any] = {}

        if self.use_remote:
            try:
                if dep.package_manager == PackageManager.PIP:
                    info = self._get_pypi_info(dep)
                elif dep.package_manager == PackageManager.NPM:
                    info = self._get_npm_info(dep)
                elif dep.package_manager == PackageManager.MAVEN:
                    info = self._get_maven_info(dep)
                elif dep.package_manager == PackageManager.GO:
                    info = self._get_go_info(dep)
            except Exception:
                pass

        info = self._apply_heuristic_info(dep, info)

        self._package_info_cache[cache_key] = info
        return info

    def _get_pypi_info(self, dep: Dependency) -> Dict[str, Any]:
        """从 PyPI 获取包信息"""
        info: Dict[str, Any] = {}
        try:
            url = f"https://pypi.org/pypi/{dep.name}/json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                info_data = data.get("info", {})

                releases = data.get("releases", {})
                version_dates = []
                for version, release_info in releases.items():
                    if release_info:
                        for item in release_info:
                            if "upload_time" in item:
                                try:
                                    upload_time = datetime.fromisoformat(item["upload_time"].replace("Z", "+00:00"))
                                    version_dates.append(upload_time)
                                except Exception:
                                    pass

                if version_dates:
                    version_dates.sort(reverse=True)
                    info["last_release_date"] = version_dates[0]

                    one_year_ago = datetime.now() - timedelta(days=365)
                    info["release_count_last_year"] = sum(
                        1 for d in version_dates if d >= one_year_ago
                    )

                info["is_deprecated"] = info_data.get("yanked", False)
                maintainers = info_data.get("maintainer", []) or []
                info["maintainer_count"] = len(maintainers) if maintainers else 1

        except Exception:
            pass
        return info

    def _get_npm_info(self, dep: Dependency) -> Dict[str, Any]:
        """从 npm 获取包信息"""
        info: Dict[str, Any] = {}
        try:
            url = f"https://registry.npmjs.org/{dep.name}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()

                time_data = data.get("time", {})
                version_times = []
                for version, time_str in time_data.items():
                    if version not in ["created", "modified"]:
                        try:
                            t = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                            version_times.append(t)
                        except Exception:
                            pass

                if version_times:
                    version_times.sort(reverse=True)
                    info["last_release_date"] = version_times[0]

                    one_year_ago = datetime.now() - timedelta(days=365)
                    info["release_count_last_year"] = sum(
                        1 for d in version_times if d >= one_year_ago
                    )

                info_data = data.get("versions", {})
                if info_data and dep.version in info_data:
                    pkg_info = info_data[dep.version]
                    info["is_deprecated"] = "deprecated" in pkg_info and pkg_info["deprecated"]

                maintainers = data.get("maintainers", [])
                info["maintainer_count"] = len(maintainers)

        except Exception:
            pass
        return info

    def _get_maven_info(self, dep: Dependency) -> Dict[str, Any]:
        """从 Maven Central 获取包信息"""
        info: Dict[str, Any] = {}
        try:
            group_id = dep.group_id or dep.name
            artifact_id = dep.name

            url = (
                f"https://search.maven.org/solrsearch/select"
                f"?q=g:{group_id}+AND+a:{artifact_id}"
                f"&core=gav&rows=20&wt=json"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])

                timestamps = [d.get("timestamp", 0) for d in docs if d.get("timestamp")]
                if timestamps:
                    timestamps.sort(reverse=True)
                    last_ts = timestamps[0] / 1000
                    info["last_release_date"] = datetime.fromtimestamp(last_ts)

                    one_year_ago = (datetime.now() - timedelta(days=365)).timestamp() * 1000
                    info["release_count_last_year"] = sum(
                        1 for ts in timestamps if ts >= one_year_ago
                    )

        except Exception:
            pass
        return info

    def _get_go_info(self, dep: Dependency) -> Dict[str, Any]:
        """获取 Go 模块信息"""
        info: Dict[str, Any] = {}
        try:
            url = f"https://proxy.golang.org/{dep.name}/@v/list"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split("\n")
                versions = [line.strip() for line in lines if line.strip()]

                if versions:
                    info["last_release_date"] = datetime.now() - timedelta(days=90)
                    info["release_count_last_year"] = len(versions)

        except Exception:
            pass
        return info

    def _apply_heuristic_info(
        self, dep: Dependency, info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用启发式信息补充"""
        common_well_maintained = {
            "django": (90, 12),
            "flask": (85, 8),
            "requests": (95, 6),
            "numpy": (95, 24),
            "pandas": (95, 18),
            "react": (95, 24),
            "vue": (90, 12),
            "lodash": (85, 6),
            "express": (85, 8),
            "spring-boot": (90, 12),
            "spring-core": (90, 12),
            "log4j": (70, 4),
            "gin": (85, 12),
            "echo": (80, 8),
        }

        name_lower = dep.name.lower()
        if name_lower in common_well_maintained:
            if "last_release_date" not in info:
                quality, releases = common_well_maintained[name_lower]
                if quality >= 80:
                    info["last_release_date"] = datetime.now() - timedelta(days=60)
                elif quality >= 60:
                    info["last_release_date"] = datetime.now() - timedelta(days=180)
                else:
                    info["last_release_date"] = datetime.now() - timedelta(days=365)
                info["release_count_last_year"] = releases

            if "maintainer_count" not in info:
                info["maintainer_count"] = 5

        if "maintainer_count" not in info:
            info["maintainer_count"] = 1

        return info

    def get_project_health_summary(
        self, scores: List[DependencyHealthScore]
    ) -> Dict[str, Any]:
        """获取项目整体健康摘要"""
        if not scores:
            return {"overall_score": 0.0, "health_level": "UNKNOWN"}

        avg_score = sum(s.overall_score for s in scores) / len(scores)

        critical_count = sum(1 for s in scores if s.health_level == "CRITICAL")
        poor_count = sum(1 for s in scores if s.health_level == "POOR")

        if critical_count > 0:
            avg_score = max(0, avg_score - critical_count * 5)
        if poor_count > 0:
            avg_score = max(0, avg_score - poor_count * 2)

        avg_score = round(avg_score, 1)

        if avg_score >= 80:
            level = "EXCELLENT"
        elif avg_score >= 60:
            level = "GOOD"
        elif avg_score >= 40:
            level = "FAIR"
        elif avg_score >= 20:
            level = "POOR"
        else:
            level = "CRITICAL"

        return {
            "overall_score": avg_score,
            "health_level": level,
            "dependency_count": len(scores),
            "distribution": {
                "EXCELLENT": sum(1 for s in scores if s.health_level == "EXCELLENT"),
                "GOOD": sum(1 for s in scores if s.health_level == "GOOD"),
                "FAIR": sum(1 for s in scores if s.health_level == "FAIR"),
                "POOR": sum(1 for s in scores if s.health_level == "POOR"),
                "CRITICAL": sum(1 for s in scores if s.health_level == "CRITICAL"),
            },
            "recommendations": self._generate_project_recommendations(scores, avg_score),
        }

    def _generate_project_recommendations(
        self, scores: List[DependencyHealthScore], overall_score: float
    ) -> List[str]:
        """生成项目级别的建议"""
        recommendations = []

        critical_deps = [s for s in scores if s.health_level == "CRITICAL"]
        poor_deps = [s for s in scores if s.health_level == "POOR"]

        if critical_deps:
            recommendations.append(f"🔴 {len(critical_deps)} dependencies have CRITICAL health issues:")
            for dep in critical_deps[:5]:
                recommendations.append(f"   - {dep.dependency.full_name} ({dep.overall_score}/100)")

        if poor_deps:
            recommendations.append(f"🟠 {len(poor_deps)} dependencies have POOR health:")
            for dep in poor_deps[:3]:
                recommendations.append(f"   - {dep.dependency.full_name} ({dep.overall_score}/100)")

        if overall_score >= 80:
            recommendations.append("✅ Project dependency health is excellent!")
        elif overall_score >= 60:
            recommendations.append("✅ Project dependency health is good. Monitor high-risk dependencies.")
        elif overall_score >= 40:
            recommendations.append("⚠️  Project dependency health is fair. Consider upgrading problematic dependencies.")
        else:
            recommendations.append("🔴 Project dependency health is poor. Immediate action recommended.")

        return recommendations
