import jieba
import numpy as np
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
import re

class TextEmbedding:
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.model = SentenceTransformer(model_name)
        self.stop_words = self._load_stop_words()
        self.tfidf = TfidfVectorizer(max_features=10000)
        
    def _load_stop_words(self) -> set:
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '有', '年', '什么', '可以', '对', '能', '和', '跟', '与', '及', '或',
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with',
            'at', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'amp', 'nbsp'
        }
        return stop_words
    
    def preprocess_text(self, text: str) -> str:
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.lower().strip()
        return text
    
    def tokenize_chinese(self, text: str) -> List[str]:
        words = jieba.cut(text)
        words = [w for w in words if w not in self.stop_words and len(w) > 1]
        return words
    
    def get_embedding(self, text: str) -> np.ndarray:
        processed = self.preprocess_text(text)
        embedding = self.model.encode(processed)
        return embedding
    
    def get_keywords_tfidf(self, texts: List[str], top_k: int = 10) -> List[str]:
        processed_texts = []
        for text in texts:
            words = self.tokenize_chinese(self.preprocess_text(text))
            processed_texts.append(' '.join(words))
        
        try:
            tfidf_matrix = self.tfidf.fit_transform(processed_texts)
            feature_names = self.tfidf.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            top_indices = scores.argsort()[-top_k:][::-1]
            return [feature_names[i] for i in top_indices]
        except:
            words = []
            for text in texts:
                words.extend(self.tokenize_chinese(self.preprocess_text(text)))
            from collections import Counter
            counter = Counter(words)
            return [word for word, _ in counter.most_common(top_k)]
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
