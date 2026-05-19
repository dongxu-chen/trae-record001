import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CloudProviderConfig:
    enabled: bool = False
    access_key: str = ""
    secret_key: str = ""
    region: str = "cn-hangzhou"
    account_id: str = ""


@dataclass
class ClickHouseConfig:
    host: str = "localhost"
    port: int = 8123
    user: str = "default"
    password: str = ""
    database: str = "cloud_cost"


@dataclass
class AnomalyDetectionConfig:
    threshold_std: float = 2.0
    min_percentage_change: float = 20.0
    min_days_for_baseline: int = 7


@dataclass
class OptimizationConfig:
    idle_cpu_threshold: float = 5.0
    idle_network_threshold: float = 1024.0
    ri_savings_threshold: float = 30.0


@dataclass
class Settings:
    clickhouse: ClickHouseConfig = field(default_factory=ClickHouseConfig)
    aws: CloudProviderConfig = field(default_factory=CloudProviderConfig)
    aliyun: CloudProviderConfig = field(default_factory=CloudProviderConfig)
    tencent: CloudProviderConfig = field(default_factory=CloudProviderConfig)
    anomaly_detection: AnomalyDetectionConfig = field(default_factory=AnomalyDetectionConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    label_keys: List[str] = field(default_factory=lambda: ["project", "team", "environment", "service"])
    currency: str = "CNY"

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls()
        settings.clickhouse.host = os.getenv("CLICKHOUSE_HOST", settings.clickhouse.host)
        settings.clickhouse.port = int(os.getenv("CLICKHOUSE_PORT", str(settings.clickhouse.port)))
        settings.clickhouse.user = os.getenv("CLICKHOUSE_USER", settings.clickhouse.user)
        settings.clickhouse.password = os.getenv("CLICKHOUSE_PASSWORD", settings.clickhouse.password)
        settings.clickhouse.database = os.getenv("CLICKHOUSE_DB", settings.clickhouse.database)

        settings.aws.enabled = os.getenv("AWS_ENABLED", "false").lower() == "true"
        settings.aws.access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        settings.aws.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        settings.aws.region = os.getenv("AWS_REGION", "us-east-1")

        settings.aliyun.enabled = os.getenv("ALIBABA_ENABLED", "false").lower() == "true"
        settings.aliyun.access_key = os.getenv("ALIBABA_ACCESS_KEY_ID", "")
        settings.aliyun.secret_key = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "")
        settings.aliyun.region = os.getenv("ALIBABA_REGION", "cn-hangzhou")

        settings.tencent.enabled = os.getenv("TENCENT_ENABLED", "false").lower() == "true"
        settings.tencent.access_key = os.getenv("TENCENT_SECRET_ID", "")
        settings.tencent.secret_key = os.getenv("TENCENT_SECRET_KEY", "")
        settings.tencent.region = os.getenv("TENCENT_REGION", "ap-shanghai")

        return settings
