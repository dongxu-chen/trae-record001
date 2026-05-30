import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode


def generate_cache_key(endpoint: str, params: Optional[Dict[str, Any]] = None,
                       method: str = "GET") -> str:
    """生成缓存键"""
    key_parts = [method.upper(), endpoint]
    if params:
        sorted_params = json.dumps(params, sort_keys=True)
        key_parts.append(sorted_params)
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def extract_endpoint_pattern(endpoint: str) -> str:
    """提取端点模式（将ID等变量替换为占位符）"""
    pattern = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', endpoint)
    pattern = re.sub(r'/\d+(\.\d+)?', '/{id}', pattern)
    pattern = re.sub(r'/[A-Za-z0-9_]+-[A-Za-z0-9_]+', '/{slug}', pattern)
    return pattern


def parse_timestamp(ts_str: str) -> Optional[datetime]:
    """解析多种格式的时间戳"""
    formats = [
        "%d/%b/%Y:%H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%b %d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(ts_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    
    try:
        return datetime.fromtimestamp(float(ts_str))
    except (ValueError, TypeError):
        return None


def extract_fields_from_response(response_data: Any, prefix: str = "") -> List[str]:
    """从响应数据中提取所有字段路径"""
    fields = []
    
    if isinstance(response_data, dict):
        for key, value in response_data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            fields.append(field_path)
            fields.extend(extract_fields_from_response(value, field_path))
    elif isinstance(response_data, list) and response_data:
        if len(response_data) > 0 and isinstance(response_data[0], (dict, list)):
            for i, item in enumerate(response_data[:3]):
                field_path = f"{prefix}[{i}]" if prefix else f"[{i}]"
                fields.extend(extract_fields_from_response(item, field_path))
    
    return fields


def calculate_size_bytes(data: Any) -> int:
    """计算数据的字节大小"""
    if data is None:
        return 0
    return len(json.dumps(data, ensure_ascii=False).encode('utf-8'))


def format_size(size_bytes: int) -> str:
    """格式化字节大小为可读字符串"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def group_by_time_window(timestamps: List[datetime], window_minutes: int = 5) -> Dict[datetime, int]:
    """按时间窗口分组统计"""
    from collections import defaultdict
    
    groups = defaultdict(int)
    for ts in timestamps:
        window_start = ts.replace(
            minute=(ts.minute // window_minutes) * window_minutes,
            second=0,
            microsecond=0
        )
        groups[window_start] += 1
    
    return dict(sorted(groups.items()))


def detect_periodicity(series: List[int], min_period: int = 3, max_period: int = 48) -> Optional[int]:
    """检测时间序列的周期性"""
    if len(series) < max_period * 2:
        return None
    
    from collections import Counter
    
    for period in range(min_period, max_period + 1):
        segments = []
        for i in range(0, len(series), period):
            segment = tuple(series[i:i + period])
            if len(segment) == period:
                segments.append(segment)
        
        if len(segments) >= 3:
            counter = Counter(segments)
            most_common = counter.most_common(1)[0]
            if most_common[1] / len(segments) > 0.7:
                return period
    
    return None


def calculate_redundancy_ratio(values: List[Any]) -> float:
    """计算值的冗余比率（重复率）"""
    if not values:
        return 0.0
    unique_count = len(set([json.dumps(v, sort_keys=True) for v in values]))
    return 1.0 - (unique_count / len(values))


def normalize_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    参数归一化：排序键、移除空值、标准化值类型
    """
    if not params:
        return {}
    
    normalized = {}
    for key in sorted(params.keys()):
        value = params[key]
        
        if value is None or (isinstance(value, str) and value.strip() == ''):
            continue
        
        if isinstance(value, str):
            value = value.strip()
            try:
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)
            except (ValueError, TypeError):
                pass
        
        elif isinstance(value, list):
            value = sorted([str(v) for v in value])
        
        elif isinstance(value, dict):
            value = normalize_params(value)
        
        normalized[key] = value
    
    return normalized


def parse_url_params(url: str) -> Dict[str, Any]:
    """从URL中解析并归一化参数"""
    try:
        parsed = urlparse(url)
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=False)
            result = {}
            for k, v in params.items():
                if len(v) == 1:
                    result[k] = v[0]
                else:
                    result[k] = v
            return normalize_params(result)
    except Exception:
        pass
    return {}


