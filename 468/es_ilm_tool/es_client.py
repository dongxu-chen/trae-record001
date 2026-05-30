import logging
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from es_ilm_tool import config

logger = logging.getLogger(__name__)


class ESClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self) -> Elasticsearch:
        if self._client is None or not self._client.ping():
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Elasticsearch:
        try:
            client = Elasticsearch(
                hosts=config.ES_HOSTS,
                basic_auth=(config.ES_USERNAME, config.ES_PASSWORD),
                request_timeout=config.ES_TIMEOUT,
                verify_certs=False,
                ssl_show_warn=False,
            )
            info = client.info()
            logger.info("Connected to Elasticsearch %s", info["version"]["number"])
            return client
        except es_exceptions.ConnectionError as e:
            logger.error("Failed to connect to Elasticsearch: %s", e)
            raise

    def get_index_stats(self, index_name: str, level: str = "shards") -> dict:
        try:
            stats = self.client.indices.stats(index=index_name, level=level)
            return stats.get("indices", {}).get(index_name, {})
        except es_exceptions.NotFoundError:
            logger.warning("Index %s not found", index_name)
            return {}

    def get_all_indices(self, pattern: str = "*") -> list:
        try:
            result = self.client.cat.indices(index=pattern, format="json")
            return result
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get indices: %s", e)
            return []

    def get_index_settings(self, index_name: str) -> dict:
        try:
            settings = self.client.indices.get_settings(index=index_name)
            return settings.get(index_name, {}).get("settings", {})
        except es_exceptions.NotFoundError:
            return {}

    def get_index_mapping(self, index_name: str) -> dict:
        try:
            mapping = self.client.indices.get_mapping(index=index_name)
            return mapping.get(index_name, {}).get("mappings", {})
        except es_exceptions.NotFoundError:
            return {}

    def get_cluster_health(self) -> dict:
        try:
            return self.client.cluster.health()
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get cluster health: %s", e)
            return {}

    def get_node_stats(self) -> dict:
        try:
            return self.client.nodes.stats()
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to get node stats: %s", e)
            return {}

    def update_index_settings(self, index_name: str, settings: dict) -> bool:
        try:
            self.client.indices.put_settings(index=index_name, body=settings)
            logger.info("Updated settings for index %s", index_name)
            return True
        except es_exceptions.ElasticsearchException as e:
            logger.error("Failed to update settings for %s: %s", index_name, e)
            return False

    def get_alias(self, alias_name: str) -> dict:
        try:
            return self.client.indices.get_alias(name=alias_name)
        except es_exceptions.NotFoundError:
            return {}

    def health_check(self) -> dict:
        try:
            info = self.client.info()
            health = self.get_cluster_health()
            return {
                "status": "healthy",
                "cluster_name": health.get("cluster_name", "unknown"),
                "es_version": info.get("version", {}).get("number", "unknown"),
                "status_code": health.get("status", "unknown"),
                "number_of_nodes": health.get("number_of_nodes", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
