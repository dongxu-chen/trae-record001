import hashlib
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from es_collector import SlowQuery

logger = logging.getLogger(__name__)


class CacheType(Enum):
    REQUEST_CACHE = "request_cache"
    FIELD_DATA_CACHE = "field_data_cache"
    QUERY_CACHE = "query_cache"
    SHARD_REQUEST_CACHE = "shard_request_cache"


class CacheRecommendationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QueryCacheStats:
    query_hash: str
    index_name: str
    total_executions: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    last_executed: float = 0.0
    estimated_size_bytes: int = 0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / max(total, 1)

    def record(self, response_ms: float, cache_hit: Optional[bool]):
        self.total_executions += 1
        self.total_time_ms += response_ms
        self.avg_time_ms = self.total_time_ms / self.total_executions
        self.last_executed = time.time()
        if cache_hit is True:
            self.cache_hits += 1
        elif cache_hit is False:
            self.cache_misses += 1


@dataclass
class IndexCacheStats:
    index_name: str
    request_cache_hit_count: int = 0
    request_cache_miss_count: int = 0
    request_cache_evictions: int = 0
    request_cache_size_bytes: int = 0
    field_data_cache_size_bytes: int = 0
    field_data_cache_evictions: int = 0
    query_cache_hit_count: int = 0
    query_cache_miss_count: int = 0
    query_cache_evictions: int = 0

    @property
    def request_cache_hit_rate(self) -> float:
        total = self.request_cache_hit_count + self.request_cache_miss_count
        return self.request_cache_hit_count / max(total, 1)

    @property
    def query_cache_hit_rate(self) -> float:
        total = self.query_cache_hit_count + self.query_cache_miss_count
        return self.query_cache_hit_count / max(total, 1)


