import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from es_collector import SlowQuery

logger = logging.getLogger(__name__)


class CauseCategory(Enum):
    DEEP_PAGINATION = "deep_pagination"
    FUZZY_QUERY = "fuzzy_query"
    CACHE_MISS = "cache_miss"
    WILDCARD_QUERY = "wildcard_query"
    PREFIX_QUERY = "prefix_query"
    SCRIPT_QUERY = "script_query"
    HIGH_CARDINALITY_AGG = "high_cardinality_agg"
    TOO_MANY_SHARDS = "too_many_shards"
    COMPLEX_BOOL = "complex_bool"
    MISSING_FIELD_MAPPING = "missing_field_mapping"
    UNDEFINED = "undefined"


SEARCH_TYPE_INFO = {
    "query_then_fetch": {
        "label": "query_then_fetch (默认)",
        "deep_pag_behavior": "每个分片返回 from+size 条文档的排序值给协调节点，"
                             "协调节点合并排序后取 [from, from+size) 的文档ID，"
                             "再向相关分片拉取完整文档。深分页时协调节点内存和网络开销线性增长。",
        "phase_detail": "Phase 1: 各分片执行查询返回 from+size 个 docId/sort → "
                        "Phase 2: 协调节点合并排序取 topN → Phase 3: 按需拉取 _source",
    },
    "dfs_query_then_fetch": {
        "label": "dfs_query_then_fetch (DFS)",
        "deep_pag_behavior": "在 query_then_fetch 之前增加一个 DFS 阶段，"
                             "从所有分片收集词频和文档频率信息以优化相关性评分。"
                             "深分页时额外增加一轮全网往返(round-trip)，性能更差。"
                             "适合对评分精度要求高的场景，但深分页时更不可取。",
        "phase_detail": "Phase 0: DFS 收集各分片词频 → Phase 1-3: 同 query_then_fetch",
    },
    "scroll": {
        "label": "scroll (游标)",
        "deep_pag_behavior": "基于快照的遍历，不受深分页影响。"
                             "scroll 维护一个搜索上下文(snapshot)，每次返回下一批结果，"
                             "不再需要 from 偏移量，适合全量导出。",
        "phase_detail": "创建 scroll 上下文 → 按批次遍历 → 维护搜索上下文直到超时",
    },
    "search_after": {
        "label": "search_after (游标分页)",
        "deep_pag_behavior": "基于排序值的游标分页，不受深分页影响。"
                             "使用上一页最后一条的排序值作为游标，"
                             "ES 直接定位到该位置继续扫描，跳过 from 偏移量开销。",
        "phase_detail": "首次查询 → 取最后一条 sort 值 → 以 sort 值为游标翻页",
    },
}


@dataclass
class DiagnosisResult:
    slow_query: SlowQuery
    causes: List[CauseCategory] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    severity: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.slow_query.query_id,
            "index_name": self.slow_query.index_name,
            "response_time_ms": self.slow_query.response_time_ms,
            "causes": [c.value for c in self.causes],
            "details": self.details,
            "suggestions": self.suggestions,
            "severity": self.severity,
        }


