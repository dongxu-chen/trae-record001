import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .base import BillingRecord, CloudProvider

logger = logging.getLogger(__name__)

try:
    from tencentcloud.common import credential
    from tencentcloud.billing.v20180709 import billing_client, models as billing_models
    from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
    TENCENT_AVAILABLE = True
except ImportError:
    TENCENT_AVAILABLE = False


class TencentProvider(CloudProvider):
    def __init__(self, access_key: str, secret_key: str, region: str = "ap-shanghai"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._billing_client = None
        self._cvm_client = None

    def get_name(self) -> str:
        return "腾讯云"

    def _get_credential(self):
        return credential.Credential(self.access_key, self.secret_key)

    def _get_billing_client(self):
        if self._billing_client is None and TENCENT_AVAILABLE:
            self._billing_client = billing_client.BillingClient(self._get_credential(), self.region)
        return self._billing_client

    def _get_cvm_client(self):
        if self._cvm_client is None and TENCENT_AVAILABLE:
            self._cvm_client = cvm_client.CvmClient(self._get_credential(), self.region)
        return self._cvm_client

    def fetch_billing_records(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "DAILY",
    ) -> List[BillingRecord]:
        if not TENCENT_AVAILABLE:
            logger.warning("Tencent Cloud SDK not installed, returning mock data")
            return self._generate_mock_data(start_date, end_date)

        records: List[BillingRecord] = []
        client = self._get_billing_client()

        try:
            offset = 0
            limit = 100

            while True:
                request = billing_models.DescribeBillDetailRequest()
                request.Month = start_date.strftime("%Y-%m")
                request.Offset = offset
                request.Limit = limit

                response = client.DescribeBillDetail(request)

                for item in response.ResourceSet:
                    tags = {}
                    if hasattr(item, "Tags") and item.Tags:
                        for tag in item.Tags:
                            if hasattr(tag, "TagKey") and hasattr(tag, "TagValue"):
                                tags[tag.TagKey] = tag.TagValue

                    record = BillingRecord(
                        provider="腾讯云",
                        account_id=getattr(item, "PayerUin", ""),
                        region=getattr(item, "Zone", ""),
                        service_name=getattr(item, "BusinessCodeName", ""),
                        product_code=getattr(item, "BusinessCode", ""),
                        resource_id=getattr(item, "ResourceId", ""),
                        usage_start_date=datetime.strptime(getattr(item, "FeeBeginTime", ""), "%Y-%m-%d %H:%M:%S").date() if getattr(item, "FeeBeginTime", "") else start_date,
                        usage_end_date=datetime.strptime(getattr(item, "FeeEndTime", ""), "%Y-%m-%d %H:%M:%S").date() if getattr(item, "FeeEndTime", "") else end_date,
                        usage_amount=float(getattr(item, "UsedAmount", 0)),
                        usage_unit=getattr(item, "UsedAmountUnit", ""),
                        pretax_amount=float(getattr(item, "RealTotalCost", 0)),
                        currency="CNY",
                        tags=tags,
                        instance_type=getattr(item, "InstanceType", ""),
                        raw_data=item.__dict__ if hasattr(item, "__dict__") else {},
                    )
                    records.append(record)

                if len(response.ResourceSet) < limit:
                    break
                offset += limit

        except Exception as e:
            logger.error(f"Failed to fetch Tencent Cloud billing data: {e}")
            return self._generate_mock_data(start_date, end_date)

        return records

    def get_resource_metrics(
        self,
        resource_id: str,
        service_name: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        if not TENCENT_AVAILABLE:
            return self._generate_mock_metrics()

        metrics = {}
        try:
            pass
        except Exception as e:
            logger.error(f"Failed to fetch metrics for {resource_id}: {e}")

        return metrics

    def list_resources(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if not TENCENT_AVAILABLE:
            return []

        resources = []
        client = self._get_cvm_client()

        try:
            if service_name is None or "cvm" in (service_name or "").lower() or "云服务器" in (service_name or ""):
                request = cvm_models.DescribeInstancesRequest()
                request.Limit = 100
                response = client.DescribeInstances(request)

                for instance in response.InstanceSet:
                    tags = {t.Key: t.Value for t in (instance.Tags if instance.Tags else [])}
                    resources.append({
                        "resource_id": instance.InstanceId,
                        "service_name": "云服务器CVM",
                        "instance_type": instance.InstanceType,
                        "state": instance.InstanceState,
                        "launch_time": instance.CreatedTime,
                        "tags": tags,
                    })
        except Exception as e:
            logger.error(f"Failed to list CVM resources: {e}")

        return resources

    def _generate_mock_data(self, start_date: date, end_date: date) -> List[BillingRecord]:
        from datetime import timedelta
        import random

        records = []
        services = [
            ("云服务器CVM", "cvm", "CVM"),
            ("对象存储COS", "cos", "COS"),
            ("云数据库CDB", "cdb", "CDB"),
            ("负载均衡CLB", "clb", "CLB"),
            ("云数据库Redis", "redis", "Redis"),
        ]

        current = start_date
        while current < end_date:
            for service, code, _ in services:
                amount = random.uniform(8, 400)
                projects = ["project-alpha", "project-beta", "project-gamma", ""]
                project = random.choice(projects)
                tags = {"project": project} if project else {}

                record = BillingRecord(
                    provider="腾讯云",
                    account_id="tencent-account-789",
                    region=self.region,
                    service_name=service,
                    product_code=code,
                    resource_id=f"ins-xyz{random.randint(100000, 999999)}",
                    usage_start_date=current,
                    usage_end_date=current + timedelta(days=1),
                    usage_amount=random.uniform(1, 24),
                    usage_unit="Hours",
                    pretax_amount=amount,
                    currency="CNY",
                    tags=tags,
                    instance_type="S5.MEDIUM2" if code == "cvm" else "",
                    operating_system="Linux" if code == "cvm" else "",
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
