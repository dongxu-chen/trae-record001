from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json
import hashlib


@dataclass
class ClickLog:
    click_id: str
    timestamp: datetime
    ip: str
    device_id: str
    user_agent: str
    publisher_id: str
    campaign_id: str
    ad_id: str
    referrer: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_mobile: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClickLog':
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp)
        
        return cls(
            click_id=data.get('click_id', cls._generate_id()),
            timestamp=timestamp,
            ip=data.get('ip', ''),
            device_id=data.get('device_id', ''),
            user_agent=data.get('user_agent', ''),
            publisher_id=data.get('publisher_id', ''),
            campaign_id=data.get('campaign_id', ''),
            ad_id=data.get('ad_id', ''),
            referrer=data.get('referrer', ''),
            session_id=data.get('session_id'),
            user_id=data.get('user_id'),
            country=data.get('country'),
            city=data.get('city'),
            is_mobile=data.get('is_mobile', False),
            extra=data.get('extra', {})
        )

    @staticmethod
    def _generate_id() -> str:
        return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'click_id': self.click_id,
            'timestamp': self.timestamp.isoformat(),
            'ip': self.ip,
            'device_id': self.device_id,
            'user_agent': self.user_agent,
            'publisher_id': self.publisher_id,
            'campaign_id': self.campaign_id,
            'ad_id': self.ad_id,
            'referrer': self.referrer,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'country': self.country,
            'city': self.city,
            'is_mobile': self.is_mobile,
            'extra': self.extra
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class ClickFeatures:
    click_id: str
    timestamp: float
    ip_click_count_1min: int = 0
    ip_click_count_5min: int = 0
    ip_click_count_1h: int = 0
    device_click_count_1min: int = 0
    device_click_count_5min: int = 0
    device_click_count_1h: int = 0
    session_click_count: int = 0
    time_since_last_click_ip: float = 0.0
    time_since_last_click_device: float = 0.0
    click_interval_std_ip: float = 0.0
    click_interval_std_device: float = 0.0
    unique_publishers_per_ip: int = 0
    unique_ads_per_ip: int = 0
    hour_of_day: int = 0
    day_of_week: int = 0
    is_weekend: bool = False
    ip_entropy: float = 0.0
    publisher_click_ratio: float = 0.0

    def to_feature_vector(self) -> list:
        return [
            self.ip_click_count_1min,
            self.ip_click_count_5min,
            self.ip_click_count_1h,
            self.device_click_count_1min,
            self.device_click_count_5min,
            self.device_click_count_1h,
            self.session_click_count,
            self.time_since_last_click_ip,
            self.time_since_last_click_device,
            self.click_interval_std_ip,
            self.click_interval_std_device,
            self.unique_publishers_per_ip,
            self.unique_ads_per_ip,
            self.hour_of_day,
            self.day_of_week,
            1 if self.is_weekend else 0,
            self.ip_entropy,
            self.publisher_click_ratio
        ]

    def get_feature_names(self) -> list:
        return [
            'ip_click_count_1min',
            'ip_click_count_5min',
            'ip_click_count_1h',
            'device_click_count_1min',
            'device_click_count_5min',
            'device_click_count_1h',
            'session_click_count',
            'time_since_last_click_ip',
            'time_since_last_click_device',
            'click_interval_std_ip',
            'click_interval_std_device',
            'unique_publishers_per_ip',
            'unique_ads_per_ip',
            'hour_of_day',
            'day_of_week',
            'is_weekend',
            'ip_entropy',
            'publisher_click_ratio'
        ]
