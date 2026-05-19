#!/usr/bin/env python3
import fnmatch
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SeverityThreshold:
    critical: int = 0
    high: int = 2
    medium: int = 10
    low: int = 50
    cvss_score_threshold: float = 7.0


@dataclass
class NamespaceSelector:
    include: List[str] = field(default_factory=lambda: ["*"])
    exclude: List[str] = field(default_factory=lambda: [
        "kube-system",
        "kube-public",
        "kube-node-lease"
    ])


@dataclass
class ImageFilter:
    include: List[str] = field(default_factory=lambda: ["*"])
    exclude: List[str] = field(default_factory=lambda: [
        "registry.k8s.io/*"
    ])


@dataclass
class RemediationConfig:
    auto_remediate: bool = False
    comment_template: str = "镜像 {image} 存在 {count} 个高危漏洞，请升级镜像"


@dataclass
class ScanPolicy:
    name: str = "default"
    enabled: bool = True
    namespace_selector: NamespaceSelector = field(default_factory=NamespaceSelector)
    severity_threshold: SeverityThreshold = field(default_factory=SeverityThreshold)
    scan_timeout: int = 120
    image_filter: ImageFilter = field(default_factory=ImageFilter)
    remediation: RemediationConfig = field(default_factory=RemediationConfig)
    dry_run: bool = False


class PolicyManager:
    def __init__(self):
        self._policies: Dict[str, ScanPolicy] = {}
        self._default_policy = ScanPolicy()

    def update_policy(self, name: str, spec: Dict):
        """从CRD spec更新策略配置"""
        namespace_spec = spec.get("namespaceSelector", {})
        severity_spec = spec.get("severityThreshold", {})
        image_spec = spec.get("imageFilter", {})
        remediation_spec = spec.get("remediation", {})

        policy = ScanPolicy(
            name=name,
            enabled=spec.get("enabled", True),
            namespace_selector=NamespaceSelector(
                include=namespace_spec.get("include", ["*"]),
                exclude=namespace_spec.get("exclude", [])
            ),
            severity_threshold=SeverityThreshold(
                critical=severity_spec.get("critical", 0),
                high=severity_spec.get("high", 2),
                medium=severity_spec.get("medium", 10),
                low=severity_spec.get("low", 50),
                cvss_score_threshold=severity_spec.get("cvssScoreThreshold", 7.0)
            ),
            scan_timeout=spec.get("scanTimeout", 120),
            image_filter=ImageFilter(
                include=image_spec.get("include", ["*"]),
                exclude=image_spec.get("exclude", [])
            ),
            remediation=RemediationConfig(
                auto_remediate=remediation_spec.get("autoRemediate", False),
                comment_template=remediation_spec.get("commentTemplate", "")
            ),
            dry_run=spec.get("dryRun", False)
        )

        self._policies[name] = policy
        logger.info(f"已更新扫描策略: {name}")

    def remove_policy(self, name: str):
        """移除策略"""
        if name in self._policies:
            del self._policies[name]
            logger.info(f"已移除扫描策略: {name}")

    def get_effective_policy(self, namespace: str = None) -> ScanPolicy:
        """获取有效的扫描策略"""
        if not self._policies:
            return self._default_policy

        for policy in self._policies.values():
            if policy.enabled:
                if namespace and not self._should_scan_namespace(namespace, policy.namespace_selector):
                    continue
                return policy

        return self._default_policy

    def _should_scan_namespace(self, namespace: str, selector: NamespaceSelector) -> bool:
        """判断命名空间是否需要扫描"""
        for pattern in selector.exclude:
            if fnmatch.fnmatch(namespace, pattern):
                return False

        for pattern in selector.include:
            if fnmatch.fnmatch(namespace, pattern):
                return True

        return False

    def should_scan_image(self, image: str, policy: ScanPolicy) -> bool:
        """判断镜像是否需要扫描"""
        for pattern in policy.image_filter.exclude:
            if fnmatch.fnmatch(image, pattern):
                return False

        for pattern in policy.image_filter.include:
            if fnmatch.fnmatch(image, pattern):
                return True

        return False

    def should_scan_pod(self, namespace: str, images: List[str]) -> Optional[ScanPolicy]:
        """判断Pod是否需要扫描，返回使用的策略"""
        policy = self.get_effective_policy(namespace)

        if not policy.enabled:
            return None

        if not self._should_scan_namespace(namespace, policy.namespace_selector):
            return None

        for image in images:
            if self.should_scan_image(image, policy):
                return policy

        return None


policy_manager = PolicyManager()
