import time
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque
import yaml

from .data_models import ClickLog, ClickFeatures
from .threshold_manager import PublisherLimitManager

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class RuleResult:
    rule_name: str
    triggered: bool
    fraud_score: float
    reason: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class RedisFrequencyCounter:
    def __init__(self, redis_config: Dict):
        self.redis_config = redis_config
        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        if not REDIS_AVAILABLE:
            self.client = None
            return
        
        try:
            self.client = redis.Redis(
                host=self.redis_config.get('host', 'localhost'),
                port=self.redis_config.get('port', 6379),
                db=self.redis_config.get('db', 0),
                password=self.redis_config.get('password'),
                socket_timeout=self.redis_config.get('socket_timeout', 5000) / 1000,
                decode_responses=True
            )
            self.client.ping()
        except Exception as e:
            print(f"Redis连接失败，使用本地内存: {e}")
            self.client = None

    def is_connected(self) -> bool:
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False

    def increment_and_get_count(self, key: str, window_seconds: int) -> int:
        if self.client is None:
            return 0
        
        current_time = int(time.time())
        window_key = f"{key}:{current_time // window_seconds}"
        
        pipe = self.client.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds * 2)
        result, _ = pipe.execute()
        
        return int(result) if result else 0

    def get_sliding_window_count(self, key_prefix: str, window_seconds: int) -> int:
        if self.client is None:
            return 0
        
        current_time = int(time.time())
        total = 0
        
        for i in range(2):
            window_key = f"{key_prefix}:{(current_time - i * window_seconds) // window_seconds}"
            count = self.client.get(window_key)
            if count:
                total += int(count)
        
        return total

    def record_timestamp(self, key: str, timestamp: float, max_history: int = 100):
        if self.client is None:
            return
        
        list_key = f"timestamps:{key}"
        pipe = self.client.pipeline()
        pipe.zadd(list_key, {str(timestamp): timestamp})
        pipe.zremrangebyrank(list_key, 0, -max_history - 1)
        pipe.expire(list_key, 3600)
        pipe.execute()

    def get_recent_timestamps(self, key: str, window_seconds: int) -> List[float]:
        if self.client is None:
            return []
        
        list_key = f"timestamps:{key}"
        current_time = time.time()
        min_score = current_time - window_seconds
        
        try:
            values = self.client.zrangebyscore(list_key, min_score, current_time, withscores=True)
            return [float(score) for _, score in values]
        except:
            return []


