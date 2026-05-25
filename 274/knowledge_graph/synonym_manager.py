import os
import jieba
from typing import Dict, List, Set

from config import Config


class SynonymManager:
    def __init__(self, synonym_path: str = None):
        self.synonym_path = synonym_path or Config.SYNONYM_PATH
        self.synonym_dict: Dict[str, List[str]] = {}
        self.reverse_dict: Dict[str, str] = {}
        
        if os.path.exists(self.synonym_path):
            self._load_from_file()
        else:
            self._create_default_synonyms()

    def _load_from_file(self):
        with open(self.synonym_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) >= 2:
                    main_term = parts[0].strip()
                    synonyms = [s.strip() for s in parts[1].split(',')]
                    self.synonym_dict[main_term] = synonyms
                    
                    for syn in synonyms:
                        self.reverse_dict[syn] = main_term

    def _create_default_synonyms(self):
        default_synonyms = {
            '手机': ['移动电话', '智能手机', '智能机'],
            '笔记本电脑': ['笔记本', '手提电脑', '电脑本'],
            '耳机': ['耳麦', '耳塞'],
            '显示器': ['显示屏', '屏幕'],
            '电视': ['电视机', '彩电'],
            '鼠标': ['滑鼠'],
            '键盘': ['键盤'],
            '平板': ['平板电脑', 'Pad'],
            '手表': ['腕表'],
            '相机': ['照相机', '摄影机'],
            '苹果': ['Apple'],
            '华为': ['HUAWEI'],
            '小米': ['Xiaomi', 'MI'],
            '三星': ['Samsung'],
            '索尼': ['Sony'],
            '戴尔': ['Dell'],
            '联想': ['Lenovo'],
        }
        
        for main_term, synonyms in default_synonyms.items():
            self.synonym_dict[main_term] = synonyms
            for syn in synonyms:
                self.reverse_dict[syn] = main_term

    def get_synonyms(self, term: str) -> List[str]:
        if term in self.synonym_dict:
            return self.synonym_dict[term]
        
        if term in self.reverse_dict:
            main_term = self.reverse_dict[term]
            synonyms = self.synonym_dict.get(main_term, [])
            return [s for s in synonyms if s != term] + [main_term]
        
        return []

    def get_main_term(self, term: str) -> str:
        return self.reverse_dict.get(term, term)

    def normalize_term(self, term: str) -> str:
        return self.reverse_dict.get(term, term)

    def add_synonym(self, main_term: str, synonym: str):
        if main_term not in self.synonym_dict:
            self.synonym_dict[main_term] = []
        
        if synonym not in self.synonym_dict[main_term]:
            self.synonym_dict[main_term].append(synonym)
        
        self.reverse_dict[synonym] = main_term

    def remove_synonym(self, main_term: str, synonym: str):
        if main_term in self.synonym_dict and synonym in self.synonym_dict[main_term]:
            self.synonym_dict[main_term].remove(synonym)
        
        if synonym in self.reverse_dict:
            del self.reverse_dict[synonym]

    def expand_query(self, query: str) -> str:
        words = jieba.lcut(query)
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            synonyms = self.get_synonyms(word)
            expanded_words.extend(synonyms)
        
        return ' '.join(set(expanded_words))

    def expand_query_to_list(self, query: str) -> List[str]:
        words = jieba.lcut(query)
        expanded_terms = set()
        
        for word in words:
            expanded_terms.add(word)
            synonyms = self.get_synonyms(word)
            expanded_terms.update(synonyms)
        
        return list(expanded_terms)

    def normalize_query(self, query: str) -> str:
        words = jieba.lcut(query)
        normalized_words = [self.normalize_term(word) for word in words]
        return ''.join(normalized_words)

    def get_all_terms(self) -> Set[str]:
        all_terms = set(self.synonym_dict.keys())
        all_terms.update(self.reverse_dict.keys())
        return all_terms

    def save(self, save_path: str = None):
        save_path = save_path or self.synonym_path
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            for main_term, synonyms in self.synonym_dict.items():
                if synonyms:
                    f.write(f'{main_term}: {", ".join(synonyms)}\n')

    def get_stats(self) -> Dict:
        return {
            'main_terms_count': len(self.synonym_dict),
            'total_synonyms': len(self.reverse_dict),
            'all_terms_count': len(self.get_all_terms())
        }
