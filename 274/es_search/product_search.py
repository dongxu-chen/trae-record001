import json
import os
from typing import List, Dict, Optional, Any
from elasticsearch import Elasticsearch, helpers

from config import Config


class ProductSearch:
    def __init__(self, es_host: str = None, es_port: int = None, index_name: str = None):
        self.es_host = es_host or Config.ES_HOST
        self.es_port = es_port or Config.ES_PORT
        self.index_name = index_name or Config.ES_INDEX
        
        self.es = Elasticsearch([f'http://{self.es_host}:{self.es_port}'])
        
        if not self.es.ping():
            print(f'Warning: Could not connect to Elasticsearch at {self.es_host}:{self.es_port}')
            print('Using fallback search mode...')
            self.use_fallback = True
            self.fallback_data = self._load_fallback_data()
        else:
            self.use_fallback = False
            self._create_index_if_not_exists()

    def _load_fallback_data(self) -> List[Dict]:
        products_path = os.path.join(Config.DATA_DIR, 'products.json')
        if os.path.exists(products_path):
            with open(products_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _create_index_if_not_exists(self):
        if not self.es.indices.exists(index=self.index_name):
            mappings = {
                'mappings': {
                    'properties': {
                        'id': {'type': 'keyword'},
                        'name': {
                            'type': 'text',
                            'analyzer': 'ik_max_word',
                            'search_analyzer': 'ik_smart',
                            'fields': {
                                'keyword': {'type': 'keyword', 'ignore_above': 256}
                            }
                        },
                        'brand': {'type': 'keyword'},
                        'category': {'type': 'keyword'},
                        'spec': {
                            'type': 'text',
                            'analyzer': 'ik_max_word',
                            'search_analyzer': 'ik_smart'
                        },
                        'price': {'type': 'double'},
                        'description': {
                            'type': 'text',
                            'analyzer': 'ik_max_word',
                            'search_analyzer': 'ik_smart'
                        }
                    }
                },
                'settings': {
                    'number_of_shards': 1,
                    'number_of_replicas': 0,
                    'analysis': {
                        'analyzer': {
                            'ik_max_word': {
                                'type': 'custom',
                                'tokenizer': 'ik_max_word'
                            },
                            'ik_smart': {
                                'type': 'custom',
                                'tokenizer': 'ik_smart'
                            }
                        }
                    }
                }
            }
            
            self.es.indices.create(index=self.index_name, body=mappings)
            print(f'Index {self.index_name} created successfully')

    def index_product(self, product: Dict[str, Any]) -> bool:
        if self.use_fallback:
            self.fallback_data.append(product)
            return True
        
        try:
            self.es.index(
                index=self.index_name,
                id=product['id'],
                body=product
            )
            return True
        except Exception as e:
            print(f'Error indexing product: {e}')
            return False

    def bulk_index_products(self, products: List[Dict[str, Any]]) -> int:
        if self.use_fallback:
            self.fallback_data.extend(products)
            return len(products)
        
        actions = [
            {
                '_index': self.index_name,
                '_id': product['id'],
                '_source': product
            }
            for product in products
        ]
        
        try:
            success, _ = helpers.bulk(self.es, actions)
            return success
        except Exception as e:
            print(f'Error bulk indexing products: {e}')
            return 0

    def delete_index(self) -> bool:
        if self.use_fallback:
            self.fallback_data = []
            return True
        
        try:
            if self.es.indices.exists(index=self.index_name):
                self.es.indices.delete(index=self.index_name)
                return True
            return False
        except Exception as e:
            print(f'Error deleting index: {e}')
            return False

    def _fallback_search(self, query: str, brands: List[str] = None, 
                        categories: List[str] = None, specs: List[str] = None,
                        min_price: float = None, max_price: float = None,
                        top_n: int = 10) -> List[Dict]:
        results = []
        query_terms = query.lower().split()
        
        for product in self.fallback_data:
            score = 0
            text = f"{product['name']} {product['description']} {product['spec']}".lower()
            
            for term in query_terms:
                if term in text:
                    score += 2
                if term in product['name'].lower():
                    score += 3
            
            if brands and product['brand'] in brands:
                score += 5
            
            if categories and product['category'] in categories:
                score += 5
            
            if specs:
                for spec in specs:
                    if spec.lower() in product['spec'].lower():
                        score += 3
            
            if min_price is not None and product['price'] < min_price:
                continue
            if max_price is not None and product['price'] > max_price:
                continue
            
            if score > 0:
                results.append({
                    **product,
                    '_score': score
                })
        
        results.sort(key=lambda x: x['_score'], reverse=True)
        return results[:top_n]

    def search(self, query: str, brands: List[str] = None, 
               categories: List[str] = None, specs: List[str] = None,
               min_price: float = None, max_price: float = None,
               top_n: int = 10) -> List[Dict]:
        if self.use_fallback:
            return self._fallback_search(query, brands, categories, specs, 
                                        min_price, max_price, top_n)
        
        must_clauses = []
        filter_clauses = []
        
        if query:
            must_clauses.append({
                'multi_match': {
                    'query': query,
                    'fields': ['name^3', 'description', 'spec'],
                    'type': 'most_fields',
                    'operator': 'or'
                }
            })
        
        if brands:
            filter_clauses.append({
                'terms': {'brand': brands}
            })
        
        if categories:
            filter_clauses.append({
                'terms': {'category': categories}
            })
        
        if specs:
            must_clauses.append({
                'match': {'spec': ' '.join(specs)}
            })
        
        price_range = {}
        if min_price is not None:
            price_range['gte'] = min_price
        if max_price is not None:
            price_range['lte'] = max_price
        if price_range:
            filter_clauses.append({
                'range': {'price': price_range}
            })
        
        es_query = {
            'query': {
                'bool': {
                    'must': must_clauses if must_clauses else [{'match_all': {}}],
                    'filter': filter_clauses
                }
            },
            'size': top_n,
            'sort': [{'_score': {'order': 'desc'}}]
        }
        
        try:
            response = self.es.search(index=self.index_name, body=es_query)
            results = []
            for hit in response['hits']['hits']:
                product = hit['_source']
                product['_score'] = hit['_score']
                results.append(product)
            return results
        except Exception as e:
            print(f'Error searching: {e}')
            return []

    def semantic_search(self, query: str, expanded_terms: List[str] = None,
                       brands: List[str] = None, categories: List[str] = None,
                       specs: List[str] = None, min_price: float = None,
                       max_price: float = None, top_n: int = 10) -> Dict:
        search_queries = [query]
        if expanded_terms:
            search_queries.extend(expanded_terms)
        
        combined_query = ' '.join(search_queries)
        
        results = self.search(
            query=combined_query,
            brands=brands,
            categories=categories,
            specs=specs,
            min_price=min_price,
            max_price=max_price,
            top_n=top_n
        )
        
        return {
            'original_query': query,
            'expanded_terms': expanded_terms or [],
            'total': len(results),
            'results': results
        }

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        if self.use_fallback:
            for product in self.fallback_data:
                if product['id'] == product_id:
                    return product
            return None
        
        try:
            response = self.es.get(index=self.index_name, id=product_id)
            return response['_source']
        except Exception as e:
            print(f'Error getting product: {e}')
            return None

    def get_all_products(self) -> List[Dict]:
        if self.use_fallback:
            return self.fallback_data
        
        try:
            response = self.es.search(
                index=self.index_name,
                body={'query': {'match_all': {}}},
                size=1000
            )
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception as e:
            print(f'Error getting all products: {e}')
            return []

    def get_stats(self) -> Dict:
        if self.use_fallback:
            return {
                'total_products': len(self.fallback_data),
                'mode': 'fallback'
            }
        
        try:
            count = self.es.count(index=self.index_name)
            return {
                'total_products': count['count'],
                'mode': 'elasticsearch',
                'index_name': self.index_name
            }
        except Exception as e:
            print(f'Error getting stats: {e}')
            return {'error': str(e)}
