from elasticsearch import Elasticsearch
from config import settings
import logging

logger = logging.getLogger(__name__)


def get_es_client() -> Elasticsearch:
    try:
        es = Elasticsearch(
            settings.elasticsearch_host,
            basic_auth=(settings.elasticsearch_user, settings.elasticsearch_password),
            verify_certs=False,
            timeout=30,
        )
        if not es.ping():
            logger.warning("Elasticsearch connection failed, check your configuration")
        return es
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        raise


def create_indices(es: Elasticsearch):
    indices = {
        settings.documents_index: {
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                }
            }
        },
        settings.queries_index: {
            "mappings": {
                "properties": {
                    "query_id": {"type": "keyword"},
                    "query_text": {"type": "text"},
                    "description": {"type": "text"},
                    "query_type": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            }
        },
        settings.annotations_index: {
            "mappings": {
                "properties": {
                    "query_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "relevance": {"type": "integer"},
                    "annotator": {"type": "keyword"},
                    "request_id": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        },
        settings.evaluations_index: {
            "mappings": {
                "properties": {
                    "evaluation_id": {"type": "keyword"},
                    "model_name": {"type": "keyword"},
                    "query_id": {"type": "keyword"},
                    "request_id": {"type": "keyword"},
                    "query_type": {"type": "keyword"},
                    "k": {"type": "integer"},
                    "results": {
                        "type": "nested",
                        "properties": {
                            "doc_id": {"type": "keyword"},
                            "score": {"type": "float"},
                            "rank": {"type": "integer"},
                            "relevant": {"type": "boolean"},
                        },
                    },
                    "metrics": {"type": "object"},
                    "created_at": {"type": "date"},
                }
            }
        },
        settings.models_index: {
            "mappings": {
                "properties": {
                    "model_name": {"type": "keyword"},
                    "description": {"type": "text"},
                    "endpoint": {"type": "keyword"},
                    "is_active": {"type": "boolean"},
                    "created_at": {"type": "date"},
                }
            }
        },
        settings.click_events_index: {
            "mappings": {
                "properties": {
                    "request_id": {"type": "keyword"},
                    "query_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "rank": {"type": "integer"},
                    "click_position": {"type": "integer"},
                    "dwell_time": {"type": "float"},
                    "click_type": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            }
        },
        settings.ab_tests_index: {
            "mappings": {
                "properties": {
                    "test_id": {"type": "keyword"},
                    "test_name": {"type": "keyword"},
                    "control_model": {"type": "keyword"},
                    "treatment_model": {"type": "keyword"},
                    "traffic_split": {"type": "float"},
                    "status": {"type": "keyword"},
                    "start_date": {"type": "date"},
                    "end_date": {"type": "date"},
                    "description": {"type": "text"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        },
        settings.ab_assignments_index: {
            "mappings": {
                "properties": {
                    "test_id": {"type": "keyword"},
                    "session_id": {"type": "keyword"},
                    "group": {"type": "keyword"},
                    "model_name": {"type": "keyword"},
                    "assigned_at": {"type": "date"},
                }
            }
        },
        settings.feedback_data_index: {
            "mappings": {
                "properties": {
                    "query_id": {"type": "keyword"},
                    "query_text": {"type": "text"},
                    "doc_id": {"type": "keyword"},
                    "doc_title": {"type": "text"},
                    "relevance": {"type": "integer"},
                    "source": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "model_name": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            }
        },
    }

    for index_name, mapping in indices.items():
        if not es.indices.exists(index=index_name):
            es.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index: {index_name}")
        else:
            logger.info(f"Index already exists: {index_name}")
