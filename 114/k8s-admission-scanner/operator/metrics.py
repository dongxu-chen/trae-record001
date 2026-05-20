#!/usr/bin/env python3
import logging
from dataclasses import dataclass
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


# 扫描请求计数
scan_requests_total = Counter(
    "trivy_admission_scan_requests_total",
    "Total number of image scan requests",
    ["namespace", "result"]
)

# 扫描持续时间
scan_duration_seconds = Histogram(
    "trivy_admission_scan_duration_seconds",
    "Duration of image scans in seconds",
    ["namespace"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)

# 当前活动的扫描
active_scans = Gauge(
    "trivy_admission_active_scans",
    "Number of currently active image scans"
)

# 扫描通过计数
scan_allowed_total = Counter(
    "trivy_admission_scan_allowed_total",
    "Total number of allowed pods after scan",
    ["namespace"]
)

# 扫描拒绝计数
scan_denied_total = Counter(
    "trivy_admission_scan_denied_total",
    "Total number of denied pods after scan",
    ["namespace", "reason"]
)

# 漏洞统计
vulnerabilities_found = Gauge(
    "trivy_admission_vulnerabilities_found",
    "Number of vulnerabilities found per severity",
    ["namespace", "severity"]
)

# 漏洞总数
vulnerabilities_total = Gauge(
    "trivy_admission_vulnerabilities_total",
    "Total number of vulnerabilities found",
    ["namespace"]
)

# 策略配置状态
policy_config_status = Gauge(
    "trivy_admission_policy_config_status",
    "Status of scan policy configuration",
    ["policy_name"]
)

# 跳过扫描计数
scan_skipped_total = Counter(
    "trivy_admission_scan_skipped_total",
    "Total number of skipped scans",
    ["namespace", "reason"]
)


class MetricsManager:
    """指标管理类"""

    @staticmethod
    def record_scan_request(namespace: str, result: str):
        """记录扫描请求"""
        scan_requests_total.labels(namespace=namespace, result=result).inc()

    @staticmethod
    def record_scan_duration(namespace: str, duration: float):
        """记录扫描持续时间"""
        scan_duration_seconds.labels(namespace=namespace).observe(duration)

    @staticmethod
    def record_scan_allowed(namespace: str):
        """记录扫描通过"""
        scan_allowed_total.labels(namespace=namespace).inc()

    @staticmethod
    def record_scan_denied(namespace: str, reason: str):
        """记录扫描拒绝"""
        scan_denied_total.labels(namespace=namespace, reason=reason).inc()

    @staticmethod
    def record_vulnerabilities(namespace: str, vuln_counts: dict):
        """记录漏洞统计"""
        total = 0
        for severity, count in vuln_counts.items():
            vulnerabilities_found.labels(
                namespace=namespace,
                severity=severity.lower()
            ).set(count)
            total += count
        vulnerabilities_total.labels(namespace=namespace).set(total)

    @staticmethod
    def record_scan_skipped(namespace: str, reason: str):
        """记录跳过扫描"""
        scan_skipped_total.labels(namespace=namespace, reason=reason).inc()

    @staticmethod
    def inc_active_scans():
        """增加活动扫描计数"""
        active_scans.inc()

    @staticmethod
    def dec_active_scans():
        """减少活动扫描计数"""
        active_scans.dec()


metrics_manager = MetricsManager()
