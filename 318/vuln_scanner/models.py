"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class SeverityLevel(str, Enum):
    """漏洞严重等级"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_cvss(cls, cvss_score: float) -> "SeverityLevel":
        if cvss_score >= 9.0:
            return cls.CRITICAL
        elif cvss_score >= 7.0:
            return cls.HIGH
        elif cvss_score >= 4.0:
            return cls.MEDIUM
        elif cvss_score > 0:
            return cls.LOW
        return cls.UNKNOWN

    @property
    def color(self) -> str:
        colors = {
            "CRITICAL": "\033[91m",
            "HIGH": "\033[31m",
            "MEDIUM": "\033[33m",
            "LOW": "\033[32m",
            "UNKNOWN": "\033[37m",
        }
        return colors.get(self.value, "\033[37m")

    @property
    def order(self) -> int:
        orders = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "UNKNOWN": 0,
        }
        return orders.get(self.value, 0)


class PackageManager(str, Enum):
    """包管理器类型"""
    MAVEN = "maven"
    NPM = "npm"
    PIP = "pip"
    GO = "go"
    UNKNOWN = "unknown"


@dataclass
class Dependency:
    """依赖项"""
    name: str
    version: str
    package_manager: PackageManager
    group_id: Optional[str] = None
    path: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)
    parent: Optional["Dependency"] = None
    depth: int = 0
    is_transitive: bool = False
    children: List["Dependency"] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        if self.package_manager == PackageManager.MAVEN and self.group_id:
            return f"{self.group_id}:{self.name}"
        return self.name

    @property
    def dependency_chain(self) -> List[str]:
        """获取依赖链"""
        chain = []
        current: Optional[Dependency] = self
        while current:
            chain.insert(0, current.full_name)
            current = current.parent
        return chain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "package_manager": self.package_manager.value,
            "group_id": self.group_id,
            "path": self.path,
            "depth": self.depth,
            "is_transitive": self.is_transitive,
            "dependency_chain": self.dependency_chain,
        }


@dataclass
class ReachabilityInfo:
    """漏洞可达性信息"""
    is_reachable: bool = False
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    call_sites: List[str] = field(default_factory=list)
    import_sites: List[str] = field(default_factory=list)
    analysis_method: str = "static"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_reachable": self.is_reachable,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "call_sites": self.call_sites,
            "import_sites": self.import_sites,
            "analysis_method": self.analysis_method,
        }


@dataclass
class Vulnerability:
    """漏洞信息"""
    cve_id: str
    dependency: Dependency
    title: str
    description: str
    severity: SeverityLevel
    cvss_score: float
    cvss_vector: Optional[str] = None
    affected_versions: List[str] = field(default_factory=list)
    fixed_versions: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    cwe_ids: List[str] = field(default_factory=list)
    publish_date: Optional[str] = None
    impact_scope: str = "unknown"
    reachability: Optional[ReachabilityInfo] = None

    @property
    def effective_severity(self) -> SeverityLevel:
        """考虑可达性后的有效严重等级"""
        if self.reachability and not self.reachability.is_reachable:
            if self.severity == SeverityLevel.CRITICAL:
                return SeverityLevel.HIGH
            elif self.severity == SeverityLevel.HIGH:
                return SeverityLevel.MEDIUM
            elif self.severity == SeverityLevel.MEDIUM:
                return SeverityLevel.LOW
        return self.severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cve_id": self.cve_id,
            "dependency": {
                "name": self.dependency.name,
                "version": self.dependency.version,
                "package_manager": self.dependency.package_manager.value,
                "group_id": self.dependency.group_id,
            },
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "effective_severity": self.effective_severity.value,
            "cvss_score": self.cvss_score,
            "cvss_vector": self.cvss_vector,
            "affected_versions": self.affected_versions,
            "fixed_versions": self.fixed_versions,
            "references": self.references,
            "cwe_ids": self.cwe_ids,
            "publish_date": self.publish_date,
            "impact_scope": self.impact_scope,
            "reachability": self.reachability.to_dict() if self.reachability else None,
        }


@dataclass
class ScanResult:
    """扫描结果"""
    dependencies: List[Dependency] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    scan_time: str = ""
    project_path: str = ""
    package_manager: PackageManager = PackageManager.UNKNOWN

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.LOW)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_time": self.scan_time,
            "project_path": self.project_path,
            "package_manager": self.package_manager.value,
            "dependencies_count": len(self.dependencies),
            "vulnerabilities_count": len(self.vulnerabilities),
            "severity_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "dependencies": [
                {
                    "name": d.name,
                    "version": d.version,
                    "package_manager": d.package_manager.value,
                    "group_id": d.group_id,
                }
                for d in self.dependencies
            ],
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


@dataclass
class DependencyHealthScore:
    """依赖健康评分"""
    dependency: Dependency
    overall_score: float = 0.0
    security_score: float = 0.0
    maintenance_score: float = 0.0
    activity_score: float = 0.0
    community_score: float = 0.0
    last_release_date: Optional[str] = None
    release_frequency: Optional[str] = None
    days_since_last_release: Optional[int] = None
    open_issues_count: Optional[int] = None
    maintainer_count: Optional[int] = None
    download_trend: Optional[str] = None
    is_deprecated: bool = False
    is_archived: bool = False
    has_security_policy: bool = False
    recommendations: List[str] = field(default_factory=list)

    @property
    def health_level(self) -> str:
        if self.overall_score >= 80:
            return "EXCELLENT"
        elif self.overall_score >= 60:
            return "GOOD"
        elif self.overall_score >= 40:
            return "FAIR"
        elif self.overall_score >= 20:
            return "POOR"
        return "CRITICAL"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency": self.dependency.full_name,
            "version": self.dependency.version,
            "overall_score": self.overall_score,
            "health_level": self.health_level,
            "security_score": self.security_score,
            "maintenance_score": self.maintenance_score,
            "activity_score": self.activity_score,
            "community_score": self.community_score,
            "last_release_date": self.last_release_date,
            "release_frequency": self.release_frequency,
            "days_since_last_release": self.days_since_last_release,
            "open_issues_count": self.open_issues_count,
            "maintainer_count": self.maintainer_count,
            "download_trend": self.download_trend,
            "is_deprecated": self.is_deprecated,
            "is_archived": self.is_archived,
            "has_security_policy": self.has_security_policy,
            "recommendations": self.recommendations,
        }


@dataclass
class CompatibilityInfo:
    """升级兼容性信息"""
    dependency: Dependency
    from_version: str
    to_version: str
    is_compatible: bool = True
    breaking_change_risk: str = "low"
    breaking_changes: List[str] = field(default_factory=list)
    deprecated_features: List[str] = field(default_factory=list)
    api_changes: List[str] = field(default_factory=list)
    migration_guide: Optional[str] = None
    changelog_url: Optional[str] = None
    affected_interfaces: List[str] = field(default_factory=list)
    compatibility_score: float = 100.0
    estimated_migration_effort: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency": self.dependency.full_name,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "is_compatible": self.is_compatible,
            "breaking_change_risk": self.breaking_change_risk,
            "breaking_changes": self.breaking_changes,
            "deprecated_features": self.deprecated_features,
            "api_changes": self.api_changes,
            "migration_guide": self.migration_guide,
            "changelog_url": self.changelog_url,
            "affected_interfaces": self.affected_interfaces,
            "compatibility_score": self.compatibility_score,
            "estimated_migration_effort": self.estimated_migration_effort,
        }


@dataclass
class FixSuggestion:
    """修复建议"""
    dependency: Dependency
    current_version: str
    suggested_version: str
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    upgrade_type: str = "patch"
    breaking_changes: bool = False
    compatibility: Optional[CompatibilityInfo] = None
    health_score: Optional[DependencyHealthScore] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency": self.dependency.full_name,
            "current_version": self.current_version,
            "suggested_version": self.suggested_version,
            "upgrade_type": self.upgrade_type,
            "breaking_changes": self.breaking_changes,
            "vulnerabilities_fixed": [v.cve_id for v in self.vulnerabilities],
            "compatibility": self.compatibility.to_dict() if self.compatibility else None,
            "health_score": self.health_score.to_dict() if self.health_score else None,
        }
