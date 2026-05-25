import os
import json
from typing import Dict, List, Optional

from config import Config
from bert_module import IntentClassifier, AttributeExtractor
from knowledge_graph import KnowledgeGraph, SynonymManager
from es_search import ProductSearch
from query_rewriter import QueryRewriter


class EcommerceSearchService:
    def __init__(self, use_pretrained: bool = False):
        Config.ensure_dirs()
        
        self.kg = KnowledgeGraph()
        self.synonym_manager = SynonymManager()
        self.query_rewriter = QueryRewriter(self.synonym_manager, self.kg)
        self.product_search = ProductSearch()
        
        self.intent_classifier = None
        self.attribute_extractor = None
        
        if use_pretrained:
            self._load_models()
        
        self._index_sample_data()

    def _load_models(self):
        intent_model_path = Config.INTENT_MODEL_PATH
        attr_model_path = Config.ATTR_MODEL_PATH
        
        if os.path.exists(intent_model_path):
            print(f'Loading intent classifier from {intent_model_path}...')
            self.intent_classifier = IntentClassifier(intent_model_path)
        else:
            print('Intent classifier model not found, using rule-based fallback...')
        
        if os.path.exists(attr_model_path):
            print(f'Loading attribute extractor from {attr_model_path}...')
            self.attribute_extractor = AttributeExtractor(attr_model_path)
        else:
            print('Attribute extractor model not found, using rule-based fallback...')

    def _index_sample_data(self):
        products_path = os.path.join(Config.DATA_DIR, 'products.json')
        if os.path.exists(products_path):
            with open(products_path, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            existing = self.product_search.get_all_products()
            if len(existing) == 0:
                print('Indexing sample product data...')
                self.product_search.bulk_index_products(products)
                print(f'Indexed {len(products)} products')

    def analyze_intent(self, query: str) -> Dict:
        if self.intent_classifier:
            return self.intent_classifier.predict(query)
        else:
            return self._rule_based_intent(query)

    def _rule_based_intent(self, query: str) -> Dict:
        purchase_keywords = ['买', '购买', '入手', '推荐', '哪款', '哪个', '怎么样', '如何选择']
        compare_keywords = ['对比', '比较', '哪个好', '区别', 'vs', 'VS']
        knowledge_keywords = ['什么是', '怎么', '如何', '为什么', '原理', '意思', '区别']
        
        query_lower = query.lower()
        
        intent_scores = {
            '购买意向': 0.3,
            '比价': 0.3,
            '知识查询': 0.3
        }
        
        for kw in purchase_keywords:
            if kw in query:
                intent_scores['购买意向'] += 0.2
        
        for kw in compare_keywords:
            if kw in query:
                intent_scores['比价'] += 0.3
        
        for kw in knowledge_keywords:
            if kw in query:
                intent_scores['知识查询'] += 0.25
        
        total = sum(intent_scores.values())
        normalized = {k: v / total for k, v in intent_scores.items()}
        
        intent = max(normalized, key=normalized.get)
        confidence = normalized[intent]
        
        return {
            'intent': intent,
            'confidence': confidence,
            'probabilities': normalized
        }

    def extract_attributes(self, query: str) -> Dict:
        if self.attribute_extractor:
            result = self.attribute_extractor.extract(query)
        else:
            result = self._rule_based_attribute_extraction(query)
        
        kg_brands = []
        kg_categories = []
        kg_specs = []
        
        for brand in result.get('brands', []):
            entity = self.kg.get_entity_by_name(brand)
            if entity:
                kg_brands.append(entity['name'])
        
        for category in result.get('categories', []):
            entity = self.kg.get_entity_by_name(category)
            if entity:
                kg_categories.append(entity['name'])
        
        for spec in result.get('specs', []):
            entity = self.kg.get_entity_by_name(spec)
            if entity:
                kg_specs.append(entity['name'])
        
        return {
            'brands': list(set(result.get('brands', []) + kg_brands)),
            'categories': list(set(result.get('categories', []) + kg_categories)),
            'specs': list(set(result.get('specs', []) + kg_specs))
        }

    def _rule_based_attribute_extraction(self, query: str) -> Dict:
        brands = []
        categories = []
        specs = []
        
        all_brands = self.kg.get_all_brands()
        all_categories = self.kg.get_all_categories()
        all_specs = self.kg.get_all_specs()
        
        for brand in all_brands:
            brand_name = brand['name']
            if brand_name in query or any(alias in query for alias in brand.get('alias', [])):
                brands.append(brand_name)
        
        for category in all_categories:
            cat_name = category['name']
            if cat_name in query or any(alias in query for alias in category.get('alias', [])):
                categories.append(cat_name)
        
        for spec in all_specs:
            spec_name = spec['name']
            if spec_name in query or any(alias in query for alias in spec.get('alias', [])):
                specs.append(spec_name)
        
        return {
            'brands': brands,
            'categories': categories,
            'specs': specs
        }

    def rewrite_query(self, query: str) -> Dict:
        return self.query_rewriter.rewrite_for_search(query)

    def search(self, query: str, top_n: int = 10) -> Dict:
        intent_result = self.analyze_intent(query)
        attribute_result = self.extract_attributes(query)
        rewrite_result = self.rewrite_query(query)
        
        primary_query = rewrite_result['primary_query']
        filter_terms = rewrite_result['filter_terms']
        
        brands = list(set(attribute_result['brands'] + filter_terms.get('brands', [])))
        categories = list(set(attribute_result['categories'] + filter_terms.get('categories', [])))
        specs = list(set(attribute_result['specs'] + filter_terms.get('specs', [])))
        
        expanded_terms = rewrite_result['rewrite_details']['expanded_terms']
        
        search_result = self.product_search.semantic_search(
            query=primary_query,
            expanded_terms=expanded_terms,
            brands=brands if brands else None,
            categories=categories if categories else None,
            specs=specs if specs else None,
            top_n=top_n
        )
        
        intent_response = self._generate_intent_response(
            intent_result['intent'],
            query,
            search_result['results']
        )
        
        return {
            'original_query': query,
            'intent_analysis': intent_result,
            'attribute_extraction': attribute_result,
            'query_rewrite': rewrite_result,
            'search_results': {
                'total': search_result['total'],
                'products': search_result['results']
            },
            'recommendation': intent_response,
            'recall_improvement': self._calculate_recall_improvement(
                query,
                primary_query,
                expanded_terms
            )
        }

    def _generate_intent_response(self, intent: str, query: str, products: List[Dict]) -> Dict:
        if intent == '购买意向':
            return {
                'type': 'purchase_recommendation',
                'message': f'根据您的搜索"{query}"，为您推荐以下商品：',
                'action': 'view_products'
            }
        elif intent == '比价':
            return {
                'type': 'comparison_suggestion',
                'message': f'您似乎在进行商品对比，以下是相关商品供您参考：',
                'action': 'compare_products'
            }
        elif intent == '知识查询':
            return {
                'type': 'knowledge_assistance',
                'message': f'关于"{query}"，除了搜索结果外，您还可以查看商品详情了解更多规格参数：',
                'action': 'explore_knowledge'
            }
        else:
            return {
                'type': 'general_search',
                'message': '为您找到以下相关商品：',
                'action': 'browse_products'
            }

    def _calculate_recall_improvement(self, original_query: str, 
                                       corrected_query: str, 
                                       expanded_terms: List[str]) -> Dict:
        original_terms = set(jieba.lcut(original_query))
        corrected_terms = set(jieba.lcut(corrected_query))
        expanded_terms_set = set(expanded_terms)
        
        term_expansion_rate = len(expanded_terms_set) / max(len(original_terms), 1)
        
        return {
            'original_term_count': len(original_terms),
            'expanded_term_count': len(expanded_terms_set),
            'term_expansion_rate': round(term_expansion_rate, 2),
            'new_terms_added': list(expanded_terms_set - original_terms)
        }

    def get_stats(self) -> Dict:
        return {
            'knowledge_graph': self.kg.get_graph_stats(),
            'synonym_manager': self.synonym_manager.get_stats(),
            'product_search': self.product_search.get_stats(),
            'query_rewriter': self.query_rewriter.get_rewrite_stats(),
            'models_loaded': {
                'intent_classifier': self.intent_classifier is not None,
                'attribute_extractor': self.attribute_extractor is not None
            }
        }


import jieba