@dataclass
class CacheRecommendation:
    priority: CacheRecommendationPriority
    title: str
    description: str
    target_cache: Optional[CacheType] = None
    estimated_improvement_pct: float = 0.0
    estimated_savings_ms_per_query: float = 0.0
    settings_changes: Dict[str, Any] = field(default_factory=dict)
    mapping_changes: Dict[str, Any] = field(default_factory=dict)
    query_changes: List[Dict[str, Any]] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class CacheAnalysisReport:
    overall_hit_rate: float
    overall_miss_rate: float
    cache_usage_gb: float
    eviction_rate: float
    recommendations: List[CacheRecommendation] = field(default_factory=list)
    per_index_stats: Dict[str, IndexCacheStats] = field(default_factory=dict)
    top_miss_queries: List[Tuple[str, QueryCacheStats]] = field(default_factory=list)
    top_time_consuming_queries: List[Tuple[str, QueryCacheStats]] = field(default_factory=list)

    def to_text(self) -> str:
        priority_icons = {
            CacheRecommendationPriority.LOW: "🔵",
            CacheRecommendationPriority.MEDIUM: "🟡",
            CacheRecommendationPriority.HIGH: "🟠",
            CacheRecommendationPriority.CRITICAL: "🔴",
        }

        lines = [
            "=" * 70,
            "💾 ES 查询缓存分析与优化建议报告",
            "=" * 70,
            "",
            "📊 整体缓存指标:",
            f"  请求缓存命中率: {self.overall_hit_rate * 100:.1f}%",
            f"  请求缓存未命中率: {self.overall_miss_rate * 100:.1f}%",
            f"  缓存使用量: {self.cache_usage_gb:.2f} GB",
            f"  缓存驱逐率: {self.eviction_rate * 100:.1f}%",
            "",
        ]

        if self.per_index_stats:
            lines.append("📈 按索引缓存统计:")
            for idx, stats in sorted(
                self.per_index_stats.items(),
                key=lambda x: x[1].request_cache_hit_rate,
            ):
                lines.append(
                    f"  - {idx}: 请求缓存命中 {stats.request_cache_hit_rate * 100:.1f}%, "
                    f"查询缓存命中 {stats.query_cache_hit_rate * 100:.1f}%, "
                    f"缓存大小 {stats.request_cache_size_bytes / 1024 / 1024:.1f} MB"
                )
            lines.append("")

        if self.top_miss_queries:
            lines.append("⚠ TOP 缓存未命中查询:")
            for qhash, stats in self.top_miss_queries[:5]:
                lines.append(
                    f"  - {qhash[:12]}... | 索引: {stats.index_name}, "
                    f"命中率: {stats.cache_hit_rate * 100:.0f}%, "
                    f"执行: {stats.total_executions}次, 平均: {stats.avg_time_ms:.0f}ms"
                )
            lines.append("")

        if self.top_time_consuming_queries:
            lines.append("⏱ TOP 耗时查询:")
            for qhash, stats in self.top_time_consuming_queries[:5]:
                lines.append(
                    f"  - {qhash[:12]}... | 索引: {stats.index_name}, "
                    f"总耗时: {stats.total_time_ms:.0f}ms, "
                    f"平均: {stats.avg_time_ms:.0f}ms, 执行: {stats.total_executions}次"
                )
            lines.append("")

        if self.recommendations:
            lines.append("💡 优化建议 (按优先级排序):")
            for i, rec in enumerate(self.recommendations, 1):
                icon = priority_icons.get(rec.priority, "⚪")
                lines.append(
                    f"  {icon} [{rec.priority.value.upper()}] 建议 {i}: {rec.title}"
                )
                lines.append(f"     {rec.description}")
                if rec.estimated_improvement_pct > 0:
                    lines.append(f"     预估提升: {rec.estimated_improvement_pct:.0f}%")
                if rec.estimated_savings_ms_per_query > 0:
                    lines.append(f"     预估节省: {rec.estimated_savings_ms_per_query:.0f}ms/查询")
                if rec.settings_changes:
                    lines.append(f"     设置变更: {json.dumps(rec.settings_changes, ensure_ascii=False)}")
                if rec.mapping_changes:
                    lines.append(f"     映射变更: {json.dumps(rec.mapping_changes, ensure_ascii=False)}")
                if rec.prerequisites:
                    lines.append("     前置条件:")
                    for pre in rec.prerequisites:
                        lines.append(f"       * {pre}")
                if rec.risks:
                    lines.append("     注意风险:")
                    for risk in rec.risks:
                        lines.append(f"       ⚠ {risk}")
                lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)


