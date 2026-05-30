import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from elasticsearch import exceptions as es_exceptions
from es_ilm_tool.es_client import ESClient
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class AuditLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._audit_logger = logging.getLogger("es_ilm_audit")
        self._audit_logger.setLevel(logging.INFO)
        self._setup_file_handler()

        self._es_client = ESClient() if config.AUDIT_ENABLE_ES_INDEX else None
        self._batch_buffer = []
        self._buffer_lock = threading.Lock()
        self._flush_thread = None
        self._flush_stop_event = threading.Event()

        if config.AUDIT_ENABLE_ES_INDEX:
            self._ensure_audit_index_template()
            self._start_background_flusher()

    def _setup_file_handler(self):
        os.makedirs(config.AUDIT_LOG_DIR, exist_ok=True)
        log_file = os.path.join(config.AUDIT_LOG_DIR, "ilm_audit.log")
        handler = RotatingFileHandler(
            log_file,
            maxBytes=config.AUDIT_LOG_MAX_BYTES,
            backupCount=config.AUDIT_LOG_BACKUP_COUNT,
        )
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        self._audit_logger.addHandler(handler)
        self._audit_logger.propagate = False

    def _get_audit_index_name(self) -> str:
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime(config.AUDIT_ES_INDEX_DATE_FORMAT)
        return f"{config.AUDIT_ES_INDEX_PREFIX}{date_str}"

    def _ensure_audit_index_template(self):
        try:
            template_name = f"{config.AUDIT_ES_INDEX_PREFIX}template"
            index_pattern = f"{config.AUDIT_ES_INDEX_PREFIX}*"

            template_body = {
                "index_patterns": [index_pattern],
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "refresh_interval": "5s",
                },
                "mappings": {
                    "dynamic": "strict",
                    "properties": {
                        "timestamp": {"type": "date", "format": "strict_date_optional_time"},
                        "action": {"type": "keyword"},
                        "target": {"type": "keyword"},
                        "operator": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "details": {
                            "type": "object",
                            "dynamic": True,
                            "properties": {
                                "error": {"type": "text"},
                                "old_index": {"type": "keyword"},
                                "new_index": {"type": "keyword"},
                                "target_tier": {"type": "keyword"},
                                "max_segments": {"type": "integer"},
                                "target_shards": {"type": "integer"},
                                "dry_run": {"type": "boolean"},
                            },
                        },
                    },
                },
            }

            self._es_client.client.indices.put_index_template(
                name=template_name,
                body=template_body,
            )
            logger.info("Ensured audit index template: %s", template_name)
        except es_exceptions.ElasticsearchException as e:
            logger.warning("Failed to create audit index template: %s", e)

    def _start_background_flusher(self):
        def flusher():
            while not self._flush_stop_event.is_set():
                try:
                    self._flush_stop_event.wait(config.AUDIT_ES_FLUSH_INTERVAL)
                    self.flush_buffer()
                except Exception as e:
                    logger.error("Error in audit flusher thread: %s", e)

        self._flush_thread = threading.Thread(target=flusher, daemon=True)
        self._flush_thread.start()
        logger.info("Started audit background flusher thread")

    def stop(self):
        if self._flush_thread:
            self._flush_stop_event.set()
            self._flush_thread.join(timeout=10)
        self.flush_buffer()

    def flush_buffer(self):
        with self._buffer_lock:
            if not self._batch_buffer:
                return
            batch = self._batch_buffer.copy()
            self._batch_buffer.clear()

        if not config.AUDIT_ENABLE_ES_INDEX or not self._es_client:
            return

        try:
            index_name = self._get_audit_index_name()
            bulk_body = []
            for entry in batch:
                bulk_body.append({"index": {"_index": index_name}})
                bulk_body.append(entry)

            if bulk_body:
                result = self._es_client.client.bulk(body=bulk_body, refresh="wait_for")
                if result.get("errors", False):
                    failed_items = [
                        item for item in result.get("items", [])
                        if item.get("index", {}).get("error")
                    ]
                    logger.error("Failed to index %d audit entries", len(failed_items))
                    with self._buffer_lock:
                        for item in failed_items:
                            original_idx = result["items"].index(item)
                            self._batch_buffer.append(batch[original_idx])
                else:
                    logger.debug("Successfully indexed %d audit entries to %s", len(batch), index_name)
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to flush audit batch to ES: %s", e)
            with self._buffer_lock:
                self._batch_buffer.extend(batch)

    def log(self, action: str, target: str, operator: str = "system",
            status: str = "success", details: dict = None, source: str = "api"):
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "action": action,
            "target": target,
            "operator": operator,
            "status": status,
            "source": source,
            "details": details or {},
        }
        self._audit_logger.info(json.dumps(entry, ensure_ascii=False))
        logger.debug("Audit log: %s %s on %s by %s", action, status, target, operator)

        if config.AUDIT_ENABLE_ES_INDEX:
            with self._buffer_lock:
                self._batch_buffer.append(entry)
                if len(self._batch_buffer) >= config.AUDIT_ES_BATCH_SIZE:
                    self.flush_buffer()

    def log_rollover(self, alias: str, old_index: str, new_index: str,
                     operator: str = "system", dry_run: bool = False):
        self.log(
            action="rollover" if not dry_run else "rollover_dry_run",
            target=alias,
            operator=operator,
            status="success",
            details={
                "old_index": old_index,
                "new_index": new_index,
                "dry_run": dry_run,
            },
        )

    def log_freeze(self, index_name: str, operator: str = "system"):
        self.log(action="freeze", target=index_name, operator=operator)

    def log_unfreeze(self, index_name: str, operator: str = "system"):
        self.log(action="unfreeze", target=index_name, operator=operator)

    def log_delete(self, index_name: str, operator: str = "system"):
        self.log(action="delete", target=index_name, operator=operator)

    def log_migrate(self, index_name: str, target_tier: str, operator: str = "system"):
        self.log(
            action=f"migrate_to_{target_tier}",
            target=index_name,
            operator=operator,
            details={"target_tier": target_tier},
        )

    def log_forcemerge(self, index_name: str, max_segments: int, operator: str = "system"):
        self.log(
            action="forcemerge",
            target=index_name,
            operator=operator,
            details={"max_segments": max_segments},
        )

    def log_shrink(self, index_name: str, target_name: str, target_shards: int, operator: str = "system"):
        self.log(
            action="shrink",
            target=index_name,
            operator=operator,
            details={"target_name": target_name, "target_shards": target_shards},
        )

    def log_policy_change(self, policy_name: str, action: str, operator: str = "system"):
        self.log(
            action=f"policy_{action}",
            target=policy_name,
            operator=operator,
        )

    def log_error(self, action: str, target: str, error: str, operator: str = "system"):
        self.log(
            action=action,
            target=target,
            operator=operator,
            status="error",
            details={"error": error},
        )

    def _query_file_log(self, action: str = None, target: str = None,
                        operator: str = None, status: str = None,
                        start_time: str = None, end_time: str = None,
                        limit: int = 100) -> list:
        log_file = os.path.join(config.AUDIT_LOG_DIR, "ilm_audit.log")
        if not os.path.exists(log_file):
            return []

        results = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if action and entry.get("action") != action:
                        continue
                    if target and entry.get("target") != target:
                        continue
                    if operator and entry.get("operator") != operator:
                        continue
                    if status and entry.get("status") != status:
                        continue
                    if start_time and entry.get("timestamp", "") < start_time:
                        continue
                    if end_time and entry.get("timestamp", "") > end_time:
                        continue

                    results.append(entry)
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error("Failed to query file audit log: %s", e)

        results.reverse()
        return results

    def _build_es_query(self, action: str = None, target: str = None,
                        operator: str = None, status: str = None,
                        start_time: str = None, end_time: str = None) -> dict:
        must_clauses = []

        if action:
            must_clauses.append({"term": {"action": action}})
        if target:
            must_clauses.append({"term": {"target": target}})
        if operator:
            must_clauses.append({"term": {"operator": operator}})
        if status:
            must_clauses.append({"term": {"status": status}})
        if start_time or end_time:
            range_clause = {}
            if start_time:
                range_clause["gte"] = start_time
            if end_time:
                range_clause["lte"] = end_time
            must_clauses.append({"range": {"timestamp": range_clause}})

        if not must_clauses:
            return {"match_all": {}}
        return {"bool": {"must": must_clauses}}

    def query_audit_log(self, action: str = None, target: str = None,
                        operator: str = None, status: str = None,
                        start_time: str = None, end_time: str = None,
                        limit: int = 100) -> list:
        if not config.AUDIT_ENABLE_ES_INDEX or not self._es_client:
            return self._query_file_log(action, target, operator, status, start_time, end_time, limit)

        try:
            self.flush_buffer()
            query = self._build_es_query(action, target, operator, status, start_time, end_time)
            index_pattern = f"{config.AUDIT_ES_INDEX_PREFIX}*"

            body = {
                "query": query,
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": limit,
            }

            result = self._es_client.client.search(index=index_pattern, body=body)
            hits = result.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]
        except es_exceptions.ElasticsearchException as e:
            logger.warning("Failed to query audit from ES, falling back to file: %s", e)
            return self._query_file_log(action, target, operator, status, start_time, end_time, limit)

    def search_audit_log(self, query_body: dict) -> dict:
        if not config.AUDIT_ENABLE_ES_INDEX or not self._es_client:
            return {"error": "ES audit indexing is not enabled", "results": []}

        try:
            self.flush_buffer()
            index_pattern = f"{config.AUDIT_ES_INDEX_PREFIX}*"
            result = self._es_client.client.search(index=index_pattern, body=query_body)
            hits = result.get("hits", {}).get("hits", [])
            return {
                "total": result.get("hits", {}).get("total", {}).get("value", 0),
                "max_score": result.get("hits", {}).get("max_score", 0),
                "took_ms": result.get("took", 0),
                "timed_out": result.get("timed_out", False),
                "results": [
                    {"_id": hit["_id"], "_score": hit["_score"], **hit["_source"]}
                    for hit in hits
                ],
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to search audit log: %s", e)
            return {"error": str(e), "results": []}

    def aggregate_audit_log(self, aggregation_body: dict) -> dict:
        if not config.AUDIT_ENABLE_ES_INDEX or not self._es_client:
            return {"error": "ES audit indexing is not enabled", "aggregations": {}}

        try:
            self.flush_buffer()
            index_pattern = f"{config.AUDIT_ES_INDEX_PREFIX}*"
            body = {"size": 0, "aggs": aggregation_body}
            result = self._es_client.client.search(index=index_pattern, body=body)
            return {
                "aggregations": result.get("aggregations", {}),
                "took_ms": result.get("took", 0),
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to aggregate audit log: %s", e)
            return {"error": str(e), "aggregations": {}}

    def get_audit_stats(self) -> dict:
        if not config.AUDIT_ENABLE_ES_INDEX or not self._es_client:
            return {
                "es_indexing_enabled": False,
                "pending_buffer_size": len(self._batch_buffer),
            }

        try:
            self.flush_buffer()
            index_pattern = f"{config.AUDIT_ES_INDEX_PREFIX}*"

            body = {
                "size": 0,
                "aggs": {
                    "by_action": {"terms": {"field": "action", "size": 50}},
                    "by_status": {"terms": {"field": "status", "size": 10}},
                    "by_operator": {"terms": {"field": "operator", "size": 50}},
                    "by_target": {"terms": {"field": "target", "size": 50}},
                    "by_source": {"terms": {"field": "source", "size": 10}},
                    "errors_count": {
                        "filter": {"term": {"status": "error"}},
                    },
                },
            }

            result = self._es_client.client.search(index=index_pattern, body=body)
            aggs = result.get("aggregations", {})
            count_result = self._es_client.client.count(index=index_pattern)

            return {
                "es_indexing_enabled": True,
                "audit_index": index_pattern,
                "total_entries": count_result.get("count", 0),
                "pending_buffer_size": len(self._batch_buffer),
                "by_action": [
                    {"action": b["key"], "count": b["doc_count"]}
                    for b in aggs.get("by_action", {}).get("buckets", [])
                ],
                "by_status": [
                    {"status": b["key"], "count": b["doc_count"]}
                    for b in aggs.get("by_status", {}).get("buckets", [])
                ],
                "by_operator": [
                    {"operator": b["key"], "count": b["doc_count"]}
                    for b in aggs.get("by_operator", {}).get("buckets", [])
                ],
                "by_target": [
                    {"target": b["key"], "count": b["doc_count"]}
                    for b in aggs.get("by_target", {}).get("buckets", [])
                ],
                "by_source": [
                    {"source": b["key"], "count": b["doc_count"]}
                    for b in aggs.get("by_source", {}).get("buckets", [])
                ],
                "errors_count": aggs.get("errors_count", {}).get("doc_count", 0),
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get audit stats: %s", e)
            return {
                "es_indexing_enabled": True,
                "error": str(e),
                "pending_buffer_size": len(self._batch_buffer),
            }
