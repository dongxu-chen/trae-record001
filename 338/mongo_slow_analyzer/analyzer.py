from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

from .log_parser import extract_query_pattern


def aggregate_by_pattern(entries: Iterable[Dict]) -> List[Dict]:
    """按查询模式聚合，统计次数/平均/最大耗时等。"""
    buckets: Dict[str, Dict] = defaultdict(lambda: {
        "pattern": "",
        "ns": "",
        "op": "",
        "count": 0,
        "total_ms": 0,
        "max_ms": 0,
        "min_ms": None,
        "avg_ms": 0,
        "docsExamined": 0,
        "keysExamined": 0,
        "nreturned": 0,
        "plans": set(),
        "samples": [],
    })
    for entry in entries:
        try:
            pattern = extract_query_pattern(entry)
        except Exception:
            continue
        bucket = buckets[pattern]
        bucket["pattern"] = pattern
        bucket["ns"] = entry.get("ns") or bucket["ns"]
        bucket["op"] = entry.get("op") or bucket["op"]
        duration = int(entry.get("duration") or entry.get("millis") or 0)
        bucket["count"] += 1
        bucket["total_ms"] += duration
        if duration > bucket["max_ms"]:
            bucket["max_ms"] = duration
        if bucket["min_ms"] is None or duration < bucket["min_ms"]:
            bucket["min_ms"] = duration
        bucket["docsExamined"] += int(entry.get("docsExamined", 0) or 0)
        bucket["keysExamined"] += int(entry.get("keysExamined", 0) or 0)
        bucket["nreturned"] += int(entry.get("nreturned", 0) or 0)
        plan = entry.get("planSummary") or "UNKNOWN"
        bucket["plans"].add(str(plan).split(" ")[0] if plan else "UNKNOWN")
        if len(bucket["samples"]) < 3:
            bucket["samples"].append({
                "ts": entry.get("ts"),
                "duration": duration,
                "filter": entry.get("filter"),
                "sort": entry.get("sort"),
                "raw": entry.get("raw"),
            })
    result = []
    for _, b in buckets.items():
        b["avg_ms"] = round(b["total_ms"] / b["count"], 2) if b["count"] else 0
        b["plans"] = sorted(b["plans"])
        result.append(b)
    return result


def rank_slow_queries(entries: Iterable[Dict], by: str = "total_ms", limit: int = 50) -> List[Dict]:
    """慢查询排名，支持按 total_ms / max_ms / avg_ms / count 排序。"""
    aggregated = aggregate_by_pattern(entries)
    key = by if by in ("total_ms", "max_ms", "avg_ms", "count") else "total_ms"
    aggregated.sort(key=lambda x: x[key], reverse=True)
    return aggregated[:limit]


# ---------------------------------------------------------------------------
# 字段选择性估计
# ---------------------------------------------------------------------------

def _estimate_field_selectivity(entries: List[Dict]) -> Dict[str, Dict]:
    """基于慢查询样本估计每个字段的选择性。

    对每个 filter 字段，统计：
      - distinct_count: 样本中出现的不同值数量（越高选择性越高）
      - query_count:   涉及该字段的慢查询次数
      - selectivity_score: distinct_count * log(query_count + 1)
    """
    field_values: Dict[str, set] = defaultdict(set)
    field_query_count: Dict[str, int] = defaultdict(int)

    for entry in entries:
        filter_doc = entry.get("filter") or {}
        sort_doc = entry.get("sort") or {}
        if not isinstance(filter_doc, dict):
            filter_doc = {}
        if not isinstance(sort_doc, dict):
            sort_doc = {}

        for field, val in filter_doc.items():
            if field.startswith("$"):
                continue
            field_query_count[field] += 1
            if isinstance(val, dict):
                for op, v in val.items():
                    if op in ("$gt", "$gte", "$lt", "$lte", "$ne", "$regex"):
                        field_values[field].add(repr(v))
                    elif op in ("$in", "$nin", "$all") and isinstance(v, list):
                        for item in v:
                            field_values[field].add(repr(item))
                    break
            elif isinstance(val, list):
                for item in val:
                    field_values[field].add(repr(item))
            else:
                field_values[field].add(repr(val))

        for field in sort_doc.keys():
            if field.startswith("$"):
                continue
            field_query_count[field] += 1

    result: Dict[str, Dict] = {}
    for field in field_query_count:
        distinct = len(field_values.get(field, set()))
        qc = field_query_count[field]
        result[field] = {
            "distinct_count": distinct,
            "query_count": qc,
            "selectivity_score": round(distinct * math.log(qc + 1), 2),
        }
    return result


