import math
import mmh3
from bitarray import bitarray
from typing import List, Optional, Dict, Set, Any
from collections import defaultdict


class BloomFilter:
    def __init__(self, capacity: int, error_rate: float = 0.01):
        """
        初始化布隆过滤器
        
        Args:
            capacity: 预期存储的元素数量
            error_rate: 期望的误报率 (0, 1)
        """
        self.capacity = capacity
        self.error_rate = error_rate
        
        self.bit_size = self._calculate_bit_size(capacity, error_rate)
        self.hash_count = self._calculate_hash_count(self.bit_size, capacity)
        
        self.bit_array = bitarray(self.bit_size)
        self.bit_array.setall(0)
        self.items_count = 0
    
    @staticmethod
    def _calculate_bit_size(n: int, p: float) -> int:
        """计算所需的位数"""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)
    
    @staticmethod
    def _calculate_hash_count(m: int, n: int) -> int:
        """计算最佳哈希函数数量"""
        k = (m / n) * math.log(2)
        return int(k)
    
    def add(self, item: str) -> None:
        """添加元素"""
        for i in range(self.hash_count):
            digest = mmh3.hash(item, i) % self.bit_size
            self.bit_array[digest] = 1
        self.items_count += 1
    
    def __contains__(self, item: str) -> bool:
        """检查元素是否可能存在"""
        for i in range(self.hash_count):
            digest = mmh3.hash(item, i) % self.bit_size
            if self.bit_array[digest] == 0:
                return False
        return True
    
    def exists(self, item: str) -> bool:
        """检查元素是否可能存在（显式方法）"""
        return item in self
    
    def get_false_positive_rate(self) -> float:
        """计算当前的理论误报率"""
        if self.items_count == 0:
            return 0.0
        return (1 - math.exp(
            -self.hash_count * self.items_count / self.bit_size
        )) ** self.hash_count
    
    def get_memory_usage_kb(self) -> float:
        """获取内存使用量（KB）"""
        return (self.bit_size / 8) / 1024
    
    def reset(self) -> None:
        """重置过滤器"""
        self.bit_array.setall(0)
        self.items_count = 0
    
    def to_dict(self) -> dict:
        """导出配置信息"""
        return {
            "capacity": self.capacity,
            "error_rate": self.error_rate,
            "bit_size": self.bit_size,
            "hash_count": self.hash_count,
            "items_count": self.items_count,
            "memory_usage_kb": self.get_memory_usage_kb(),
            "current_fpr": self.get_false_positive_rate()
        }


class CacheBloomFilter:
    """专门用于缓存场景的布隆过滤器"""
    
    def __init__(self, expected_endpoints: int = 10000, error_rate: float = 0.01):
        self.endpoint_bloom = BloomFilter(expected_endpoints, error_rate)
        self.field_bloom = BloomFilter(expected_endpoints * 10, error_rate)
        self.request_history: List[str] = []
    
    def record_request(self, endpoint: str, response_fields: Optional[List[str]] = None) -> None:
        """记录请求"""
        cache_key = f"endpoint:{endpoint}"
        self.endpoint_bloom.add(cache_key)
        self.request_history.append(endpoint)
        
        if response_fields:
            for field in response_fields:
                field_key = f"field:{endpoint}:{field}"
                self.field_bloom.add(field_key)
    
    def check_endpoint_cache(self, endpoint: str) -> dict:
        """检查端点是否可缓存"""
        cache_key = f"endpoint:{endpoint}"
        exists = cache_key in self.endpoint_bloom
        historical_count = self.request_history.count(endpoint)
        
        return {
            "may_exist": exists,
            "historical_count": historical_count,
            "cache_hit_probability": min(historical_count / len(self.request_history), 1.0) if self.request_history else 0.0
        }
    
    def check_field_cache(self, endpoint: str, field: str) -> dict:
        """检查字段是否可缓存"""
        field_key = f"field:{endpoint}:{field}"
        exists = field_key in self.field_bloom
        
        return {
            "may_exist": exists,
            "recommendation": "cache" if exists else "no_cache"
        }
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "endpoint_filter": self.endpoint_bloom.to_dict(),
            "field_filter": self.field_bloom.to_dict(),
            "total_requests_recorded": len(self.request_history),
            "unique_endpoints_estimated": len(set(self.request_history))
        }
    
    def batch_check(self, endpoints: List[str]) -> List[dict]:
        """批量检查多个端点"""
        results = []
        for ep in endpoints:
            results.append({
                "endpoint": ep,
                **self.check_endpoint_cache(ep)
            })
        return results


