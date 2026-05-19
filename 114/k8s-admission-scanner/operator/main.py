#!/usr/bin/env python3
import asyncio
import logging
import os
from typing import Dict, List, Optional

import kopf
from prometheus_client import start_http_server

from .config import policy_manager
from .scanner import scanner
from .event_recorder import event_recorder
from .metrics import metrics_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 配置
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "9443"))
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))
FAIL_OPEN = os.getenv("FAIL_OPEN", "false").lower() == "true"


def extract_pod_images(pod: Dict) -> List[str]:
    """从Pod spec中提取所有镜像"""
    images = []
    spec = pod.get("spec", {})

    # 提取主容器镜像
    for container in spec.get("containers", []):
        if "image" in container:
            images.append(container["image"])

    # 提取初始化容器镜像
    for container in spec.get("initContainers", []):
        if "image" in container:
            images.append(container["image"])

    # 提取临时容器镜像
    for container in spec.get("ephemeralContainers", []):
        if "image" in container:
            images.append(container["image"])

    return list(set(images))  # 去重


# CRD处理: ImageScanPolicy 创建/更新
@kopf.on.create("security.trivy.io", "v1alpha1", "imagescanpolicies")
@kopf.on.update("security.trivy.io", "v1alpha1", "imagescanpolicies")
def handle_policy_change(name, spec, **kwargs):
    """处理扫描策略创建/更新"""
    logger.info(f"收到策略更新: {name}")
    policy_manager.update_policy(name, spec)


# CRD处理: ImageScanPolicy 删除
@kopf.on.delete("security.trivy.io", "v1alpha1", "imagescanpolicies")
def handle_policy_delete(name, **kwargs):
    """处理扫描策略删除"""
    logger.info(f"收到策略删除: {name}")
    policy_manager.remove_policy(name)


# Admission Webhook: Pod创建验证
@kopf.on.validate("pods", id="trivy-image-scan", operation="CREATE")
def validate_pod_create(name, namespace, body, **kwargs):
    """验证Pod创建 - 扫描镜像漏洞"""
    pod_name = name or "unknown"

    # 提取镜像
    images = extract_pod_images(body)
    if not images:
        logger.info(f"Pod {namespace}/{pod_name} 没有镜像需要扫描")
        return

    # 检查是否需要扫描
    policy = policy_manager.should_scan_pod(namespace, images)
    if not policy:
        logger.info(f"跳过Pod {namespace}/{pod_name} 的扫描（白名单）")
        event_recorder.record_scan_skipped(pod_name, namespace, "白名单策略")
        metrics_manager.record_scan_skipped(namespace, "whitelist")
        return

    logger.info(f"开始验证Pod {namespace}/{pod_name}, 镜像: {images}")
    event_recorder.record_scan_start(pod_name, namespace, images)

    # 执行扫描
    try:
        all_allowed, results, reason = scanner.scan_pod_images(
            images, namespace, policy
        )
    except Exception as e:
        error_msg = f"扫描异常: {str(e)}"
        logger.error(f"Pod {namespace}/{pod_name} {error_msg}")
        event_recorder.record_scan_error(pod_name, namespace, error_msg)

        if FAIL_OPEN:
            logger.warning(f"FAIL_OPEN模式: 允许Pod创建，尽管扫描失败")
            return
        else:
            raise kopf.PermanentError(error_msg)

    # 检查扫描结果
    if not all_allowed and not policy.dry_run:
        # 拒绝Pod创建
        event_recorder.record_scan_denied(pod_name, namespace, results, reason)
        metrics_manager.record_scan_denied(namespace, "vulnerabilities")

        # 生成拒绝消息
        critical_count = sum(r.vuln_counts.get("CRITICAL", 0) for r in results)
        high_count = sum(r.vuln_counts.get("HIGH", 0) for r in results)
        max_cvss = max([r.max_cvss for r in results], default=0.0)

        template = policy.remediation.comment_template
        if template:
            message = template.format(
                image=", ".join(images),
                critical_count=critical_count,
                high_count=high_count,
                max_cvss=max_cvss
            )
        else:
            message = (
                f"镜像安全扫描失败: {reason}. "
                f"发现 {critical_count} 个严重漏洞, {high_count} 个高危漏洞, "
                f"最高CVSS分数: {max_cvss}"
            )

        logger.warning(f"拒绝Pod {namespace}/{pod_name} 创建: {message}")
        raise kopf.AdmissionError(message, code=403)

    elif policy.dry_run and not all_allowed:
        # 试运行模式：只记录不拒绝
        logger.info(f"DryRun模式: Pod {namespace}/{pod_name} 本应被拒绝，但已通过")
        event_recorder.record_scan_denied(pod_name, namespace, results, reason, dry_run=True)
        metrics_manager.record_scan_denied(namespace, "dryrun")
    else:
        # 扫描通过
        event_recorder.record_scan_success(pod_name, namespace, results)
        metrics_manager.record_scan_allowed(namespace)
        logger.info(f"Pod {namespace}/{pod_name} 扫描通过")


