"""
漏洞影响范围分析器
"""
from typing import List, Dict, Any, Set
import re

from ..models import Vulnerability, Dependency, SeverityLevel, PackageManager


class ImpactAnalyzer:
    """漏洞影响范围分析器"""

    SCOPE_KEYWORDS = {
        "remote": [
            "remote", "network", "internet", "external", "unauthenticated",
            "remote attacker", "over the network",
        ],
        "local": [
            "local", "localhost", "127.0.0.1", "loopback", "local attacker",
        ],
        "adjacent": [
            "adjacent", "same network", "local network", "intranet",
        ],
    }

    COMPONENT_TYPES = {
        "web_framework": ["django", "flask", "spring", "express", "fastapi", "gin", "beego"],
        "database_driver": ["mysql", "postgres", "mongodb", "redis", "sqlite", "oracle", "mssql"],
        "authentication": ["jwt", "oauth", "passport", "auth0", "shiro", "spring-security"],
        "cryptography": ["openssl", "crypto", "bcrypt", "hashlib", "encrypt", "cipher"],
        "networking": ["requests", "axios", "http", "netty", "socket"],
        "logging": ["log4j", "logback", "slf4j", "winston", "pino"],
        "serialization": ["jackson", "gson", "fastjson", "pickle", "protobuf"],
        "file_processing": ["poi", "pdfbox", "imaging", "pillow", "imagemagick"],
    }

    def analyze(self, vulnerability: Vulnerability) -> str:
        """分析漏洞影响范围"""
        scope = "unknown"
        text = f"{vulnerability.title} {vulnerability.description}".lower()
        vector = (vulnerability.cvss_vector or "").lower()

        if "av:n" in vector or "attack vector:network" in text:
            scope = "network"
        elif "av:a" in vector or "attack vector:adjacent" in text:
            scope = "adjacent"
        elif "av:l" in vector or "attack vector:local" in text:
            scope = "local"
        elif "av:p" in vector or "attack vector:physical" in text:
            scope = "physical"
        else:
            for scope_type, keywords in self.SCOPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in text:
                        scope = scope_type
                        break
                if scope != "unknown":
                    break

        return scope

    def analyze_component_type(self, dependency: Dependency) -> str:
        """分析依赖组件类型"""
        name = dependency.name.lower()
        full_name = dependency.full_name.lower()

        for comp_type, keywords in self.COMPONENT_TYPES.items():
            for keyword in keywords:
                if keyword in name or keyword in full_name:
                    return comp_type

        if dependency.package_manager == PackageManager.MAVEN:
            group_id = (dependency.group_id or "").lower()
            for comp_type, keywords in self.COMPONENT_TYPES.items():
                for keyword in keywords:
                    if keyword in group_id:
                        return comp_type

        return "other"

    def get_impact_score(self, vulnerability: Vulnerability, dependency: Dependency) -> int:
        """计算影响分数"""
        score = 0

        if vulnerability.cvss_score > 0:
            score += int(vulnerability.cvss_score * 10)

        severity_weights = {
            SeverityLevel.CRITICAL: 100,
            SeverityLevel.HIGH: 70,
            SeverityLevel.MEDIUM: 40,
            SeverityLevel.LOW: 10,
            SeverityLevel.UNKNOWN: 5,
        }
        score += severity_weights.get(vulnerability.severity, 0)

        scope = vulnerability.impact_scope or self.analyze(vulnerability)
        scope_weights = {
            "network": 50,
            "adjacent": 30,
            "local": 15,
            "physical": 5,
            "unknown": 10,
        }
        score += scope_weights.get(scope, 0)

        component_type = self.analyze_component_type(dependency)
        component_weights = {
            "web_framework": 30,
            "database_driver": 25,
            "authentication": 40,
            "cryptography": 35,
            "networking": 20,
            "logging": 25,
            "serialization": 30,
            "file_processing": 15,
            "other": 10,
        }
        score += component_weights.get(component_type, 10)

        extras = dependency.extras or {}
        if extras.get("dep_type") == "dependencies":
            score += 20
        elif extras.get("dep_type") == "devDependencies":
            score += 5

        if extras.get("scope") == "compile":
            score += 20

        return min(score, 100)

    def get_dependency_usage_context(self, dependency: Dependency) -> Dict[str, Any]:
        """获取依赖使用上下文信息"""
        return {
            "component_type": self.analyze_component_type(dependency),
            "package_manager": dependency.package_manager.value,
            "is_production": self._is_production_dependency(dependency),
            "extras": dependency.extras,
        }

    def _is_production_dependency(self, dependency: Dependency) -> bool:
        """判断是否为生产环境依赖"""
        extras = dependency.extras or {}
        dep_type = extras.get("dep_type", "")
        scope = extras.get("scope", "")

        if dep_type == "devDependencies":
            return False
        if scope in ["test", "provided"]:
            return False
        if extras.get("indirect"):
            return True

        return True

    def analyze_batch(self, vulnerabilities: List[Vulnerability]) -> List[Vulnerability]:
        """批量分析漏洞影响"""
        for vuln in vulnerabilities:
            vuln.impact_scope = self.analyze(vuln)
        return vulnerabilities

    def generate_impact_report(
        self,
        vulnerabilities: List[Vulnerability],
        dependencies: List[Dependency],
    ) -> Dict[str, Any]:
        """生成影响分析报告"""
        dep_map = {d.full_name: d for d in dependencies}

        report = {
            "total_vulnerabilities": len(vulnerabilities),
            "by_severity": {},
            "by_scope": {},
            "by_component_type": {},
            "by_production_status": {"production": 0, "development": 0},
            "high_risk_dependencies": [],
        }

        for vuln in vulnerabilities:
            dep = dep_map.get(vuln.dependency.full_name, vuln.dependency)

            severity = vuln.severity.value
            report["by_severity"][severity] = report["by_severity"].get(severity, 0) + 1

            scope = vuln.impact_scope or self.analyze(vuln)
            report["by_scope"][scope] = report["by_scope"].get(scope, 0) + 1

            comp_type = self.analyze_component_type(dep)
            report["by_component_type"][comp_type] = report["by_component_type"].get(comp_type, 0) + 1

            if self._is_production_dependency(dep):
                report["by_production_status"]["production"] += 1
            else:
                report["by_production_status"]["development"] += 1

            impact_score = self.get_impact_score(vuln, dep)
            if impact_score >= 70:
                report["high_risk_dependencies"].append({
                    "dependency": dep.full_name,
                    "version": dep.version,
                    "cve_id": vuln.cve_id,
                    "severity": vuln.severity.value,
                    "impact_score": impact_score,
                    "component_type": comp_type,
                })

        report["high_risk_dependencies"].sort(key=lambda x: x["impact_score"], reverse=True)

        return report
