from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict, deque
import math
import numpy as np
from .data_models import ClickLog, ClickFeatures


class FeatureExtractor:
    def __init__(self):
        self.ip_click_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.device_click_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.session_click_count: Dict[str, int] = defaultdict(int)
        self.ip_publishers: Dict[str, set] = defaultdict(set)
        self.ip_ads: Dict[str, set] = defaultdict(set)
        self.publisher_total_clicks: Dict[str, int] = defaultdict(int)
        self.ip_clicks_for_publisher: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def extract_features(self, click_log: ClickLog) -> ClickFeatures:
        timestamp = click_log.timestamp.timestamp()
        dt = click_log.timestamp

        features = ClickFeatures(
            click_id=click_log.click_id,
            timestamp=timestamp,
            hour_of_day=dt.hour,
            day_of_week=dt.weekday(),
            is_weekend=dt.weekday() >= 5
        )

        self._update_click_history(click_log.ip, click_log.device_id, timestamp, click_log.session_id)
        self._update_publisher_ad_tracking(click_log)

        features.ip_click_count_1min = self._count_clicks_in_window(self.ip_click_history[click_log.ip], 60)
        features.ip_click_count_5min = self._count_clicks_in_window(self.ip_click_history[click_log.ip], 300)
        features.ip_click_count_1h = self._count_clicks_in_window(self.ip_click_history[click_log.ip], 3600)

        features.device_click_count_1min = self._count_clicks_in_window(self.device_click_history[click_log.device_id], 60)
        features.device_click_count_5min = self._count_clicks_in_window(self.device_click_history[click_log.device_id], 300)
        features.device_click_count_1h = self._count_clicks_in_window(self.device_click_history[click_log.device_id], 3600)

        if click_log.session_id:
            features.session_click_count = self.session_click_count[click_log.session_id]

        features.time_since_last_click_ip = self._time_since_last_click(self.ip_click_history[click_log.ip], timestamp)
        features.time_since_last_click_device = self._time_since_last_click(self.device_click_history[click_log.device_id], timestamp)

        features.click_interval_std_ip = self._calculate_interval_std(self.ip_click_history[click_log.ip])
        features.click_interval_std_device = self._calculate_interval_std(self.device_click_history[click_log.device_id])

        features.unique_publishers_per_ip = len(self.ip_publishers[click_log.ip])
        features.unique_ads_per_ip = len(self.ip_ads[click_log.ip])

        features.ip_entropy = self._calculate_ip_entropy(click_log.ip)
        features.publisher_click_ratio = self._calculate_publisher_ratio(click_log)

        return features

    def _update_click_history(self, ip: str, device_id: str, timestamp: float, session_id: Optional[str]):
        self.ip_click_history[ip].append(timestamp)
        self.device_click_history[device_id].append(timestamp)
        if session_id:
            self.session_click_count[session_id] += 1

    def _update_publisher_ad_tracking(self, click_log: ClickLog):
        self.ip_publishers[click_log.ip].add(click_log.publisher_id)
        self.ip_ads[click_log.ip].add(click_log.ad_id)
        self.publisher_total_clicks[click_log.publisher_id] += 1
        self.ip_clicks_for_publisher[click_log.publisher_id][click_log.ip] += 1

    def _count_clicks_in_window(self, history: deque, window_seconds: int) -> int:
        if not history:
            return 0
        current_time = history[-1]
        count = 0
        for ts in reversed(history):
            if current_time - ts <= window_seconds:
                count += 1
            else:
                break
        return count

    def _time_since_last_click(self, history: deque, current_timestamp: float) -> float:
        if len(history) < 2:
            return 0.0
        return current_timestamp - history[-2]

    def _calculate_interval_std(self, history: deque) -> float:
        if len(history) < 3:
            return 0.0
        timestamps = list(history)[-20:]
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        return float(np.std(intervals)) if intervals else 0.0

    def _calculate_ip_entropy(self, ip: str) -> float:
        publisher_counts = list(self.ip_clicks_for_publisher.values())
        if not publisher_counts:
            return 0.0
        
        ip_counts = defaultdict(int)
        for pub_dict in publisher_counts:
            for ip_addr, count in pub_dict.items():
                ip_counts[ip_addr] += count
        
        total = sum(ip_counts.values())
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in ip_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy

    def _calculate_publisher_ratio(self, click_log: ClickLog) -> float:
        total_publisher_clicks = self.publisher_total_clicks[click_log.publisher_id]
        if total_publisher_clicks == 0:
            return 0.0
        ip_clicks_for_pub = self.ip_clicks_for_publisher[click_log.publisher_id][click_log.ip]
        return ip_clicks_for_pub / total_publisher_clicks

    def get_batch_features(self, click_logs: List[ClickLog]) -> List[ClickFeatures]:
        return [self.extract_features(log) for log in click_logs]

    def reset(self):
        self.ip_click_history.clear()
        self.device_click_history.clear()
        self.session_click_count.clear()
        self.ip_publishers.clear()
        self.ip_ads.clear()
        self.publisher_total_clicks.clear()
        self.ip_clicks_for_publisher.clear()
