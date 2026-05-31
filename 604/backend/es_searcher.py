from typing import List, Dict, Any, Optional
import logging
from config import settings
from sample_data import get_sample_cases

logger = logging.getLogger(__name__)


class ElasticSearcher:
    def __init__(self):
        self._client = None
        self._use_mock = True
        self._sample_cases = get_sample_cases()
        self._init_es()
    
    def _init_es(self):
        try:
            from elasticsearch import Elasticsearch
            self._client = Elasticsearch(
                hosts=[{"host": settings.ELASTICSEARCH_HOST, "port": settings.ELASTICSEARCH_PORT}]
            )
            if self._client.ping():
                self._use_mock = False
                logger.info("Elasticsearch连接成功")
            else:
                logger.warning("Elasticsearch无法连接，使用模拟数据模式")
        except Exception as e:
            logger.warning(f"Elasticsearch初始化失败，使用模拟数据模式: {e}")
    
    def check_connection(self) -> bool:
        if self._use_mock:
            return False
        try:
            return self._client.ping()
        except:
            return False
    
    def create_index_if_not_exists(self):
        if self._use_mock:
            return
        
        if not self._client.indices.exists(index=settings.ELASTICSEARCH_INDEX):
            mappings = {
                "mappings": {
                    "properties": {
                        "case_id": {"type": "keyword"},
                        "case_title": {"type": "text", "analyzer": "ik_max_word"},
                        "case_type": {"type": "keyword"},
                        "description": {"type": "text", "analyzer": "ik_max_word"},
                        "summary": {"type": "text", "analyzer": "ik_max_word"},
                        "court": {"type": "keyword"},
                        "judgment_date": {"type": "date"},
                        "embedding": {"type": "dense_vector", "dims": 384},
                        "key_points": {"type": "keyword"},
                        "legal_entities": {"type": "object"},
                        "law_articles": {"type": "keyword"}
                    }
                }
            }
            self._client.indices.create(index=settings.ELASTICSEARCH_INDEX, body=mappings)
            logger.info(f"创建索引: {settings.ELASTICSEARCH_INDEX}")
    
    def search_similar_cases(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        case_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if self._use_mock:
            return self._mock_similar_search(query_embedding, top_k, case_type)
        
        try:
            script_query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            }
            
            if case_type:
                script_query["script_score"]["query"] = {
                    "term": {"case_type": case_type}
                }
            
            response = self._client.search(
                index=settings.ELASTICSEARCH_INDEX,
                query=script_query,
                size=top_k,
                _source=["case_id", "case_title", "case_type", "description", "summary", "key_points", "legal_entities", "court", "judgment_date"]
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                case = hit["_source"]
                case["similarity_score"] = hit["_score"] - 1.0
                results.append(case)
            
            return results
        
        except Exception as e:
            logger.error(f"Elasticsearch搜索失败: {e}")
            return self._mock_similar_search(query_embedding, top_k, case_type)
    
    def _mock_similar_search(
        self, 
        query_embedding: List[float], 
        top_k: int,
        case_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        import numpy as np
        
        cases = self._sample_cases
        if case_type:
            cases = [c for c in cases if c.get("case_type") == case_type]
        
        query_vec = np.array(query_embedding)
        
        for case in cases:
            if "embedding" in case:
                case_vec = np.array(case["embedding"])
                similarity = np.dot(query_vec, case_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(case_vec))
                case["similarity_score"] = float(similarity)
            else:
                case["similarity_score"] = 0.5
        
        cases.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        return cases[:top_k]
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        if self._use_mock:
            for case in self._sample_cases:
                if case.get("case_id") == case_id:
                    return case
            return None
        
        try:
            response = self._client.get(index=settings.ELASTICSEARCH_INDEX, id=case_id)
            if response["found"]:
                return response["_source"]
        except Exception as e:
            logger.error(f"获取案例失败: {e}")
        
        return None
    
    def index_case(self, case_data: Dict[str, Any]) -> bool:
        if self._use_mock:
            self._sample_cases.append(case_data)
            return True
        
        try:
            self._client.index(
                index=settings.ELASTICSEARCH_INDEX,
                id=case_data["case_id"],
                body=case_data
            )
            return True
        except Exception as e:
            logger.error(f"索引案例失败: {e}")
            return False
    
    def bulk_index_cases(self, cases: List[Dict[str, Any]]) -> bool:
        if self._use_mock:
            self._sample_cases.extend(cases)
            return True
        
        try:
            from elasticsearch import helpers
            actions = [
                {
                    "_index": settings.ELASTICSEARCH_INDEX,
                    "_id": case["case_id"],
                    "_source": case
                }
                for case in cases
            ]
            helpers.bulk(self._client, actions)
            return True
        except Exception as e:
            logger.error(f"批量索引失败: {e}")
            return False