class PenetrationProtector:
    """缓存穿透防护器"""
    
    def __init__(self, 
                 null_value_ttl: int = 60,
                 bloom_filter_capacity: int = 100000,
                 bloom_filter_error_rate: float = 0.001,
                 max_hot_data: int = 1000):
        """
        初始化穿透防护器
        
        Args:
            null_value_ttl: 空值缓存时间（秒）
            bloom_filter_capacity: 布隆过滤器容量
            bloom_filter_error_rate: 布隆过滤器误报率
            max_hot_data: 最大热点数据数量
        """
        self.null_value_ttl = null_value_ttl
        self.max_hot_data = max_hot_data
        
        self.key_existence_filter = BloomFilter(bloom_filter_capacity, bloom_filter_error_rate)
        self.null_value_cache: Dict[str, Any] = {}
        self.null_value_expiry: Dict[str, float] = {}
        self.hot_data_set: Set[str] = set()
        self.access_frequency: Dict[str, int] = defaultdict(int)
        self.preload_queue: List[str] = []
        
    def record_key_access(self, key: str, exists: bool = True) -> None:
        """记录键的访问"""
        self.access_frequency[key] += 1
        
        if exists:
            self.key_existence_filter.add(key)
            self._update_hot_data(key)
    
    def _update_hot_data(self, key: str) -> None:
        """更新热点数据集"""
        if len(self.hot_data_set) < self.max_hot_data:
            self.hot_data_set.add(key)
            return
        
        freq = self.access_frequency[key]
        min_freq = min(self.access_frequency.get(k, 0) for k in self.hot_data_set)
        
        if freq > min_freq:
            for k in list(self.hot_data_set):
                if self.access_frequency.get(k, 0) == min_freq:
                    self.hot_data_set.remove(k)
                    break
            self.hot_data_set.add(key)
    
    def is_key_valid(self, key: str) -> bool:
        """
        检查键是否可能有效（防止穿透攻击）
        
        Returns:
            True表示可能有效，False表示肯定无效
        """
        return key in self.key_existence_filter
    
    def get_null_value(self, key: str) -> Optional[Any]:
        """获取空值缓存"""
        import time
        if key in self.null_value_cache:
            if time.time() < self.null_value_expiry.get(key, 0):
                return self.null_value_cache[key]
            else:
                del self.null_value_cache[key]
                del self.null_value_expiry[key]
        return None
    
    def set_null_value(self, key: str, value: Any = None) -> None:
        """设置空值缓存"""
        import time
        self.null_value_cache[key] = value
        self.null_value_expiry[key] = time.time() + self.null_value_ttl
    
    def get_hot_data_keys(self) -> List[str]:
        """获取热点数据键列表"""
        return sorted(self.hot_data_set, key=lambda k: self.access_frequency.get(k, 0), reverse=True)
    
    def generate_preload_plan(self, top_n: int = 100) -> List[Dict[str, Any]]:
        """生成预加载计划"""
        hot_keys = self.get_hot_data_keys()[:top_n]
        plan = []
        
        for i, key in enumerate(hot_keys):
            priority = 'critical' if i < len(hot_keys) * 0.2 else 'high' if i < len(hot_keys) * 0.5 else 'normal'
            plan.append({
                'key': key,
                'priority': priority,
                'access_frequency': self.access_frequency.get(key, 0),
                'is_hot': key in self.hot_data_set
            })
        
        return plan
    
    def detect_penetration_attack(self, 
                                   request_window: List[str], 
                                   threshold_miss_rate: float = 0.95,
                                   min_requests: int = 50) -> Dict[str, Any]:
        """
        检测穿透攻击
        
        Args:
            request_window: 请求窗口内的键列表
            threshold_miss_rate: 触发告警的未命中率阈值
            min_requests: 最小请求数
            
        Returns:
            攻击检测结果
        """
        if len(request_window) < min_requests:
            return {'attack_detected': False, 'reason': '请求样本不足'}
        
        miss_count = sum(1 for key in request_window if not self.is_key_valid(key))
        miss_rate = miss_count / len(request_window)
        
        if miss_rate >= threshold_miss_rate:
            return {
                'attack_detected': True,
                'miss_rate': miss_rate,
                'request_count': len(request_window),
                'miss_count': miss_count,
                'recommendation': '建议启用更严格的限流和布隆过滤',
                'suspicious_keys': list(set(key for key in request_window if not self.is_key_valid(key)))[:10]
            }
        
        return {
            'attack_detected': False,
            'miss_rate': miss_rate,
            'request_count': len(request_window),
            'miss_count': miss_count
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'null_value_cache_size': len(self.null_value_cache),
            'hot_data_count': len(self.hot_data_set),
            'total_keys_tracked': len(self.access_frequency),
            'bloom_filter_stats': self.key_existence_filter.to_dict(),
            'top_hot_keys': self.get_hot_data_keys()[:10]
        }


