import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import yaml


class PublisherThresholdManager:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.threshold_config = self.config.get('model', {}).get('dynamic_threshold', {})
        self.publisher_config = self.config.get('publisher_thresholds', {})
        
        self.enabled = self.threshold_config.get('enabled', True)
        self.per_publisher = self.threshold_config.get('per_publisher', True)
        self.update_interval = self.threshold_config.get('update_interval_seconds', 3600)
        self.min_samples = self.threshold_config.get('min_samples', 100)
        self.percentile = self.threshold_config.get('percentile', 95)
        self.default_threshold = self.threshold_config.get('default_threshold', 0.7)
        
        self.publisher_scores: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.publisher_thresholds: Dict[str, float] = {}
        self.last_update_time: Dict[str, float] = {}
        self.publisher_stats: Dict[str, Dict] = defaultdict(dict)
        
        self._load_static_thresholds()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_static_thresholds(self):
        default_config = self.publisher_config.get('default', {})
        self.default_threshold = default_config.get('fraud_threshold', self.default_threshold)
        
        overrides = self.publisher_config.get('overrides', {})
        for publisher_id, config in overrides.items():
            if 'fraud_threshold' in config:
                self.publisher_thresholds[publisher_id] = config['fraud_threshold']

    def record_score(self, publisher_id: str, fraud_score: float):
        if not self.enabled or not self.per_publisher:
            return
        
        self.publisher_scores[publisher_id].append(fraud_score)
        
        now = time.time()
        last_update = self.last_update_time.get(publisher_id, 0)
        if now - last_update >= self.update_interval:
            self._update_threshold(publisher_id)

    def _update_threshold(self, publisher_id: str):
        scores = list(self.publisher_scores[publisher_id])
        
        if len(scores) < self.min_samples:
            return
        
        scores_array = np.array(scores)
        dynamic_threshold = np.percentile(scores_array, self.percentile)
        
        static_threshold = self._get_static_threshold(publisher_id)
        
        alpha = 0.7
        final_threshold = alpha * dynamic_threshold + (1 - alpha) * static_threshold
        final_threshold = max(0.5, min(0.95, final_threshold))
        
        self.publisher_thresholds[publisher_id] = final_threshold
        self.last_update_time[publisher_id] = time.time()
        
        self.publisher_stats[publisher_id] = {
            'sample_count': len(scores),
            'mean_score': float(np.mean(scores_array)),
            'std_score': float(np.std(scores_array)),
            'dynamic_threshold': float(dynamic_threshold),
            'static_threshold': float(static_threshold),
            'final_threshold': float(final_threshold),
            'last_updated': self.last_update_time[publisher_id]
        }

    def _get_static_threshold(self, publisher_id: str) -> float:
        overrides = self.publisher_config.get('overrides', {})
        if publisher_id in overrides:
            return overrides[publisher_id].get('fraud_threshold', self.default_threshold)
        return self.default_threshold

    def get_threshold(self, publisher_id: str) -> float:
        if not self.enabled:
            return self.default_threshold
        
        if publisher_id in self.publisher_thresholds:
            return self.publisher_thresholds[publisher_id]
        
        return self._get_static_threshold(publisher_id)

    def is_fraud(self, publisher_id: str, fraud_score: float) -> Tuple[bool, float]:
        threshold = self.get_threshold(publisher_id)
        return fraud_score >= threshold, threshold

    def get_publisher_stats(self, publisher_id: str) -> Dict:
        return self.publisher_stats.get(publisher_id, {
            'sample_count': len(self.publisher_scores.get(publisher_id, [])),
            'threshold': self.get_threshold(publisher_id)
        })

    def get_all_publisher_stats(self) -> Dict[str, Dict]:
        result = {}
        for publisher_id in set(list(self.publisher_thresholds.keys()) + 
                               list(self.publisher_config.get('overrides', {}).keys())):
            result[publisher_id] = self.get_publisher_stats(publisher_id)
        return result

    def force_update_all(self):
        for publisher_id in list(self.publisher_scores.keys()):
            self._update_threshold(publisher_id)

    def reset_publisher(self, publisher_id: str):
        if publisher_id in self.publisher_scores:
            self.publisher_scores[publisher_id].clear()
        if publisher_id in self.publisher_thresholds:
            del self.publisher_thresholds[publisher_id]
        if publisher_id in self.last_update_time:
            del self.last_update_time[publisher_id]
        if publisher_id in self.publisher_stats:
            del self.publisher_stats[publisher_id]


class PublisherLimitManager:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.publisher_config = self.config.get('publisher_thresholds', {})

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_high_freq_ip_limit(self, publisher_id: str) -> int:
        overrides = self.publisher_config.get('overrides', {})
        if publisher_id in overrides:
            return overrides[publisher_id].get('high_freq_ip_limit', 
                    self.publisher_config.get('default', {}).get('high_freq_ip_limit', 30))
        return self.publisher_config.get('default', {}).get('high_freq_ip_limit', 30)

    def get_high_freq_device_limit(self, publisher_id: str) -> int:
        overrides = self.publisher_config.get('overrides', {})
        if publisher_id in overrides:
            return overrides[publisher_id].get('high_freq_device_limit',
                    self.publisher_config.get('default', {}).get('high_freq_device_limit', 20))
        return self.publisher_config.get('default', {}).get('high_freq_device_limit', 20)
