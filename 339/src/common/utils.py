import json
import yaml
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config", "config.yaml"
        )
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def generate_user_id() -> str:
    return str(uuid.uuid4())

def generate_event_id() -> str:
    return hashlib.md5(f"{datetime.now().timestamp()}{uuid.uuid4()}".encode()).hexdigest()

def datetime_to_timestamp(dt: Optional[datetime] = None) -> float:
    if dt is None:
        dt = datetime.now()
    return dt.timestamp()

def timestamp_to_datetime(ts: float) -> datetime:
    return datetime.fromtimestamp(ts)

def days_between(dt1: datetime, dt2: datetime) -> int:
    return abs((dt1 - dt2).days)

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator

def parse_json_safe(json_str: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

def to_json_safe(obj: Any, indent: Optional[int] = None) -> str:
    def default_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)
    
    return json.dumps(obj, default=default_serializer, indent=indent, ensure_ascii=False)

def quantile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * q)
    idx = min(idx, len(sorted_vals) - 1)
    idx = max(idx, 0)
    return sorted_vals[idx]

def exponential_decay(value: float, days: int, decay_rate: float = 0.05) -> float:
    return value * (1 - decay_rate) ** days

def generate_time_windows(base_date: Optional[datetime] = None, 
                          windows: List[int] = None) -> Dict[str, Dict[str, datetime]]:
    if base_date is None:
        base_date = datetime.now()
    if windows is None:
        config = load_config()
        windows = config["features"]["time_window_days"]
    
    result = {}
    for days in windows:
        end_date = base_date
        start_date = end_date - timedelta(days=days)
        result[f"last_{days}d"] = {
            "start": start_date,
            "end": end_date
        }
    return result

def get_risk_level(probability: float, config: Optional[Dict] = None) -> str:
    if config is None:
        config = load_config()
    
    high_threshold = config["model"]["high_risk_threshold"]
    medium_threshold = config["model"]["medium_risk_threshold"]
    
    if probability >= high_threshold:
        return "high"
    elif probability >= medium_threshold:
        return "medium"
    else:
        return "low"
