import logging
import time
from datetime import datetime, timezone
from elasticsearch import exceptions as es_exceptions
from es_ilm_tool.es_client import ESClient
from es_ilm_tool.ilm_policy import ILMPolicyManager
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class IndexInfo:
    def __init__(self, name: str, size_bytes: int, doc_count: int,
                 creation_date_ms: int, status: str, tier: str,
                 ilm_policy: str = "", ilm_phase: str = "",
                 shards: dict = None):
        self.name = name
        self.size_bytes = size_bytes
        self.doc_count = doc_count
        self.creation_date = datetime.fromtimestamp(creation_date_ms / 1000, tz=timezone.utc) if creation_date_ms else None
        self.status = status
        self.tier = tier
        self.ilm_policy = ilm_policy
        self.ilm_phase = ilm_phase
        self.shards = shards or {}

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)

    @property
    def age_days(self) -> int:
        if not self.creation_date:
            return 0
        delta = datetime.now(tz=timezone.utc) - self.creation_date
        return delta.days

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "size_gb": round(self.size_gb, 2),
            "doc_count": self.doc_count,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "age_days": self.age_days,
            "status": self.status,
            "tier": self.tier,
            "ilm_policy": self.ilm_policy,
            "ilm_phase": self.ilm_phase,
            "shards": self.shards,
        }


