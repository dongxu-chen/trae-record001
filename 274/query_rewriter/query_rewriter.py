import re
import jieba
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher

from config import Config
from knowledge_graph import SynonymManager, KnowledgeGraph


class QueryCorrector:
    def __init__(self, knowledge_graph: KnowledgeGraph, confidence_threshold: float = None):
        self.kg = knowledge_graph
        self.confidence_threshold = confidence_threshold or Config.REWRITE_CONFIDENCE_THRESHOLD
        self.corpus_words = self._build_corpus()
        self.char_frequency = self._build_char_frequency()

    def _build_corpus(self) -> Set[str]:
        corpus = set()
        
        for entity in self.kg.entity_index.values():
            corpus.add(entity['name'])
            for alias in entity.get('alias', []):
                corpus.add(alias)
        
        common_terms = [
            '手机', '电脑', '笔记本', '耳机', '显示器', '电视', '鼠标', '键盘',
            '平板', '手表', '相机', '买', '推荐', '哪个', '什么', '怎么', '怎么样',
            '好', '性价比', '高', '便宜', '贵', '对比', '区别', '苹果', '华为', '小米',
            '三星', '索尼', '戴尔', '联想', '惠普', '华硕', '罗技', '寸', 'G', 'GB',
            'K', 'Pro', 'Max', 'Ultra'
        ]
        
        for term in common_terms:
            corpus.add(term)
        
        return corpus

    def _build_char_frequency(self) -> Dict[str, int]:
        frequency = {}
        for word in self.corpus_words:
            for char in word:
                frequency[char] = frequency.get(char, 0) + 1
        return frequency

    def _edit_distance(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def _find_similar_word(self, word: str) -> Tuple[str, float]:
        if word in self.corpus_words:
            return word, 1.0
        
        normalized_word = self.kg.normalize_term(word)
        if normalized_word != word and normalized_word in self.corpus_words:
            return normalized_word, 0.95
        
        best_match = word
        best_score = 0.0
        
        for corpus_word in self.corpus_words:
            if abs(len(word) - len(corpus_word)) > 2:
                continue
            
            similarity = SequenceMatcher(None, word, corpus_word).ratio()
            
            if similarity > best_score:
                best_score = similarity
                best_match = corpus_word
        
        if best_score >= self.confidence_threshold:
            return best_match, best_score
        else:
            return word, best_score

    def correct(self, query: str) -> Tuple[str, List[Dict]]:
        words = jieba.lcut(query)
        corrected_words = []
        corrections = []
        
        for word in words:
            corrected, confidence = self._find_similar_word(word)
            corrected_words.append(corrected)
            
            if corrected != word:
                corrections.append({
                    'original': word,
                    'corrected': corrected,
                    'confidence': round(confidence, 4),
                    'applied': confidence >= self.confidence_threshold
                })
        
        corrected_query = ''.join(corrected_words)
        
        return corrected_query, corrections


class QueryExpander:
    def __init__(self, synonym_manager: SynonymManager, knowledge_graph: KnowledgeGraph, 
                 confidence_threshold: float = None):
        self.synonym_manager = synonym_manager
        self.kg = knowledge_graph
        self.confidence_threshold = confidence_threshold or Config.REWRITE_CONFIDENCE_THRESHOLD

    def expand(self, query: str) -> Dict:
        words = jieba.lcut(query)
        expanded_terms: Set[str] = set()
        synonym_map: Dict[str, List[str]] = {}
        kg_expansions: Dict[str, List[str]] = {}
        
        for word in words:
            normalized_word = self.kg.normalize_term(word)
            base_word = normalized_word if normalized_word != word else word
            expanded_terms.add(base_word)
            
            synonyms = self.synonym_manager.get_synonyms(base_word)
            if synonyms:
                synonym_map[base_word] = synonyms
                expanded_terms.update(synonyms)
            
            kg_terms = self.kg.expand_query_terms([base_word])
            if len(kg_terms) > 1:
                kg_expansions[base_word] = list(kg_terms - {base_word})
                expanded_terms.update(kg_terms)
        
        return {
            'original_query': query,
            'expanded_terms': list(expanded_terms),
            'synonym_expansions': synonym_map,
            'knowledge_graph_expansions': kg_expansions
        }


class QueryRewriter:
    def __init__(self, synonym_manager: SynonymManager = None, knowledge_graph: KnowledgeGraph = None,
                 confidence_threshold: float = None):
        self.synonym_manager = synonym_manager or SynonymManager()
        self.kg = knowledge_graph or KnowledgeGraph()
        self.confidence_threshold = confidence_threshold or Config.REWRITE_CONFIDENCE_THRESHOLD
        self.corrector = QueryCorrector(self.kg, self.confidence_threshold)
        self.expander = QueryExpander(self.synonym_manager, self.kg, self.confidence_threshold)

    def rewrite(self, query: str) -> Dict:
        cleaned_query = self._clean_query(query)
        
        corrected_query, corrections = self.corrector.correct(cleaned_query)
        
        expansion_result = self.expander.expand(corrected_query)
        
        normalized_query = self.synonym_manager.normalize_query(corrected_query)
        
        query_variations = self._generate_query_variations(
            corrected_query, 
            expansion_result['expanded_terms']
        )
        
        low_confidence_words = [c for c in corrections if not c.get('applied', True)]
        
        return {
            'original_query': query,
            'cleaned_query': cleaned_query,
            'corrected_query': corrected_query,
            'normalized_query': normalized_query,
            'corrections': corrections,
            'expanded_terms': expansion_result['expanded_terms'],
            'synonym_expansions': expansion_result['synonym_expansions'],
            'knowledge_graph_expansions': expansion_result['knowledge_graph_expansions'],
            'query_variations': query_variations,
            'recall_boost_terms': self._get_recall_boost_terms(expansion_result),
            'confidence_threshold': self.confidence_threshold,
            'low_confidence_words': low_confidence_words,
            'preserved_original_words': [c['original'] for c in low_confidence_words]
        }

    def _clean_query(self, query: str) -> str:
        query = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        query = re.sub(r'\s+', ' ', query)
        return query.strip()

    def _generate_query_variations(self, query: str, expanded_terms: List[str]) -> List[str]:
        variations = [query]
        
        words = jieba.lcut(query)
        if len(words) > 1:
            variations.append(' '.join(words))
            variations.append(''.join(reversed(words)))
        
        if expanded_terms:
            variations.append(' '.join(expanded_terms))
        
        return list(set(variations))

    def _get_recall_boost_terms(self, expansion_result: Dict) -> List[str]:
        boost_terms = set()
        
        for word, synonyms in expansion_result['synonym_expansions'].items():
            boost_terms.update(synonyms)
        
        for word, kg_terms in expansion_result['knowledge_graph_expansions'].items():
            boost_terms.update(kg_terms)
        
        return list(boost_terms)

    def rewrite_for_search(self, query: str) -> Dict:
        rewrite_result = self.rewrite(query)
        
        primary_query = rewrite_result['corrected_query']
        boost_queries = [
            rewrite_result['normalized_query'],
            ' '.join(rewrite_result['expanded_terms'])
        ]
        
        return {
            'primary_query': primary_query,
            'boost_queries': boost_queries,
            'filter_terms': self._extract_filter_terms(rewrite_result),
            'rewrite_details': rewrite_result
        }

    def _extract_filter_terms(self, rewrite_result: Dict) -> Dict[str, List[str]]:
        all_terms = rewrite_result['expanded_terms']
        filters = {
            'brands': [],
            'categories': [],
            'specs': []
        }
        
        for term in all_terms:
            entity = self.kg.get_entity_by_name(term)
            if entity:
                entity_type = entity.get('type')
                if entity_type == '品牌':
                    filters['brands'].append(entity['name'])
                elif entity_type == '品类':
                    filters['categories'].append(entity['name'])
                elif entity_type == '规格':
                    filters['specs'].append(entity['name'])
        
        return filters

    def get_rewrite_stats(self) -> Dict:
        return {
            'synonym_manager_stats': self.synonym_manager.get_stats(),
            'knowledge_graph_stats': self.kg.get_graph_stats(),
            'corrector_corpus_size': len(self.corrector.corpus_words),
            'confidence_threshold': self.confidence_threshold
        }