# ---------------------------------------------------------------------------
# 索引建议（含字段选择性排序与 ESR 顺序指导）
# ---------------------------------------------------------------------------

def suggest_indexes(
    entries: Iterable[Dict],
    existing_indexes: List[Dict] | None = None,
) -> List[Dict]:
    """基于查询模式、扫描统计与字段选择性生成索引优化建议。"""
    entries_list = list(entries)
    selectivity_map = _estimate_field_selectivity(entries_list)

    existing_keys = set()
    for idx in existing_indexes or []:
        key = idx.get("key", {})
        if key:
            existing_keys.add(tuple(key.items()))

    suggestions: Dict[str, Dict] = {}
    for entry in entries_list:
        plan = str(entry.get("planSummary") or "")
        docs_examined = int(entry.get("docsExamined", 0) or 0)
        keys_examined = int(entry.get("keysExamined", 0) or 0)
        filter_doc = entry.get("filter") or {}
        sort = entry.get("sort") or {}
        if not isinstance(filter_doc, dict):
            filter_doc = {}
        if not isinstance(sort, dict):
            sort = {}

        recommended = False
        reasons = []
        if "COLLSCAN" in plan:
            recommended = True
            reasons.append("执行计划为 COLLSCAN（集合扫描）")
        nret = int(entry.get("nreturned", 0) or 0)
        if docs_examined > 1000 and (nret == 0 or docs_examined / max(1, nret) > 10):
            recommended = True
            reasons.append("扫描文档数远超返回文档数，过滤效率低")
        if not recommended:
            continue

        key_candidate, field_selectivity, ordering_notes = _build_index_key(
            filter_doc, sort, selectivity_map
        )
        if not key_candidate:
            continue
        key_tuple = tuple(key_candidate.items())
        if key_tuple in existing_keys:
            continue

        pattern = extract_query_pattern(entry)
        bucket = suggestions.setdefault(key_tuple, {
            "index": key_candidate,
            "ns": entry.get("ns"),
            "pattern": pattern,
            "count": 0,
            "reasons": set(),
            "worst_docsExamined": 0,
            "worst_keysExamined": 0,
            "field_selectivity": field_selectivity,
            "ordering_notes": ordering_notes,
        })
        bucket["count"] += 1
        bucket["reasons"].update(reasons)
        if docs_examined > bucket["worst_docsExamined"]:
            bucket["worst_docsExamined"] = docs_examined
        if keys_examined > bucket["worst_keysExamined"]:
            bucket["worst_keysExamined"] = keys_examined

    out = []
    for _, b in suggestions.items():
        b["reasons"] = sorted(b["reasons"])
        out.append(b)
    out.sort(key=lambda x: (x["count"], x["worst_docsExamined"]), reverse=True)
    return out