class CacheOptimizer:
    def __init__(self,
                 min_queries_for_analysis: int = 5,
                 min_savings_for_recommendation_ms: float = 100.0):
        self.min_queries_for_analysis = min_queries_for_analysis
        self.min_savings_for_recommendation_ms = min_savings_for_recommendation_ms

        self.query_stats: Dict[str, QueryCacheStats] = {}
        self.index_stats: Dict[str, IndexCacheStats] = {}
        self.total_requests: int = 0
        self.total_cache_hits: int = 0
        self.total_cache_misses: int = 0
        self.total_evictions: int = 0
        self.total_cache_size_bytes: int = 0

    def record_query(self, slow_query: SlowQuery):
        self.total_requests += 1

        qhash = self._hash_query(slow_query)
        if qhash not in self.query_stats:
            self.query_stats[qhash] = QueryCacheStats(
                query_hash=qhash,
                index_name=slow_query.index_name,
            )
        self.query_stats[qhash].record(slow_query.response_time_ms, slow_query.cache_hit)

        if slow_query.cache_hit is True:
            self.total_cache_hits += 1
        elif slow_query.cache_hit is False:
            self.total_cache_misses += 1

        if slow_query.index_name not in self.index_stats:
            self.index_stats[slow_query.index_name] = IndexCacheStats(
                index_name=slow_query.index_name,
            )
        idx_stats = self.index_stats[slow_query.index_name]
        if slow_query.cache_hit is True:
            idx_stats.request_cache_hit_count += 1
        elif slow_query.cache_hit is False:
            idx_stats.request_cache_miss_count += 1

    def update_from_es_stats(self, index_name: str, es_stats: Dict[str, Any]):
        if index_name not in self.index_stats:
            self.index_stats[index_name] = IndexCacheStats(index_name=index_name)
        stats = self.index_stats[index_name]

        total_stats = es_stats.get("total", {})
        request_cache = total_stats.get("request_cache", {})
        field_data = total_stats.get("fielddata", {})
        query_cache = total_stats.get("query_cache", {})

        stats.request_cache_hit_count += request_cache.get("hit_count", 0)
        stats.request_cache_miss_count += request_cache.get("miss_count", 0)
        stats.request_cache_evictions += request_cache.get("evictions", 0)
        stats.request_cache_size_bytes += request_cache.get("memory_size_in_bytes", 0)
        stats.field_data_cache_size_bytes += field_data.get("memory_size_in_bytes", 0)
        stats.field_data_cache_evictions += field_data.get("evictions", 0)
        stats.query_cache_hit_count += query_cache.get("hit_count", 0)
        stats.query_cache_miss_count += query_cache.get("miss_count", 0)
        stats.query_cache_evictions += query_cache.get("evictions", 0)

        self.total_cache_hits += stats.request_cache_hit_count
        self.total_cache_misses += stats.request_cache_miss_count
        self.total_evictions += stats.request_cache_evictions
        self.total_cache_size_bytes += stats.request_cache_size_bytes

    def analyze(self) -> CacheAnalysisReport:
        overall_hits = self.total_cache_hits
        overall_misses = self.total_cache_misses
        overall_total = overall_hits + overall_misses
        overall_hit_rate = overall_hits / max(overall_total, 1)
        overall_miss_rate = overall_misses / max(overall_total, 1)
        cache_usage_gb = self.total_cache_size_bytes / 1024 / 1024 / 1024
        eviction_rate = self.total_evictions / max(overall_total, 1)

        recommendations = self._generate_recommendations(overall_hit_rate, overall_miss_rate)

        top_miss = sorted(
            self.query_stats.items(),
            key=lambda x: x[1].cache_misses,
            reverse=True,
        )[:10]

        top_time = sorted(
            self.query_stats.items(),
            key=lambda x: x[1].total_time_ms,
            reverse=True,
        )[:10]

        return CacheAnalysisReport(
            overall_hit_rate=overall_hit_rate,
            overall_miss_rate=overall_miss_rate,
            cache_usage_gb=cache_usage_gb,
            eviction_rate=eviction_rate,
            recommendations=recommendations,
            per_index_stats=self.index_stats,
            top_miss_queries=top_miss,
            top_time_consuming_queries=top_time,
        )

    def _generate_recommendations(
        self,
        overall_hit_rate: float,
        overall_miss_rate: float,
    ) -> List[CacheRecommendation]:
        recs: List[CacheRecommendation] = []

        if overall_hit_rate < 0.10:
            recs.append(CacheRecommendation(
                priority=CacheRecommendationPriority.CRITICAL,
                title="紧急开启请求缓存",
                description=(
                    f"当前请求缓存命中率仅为 {overall_hit_rate * 100:.1f}%，"
                    f"远低于健康阈值 (建议 > 30%)。缓存未命中导致每个查询都需要重新计算结果，"
                    f"严重影响集群性能。"
                ),
                target_cache=CacheType.REQUEST_CACHE,
                estimated_improvement_pct=50.0,
                estimated_savings_ms_per_query=200.0,
                settings_changes={
                    "index.requests.cache.enable": True,
                    "index.requests.cache.size": "10%",
                },
                prerequisites=[
                    "确认 ES 版本支持 request cache (2.x+)",
                    "确认节点有足够内存分配给缓存",
                ],
                risks=[
                    "开启缓存会增加节点内存占用，需监控内存使用率",
                    "对于动态查询(含 now/random)，缓存不会生效",
                ],
            ))
        elif overall_hit_rate < 0.30:
            recs.append(CacheRecommendation(
                priority=CacheRecommendationPriority.HIGH,
                title="请求缓存命中率偏低，建议优化",
                description=(
                    f"当前请求缓存命中率为 {overall_hit_rate * 100:.1f}%，"
                    f"低于建议的 30%。可能的原因: 1) 查询中包含动态函数(now/random)；"
                    f"2) 查询模式变化大，缺少重复查询；3) 缓存大小不足导致频繁驱逐。"
                ),
                target_cache=CacheType.REQUEST_CACHE,
                estimated_improvement_pct=30.0,
                estimated_savings_ms_per_query=100.0,
                settings_changes={
                    "index.requests.cache.size": "15%",
                },
                prerequisites=[
                    "检查查询是否包含 now/rand 等不可缓存函数",
                    "检查缓存驱逐率是否过高",
                ],
                risks=[
                    "增大缓存可能增加 GC 压力",
                ],
            ))

        if self.total_evictions > self.total_cache_hits * 0.1:
            recs.append(CacheRecommendation(
                priority=CacheRecommendationPriority.HIGH,
                title="缓存驱逐率过高，建议增大缓存",
                description=(
                    f"当前缓存驱逐率为 {self.total_evictions / max(self.total_cache_hits + self.total_cache_misses, 1) * 100:.1f}%，"
                    f"超过 10% 的阈值。这意味着缓存大小不足以容纳热点数据，"
                    f"频繁驱逐会增加 GC 压力并降低缓存命中率。"
                ),
                target_cache=CacheType.REQUEST_CACHE,
                estimated_improvement_pct=25.0,
                estimated_savings_ms_per_query=80.0,
                settings_changes={
                    "indices.requests.cache.size": "20%",
                },
                prerequisites=[
                    "确认节点有足够内存",
                    "监控节点 heap 使用情况",
                ],
                risks=[
                    "增大缓存需确保有足够的堆内存",
                ],
            ))

        for idx, stats in self.index_stats.items():
            if stats.request_cache_hit_count + stats.request_cache_miss_count < self.min_queries_for_analysis:
                continue
            if stats.request_cache_hit_rate < 0.10:
                recs.append(CacheRecommendation(
                    priority=CacheRecommendationPriority.HIGH,
                    title=f"索引 [{idx}] 请求缓存未命中",
                    description=(
                        f"索引 {idx} 的请求缓存命中率仅为 {stats.request_cache_hit_rate * 100:.1f}%。"
                        f"如该索引有大量重复聚合查询(size=0)，请确认请求缓存已开启。"
                    ),
                    target_cache=CacheType.REQUEST_CACHE,
                    estimated_improvement_pct=40.0,
                    estimated_savings_ms_per_query=150.0,
                    settings_changes={
                        "index.requests.cache.enable": True,
                    },
                    prerequisites=[],
                    risks=[],
                ))
            if stats.field_data_cache_evictions > 0:
                recs.append(CacheRecommendation(
                    priority=CacheRecommendationPriority.MEDIUM,
                    title=f"索引 [{idx}] FieldData 缓存驱逐",
                    description=(
                        f"索引 {idx} 已发生 {stats.field_data_cache_evictions} 次 FieldData 缓存驱逐。"
                        f"FieldData 用于 text 字段的排序/聚合，未启用 doc_values 的 text 字段会触发 fielddata 加载，"
                        f"消耗大量内存。"
                    ),
                    target_cache=CacheType.FIELD_DATA_CACHE,
                    estimated_improvement_pct=35.0,
                    estimated_savings_ms_per_query=120.0,
                    settings_changes={
                        "indices.fielddata.cache.size": "20%",
                    },
                    mapping_changes={
                        "建议": "为排序/聚合字段使用 keyword 类型或启用 doc_values",
                    },
                    prerequisites=[],
                    risks=[
                        "增大 fielddata 缓存可能增加堆内存压力",
                        "根本解决方法是优化字段映射，避免对 text 字段排序/聚合",
                    ],
                ))

        high_cost_low_hit = [
            (qhash, stats) for qhash, stats in self.query_stats.items()
            if stats.total_executions >= self.min_queries_for_analysis
            and stats.cache_hit_rate < 0.20
            and stats.avg_time_ms > self.min_savings_for_recommendation_ms
        ]
        if high_cost_low_hit:
            for qhash, stats in high_cost_low_hit[:3]:
                recs.append(CacheRecommendation(
                    priority=CacheRecommendationPriority.MEDIUM,
                    title=f"优化高频慢查询 {qhash[:12]}...",
                    description=(
                        f"该查询在索引 {stats.index_name} 上执行了 {stats.total_executions} 次，"
                        f"缓存命中率仅 {stats.cache_hit_rate * 100:.0f}%，"
                        f"平均耗时 {stats.avg_time_ms:.0f}ms，累计耗时 {stats.total_time_ms:.0f}ms。"
                        f"如果该查询不包含动态参数，建议调整为可缓存的查询模式。"
                    ),
                    estimated_improvement_pct=30.0,
                    estimated_savings_ms_per_query=stats.avg_time_ms * 0.5,
                    query_changes=[
                        {
                            "建议": "确认查询是否可缓存",
                            "检查项": [
                                "size=0 (仅聚合)",
                                "不包含 now/rand 等函数",
                                "查询参数固定",
                                "使用 preference=_local 可能影响缓存",
                            ],
                        }
                    ],
                    prerequisites=[],
                    risks=[],
                ))

        slow_queries_without_cache = [
            (qhash, stats) for qhash, stats in self.query_stats.items()
            if stats.total_executions >= self.min_queries_for_analysis
            and stats.avg_time_ms > self.min_savings_for_recommendation_ms * 2
        ]
        if slow_queries_without_cache:
            recs.append(CacheRecommendation(
                priority=CacheRecommendationPriority.LOW,
                title="为高频慢查询考虑应用层缓存",
                description=(
                    f"检测到 {len(slow_queries_without_cache)} 个高频慢查询无法有效利用 ES 缓存，"
                    f"建议在应用层增加缓存(Redis/Memcached)进一步降低延迟。"
                ),
                estimated_improvement_pct=70.0,
                estimated_savings_ms_per_query=500.0,
                prerequisites=[
                    "业务可接受一定的数据延迟",
                    "有应用层缓存基础设施",
                    "能够处理缓存一致性问题",
                ],
                risks=[
                    "需要处理缓存失效和一致性问题",
                    "增加系统复杂度",
                ],
            ))

        recs.sort(key=lambda r: (
            CacheRecommendationPriority[r.priority.upper()].value
            if isinstance(r.priority, str) else r.priority.value
        ), reverse=False)

        return recs

    @staticmethod
    def _hash_query(slow_query: SlowQuery) -> str:
        body = {
            "index": slow_query.index_name,
            "from": slow_query.from_offset,
            "size": slow_query.size,
            "sort": slow_query.query_body.get("sort"),
            "query": slow_query.query_body.get("query"),
            "aggs": slow_query.query_body.get("aggs") or slow_query.query_body.get("aggregations"),
            "search_type": slow_query.search_type,
        }
        json_str = json.dumps(body, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode("utf-8")).hexdigest()

    def get_query_similarity(
        self,
        q1: Dict[str, Any],
        q2: Dict[str, Any],
    ) -> float:
        s1 = json.dumps(q1, sort_keys=True, default=str)
        s2 = json.dumps(q2, sort_keys=True, default=str)
        if s1 == s2:
            return 1.0
        set1 = set(s1)
        set2 = set(s2)
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / max(len(union), 1)
