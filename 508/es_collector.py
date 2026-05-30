import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)


@dataclass
class SlowQuery:
    query_id: str = ""
    index_name: str = ""
    query_body: Dict[str, Any] = field(default_factory=dict)
    response_time_ms: float = 0.0
    timestamp: float = 0.0
    search_type: str = ""
    total_shards: int = 0
    successful_shards: int = 0
    profile_data: Optional[Dict[str, Any]] = None
    cache_hit: Optional[bool] = None
    hits_total: int = 0
    from_offset: int = 0
    size: int = 0


class ESCollector:
    def __init__(self, hosts: List[str], username: str = "", password: str = "",
                 timeout: int = 30, verify_certs: bool = False):
        self.es = Elasticsearch(
            hosts=hosts,
            basic_auth=(username, password) if username and password else None,
            request_timeout=timeout,
            verify_certs=verify_certs,
        )
        self._verify_connection()

    def _verify_connection(self):
        try:
            info = self.es.info()
            logger.info("Connected to ES cluster: %s (version %s)",
                        info.get("cluster_name"), info.get("version", {}).get("number"))
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch: %s", e)
            raise

    def collect_slow_logs(self, index_pattern: str = "*",
                          log_index: str = ".slowlog-*",
                          from_ts: Optional[str] = None,
                          to_ts: Optional[str] = None) -> List[SlowQuery]:
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "took_millis"}}
                    ]
                }
            },
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 100
        }
        if from_ts or to_ts:
            range_clause: Dict[str, Any] = {"range": {"timestamp": {}}}
            if from_ts:
                range_clause["range"]["timestamp"]["gte"] = from_ts
            if to_ts:
                range_clause["range"]["timestamp"]["lte"] = to_ts
            query["query"]["bool"]["must"].append(range_clause)

        try:
            result = self.es.search(index=log_index, body=query)
        except Exception as e:
            logger.warning("Failed to fetch slow logs from %s: %s", log_index, e)
            return []

        slow_queries = []
        for hit in result.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            sq = SlowQuery(
                query_id=hit.get("_id", ""),
                index_name=src.get("index", ""),
                query_body=src.get("source", {}),
                response_time_ms=float(src.get("took_millis", 0)),
                timestamp=self._parse_timestamp(src.get("timestamp", "")),
                search_type=src.get("search_type", ""),
                total_shards=src.get("total_shards", 0),
                successful_shards=src.get("successful_shards", 0),
            )
            slow_queries.append(sq)
        return slow_queries

    def profile_query(self, index_name: str, query_body: Dict[str, Any]) -> Dict[str, Any]:
        profile_query = {**query_body, "profile": True}
        try:
            result = self.es.search(index=index_name, body=profile_query)
            return result.get("profile", {})
        except Exception as e:
            logger.error("Failed to profile query on %s: %s", index_name, e)
            return {}

    def execute_and_collect(self, index_name: str, query_body: Dict[str, Any],
                            threshold_ms: float) -> Optional[SlowQuery]:
        start = time.monotonic()
        try:
            result = self.es.search(index=index_name, body=query_body)
        except Exception as e:
            logger.error("Query execution failed on %s: %s", index_name, e)
            return None

        elapsed_ms = (time.monotonic() - start) * 1000
        if elapsed_ms < threshold_ms:
            return None

        hits_info = result.get("hits", {})
        shards_info = result.get("_shards", {})

        from_offset = query_body.get("from", 0)
        size = query_body.get("size", 10)

        profile_data = None
        if elapsed_ms > threshold_ms:
            profile_data = self.profile_query(index_name, query_body)

        cache_hit = self._check_cache_status(result)

        return SlowQuery(
            query_id=f"{index_name}-{int(time.time() * 1000)}",
            index_name=index_name,
            query_body=query_body,
            response_time_ms=elapsed_ms,
            timestamp=time.time(),
            search_type=query_body.get("search_type", "query_then_fetch"),
            total_shards=shards_info.get("total", 0),
            successful_shards=shards_info.get("successful", 0),
            profile_data=profile_data,
            cache_hit=cache_hit,
            hits_total=hits_info.get("total", {}).get("value", 0) if isinstance(hits_info.get("total"), dict) else hits_info.get("total", 0),
            from_offset=from_offset,
            size=size,
        )

    def _check_cache_status(self, result: Dict[str, Any]) -> Optional[bool]:
        profile = result.get("profile")
        if not profile:
            return None
        shards = profile.get("shards", [])
        if not shards:
            return None
        for shard in shards:
            searches = shard.get("searches", [])
            for search in searches:
                query_info = search.get("query", [])
                for q in query_info:
                    if q.get("query_type") == "CacheHelper":
                        return True
        return False

    def get_index_stats(self, index_name: str) -> Dict[str, Any]:
        try:
            stats = self.es.indices.stats(index=index_name)
            return stats.get("indices", {}).get(index_name, {})
        except Exception as e:
            logger.warning("Failed to get index stats for %s: %s", index_name, e)
            return {}

    def get_node_stats(self) -> Dict[str, Any]:
        try:
            stats = self.es.nodes.stats(metric="indices")
            return stats.get("nodes", {})
        except Exception as e:
            logger.warning("Failed to get node stats: %s", e)
            return {}

    def get_index_settings(self, index_name: str) -> Dict[str, Any]:
        try:
            settings = self.es.indices.get_settings(index=index_name)
            return settings.get(index_name, {}).get("settings", {})
        except Exception as e:
            logger.warning("Failed to get index settings for %s: %s", index_name, e)
            return {}

    def get_index_mapping(self, index_name: str) -> Dict[str, Any]:
        try:
            mapping = self.es.indices.get_mapping(index=index_name)
            return mapping.get(index_name, {}).get("mappings", {})
        except Exception as e:
            logger.warning("Failed to get index mapping for %s: %s", index_name, e)
            return {}

    def get_cluster_health(self) -> Dict[str, Any]:
        try:
            return self.es.cluster.health()
        except Exception as e:
            logger.warning("Failed to get cluster health: %s", e)
            return {}

    def get_pending_tasks(self) -> Dict[str, Any]:
        try:
            return self.es.cluster.pending_tasks()
        except Exception as e:
            logger.warning("Failed to get pending tasks: %s", e)
            return {}

    def get_thread_pool_stats(self) -> Dict[str, Any]:
        try:
            stats = self.es.nodes.stats(metric="thread_pool")
            return stats.get("nodes", {})
        except Exception as e:
            logger.warning("Failed to get thread pool stats: %s", e)
            return {}

    def get_detailed_index_stats(self, index_name: str) -> Dict[str, Any]:
        try:
            stats = self.es.indices.stats(
                index=index_name,
                metric="search,indexing,get,merge,refresh,flush,segments,request_cache,query_cache,fielddata"
            )
            return stats.get("indices", {}).get(index_name, {})
        except Exception as e:
            logger.warning("Failed to get detailed stats for %s: %s", index_name, e)
            return {}

    def get_search_stats(self, index_name: str = "*") -> Dict[str, Any]:
        try:
            stats = self.es.indices.stats(index=index_name, metric="search")
            all_indices = stats.get("indices", {})
            if index_name != "*" and index_name in all_indices:
                return all_indices[index_name].get("total", {}).get("search", {})
            total = stats.get("_all", {}).get("total", {})
            return total.get("search", {})
        except Exception as e:
            logger.warning("Failed to get search stats: %s", e)
            return {}

    def get_cache_stats(self, index_name: str = "*") -> Dict[str, Any]:
        try:
            stats = self.es.indices.stats(
                index=index_name,
                metric="request_cache,query_cache,fielddata"
            )
            return stats.get("indices", {}).get(index_name, stats.get("_all", {})).get("total", {})
        except Exception as e:
            logger.warning("Failed to get cache stats: %s", e)
            return {}

    def get_hot_threads(self) -> str:
        try:
            return self.es.nodes.hot_threads()
        except Exception as e:
            logger.warning("Failed to get hot threads: %s", e)
            return ""

    def explain_query(self, index_name: str, query_body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.es.indices.explain(
                index=index_name,
                id="__query_explain__",
                body=query_body,
                ignore=[404],
            )
        except Exception as e:
            logger.warning("Failed to explain query on %s: %s", index_name, e)
            return {}

    def validate_query(self, index_name: str, query_body: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.es.indices.validate_query(
                index=index_name,
                body=query_body,
                explain=True,
                rewrite=True,
            )
        except Exception as e:
            logger.warning("Failed to validate query on %s: %s", index_name, e)
            return {"valid": False, "error": str(e)}

    def get_slow_log_settings(self, index_name: str) -> Dict[str, Any]:
        try:
            settings = self.es.indices.get_settings(
                index=index_name,
                flat_settings=True,
                include_defaults=True,
            )
            idx_settings = settings.get(index_name, {}).get("settings", {})
            return {
                "search": {
                    "query_warn_threshold": idx_settings.get("index.search.slowlog.threshold.query.warn"),
                    "query_info_threshold": idx_settings.get("index.search.slowlog.threshold.query.info"),
                    "query_debug_threshold": idx_settings.get("index.search.slowlog.threshold.query.debug"),
                    "query_trace_threshold": idx_settings.get("index.search.slowlog.threshold.query.trace"),
                    "fetch_warn_threshold": idx_settings.get("index.search.slowlog.threshold.fetch.warn"),
                },
                "index": {
                    "warn_threshold": idx_settings.get("index.indexing.slowlog.threshold.index.warn"),
                    "info_threshold": idx_settings.get("index.indexing.slowlog.threshold.index.info"),
                },
                "level": idx_settings.get("index.search.slowlog.level"),
            }
        except Exception as e:
            logger.warning("Failed to get slow log settings for %s: %s", index_name, e)
            return {}

    def get_task_list(self, detailed: bool = False) -> List[Dict[str, Any]]:
        try:
            result = self.es.tasks.list(
                actions="*search*",
                detailed=detailed,
            )
            return result.get("tasks", [])
        except Exception as e:
            logger.warning("Failed to get task list: %s", e)
            return []

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        try:
            return self.es.tasks.cancel(task_id=task_id)
        except Exception as e:
            logger.warning("Failed to cancel task %s: %s", task_id, e)
            return {}

    @staticmethod
    def _parse_timestamp(ts_str: str) -> float:
        if not ts_str:
            return 0.0
        try:
            from datetime import datetime, timezone
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(ts_str, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
                except ValueError:
                    continue
            return 0.0
        except Exception:
            return 0.0
