import logging
from datetime import datetime
from elasticsearch import exceptions as es_exceptions
from es_ilm_tool.es_client import ESClient
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class ILMPolicyManager:
    def __init__(self):
        self.es = ESClient()

    def create_policy(self, policy_name: str, policy_def: dict) -> bool:
        try:
            body = {"policy": policy_def}
            self.es.client.ilm.put_lifecycle(name=policy_name, body=body)
            logger.info("Created ILM policy: %s", policy_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to create ILM policy %s: %s", policy_name, e)
            return False

    def get_policy(self, policy_name: str) -> dict:
        try:
            result = self.es.client.ilm.get_lifecycle(name=policy_name)
            return result.get(policy_name, {})
        except es_exceptions.NotFoundError:
            logger.warning("ILM policy %s not found", policy_name)
            return {}
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get ILM policy %s: %s", policy_name, e)
            return {}

    def delete_policy(self, policy_name: str) -> bool:
        try:
            self.es.client.ilm.delete_lifecycle(name=policy_name)
            logger.info("Deleted ILM policy: %s", policy_name)
            return True
        except es_exceptions.NotFoundError:
            logger.warning("ILM policy %s not found for deletion", policy_name)
            return False
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to delete ILM policy %s: %s", policy_name, e)
            return False

    def list_policies(self) -> list:
        try:
            result = self.es.client.ilm.get_lifecycle()
            policies = []
            for name, data in result.items():
                policies.append({
                    "name": name,
                    "policy": data.get("policy", {}),
                    "modified_date": data.get("modified_date"),
                })
            return policies
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to list ILM policies: %s", e)
            return []

    def apply_policy_to_index(self, index_name: str, policy_name: str) -> bool:
        try:
            body = {
                "index.lifecycle.name": policy_name,
                "index.lifecycle.rollover_alias": index_name.split("-")[0],
            }
            self.es.client.indices.put_settings(index=index_name, body=body)
            logger.info("Applied ILM policy %s to index %s", policy_name, index_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to apply policy %s to %s: %s", policy_name, index_name, e)
            return False

    def remove_policy_from_index(self, index_name: str) -> bool:
        try:
            body = {
                "index.lifecycle.name": None,
            }
            self.es.client.indices.put_settings(index=index_name, body=body)
            logger.info("Removed ILM policy from index %s", index_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to remove policy from %s: %s", index_name, e)
            return False

    def get_index_ilm_status(self, index_name: str) -> dict:
        try:
            result = self.es.client.ilm.explain_lifecycle(index=index_name)
            indices = result.get("indices", {})
            return indices.get(index_name, {})
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get ILM status for %s: %s", index_name, e)
            return {}

    def retry_ilm(self, index_name: str) -> bool:
        try:
            self.es.client.ilm.retry(index=index_name)
            logger.info("Retried ILM for index %s", index_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to retry ILM for %s: %s", index_name, e)
            return False

    def build_default_policy(self) -> dict:
        return {
            "phases": {
                "hot": {
                    "min_age": "0ms",
                    "actions": {
                        "rollover": {
                            "max_size": f"{config.ROLLOVER_MAX_SIZE_GB}gb",
                            "max_docs": config.ROLLOVER_MAX_DOCS,
                            "max_age": f"{config.ROLLOVER_MAX_AGE_DAYS}d",
                        },
                        "set_priority": {"priority": 100},
                    },
                },
                "warm": {
                    "min_age": f"{config.MIGRATE_TO_WARM_AGE_DAYS}d",
                    "actions": {
                        "allocate": {
                            "require": {"data_tier": "warm"},
                        },
                        "shrink": {"number_of_shards": 1},
                        "forcemerge": {"max_num_segments": 1},
                        "set_priority": {"priority": 50},
                    },
                },
                "cold": {
                    "min_age": f"{config.MIGRATE_TO_COLD_AGE_DAYS}d",
                    "actions": {
                        "allocate": {
                            "require": {"data_tier": "cold"},
                        },
                        "freeze": {},
                        "set_priority": {"priority": 0},
                    },
                },
                "delete": {
                    "min_age": f"{config.DELETE_AGE_DAYS}d",
                    "actions": {
                        "delete": {"delete_searchable_snapshot": True},
                    },
                },
            },
        }

    def ensure_default_policy(self, policy_name: str = "default_ilm_policy") -> bool:
        existing = self.get_policy(policy_name)
        if existing:
            logger.info("Default ILM policy '%s' already exists", policy_name)
            return True
        policy_def = self.build_default_policy()
        return self.create_policy(policy_name, policy_def)
