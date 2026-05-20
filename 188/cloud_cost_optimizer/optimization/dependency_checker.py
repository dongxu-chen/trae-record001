import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ResourceDependency:
    """资源依赖关系"""
    resource_id: str
    resource_type: str
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    dependency_type: str = ""
    is_strong_dependency: bool = False
    notes: str = ""


@dataclass
class DependencyCheckResult:
    """依赖检查结果"""
    resource_id: str
    can_release: bool
    risk_level: str
    dependent_resources: List[str]
    dependent_services: List[str]
    warnings: List[str]
    suggestions: List[str]


class DependencyChecker:
    """资源依赖检查器 - 释放前检查关联资源状态"""

    # 资源依赖规则定义
    DEPENDENCY_RULES = {
        "compute_vm": {
            "strong_dependencies": [
                {"type": "storage_block", "description": "挂载的云硬盘/EBS", "check": "check_attached_volumes"},
                {"type": "network_loadbalancer", "description": "关联的负载均衡", "check": "check_load_balancers"},
                {"type": "database_nosql", "description": "关联的缓存/数据库", "check": "check_database_connections"},
            ],
            "soft_dependencies": [
                {"type": "network_vpc", "description": "所属VPC网络", "check": "check_vpc_membership"},
                {"type": "monitoring", "description": "关联的监控告警", "check": "check_monitoring_alerts"},
            ],
        },
        "database_relational": {
            "strong_dependencies": [
                {"type": "storage_block", "description": "关联的数据存储", "check": "check_storage_dependency"},
            ],
            "soft_dependencies": [
                {"type": "network_vpc", "description": "所属VPC网络", "check": "check_vpc_membership"},
            ],
        },
        "storage_object": {
            "strong_dependencies": [],
            "soft_dependencies": [
                {"type": "network_cdn", "description": "关联的CDN加速", "check": "check_cdn_origins"},
            ],
        },
        "network_loadbalancer": {
            "strong_dependencies": [],
            "soft_dependencies": [
                {"type": "compute_vm", "description": "后端服务器", "check": "check_backend_servers"},
            ],
        },
    }

    def __init__(self):
        self._resource_cache: Dict[str, Dict[str, Any]] = {}
        self._dependency_graph: Dict[str, ResourceDependency] = {}

    def analyze_resource_dependencies(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> ResourceDependency:
        """分析单个资源的依赖关系"""
        dependency = ResourceDependency(
            resource_id=resource_id,
            resource_type=resource_type,
        )

        if resource_type in self.DEPENDENCY_RULES:
            rules = self.DEPENDENCY_RULES[resource_type]

            for rule in rules.get("strong_dependencies", []):
                result = self._check_dependency(
                    resource_id, resource_type, rule, all_resources, billing_records
                )
                if result:
                    dependency.depends_on.extend(result)
                    dependency.is_strong_dependency = True

            for rule in rules.get("soft_dependencies", []):
                result = self._check_dependency(
                    resource_id, resource_type, rule, all_resources, billing_records
                )
                if result:
                    dependency.depends_on.extend(result)

        self._dependency_graph[resource_id] = dependency
        return dependency

    def _check_dependency(
        self,
        resource_id: str,
        resource_type: str,
        rule: Dict[str, Any],
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查特定类型的依赖"""
        check_method = getattr(self, rule["check"], None)
        if check_method:
            try:
                return check_method(resource_id, resource_type, all_resources, billing_records)
            except Exception as e:
                logger.error(f"Error checking dependency {rule['check']}: {e}")
        return []

    def check_attached_volumes(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查挂载的云硬盘"""
        dependencies = []

        if billing_records:
            for record in billing_records:
                if hasattr(record, 'resource_id') and record.resource_id:
                    if "disk" in record.service_name.lower() or "volume" in record.service_name.lower():
                        if hasattr(record, 'tags') and record.tags:
                            if any(
                                resource_id in str(v) for v in record.tags.values()
                            ):
                                dependencies.append(record.resource_id)

        return dependencies

    def check_load_balancers(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查关联的负载均衡"""
        dependencies = []

        if billing_records:
            lb_resources = [
                r for r in billing_records
                if "负载均衡" in r.service_name or "Load Balancing" in r.service_name
                or "CLB" in r.service_name or "SLB" in r.service_name
            ]

            for lb in lb_resources:
                if hasattr(lb, 'resource_id') and lb.resource_id:
                    dependencies.append(lb.resource_id)

        return dependencies

    def check_database_connections(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查数据库连接依赖"""
        dependencies = []

        if billing_records:
            db_resources = [
                r for r in billing_records
                if "数据库" in r.service_name or "Database" in r.service_name
                or "Redis" in r.service_name or "RDS" in r.service_name
            ]

            for db in db_resources:
                if hasattr(db, 'resource_id') and db.resource_id:
                    dependencies.append(db.resource_id)

        return dependencies

    def check_vpc_membership(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查VPC网络依赖"""
        dependencies = []

        if billing_records:
            vpc_resources = [
                r for r in billing_records
                if "VPC" in r.service_name or "专有网络" in r.service_name
            ]

            for vpc in vpc_resources:
                if hasattr(vpc, 'resource_id') and vpc.resource_id:
                    dependencies.append(vpc.resource_id)

        return dependencies

    def check_monitoring_alerts(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查监控告警依赖"""
        dependencies = []

        if billing_records:
            monitor_resources = [
                r for r in billing_records
                if "监控" in r.service_name or "CloudWatch" in r.service_name
                or "Monitor" in r.service_name
            ]

            for monitor in monitor_resources:
                if hasattr(monitor, 'resource_id') and monitor.resource_id:
                    dependencies.append(monitor.resource_id)

        return dependencies

    def check_cdn_origins(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查CDN源站依赖"""
        dependencies = []

        if billing_records:
            cdn_resources = [
                r for r in billing_records
                if "CDN" in r.service_name or "内容分发" in r.service_name
            ]

            for cdn in cdn_resources:
                if hasattr(cdn, 'resource_id') and cdn.resource_id:
                    dependencies.append(cdn.resource_id)

        return dependencies

    def check_backend_servers(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查负载均衡后端服务器"""
        dependencies = []

        if billing_records:
            vm_resources = [
                r for r in billing_records
                if "云服务器" in r.service_name or "EC2" in r.service_name
                or "CVM" in r.service_name
            ]

            for vm in vm_resources:
                if hasattr(vm, 'resource_id') and vm.resource_id:
                    dependencies.append(vm.resource_id)

        return dependencies

    def check_storage_dependency(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """检查存储依赖"""
        dependencies = []

        if billing_records:
            storage_resources = [
                r for r in billing_records
                if "存储" in r.service_name or "Storage" in r.service_name
                or "disk" in r.service_name.lower()
            ]

            for storage in storage_resources:
                if hasattr(storage, 'resource_id') and storage.resource_id:
                    dependencies.append(storage.resource_id)

        return dependencies

    def can_release_resource(
        self,
        resource_id: str,
        resource_type: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> DependencyCheckResult:
        """检查资源是否可以安全释放"""
        dependency = self.analyze_resource_dependencies(
            resource_id, resource_type, all_resources, billing_records
        )

        result = DependencyCheckResult(
            resource_id=resource_id,
            can_release=True,
            risk_level="low",
            dependent_resources=[],
            dependent_services=[],
            warnings=[],
            suggestions=[],
        )

        if dependency.is_strong_dependency:
            result.can_release = False
            result.risk_level = "high"
            result.warnings.append("存在强依赖资源，直接释放可能导致服务中断")
            result.suggestions.append("建议先检查并解除强依赖后再释放")

        if dependency.depends_on:
            result.dependent_resources = dependency.depends_on
            result.dependent_services = list(set(
                self._get_resource_type_from_id(r, all_resources, billing_records)
                for r in dependency.depends_on
            ))

        if not result.can_release:
            result.suggestions.append(
                f"资源 {resource_id} 依赖以下资源：{', '.join(dependency.depends_on)}"
            )

        return result

    def _get_resource_type_from_id(
        self,
        resource_id: str,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> str:
        """从资源ID推断资源类型"""
        if billing_records:
            for record in billing_records:
                if hasattr(record, 'resource_id') and record.resource_id == resource_id:
                    return record.service_name
        return "unknown"

    def get_dependency_graph(
        self,
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> Dict[str, ResourceDependency]:
        """获取所有资源的依赖图"""
        graph = {}

        if billing_records:
            for record in billing_records:
                if hasattr(record, 'resource_id') and record.resource_id:
                    resource_type = self._infer_resource_type(record.service_name)
                    if resource_type in self.DEPENDENCY_RULES:
                        dep = self.analyze_resource_dependencies(
                            record.resource_id, resource_type, all_resources, billing_records
                        )
                        graph[record.resource_id] = dep

        return graph

    def _infer_resource_type(self, service_name: str) -> str:
        """从服务名称推断资源类型"""
        type_mapping = {
            "compute_vm": ["ECS", "EC2", "CVM", "云服务器"],
            "database_relational": ["RDS", "CDB", "关系型数据库", "MySQL", "PostgreSQL"],
            "database_nosql": ["Redis", "MongoDB", "NoSQL", "缓存"],
            "storage_object": ["S3", "OSS", "COS", "对象存储"],
            "storage_block": ["disk", "EBS", "云盘", "块存储"],
            "network_loadbalancer": ["负载均衡", "CLB", "SLB", "ELB"],
            "network_cdn": ["CDN", "内容分发"],
            "network_vpc": ["VPC", "专有网络", "私有网络"],
        }

        for resource_type, keywords in type_mapping.items():
            for keyword in keywords:
                if keyword in service_name:
                    return resource_type
        return "other"

    def generate_release_plan(
        self,
        resource_ids: List[str],
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[Dict[str, Any]]:
        """生成资源释放计划"""
        plan = []

        for resource_id in resource_ids:
            resource_type = self._infer_resource_type(
                self._get_resource_type_from_id(resource_id, all_resources, billing_records)
            )
            check_result = self.can_release_resource(resource_id, resource_type, all_resources, billing_records)

            plan.append({
                "resource_id": resource_id,
                "resource_type": resource_type,
                "can_release": check_result.can_release,
                "risk_level": check_result.risk_level,
                "dependent_resources": check_result.dependent_resources,
                "warnings": check_result.warnings,
                "suggestions": check_result.suggestions,
                "release_order": 1 if check_result.can_release else 0,
            })

        plan.sort(key=lambda x: (not x["can_release"], x["risk_level"] == "high"))

        return plan

    def get_release_order(
        self,
        resource_ids: List[str],
        all_resources: List[Dict[str, Any]],
        billing_records: Optional[List[Any]],
    ) -> List[str]:
        """生成安全的资源释放顺序"""
        graph = self.get_dependency_graph(all_resources, billing_records)

        release_order = []
        visited = set()

        def visit(resource_id: str):
            if resource_id in visited:
                return
            visited.add(resource_id)

            if resource_id in graph:
                for dep in graph[resource_id].depends_on:
                    visit(dep)

            release_order.append(resource_id)

        for resource_id in resource_ids:
            visit(resource_id)

        return release_order
