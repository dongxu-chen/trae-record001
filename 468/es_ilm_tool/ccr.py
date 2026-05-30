import logging
import fnmatch
from datetime import datetime, timezone
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from es_ilm_tool.es_client import ESClient
from es_ilm_tool.lifecycle import LifecycleEngine
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class CCRManager:
    def __init__(self):
        self.es = ESClient()
        self.engine = LifecycleEngine()
        self._remote_client = None

    @property
    def remote_client(self) -> Elasticsearch:
        if self._remote_client is None:
            try:
                self._remote_client = Elasticsearch(
                    hosts=config.CCR_REMOTE_HOSTS,
                    basic_auth=(config.CCR_REMOTE_USERNAME, config.CCR_REMOTE_PASSWORD),
                    request_timeout=config.ES_TIMEOUT,
                    verify_certs=False,
                    ssl_show_warn=False,
                )
                info = self._remote_client.info()
                logger.info("Connected to remote ES cluster %s: %s",
                            config.CCR_REMOTE_CLUSTER_NAME, info["version"]["number"])
            except es_exceptions.ConnectionError as e:
                logger.error("Failed to connect to remote ES cluster: %s", e)
                raise
        return self._remote_client

    def register_remote_cluster(self) -> dict:
        try:
            body = {
                "persistent": {
                    f"cluster.remote.{config.CCR_REMOTE_CLUSTER_NAME}.seeds": [
                        host.replace("http://", "").replace("https://", "")
                        for host in config.CCR_REMOTE_HOSTS
                    ],
                }
            }
            self.es.client.cluster.put_settings(body=body)
            logger.info("Registered remote cluster: %s", config.CCR_REMOTE_CLUSTER_NAME)
            return {"success": True, "cluster_name": config.CCR_REMOTE_CLUSTER_NAME}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to register remote cluster: %s", e)
            return {"success": False, "error": str(e)}

    def get_remote_cluster_info(self) -> dict:
        try:
            info = self.remote_client.info()
            health = self.remote_client.cluster.health()
            return {
                "cluster_name": info.get("cluster_name"),
                "version": info.get("version", {}).get("number"),
                "status": health.get("status"),
                "number_of_nodes": health.get("number_of_nodes"),
                "active_shards": health.get("active_shards"),
            }
        except Exception as e:
            return {"error": str(e)}

    def create_follower_index(self, leader_index: str, follower_index: str = None) -> dict:
        if not config.CCR_ENABLED:
            return {"success": False, "error": "CCR is not enabled"}

        try:
            if follower_index is None:
                follower_index = leader_index

            settings = self.es.get_index_settings(leader_index)
            number_of_shards = int(settings.get("index", {}).get("number_of_shards", 1))
            number_of_replicas = int(settings.get("index", {}).get("number_of_replicas", 1))

            body = {
                "settings": {
                    "number_of_shards": number_of_shards,
                    "number_of_replicas": number_of_replicas,
                    "index.xpack.ccr.following_index": True,
                },
                "remote_cluster": config.CCR_REMOTE_CLUSTER_NAME,
                "leader_index": leader_index,
                "read_poll_timeout": "1m",
                "max_outstanding_read_requests": config.CCR_REMOTE_MAX_OUTSTANDING_READ_REQUESTS,
                "max_outstanding_write_requests": config.CCR_REMOTE_MAX_OUTSTANDING_WRITES,
                "max_read_request_size": config.CCR_REMOTE_MAX_READ_REQUEST_SIZE,
                "max_retry_delay": "10s",
            }

            self.es.client.ccr.follow(
                index=follower_index,
                body=body,
                wait_for_active_shards=1,
            )

            logger.info("Created follower index %s following leader %s",
                        follower_index, leader_index)

            return {
                "success": True,
                "follower_index": follower_index,
                "leader_index": leader_index,
                "remote_cluster": config.CCR_REMOTE_CLUSTER_NAME,
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to create follower for %s: %s", leader_index, e)
            return {"success": False, "leader_index": leader_index, "error": str(e)}

    def unfollow_index(self, follower_index: str) -> dict:
        try:
            self.es.client.ccr.unfollow(index=follower_index)
            logger.info("Unfollowed index %s", follower_index)
            return {"success": True, "follower_index": follower_index}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to unfollow %s: %s", follower_index, e)
            return {"success": False, "follower_index": follower_index, "error": str(e)}

    def pause_follow(self, follower_index: str) -> dict:
        try:
            self.es.client.ccr.pause_follow(index=follower_index)
            logger.info("Paused follow for %s", follower_index)
            return {"success": True, "follower_index": follower_index}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to pause follow %s: %s", follower_index, e)
            return {"success": False, "follower_index": follower_index, "error": str(e)}

    def resume_follow(self, follower_index: str) -> dict:
        try:
            self.es.client.ccr.resume_follow(index=follower_index)
            logger.info("Resumed follow for %s", follower_index)
            return {"success": True, "follower_index": follower_index}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to resume follow %s: %s", follower_index, e)
            return {"success": False, "follower_index": follower_index, "error": str(e)}

    def get_follower_info(self, follower_index: str) -> dict:
        try:
            result = self.es.client.ccr.follow_info(index=follower_index)
            follower_info = result.get("follower_indices", [])
            if follower_info:
                return follower_info[0]
            return {}
        except es_exceptions.NotFoundError:
            return {}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get follower info for %s: %s", follower_index, e)
            return {"error": str(e)}

    def get_follower_stats(self, follower_index: str) -> dict:
        try:
            result = self.es.client.ccr.stats(index=follower_index)
            return result
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get follower stats for %s: %s", follower_index, e)
            return {"error": str(e)}

    def list_follower_indices(self) -> list:
        try:
            result = self.es.client.ccr.follow_info()
            followers = result.get("follower_indices", [])
            result_list = []
            for f in followers:
                result_list.append({
                    "follower_index": f.get("follower_index"),
                    "remote_cluster": f.get("remote_cluster"),
                    "leader_index": f.get("leader_index"),
                    "status": f.get("status"),
                    "parameters": f.get("parameters", {}),
                })
            return result_list
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to list follower indices: %s", e)
            return []

    def get_leader_indices_to_sync(self) -> list:
        try:
            if config.CCR_AUTO_FOLLOW_PATTERN:
                patterns = config.CCR_AUTO_FOLLOW_PATTERN.split(",")
            else:
                patterns = ["*"]

            indices = self.engine.list_all_indices("*")
            to_sync = []

            for idx_dict in indices:
                name = idx_dict.get("name", "")
                tier = idx_dict.get("tier", "hot")

                if config.CCR_SYNC_HOT_ONLY and tier != "hot":
                    continue

                matched = False
                for pattern in patterns:
                    if fnmatch.fnmatch(name, pattern.strip()):
                        matched = True
                        break

                if matched:
                    to_sync.append({
                        "index": name,
                        "tier": tier,
                        "size_gb": idx_dict.get("size_gb", 0),
                        "doc_count": idx_dict.get("doc_count", 0),
                        "age_days": idx_dict.get("age_days", 0),
                    })

            return to_sync
        except Exception as e:
            logger.error("Failed to get leader indices to sync: %s", e)
            return []

    def auto_create_followers(self, dry_run: bool = True) -> dict:
        if not config.CCR_ENABLED:
            return {"success": False, "error": "CCR is not enabled"}

        try:
            self.register_remote_cluster()
        except Exception as e:
            return {"success": False, "error": f"Failed to register remote cluster: {str(e)}"}

        indices_to_sync = self.get_leader_indices_to_sync()
        existing_followers = {
            f.get("follower_index"): f for f in self.list_follower_indices()
        }

        results = []
        for idx in indices_to_sync:
            index_name = idx["index"]
            if index_name in existing_followers:
                results.append({
                    "index": index_name,
                    "status": "already_following",
                    "leader_index": existing_followers[index_name].get("leader_index"),
                })
                continue

            if dry_run:
                results.append({
                    "index": index_name,
                    "status": "would_create_follower",
                    "leader_index": index_name,
                })
                continue

            if len(results) >= config.CCR_MAX_CONCURRENT_FOLLOWERS:
                break

            result = self.create_follower_index(index_name)
            results.append(result)

        return {
            "dry_run": dry_run,
            "candidates_count": len(indices_to_sync),
            "existing_followers": len(existing_followers),
            "results": results,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def sync_hot_indices(self, dry_run: bool = True) -> dict:
        return self.auto_create_followers(dry_run=dry_run)

    def get_ccr_stats(self) -> dict:
        try:
            stats = self.es.client.ccr.stats()
            auto_follow_stats = stats.get("auto_follow_stats", {})
            follower_stats = stats.get("follower_indices", [])

            total_read_ops = 0
            total_write_ops = 0
            total_read_time_ms = 0
            total_write_time_ms = 0
            failed_followers = []

            for follower in follower_stats:
                shards = follower.get("shards", [])
                for shard in shards:
                    read_stats = shard.get("read_exceptions", [])
                    if read_stats:
                        failed_followers.append({
                            "index": follower.get("follower_index"),
                            "shard_id": shard.get("shard_id"),
                            "errors": read_stats,
                        })
                    total_read_ops += shard.get("operations_read", 0)
                    total_write_ops += shard.get("operations_written", 0)
                    total_read_time_ms += shard.get("read_time_millis", 0)
                    total_write_time_ms += shard.get("write_time_millis", 0)

            return {
                "auto_follow_stats": auto_follow_stats,
                "follower_count": len(follower_stats),
                "failed_followers": failed_followers,
                "total_operations_read": total_read_ops,
                "total_operations_written": total_write_ops,
                "total_read_time_ms": total_read_time_ms,
                "total_write_time_ms": total_write_time_ms,
                "avg_read_latency_ms": round(
                    total_read_time_ms / max(total_read_ops, 1), 2
                ),
                "avg_write_latency_ms": round(
                    total_write_time_ms / max(total_write_ops, 1), 2
                ),
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get CCR stats: %s", e)
            return {"error": str(e)}

    def forget_follower(self, leader_index: str, follower_index: str) -> dict:
        try:
            body = {
                "follower_cluster": config.CCR_REMOTE_CLUSTER_NAME,
                "follower_index": follower_index,
            }
            self.remote_client.ccr.forget_follower(
                index=leader_index,
                body=body,
            )
            logger.info("Forgot follower %s from leader %s", follower_index, leader_index)
            return {"success": True, "leader_index": leader_index, "follower_index": follower_index}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to forget follower: %s", e)
            return {"success": False, "error": str(e)}

    def promote_follower(self, follower_index: str) -> dict:
        try:
            self.pause_follow(follower_index)
            self.unfollow_index(follower_index)
            self.es.client.indices.put_settings(
                index=follower_index,
                body={"index.blocks.write": False},
            )
            logger.info("Promoted follower index %s to regular index", follower_index)
            return {"success": True, "follower_index": follower_index}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to promote follower %s: %s", follower_index, e)
            return {"success": False, "follower_index": follower_index, "error": str(e)}