def compute_content_hash(response_data: Any, include_metadata: bool = False) -> str:
    """
    计算响应内容的哈希值，用于识别相同内容
    
    Args:
        response_data: 响应数据
        include_metadata: 是否包含元数据（如时间戳、request_id等）
    
    Returns:
        SHA256哈希字符串
    """
    if response_data is None:
        return hashlib.sha256(b'').hexdigest()
    
    if isinstance(response_data, dict):
        data_to_hash = {}
        for key, value in response_data.items():
            if not include_metadata:
                metadata_keys = ['timestamp', 'request_id', 'trace_id', 'server_time', 
                               'processing_time_ms', 'latency', 'generated_at']
                if key.lower() in metadata_keys:
                    continue
            
            if isinstance(value, (dict, list)):
                data_to_hash[key] = compute_content_hash(value, include_metadata)
            else:
                data_to_hash[key] = str(value)
        
        sorted_content = json.dumps(data_to_hash, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_content.encode('utf-8')).hexdigest()
    
    elif isinstance(response_data, list):
        items_hash = [compute_content_hash(item, include_metadata) for item in response_data]
        sorted_items = '|'.join(sorted(items_hash))
        return hashlib.sha256(sorted_items.encode('utf-8')).hexdigest()
    
    else:
        return hashlib.sha256(str(response_data).encode('utf-8')).hexdigest()


@dataclass
class DataFreshnessTag:
    """数据时效性标签"""
    tag: str
    description: str
    default_ttl_seconds: int
    min_ttl_seconds: int
    max_ttl_seconds: int
    freshness_score: float


DATA_FRESHNESS_TAGS: Dict[str, DataFreshnessTag] = {
    'realtime': DataFreshnessTag(
        tag='realtime',
        description='实时数据：需要秒级更新，如在线人数、实时库存、股票价格',
        default_ttl_seconds=5,
        min_ttl_seconds=1,
        max_ttl_seconds=30,
        freshness_score=1.0
    ),
    'near_realtime': DataFreshnessTag(
        tag='near_realtime',
        description='近实时数据：分钟级更新，如订单状态、物流信息',
        default_ttl_seconds=60,
        min_ttl_seconds=30,
        max_ttl_seconds=300,
        freshness_score=0.8
    ),
    'dynamic': DataFreshnessTag(
        tag='dynamic',
        description='动态数据：小时级更新，如用户信息、商品列表',
        default_ttl_seconds=1800,
        min_ttl_seconds=600,
        max_ttl_seconds=7200,
        freshness_score=0.5
    ),
    'semi_static': DataFreshnessTag(
        tag='semi_static',
        description='半静态数据：天级更新，如配置信息、分类列表',
        default_ttl_seconds=86400,
        min_ttl_seconds=36000,
        max_ttl_seconds=172800,
        freshness_score=0.2
    ),
    'static': DataFreshnessTag(
        tag='static',
        description='静态数据：基本不变，如历史数据、字典数据',
        default_ttl_seconds=604800,
        min_ttl_seconds=86400,
        max_ttl_seconds=2592000,
        freshness_score=0.05
    )
}


def classify_data_freshness(endpoint: str, response_data: Any = None,
                           request_params: Optional[Dict[str, Any]] = None) -> DataFreshnessTag:
    """
    根据端点和响应内容分类数据时效性
    
    Args:
        endpoint: API端点路径
        request_params: 请求参数
        response_data: 响应数据（可选）
    
    Returns:
        DataFreshnessTag 时效性标签
    """
    endpoint_lower = endpoint.lower()
    
    realtime_keywords = ['realtime', 'real-time', 'live', 'now', 'current',
                        'online', 'stock', 'price', 'quote', 'inventory',
                        'seat', 'availability', 'queue']
    for kw in realtime_keywords:
        if kw in endpoint_lower:
            return DATA_FRESHNESS_TAGS['realtime']
    
    near_realtime_keywords = ['order', 'status', 'tracking', 'shipment',
                             'delivery', 'notification', 'message', 'alert']
    for kw in near_realtime_keywords:
        if kw in endpoint_lower:
            return DATA_FRESHNESS_TAGS['near_realtime']
    
    static_keywords = ['static', 'dict', 'dictionary', 'config', 'configuration',
                      'history', 'historical', 'archive', 'log', 'record']
    for kw in static_keywords:
        if kw in endpoint_lower:
            return DATA_FRESHNESS_TAGS['static']
    
    semi_static_keywords = ['category', 'catalog', 'brand', 'tag', 'attribute',
                           'region', 'area', 'city', 'province', 'country']
    for kw in semi_static_keywords:
        if kw in endpoint_lower:
            return DATA_FRESHNESS_TAGS['semi_static']
    
    if request_params:
        if 't' in request_params or 'timestamp' in request_params or 'nocache' in request_params:
            return DATA_FRESHNESS_TAGS['realtime']
    
    if response_data and isinstance(response_data, dict):
        if 'timestamp' in response_data or 'updated_at' in response_data:
            updated_at = response_data.get('updated_at') or response_data.get('timestamp')
            if isinstance(updated_at, str):
                try:
                    update_time = parse_timestamp(updated_at)
                    if update_time:
                        age = datetime.now() - update_time
                        if age < timedelta(minutes=5):
                            return DATA_FRESHNESS_TAGS['realtime']
                        elif age < timedelta(hours=1):
                            return DATA_FRESHNESS_TAGS['near_realtime']
                        elif age < timedelta(days=1):
                            return DATA_FRESHNESS_TAGS['dynamic']
                except Exception:
                    pass
    
    return DATA_FRESHNESS_TAGS['dynamic']