class RuleEngineV2:
    def __init__(self, config_path: str = 'config/config.yaml', use_redis: bool = True):
        self.config = self._load_config(config_path)
        self.rules_config = self.config['rules']
        self.use_redis = use_redis and self.rules_config['high_frequency'].get('use_redis', True)
        
        self.redis_counter: Optional[RedisFrequencyCounter] = None
        if self.use_redis and REDIS_AVAILABLE:
            self.redis_counter = RedisFrequencyCounter(self.config['redis'])
            if not self.redis_counter.is_connected():
                self.redis_counter = None
                self.use_redis = False
        
        self.local_ip_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.local_device_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.local_session_data: Dict[str, Dict] = defaultdict(dict)
        
        self.publisher_limit_manager = PublisherLimitManager(config_path)

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def evaluate_all_rules(self, click_log: ClickLog, features: ClickFeatures) -> List[RuleResult]:
        results = []
        
        publisher_id = click_log.publisher_id
        
        results.append(self._check_high_frequency_ip(click_log, features, publisher_id))
        results.append(self._check_high_frequency_device(click_log, features, publisher_id))
        results.append(self._check_fixed_interval_ip(click_log))
        results.append(self._check_fixed_interval_device(click_log))
        results.append(self._check_invalid_session_duration(click_log))
        results.append(self._check_excessive_session_clicks(click_log, features))
        results.append(self._check_suspicious_publisher_ratio(click_log, features))
        results.append(self._check_user_agent_anomaly(click_log))
        
        self._update_state(click_log)
        
        return results

    def _get_ip_click_count_redis(self, ip: str, window_seconds: int) -> int:
        if self.redis_counter is None:
            return self._get_local_count(self.local_ip_history.get(ip, deque()), window_seconds)
        
        key = f"freq:ip:{ip}:{window_seconds}s"
        return self.redis_counter.increment_and_get_count(key, window_seconds)

    def _get_device_click_count_redis(self, device_id: str, window_seconds: int) -> int:
        if self.redis_counter is None:
            return self._get_local_count(self.local_device_history.get(device_id, deque()), window_seconds)
        
        key = f"freq:device:{device_id}:{window_seconds}s"
        return self.redis_counter.increment_and_get_count(key, window_seconds)

    def _get_local_count(self, history: deque, window_seconds: int) -> int:
        if not history:
            return 0
        current_time = time.time()
        return sum(1 for ts in history if current_time - ts <= window_seconds)

    def _check_high_frequency_ip(self, click_log: ClickLog, features: ClickFeatures, publisher_id: str) -> RuleResult:
        config = self.rules_config['high_frequency']
        window = config['window_seconds']
        max_clicks = self.publisher_limit_manager.get_high_freq_ip_limit(publisher_id)
        
        if self.use_redis and self.redis_counter:
            click_count = self._get_ip_click_count_redis(click_log.ip, window)
        else:
            click_count = features.ip_click_count_1min
        
        triggered = click_count > max_clicks
        
        fraud_score = min(1.0, click_count / (max_clicks * 2)) if triggered else 0.0
        reason = f"IP高频点击: {click_count}次/{window}秒 (发布商{publisher_id}阈值: {max_clicks})" if triggered else ""
        
        return RuleResult(
            rule_name='high_frequency_ip',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={
                'click_count': click_count,
                'threshold': max_clicks,
                'window_seconds': window,
                'publisher_id': publisher_id,
                'use_redis': self.use_redis
            }
        )

    def _check_high_frequency_device(self, click_log: ClickLog, features: ClickFeatures, publisher_id: str) -> RuleResult:
        config = self.rules_config['high_frequency']
        window = config['window_seconds']
        max_clicks = self.publisher_limit_manager.get_high_freq_device_limit(publisher_id)
        
        if self.use_redis and self.redis_counter:
            click_count = self._get_device_click_count_redis(click_log.device_id, window)
        else:
            click_count = features.device_click_count_1min
        
        triggered = click_count > max_clicks
        
        fraud_score = min(1.0, click_count / (max_clicks * 2)) if triggered else 0.0
        reason = f"设备高频点击: {click_count}次/{window}秒 (发布商{publisher_id}阈值: {max_clicks})" if triggered else ""
        
        return RuleResult(
            rule_name='high_frequency_device',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={
                'click_count': click_count,
                'threshold': max_clicks,
                'window_seconds': window,
                'publisher_id': publisher_id,
                'use_redis': self.use_redis
            }
        )

    def _check_fixed_interval_ip(self, click_log: ClickLog) -> RuleResult:
        config = self.rules_config['fixed_interval']
        window = config['window_seconds']
        min_clicks = config['min_clicks']
        tolerance = config['tolerance_seconds']
        
        if self.use_redis and self.redis_counter:
            timestamps = self.redis_counter.get_recent_timestamps(f"ip:{click_log.ip}", window)
        else:
            timestamps = list(self.local_ip_history.get(click_log.ip, deque()))
            current_time = time.time()
            timestamps = [ts for ts in timestamps if current_time - ts <= window]
        
        if len(timestamps) < min_clicks:
            return RuleResult('fixed_interval_ip', False, 0.0, '', {})
        
        timestamps.sort()
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        
        if not intervals:
            return RuleResult('fixed_interval_ip', False, 0.0, '', {})
        
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        triggered = std_interval < tolerance and mean_interval > 0
        
        fraud_score = 0.0
        reason = ""
        if triggered:
            cv = std_interval / mean_interval if mean_interval > 0 else 0
            fraud_score = min(1.0, 1.0 - cv * 2)
            reason = f"IP固定间隔点击: 间隔均值={mean_interval:.2f}s, 标准差={std_interval:.3f}s"
        
        return RuleResult(
            rule_name='fixed_interval_ip',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={
                'mean_interval': float(mean_interval),
                'std_interval': float(std_interval),
                'click_count': len(timestamps),
                'use_redis': self.use_redis
            }
        )

    def _check_fixed_interval_device(self, click_log: ClickLog) -> RuleResult:
        config = self.rules_config['fixed_interval']
        window = config['window_seconds']
        min_clicks = config['min_clicks']
        tolerance = config['tolerance_seconds']
        
        if self.use_redis and self.redis_counter:
            timestamps = self.redis_counter.get_recent_timestamps(f"device:{click_log.device_id}", window)
        else:
            timestamps = list(self.local_device_history.get(click_log.device_id, deque()))
            current_time = time.time()
            timestamps = [ts for ts in timestamps if current_time - ts <= window]
        
        if len(timestamps) < min_clicks:
            return RuleResult('fixed_interval_device', False, 0.0, '', {})
        
        timestamps.sort()
        intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
        
        if not intervals:
            return RuleResult('fixed_interval_device', False, 0.0, '', {})
        
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        triggered = std_interval < tolerance and mean_interval > 0
        
        fraud_score = 0.0
        reason = ""
        if triggered:
            cv = std_interval / mean_interval if mean_interval > 0 else 0
            fraud_score = min(1.0, 1.0 - cv * 2)
            reason = f"设备固定间隔点击: 间隔均值={mean_interval:.2f}s, 标准差={std_interval:.3f}s"
        
        return RuleResult(
            rule_name='fixed_interval_device',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={
                'mean_interval': float(mean_interval),
                'std_interval': float(std_interval),
                'click_count': len(timestamps),
                'use_redis': self.use_redis
            }
        )

    def _check_invalid_session_duration(self, click_log: ClickLog) -> RuleResult:
        config = self.rules_config['invalid_traffic']
        min_duration = config['min_session_duration_seconds']
        
        if not click_log.session_id:
            return RuleResult('invalid_session_duration', False, 0.0, '', {})
        
        session_data = self.local_session_data[click_log.session_id]
        if 'start_time' not in session_data:
            session_data['start_time'] = click_log.timestamp.timestamp()
            return RuleResult('invalid_session_duration', False, 0.0, '', {})
        
        session_duration = click_log.timestamp.timestamp() - session_data['start_time']
        click_count = session_data.get('click_count', 0) + 1
        
        triggered = click_count > 3 and session_duration < min_duration
        
        fraud_score = 0.7 if triggered else 0.0
        reason = f"无效会话时长: {session_duration:.2f}s, {click_count}次点击" if triggered else ""
        
        return RuleResult(
            rule_name='invalid_session_duration',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={'session_duration': session_duration, 'click_count': click_count}
        )

    def _check_excessive_session_clicks(self, click_log: ClickLog, features: ClickFeatures) -> RuleResult:
        config = self.rules_config['invalid_traffic']
        max_clicks = config['max_click_rate_per_user']
        
        session_clicks = features.session_click_count
        triggered = session_clicks > max_clicks
        
        fraud_score = min(1.0, session_clicks / (max_clicks * 2)) if triggered else 0.0
        reason = f"会话点击过量: {session_clicks}次 (阈值: {max_clicks})" if triggered else ""
        
        return RuleResult(
            rule_name='excessive_session_clicks',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={'session_clicks': session_clicks, 'threshold': max_clicks}
        )

    def _check_suspicious_publisher_ratio(self, click_log: ClickLog, features: ClickFeatures) -> RuleResult:
        ratio = features.publisher_click_ratio
        triggered = ratio > 0.5
        
        fraud_score = min(1.0, ratio) if triggered else 0.0
        reason = f"发布商点击占比异常: {ratio:.2%}" if triggered else ""
        
        return RuleResult(
            rule_name='suspicious_publisher_ratio',
            triggered=triggered,
            fraud_score=fraud_score,
            reason=reason,
            details={'ratio': ratio}
        )

    def _check_user_agent_anomaly(self, click_log: ClickLog) -> RuleResult:
        user_agent = click_log.user_agent.lower()
        
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'curl', 'wget', 'python', 'java/',
            'phantomjs', 'headless', 'selenium'
        ]
        
        triggered = any(pattern in user_agent for pattern in suspicious_patterns)
        triggered_empty = len(user_agent.strip()) < 10
        
        fraud_score = 0.0
        reason = ""
        
        if triggered:
            fraud_score = 0.9
            reason = "可疑User-Agent: 包含爬虫/机器人特征"
        elif triggered_empty:
            fraud_score = 0.5
            reason = "User-Agent过短或为空"
        
        return RuleResult(
            rule_name='user_agent_anomaly',
            triggered=triggered or triggered_empty,
            fraud_score=fraud_score,
            reason=reason,
            details={'user_agent_length': len(user_agent)}
        )

    def _update_state(self, click_log: ClickLog):
        timestamp = click_log.timestamp.timestamp()
        
        if self.use_redis and self.redis_counter:
            self.redis_counter.record_timestamp(f"ip:{click_log.ip}", timestamp)
            self.redis_counter.record_timestamp(f"device:{click_log.device_id}", timestamp)
        else:
            self.local_ip_history[click_log.ip].append(timestamp)
            self.local_device_history[click_log.device_id].append(timestamp)
        
        if click_log.session_id:
            session_data = self.local_session_data[click_log.session_id]
            session_data['click_count'] = session_data.get('click_count', 0) + 1

    def get_aggregated_rule_score(self, results: List[RuleResult]) -> float:
        if not results:
            return 0.0
        
        scores = [r.fraud_score for r in results if r.triggered]
        if not scores:
            return 0.0
        
        weights = {
            'high_frequency_ip': 1.2,
            'high_frequency_device': 1.1,
            'fixed_interval_ip': 1.3,
            'fixed_interval_device': 1.2,
            'invalid_session_duration': 1.0,
            'excessive_session_clicks': 1.1,
            'suspicious_publisher_ratio': 0.8,
            'user_agent_anomaly': 1.0
        }
        
        weighted_scores = []
        for r in results:
            if r.triggered:
                weight = weights.get(r.rule_name, 1.0)
                weighted_scores.append(r.fraud_score * weight)
        
        return min(1.0, sum(weighted_scores) / len(scores) if scores else 0.0)

    def reset(self):
        self.local_ip_history.clear()
        self.local_device_history.clear()
        self.local_session_data.clear()
