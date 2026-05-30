import logging
import threading
from prometheus_client import Counter, Gauge, Histogram, start_http_server, CollectorRegistry
from es_ilm_tool.es_client import ESClient
from es_ilm_tool import config

logger = logging.getLogger(__name__)

registry = CollectorRegistry()

ILM_ROLLOVER_TOTAL = Counter(
    "es_ilm_rollover_total",
    "Total number of index rollover operations",
    ["alias", "status"],
    registry=registry,
)

ILM_FREEZE_TOTAL = Counter(
    "es_ilm_freeze_total",
    "Total number of index freeze operations",
    ["index", "status"],
    registry=registry,
)

ILM_DELETE_TOTAL = Counter(
    "es_ilm_delete_total",
    "Total number of index delete operations",
    ["index", "status"],
    registry=registry,
)

ILM_MIGRATE_TOTAL = Counter(
    "es_ilm_migrate_total",
    "Total number of index tier migration operations",
    ["index", "target_tier", "status"],
    registry=registry,
)

ES_INDEX_SIZE_BYTES = Gauge(
    "es_index_size_bytes",
    "Size of Elasticsearch index in bytes",
    ["index"],
    registry=registry,
)

ES_INDEX_DOC_COUNT = Gauge(
    "es_index_doc_count",
    "Number of documents in Elasticsearch index",
    ["index"],
    registry=registry,
)

ES_INDEX_AGE_DAYS = Gauge(
    "es_index_age_days",
    "Age of Elasticsearch index in days",
    ["index"],
    registry=registry,
)

ES_CLUSTER_HEALTH = Gauge(
    "es_cluster_health",
    "Elasticsearch cluster health status (0=red, 1=yellow, 2=green)",
    ["cluster"],
    registry=registry,
)

ES_CLUSTER_SHARDS = Gauge(
    "es_cluster_shards",
    "Elasticsearch cluster shard counts",
    ["type"],
    registry=registry,
)

ES_NODE_HEAP_PERCENT = Gauge(
    "es_node_heap_used_percent",
    "Heap usage percent per node",
    ["node", "host"],
    registry=registry,
)

ES_NODE_CPU_PERCENT = Gauge(
    "es_node_cpu_percent",
    "CPU usage percent per node",
    ["node", "host"],
    registry=registry,
)

ILM_OPERATION_DURATION = Histogram(
    "es_ilm_operation_duration_seconds",
    "Duration of ILM operations in seconds",
    ["operation"],
    registry=registry,
)

ES_COST_MONTHLY_TOTAL = Gauge(
    "es_cost_monthly_total",
    "Total monthly cost of Elasticsearch cluster",
    ["currency"],
    registry=registry,
)

ES_COST_TIER_MONTHLY = Gauge(
    "es_cost_tier_monthly",
    "Monthly cost per tier",
    ["tier", "currency"],
    registry=registry,
)

ES_COST_INDEX_MONTHLY = Gauge(
    "es_cost_index_monthly",
    "Monthly cost per index",
    ["index", "tier", "currency"],
    registry=registry,
)

ES_INDEX_FRAGMENTATION_RATIO = Gauge(
    "es_index_fragmentation_ratio_percent",
    "Index fragmentation ratio in percent",
    ["index"],
    registry=registry,
)

ES_INDEX_DELETED_DOCS_RATIO = Gauge(
    "es_index_deleted_docs_ratio_percent",
    "Ratio of deleted documents in percent",
    ["index"],
    registry=registry,
)

ES_CCR_FOLLOWER_COUNT = Gauge(
    "es_ccr_follower_count",
    "Number of CCR follower indices",
    ["remote_cluster"],
    registry=registry,
)

ES_CCR_OPERATIONS_READ_TOTAL = Counter(
    "es_ccr_operations_read_total",
    "Total operations read from leader",
    ["follower_index"],
    registry=registry,
)

ES_CCR_OPERATIONS_WRITTEN_TOTAL = Counter(
    "es_ccr_operations_written_total",
    "Total operations written to follower",
    ["follower_index"],
    registry=registry,
)

ES_CCR_FAILED_FOLLOWERS = Gauge(
    "es_ccr_failed_followers",
    "Number of failed CCR follower indices",
    ["remote_cluster"],
    registry=registry,
)

HEALTH_MAP = {"green": 2, "yellow": 1, "red": 0}


