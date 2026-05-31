import jieba
from pypinyin import lazy_pinyin

class EditDistanceCorrector:
    def __init__(self, domain_dict, max_distance=2):
        self.domain_dict = domain_dict
        self.max_distance = max_distance
    
    def edit_distance(self, s1, s2):
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
    
    def _get_edits1(self, word):
        chars = list(word)
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = []
        for L, R in splits:
            if R:
                for c in 'abcdefghijklmnopqrstuvwxyz':
                    replaces.append(L + c + R[1:])
        inserts = []
        for L, R in splits:
            for c in 'abcdefghijklmnopqrstuvwxyz':
                inserts.append(L + c + R)
        return set(deletes + transposes + replaces + inserts)
    
    def _get_edits2(self, word):
        return set(e2 for e1 in self._get_edits1(word) for e2 in self._get_edits1(e1))
    
    def correct(self, word):
        all_words = self.domain_dict.get_all_words()
        
        if word in all_words:
            return [(word, 0, self.domain_dict.get_weight(word))]
        
        candidates = []
        
        word_pinyin = ''.join(lazy_pinyin(word))
        pinyin_matches = self.domain_dict.fuzzy_match_pinyin(word_pinyin, max_distance=self.max_distance)
        for dict_word, pinyin_dist in pinyin_matches:
            dist = self.edit_distance(word, dict_word)
            if dist <= self.max_distance:
                weight = self.domain_dict.get_weight(dict_word)
                candidates.append((dict_word, dist, weight))
        
        for dict_word in all_words:
            if abs(len(dict_word) - len(word)) <= self.max_distance:
                dist = self.edit_distance(word, dict_word)
                if dist <= self.max_distance:
                    weight = self.domain_dict.get_weight(dict_word)
                    candidates.append((dict_word, dist, weight))
        
        seen = {}
        for word, dist, weight in candidates:
            if word not in seen or dist < seen[word][0]:
                seen[word] = (dist, weight)
        
        candidates = [(w, d, wt) for w, (d, wt) in seen.items()]
        candidates.sort(key=lambda x: (x[1], -x[2]))
        
        return candidates
    
    def correct_query(self, query):
        words = jieba.lcut(query)
        corrected_words = []
        all_candidates = []
        
        for word in words:
            candidates = self.correct(word)
            if candidates:
                corrected_words.append(candidates[0][0])
            else:
                corrected_words.append(word)
            all_candidates.append({
                'original': word,
                'candidates': candidates[:5]
            })
        
        corrected_query = ''.join(corrected_words)
        return corrected_query, all_candidates
