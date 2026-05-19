import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from .base import BillingRecord, CloudProvider

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class AWSProvider(CloudProvider):
    def __init__(self, access_key: str, secret_key: str, region: str = "us-east-1"):
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self._ce_client = None
        self._ec2_client = None
        self._cw_client = None

    def get_name(self) -> str:
        return "AWS"

    def _get_ce_client(self):
        if self._ce_client is None and BOTO3_AVAILABLE:
            self._ce_client = boto3.client(
                "ce",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        return self._ce_client

    def _get_ec2_client(self):
        if self._ec2_client is None and BOTO3_AVAILABLE:
            self._ec2_client = boto3.client(
                "ec2",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        return self._ec2_client

    def _get_cw_client(self):
        if self._cw_client is None and BOTO3_AVAILABLE:
            self._cw_client = boto3.client(
                "cloudwatch",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
        return self._cw_client

    def fetch_billing_records(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "DAILY",
    ) -> List[BillingRecord]:
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not installed, returning mock data")
            return self._generate_mock_data(start_date, end_date)

        records: List[BillingRecord] = []
        ce_client = self._get_ce_client()

        try:
            response = ce_client.get_cost_and_usage(
                TimePeriod={
                    "Start": start_date.isoformat(),
                    "End": end_date.isoformat(),
                },
                Granularity=granularity,
                Metrics=["UnblendedCost", "UsageQuantity"],
                GroupBy=[
                    {"Type": "DIMENSION", "Key": "SERVICE"},
                    {"Type": "DIMENSION", "Key": "USAGE_TYPE"},
                    {"Type": "DIMENSION", "Key": "RESOURCE_ID"},
                    {"Type": "TAG", "Key": "Project"},
                ],
            )

            for result in response.get("ResultsByTime", []):
                for group in result.get("Groups", []):
                    keys = group.get("Keys", [])
                    metrics = group.get("Metrics", {})
                    amount = float(metrics.get("UnblendedCost", {}).get("Amount", 0))
                    usage = float(metrics.get("UsageQuantity", {}).get("Amount", 0))

                    tags = {}
                    for key in keys:
                        if key.startswith("Project$"):
                            tags["project"] = key.split("$", 1)[1]

                    record = BillingRecord(
                        provider="AWS",
                        account_id="",
                        region=self.region,
                        service_name=keys[0] if len(keys) > 0 else "",
                        product_code=keys[1] if len(keys) > 1 else "",
                        resource_id=keys[2] if len(keys) > 2 else "",
                        usage_start_date=datetime.strptime(result["TimePeriod"]["Start"], "%Y-%m-%d").date(),
                        usage_end_date=datetime.strptime(result["TimePeriod"]["End"], "%Y-%m-%d").date(),
                        usage_amount=usage,
                        usage_unit="",
                        pretax_amount=amount,
                        currency="USD",
                        tags=tags,
                        raw_data=group,
                    )
                    records.append(record)

        except ClientError as e:
            logger.error(f"Failed to fetch AWS billing data: {e}")
            return self._generate_mock_data(start_date, end_date)

        return records

    def get_resource_metrics(
        self,
        resource_id: str,
        service_name: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        if not BOTO3_AVAILABLE:
            return self._generate_mock_metrics()

        cw_client = self._get_cw_client()
        metrics = {}

        try:
            namespace = "AWS/EC2" if "EC2" in service_name else "AWS/S3"
            response = cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": resource_id}],
                StartTime=datetime.combine(start_date, datetime.min.time()),
                EndTime=datetime.combine(end_date, datetime.max.time()),
                Period=86400,
                Statistics=["Average", "Maximum"],
            )

            datapoints = response.get("Datapoints", [])
            if datapoints:
                avg_cpu = sum(d["Average"] for d in datapoints) / len(datapoints)
                max_cpu = max(d["Maximum"] for d in datapoints)
                metrics["avg_cpu_utilization"] = avg_cpu
                metrics["max_cpu_utilization"] = max_cpu

        except ClientError as e:
            logger.error(f"Failed to fetch metrics for {resource_id}: {e}")

        return metrics

    def list_resources(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        if not BOTO3_AVAILABLE:
            return []

        resources = []
        ec2_client = self._get_ec2_client()

        try:
            if service_name is None or "EC2" in service_name:
                response = ec2_client.describe_instances()
                for reservation in response.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
                        resources.append({
                            "resource_id": instance["InstanceId"],
                            "service_name": "Amazon Elastic Compute Cloud - Compute",
                            "instance_type": instance["InstanceType"],
                            "state": instance["State"]["Name"],
                            "launch_time": instance["LaunchTime"].isoformat(),
                            "tags": tags,
                        })
        except ClientError as e:
            logger.error(f"Failed to list EC2 resources: {e}")

        return resources

    def _generate_mock_data(self, start_date: date, end_date: date) -> List[BillingRecord]:
        from datetime import timedelta
        import random

        records = []
        services = [
            ("Amazon Elastic Compute Cloud - Compute", "BoxUsage", "EC2"),
            ("Amazon Simple Storage Service", "Storage", "S3"),
            ("Amazon Relational Database Service", "db.t3.micro", "RDS"),
            ("Amazon Elastic Load Balancing", "LoadBalancing", "ELB"),
        ]

        current = start_date
        while current < end_date:
            for service, usage_type, code in services:
                amount = random.uniform(5, 200)
                projects = ["project-alpha", "project-beta", "project-gamma", ""]
                project = random.choice(projects)
                tags = {"project": project} if project else {}

                record = BillingRecord(
                    provider="AWS",
                    account_id="aws-account-123",
                    region=self.region,
                    service_name=service,
                    product_code=usage_type,
                    resource_id=f"i-{random.randint(100000, 999999)}",
                    usage_start_date=current,
                    usage_end_date=current + timedelta(days=1),
                    usage_amount=random.uniform(1, 24),
                    usage_unit="Hours",
                    pretax_amount=amount,
                    currency="USD",
                    tags=tags,
                    instance_type="t3.medium" if code == "EC2" else "",
                    operating_system="Linux" if code == "EC2" else "",
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