class LifecycleEngine:
    def __init__(self):
        self.es = ESClient()
        self.ilm_manager = ILMPolicyManager()

    def get_index_info(self, index_name: str) -> IndexInfo:
        stats = self.es.get_index_stats(index_name)
        settings = self.es.get_index_settings(index_name)

        primaries = stats.get("primaries", {})
        size_bytes = primaries.get("store", {}).get("size_in_bytes", 0)
        doc_count = primaries.get("docs", {}).get("count", 0)

        index_settings = settings.get("index", {})
        creation_date_ms = int(index_settings.get("creation_date", 0))
        status = stats.get("health", "unknown")
        tier = self._determine_tier(index_settings)
        ilm_policy = index_settings.get("lifecycle", {}).get("name", "")
        ilm_phase = ""

        if ilm_policy:
            ilm_status = self.ilm_manager.get_index_ilm_status(index_name)
            ilm_phase = ilm_status.get("phase", "")

        return IndexInfo(
            name=index_name,
            size_bytes=size_bytes,
            doc_count=doc_count,
            creation_date_ms=creation_date_ms,
            status=status,
            tier=tier,
            ilm_policy=ilm_policy,
            ilm_phase=ilm_phase,
        )

    def _determine_tier(self, index_settings: dict) -> str:
        routing = index_settings.get("routing", {}).get("allocation", {})
        require = routing.get("require", {})
        include = routing.get("include", {})

        for attr_key, tier_name in [
            (config.HOT_TIER_NODE_ATTR, "hot"),
            (config.WARM_TIER_NODE_ATTR, "warm"),
            (config.COLD_TIER_NODE_ATTR, "cold"),
        ]:
            if attr_key in require or attr_key in include:
                return tier_name
        return "hot"

    def list_all_indices(self, pattern: str = "*") -> list:
        raw_indices = self.es.get_all_indices(pattern)
        result = []
        for idx in raw_indices:
            name = idx.get("index", "")
            if name.startswith("."):
                continue
            try:
                info = self.get_index_info(name)
                result.append(info.to_dict())
            except Exception as e:
                logger.warning("Failed to get info for index %s: %s", name, e)
        return result

    def should_rollover(self, info: IndexInfo) -> bool:
        if info.size_gb >= config.ROLLOVER_MAX_SIZE_GB:
            return True
        if info.doc_count >= config.ROLLOVER_MAX_DOCS:
            return True
        if info.age_days >= config.ROLLOVER_MAX_AGE_DAYS:
            return True
        return False

    def should_freeze(self, info: IndexInfo) -> bool:
        return info.age_days >= config.FREEZE_AGE_DAYS

    def should_delete(self, info: IndexInfo) -> bool:
        return info.age_days >= config.DELETE_AGE_DAYS

    def should_migrate_to_warm(self, info: IndexInfo) -> bool:
        return info.age_days >= config.MIGRATE_TO_WARM_AGE_DAYS and info.tier == "hot"

    def should_migrate_to_cold(self, info: IndexInfo) -> bool:
        return info.age_days >= config.MIGRATE_TO_COLD_AGE_DAYS and info.tier in ("hot", "warm")

    def rollover(self, alias: str, conditions: dict = None) -> dict:
        default_conditions = {
            "max_size": f"{config.ROLLOVER_MAX_SIZE_GB}gb",
            "max_docs": config.ROLLOVER_MAX_DOCS,
            "max_age": f"{config.ROLLOVER_MAX_AGE_DAYS}d",
        }
        if conditions:
            default_conditions.update(conditions)

        try:
            result = self.es.client.indices.rollover(
                alias=alias,
                body={"conditions": default_conditions},
            )
            logger.info("Rollover executed for alias %s: %s", alias, result)
            return {
                "success": True,
                "alias": alias,
                "rolled_over": result.get("rolled_over", False),
                "old_index": result.get("old_index", ""),
                "new_index": result.get("new_index", ""),
                "conditions": default_conditions,
                "dry_run": False,
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Rollover failed for alias %s: %s", alias, e)
            return {"success": False, "alias": alias, "error": str(e)}

    def rollover_dry_run(self, alias: str, conditions: dict = None) -> dict:
        default_conditions = {
            "max_size": f"{config.ROLLOVER_MAX_SIZE_GB}gb",
            "max_docs": config.ROLLOVER_MAX_DOCS,
            "max_age": f"{config.ROLLOVER_MAX_AGE_DAYS}d",
        }
        if conditions:
            default_conditions.update(conditions)

        try:
            result = self.es.client.indices.rollover(
                alias=alias,
                body={"conditions": default_conditions},
                dry_run=True,
            )
            return {
                "success": True,
                "alias": alias,
                "would_rollover": result.get("rolled_over", False),
                "conditions_met": result.get("conditions", {}),
                "dry_run": True,
            }
        except es_exceptions.ElasticsearchException as e:
            return {"success": False, "alias": alias, "error": str(e), "dry_run": True}

    def freeze_index(self, index_name: str) -> dict:
        try:
            self.es.client.indices.freeze(index=index_name)
            logger.info("Frozen index: %s", index_name)
            return {"success": True, "index": index_name, "action": "freeze"}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to freeze index %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "freeze", "error": str(e)}

    def unfreeze_index(self, index_name: str) -> dict:
        try:
            self.es.client.indices.unfreeze(index=index_name)
            logger.info("Unfrozen index: %s", index_name)
            return {"success": True, "index": index_name, "action": "unfreeze"}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to unfreeze index %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "unfreeze", "error": str(e)}

    def delete_index(self, index_name: str) -> dict:
        try:
            self.es.client.indices.delete(index=index_name)
            logger.info("Deleted index: %s", index_name)
            return {"success": True, "index": index_name, "action": "delete"}
        except es_exceptions.NotFoundError:
            return {"success": False, "index": index_name, "action": "delete", "error": "Index not found"}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to delete index %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "delete", "error": str(e)}

    def forcemerge_index(self, index_name: str, max_segments: int = 1) -> dict:
        try:
            self.es.client.indices.forcemerge(index=index_name, max_num_segments=max_segments)
            logger.info("Force-merged index %s to %d segments", index_name, max_segments)
            return {"success": True, "index": index_name, "action": "forcemerge", "max_segments": max_segments}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to forcemerge %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "forcemerge", "error": str(e)}

    def shrink_index(self, index_name: str, target_shards: int = 1) -> dict:
        try:
            source_settings = {"index.blocks.write": True}
            self.es.client.indices.put_settings(index=index_name, body=source_settings)

            target_name = f"{index_name}-shrunk"
            body = {"number_of_shards": target_shards}
            self.es.client.indices.shrink(index=index_name, target=target_name, body=body)
            logger.info("Shrunk index %s to %s with %d shards", index_name, target_name, target_shards)
            return {"success": True, "index": index_name, "target": target_name, "action": "shrink", "target_shards": target_shards}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to shrink index %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "shrink", "error": str(e)}

    def get_fragmentation_ratio(self, index_name: str) -> dict:
        try:
            stats = self.es.get_index_stats(index_name)
            if not stats:
                return {"index": index_name, "error": "Index not found"}

            primaries = stats.get("primaries", {})
            store = primaries.get("store", {})
            segments = primaries.get("segments", {})
            docs = primaries.get("docs", {})

            size_in_bytes = store.get("size_in_bytes", 0)
            segment_size_in_bytes = segments.get("size_in_bytes", 0)
            doc_count = docs.get("count", 0)
            deleted_docs = docs.get("deleted", 0)
            segment_count = segments.get("count", 0)

            if segment_size_in_bytes > 0 and size_in_bytes > 0:
                fragmentation_ratio = round(
                    (size_in_bytes - segment_size_in_bytes) / size_in_bytes * 100, 2
                )
            else:
                fragmentation_ratio = 0.0

            if doc_count > 0:
                deleted_ratio = round(deleted_docs / doc_count * 100, 2)
            else:
                deleted_ratio = 0.0

            info = self.get_index_info(index_name)

            return {
                "index": index_name,
                "size_in_bytes": size_in_bytes,
                "segment_size_in_bytes": segment_size_in_bytes,
                "doc_count": doc_count,
                "deleted_docs": deleted_docs,
                "segment_count": segment_count,
                "fragmentation_ratio_percent": fragmentation_ratio,
                "deleted_docs_ratio_percent": deleted_ratio,
                "age_days": info.age_days,
                "tier": info.tier,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get fragmentation for %s: %s", index_name, e)
            return {"index": index_name, "error": str(e)}

    def should_rebuild(self, frag_info: dict) -> bool:
        if "error" in frag_info:
            return False
        if frag_info["age_days"] < config.REBUILD_MIN_AGE_DAYS:
            return False
        if (frag_info["size_in_bytes"] / (1024 ** 3)) < config.REBUILD_MIN_SIZE_GB:
            return False
        if frag_info["fragmentation_ratio_percent"] >= config.REBUILD_FRAGMENTATION_THRESHOLD:
            return True
        if frag_info["deleted_docs_ratio_percent"] >= config.REBUILD_FRAGMENTATION_THRESHOLD:
            return True
        return False

    def get_highly_fragmented_indices(self, pattern: str = "*") -> list:
        indices = self.list_all_indices(pattern)
        fragmented = []
        for idx_dict in indices:
            name = idx_dict.get("name", "")
            frag_info = self.get_fragmentation_ratio(name)
            if "error" in frag_info:
                continue
            if self.should_rebuild(frag_info):
                fragmented.append(frag_info)
        fragmented.sort(key=lambda x: x["fragmentation_ratio_percent"], reverse=True)
        return fragmented

    def rebuild_index(self, index_name: str, target_shards: int = None,
                      slices: str = None, wait_for_completion: bool = True) -> dict:
        try:
            frag_info = self.get_fragmentation_ratio(index_name)
            settings = self.es.get_index_settings(index_name)
            mapping = self.es.get_index_mapping(index_name)

            index_settings = settings.get("index", {})
            source_shards = int(index_settings.get("number_of_shards", 1))
            replicas = int(index_settings.get("number_of_replicas", 1))

            if target_shards is None:
                target_shards = source_shards

            temp_index = f"{index_name}-rebuild-{int(datetime.now().timestamp())}"

            create_body = {
                "settings": {
                    "number_of_shards": target_shards,
                    "number_of_replicas": replicas,
                    "index.routing.allocation.require": index_settings.get("routing", {}).get("allocation", {}).get("require", {}),
                },
                "mappings": mapping,
            }

            self.es.client.indices.create(index=temp_index, body=create_body)
            logger.info("Created temp index %s for rebuilding %s", temp_index, index_name)

            slices_value = slices if slices else config.REBUILD_SLICES
            if slices_value == "auto":
                slices_value = target_shards

            reindex_body = {
                "source": {
                    "index": index_name,
                },
                "dest": {
                    "index": temp_index,
                },
                "conflicts": "proceed",
            }

            reindex_params = {
                "wait_for_completion": wait_for_completion,
                "slices": slices_value,
                "request_timeout": "1h",
            }

            reindex_result = self.es.client.reindex(body=reindex_body, **reindex_params)

            if not wait_for_completion:
                task_id = reindex_result.get("task")
                logger.info("Reindex task submitted for %s, task_id: %s", index_name, task_id)
                return {
                    "success": True,
                    "index": index_name,
                    "temp_index": temp_index,
                    "action": "rebuild_started",
                    "task_id": task_id,
                    "status": "running",
                    "fragmentation_before": frag_info,
                }

            created = reindex_result.get("created", 0)
            updated = reindex_result.get("updated", 0)
            failures = reindex_result.get("failures", [])

            if failures:
                logger.warning("Reindex had %d failures for %s", len(failures), index_name)
                return {
                    "success": False,
                    "index": index_name,
                    "temp_index": temp_index,
                    "action": "rebuild",
                    "error": f"Reindex had {len(failures)} failures",
                    "failures": failures,
                }

            alias_info = self.es.client.indices.get_alias(index=index_name)
            aliases = alias_info.get(index_name, {}).get("aliases", {})

            logger.info("Reindex completed: %d created, %d updated", created, updated)

            self.es.client.indices.delete(index=index_name)
            logger.info("Deleted original index %s", index_name)

            self.es.client.indices.put_settings(
                index=temp_index,
                body={"index.blocks.write": False}
            )
            self.es.client.indices.rename(index=temp_index, new_name=index_name)

            for alias_name in aliases:
                self.es.client.indices.put_alias(index=index_name, name=alias_name)

            return {
                "success": True,
                "index": index_name,
                "action": "rebuild",
                "temp_index": temp_index,
                "docs_processed": created + updated,
                "fragmentation_before": frag_info,
                "aliases_restored": list(aliases.keys()),
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to rebuild index %s: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "rebuild", "error": str(e)}

    def auto_rebuild(self, pattern: str = "*", dry_run: bool = True, max_count: int = None) -> dict:
        max_to_process = max_count or config.REBUILD_MAX_CONCURRENT
        fragmented = self.get_highly_fragmented_indices(pattern)

        if dry_run:
            return {
                "dry_run": True,
                "recommended_rebuilds": fragmented,
                "count": len(fragmented),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }

        results = []
        for frag_info in fragmented[:max_to_process]:
            index_name = frag_info["index"]
            logger.info("Auto-rebuilding index %s (fragmentation: %.1f%%)",
                        index_name, frag_info["fragmentation_ratio_percent"])
            result = self.rebuild_index(index_name)
            results.append(result)

        return {
            "dry_run": False,
            "rebuild_results": results,
            "total_candidates": len(fragmented),
            "processed": len(results),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def get_nodes_by_tier(self, tier: str) -> list:
        try:
            node_attr_map = {
                "hot": config.HOT_TIER_NODE_ATTR,
                "warm": config.WARM_TIER_NODE_ATTR,
                "cold": config.COLD_TIER_NODE_ATTR,
            }
            attr = node_attr_map.get(tier, tier)
            result = self.es.client.nodes.info()
            nodes = []
            for node_id, node_data in result.get("nodes", {}).items():
                attrs = node_data.get("attributes", {})
                if attr in attrs:
                    nodes.append({
                        "node_id": node_id,
                        "name": node_data.get("name", ""),
                        "host": node_data.get("host", ""),
                        "ip": node_data.get("ip", ""),
                        "attributes": attrs,
                    })
            return nodes
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get nodes for tier %s: %s", tier, e)
            return []

    def get_cluster_disk_usage(self) -> dict:
        try:
            node_stats = self.es.client.nodes.stats(metric=["fs", "indices"])
            result = {
                "nodes": {},
                "total_disk_in_bytes": 0,
                "free_disk_in_bytes": 0,
                "used_disk_in_bytes": 0,
                "usage_percent": 0.0,
            }

            nodes_data = node_stats.get("nodes", {})
            for node_id, node_info in nodes_data.items():
                fs = node_info.get("fs", {})
                total = fs.get("total", {}).get("total_in_bytes", 0)
                free = fs.get("total", {}).get("available_in_bytes", 0)
                used = total - free if total > 0 else 0
                percent = (used / total * 100) if total > 0 else 0.0

                result["nodes"][node_id] = {
                    "name": node_info.get("name", ""),
                    "host": node_info.get("host", ""),
                    "total_disk_in_bytes": total,
                    "free_disk_in_bytes": free,
                    "used_disk_in_bytes": used,
                    "usage_percent": round(percent, 2),
                }
                result["total_disk_in_bytes"] += total
                result["free_disk_in_bytes"] += free
                result["used_disk_in_bytes"] += used

            if result["total_disk_in_bytes"] > 0:
                result["usage_percent"] = round(
                    (result["used_disk_in_bytes"] / result["total_disk_in_bytes"]) * 100, 2
                )
            return result
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get cluster disk usage: %s", e)
            return {"error": str(e)}

    def get_tier_disk_usage(self, tier: str) -> dict:
        try:
            tier_nodes = self.get_nodes_by_tier(tier)
            tier_node_ids = [n["node_id"] for n in tier_nodes]

            if not tier_node_ids:
                return {
                    "tier": tier,
                    "nodes": [],
                    "total_disk_in_bytes": 0,
                    "free_disk_in_bytes": 0,
                    "used_disk_in_bytes": 0,
                    "usage_percent": 0.0,
                    "watermark_status": "unknown",
                }

            node_stats = self.es.client.nodes.stats(
                node_id=",".join(tier_node_ids),
                metric=["fs"],
            )

            nodes_data = node_stats.get("nodes", {})
            result = {
                "tier": tier,
                "nodes": [],
                "total_disk_in_bytes": 0,
                "free_disk_in_bytes": 0,
                "used_disk_in_bytes": 0,
                "usage_percent": 0.0,
                "watermark_status": "ok",
            }

            highest_usage = 0.0
            for node_id, node_info in nodes_data.items():
                fs = node_info.get("fs", {})
                total = fs.get("total", {}).get("total_in_bytes", 0)
                free = fs.get("total", {}).get("available_in_bytes", 0)
                used = total - free if total > 0 else 0
                percent = (used / total * 100) if total > 0 else 0.0
                highest_usage = max(highest_usage, percent)

                node_disk = {
                    "node_id": node_id,
                    "name": node_info.get("name", ""),
                    "host": node_info.get("host", ""),
                    "total_disk_in_bytes": total,
                    "free_disk_in_bytes": free,
                    "used_disk_in_bytes": used,
                    "usage_percent": round(percent, 2),
                }
                result["nodes"].append(node_disk)
                result["total_disk_in_bytes"] += total
                result["free_disk_in_bytes"] += free
                result["used_disk_in_bytes"] += used

            if result["total_disk_in_bytes"] > 0:
                result["usage_percent"] = round(
                    (result["used_disk_in_bytes"] / result["total_disk_in_bytes"]) * 100, 2
                )

            if highest_usage >= config.DISK_WATERMARK_FLOOD_STAGE_PERCENT:
                result["watermark_status"] = "flood_stage"
            elif highest_usage >= config.DISK_WATERMARK_HIGH_PERCENT:
                result["watermark_status"] = "high"
            elif highest_usage >= config.DISK_WATERMARK_LOW_PERCENT:
                result["watermark_status"] = "low"
            else:
                result["watermark_status"] = "ok"

            result["highest_usage_percent"] = round(highest_usage, 2)
            result["watermarks"] = {
                "low": config.DISK_WATERMARK_LOW_PERCENT,
                "high": config.DISK_WATERMARK_HIGH_PERCENT,
                "flood_stage": config.DISK_WATERMARK_FLOOD_STAGE_PERCENT,
            }
            return result
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get disk usage for tier %s: %s", tier, e)
            return {"tier": tier, "error": str(e)}

    def check_disk_watermark_for_migration(self, target_tier: str, index_size_bytes: int = 0) -> dict:
        tier_disk = self.get_tier_disk_usage(target_tier)
        if "error" in tier_disk:
            return {"can_migrate": False, "reason": tier_disk["error"]}

        status = tier_disk["watermark_status"]
        available = tier_disk["free_disk_in_bytes"]
        nodes = tier_disk.get("nodes", [])

        if status == "flood_stage":
            return {
                "can_migrate": False,
                "reason": "Flood stage watermark exceeded",
                "details": tier_disk,
                "wait_recommended": True,
                "retry_after_seconds": config.DISK_WAIT_BACKOFF_SECONDS,
            }

        if status == "high":
            return {
                "can_migrate": False,
                "reason": "High watermark exceeded",
                "details": tier_disk,
                "wait_recommended": True,
                "retry_after_seconds": config.DISK_WAIT_BACKOFF_SECONDS,
            }

        if status == "low" and index_size_bytes > 0:
            safe_available = available * (1 - config.DISK_WATERMARK_HIGH_PERCENT / 100)
            if index_size_bytes > safe_available:
                return {
                    "can_migrate": False,
                    "reason": "Insufficient disk space after migration would exceed high watermark",
                    "details": tier_disk,
                    "index_size_bytes": index_size_bytes,
                    "safe_available_bytes": int(safe_available),
                    "wait_recommended": True,
                    "retry_after_seconds": config.DISK_WAIT_BACKOFF_SECONDS,
                }

        node_count = len(nodes)
        if node_count == 0:
            return {
                "can_migrate": False,
                "reason": f"No nodes found for tier '{target_tier}'",
                "details": tier_disk,
                "wait_recommended": True,
                "retry_after_seconds": config.DISK_WAIT_BACKOFF_SECONDS,
            }

        per_node_needed = index_size_bytes / node_count if node_count > 0 else index_size_bytes
        for node in nodes:
            node_free = node.get("free_disk_in_bytes", 0)
            node_usage = node.get("usage_percent", 0)
            node_high = (100 - config.DISK_WATERMARK_HIGH_PERCENT) / 100 * node.get("total_disk_in_bytes", node_free)
            if per_node_needed > node_high and node_usage >= config.DISK_WATERMARK_LOW_PERCENT:
                return {
                    "can_migrate": False,
                    "reason": f"Node {node.get('name')} would exceed high watermark after migration",
                    "details": tier_disk,
                    "node_name": node.get("name"),
                    "wait_recommended": True,
                    "retry_after_seconds": config.DISK_WAIT_BACKOFF_SECONDS,
                }

        return {
            "can_migrate": True,
            "reason": "Disk watermarks within safe limits",
            "details": tier_disk,
            "wait_recommended": False,
        }

    def wait_for_disk_space(self, target_tier: str, index_size_bytes: int = 0) -> dict:
        for attempt in range(config.DISK_WAIT_MAX_RETRIES):
            check = self.check_disk_watermark_for_migration(target_tier, index_size_bytes)
            if check["can_migrate"]:
                return {
                    "success": True,
                    "attempts": attempt + 1,
                    "final_check": check,
                }
            if not check.get("wait_recommended", True):
                return {
                    "success": False,
                    "attempts": attempt + 1,
                    "reason": check.get("reason", "Unknown"),
                    "final_check": check,
                }
            wait_time = config.DISK_WAIT_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning(
                "Disk watermark check failed for tier %s (attempt %d/%d): %s. Waiting %ds before retry...",
                target_tier, attempt + 1, config.DISK_WAIT_MAX_RETRIES, check.get("reason", ""), wait_time
            )
            time.sleep(wait_time)

        final_check = self.check_disk_watermark_for_migration(target_tier, index_size_bytes)
        return {
            "success": False,
            "attempts": config.DISK_WAIT_MAX_RETRIES,
            "reason": "Max retries exceeded waiting for disk space",
            "final_check": final_check,
        }

    def migrate_to_warm(self, index_name: str) -> dict:
        try:
            info = self.get_index_info(index_name)
            disk_check = self.wait_for_disk_space("warm", info.size_bytes)
            if not disk_check["success"]:
                logger.error("Cannot migrate %s to warm: %s", index_name, disk_check.get("reason", ""))
                return {
                    "success": False,
                    "index": index_name,
                    "action": "migrate_to_warm",
                    "target_tier": "warm",
                    "error": disk_check.get("reason", "Disk watermark check failed"),
                    "disk_check": disk_check,
                }

            body = {
                "index.routing.allocation.require.data_tier": "warm",
                "index.number_of_replicas": 1,
            }
            self.es.client.indices.put_settings(index=index_name, body=body)
            logger.info("Migrated index %s to warm tier", index_name)
            return {
                "success": True,
                "index": index_name,
                "action": "migrate_to_warm",
                "target_tier": "warm",
                "disk_check": disk_check,
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to migrate %s to warm: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "migrate_to_warm", "error": str(e)}

    def migrate_to_cold(self, index_name: str) -> dict:
        try:
            info = self.get_index_info(index_name)
            disk_check = self.wait_for_disk_space("cold", info.size_bytes)
            if not disk_check["success"]:
                logger.error("Cannot migrate %s to cold: %s", index_name, disk_check.get("reason", ""))
                return {
                    "success": False,
                    "index": index_name,
                    "action": "migrate_to_cold",
                    "target_tier": "cold",
                    "error": disk_check.get("reason", "Disk watermark check failed"),
                    "disk_check": disk_check,
                }

            body = {
                "index.routing.allocation.require.data_tier": "cold",
                "index.number_of_replicas": 0,
            }
            self.es.client.indices.put_settings(index=index_name, body=body)
            logger.info("Migrated index %s to cold tier", index_name)
            return {
                "success": True,
                "index": index_name,
                "action": "migrate_to_cold",
                "target_tier": "cold",
                "disk_check": disk_check,
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to migrate %s to cold: %s", index_name, e)
            return {"success": False, "index": index_name, "action": "migrate_to_cold", "error": str(e)}

    def auto_lifecycle(self, pattern: str = "*", dry_run: bool = True) -> dict:
        indices = self.list_all_indices(pattern)
        actions = {
            "rollover": [],
            "freeze": [],
            "delete": [],
            "migrate_to_warm": [],
            "migrate_to_cold": [],
        }
        executed = {
            "rollover": [],
            "freeze": [],
            "delete": [],
            "migrate_to_warm": [],
            "migrate_to_cold": [],
        }

        for idx_dict in indices:
            info = IndexInfo(
                name=idx_dict["name"],
                size_bytes=idx_dict["size_bytes"],
                doc_count=idx_dict["doc_count"],
                creation_date_ms=0,
                status=idx_dict["status"],
                tier=idx_dict["tier"],
            )
            if info.creation_date is None and idx_dict.get("creation_date"):
                from datetime import datetime as dt
                info.creation_date = dt.fromisoformat(idx_dict["creation_date"])

            if self.should_delete(info):
                actions["delete"].append(info.name)
                if not dry_run:
                    result = self.delete_index(info.name)
                    executed["delete"].append(result)
            elif self.should_migrate_to_cold(info):
                actions["migrate_to_cold"].append(info.name)
                if not dry_run:
                    result = self.migrate_to_cold(info.name)
                    executed["migrate_to_cold"].append(result)
            elif self.should_freeze(info):
                actions["freeze"].append(info.name)
                if not dry_run:
                    result = self.freeze_index(info.name)
                    executed["freeze"].append(result)
            elif self.should_migrate_to_warm(info):
                actions["migrate_to_warm"].append(info.name)
                if not dry_run:
                    result = self.migrate_to_warm(info.name)
                    executed["migrate_to_warm"].append(result)

            if self.should_rollover(info):
                actions["rollover"].append(info.name)

        return {
            "dry_run": dry_run,
            "recommended_actions": {k: v for k, v in actions.items() if v},
            "executed_actions": {k: v for k, v in executed.items() if v},
            "total_indices_scanned": len(indices),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