# Admission Webhook: Pod更新验证
@kopf.on.validate("pods", id="trivy-image-scan-update", operation="UPDATE")
def validate_pod_update(name, namespace, old, new, **kwargs):
    """验证Pod更新 - 只在镜像变化时扫描"""
    pod_name = name or "unknown"

    old_images = extract_pod_images(old) if old else []
    new_images = extract_pod_images(new) if new else []

    # 检查是否有镜像变化
    changed_images = list(set(new_images) - set(old_images))
    if not changed_images:
        # 没有镜像变化，跳过扫描
        return

    logger.info(f"Pod {namespace}/{pod_name} 镜像变化，需要扫描新镜像: {changed_images}")

    # 检查是否需要扫描
    policy = policy_manager.should_scan_pod(namespace, changed_images)
    if not policy:
        logger.info(f"跳过Pod {namespace}/{pod_name} 的更新扫描（白名单）")
        return

    event_recorder.record_scan_start(pod_name, namespace, changed_images)

    # 执行扫描
    try:
        all_allowed, results, reason = scanner.scan_pod_images(
            changed_images, namespace, policy
        )
    except Exception as e:
        error_msg = f"扫描异常: {str(e)}"
        logger.error(f"Pod {namespace}/{pod_name} {error_msg}")
        event_recorder.record_scan_error(pod_name, namespace, error_msg)

        if FAIL_OPEN:
            return
        else:
            raise kopf.PermanentError(error_msg)

    if not all_allowed and not policy.dry_run:
        event_recorder.record_scan_denied(pod_name, namespace, results, reason)
        metrics_manager.record_scan_denied(namespace, "vulnerabilities")

        message = f"镜像更新被阻止: {reason}"
        logger.warning(f"拒绝Pod {namespace}/{pod_name} 更新: {message}")
        raise kopf.AdmissionError(message, code=403)
    elif policy.dry_run and not all_allowed:
        event_recorder.record_scan_denied(pod_name, namespace, results, reason, dry_run=True)
        metrics_manager.record_scan_denied(namespace, "dryrun")
        logger.info(f"DryRun模式: Pod {namespace}/{pod_name} 更新本应被拒绝")
    else:
        event_recorder.record_scan_success(pod_name, namespace, results)
        metrics_manager.record_scan_allowed(namespace)
        logger.info(f"Pod {namespace}/{pod_name} 更新扫描通过")


@kopf.on.startup()
def startup(settings: kopf.OperatorSettings, **kwargs):
    """Operator启动时的初始化"""
    logger.info("启动Trivy Admission Scanner Operator...")

    # 启动Prometheus指标服务器
    logger.info(f"启动Prometheus指标服务器，端口: {METRICS_PORT}")
    start_http_server(METRICS_PORT)

    # 配置webhook
    settings.admission.server = kopf.WebhookServer(
        addr="0.0.0.0",
        port=WEBHOOK_PORT,
        certfile="/run/secrets/tls/tls.crt",
        pkeyfile="/run/secrets/tls/tls.key"
    )

    logger.info("Operator初始化完成，开始监听事件...")


@kopf.on.cleanup()
def cleanup(**kwargs):
    """Operator关闭时的清理"""
    logger.info("正在关闭Trivy Admission Scanner Operator...")


def main():
    """主入口"""
    logger.info("=" * 60)
    logger.info("Trivy容器镜像准入扫描器")
    logger.info("=" * 60)
    logger.info(f"Webhook端口: {WEBHOOK_PORT}")
    logger.info(f"Metrics端口: {METRICS_PORT}")
    logger.info(f"Fail-open模式: {FAIL_OPEN}")
    logger.info("=" * 60)

    # 启动Operator
    kopf.run(
        standalone=True,
        namespace=None,  # 监听所有命名空间
        clusterwide=True
    )


if __name__ == "__main__":
    main()
