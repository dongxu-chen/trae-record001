import jieba
import math
from fuzzywuzzy import process
from typing import List, Dict, Tuple
from kg.neo4j_client import Neo4jClient
from kg.schema import ENTITY_TYPES, ENTITY_SYNONYMS


class DynamicThreshold:
    def __init__(
        self,
        short_min: int = 45,
        medium_base: int = 60,
        long_max: int = 85,
        short_boundary: int = 2,
        long_boundary: int = 5,
    ):
        self.short_min = short_min
        self.medium_base = medium_base
        self.long_max = long_max
        self.short_boundary = short_boundary
        self.long_boundary = long_boundary

    def compute(self, word: str) -> int:
        word_len = len(word)

        if word_len <= self.short_boundary:
            return self.short_min

        if word_len >= self.long_boundary:
            return self.long_max

        t = (word_len - self.short_boundary) / (self.long_boundary - self.short_boundary)
        threshold = self.short_min + t * (self.long_max - self.medium_base)
        threshold = threshold + (1 - t) * (self.medium_base - self.short_min) * 0.5

        return int(round(threshold))

    def compute_batch(self, words: List[str]) -> Dict[str, int]:
        return {word: self.compute(word) for word in words}


class EntityExtractor:
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client
        self.entity_vocab = self._build_entity_vocab()
        self._init_jieba()
        self.dynamic_threshold = DynamicThreshold()

    def _build_entity_vocab(self) -> Dict[str, str]:
        vocab = {}
        try:
            for entity_type in ENTITY_TYPES.keys():
                query = f"MATCH (n:{entity_type}) RETURN n.name as name"
                results = self.neo4j_client.execute_query(query)
                for result in results:
                    name = result["name"]
                    vocab[name] = entity_type
                    if name in ENTITY_SYNONYMS:
                        for synonym in ENTITY_SYNONYMS[name]:
                            vocab[synonym] = entity_type
        except Exception as e:
            print(f"构建实体词汇表时出错: {e}")

        return vocab

    def _init_jieba(self):
        for entity in self.entity_vocab.keys():
            jieba.add_word(entity)

    def extract_entities(self, text: str) -> List[Dict[str, any]]:
        entities = []
        words = jieba.lcut(text)

        for word in words:
            if word in self.entity_vocab:
                canonical_name = self._get_canonical_name(word)
                entities.append({
                    "text": word,
                    "canonical_name": canonical_name,
                    "type": self.entity_vocab[word],
                    "start": text.find(word),
                    "end": text.find(word) + len(word),
                    "match_method": "exact"
                })

        entities = self._remove_duplicates(entities)

        if not entities:
            fuzzy_entities = self.fuzzy_match(text)
            entities.extend(fuzzy_entities)

        return entities

    def _get_canonical_name(self, term: str) -> str:
        for canonical, synonyms in ENTITY_SYNONYMS.items():
            if term in synonyms:
                return canonical
        return term

    def _remove_duplicates(self, entities: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for entity in entities:
            key = (entity["canonical_name"], entity["type"])
            if key not in seen:
                seen.add(key)
                unique.append(entity)
        return unique

    def fuzzy_match(self, text: str, threshold: int = None) -> List[Dict[str, any]]:
        entities = []
        all_entity_names = list(self.entity_vocab.keys())

        for word in jieba.lcut(text):
            if len(word) < 2:
                continue

            if threshold is not None:
                dynamic_threshold = threshold
            else:
                dynamic_threshold = self.dynamic_threshold.compute(word)

            matches = process.extract(word, all_entity_names, limit=5)

            for match_name, score in matches:
                if score >= dynamic_threshold:
                    canonical_name = self._get_canonical_name(match_name)
                    entities.append({
                        "text": word,
                        "matched_text": match_name,
                        "canonical_name": canonical_name,
                        "type": self.entity_vocab[match_name],
                        "confidence": score / 100.0,
                        "fuzzy": True,
                        "match_method": "fuzzy",
                        "match_score": score,
                        "dynamic_threshold": dynamic_threshold,
                        "word_length": len(word)
                    })

        return self._remove_duplicates(entities)

    def fuzzy_match_with_detail(self, text: str) -> Dict[str, any]:
        words = jieba.lcut(text)
        all_entity_names = list(self.entity_vocab.keys())

        detail = {
            "original_text": text,
            "segmented_words": words,
            "thresholds": {},
            "matches": [],
            "entities": []
        }

        for word in words:
            if len(word) < 2:
                continue

            dynamic_threshold = self.dynamic_threshold.compute(word)
            detail["thresholds"][word] = {
                "threshold": dynamic_threshold,
                "word_length": len(word),
                "reason": self._threshold_reason(word, dynamic_threshold)
            }

            matches = process.extract(word, all_entity_names, limit=5)

            for match_name, score in matches:
                match_info = {
                    "query_word": word,
                    "matched_name": match_name,
                    "score": score,
                    "threshold": dynamic_threshold,
                    "passed": score >= dynamic_threshold,
                    "word_length": len(word)
                }
                detail["matches"].append(match_info)

                if score >= dynamic_threshold:
                    canonical_name = self._get_canonical_name(match_name)
                    detail["entities"].append({
                        "text": word,
                        "matched_text": match_name,
                        "canonical_name": canonical_name,
                        "type": self.entity_vocab[match_name],
                        "confidence": score / 100.0,
                        "fuzzy": True,
                        "match_method": "fuzzy",
                        "dynamic_threshold": dynamic_threshold
                    })

        detail["entities"] = self._remove_duplicates(detail["entities"])
        return detail

    def _threshold_reason(self, word: str, threshold: int) -> str:
        word_len = len(word)
        if word_len <= self.dynamic_threshold.short_boundary:
            return f"短实体(len={word_len})，阈值降低至{threshold}以增加召回率"
        elif word_len >= self.dynamic_threshold.long_boundary:
            return f"长实体(len={word_len})，阈值提高至{threshold}以保证精确率"
        else:
            return f"中等实体(len={word_len})，自适应阈值{threshold}"

    def find_entities_by_type(self, text: str, entity_type: str) -> List[Dict[str, any]]:
        all_entities = self.extract_entities(text)
        return [e for e in all_entities if e["type"] == entity_type]

    def refresh_vocab(self):
        self.entity_vocab = self._build_entity_vocab()
        self._init_jieba()
