#!/usr/bin/env python3
import logging
from datetime import datetime
from typing import List

import kopf

from .scanner import ScanResult

logger = logging.getLogger(__name__)


class EventRecorder:
    """K8s事件记录器"""

    @staticmethod
    def record_scan_start(pod_name: str, namespace: str, images: List[str]):
        """记录扫描开始事件"""
        try:
            kopf.event(
                type="Normal",
                reason="ImageScanStarted",
                message=f"开始扫描镜像: {', '.join(images)}",
                obj={
                    "metadata": {
                        "name": pod_name,
                        "namespace": namespace
                    }
                }
            )
        except Exception as e:
            logger.warning(f"记录扫描开始事件失败: {e}")

    @staticmethod
    def record_scan_success(pod_name: str, namespace: str, results: List[ScanResult]):
        """记录扫描成功事件"""
        try:
            total_vulns = sum(len(r.vulnerabilities) for r in results)
            critical_count = sum(r.vuln_counts.get("CRITICAL", 0) for r in results)
            high_count = sum(r.vuln_counts.get("HIGH", 0) for r in results)

            message = (
                f"镜像扫描通过: 共发现 {total_vulns} 个漏洞 "
                f"(CRITICAL: {critical_count}, HIGH: {high_count})"
            )

            kopf.event(
                type="Normal",
                reason="ImageScanPassed",
                message=message,
                obj={
                    "metadata": {
                        "name": pod_name,
                        "namespace": namespace
                    }
                }
            )
        except Exception as e:
            logger.warning(f"记录扫描成功事件失败: {e}")

    @staticmethod
    def record_scan_denied(pod_name: str, namespace: str, results: List[ScanResult],
                          reason: str, dry_run: bool = False):
        """记录扫描拒绝事件"""
        try:
            # 汇总漏洞信息
            critical_count = sum(r.vuln_counts.get("CRITICAL", 0) for r in results)
            high_count = sum(r.vuln_counts.get("HIGH", 0) for r in results)
            medium_count = sum(r.vuln_counts.get("MEDIUM", 0) for r in results)
            max_cvss = max([r.max_cvss for r in results], default=0.0)

            dry_run_prefix = "[DryRun] " if dry_run else ""

            message = (
                f"{dry_run_prefix}镜像扫描拒绝: {reason}. "
                f"漏洞统计 - CRITICAL: {critical_count}, HIGH: {high_count}, "
                f"MEDIUM: {medium_count}, MAX_CVSS: {max_cvss}"
            )

            kopf.event(
                type="Warning",
                reason="ImageScanDenied",
                message=message,
                obj={
                    "metadata": {
                        "name": pod_name,
                        "namespace": namespace
                    }
                }
            )
        except Exception as e:
            logger.warning(f"记录扫描拒绝事件失败: {e}")

    @staticmethod
    def record_scan_error(pod_name: str, namespace: str, error: str):
        """记录扫描错误事件"""
        try:
            kopf.event(
                type="Warning",
                reason="ImageScanFailed",
                message=f"镜像扫描失败: {error}",
                obj={
                    "metadata": {
                        "name": pod_name,
                        "namespace": namespace
                    }
                }
            )
        except Exception as e:
            logger.warning(f"记录扫描错误事件失败: {e}")

    @staticmethod
    def record_scan_skipped(pod_name: str, namespace: str, reason: str):
        """记录跳过扫描事件"""
        try:
            kopf.event(
                type="Normal",
                reason="ImageScanSkipped",
                message=f"镜像扫描跳过: {reason}",
                obj={
                    "metadata": {
                        "name": pod_name,
                        "namespace": namespace
                    }
                }
            )
        except Exception as e:
            logger.warning(f"记录跳过扫描事件失败: {e}")


event_recorder = EventRecorder()