class HotDataPreloader:
    """热点数据预加载器"""
    
    def __init__(self, max_concurrent_loads: int = 10):
        self.max_concurrent_loads = max_concurrent_loads
        self.preload_queue: List[Dict[str, Any]] = []
        self.loaded_data: Dict[str, Any] = {}
        self.load_stats: Dict[str, int] = defaultdict(int)
        
    def add_to_preload_queue(self, 
                             key: str, 
                             priority: str = 'normal',
                             estimated_load_time_ms: int = 100) -> None:
        """添加到预加载队列"""
        if key not in self.loaded_data:
            self.preload_queue.append({
                'key': key,
                'priority': priority,
                'estimated_load_time_ms': estimated_load_time_ms,
                'added_at': __import__('time').time()
            })
            self._sort_queue()
    
    def _sort_queue(self) -> None:
        """按优先级排序队列"""
        priority_order = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
        self.preload_queue.sort(key=lambda x: (priority_order.get(x['priority'], 3), x['added_at']))
    
    def simulate_preload(self, 
                          data_sources: Dict[str, Any],
                          duration_minutes: int = 30) -> Dict[str, Any]:
        """
        模拟预加载过程
        
        Args:
            data_sources: 数据源模拟字典 {key: load_time_ms}
            duration_minutes: 模拟时长（分钟）
            
        Returns:
            预加载模拟结果
        """
        if not self.preload_queue:
            return {
                'preloaded_count': 0,
                'total_count': 0,
                'estimated_hit_rate_improvement': 0.0,
                'estimated_latency_reduction_ms': 0.0
            }
        
        total_seconds = duration_minutes * 60
        processing_capacity = total_seconds * 1000 / 50
        
        sorted_queue = sorted(self.preload_queue, 
                             key=lambda x: {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}.get(x['priority'], 3))
        
        preloaded = []
        cumulative_time = 0
        
        for item in sorted_queue:
            load_time = data_sources.get(item['key'], item.get('estimated_load_time_ms', 100))
            if cumulative_time + load_time <= total_seconds * 1000:
                preloaded.append(item['key'])
                cumulative_time += load_time
                if len(preloaded) >= self.max_concurrent_loads * (total_seconds // 10):
                    break
        
        original_hit_rate = len(self.loaded_data) / max(1, len(self.preload_queue) + len(self.loaded_data))
        new_hit_rate = (len(self.loaded_data) + len(preloaded)) / max(1, len(self.preload_queue) + len(self.loaded_data))
        
        avg_load_time = sum(data_sources.values()) / len(data_sources) if data_sources else 100
        cache_time = 5
        
        return {
            'preloaded_count': len(preloaded),
            'total_count': len(self.preload_queue),
            'preload_ratio': len(preloaded) / len(self.preload_queue) if self.preload_queue else 0,
            'original_hit_rate': original_hit_rate,
            'estimated_hit_rate': min(0.95, new_hit_rate),
            'estimated_hit_rate_improvement': new_hit_rate - original_hit_rate,
            'estimated_latency_reduction_ms': max(0, avg_load_time - cache_time),
            'preloaded_keys': preloaded[:20],
            'remaining_queue': [x['key'] for x in sorted_queue[len(preloaded):][:10]]
        }
    
    def mark_loaded(self, key: str, data: Any) -> None:
        """标记数据已加载"""
        self.loaded_data[key] = data
        self.load_stats[key] += 1
        self.preload_queue = [x for x in self.preload_queue if x['key'] != key]
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self.preload_queue)
    
    def get_priority_breakdown(self) -> Dict[str, int]:
        """获取队列优先级分布"""
        breakdown = defaultdict(int)
        for item in self.preload_queue:
            breakdown[item['priority']] += 1
        return dict(breakdown)