def get_nested_value(data: Any, path: str) -> Any:
    """通过点路径获取嵌套值"""
    try:
        keys = path.replace('[', '.').replace(']', '').split('.')
        keys = [k for k in keys if k]
        
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if idx < len(current) else None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    except (KeyError, IndexError, TypeError):
        return None


def serialize_fields(data: Any, field_paths: List[str]) -> Dict[str, Any]:
    """
    按需序列化：仅序列化指定的字段
    
    Args:
        data: 原始响应数据
        field_paths: 需要缓存的字段路径列表
    
    Returns:
        仅包含指定字段的字典
    """
    if not field_paths or data is None:
        return {}
    
    def _deep_copy_filtered(source: Any, paths: List[List[str]], path_idx: int) -> Any:
        """
        递归复制数据，仅保留指定路径的字段
        paths: 所有字段路径的列表，每个路径是key的列表
        path_idx: 当前处理的路径深度
        """
        if not paths:
            return None
        
        if path_idx >= max(len(p) for p in paths):
            return source
        
        if isinstance(source, dict):
            result = {}
            key_groups = {}
            for p in paths:
                if path_idx < len(p):
                    key = p[path_idx]
                    if key not in key_groups:
                        key_groups[key] = []
                    key_groups[key].append(p)
            
            for key, sub_paths in key_groups.items():
                if key in source:
                    sub_result = _deep_copy_filtered(source[key], sub_paths, path_idx + 1)
                    if sub_result is not None:
                        result[key] = sub_result
            return result if result else None
        
        if isinstance(source, list):
            result = []
            for item in source:
                copied = _deep_copy_filtered(item, paths, path_idx)
                if copied is not None:
                    result.append(copied)
            return result if result else None
        
        return source
    
    parsed_paths = []
    for path in field_paths:
        keys = path.replace('[', '.').replace(']', '').split('.')
        keys = [k for k in keys if k]
        if keys:
            parsed_paths.append(keys)
    
    result = _deep_copy_filtered(data, parsed_paths, 0)
    return result if isinstance(result, dict) else {}


def deserialize_fields(cached_data: Dict[str, Any]) -> Any:
    """
    反序列化字段数据
    
    Args:
        cached_data: 缓存的字段数据
    
    Returns:
        重建的响应数据
    """
    return cached_data


def calculate_hotness_score(request_count: int, avg_interval_seconds: float,
                           time_decay_factor: float = 0.95) -> float:
    """
    计算字段热度评分
    
    Args:
        request_count: 请求次数
        avg_interval_seconds: 平均请求间隔（秒）
        time_decay_factor: 时间衰减因子
    
    Returns:
        热度评分 (0-1)
    """
    if request_count < 2 or avg_interval_seconds <= 0:
        return 0.0
    
    frequency_score = min(1.0, 1.0 / (1.0 + avg_interval_seconds / 3600.0))
    volume_score = min(1.0, request_count / 100.0)
    
    hotness = (frequency_score * 0.6 + volume_score * 0.4) * time_decay_factor
    
    return min(1.0, max(0.0, hotness))