def _build_index_key(
    filter_doc: Dict,
    sort: Dict,
    selectivity_map: Dict[str, Dict],
) -> Tuple[Dict, Dict, List[str]]:
    """根据 filter / sort 和字段选择性构造推荐索引。

    返回 (index_dict, field_selectivity_dict, ordering_notes)。
    遵循 ESR 原则：等值字段按选择性降序 → 范围字段 → 排序字段。
    """
    equality_fields: List[str] = []
    range_fields: List[str] = []
    sort_fields: List[str] = []

    for field, val in filter_doc.items():
        if field.startswith("$"):
            continue
        if isinstance(val, dict) and _is_range_query(val):
            range_fields.append(field)
        else:
            equality_fields.append(field)

    for field in sort.keys():
        if field.startswith("$"):
            continue
        sort_fields.append(field)

    # 按选择性分数降序排列等值字段
    equality_fields.sort(
        key=lambda f: selectivity_map.get(f, {}).get("selectivity_score", 0),
        reverse=True,
    )
    # 范围字段也按选择性排序
    range_fields.sort(
        key=lambda f: selectivity_map.get(f, {}).get("selectivity_score", 0),
        reverse=True,
    )

    index: Dict = {}
    field_selectivity: Dict = {}
    notes: List[str] = []

    for f in equality_fields:
        index[f] = 1
        sel = selectivity_map.get(f, {})
        field_selectivity[f] = {
            "type": "equality",
            "distinct_count": sel.get("distinct_count", "?"),
            "query_count": sel.get("query_count", 0),
            "selectivity_score": sel.get("selectivity_score", 0),
        }

    for f in range_fields:
        if f not in index:
            index[f] = 1
            sel = selectivity_map.get(f, {})
            field_selectivity[f] = {
                "type": "range",
                "distinct_count": sel.get("distinct_count", "?"),
                "query_count": sel.get("query_count", 0),
                "selectivity_score": sel.get("selectivity_score", 0),
            }

    for f in sort_fields:
        if f not in index:
            index[f] = 1 if sort.get(f) == 1 else -1
            field_selectivity[f] = {
                "type": "sort",
                "direction": 1 if sort.get(f) == 1 else -1,
            }

    # 生成顺序说明
    if equality_fields:
        notes.append(
            "等值字段按选择性排序: "
            + " > ".join(equality_fields)
        )
    if range_fields:
        notes.append(
            "范围字段: " + " > ".join(range_fields) + "（位于等值字段之后）"
        )
    if sort_fields:
        notes.append(
            "排序字段: " + ", ".join(sort_fields) + "（位于末尾）"
        )

    return index, field_selectivity, notes


def _is_range_query(val: Dict) -> bool:
    if not isinstance(val, dict):
        return False
    return any(k in val for k in ("$gt", "$gte", "$lt", "$lte", "$ne", "$regex", "$in"))


# ---------------------------------------------------------------------------
# 分片热点分析（动态分位阈值）
# ---------------------------------------------------------------------------

def analyze_shard_hotspot(
    entries: Iterable[Dict],
    shard_info: Dict | None = None,
) -> Dict:
    """基于慢日志访问分布分位数动态计算热点阈值。"""
    ns_counter: Dict[str, int] = defaultdict(int)
    ns_duration: Dict[str, int] = defaultdict(int)
    ns_plans: Dict[str, set] = defaultdict(set)
    for entry in entries:
        ns = entry.get("ns") or "unknown"
        ns_counter[ns] += 1
        ns_duration[ns] += int(entry.get("duration") or 0)
        plan = str(entry.get("planSummary") or "UNKNOWN")
        ns_plans[ns].add(plan.split(" ")[0])

    # 计算每个集合的综合热度分数
    scores: Dict[str, float] = {}
    for ns in ns_counter:
        # 使用 count 和 total_ms 的对数加权，避免极端值主导
        scores[ns] = _hot_score(ns_counter[ns], ns_duration[ns])

    # 基于分位数动态计算阈值
    sorted_scores = sorted(scores.values())
    if sorted_scores:
        q25 = _percentile(sorted_scores, 25)
        q50 = _percentile(sorted_scores, 50)
        q75 = _percentile(sorted_scores, 75)
        q90 = _percentile(sorted_scores, 90)
    else:
        q25 = q50 = q75 = q90 = 0

    quantile_thresholds = {
        "q25": round(q25, 2),
        "q50": round(q50, 2),
        "q75": round(q75, 2),
        "q90": round(q90, 2),
    }

    collections = []
    for ns, score in scores.items():
        level = _classify_hotspot(score, q75, q90)
        collections.append({
            "ns": ns,
            "count": ns_counter[ns],
            "total_ms": ns_duration[ns],
            "hot_score": round(score, 2),
            "plans": sorted(ns_plans[ns]),
            "hotspot_level": level,
        })
    collections.sort(key=lambda x: x["hot_score"], reverse=True)

    return {
        "is_sharded": bool(shard_info and shard_info.get("is_sharded")),
        "shards": shard_info.get("shards", []) if shard_info else [],
        "collections": collections,
        "quantile_thresholds": quantile_thresholds,
        "classification_rule": (
            "score >= Q90 为 HIGH; Q75 <= score < Q90 为 MEDIUM; score < Q75 为 LOW"
        ),
    }


