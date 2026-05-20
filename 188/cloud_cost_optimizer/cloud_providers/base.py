from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class BillingRecord:
    provider: str
    account_id: str
    region: str
    service_name: str
    product_code: str
    resource_id: str
    usage_start_date: date
    usage_end_date: date
    usage_amount: float
    usage_unit: str
    pretax_amount: float
    currency: str
    tags: Dict[str, str] = field(default_factory=dict)
    instance_type: str = ""
    operating_system: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "account_id": self.account_id,
            "region": self.region,
            "service_name": self.service_name,
            "product_code": self.product_code,
            "resource_id": self.resource_id,
            "usage_start_date": self.usage_start_date.isoformat() if isinstance(self.usage_start_date, date) else self.usage_start_date,
            "usage_end_date": self.usage_end_date.isoformat() if isinstance(self.usage_end_date, date) else self.usage_end_date,
            "usage_amount": self.usage_amount,
            "usage_unit": self.usage_unit,
            "pretax_amount": self.pretax_amount,
            "currency": self.currency,
            "tags": self.tags,
            "instance_type": self.instance_type,
            "operating_system": self.operating_system,
        }


class CloudProvider(ABC):
    """云厂商基类"""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def fetch_billing_records(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "DAILY",
    ) -> List[BillingRecord]:
        pass

    @abstractmethod
    def get_resource_metrics(
        self,
        resource_id: str,
        service_name: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_resources(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        pass