def select_hot_fields(field_stats: List[Dict[str, Any]], 
                      hotness_threshold: float = 0.3,
                      max_fields: int = 20) -> List[str]:
    """
    选择热点字段用于缓存
    
    Args:
        field_stats: 字段统计信息列表，每个包含field_path, request_count, avg_interval, redundancy_ratio
        hotness_threshold: 热度阈值
        max_fields: 最大缓存字段数
    
    Returns:
        选择的字段路径列表
    """
    scored_fields = []
    for stat in field_stats:
        hotness = calculate_hotness_score(
            stat.get('request_count', 1),
            stat.get('avg_interval_seconds', 3600)
        )
        redundancy = stat.get('redundancy_ratio', 0)
        combined_score = hotness * 0.7 + redundancy * 0.3
        
        scored_fields.append({
            'field_path': stat['field_path'],
            'hotness': hotness,
            'redundancy': redundancy,
            'combined_score': combined_score
        })
    
    scored_fields.sort(key=lambda x: x['combined_score'], reverse=True)
    
    selected = [
        f['field_path'] for f in scored_fields
        if f['combined_score'] >= hotness_threshold
    ][:max_fields]
    
    return selected


def compare_content_hash(hash1: str, hash2: str) -> float:
    """
    比较两个内容哈希的相似度（仅用于同一算法生成的哈希）
    
    Returns:
        相似度 (0-1)，1表示完全相同
    """
    if hash1 == hash2:
        return 1.0
    
    bytes1 = bytes.fromhex(hash1)
    bytes2 = bytes.fromhex(hash2)
    
    hamming_distance = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(bytes1, bytes2))
    total_bits = len(bytes1) * 8
    similarity = 1.0 - (hamming_distance / total_bits)
    
    return max(0.0, similarity)


@dataclass
class CacheMetrics:
    """缓存监控指标"""
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    request_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    avg_latency_ms: float = 0.0
    hit_latency_ms: float = 0.0
    miss_latency_ms: float = 0.0
    memory_usage_bytes: int = 0
    memory_limit_bytes: int = 0


@dataclass
class AdaptiveStrategyConfig:
    """自适应策略配置"""
    min_hit_rate_threshold: float = 0.5
    target_hit_rate: float = 0.75
    max_memory_usage_ratio: float = 0.9
    ttl_adjustment_factor: float = 0.2
    min_ttl_seconds: int = 60
    max_ttl_seconds: int = 86400
    check_interval_seconds: int = 300
    hotness_threshold: float = 0.4


@dataclass
class StrategyAdjustment:
    """策略调整建议"""
    endpoint: str
    adjustment_type: str
    previous_value: Any
    new_value: Any
    reason: str
    expected_improvement: float
    confidence: float


@dataclass
class WarmupSimulationResult:
    """预热模拟结果"""
    endpoint: str
    original_hit_rate: float
    warmed_hit_rate: float
    hit_rate_improvement: float
    warmup_duration_seconds: int
    preloaded_items_count: int
    preloaded_fields_count: int
    estimated_memory_usage_bytes: int
    latency_improvement_ms: float
    warmup_schedule: List[Dict[str, Any]]


@dataclass
class CachePenetrationProtection:
    """缓存穿透防护配置"""
    bloom_filter_enabled: bool = True
    null_value_caching: bool = True
    null_value_ttl_seconds: int = 60
    hot_data_preload: bool = True
    preload_threshold: float = 0.7
    max_preload_count: int = 1000
    rate_limit_enabled: bool = False
    rate_limit_per_second: int = 100


def calculate_cache_metrics(request_history: List[Dict[str, Any]]) -> CacheMetrics:
    """
    根据请求历史计算缓存指标
    
    Args:
        request_history: 请求历史记录列表
        
    Returns:
        CacheMetrics对象
    """
    if not request_history:
        return CacheMetrics()
    
    total = len(request_history)
    hits = sum(1 for r in request_history if r.get('cache_hit', False))
    misses = total - hits
    
    hit_latencies = [r.get('latency_ms', 0) for r in request_history if r.get('cache_hit', False)]
    miss_latencies = [r.get('latency_ms', 0) for r in request_history if not r.get('cache_hit', False)]
    
    return CacheMetrics(
        hit_rate=hits / total if total > 0 else 0.0,
        miss_rate=misses / total if total > 0 else 0.0,
        request_count=total,
        hit_count=hits,
        miss_count=misses,
        eviction_count=sum(1 for r in request_history if r.get('evicted', False)),
        avg_latency_ms=sum(r.get('latency_ms', 0) for r in request_history) / total if total > 0 else 0.0,
        hit_latency_ms=sum(hit_latencies) / len(hit_latencies) if hit_latencies else 0.0,
        miss_latency_ms=sum(miss_latencies) / len(miss_latencies) if miss_latencies else 0.0
    )