def _hot_score(count: int, total_ms: int) -> float:
    """对数加权的热度分数，避免极端值主导。"""
    return math.log1p(count) * 10 + math.log1p(total_ms)


def _percentile(sorted_values: List[float], p: float) -> float:
    """计算分位数（线性插值）。"""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_values[0])
    rank = (p / 100.0) * (n - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return float(sorted_values[lower])
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _classify_hotspot(score: float, q75: float, q90: float) -> str:
    """基于分位数动态分类。"""
    if q90 == q75:
        # 数据过于集中，退化为基于均值的分类
        return "HIGH" if score > 0 else "LOW"
    if score >= q90:
        return "HIGH"
    if score >= q75:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# 覆盖查询分析
# ---------------------------------------------------------------------------

def analyze_covered_queries(
    entries: Iterable[Dict],
    existing_indexes: List[Dict] | None = None,
) -> List[Dict]:
    """分析可被索引覆盖的查询（docsExamined=0 且 projection 中的字段都在索引中）。

    判定规则：
    1. 查询执行过 IXSCAN（使用了索引）
    2. docsExamined == 0 或 docsExamined <= keysExamined * 0.1（接近覆盖）
    3. projection 中的所有字段都存在于现有索引的键中（或没有 projection）
    """
    entries_list = list(entries)
    indexes = existing_indexes or []

    # 索引键集合映射: ns -> [ (index_name, key_set) ]
    ns_indexes: Dict[str, List[Tuple[str, set]]] = defaultdict(list)
    for idx in indexes:
        ns = idx.get("ns") or ""
        if ns and "." in ns:
            coll = ns.split(".", 1)[1]
            ns_indexes[coll].append((idx.get("name", "unknown"), set(idx.get("key", {}).keys())))

    covered: List[Dict] = []
    for entry in entries_list:
        plan = str(entry.get("planSummary") or "")
        if "IXSCAN" not in plan:
            continue

        keys_examined = int(entry.get("keysExamined", 0) or 0)
        docs_examined = int(entry.get("docsExamined", 0) or 0)
        nreturned = int(entry.get("nreturned", 0) or 0)

        # 覆盖索引判定：
        # - 完全覆盖：docsExamined == 0（无需回表）
        # - 接近覆盖：docsExamined / keysExamined <= 0.9（索引扫描为主，少量回表）
        # - 注意：IXSCAN 本身说明已经走了索引
        if keys_examined > 0 and docs_examined > keys_examined * 0.9:
            continue

        filter_doc = entry.get("filter") or {}
        projection = entry.get("projection") or {}
        sort_doc = entry.get("sort") or {}
        ns = entry.get("ns") or ""
        coll = ns.split(".", 1)[1] if "." in ns else ""

        used_fields: set = set()
        _collect_fields(filter_doc, used_fields)
        _collect_fields(projection, used_fields)
        _collect_fields(sort_doc, used_fields)

        # 检查是否有索引可以覆盖所有 used_fields（含 _id 投影）
        coverable_by = []
        for idx_name, idx_keys in ns_indexes.get(coll, []):
            if used_fields.issubset(idx_keys) or (
                len(used_fields) == 0 and idx_keys
            ):
                coverable_by.append(idx_name)

        coverage_ratio = (
            1.0 if docs_examined == 0 else 1.0 - (docs_examined / max(1, keys_examined))
        )

        covered.append({
            "ns": ns,
            "op": entry.get("op"),
            "filter": filter_doc,
            "projection": projection,
            "sort": sort_doc,
            "used_fields": sorted(used_fields),
            "keysExamined": keys_examined,
            "docsExamined": docs_examined,
            "nreturned": nreturned,
            "planSummary": plan,
            "is_fully_covered": docs_examined == 0,
            "coverage_ratio": round(coverage_ratio, 4),
            "coverable_by_indexes": coverable_by,
            "suggestion": (
                "已被覆盖，无需回表" if docs_examined == 0 else
                "接近覆盖，建议将 projection 字段加入索引以消除回表"
            ),
        })

    # 按模式聚合
    pattern_buckets: Dict[str, Dict] = defaultdict(lambda: {
        "pattern": "",
        "ns": "",
        "count": 0,
        "total_keysExamined": 0,
        "total_docsExamined": 0,
        "avg_coverage_ratio": 0.0,
        "samples": [],
        "coverable_by_indexes": set(),
        "is_fully_covered": True,
        "used_fields": set(),
    })
    for item in covered:
        try:
            pattern = extract_query_pattern(item)
        except Exception:
            continue
        bucket = pattern_buckets[pattern]
        bucket["pattern"] = pattern
        bucket["ns"] = item["ns"]
        bucket["count"] += 1
        bucket["total_keysExamined"] += item["keysExamined"]
        bucket["total_docsExamined"] += item["docsExamined"]
        bucket["avg_coverage_ratio"] += item["coverage_ratio"]
        bucket["is_fully_covered"] = bucket["is_fully_covered"] and item["is_fully_covered"]
        bucket["coverable_by_indexes"].update(item["coverable_by_indexes"])
        bucket["used_fields"].update(item["used_fields"])
        if len(bucket["samples"]) < 2:
            bucket["samples"].append(item)
    result = []
    for _, b in pattern_buckets.items():
        b["avg_coverage_ratio"] = round(b["avg_coverage_ratio"] / b["count"], 4)
        b["coverable_by_indexes"] = sorted(b["coverable_by_indexes"])
        b["used_fields"] = sorted(b["used_fields"])
        b["suggestion"] = (
            "已完全覆盖（无需回表）" if b["is_fully_covered"] else
            "建议将投影/排序字段加入索引以实现完全覆盖"
        )
        result.append(b)
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def _collect_fields(doc: Dict, out: set):
    """递归收集查询文档中使用的所有字段名。"""
    if not isinstance(doc, dict):
        return
    for k, v in doc.items():
        if k.startswith("$"):
            if isinstance(v, dict):
                _collect_fields(v, out)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        _collect_fields(item, out)
            continue
        if v != 0 and v is not False:
            out.add(k)
        if isinstance(v, dict):
            _collect_fields(v, out)


# ---------------------------------------------------------------------------
# 慢查询趋势预测
# ---------------------------------------------------------------------------

def forecast_slow_query_trend(
    entries: Iterable[Dict],
    periods: int = 7,
) -> Dict:
    """基于历史慢查询时间序列预测未来慢查询量。

    使用简单指数平滑 (Simple Exponential Smoothing) + 线性回归组合：
    1. 将历史数据按时间桶聚合（小时/天）
    2. 计算平滑趋势
    3. 线性回归预测未来 N 个周期
    """
    entries_list = list(entries)
    if not entries_list:
        return {"has_data": False, "forecast": [], "history": [], "metrics": {}}

    # 解析时间戳，按小时聚合
    ts_buckets: Dict[str, int] = defaultdict(int)
    ts_bucket_ms: Dict[str, float] = defaultdict(float)
    for e in entries_list:
        ts = _parse_timestamp(e.get("ts"))
        if ts is None:
            continue
        bucket = ts.strftime("%Y-%m-%d %H:00")
        ts_buckets[bucket] += 1
        ts_bucket_ms[bucket] += int(e.get("duration") or 0)

    if len(ts_buckets) < 2:
        # 数据点不足，生成模拟趋势
        return _generate_synthetic_forecast(entries_list, periods)

    sorted_buckets = sorted(ts_buckets.keys())
    history = []
    for bucket in sorted_buckets:
        history.append({
            "timestamp": bucket,
            "count": ts_buckets[bucket],
            "total_ms": round(ts_bucket_ms[bucket], 0),
        })

    # 简单指数平滑 alpha
    alpha = 0.3
    counts = [h["count"] for h in history]
    smoothed = _simple_exponential_smoothing(counts, alpha)

    # 线性回归预测
    n = len(counts)
    xs = list(range(n))
    slope, intercept = _linear_regression(xs, counts)

    forecast = []
    last_time = datetime.strptime(sorted_buckets[-1], "%Y-%m-%d %H:00")
    for i in range(periods):
        pred_x = n + i
        pred_count = max(0, round(slope * pred_x + intercept, 2))
        smoothed_forecast = smoothed[-1] if smoothed else 0
        pred_time = last_time + timedelta(hours=i + 1)
        forecast.append({
            "timestamp": pred_time.strftime("%Y-%m-%d %H:00"),
            "predicted_count": pred_count,
            "smoothed_count": round(smoothed_forecast, 2),
            "trend": "上升" if slope > 0.1 else ("下降" if slope < -0.1 else "平稳"),
        })

    # 计算置信区间（基于残差标准差）
    residuals = [counts[i] - (slope * i + intercept) for i in range(n)]
    std_resid = math.sqrt(sum(r * r for r in residuals) / max(1, n - 2)) if n > 2 else 0

    return {
        "has_data": True,
        "history": history,
        "forecast": forecast,
        "metrics": {
            "periods": periods,
            "alpha": alpha,
            "slope": round(slope, 4),
            "intercept": round(intercept, 4),
            "trend": "上升" if slope > 0.1 else ("下降" if slope < -0.1 else "平稳"),
            "residual_std": round(std_resid, 2),
            "history_points": n,
        },
    }


def _generate_synthetic_forecast(entries_list: List[Dict], periods: int) -> Dict:
    """当时间数据不足时生成模拟趋势。"""
    total_count = len(entries_list)
    total_ms = sum(int(e.get("duration") or 0) for e in entries_list)
    avg_count = total_count / max(1, periods)

    history = [{
        "timestamp": "综合样本",
        "count": total_count,
        "total_ms": total_ms,
    }]
    forecast = []
    base = avg_count
    for i in range(periods):
        # 模拟小幅波动
        noise = math.sin(i * 0.5) * base * 0.2
        pred = max(0, round(base + noise, 2))
        forecast.append({
            "timestamp": f"预测周期 {i+1}",
            "predicted_count": pred,
            "smoothed_count": round(base, 2),
            "trend": "平稳",
        })

    return {
        "has_data": True,
        "history": history,
        "forecast": forecast,
        "metrics": {
            "periods": periods,
            "alpha": 0.3,
            "slope": 0.0,
            "intercept": base,
            "trend": "平稳",
            "residual_std": 0.0,
            "history_points": 1,
            "note": "时间数据不足，使用模拟趋势",
        },
    }


def _parse_timestamp(ts) -> datetime | None:
    """解析多种时间戳格式。"""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    s = str(ts).strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    # 带 +0800 的格式
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)([+-]\d{4})", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            pass
    return None


