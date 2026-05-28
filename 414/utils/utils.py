import hashlib
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


def setup_logging(config):
    log_level = getattr(logging, config.get("log_level", "INFO"))
    log_format = config.get("log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    log_file = config.get("log_file")
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        from logging.handlers import RotatingFileHandler
        max_bytes = config.get("max_log_size_mb", 100) * 1024 * 1024
        backup_count = config.get("backup_count", 5)
        handlers.append(RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        ))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


def generate_transaction_id():
    return hashlib.sha256(
        f"{uuid.uuid4().hex}{time.time_ns()}".encode()
    ).hexdigest()[:16]


def current_timestamp_ms():
    return int(time.time() * 1000)


def timestamp_to_datetime(ts_ms):
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)


def current_hour_utc():
    return datetime.now(timezone.utc).hour


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c


def normalize_features(features, scaler=None):
    features = np.array(features, dtype=np.float32)
    if features.ndim == 1:
        features = features.reshape(1, -1)
    if scaler is not None:
        return scaler.transform(features)
    return features


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def softmax(x):
    x_max = np.max(x, axis=-1, keepdims=True)
    e_x = np.exp(x - x_max)
    return e_x / np.sum(e_x, axis=-1, keepdims=True)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def safe_divide(numerator, denominator, default=0.0):
    if denominator == 0:
        return default
    return numerator / denominator


def exponential_moving_average(values, alpha=0.3):
    if not values:
        return 0.0
    ema = values[0]
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def percentile_rank(value, values_list):
    if not values_list:
        return 0.5
    sorted_vals = sorted(values_list)
    count = sum(1 for v in sorted_vals if v <= value)
    return count / len(sorted_vals)
