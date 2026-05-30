import logging
from datetime import datetime, timezone
from statistics import mean
from es_ilm_tool.es_client import ESClient
from es_ilm_tool import config

logger = logging.getLogger(__name__)


def _percentile(sorted_data: list, p: float) -> float:
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


class PerformanceAnalyzer:
    def __init__(self):
        self.es = ESClient()

    def get_index_performance(self, index_name: str) -> dict:
        stats = self.es.get_index_stats(index_name)
        if not stats:
            return {"index": index_name, "error": "Index not found or no stats available"}

        primaries = stats.get("primaries", {})
        total = stats.get("total", {})

        indexing = primaries.get("indexing", {})
        search = primaries.get("search", {})
        get_ops = primaries.get("get", {})
        merges = primaries.get("merges", {})
        store = primaries.get("store", {})
        segments = primaries.get("segments", {})
        translog = primaries.get("translog", {})
        refresh = primaries.get("refresh", {})
        flush = primaries.get("flush", {})

        return {
            "index": index_name,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "store": {
                "size_in_bytes": store.get("size_in_bytes", 0),
                "size_gb": round(store.get("size_in_bytes", 0) / (1024 ** 3), 2),
                "reserved_in_bytes": store.get("reserved_in_bytes", 0),
            },
            "documents": {
                "count": primaries.get("docs", {}).get("count", 0),
                "deleted": primaries.get("docs", {}).get("deleted", 0),
            },
            "indexing": {
                "total_operations": indexing.get("index_total", 0),
                "current_operations": indexing.get("index_current", 0),
                "total_time_ms": indexing.get("index_time_in_millis", 0),
                "avg_time_per_op_ms": round(
                    indexing.get("index_time_in_millis", 0) / max(indexing.get("index_total", 1), 1), 3
                ),
                "failed_operations": indexing.get("index_failed", 0),
                "throttle_time_ms": indexing.get("throttle_time_in_millis", 0),
            },
            "search": {
                "query_total": search.get("query_total", 0),
                "query_current": search.get("query_current", 0),
                "query_time_ms": search.get("query_time_in_millis", 0),
                "avg_query_time_ms": round(
                    search.get("query_time_in_millis", 0) / max(search.get("query_total", 1), 1), 3
                ),
                "fetch_total": search.get("fetch_total", 0),
                "fetch_time_ms": search.get("fetch_time_in_millis", 0),
                "scroll_total": search.get("scroll_total", 0),
            },
            "get": {
                "total": get_ops.get("total", 0),
                "time_ms": get_ops.get("time_in_millis", 0),
                "exists_total": get_ops.get("exists_total", 0),
                "missing_total": get_ops.get("missing_total", 0),
                "avg_time_ms": round(
                    get_ops.get("time_in_millis", 0) / max(get_ops.get("total", 1), 1), 3
                ),
            },
            "merges": {
                "total": merges.get("total", 0),
                "total_time_ms": merges.get("total_time_in_millis", 0),
                "total_docs": merges.get("total_docs", 0),
                "total_size_in_bytes": merges.get("total_size_in_bytes", 0),
                "current": merges.get("current", 0),
            },
            "segments": {
                "count": segments.get("count", 0),
                "memory_in_bytes": segments.get("memory_in_bytes", 0),
                "size_in_bytes": segments.get("size_in_bytes", 0),
            },
            "translog": {
                "operations": translog.get("operations", 0),
                "size_in_bytes": translog.get("size_in_bytes", 0),
                "uncommitted_operations": translog.get("uncommitted_operations", 0),
            },
            "refresh": {
                "total": refresh.get("total", 0),
                "total_time_ms": refresh.get("total_time_in_millis", 0),
                "listeners": refresh.get("listeners", 0),
            },
            "flush": {
                "total": flush.get("total", 0),
                "total_time_ms": flush.get("total_time_in_millis", 0),
            },
            "total_shards": stats.get("shards", {}).get("total", 0),
            "successful_shards": stats.get("shards", {}).get("successful", 0),
            "failed_shards": stats.get("shards", {}).get("failed", 0),
            "shard_latency": self._get_shard_latency_stats(stats),
        }

    def _get_shard_latency_stats(self, stats: dict) -> dict:
        shards = stats.get("shards", {})
        all_query_latencies = []
        all_index_latencies = []
        shard_details = []

        for shard_id, shard_list in shards.items():
            for shard_data in shard_list:
                shard_stats = shard_data.get("stats", {})
                search_stats = shard_stats.get("search", {})
                indexing_stats = shard_stats.get("indexing", {})

                query_total = search_stats.get("query_total", 0)
                query_time = search_stats.get("query_time_in_millis", 0)
                avg_query_latency = round(query_time / max(query_total, 1), 3)

                index_total = indexing_stats.get("index_total", 0)
                index_time = indexing_stats.get("index_time_in_millis", 0)
                avg_index_latency = round(index_time / max(index_total, 1), 3)

                routing = shard_data.get("routing", {})
                shard_detail = {
                    "shard_id": shard_id,
                    "primary": shard_data.get("primary", False),
                    "node": routing.get("node", ""),
                    "state": shard_data.get("state", ""),
                    "avg_query_latency_ms": avg_query_latency,
                    "query_total": query_total,
                    "avg_index_latency_ms": avg_index_latency,
                    "index_total": index_total,
                    "size_in_bytes": shard_stats.get("store", {}).get("size_in_bytes", 0),
                    "doc_count": shard_stats.get("docs", {}).get("count", 0),
                }
                shard_details.append(shard_detail)

                if query_total > 0:
                    all_query_latencies.append(avg_query_latency)
                if index_total > 0:
                    all_index_latencies.append(avg_index_latency)

        sorted_query = sorted(all_query_latencies)
        sorted_index = sorted(all_index_latencies)

        shard_details.sort(key=lambda x: x["avg_query_latency_ms"], reverse=True)
        slow_shards = [
            s for s in shard_details
            if s["avg_query_latency_ms"] > config.PERF_SLOW_SHARD_THRESHOLD_MS
            or s["avg_index_latency_ms"] > config.PERF_SLOW_SHARD_THRESHOLD_MS
        ]

        return {
            "query_p50_ms": round(_percentile(sorted_query, 50), 3),
            "query_p95_ms": round(_percentile(sorted_query, 95), 3),
            "query_p99_ms": round(_percentile(sorted_query, 99), 3),
            "query_avg_ms": round(mean(all_query_latencies), 3) if all_query_latencies else 0,
            "query_max_ms": sorted_query[-1] if sorted_query else 0,
            "index_p50_ms": round(_percentile(sorted_index, 50), 3),
            "index_p95_ms": round(_percentile(sorted_index, 95), 3),
            "index_p99_ms": round(_percentile(sorted_index, 99), 3),
            "index_avg_ms": round(mean(all_index_latencies), 3) if all_index_latencies else 0,
            "index_max_ms": sorted_index[-1] if sorted_index else 0,
            "total_shards_analyzed": len(shard_details),
            "slow_shards_count": len(slow_shards),
            "slow_shards": slow_shards[:config.PERF_ANALYSIS_TOP_N],
            "all_shards": shard_details,
        }

    def get_shard_performance(self, index_name: str) -> dict:
        try:
            stats = self.es.client.indices.stats(index=index_name, level="shards")
            index_stats = stats.get("indices", {}).get(index_name, {})
            latency_stats = self._get_shard_latency_stats(index_stats)
            return {
                "index": index_name,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                **latency_stats,
            }
        except Exception as e:
            logger.error("Failed to get shard performance for %s: %s", index_name, e)
            return {"index": index_name, "error": str(e)}

    def get_slow_shards(self, threshold_ms: int = None, top_n: int = None) -> list:
        threshold = threshold_ms or config.PERF_SLOW_SHARD_THRESHOLD_MS
        n = top_n or config.PERF_ANALYSIS_TOP_N
        indices = self.es.get_all_indices()
        all_slow_shards = []

        for idx in indices:
            name = idx.get("index", "")
            if name.startswith("."):
                continue
            try:
                shard_perf = self.get_shard_performance(name)
                slow_shards = shard_perf.get("slow_shards", [])
                for shard in slow_shards:
                    shard["index"] = name
                    all_slow_shards.append(shard)
            except Exception as e:
                logger.warning("Failed to analyze shards for %s: %s", name, e)

        all_slow_shards.sort(key=lambda x: x["avg_query_latency_ms"], reverse=True)
        return all_slow_shards[:n]

    def get_slow_indices(self, threshold_ms: int = None) -> list:
        threshold = threshold_ms or config.PERF_SLOW_QUERY_THRESHOLD_MS
        indices = self.es.get_all_indices()
        slow_indices = []

        for idx in indices:
            name = idx.get("index", "")
            if name.startswith("."):
                continue
            perf = self.get_index_performance(name)
            avg_query = perf.get("search", {}).get("avg_query_time_ms", 0)
            avg_index = perf.get("indexing", {}).get("avg_time_per_op_ms", 0)

            if avg_query > threshold or avg_index > threshold:
                slow_indices.append({
                    "index": name,
                    "avg_query_time_ms": avg_query,
                    "avg_index_time_ms": avg_index,
                    "threshold_ms": threshold,
                })

        slow_indices.sort(key=lambda x: x["avg_query_time_ms"], reverse=True)
        return slow_indices[:config.PERF_ANALYSIS_TOP_N]

    def get_largest_indices(self, top_n: int = None) -> list:
        n = top_n or config.PERF_ANALYSIS_TOP_N
        indices = self.es.get_all_indices()
        size_list = []

        for idx in indices:
            name = idx.get("index", "")
            if name.startswith("."):
                continue
            perf = self.get_index_performance(name)
            size_list.append({
                "index": name,
                "size_gb": perf.get("store", {}).get("size_gb", 0),
                "doc_count": perf.get("documents", {}).get("count", 0),
            })

        size_list.sort(key=lambda x: x["size_gb"], reverse=True)
        return size_list[:n]

    def get_cluster_performance(self) -> dict:
        health = self.es.get_cluster_health()
        node_stats = self.es.get_node_stats()

        nodes = node_stats.get("nodes", {})
        node_perf = []
        for node_id, node_data in nodes.items():
            os_info = node_data.get("os", {})
            jvm = node_data.get("jvm", {})
            process = node_data.get("process", {})
            fs = node_data.get("fs", {})
            indices = node_data.get("indices", {})

            node_perf.append({
                "node_id": node_id,
                "name": node_data.get("name", ""),
                "host": node_data.get("host", ""),
                "cpu_percent": os_info.get("cpu", {}).get("percent", 0),
                "heap_used_percent": jvm.get("mem", {}).get("heap_used_percent", 0),
                "heap_used_in_bytes": jvm.get("mem", {}).get("heap_used_in_bytes", 0),
                "heap_max_in_bytes": jvm.get("mem", {}).get("heap_max_in_bytes", 0),
                "open_file_descriptors": process.get("open_file_descriptors", 0),
                "disk_total_in_bytes": fs.get("total", {}).get("total_in_bytes", 0) if fs.get("total") else 0,
                "disk_free_in_bytes": fs.get("total", {}).get("available_in_bytes", 0) if fs.get("total") else 0,
                "indices_size_in_bytes": indices.get("store", {}).get("size_in_bytes", 0),
                "indices_doc_count": indices.get("docs", {}).get("count", 0),
            })

        return {
            "cluster_name": health.get("cluster_name", "unknown"),
            "status": health.get("status", "unknown"),
            "number_of_nodes": health.get("number_of_nodes", 0),
            "active_primary_shards": health.get("active_primary_shards", 0),
            "active_shards": health.get("active_shards", 0),
            "relocating_shards": health.get("relocating_shards", 0),
            "initializing_shards": health.get("initializing_shards", 0),
            "unassigned_shards": health.get("unassigned_shards", 0),
            "pending_tasks": health.get("number_of_pending_tasks", 0),
            "nodes": node_perf,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def analyze_index_health(self, index_name: str) -> dict:
        perf = self.get_index_performance(index_name)
        issues = []
        recommendations = []

        doc_deleted = perf.get("documents", {}).get("deleted", 0)
        doc_count = perf.get("documents", {}).get("count", 0)
        if doc_count > 0 and doc_deleted / doc_count > 0.1:
            issues.append("High deletion ratio detected")
            recommendations.append("Consider running force merge to reclaim deleted document space")

        merge_current = perf.get("merges", {}).get("current", 0)
        if merge_current > 5:
            issues.append(f"High merge activity: {merge_current} ongoing merges")
            recommendations.append("Consider adjusting merge policy or scheduling merges during off-peak hours")

        avg_query_ms = perf.get("search", {}).get("avg_query_time_ms", 0)
        if avg_query_ms > config.PERF_SLOW_QUERY_THRESHOLD_MS:
            issues.append(f"Slow queries detected: avg {avg_query_ms}ms")
            recommendations.append("Review mapping, consider adding specific queries or warming caches")

        segment_count = perf.get("segments", {}).get("count", 0)
        if segment_count > 100:
            issues.append(f"High segment count: {segment_count}")
            recommendations.append("Run force merge to reduce segment count")

        translog_uncommitted = perf.get("translog", {}).get("uncommitted_operations", 0)
        if translog_uncommitted > 10000:
            issues.append(f"High uncommitted translog operations: {translog_uncommitted}")
            recommendations.append("Check if flush is working properly or increase flush interval")

        failed_shards = perf.get("failed_shards", 0)
        if failed_shards > 0:
            issues.append(f"Failed shards: {failed_shards}")
            recommendations.append("Investigate shard failures immediately - potential data loss risk")

        throttle_time = perf.get("indexing", {}).get("throttle_time_ms", 0)
        if throttle_time > 0:
            issues.append(f"Indexing throttled for {throttle_time}ms")
            recommendations.append("Consider increasing index store throttle or adjusting ILM timing")

        return {
            "index": index_name,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "health_score": max(0, 100 - len(issues) * 15),
            "issues": issues,
            "recommendations": recommendations,
            "performance_summary": {
                "size_gb": perf.get("store", {}).get("size_gb", 0),
                "doc_count": doc_count,
                "avg_query_ms": avg_query_ms,
                "avg_index_ms": perf.get("indexing", {}).get("avg_time_per_op_ms", 0),
                "segment_count": segment_count,
            },
        }
