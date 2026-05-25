"""
漏洞等级评估器
"""
from typing import List, Dict, Any
import re

from ..models import Vulnerability, SeverityLevel, Dependency


class SeverityEvaluator:
    """漏洞严重等级评估器"""

    KEYWORDS = {
        SeverityLevel.CRITICAL: [
            "remote code execution", "rce", "command injection", "sql injection",
            "arbitrary code", "code execution", "remote command", "backdoor",
            "unauthenticated", "authentication bypass", "privilege escalation",
            "critical", "cve-2021-44228", "log4shell", "spring4shell",
        ],
        SeverityLevel.HIGH: [
            "denial of service", "dos", "ddos", "information disclosure",
            "data leakage", "path traversal", "directory traversal",
            "file inclusion", "xss", "cross-site scripting", "csrf",
            "server-side request forgery", "ssrf", "xml external entity",
            "xxe", "insecure deserialization", "high severity",
        ],
        SeverityLevel.MEDIUM: [
            "open redirect", "clickjacking", "missing authentication",
            "insecure direct object reference", "idor", "broken access control",
            "sensitive data exposure", "weak encryption", "medium severity",
        ],
        SeverityLevel.LOW: [
            "information leak", "version disclosure", "improper error handling",
            "insufficient logging", "low severity",
        ],
    }

    def evaluate(
        self,
        vulnerability: Vulnerability,
        dependency: Dependency,
    ) -> SeverityLevel:
        """评估漏洞等级"""
        if vulnerability.cvss_score > 0:
            return SeverityLevel.from_cvss(vulnerability.cvss_score)

        return self._evaluate_from_description(vulnerability)

    def _evaluate_from_description(self, vulnerability: Vulnerability) -> SeverityLevel:
        """从描述信息评估漏洞等级"""
        text = f"{vulnerability.title} {vulnerability.description}".lower()

        for level in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
            keywords = self.KEYWORDS.get(level, [])
            for keyword in keywords:
                if keyword.lower() in text:
                    return level

        return SeverityLevel.UNKNOWN

    def evaluate_batch(
        self,
        vulnerabilities: List[Vulnerability],
        dependencies: List[Dependency],
    ) -> List[Vulnerability]:
        """批量评估漏洞等级"""
        dep_map = {d.full_name: d for d in dependencies}

        for vuln in vulnerabilities:
            dep = dep_map.get(vuln.dependency.full_name, vuln.dependency)
            vuln.severity = self.evaluate(vuln, dep)

        return vulnerabilities

    def get_severity_stats(self, vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        """获取漏洞等级统计"""
        stats = {
            SeverityLevel.CRITICAL.value: 0,
            SeverityLevel.HIGH.value: 0,
            SeverityLevel.MEDIUM.value: 0,
            SeverityLevel.LOW.value: 0,
            SeverityLevel.UNKNOWN.value: 0,
        }

        for vuln in vulnerabilities:
            stats[vuln.severity.value] += 1

        return stats

    def get_risk_score(self, vulnerabilities: List[Vulnerability]) -> float:
        """计算整体风险分数"""
        if not vulnerabilities:
            return 0.0

        weights = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 7,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 1,
            SeverityLevel.UNKNOWN: 0.5,
        }

        total_weight = 0
        for vuln in vulnerabilities:
            weight = weights.get(vuln.severity, 0)
            if vuln.cvss_score > 0:
                total_weight += (vuln.cvss_score / 10) * weight
            else:
                total_weight += weight

        max_possible = len(vulnerabilities) * 10
        return (total_weight / max_possible) * 100 if max_possible > 0 else 0.0
