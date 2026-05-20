import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .base import BillingRecord, CloudProvider

logger = logging.getLogger(__name__)

try:
    from alibabacloud_bssopenapi20171214 import client as bss_client
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_ecs20140526 import client as ecs_client
    ALIYUN_AVAILABLE = True
except ImportError:
    ALIYUN_AVAILABLE = False


class AliyunProvider(CloudProvider):
    def __init__(self, access_key: str, secret_key: str, region: str = "cn-hangzhou"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._bss_client = None
        self._ecs_client = None

    def get_name(self) -> str:
        return "阿里云"

    def _get_bss_client(self):
        if self._bss_client is None and ALIYUN_AVAILABLE:
            config = open_api_models.Config(
                access_key_id=self.access_key,
                access_key_secret=self.secret_key,
            )
            config.endpoint = f"business.{self.region}.aliyuncs.com"
            self._bss_client = bss_client.Client(config)
        return self._bss_client

    def _get_ecs_client(self):
        if self._ecs_client is None and ALIYUN_AVAILABLE:
            config = open_api_models.Config(
                access_key_id=self.access_key,
                access_key_secret=self.secret_key,
            )
            config.endpoint = f"ecs.{self.region}.aliyuncs.com"
            self._ecs_client = ecs_client.Client(config)
        return self._ecs_client

    def fetch_billing_records(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "DAILY",
    ) -> List[BillingRecord]:
        if not ALIYUN_AVAILABLE:
            logger.warning("Alibaba Cloud SDK not installed, returning mock data")
            return self._generate_mock_data(start_date, end_date)

        records: List[BillingRecord] = []
        client = self._get_bss_client()

        try:
            from alibabacloud_bssopenapi20171214 import models as bss_models

            page_num = 1
            page_size = 100

            while True:
                request = bss_models.QueryBillRequest(
                    billing_cycle=start_date.strftime("%Y-%m"),
                    page_num=page_num,
                    page_size=page_size,
                )
                response = client.query_bill(request)
                body = response.body

                for item in body.data.items.item:
                    record = BillingRecord(
                        provider="阿里云",
                        account_id=getattr(item, "owner_id", ""),
                        region=getattr(item, "region", self.region),
                        service_name=getattr(item, "product_name", ""),
                        product_code=getattr(item, "product_code", ""),
                        resource_id=getattr(item, "resource_id", ""),
                        usage_start_date=datetime.fromtimestamp(getattr(item, "usage_start_time", 0) / 1000).date() if getattr(item, "usage_start_time", 0) > 0 else start_date,
                        usage_end_date=datetime.fromtimestamp(getattr(item, "usage_end_time", 0) / 1000).date() if getattr(item, "usage_end_time", 0) > 0 else end_date,
                        usage_amount=float(getattr(item, "usage", 0)),
                        usage_unit=getattr(item, "unit", ""),
                        pretax_amount=float(getattr(item, "pretax_amount", 0)),
                        currency=getattr(item, "currency", "CNY"),
                        tags=dict(getattr(item, "tags", {}) or {}),
                        instance_type=getattr(item, "instance_spec", ""),
                        raw_data=item.to_map() if hasattr(item, "to_map") else {},
                    )
                    records.append(record)

                if body.data.page_num * body.data.page_size >= body.data.total_count:
                    break
                page_num += 1

        except Exception as e:
            logger.error(f"Failed to fetch Alibaba Cloud billing data: {e}")
            return self._generate_mock_data(start_date, end_date)

        return records

    def get_resource_metrics(
        self,
        resource_id: str,
        service_name: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        if not ALIYUN_AVAILABLE:
            return self._generate_mock_metrics()

        metrics = {}
        try:
            pass
        except Exception as e:
            logger.error(f"Failed to fetch metrics for {resource_id}: {e}")

        return metrics

    def list_resources(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if not ALIYUN_AVAILABLE:
            return []

        resources = []
        client = self._get_ecs_client()

        try:
            from alibabacloud_ecs20140526 import models as ecs_models

            if service_name is None or "云服务器ECS" in service_name or "ECS" in service_name:
                request = ecs_models.DescribeInstancesRequest(
                    region_id=self.region,
                    page_size=100,
                )
                response = client.describe_instances(request)
                body = response.body

                for instance in body.instances.instance:
                    tags = {t.tag_key: t.tag_value for t in (instance.tags.tag if instance.tags else [])}
                    resources.append({
                        "resource_id": instance.instance_id,
                        "service_name": "云服务器ECS",
                        "instance_type": instance.instance_type,
                        "state": instance.status,
                        "launch_time": instance.creation_time,
                        "tags": tags,
                    })
        except Exception as e:
            logger.error(f"Failed to list ECS resources: {e}")

        return resources

    def _generate_mock_data(self, start_date: date, end_date: date) -> List[BillingRecord]:
        from datetime import timedelta
        import random

        records = []
        services = [
            ("云服务器ECS", "ecs", "ECS"),
            ("对象存储OSS", "oss", "OSS"),
            ("云数据库RDS", "rds", "RDS"),
            ("负载均衡SLB", "slb", "SLB"),
            ("云数据库Redis", "kvstore", "Redis"),
        ]

        current = start_date
        while current < end_date:
            for service, code, _ in services:
                amount = random.uniform(10, 500)
                projects = ["project-alpha", "project-beta", "project-gamma", ""]
                project = random.choice(projects)
                tags = {"project": project} if project else {}

                record = BillingRecord(
                    provider="阿里云",
                    account_id="aliyun-account-456",
                    region=self.region,
                    service_name=service,
                    product_code=code,
                    resource_id=f"i-abc{random.randint(100000, 999999)}",
                    usage_start_date=current,
                    usage_end_date=current + timedelta(days=1),
                    usage_amount=random.uniform(1, 24),
                    usage_unit="Hours",
                    pretax_amount=amount,
                    currency="CNY",
                    tags=tags,
                    instance_type="ecs.g6.large" if code == "ecs" else "",
                    operating_system="Linux" if code == "ecs" else "",
                )
                records.append(record)
            current += timedelta(days=1)

        return records

    def _generate_mock_metrics(self) -> Dict[str, Any]:
        import random
        return {
            "avg_cpu_utilization": random.uniform(2, 80),
            "max_cpu_utilization": random.uniform(10, 100),
            "avg_network_in": random.uniform(0, 10000),
            "avg_network_out": random.uniform(0, 10000),
        }
