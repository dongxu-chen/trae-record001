from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TrieNode:
    children: Dict[str, 'TrieNode'] = None
    is_end: bool = False
    weight: float = 0.0
    hotword: str = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = {}


class WeightedHotwordTrie:
    def __init__(self, boost_factor: float = 10.0):
        self.root = TrieNode()
        self.boost_factor = boost_factor
        self.hotword_weights: Dict[str, float] = {}
        
    def add_hotword(self, hotword: str, weight: Optional[float] = None):
        if weight is None:
            weight = self.boost_factor * (1 + len(hotword) * 0.1)
        
        self.hotword_weights[hotword] = weight
        
        node = self.root
        for char in hotword:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        
        node.is_end = True
        node.weight = weight
        node.hotword = hotword
        
    def add_hotwords(self, hotwords: List[str]):
        sorted_hotwords = sorted(hotwords, key=lambda x: len(x), reverse=True)
        for hotword in sorted_hotwords:
            self.add_hotword(hotword)
            
    def search(self, text: str) -> List[Tuple[str, int, int, float]]:
        matches = []
        n = len(text)
        
        for i in range(n):
            node = self.root
            j = i
            longest_match_end = -1
            longest_match_hotword = None
            longest_match_weight = 0
            
            while j < n and text[j] in node.children:
                node = node.children[text[j]]
                j += 1
                
                if node.is_end:
                    longest_match_end = j
                    longest_match_hotword = node.hotword
                    longest_match_weight = node.weight
            
            if longest_match_end != -1:
                matches.append((
                    longest_match_hotword,
                    i,
                    longest_match_end,
                    longest_match_weight
                ))
        
        return self._merge_overlapping_matches(matches)
    
    def _merge_overlapping_matches(
        self,
        matches: List[Tuple[str, int, int, float]]
    ) -> List[Tuple[str, int, int, float]]:
        if not matches:
            return []
        
        sorted_matches = sorted(matches, key=lambda x: (x[1], -(x[2] - x[1]), -x[3]))
        
        merged = []
        last_end = -1
        
        for match in sorted_matches:
            hotword, start, end, weight = match
            if start >= last_end:
                merged.append(match)
                last_end = end
        
        return merged
    
    def find_all_hotwords(self, text: str) -> List[Tuple[str, float]]:
        matches = self.search(text)
        return [(hotword, weight) for hotword, _, _, weight in matches]
    
    def get_logit_boost_map(self, tokenizer, text: str) -> Dict[int, float]:
        boost_map = {}
        matches = self.search(text)
        
        for hotword, start, end, weight in matches:
            token_ids = tokenizer.encode(hotword, add_special_tokens=False)
            for token_id in token_ids:
                if token_id in boost_map:
                    boost_map[token_id] = max(boost_map[token_id], weight)
                else:
                    boost_map[token_id] = weight
        
        return boost_map
    
    def clear(self):
        self.root = TrieNode()
        self.hotword_weights.clear()
    
    def get_hotwords(self) -> List[str]:
        return list(self.hotword_weights.keys())


class HotwordEnhancer:
    def __init__(self, boost_factor: float = 10.0):
        self.trie = WeightedHotwordTrie(boost_factor)
        self.tokenizer = None
        
    def set_tokenizer(self, tokenizer):
        self.tokenizer = tokenizer
        
    def set_hotwords(self, hotwords: List[str], boost_factor: Optional[float] = None):
        self.trie.clear()
        if boost_factor:
            self.trie.boost_factor = boost_factor
        self.trie.add_hotwords(hotwords)
        
    def enhance_logits(self, logits, predicted_text: str = ""):
        import torch
        
        if self.tokenizer is None or not self.trie.get_hotwords():
            return logits
        
        boost_map = self.trie.get_logit_boost_map(self.tokenizer, predicted_text)
        
        if not boost_map:
            return logits
        
        boosted_logits = logits.clone()
        for token_id, boost in boost_map.items():
            boosted_logits[:, :, token_id] += boost
        
        return boosted_logits
    
    def find_matched_hotwords(self, text: str) -> List[Tuple[str, float]]:
        return self.trie.find_all_hotwords(text)
    
    def get_hotwords(self) -> List[str]:
        return self.trie.get_hotwords()