def _simple_exponential_smoothing(values: List[float], alpha: float) -> List[float]:
    if not values:
        return []
    smoothed = [values[0]]
    for i in range(1, len(values)):
        smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
    return smoothed


def _linear_regression(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    """最小二乘法线性回归，返回 (slope, intercept)。"""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.0, mean_y
    slope = num / den
    intercept = mean_y - slope * mean_x
    return slope, intercept


# ---------------------------------------------------------------------------
# Explain 执行计划火焰图转换
# ---------------------------------------------------------------------------

def convert_explain_to_flamegraph(
    explain_result: Dict,
) -> Dict:
    """将 MongoDB explain("executionStats") 结果转换为火焰图数据结构。

    返回:
      {
        "name": "ROOT",
        "value": total_execution_time_ms,
        "children": [ ... ],
        "nodes": [ { id, name, value, children: [...] } ],
        "edges": [ { source, target, value } ],
      }
    """
    exec_stats = explain_result.get("executionStats", {})
    total_time = exec_stats.get("executionTimeMillis", 0) or 0

    stages_tree = _extract_execution_stages(exec_stats)

    # 扁平化节点列表（DFS 分配 id）
    nodes: List[Dict] = []
    edges: List[Dict] = []
    _flatten_stages(stages_tree, nodes, edges, parent_id=None, next_id=[0])

    return {
        "total_execution_time_ms": total_time,
        "n_returned": exec_stats.get("nReturned", 0),
        "total_keys_examined": exec_stats.get("totalKeysExamined", 0),
        "total_docs_examined": exec_stats.get("totalDocsExamined", 0),
        "tree": stages_tree,
        "nodes": nodes,
        "edges": edges,
        "svg_ready": True,
    }


def _extract_execution_stages(exec_stats: Dict) -> Dict:
    """从 executionStats 中提取结构化的阶段树。"""
    exec_stages = exec_stats.get("executionStages", {})
    if not exec_stages:
        return {"name": "UNKNOWN", "value": 0, "children": []}

    def build_node(stage: Dict) -> Dict:
        name = stage.get("stage", "UNKNOWN")
        time_ms = (
            stage.get("executionTimeMillisEstimate") or
            stage.get("executionTimeMillis") or
            0
        )
        node = {
            "name": name,
            "value": int(time_ms),
            "details": {
                "keysExamined": stage.get("keysExamined", 0),
                "docsExamined": stage.get("docsExamined", 0),
                "nReturned": stage.get("nReturned", 0),
                "filter": stage.get("filter"),
                "indexName": stage.get("indexName"),
                "indexBounds": stage.get("indexBounds"),
                "direction": stage.get("direction"),
            },
            "children": [],
        }
        # 递归处理子阶段
        for key in ("inputStage", "innerStage", "outerStage", "firstStage", "secondStage"):
            child = stage.get(key)
            if child and isinstance(child, dict):
                node["children"].append(build_node(child))
        # 处理 inputStages 数组
        if "inputStages" in stage and isinstance(stage["inputStages"], list):
            for child in stage["inputStages"]:
                node["children"].append(build_node(child))
        return node

    return build_node(exec_stages)


def _flatten_stages(
    node: Dict,
    out_nodes: List[Dict],
    out_edges: List[Dict],
    parent_id: int | None,
    next_id: List[int],
):
    """DFS 扁平化阶段树，生成 D3.js 火焰图/树图可用的节点与边列表。"""
    node_id = next_id[0]
    next_id[0] += 1

    out_nodes.append({
        "id": node_id,
        "name": node.get("name"),
        "value": node.get("value", 0),
        "details": node.get("details", {}),
        "parent": parent_id,
    })
    if parent_id is not None:
        out_edges.append({
            "source": parent_id,
            "target": node_id,
            "value": node.get("value", 0),
        })
    for child in node.get("children", []):
        _flatten_stages(child, out_nodes, out_edges, node_id, next_id)


# ---------------------------------------------------------------------------
# 模拟 Explain（用于日志文件模式下的演示）
# ---------------------------------------------------------------------------

def simulate_explain_for_entry(entry: Dict) -> Dict:
    """为日志条目模拟生成 explain 结果，用于纯日志模式下的可视化演示。"""
    plan = str(entry.get("planSummary") or "COLLSCAN")
    duration = int(entry.get("duration") or 0) or 0
    docs_examined = int(entry.get("docsExamined", 0) or 0)
    keys_examined = int(entry.get("keysExamined", 0) or 0)
    nreturned = int(entry.get("nreturned", 0) or 0)

    if "IXSCAN" in plan:
        # 索引扫描 → 有回表或无回表
        stages = {
            "executionStats": {
                "executionTimeMillis": duration,
                "nReturned": nreturned,
                "totalKeysExamined": keys_examined,
                "totalDocsExamined": docs_examined,
                "executionStages": {
                    "stage": "FETCH",
                    "executionTimeMillisEstimate": int(duration * 0.3),
                    "docsExamined": docs_examined,
                    "nReturned": nreturned,
                    "inputStage": {
                        "stage": "IXSCAN",
                        "executionTimeMillisEstimate": int(duration * 0.7),
                        "keysExamined": keys_examined,
                        "nReturned": nreturned,
                        "indexName": plan.split("{")[-1].rstrip("}").strip() if "{" in plan else "unknown_idx",
                        "indexBounds": entry.get("filter", {}),
                        "direction": "forward",
                    },
                },
            }
        }
    else:
        # 集合扫描
        stages = {
            "executionStats": {
                "executionTimeMillis": duration,
                "nReturned": nreturned,
                "totalKeysExamined": keys_examined,
                "totalDocsExamined": docs_examined,
                "executionStages": {
                    "stage": "COLLSCAN",
                    "executionTimeMillisEstimate": duration,
                    "docsExamined": docs_examined,
                    "nReturned": nreturned,
                    "filter": entry.get("filter", {}),
                    "direction": "forward",
                },
            }
        }
    return stages


# ---------------------------------------------------------------------------
# 报告汇总
# ---------------------------------------------------------------------------

def build_report(
    entries: Iterable[Dict],
    existing_indexes: List[Dict] | None = None,
    shard_info: Dict | None = None,
    limit: int = 50,
) -> Dict:
    entries_list = list(entries)
    ranking = rank_slow_queries(entries_list, by="total_ms", limit=limit)
    avg_slow = rank_slow_queries(entries_list, by="avg_ms", limit=limit)
    counts = rank_slow_queries(entries_list, by="count", limit=limit)
    suggestions = suggest_indexes(entries_list, existing_indexes)
    shard = analyze_shard_hotspot(entries_list, shard_info)
    covered = analyze_covered_queries(entries_list, existing_indexes)
    trend = forecast_slow_query_trend(entries_list, periods=7)

    # 为排名前 5 的慢查询生成火焰图数据
    explain_samples = []
    for rank_item in ranking[:5]:
        if rank_item["samples"]:
            sample = rank_item["samples"][0]
            simulated = simulate_explain_for_entry(sample)
            flame = convert_explain_to_flamegraph(simulated)
            explain_samples.append({
                "ns": rank_item["ns"],
                "pattern": rank_item["pattern"],
                "flamegraph": flame,
                "simulated": True,
            })

    return {
        "total_entries": len(entries_list),
        "total_unique_patterns": len(aggregate_by_pattern(entries_list)),
        "ranking_by_total_ms": ranking,
        "ranking_by_avg_ms": avg_slow,
        "ranking_by_count": counts,
        "index_suggestions": suggestions,
        "shard_hotspots": shard,
        "covered_queries": covered,
        "trend_forecast": trend,
        "explain_samples": explain_samples,
    }