class MetricsExporter:
    def __init__(self):
        self.es = ESClient()
        self._server_started = False
        from es_ilm_tool.lifecycle import LifecycleEngine
        from es_ilm_tool.cost_analysis import CostAnalyzer
        from es_ilm_tool.ccr import CCRManager
        self.lifecycle = LifecycleEngine()
        self.cost_analyzer = CostAnalyzer()
        self.ccr_manager = CCRManager()

    def start_metrics_server(self):
        if self._server_started:
            return
        try:
            start_http_server(config.PROMETHEUS_PORT, registry=registry)
            self._server_started = True
            logger.info("Prometheus metrics server started on port %d", config.PROMETHEUS_PORT)
        except OSError as e:
            logger.warning("Failed to start metrics server: %s", e)

    def record_rollover(self, alias: str, success: bool):
        status = "success" if success else "failure"
        ILM_ROLLOVER_TOTAL.labels(alias=alias, status=status).inc()

    def record_freeze(self, index_name: str, success: bool):
        status = "success" if success else "failure"
        ILM_FREEZE_TOTAL.labels(index=index_name, status=status).inc()

    def record_delete(self, index_name: str, success: bool):
        status = "success" if success else "failure"
        ILM_DELETE_TOTAL.labels(index=index_name, status=status).inc()

    def record_migrate(self, index_name: str, target_tier: str, success: bool):
        status = "success" if success else "failure"
        ILM_MIGRATE_TOTAL.labels(index=index_name, target_tier=target_tier, status=status).inc()

    def update_cost_metrics(self):
        try:
            cluster_cost = self.cost_analyzer.calculate_cluster_cost()
            ES_COST_MONTHLY_TOTAL.labels(currency=config.COST_CURRENCY).set(
                cluster_cost.get("total_monthly_cost", 0)
            )
            for tier, tier_data in cluster_cost.get("by_tier", {}).items():
                ES_COST_TIER_MONTHLY.labels(tier=tier, currency=config.COST_CURRENCY).set(
                    tier_data.get("monthly_cost", 0)
                )
            for idx in cluster_cost.get("most_expensive_indices", []):
                idx_name = idx.get("index", "")
                tier = idx.get("tier", "hot")
                cost = idx.get("monthly_cost", 0)
                if idx_name:
                    ES_COST_INDEX_MONTHLY.labels(
                        index=idx_name, tier=tier, currency=config.COST_CURRENCY
                    ).set(cost)
        except Exception as e:
            logger.error("Failed to update cost metrics: %s", e)

    def update_fragmentation_metrics(self):
        try:
            indices = self.lifecycle.list_all_indices("*")
            for idx_dict in indices:
                name = idx_dict.get("index", "") or idx_dict.get("name", "")
                if not name or name.startswith("."):
                    continue
                frag_info = self.lifecycle.get_fragmentation_ratio(name)
                if "error" in frag_info:
                    continue
                ES_INDEX_FRAGMENTATION_RATIO.labels(index=name).set(
                    frag_info.get("fragmentation_ratio_percent", 0)
                )
                ES_INDEX_DELETED_DOCS_RATIO.labels(index=name).set(
                    frag_info.get("deleted_docs_ratio_percent", 0)
                )
        except Exception as e:
            logger.error("Failed to update fragmentation metrics: %s", e)

    def update_ccr_metrics(self):
        if not config.CCR_ENABLED:
            return
        try:
            ccr_stats = self.ccr_manager.get_ccr_stats()
            if "error" in ccr_stats:
                return
            follower_count = ccr_stats.get("follower_count", 0)
            failed_count = len(ccr_stats.get("failed_followers", []))
            ES_CCR_FOLLOWER_COUNT.labels(remote_cluster=config.CCR_REMOTE_CLUSTER_NAME).set(
                follower_count
            )
            ES_CCR_FAILED_FOLLOWERS.labels(remote_cluster=config.CCR_REMOTE_CLUSTER_NAME).set(
                failed_count
            )
        except Exception as e:
            logger.error("Failed to update CCR metrics: %s", e)

    def update_index_metrics(self):
        try:
            indices = self.es.get_all_indices()
            for idx in indices:
                name = idx.get("index", "")
                if name.startswith("."):
                    continue
                try:
                    stats = self.es.get_index_stats(name)
                    if not stats:
                        continue
                    primaries = stats.get("primaries", {})
                    size = primaries.get("store", {}).get("size_in_bytes", 0)
                    doc_count = primaries.get("docs", {}).get("count", 0)
                    ES_INDEX_SIZE_BYTES.labels(index=name).set(size)
                    ES_INDEX_DOC_COUNT.labels(index=name).set(doc_count)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Failed to update index metrics: %s", e)

    def update_cluster_metrics(self):
        try:
            health = self.es.get_cluster_health()
            cluster_name = health.get("cluster_name", "unknown")
            status = health.get("status", "unknown")
            ES_CLUSTER_HEALTH.labels(cluster=cluster_name).set(HEALTH_MAP.get(status, 0))

            ES_CLUSTER_SHARDS.labels(type="active_primary").set(health.get("active_primary_shards", 0))
            ES_CLUSTER_SHARDS.labels(type="active").set(health.get("active_shards", 0))
            ES_CLUSTER_SHARDS.labels(type="relocating").set(health.get("relocating_shards", 0))
            ES_CLUSTER_SHARDS.labels(type="initializing").set(health.get("initializing_shards", 0))
            ES_CLUSTER_SHARDS.labels(type="unassigned").set(health.get("unassigned_shards", 0))
        except Exception as e:
            logger.error("Failed to update cluster metrics: %s", e)

    def update_node_metrics(self):
        try:
            node_stats = self.es.get_node_stats()
            nodes = node_stats.get("nodes", {})
            for node_id, node_data in nodes.items():
                name = node_data.get("name", "")
                host = node_data.get("host", "")
                cpu = node_data.get("os", {}).get("cpu", {}).get("percent", 0)
                heap = node_data.get("jvm", {}).get("mem", {}).get("heap_used_percent", 0)
                ES_NODE_CPU_PERCENT.labels(node=name, host=host).set(cpu)
                ES_NODE_HEAP_PERCENT.labels(node=name, host=host).set(heap)
        except Exception as e:
            logger.error("Failed to update node metrics: %s", e)

    def update_all_metrics(self):
        self.update_cluster_metrics()
        self.update_index_metrics()
        self.update_node_metrics()
        self.update_cost_metrics()
        self.update_fragmentation_metrics()
        self.update_ccr_metrics()
