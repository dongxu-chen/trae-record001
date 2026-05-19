#!/usr/bin/env python3
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import ScanPolicy, policy_manager
from .metrics import metrics_manager

logger = logging.getLogger(__name__)


@dataclass
class Vulnerability:
    vulnerability_id: str
    severity: str
    package_name: str
    installed_version: str
    fixed_version: str
    description: str = ""
    cvss_score: float = 0.0


@dataclass
class ScanResult:
    image: str
    success: bool
    allowed: bool = True
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    vuln_counts: Dict[str, int] = field(default_factory=dict)
    max_cvss: float = 0.0
    reason: str = ""
    scan_duration: float = 0.0
    error: Optional[str] = None


class TrivyScanner:
    """Trivy扫描器封装"""

    def __init__(self):
        self._check_trivy_installed()

    def _check_trivy_installed(self):
        """检查Trivy是否安装"""
        try:
            result = subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                logger.info(f"Trivy版本: {result.stdout.strip()}")
                return
        except Exception as e:
            logger.warning(f"检查Trivy版本失败: {e}")

        logger.warning("Trivy未找到，将尝试在首次运行时自动下载数据库")

    def scan_image(self, image: str, policy: ScanPolicy, namespace: str) -> ScanResult:
        """扫描单个镜像"""
        start_time = time.time()
        metrics_manager.inc_active_scans()

        result = ScanResult(image=image, success=False)

        try:
            logger.info(f"开始扫描镜像: {image} (命名空间: {namespace})")

            env = {
                "TRIVY_QUIET": "true",
                "TRIVY_TIMEOUT": str(policy.scan_timeout),
            }

            scan_result = subprocess.run(
                [
                    "trivy", "image",
                    "--format", "json",
                    "--scanners", "vuln",
                    "--vuln-type", "os,library",
                    "--severity", "CRITICAL,HIGH,MEDIUM,LOW",
                    "--timeout", f"{policy.scan_timeout}s",
                    image
                ],
                capture_output=True,
                text=True,
                timeout=policy.scan_timeout + 10,
                env=env
            )

            if scan_result.returncode != 0:
                error_msg = scan_result.stderr or "未知错误"
                logger.error(f"扫描镜像 {image} 失败: {error_msg}")
                result.error = error_msg
                return result

            result.success = True
            result.vulnerabilities = self._parse_vulnerabilities(scan_result.stdout)
            result.vuln_counts = self._count_vulnerabilities(result.vulnerabilities)
            result.max_cvss = max(
                [v.cvss_score for v in result.vulnerabilities],
                default=0.0
            )

            # 判断是否允许
            result.allowed, result.reason = self._check_policy(result, policy)

            logger.info(
                f"扫描完成: {image}, 漏洞数: {len(result.vulnerabilities)}, "
                f"允许: {result.allowed}, 原因: {result.reason}"
            )

        except subprocess.TimeoutExpired:
            error_msg = f"扫描超时（超过 {policy.scan_timeout} 秒）"
            logger.error(f"扫描镜像 {image} 超时")
            result.error = error_msg
        except Exception as e:
            error_msg = f"扫描异常: {str(e)}"
            logger.error(f"扫描镜像 {image} 异常: {str(e)}")
            result.error = error_msg
        finally:
            metrics_manager.dec_active_scans()
            result.scan_duration = time.time() - start_time

        return result

    def _parse_vulnerabilities(self, raw_output: str) -> List[Vulnerability]:
        """解析Trivy JSON输出"""
        vulnerabilities = []

        try:
            data = json.loads(raw_output)

            for result in data.get("Results", []):
                for vuln in result.get("Vulnerabilities", []):
                    cvss_score = 0.0
                    cvss_data = vuln.get("CVSS", {})
                    if cvss_data:
                        for vendor_data in cvss_data.values():
                            if vendor_data.get("V3Score"):
                                cvss_score = float(vendor_data["V3Score"])
                                break
                            elif vendor_data.get("V2Score"):
                                cvss_score = float(vendor_data["V2Score"])
                                break

                    vulnerabilities.append(Vulnerability(
                        vulnerability_id=vuln.get("VulnerabilityID", ""),
                        severity=vuln.get("Severity", "UNKNOWN"),
                        package_name=vuln.get("PkgName", ""),
                        installed_version=vuln.get("InstalledVersion", ""),
                        fixed_version=vuln.get("FixedVersion", ""),
                        description=vuln.get("Description", ""),
                        cvss_score=cvss_score
                    ))

        except json.JSONDecodeError as e:
            logger.error(f"解析扫描结果失败: {e}")

        return vulnerabilities

    def _count_vulnerabilities(self, vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        """按严重程度统计漏洞数量"""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}

        for vuln in vulnerabilities:
            severity = vuln.severity.upper()
            if severity in counts:
                counts[severity] += 1
            else:
                counts["UNKNOWN"] += 1

        return counts

    def _check_policy(self, scan_result: ScanResult, policy: ScanPolicy) -> tuple[bool, str]:
        """根据策略检查是否允许部署"""
        counts = scan_result.vuln_counts
        threshold = policy.severity_threshold

        # 检查严重漏洞
        if counts["CRITICAL"] > threshold.critical:
            return False, (
                f"严重漏洞数量超过阈值: {counts['CRITICAL']} > {threshold.critical}"
            )

        # 检查高危漏洞
        if counts["HIGH"] > threshold.high:
            return False, (
                f"高危漏洞数量超过阈值: {counts['HIGH']} > {threshold.high}"
            )

        # 检查中危漏洞
        if counts["MEDIUM"] > threshold.medium:
            return False, (
                f"中危漏洞数量超过阈值: {counts['MEDIUM']} > {threshold.medium}"
            )

        # 检查低危漏洞
        if counts["LOW"] > threshold.low:
            return False, (
                f"低危漏洞数量超过阈值: {counts['LOW']} > {threshold.low}"
            )

        # 检查CVSS分数
        if scan_result.max_cvss > threshold.cvss_score_threshold:
            return False, (
                f"最高CVSS分数超过阈值: {scan_result.max_cvss} > {threshold.cvss_score_threshold}"
            )

        return True, "所有检查通过"

    def scan_pod_images(self, images: List[str], namespace: str,
                       policy: ScanPolicy) -> tuple[bool, List[ScanResult], str]:
        """扫描Pod中的所有镜像"""
        all_results = []
        all_allowed = True
        total_vuln_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}

        for image in images:
            # 检查是否需要扫描此镜像
            if not policy_manager.should_scan_image(image, policy):
                logger.info(f"跳过镜像扫描（白名单）: {image}")
                metrics_manager.record_scan_skipped(namespace, "whitelist")
                continue

            # 执行扫描
            result = self.scan_image(image, policy, namespace)
            all_results.append(result)

            # 记录指标
            metrics_manager.record_scan_request(namespace, "success" if result.success else "failed")
            metrics_manager.record_scan_duration(namespace, result.scan_duration)

            # 合并漏洞统计
            for severity, count in result.vuln_counts.items():
                total_vuln_counts[severity] += count

            if not result.allowed:
                all_allowed = False

        # 记录漏洞统计
        metrics_manager.record_vulnerabilities(namespace, total_vuln_counts)

        # 生成汇总原因
        if all_allowed:
            reason = "所有镜像扫描通过"
        else:
            failed_images = [r.image for r in all_results if not r.allowed]
            reason = f"以下镜像存在安全问题: {', '.join(failed_images)}"

        return all_allowed, all_results, reason


scanner = TrivyScanner()