def recommend_strategy_adjustment(
    current_metrics: CacheMetrics,
    config: AdaptiveStrategyConfig,
    endpoint_stats: Dict[str, Any]
) -> List[StrategyAdjustment]:
    """
    根据当前指标推荐策略调整
    
    Args:
        current_metrics: 当前缓存指标
        config: 自适应配置
        endpoint_stats: 端点统计信息
        
    Returns:
        调整建议列表
    """
    adjustments = []
    
    hit_rate = current_metrics.hit_rate
    memory_ratio = (current_metrics.memory_usage_bytes / current_metrics.memory_limit_bytes 
                    if current_metrics.memory_limit_bytes > 0 else 0)
    
    if hit_rate < config.min_hit_rate_threshold:
        current_ttl = endpoint_stats.get('current_ttl', 300)
        new_ttl = min(config.max_ttl_seconds, int(current_ttl * (1 + config.ttl_adjustment_factor)))
        
        adjustments.append(StrategyAdjustment(
            endpoint=endpoint_stats.get('endpoint', 'unknown'),
            adjustment_type='ttl_increase',
            previous_value=current_ttl,
            new_value=new_ttl,
            reason=f"命中率过低 ({hit_rate:.1%} < {config.min_hit_rate_threshold:.1%})",
            expected_improvement=min(0.3, (config.target_hit_rate - hit_rate) * 0.5),
            confidence=0.8
        ))
    
    if memory_ratio > config.max_memory_usage_ratio:
        current_ttl = endpoint_stats.get('current_ttl', 300)
        new_ttl = max(config.min_ttl_seconds, int(current_ttl * (1 - config.ttl_adjustment_factor)))
        
        adjustments.append(StrategyAdjustment(
            endpoint=endpoint_stats.get('endpoint', 'unknown'),
            adjustment_type='ttl_decrease',
            previous_value=current_ttl,
            new_value=new_ttl,
            reason=f"内存使用率过高 ({memory_ratio:.1%} > {config.max_memory_usage_ratio:.1%})",
            expected_improvement=0.15,
            confidence=0.75
        ))
    
    hot_field_count = endpoint_stats.get('hot_field_count', 0)
    cached_field_count = endpoint_stats.get('cached_field_count', 0)
    if hot_field_count > 0 and cached_field_count / hot_field_count < 0.5:
        adjustments.append(StrategyAdjustment(
            endpoint=endpoint_stats.get('endpoint', 'unknown'),
            adjustment_type='field_cache_expansion',
            previous_value=cached_field_count,
            new_value=min(20, hot_field_count),
            reason=f"热点字段缓存覆盖率过低 ({cached_field_count}/{hot_field_count})",
            expected_improvement=0.1,
            confidence=0.65
        ))
    
    return adjustments


