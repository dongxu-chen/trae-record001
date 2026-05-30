import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from config.config import ES_HOST, ES_INDEX


PRODUCT_MAPPING = {
    "mappings": {
        "properties": {
            "product_id": {"type": "keyword"},
            "title": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_smart"},
            "category": {"type": "keyword"},
            "brand": {"type": "keyword"},
            "price": {"type": "float"},
            "sales_volume": {"type": "integer"},
            "click_rate": {"type": "float"},
            "cart_rate": {"type": "float"},
            "conversion_rate": {"type": "float"},
            "ctr_7d": {"type": "float"},
            "ctr_30d": {"type": "float"},
            "return_rate": {"type": "float"},
            "review_score": {"type": "float"},
        }
    }
}


class ElasticsearchClient:
    def __init__(self, host=None, index=None):
        self.host = host or ES_HOST
        self.index = index or ES_INDEX
        self.es = Elasticsearch(self.host)

    def create_index(self, mapping=None):
        if self.es.indices.exists(index=self.index):
            self.es.indices.delete(index=self.index)
        body = mapping or PRODUCT_MAPPING
        self.es.indices.create(index=self.index, body=body)
        return True

    def index_product(self, product):
        doc = {
            "product_id": product.get("product_id", ""),
            "title": product.get("title", ""),
            "category": product.get("category", ""),
            "brand": product.get("brand", ""),
            "price": product.get("price", 0.0),
            "sales_volume": product.get("sales_volume", 0),
            "click_rate": product.get("click_rate", 0.0),
            "cart_rate": product.get("cart_rate", 0.0),
            "conversion_rate": product.get("conversion_rate", 0.0),
            "ctr_7d": product.get("ctr_7d", 0.0),
            "ctr_30d": product.get("ctr_30d", 0.0),
            "return_rate": product.get("return_rate", 0.0),
            "review_score": product.get("review_score", 0.0),
        }
        self.es.index(index=self.index, id=product.get("product_id"), document=doc)
        return True

    def bulk_index_products(self, products):
        from elasticsearch.helpers import bulk

        actions = []
        for p in products:
            action = {
                "_index": self.index,
                "_id": p.get("product_id"),
                "_source": {
                    "product_id": p.get("product_id", ""),
                    "title": p.get("title", ""),
                    "category": p.get("category", ""),
                    "brand": p.get("brand", ""),
                    "price": p.get("price", 0.0),
                    "sales_volume": p.get("sales_volume", 0),
                    "click_rate": p.get("click_rate", 0.0),
                    "cart_rate": p.get("cart_rate", 0.0),
                    "conversion_rate": p.get("conversion_rate", 0.0),
                    "ctr_7d": p.get("ctr_7d", 0.0),
                    "ctr_30d": p.get("ctr_30d", 0.0),
                    "return_rate": p.get("return_rate", 0.0),
                    "review_score": p.get("review_score", 0.0),
                },
            }
            actions.append(action)
        success, failed = bulk(self.es, actions)
        return success, failed

    def search(self, query, size=100):
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "category^1.5", "brand^2"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
            "size": size,
        }
        result = self.es.search(index=self.index, body=body)
        hits = result["hits"]["hits"]
        products = []
        for hit in hits:
            source = hit["_source"]
            source["_score"] = hit["_score"]
            products.append(source)
        return products

    def search_with_bm25(self, query, size=100):
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "category^1.5", "brand^2"],
                    "type": "best_fields",
                }
            },
            "size": size,
            "explain": False,
        }
        result = self.es.search(index=self.index, body=body)
        hits = result["hits"]["hits"]
        products = []
        for hit in hits:
            source = hit["_source"]
            source["es_bm25_score"] = hit["_score"]
            products.append(source)
        return products

    def get_product(self, product_id):
        try:
            result = self.es.get(index=self.index, id=product_id)
            return result["_source"]
        except Exception:
            return None

    def delete_index(self):
        if self.es.indices.exists(index=self.index):
            self.es.indices.delete(index=self.index)
            return True
        return False
