import heapq
import time
from collections import Counter, defaultdict, deque
from typing import Iterator, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class Statistics:
    total_requests: int = 0
    total_bytes: int = 0
    status_codes: Counter = field(default_factory=Counter)
    ips: Counter = field(default_factory=Counter)
    methods: Counter = field(default_factory=Counter)
    paths: Counter = field(default_factory=Counter)
    user_agents: Counter = field(default_factory=Counter)
    requests_per_hour: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    requests_per_day: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top_referers: Counter = field(default_factory=Counter)

    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "total_bytes": self.total_bytes,
            "status_codes": dict(self.status_codes),
            "ips": dict(self.ips),
            "methods": dict(self.methods),
            "paths": dict(self.paths),
            "user_agents": dict(self.user_agents),
            "requests_per_hour": dict(self.requests_per_hour),
            "requests_per_day": dict(self.requests_per_day),
            "top_referers": dict(self.top_referers)
        }

@dataclass
class WindowStats:
    total_requests: int = 0
    total_2xx: int = 0
    total_3xx: int = 0
    total_4xx: int = 0
    total_5xx: int = 0
    total_bytes: int = 0
    
    def error_count(self) -> int:
        return self.total_4xx + self.total_5xx
    
    def error_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.error_count() / self.total_requests) * 100.0
    
    def five_hundred_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_5xx / self.total_requests) * 100.0
    
    def four_hundred_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.total_4xx / self.total_requests) * 100.0
    
    def to_dict(self) -> Dict:
        return {
            "total_requests": self.total_requests,
            "total_2xx": self.total_2xx,
            "total_3xx": self.total_3xx,
            "total_4xx": self.total_4xx,
            "total_5xx": self.total_5xx,
            "error_rate": self.error_rate(),
            "five_hundred_rate": self.five_hundred_rate(),
            "four_hundred_rate": self.four_hundred_rate(),
            "total_bytes": self.total_bytes
        }

