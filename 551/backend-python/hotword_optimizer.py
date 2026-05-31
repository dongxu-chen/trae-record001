import re
from collections import defaultdict

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

class WeightedTrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.weight = 0
        self.word = None
        self.hotword_info = None

class WeightedTrie:
    def __init__(self):
        self.root = WeightedTrieNode()
        self.words = set()
    
    def insert(self, word, weight=1.0, hotword_info=None):
        if not word or len(word) < 2:
            return False
        
        if word in self.words:
            self._update_weight(word, weight)
            return False
        
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = WeightedTrieNode()
            node = node.children[char]
        
        node.is_end_of_word = True
        node.weight = weight
        node.word = word
        node.hotword_info = hotword_info
        self.words.add(word)
        
        self._propagate_weight(self.root, word, weight)
        
        return True
    
    def _propagate_weight(self, root, word, weight):
        node = root
        for char in word:
            if char in node.children:
                node = node.children[char]
                if node.weight < weight:
                    node.weight = weight
    
    def _update_weight(self, word, weight):
        node = self.root
        for char in word:
            if char in node.children:
                node = node.children[char]
            else:
                return
        
        if node.is_end_of_word and node.weight < weight:
            node.weight = weight
            self._propagate_weight(self.root, word, weight)
    
    def search(self, word):
        if not word:
            return None
        
        node = self.root
        for char in word:
            if char not in node.children:
                return None
            node = node.children[char]
        
        return node if node.is_end_of_word else None
    
    def delete(self, word):
        if word not in self.words:
            return False
        
        self._delete_recursive(self.root, word, 0)
        self.words.discard(word)
        return True
    
    def _delete_recursive(self, node, word, index):
        if index == len(word):
            if not node.is_end_of_word:
                return False
            node.is_end_of_word = False
            node.word = None
            node.hotword_info = None
            node.weight = 0
            return len(node.children) == 0
        
        char = word[index]
        if char not in node.children:
            return False
        
        should_delete_child = self._delete_recursive(node.children[char], word, index + 1)
        
        if should_delete_child:
            del node.children[char]
            return len(node.children) == 0 and not node.is_end_of_word
        
        max_child_weight = max(
            (child.weight for child in node.children.values()),
            default=0
        )
        node.weight = max(node.weight if node.is_end_of_word else 0, max_child_weight)
        
        return False
    
    def find_all_matches(self, text, threshold=0.7):
        matches = []
        n = len(text)
        
        for i in range(n):
            node = self.root
            current_match = None
            
            for j in range(i, n):
                char = text[j]
                if char not in node.children:
                    break
                
                node = node.children[char]
                
                if node.is_end_of_word:
                    similarity = self._calculate_similarity(text[i:j+1], node.word)
                    if similarity >= threshold:
                        current_match = {
                            'word': node.word,
                            'start': i,
                            'end': j + 1,
                            'weight': node.weight,
                            'similarity': similarity,
                            'matched_text': text[i:j+1]
                        }
            
            if current_match:
                matches.append(current_match)
        
        matches = self._resolve_overlaps(matches)
        matches.sort(key=lambda x: (-x['weight'], -x['similarity']))
        
        return matches
    
    def _calculate_similarity(self, text1, text2):
        if not text1 or not text2:
            return 0.0
        
        len1, len2 = len(text1), len(text2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        jaccard = intersection / union if union > 0 else 0.0
        
        length_ratio = min(len1, len2) / max(len1, len2)
        
        return jaccard * 0.7 + length_ratio * 0.3
    
    def _resolve_overlaps(self, matches):
        if not matches:
            return []
        
        matches.sort(key=lambda x: x['start'])
        
        resolved = []
        i = 0
        while i < len(matches):
            current = matches[i]
            
            j = i + 1
            while j < len(matches):
                next_match = matches[j]
                if next_match['start'] < current['end']:
                    if next_match['weight'] > current['weight']:
                        current = next_match
                    elif next_match['weight'] == current['weight']:
                        if next_match['similarity'] > current['similarity']:
                            current = next_match
                    j += 1
                else:
                    break
            
            resolved.append(current)
            i = j
        
        return resolved
    
    def get_all_words(self):
        return sorted(list(self.words))
    
    def size(self):
        return len(self.words)
    
    def clear(self):
        self.root = WeightedTrieNode()
        self.words.clear()

class HotwordOptimizer:
    def __init__(self, hotwords=None, language='zh-CN'):
        self.language = language
        self.trie = WeightedTrie()
        self.hotword_weights = {}
        self.word_frequency = defaultdict(int)
        
        if hotwords:
            for i, word in enumerate(hotwords):
                weight = 1.0 + (len(hotwords) - i) * 0.1
                self.add_hotword(word, weight)
        
        if JIEBA_AVAILABLE and language.startswith('zh'):
            for word in self.trie.words:
                jieba.add_word(word, freq=100000)
    
    def add_hotword(self, word, weight=None):
        if not word or len(word) < 2:
            return False
        
        if weight is None:
            existing_count = self.trie.size()
            weight = 1.0 + existing_count * 0.05
        
        hotword_info = {
            'word': word,
            'weight': weight,
            'added_at': None,
            'match_count': 0
        }
        
        success = self.trie.insert(word, weight, hotword_info)
        
        if success:
            self.hotword_weights[word] = weight
            if JIEBA_AVAILABLE and self.language.startswith('zh'):
                jieba.add_word(word, freq=100000)
        
        return success
    
    def remove_hotword(self, word):
        if word in self.hotword_weights:
            del self.hotword_weights[word]
        
        if JIEBA_AVAILABLE and self.language.startswith('zh'):
            try:
                jieba.del_word(word)
            except:
                pass
        
        return self.trie.delete(word)
    
    def set_hotwords(self, hotwords):
        self.trie.clear()
        self.hotword_weights.clear()
        self.word_frequency.clear()
        
        for i, word in enumerate(hotwords):
            weight = 1.0 + (len(hotwords) - i) * 0.1
            self.add_hotword(word, weight)
    
    def optimize(self, text):
        if not text or self.trie.size() == 0:
            return text
        
        matches = self.trie.find_all_matches(text, threshold=0.6)
        
        if not matches:
            return text
        
        optimized_text = text
        offset = 0
        
        matches.sort(key=lambda x: x['start'])
        
        for match in matches:
            start = match['start'] + offset
            end = match['end'] + offset
            original_length = end - start
            replacement = match['word']
            replacement_length = len(replacement)
            
            optimized_text = optimized_text[:start] + replacement + optimized_text[end:]
            offset += replacement_length - original_length
            
            self.word_frequency[match['word']] += 1
            
            if match['word'] in self.hotword_weights:
                self.hotword_weights[match['word']] += 0.01
        
        return optimized_text
    
    def get_hotword_list(self):
        words = self.trie.get_all_words()
        return [
            {
                'word': word,
                'weight': self.hotword_weights.get(word, 1.0),
                'match_count': self.word_frequency.get(word, 0)
            }
            for word in words
        ]
    
    def get_top_hotwords(self, n=10):
        hotwords = self.get_hotword_list()
        hotwords.sort(key=lambda x: (-x['weight'], -x['match_count']))
        return hotwords[:n]
    
    def set_language(self, language):
        old_language = self.language
        self.language = language
        
        if language.startswith('zh') and JIEBA_AVAILABLE:
            if not old_language.startswith('zh'):
                for word in self.trie.words:
                    jieba.add_word(word, freq=100000)
    
    def get_stats(self):
        return {
            'total_hotwords': self.trie.size(),
            'total_matches': sum(self.word_frequency.values()),
            'language': self.language,
            'top_hotwords': self.get_top_hotwords(5)
        }
