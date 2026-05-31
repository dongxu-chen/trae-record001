import os
import pickle
import jieba
from collections import defaultdict

class NGramLanguageModel:
    def __init__(self, n=2, save_path=None):
        self.n = n
        self.save_path = save_path
        self.ngrams = defaultdict(int)
        self.context_counts = defaultdict(int)
        self.vocab = defaultdict(int)
        self.total_words = 0
    
    def train(self, corpus):
        for sentence in corpus:
            words = jieba.lcut(sentence)
            words = ['<START>'] * (self.n - 1) + words + ['<END>']
            
            for word in words:
                self.vocab[word] += 1
                self.total_words += 1
            
            for i in range(len(words) - self.n + 1):
                ngram = tuple(words[i:i+self.n])
                context = ngram[:-1]
                self.ngrams[ngram] += 1
                self.context_counts[context] += 1
    
    def probability(self, word, context):
        context = tuple(context[-(self.n - 1):])
        ngram = context + (word,)
        
        ngram_count = self.ngrams.get(ngram, 0)
        context_count = self.context_counts.get(context, 0)
        
        if context_count == 0:
            return self.vocab.get(word, 1) / (self.total_words + len(self.vocab))
        
        return ngram_count / context_count
    
    def sentence_probability(self, sentence):
        words = jieba.lcut(sentence)
        words = ['<START>'] * (self.n - 1) + words + ['<END>']
        
        log_prob = 0.0
        for i in range(self.n - 1, len(words)):
            context = words[i - self.n + 1:i]
            word = words[i]
            prob = self.probability(word, context)
            log_prob += prob
        
        return log_prob
    
    def score_candidates(self, original_query, candidates):
        scored = []
        original_prob = self.sentence_probability(original_query)
        
        for candidate in candidates:
            cand_prob = self.sentence_probability(candidate[0])
            score = cand_prob / max(original_prob, 1e-10)
            scored.append((candidate[0], candidate[1], candidate[2], score))
        
        scored.sort(key=lambda x: (-x[3], x[1], -x[2]))
        return scored
    
    def save(self):
        if self.save_path:
            with open(self.save_path, 'wb') as f:
                pickle.dump({
                    'n': self.n,
                    'ngrams': dict(self.ngrams),
                    'context_counts': dict(self.context_counts),
                    'vocab': dict(self.vocab),
                    'total_words': self.total_words
                }, f)
    
    def load(self):
        if self.save_path and os.path.exists(self.save_path):
            with open(self.save_path, 'rb') as f:
                data = pickle.load(f)
                self.n = data['n']
                self.ngrams = defaultdict(int, data['ngrams'])
                self.context_counts = defaultdict(int, data['context_counts'])
                self.vocab = defaultdict(int, data['vocab'])
                self.total_words = data['total_words']
            return True
        return False