class QueryAnalyzer:
    DEEP_PAGINATION_THRESHOLD = 5000
    COMPLEX_BOOL_CLAUSE_THRESHOLD = 20
    HIGH_CARDINALITY_THRESHOLD = 100000

    def analyze(self, slow_query: SlowQuery) -> DiagnosisResult:
        result = DiagnosisResult(slow_query=slow_query)

        self._check_deep_pagination(slow_query, result)
        self._check_fuzzy_query(slow_query, result)
        self._check_wildcard_query(slow_query, result)
        self._check_prefix_query(slow_query, result)
        self._check_script_query(slow_query, result)
        self._check_cache_status(slow_query, result)
        self._check_complex_bool(slow_query, result)
        self._check_aggregation(slow_query, result)
        self._check_shard_count(slow_query, result)
        self._check_missing_sort_field(slow_query, result)
        self._check_profile_data(slow_query, result)

        self._determine_severity(result)
        return result

    def _check_deep_pagination(self, sq: SlowQuery, result: DiagnosisResult):
        offset = sq.from_offset
        size = sq.size
        if offset + size <= self.DEEP_PAGINATION_THRESHOLD:
            return

        search_type = sq.search_type or "query_then_fetch"
        type_info = SEARCH_TYPE_INFO.get(search_type, SEARCH_TYPE_INFO["query_then_fetch"])

        is_scroll_or_after = search_type in ("scroll", "search_after")

        result.causes.append(CauseCategory.DEEP_PAGINATION)

        deep_pag_detail: Dict[str, Any] = {
            "from": offset,
            "size": size,
            "total_offset": offset + size,
            "threshold": self.DEEP_PAGINATION_THRESHOLD,
            "search_type": search_type,
            "search_type_label": type_info["label"],
            "phase_detail": type_info["phase_detail"],
        }

        if is_scroll_or_after:
            deep_pag_detail["note"] = (
                f"当前使用 {type_info['label']} 分页方式，虽然不受传统深分页影响，"
                f"但 from={offset} 表明可能仍在使用 from/size 参数，需确认是否正确使用游标。"
            )
            result.suggestions.append(
                f"深分页 + {type_info['label']}: from={offset}, size={size}, 总偏移={offset + size}。"
                f"{type_info['deep_pag_behavior']} "
                f"当前虽使用了 {type_info['label']}，但 from 参数非零，"
                f"请确认游标分页使用方式是否正确: search_after 应不设置 from，直接使用 sort 值翻页。"
            )
        else:
            deep_pag_detail["performance_impact"] = type_info["deep_pag_behavior"]
            if search_type == "dfs_query_then_fetch":
                deep_pag_detail["extra_cost"] = (
                    "DFS 阶段在深分页场景下增加一轮全网往返，"
                    "建议: 如不需要精确文档频率，改用 query_then_fetch 减少开销。"
                )
            result.suggestions.append(
                f"深分页检测: from={offset}, size={size}, 总偏移={offset + size} "
                f"超过阈值 {self.DEEP_PAGINATION_THRESHOLD}。"
                f"查询类型: {type_info['label']}，执行流程: {type_info['phase_detail']}。"
                f"性能影响: {type_info['deep_pag_behavior']}"
            )
            if search_type == "dfs_query_then_fetch":
                result.suggestions.append(
                    f"DFS + 深分页叠加影响: 当前使用 {type_info['label']}，"
                    f"深分页下 DFS 阶段增加一轮全网往返(round-trip)收集词频，"
                    f"协调节点开销 = DFS往返 + from×shards 条排序值合并。"
                    f"建议: (1) 如不需要精确 TF/IDF 评分，改用 query_then_fetch; "
                    f"(2) 切换到 search_after 游标分页; (3) 使用 scroll API 批量导出。"
                )
            else:
                result.suggestions.append(
                    f"建议使用 search_after 替代 from/size 分页，或使用 scroll API 批量导出数据。"
                    f"search_after 优势: 不需要 from 偏移量，基于排序值直接定位，"
                    f"内存开销恒定不受页码影响。scroll 优势: 基于快照遍历，适合全量导出。"
                )

        result.details["deep_pagination"] = deep_pag_detail

    def _check_fuzzy_query(self, sq: SlowQuery, result: DiagnosisResult):
        fuzzy_found = self._find_in_query(sq.query_body, "fuzzy")
        if fuzzy_found:
            result.causes.append(CauseCategory.FUZZY_QUERY)
            result.details["fuzzy_query"] = {
                "locations": fuzzy_found,
                "note": "fuzzy 查询需要计算编辑距离，性能开销大",
            }
            result.suggestions.append(
                "模糊查询检测: 查询中包含 fuzzy 子句。"
                "建议: (1) 使用 edge_ngram 或 completion suggester 替代 fuzzy 实现搜索建议; "
                "(2) 限制 fuzziness 参数为 1; (3) 对模糊搜索字段设置专用映射。"
            )

    def _check_wildcard_query(self, sq: SlowQuery, result: DiagnosisResult):
        wildcard_found = self._find_in_query(sq.query_body, "wildcard")
        if not wildcard_found:
            return
        result.causes.append(CauseCategory.WILDCARD_QUERY)

        has_leading_wildcard = False
        leading_locations = []
        for loc in wildcard_found:
            wc_val = self._extract_query_value(sq.query_body, loc)
            if isinstance(wc_val, str) and wc_val.startswith("*"):
                has_leading_wildcard = True
                leading_locations.append(loc)

        detail: Dict[str, Any] = {"locations": wildcard_found}
        if has_leading_wildcard:
            detail["has_leading_wildcard"] = True
            detail["leading_wildcard_locations"] = leading_locations

        result.details["wildcard_query"] = detail

        base_suggestion = (
            "通配符查询检测: 查询中包含 wildcard 子句，尤其是前缀通配符(*xxx)会导致全索引扫描。"
        )
        edge_ngram_suggestion = (
            "建议改用 edge_ngram 索引方案: "
            "(1) 在索引映射中为该字段添加 edge_ngram 子字段 analyzer; "
            "(2) 示例映射: {'type': 'text', 'analyzer': 'custom_edge_ngram'}，"
            "其中 analyzer 使用 edge_ngram tokenizer (min_gram=2, max_gram=20); "
            "(3) 查询时改用 match 查询替代 wildcard，性能提升数十倍; "
            "(4) edge_ngram 将所有前缀子串预建索引，空间换时间。"
        )
        if has_leading_wildcard:
            result.suggestions.append(
                base_suggestion +
                "当前检测到前缀通配符(leading wildcard)，影响最严重。" +
                edge_ngram_suggestion +
                "临时方案: (1) 避免 leading wildcard; (2) 使用 ngram tokenizer 替代; "
                "(3) 考虑使用 prefix query 替代 trailing wildcard (*xxx → prefix query)。"
            )
        else:
            result.suggestions.append(
                base_suggestion +
                edge_ngram_suggestion +
                "同时可考虑: (1) 使用 prefix query 替代 trailing wildcard; "
                "(2) 使用 ngram tokenizer 替代中间通配符。"
            )

    def _check_prefix_query(self, sq: SlowQuery, result: DiagnosisResult):
        prefix_found = self._find_in_query(sq.query_body, "prefix")
        if not prefix_found:
            return
        result.causes.append(CauseCategory.PREFIX_QUERY)

        prefix_fields = []
        for loc in prefix_found:
            val = self._extract_query_value(sq.query_body, loc)
            prefix_fields.append({"location": loc, "value": val})

        result.details["prefix_query"] = {
            "locations": prefix_found,
            "fields": prefix_fields,
            "note": "prefix query 对未优化字段会执行倒排词典全扫描(scan-and-seek)",
        }
        result.suggestions.append(
            "前缀匹配查询检测: 查询中包含 prefix 子句。"
            "prefix query 在未优化字段上会执行倒排索引词典扫描(scan-and-seek)，"
            "时间复杂度与词典大小正相关，数据量大时性能很差。"
            "强烈建议改用 edge_ngram 方案: "
            "(1) 为需要前缀搜索的字段添加 edge_ngram 类型子字段; "
            "(2) 映射示例: "
            "'title': {'type': 'text', 'fields': {'edge_ngram': {'type': 'text', "
            "'analyzer': 'edge_ngram_analyzer'}}}; "
            "(3) 定义 analyzer: {'tokenizer': {'type': 'edge_ngram', 'min_gram': 2, 'max_gram': 20}}; "
            "(4) 查询时对子字段使用 match 查询: {'match': {'title.edge_ngram': '搜索词'}}; "
            "(5) edge_ngram 将所有前缀预建为独立 token，查询退化为精确匹配 O(1)。"
        )

    def _check_script_query(self, sq: SlowQuery, result: DiagnosisResult):
        script_found = self._find_in_query(sq.query_body, "script")
        if script_found:
            result.causes.append(CauseCategory.SCRIPT_QUERY)
            result.details["script_query"] = {
                "locations": script_found,
            }
            result.suggestions.append(
                "脚本查询检测: 查询中包含 script 子句，脚本无法利用倒排索引且无法缓存。"
                "建议: (1) 使用 function_score + field_value_factor 替代脚本排序; "
                "(2) 使用 runtime fields 预计算; (3) 如必须使用脚本，使用 painless 并开启缓存。"
            )

    def _check_cache_status(self, sq: SlowQuery, result: DiagnosisResult):
        if sq.cache_hit is False:
            result.causes.append(CauseCategory.CACHE_MISS)
            result.details["cache_miss"] = {
                "note": "查询未命中请求缓存",
            }
            result.suggestions.append(
                "缓存未命中检测: 查询未命中 ES 请求缓存(request cache)。"
                "建议: (1) 确认 index.requests.cache.enable=true; "
                "(2) 对相同查询参数使用 size=0 的聚合查询可被缓存; "
                "(3) 避免在查询中使用 now、random 等无法缓存的函数; "
                "(4) 检查分片大小是否过小导致缓存效率低。"
            )

    def _check_complex_bool(self, sq: SlowQuery, result: DiagnosisResult):
        clause_count = self._count_bool_clauses(sq.query_body)
        if clause_count > self.COMPLEX_BOOL_CLAUSE_THRESHOLD:
            result.causes.append(CauseCategory.COMPLEX_BOOL)
            result.details["complex_bool"] = {
                "clause_count": clause_count,
                "threshold": self.COMPLEX_BOOL_CLAUSE_THRESHOLD,
            }
            result.suggestions.append(
                f"复杂布尔查询检测: bool 查询包含 {clause_count} 个子句，"
                f"超过阈值 {self.COMPLEX_BOOL_CLAUSE_THRESHOLD}。"
                f"建议: (1) 拆分为多个简单查询; (2) 使用 filter 上下文替代 must 提升性能; "
                f"(3) 利用 terms query 批量替代多个 term 组合; (4) 考虑使用 percolate query。"
            )

    def _check_aggregation(self, sq: SlowQuery, result: DiagnosisResult):
        aggs = sq.query_body.get("aggs") or sq.query_body.get("aggregations")
        if not aggs:
            return
        agg_types = self._extract_agg_types(aggs)
        high_card_aggs = [t for t in agg_types if t in ("terms", "cardinality", "composite")]
        nested_count = self._count_nested_aggs(aggs)

        if high_card_aggs and sq.hits_total > self.HIGH_CARDINALITY_THRESHOLD:
            result.causes.append(CauseCategory.HIGH_CARDINALITY_AGG)
            result.details["high_cardinality_agg"] = {
                "agg_types": high_card_aggs,
                "hits_total": sq.hits_total,
                "nested_depth": nested_count,
            }
            result.suggestions.append(
                f"高基数聚合检测: 查询包含 {high_card_aggs} 类型聚合，"
                f"且匹配文档数 {sq.hits_total} 超过阈值 {self.HIGH_CARDINALITY_THRESHOLD}。"
                f"建议: (1) 使用 sampler 聚合先采样再聚合; "
                f"(2) 对 terms 聚合设置合理的 size 参数; "
                f"(3) 考虑预聚合 (rollup) 或使用 transforms; (4) 减少嵌套聚合深度。"
            )

    def _check_shard_count(self, sq: SlowQuery, result: DiagnosisResult):
        if sq.total_shards > 50:
            result.causes.append(CauseCategory.TOO_MANY_SHARDS)
            result.details["too_many_shards"] = {
                "total_shards": sq.total_shards,
                "successful_shards": sq.successful_shards,
            }
            result.suggestions.append(
                f"分片过多检测: 查询涉及 {sq.total_shards} 个分片，"
                f"分片过多会增加协调节点开销和合并成本。"
                f"建议: (1) 使用索引路由 (routing) 减少分片扫描; "
                f"(2) 合并小索引或使用 shrink API; "
                f"(3) 控制单分片大小在 10-50GB; (4) 使用索引别名隔离热冷数据。"
            )

    def _check_missing_sort_field(self, sq: SlowQuery, result: DiagnosisResult):
        sort = sq.query_body.get("sort")
        if not sort:
            return
        profile_data = sq.profile_data
        if not profile_data:
            return
        for shard in profile_data.get("shards", []):
            for search in shard.get("searches", []):
                for rewrite in search.get("rewrite_time", []):
                    pass
                for coll in search.get("collector", []):
                    if "SortedFloat" in coll.get("name", "") or "SortedTopDocs" in coll.get("name", ""):
                        if not self._has_doc_values_for_sort(sq, sort):
                            result.details["missing_sort_field"] = {
                                "sort_fields": sort,
                                "note": "排序字段可能未启用 doc_values",
                            }
                            result.suggestions.append(
                                "排序字段检测: 排序可能使用了未启用 doc_values 的字段（如 text 类型），"
                                "导致需要 fielddata 加载。"
                                "建议: (1) 为排序字段启用 doc_values; (2) 使用 keyword 子字段排序; "
                                "(3) 避免对 text 字段排序。"
                            )
                            return

    def _check_profile_data(self, sq: SlowQuery, result: DiagnosisResult):
        if not sq.profile_data:
            return
        slow_shards = []
        for shard in sq.profile_data.get("shards", []):
            shard_id = shard.get("id", "")
            searches = shard.get("searches", [])
            for search in searches:
                query_time = search.get("query_time_in_nanos", 0) / 1_000_000
                if query_time > sq.response_time_ms * 0.5:
                    slow_shards.append({
                        "shard_id": shard_id,
                        "query_time_ms": round(query_time, 2),
                        "ratio": round(query_time / max(sq.response_time_ms, 1), 2),
                    })
        if slow_shards:
            result.details["slow_shards"] = slow_shards
            for ss in slow_shards:
                if ss["ratio"] > 0.8:
                    result.suggestions.append(
                        f"热点分片检测: 分片 {ss['shard_id']} 耗时 {ss['query_time_ms']}ms，"
                        f"占总时间 {ss['ratio']*100:.0f}%。"
                        f"建议检查该分片数据分布是否倾斜，考虑重新分片或调整路由策略。"
                    )
                    break

    def _determine_severity(self, result: DiagnosisResult):
        rt = result.slow_query.response_time_ms
        cause_count = len(result.causes)

        critical_causes = {CauseCategory.DEEP_PAGINATION, CauseCategory.SCRIPT_QUERY}
        if rt > 30000 or (cause_count >= 3 and rt > 10000) or bool(critical_causes & set(result.causes) and rt > 10000):
            result.severity = "critical"
        elif rt > 10000 or cause_count >= 2:
            result.severity = "high"
        elif rt > 3000 or cause_count >= 1:
            result.severity = "medium"
        else:
            result.severity = "low"

    @staticmethod
    def _find_in_query(query_body: Dict[str, Any], key: str) -> List[str]:
        results = []
        QueryAnalyzer._walk_query(query_body, key, results, path="")
        return results

    @staticmethod
    def _walk_query(obj: Any, target_key: str, results: List[str], path: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                if k == target_key:
                    results.append(current_path)
                QueryAnalyzer._walk_query(v, target_key, results, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                QueryAnalyzer._walk_query(item, target_key, results, f"{path}[{i}]")

    @staticmethod
    def _count_bool_clauses(query_body: Dict[str, Any]) -> int:
        count = 0
        for key in ("must", "must_not", "should", "filter"):
            clauses = query_body.get("query", {}).get("bool", {}).get(key, [])
            count += len(clauses) if isinstance(clauses, list) else (1 if clauses else 0)
        return count

    @staticmethod
    def _extract_agg_types(aggs: Dict[str, Any]) -> Set[str]:
        types = set()
        for agg_name, agg_def in aggs.items():
            for k, v in agg_def.items():
                if k != "aggs" and k != "aggregations":
                    types.add(k)
                if k in ("aggs", "aggregations") and isinstance(v, dict):
                    types.update(QueryAnalyzer._extract_agg_types(v))
        return types

    @staticmethod
    def _count_nested_aggs(aggs: Dict[str, Any], depth: int = 0) -> int:
        max_depth = depth
        for agg_name, agg_def in aggs.items():
            sub_aggs = agg_def.get("aggs") or agg_def.get("aggregations")
            if sub_aggs:
                d = QueryAnalyzer._count_nested_aggs(sub_aggs, depth + 1)
                max_depth = max(max_depth, d)
        return max_depth

    @staticmethod
    def _has_doc_values_for_sort(sq: SlowQuery, sort: Any) -> bool:
        return True

    @staticmethod
    def _extract_query_value(query_body: Dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        current: Any = query_body
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None
            elif isinstance(current, list):
                try:
                    idx = int(part.strip("[]"))
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        if isinstance(current, dict):
            for v in current.values():
                if isinstance(v, (str, int, float)):
                    return v
                if isinstance(v, dict) and "value" in v:
                    return v["value"]
        return current