def simulate_cache_warmup(
    request_patterns: List[Dict[str, Any]],
    hot_data: List[Dict[str, Any]],
    warmup_duration_minutes: int = 30
) -> WarmupSimulationResult:
    """
    模拟缓存预热效果
    
    Args:
        request_patterns: 请求模式列表
        hot_data: 热点数据列表
        warmup_duration_minutes: 预定时长（分钟）
        
    Returns:
        WarmupSimulationResult
    """
    if not request_patterns:
        return WarmupSimulationResult(
            endpoint='unknown',
            original_hit_rate=0.0,
            warmed_hit_rate=0.0,
            hit_rate_improvement=0.0,
            warmup_duration_seconds=warmup_duration_minutes * 60,
            preloaded_items_count=0,
            preloaded_fields_count=0,
            estimated_memory_usage_bytes=0,
            latency_improvement_ms=0.0,
            warmup_schedule=[]
        )
    
    endpoint = request_patterns[0].get('endpoint', 'unknown')
    total_requests = len(request_patterns)
    original_hits = sum(1 for r in request_patterns if r.get('cache_hit', False))
    original_hit_rate = original_hits / total_requests
    
    hot_endpoints = set(d.get('endpoint') for d in hot_data if d.get('hotness', 0) >= 0.7)
    warmed_hits = original_hits + sum(1 for r in request_patterns 
                                     if not r.get('cache_hit', False) and r.get('endpoint') in hot_endpoints)
    warmed_hit_rate = min(0.95, warmed_hits / total_requests)
    
    total_fields = 0
    for d in hot_data:
        total_fields += len(d.get('hot_fields', []))
    
    avg_hit_latency = sum(r.get('latency_ms', 10) for r in request_patterns if r.get('cache_hit', False))
    avg_hit_latency = avg_hit_latency / original_hits if original_hits > 0 else 10
    
    avg_miss_latency = sum(r.get('latency_ms', 100) for r in request_patterns if not r.get('cache_hit', False))
    avg_miss_latency = avg_miss_latency / (total_requests - original_hits) if (total_requests - original_hits) > 0 else 100
    
    latency_improvement = (avg_miss_latency - avg_hit_latency) * (warmed_hits - original_hits) / total_requests
    
    schedule = []
    phase1_count = min(len(hot_data), int(len(hot_data) * 0.5))
    if phase1_count > 0:
        schedule.append({
            'phase': 1,
            'duration_minutes': 5,
            'items_count': phase1_count,
            'description': '第一阶段：预加载Top 50%热点数据'
        })
    
    phase2_count = len(hot_data) - phase1_count
    if phase2_count > 0:
        schedule.append({
            'phase': 2,
            'duration_minutes': warmup_duration_minutes - 5,
            'items_count': phase2_count,
            'description': '第二阶段：渐进加载剩余热点数据'
        })
    
    return WarmupSimulationResult(
        endpoint=endpoint,
        original_hit_rate=original_hit_rate,
        warmed_hit_rate=warmed_hit_rate,
        hit_rate_improvement=warmed_hit_rate - original_hit_rate,
        warmup_duration_seconds=warmup_duration_minutes * 60,
        preloaded_items_count=len(hot_data),
        preloaded_fields_count=total_fields,
        estimated_memory_usage_bytes=sum(d.get('size_bytes', 0) for d in hot_data),
        latency_improvement_ms=latency_improvement,
        warmup_schedule=schedule
    )


def identify_penetration_risks(
    request_history: List[Dict[str, Any]],
    protection_config: CachePenetrationProtection
) -> List[Dict[str, Any]]:
    """
    识别缓存穿透风险
    
    Args:
        request_history: 请求历史
        protection_config: 防护配置
        
    Returns:
        风险列表
    """
    risks = []
    
    endpoint_counts = {}
    for r in request_history:
        ep = r.get('endpoint', 'unknown')
        endpoint_counts[ep] = endpoint_counts.get(ep, 0) + 1
    
    for ep, count in endpoint_counts.items():
        ep_requests = [r for r in request_history if r.get('endpoint') == ep]
        miss_rate = sum(1 for r in ep_requests if not r.get('cache_hit', False)) / len(ep_requests)
        
        if miss_rate >= 0.9 and count >= 100:
            risks.append({
                'endpoint': ep,
                'request_count': count,
                'miss_rate': miss_rate,
                'risk_level': 'high' if miss_rate >= 0.95 else 'medium',
                'recommendation': '建议启用布隆过滤器和空值缓存'
            })
    
    return risks


def generate_preload_plan(
    hot_endpoints: List[Dict[str, Any]],
    max_preload_count: int = 100
) -> List[Dict[str, Any]]:
    """
    生成预加载计划
    
    Args:
        hot_endpoints: 热点端点列表
        max_preload_count: 最大预加载数量
        
    Returns:
        预加载计划
    """
    sorted_endpoints = sorted(
        hot_endpoints,
        key=lambda x: x.get('hotness', 0) * x.get('request_count', 0),
        reverse=True
    )[:max_preload_count]
    
    plan = []
    for i, ep in enumerate(sorted_endpoints):
        priority = 'critical' if i < len(sorted_endpoints) * 0.2 else 'high' if i < len(sorted_endpoints) * 0.5 else 'normal'
        plan.append({
            'endpoint': ep.get('endpoint'),
            'priority': priority,
            'hotness': ep.get('hotness', 0),
            'request_count': ep.get('request_count', 0),
            'estimated_size_bytes': ep.get('size_bytes', 0),
            'preload_fields': ep.get('hot_fields', []),
            'recommended_ttl': ep.get('recommended_ttl', 3600)
        })
    
    return plan

