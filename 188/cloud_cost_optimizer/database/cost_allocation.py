import logging
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional

from ..cloud_providers import BillingRecord
from ..config import Settings

logger = logging.getLogger(__name__)


class CostAllocator:
    """费用分摊器 - 按标签/项目对费用进行分摊"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.label_keys = settings.label_keys

    def allocate_by_label(
        self,
        records: List[BillingRecord],
        label_key: str,
    ) -> List[Dict[str, Any]]:
        """按指定标签分摊费用"""
        allocations = defaultdict(lambda: {
            "label_value": "unknown",
            "total_cost": 0.0,
            "resource_count": 0,
            "services": defaultdict(float),
            "resources": set(),
        })

        for record in records:
            label_value = record.tags.get(label_key, "unknown")
            alloc = allocations[label_value]
            alloc["label_value"] = label_value
            alloc["total_cost"] += record.pretax_amount
            alloc["services"][record.service_name] += record.pretax_amount
            if record.resource_id:
                alloc["resources"].add(record.resource_id)
                alloc["resource_count"] = len(alloc["resources"])

        result = []
        for label_value, data in allocations.items():
            top_services = sorted(
                data["services"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            result.append({
                "allocation_date": date.today(),
                "provider": records[0].provider if records else "",
                "label_key": label_key,
                "label_value": label_value,
                "total_cost": data["total_cost"],
                "resource_count": data["resource_count"],
                "top_services": [
                    {"service_name": s[0], "cost": s[1]}
                    for s in top_services
                ],
            })

        return sorted(result, key=lambda x: x["total_cost"], reverse=True)

    def allocate_for_all_labels(
        self,
        records: List[BillingRecord],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """为所有配置的标签生成费用分摊"""
        results = {}
        for label_key in self.label_keys:
            results[label_key] = self.allocate_by_label(records, label_key)
        return results

    def generate_allocation_records(
        self,
        records: List[BillingRecord],
        label_key: str,
    ) -> List[Dict[str, Any]]:
        """生成用于存储的费用分摊记录"""
        service_allocations = defaultdict(lambda: defaultdict(float))
        resource_counts = defaultdict(lambda: defaultdict(set))

        for record in records:
            label_value = record.tags.get(label_key, "unknown")
            service_allocations[label_value][record.service_name] += record.pretax_amount
            if record.resource_id:
                resource_counts[label_value][record.service_name].add(record.resource_id)

        allocation_records = []
        for label_value, services in service_allocations.items():
            for service_name, total_cost in services.items():
                allocation_records.append({
                    "allocation_date": date.today(),
                    "provider": records[0].provider if records else "",
                    "label_key": label_key,
                    "label_value": label_value,
                    "service_name": service_name,
                    "total_cost": total_cost,
                    "resource_count": len(resource_counts[label_value][service_name]),
                })

        return allocation_records

    def get_unallocated_resources(
        self,
        records: List[BillingRecord],
    ) -> List[BillingRecord]:
        """获取没有标签的资源（未分摊的）"""
        unallocated = []
        for record in records:
            has_label = any(
                key in record.tags and record.tags[key]
                for key in self.label_keys
            )
            if not has_label:
                unallocated.append(record)
        return unallocated

    def get_unallocated_summary(
        self,
        records: List[BillingRecord],
    ) -> Dict[str, Any]:
        """获取未分摊资源的汇总信息"""
        unallocated = self.get_unallocated_resources(records)
        total_cost = sum(r.pretax_amount for r in unallocated)
        services = defaultdict(float)
        for r in unallocated:
            services[r.service_name] += r.pretax_amount

        return {
            "total_cost": total_cost,
            "resource_count": len(set(r.resource_id for r in unallocated if r.resource_id)),
            "record_count": len(unallocated),
            "services": sorted(
                services.items(),
                key=lambda x: x[1],
                reverse=True
            ),
        }