class SlidingWindow:
    def __init__(self, window_seconds: int = 60, bucket_seconds: int = 1):
        self.window_seconds = window_seconds
        self.bucket_seconds = bucket_seconds
        self.buckets: deque = deque()
        self.current_bucket_ts: int = 0
        self.current_stats = WindowStats()
    
    def _bucket_key(self, ts: int) -> int:
        return (ts // self.bucket_seconds) * self.bucket_seconds
    
    def _expire_old_buckets(self, current_ts: int):
        cutoff = current_ts - self.window_seconds
        while self.buckets and self.buckets[0][0] < cutoff:
            self.buckets.popleft()
        
        if self.current_bucket_ts and self.current_bucket_ts < cutoff:
            self.current_stats = WindowStats()
            self.current_bucket_ts = 0
    
    def record(self, record: Dict):
        timestamp = record.get("timestamp")
        if timestamp is None:
            ts = int(time.time())
        elif isinstance(timestamp, datetime):
            ts = int(timestamp.timestamp())
        else:
            ts = int(time.time())
        
        bucket_ts = self._bucket_key(ts)
        status = record.get("status", 0)
        bytes_val = record.get("bytes", 0)
        
        if bucket_ts != self.current_bucket_ts:
            if self.current_bucket_ts > 0:
                self.buckets.append((self.current_bucket_ts, self.current_stats))
            self.current_stats = WindowStats()
            self.current_bucket_ts = bucket_ts
        
        self.current_stats.total_requests += 1
        self.current_stats.total_bytes += bytes_val
        
        if 200 <= status < 300:
            self.current_stats.total_2xx += 1
        elif 300 <= status < 400:
            self.current_stats.total_3xx += 1
        elif 400 <= status < 500:
            self.current_stats.total_4xx += 1
        elif 500 <= status < 600:
            self.current_stats.total_5xx += 1
        
        self._expire_old_buckets(int(time.time()))
    
    def get_current_stats(self) -> WindowStats:
        current_ts = int(time.time())
        self._expire_old_buckets(current_ts)
        
        result = WindowStats()
        result.total_requests = self.current_stats.total_requests
        result.total_2xx = self.current_stats.total_2xx
        result.total_3xx = self.current_stats.total_3xx
        result.total_4xx = self.current_stats.total_4xx
        result.total_5xx = self.current_stats.total_5xx
        result.total_bytes = self.current_stats.total_bytes
        
        for _, stats in self.buckets:
            result.total_requests += stats.total_requests
            result.total_2xx += stats.total_2xx
            result.total_3xx += stats.total_3xx
            result.total_4xx += stats.total_4xx
            result.total_5xx += stats.total_5xx
            result.total_bytes += stats.total_bytes
        
        return result
    
    def get_qps(self) -> float:
        stats = self.get_current_stats()
        if stats.total_requests == 0:
            return 0.0
        return stats.total_requests / self.window_seconds
    
    def clear(self):
        self.buckets.clear()
        self.current_stats = WindowStats()
        self.current_bucket_ts = 0

class HeapTopK:
    def __init__(self, k: int):
        self.k = k
        self.heap: List[tuple] = []
        self.item_map: Dict[str, int] = {}
    
    def update(self, item: str, count: int):
        self.item_map[item] = count
        
        for i, (c, it) in enumerate(self.heap):
            if it == item:
                self.heap[i] = (count, item)
                heapq.heapify(self.heap)
                return
        
        if len(self.heap) < self.k:
            heapq.heappush(self.heap, (count, item))
        elif count > self.heap[0][0]:
            heapq.heapreplace(self.heap, (count, item))
    
    def get_top(self) -> List[tuple]:
        result = [(item, count) for count, item in self.heap]
        result.sort(key=lambda x: (-x[1], x[0]))
        return result
    
    def clear(self):
        self.heap.clear()
        self.item_map.clear()

class StatisticsCollector:
    def __init__(self, top_n: int = 10, window_seconds: int = 60):
        self.stats = Statistics()
        self.top_n = top_n
        self._heap_ips = HeapTopK(top_n)
        self._heap_paths = HeapTopK(top_n)
        self._heap_ua = HeapTopK(top_n)
        self._heap_referers = HeapTopK(top_n)
        self._sliding_window = SlidingWindow(window_seconds=window_seconds)
    
    def process(self, records: Iterator[Dict]) -> Statistics:
        for record in records:
            self._process_record(record)
        return self.stats
    
    def _process_record(self, record: Dict):
        self.stats.total_requests += 1
        self.stats.total_bytes += record.get("bytes", 0)
        
        self._sliding_window.record(record)
        
        if "status" in record:
            self.stats.status_codes[record["status"]] += 1
        
        if "ip" in record:
            ip = record["ip"]
            self.stats.ips[ip] += 1
            self._heap_ips.update(ip, self.stats.ips[ip])
        
        if "method" in record:
            self.stats.methods[record["method"]] += 1
        
        if "path" in record:
            path = record["path"]
            self.stats.paths[path] += 1
            self._heap_paths.update(path, self.stats.paths[path])
        
        if "user_agent" in record:
            ua = record["user_agent"]
            self.stats.user_agents[ua] += 1
            self._heap_ua.update(ua, self.stats.user_agents[ua])
        
        if "referer" in record and record["referer"] != "-":
            ref = record["referer"]
            self.stats.top_referers[ref] += 1
            self._heap_referers.update(ref, self.stats.top_referers[ref])
        
        timestamp = record.get("timestamp")
        if timestamp:
            if isinstance(timestamp, datetime):
                hour = timestamp.hour
                day = timestamp.strftime("%Y-%m-%d")
                self.stats.requests_per_hour[hour] += 1
                self.stats.requests_per_day[day] += 1
    
    def get_window_stats(self) -> WindowStats:
        return self._sliding_window.get_current_stats()
    
    def get_qps(self) -> float:
        return self._sliding_window.get_qps()
    
    def get_top_ips(self, n: Optional[int] = None) -> List[tuple]:
        if n is None or n == self.top_n:
            return self._heap_ips.get_top()
        return self.stats.ips.most_common(n)
    
    def get_top_status_codes(self, n: Optional[int] = None) -> List[tuple]:
        return self.stats.status_codes.most_common(n or self.top_n)
    
    def get_top_paths(self, n: Optional[int] = None) -> List[tuple]:
        if n is None or n == self.top_n:
            return self._heap_paths.get_top()
        return self.stats.paths.most_common(n)
    
    def get_top_user_agents(self, n: Optional[int] = None) -> List[tuple]:
        if n is None or n == self.top_n:
            return self._heap_ua.get_top()
        return self.stats.user_agents.most_common(n)
    
    def get_top_referers(self, n: Optional[int] = None) -> List[tuple]:
        if n is None or n == self.top_n:
            return self._heap_referers.get_top()
        return self.stats.top_referers.most_common(n)
    
    def get_status_code_summary(self) -> Dict[str, int]:
        summary = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0, "other": 0}
        for status, count in self.stats.status_codes.items():
            if 200 <= status < 300:
                summary["2xx"] += count
            elif 300 <= status < 400:
                summary["3xx"] += count
            elif 400 <= status < 500:
                summary["4xx"] += count
            elif 500 <= status < 600:
                summary["5xx"] += count
            else:
                summary["other"] += count
        return summary
    
    def get_bandwidth_mb(self) -> float:
        return self.stats.total_bytes / (1024 * 1024)
