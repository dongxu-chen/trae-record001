import os
from pypinyin import lazy_pinyin, Style
import numpy as np

class DomainDictionary:
    def __init__(self, dict_path):
        self.dict_path = dict_path
        self.words = {}
        self.pinyin_index = {}
        self.pinyin_list_index = {}
        self.pinyin_vectors = {}
        self.char_to_idx = {}
        self.idx_to_char = {}
        self._init_pinyin_chars()
        self.load_dictionary()
    
    def _init_pinyin_chars(self):
        pinyin_chars = 'abcdefghijklmnopqrstuvwxyz'
        for i, c in enumerate(pinyin_chars):
            self.char_to_idx[c] = i
            self.idx_to_char[i] = c
    
    def _pinyin_to_vector(self, pinyin_str):
        vec_size = len(self.char_to_idx)
        vector = np.zeros(vec_size, dtype=np.float32)
        for c in pinyin_str.lower():
            if c in self.char_to_idx:
                vector[self.char_to_idx[c]] += 1
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector
    
    def _cosine_similarity(self, vec1, vec2):
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def load_dictionary(self):
        if not os.path.exists(self.dict_path):
            return
        
        with open(self.dict_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    word = parts[0]
                    weight = int(parts[1]) if parts[1].isdigit() else 1
                    self.words[word] = weight
                    
                    pinyin_list = lazy_pinyin(word)
                    pinyin_key = ''.join(pinyin_list)
                    
                    if pinyin_key not in self.pinyin_index:
                        self.pinyin_index[pinyin_key] = []
                    self.pinyin_index[pinyin_key].append(word)
                    
                    if pinyin_key not in self.pinyin_list_index:
                        self.pinyin_list_index[pinyin_key] = pinyin_list
                    
                    self.pinyin_vectors[pinyin_key] = self._pinyin_to_vector(pinyin_key)
    
    def get_weight(self, word):
        return self.words.get(word, 0)
    
    def get_all_words(self):
        return list(self.words.keys())
    
    def get_words_by_pinyin(self, pinyin_str):
        return self.pinyin_index.get(pinyin_str, [])
    
    def pinyin_vector_similarity(self, pinyin_str1, pinyin_str2):
        vec1 = self._pinyin_to_vector(pinyin_str1)
        vec2 = self._pinyin_to_vector(pinyin_str2)
        return self._cosine_similarity(vec1, vec2)
    
    def vector_match_pinyin(self, pinyin_str, min_similarity=0.7):
        matches = []
        input_vec = self._pinyin_to_vector(pinyin_str)
        
        for key_pinyin, words in self.pinyin_index.items():
            key_vec = self.pinyin_vectors.get(key_pinyin)
            if key_vec is not None:
                similarity = self._cosine_similarity(input_vec, key_vec)
                if similarity >= min_similarity:
                    for word in words:
                        matches.append((word, similarity))
        
        matches.sort(key=lambda x: -x[1])
        return matches
    
    def exact_pinyin_match(self, pinyin_str):
        if pinyin_str in self.pinyin_index:
            return self.pinyin_index[pinyin_str]
        return []
    
    def fuzzy_match_pinyin(self, pinyin_str, max_distance=1):
        matches = []
        for key_pinyin, words in self.pinyin_index.items():
            distance = self._pinyin_distance(pinyin_str, key_pinyin)
            if distance <= max_distance:
                for word in words:
                    matches.append((word, distance))
        return matches
    
    def _pinyin_distance(self, s1, s2):
        if len(s1) > len(s2):
            s1, s2 = s2, s1
        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2 + 1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]
    
    def add_word(self, word, weight=1):
        self.words[word] = weight
        pinyin_list = lazy_pinyin(word)
        pinyin_key = ''.join(pinyin_list)
        
        if pinyin_key not in self.pinyin_index:
            self.pinyin_index[pinyin_key] = []
        if word not in self.pinyin_index[pinyin_key]:
            self.pinyin_index[pinyin_key].append(word)
        
        if pinyin_key not in self.pinyin_list_index:
            self.pinyin_list_index[pinyin_key] = pinyin_list
        
        self.pinyin_vectors[pinyin_key] = self._pinyin_to_vector(pinyin_key)
    
    def save_dictionary(self):
        sorted_words = sorted(self.words.items(), key=lambda x: -x[1])
        with open(self.dict_path, 'w', encoding='utf-8') as f:
            for word, weight in sorted_words:
                f.write(f"{word} {weight}\n")
