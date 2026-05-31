import re
import nltk
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple


nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


class ExtractiveChunker:
    def __init__(self, max_chars: int = 5000, overlap_chars: int = 500):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.max_chars:
            return [text]
        
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > self.max_chars and current_chunk:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-self.overlap_chars:] if len(current_chunk) > self.overlap_chars else current_chunk
                current_chunk = overlap_text
            current_chunk += para + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class ExtractiveSummarizer:
    def __init__(self, max_chars_per_chunk: int = 5000):
        self.stopwords = set()
        self._load_stopwords()
        self.chunker = ExtractiveChunker(max_chars=max_chars_per_chunk)

    def _load_stopwords(self):
        try:
            from nltk.corpus import stopwords
            self.stopwords = set(stopwords.words('english'))
        except:
            pass

    def _preprocess_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    def _sentence_tokenize(self, text: str) -> List[str]:
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _textrank_similarity_matrix(self, sentences: List[str]) -> np.ndarray:
        if len(sentences) == 0:
            return np.array([])
        
        tfidf = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
        
        try:
            tfidf_matrix = tfidf.fit_transform(sentences)
            similarity_matrix = cosine_similarity(tfidf_matrix)
        except:
            n = len(sentences)
            similarity_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j:
                        words_i = set(sentences[i].lower().split())
                        words_j = set(sentences[j].lower().split())
                        if self.stopwords:
                            words_i = words_i - self.stopwords
                            words_j = words_j - self.stopwords
                        if len(words_i) + len(words_j) > 0:
                            similarity_matrix[i][j] = len(words_i & words_j) / len(words_i | words_j)
        
        return similarity_matrix

    def _textrank(self, sentences: List[str], top_n: int = 3) -> List[Tuple[int, str, float]]:
        if len(sentences) <= top_n:
            return [(i, s, 1.0) for i, s in enumerate(sentences)]
        
        similarity_matrix = self._textrank_similarity_matrix(sentences)
        
        if similarity_matrix.size == 0:
            return [(i, s, 1.0) for i, s in enumerate(sentences[:top_n])]
        
        nx_graph = nx.from_numpy_array(similarity_matrix)
        scores = nx.pagerank(nx_graph, max_iter=500)
        
        ranked_sentences = sorted(
            ((scores[i], i, sent) for i, sent in enumerate(sentences)),
            reverse=True
        )
        
        top_sentences = sorted(
            ranked_sentences[:top_n],
            key=lambda x: x[1]
        )
        
        return [(idx, sent, score) for score, idx, sent in top_sentences]

    def _mmr_summarize(
        self,
        sentences: List[str],
        top_n: int = 3,
        lambda_param: float = 0.7
    ) -> List[Tuple[int, str, float]]:
        if len(sentences) <= top_n:
            return [(i, s, 1.0) for i, s in enumerate(sentences)]
        
        tfidf = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = tfidf.fit_transform(sentences)
        
        doc_vector = tfidf_matrix.sum(axis=0)
        doc_norm = np.linalg.norm(doc_vector)
        if doc_norm > 0:
            doc_vector = doc_vector / doc_norm
        
        selected_indices = []
        remaining_indices = list(range(len(sentences)))
        
        for _ in range(top_n):
            if not remaining_indices:
                break
            
            best_idx = -1
            best_score = -1
            
            for idx in remaining_indices:
                sentence_vector = tfidf_matrix[idx]
                relevance = cosine_similarity(sentence_vector, doc_vector)[0][0]
                
                redundancy = 0
                if selected_indices:
                    selected_matrix = tfidf_matrix[selected_indices]
                    redundancy = np.max(cosine_similarity(sentence_vector, selected_matrix))
                
                mmr_score = lambda_param * relevance - (1 - lambda_param) * redundancy
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
        
        selected_indices.sort()
        
        return [(idx, sentences[idx], 1.0) for idx in selected_indices]

    def summarize(
        self,
        text: str,
        num_sentences: int = 3,
        method: str = "textrank",
        preserve_keywords: bool = True,
        enable_sliding_window: bool = True
    ) -> Tuple[str, int]:
        text = self._preprocess_text(text)
        
        if enable_sliding_window and len(text) > self.chunker.max_chars:
            chunks = self.chunker.chunk_text(text)
            chunks_processed = len(chunks)
            
            per_chunk_sentences = max(2, num_sentences // len(chunks) + 1)
            
            all_selected = []
            global_offset = 0
            
            for chunk in chunks:
                sentences = self._sentence_tokenize(chunk)
                if len(sentences) == 0:
                    global_offset += len(chunk)
                    continue
                
                if method == "mmr":
                    ranked = self._mmr_summarize(sentences, per_chunk_sentences)
                else:
                    ranked = self._textrank(sentences, per_chunk_sentences)
                
                for idx, sent, score in ranked:
                    all_selected.append((score, sent))
                
                global_offset += len(chunk)
            
            all_selected.sort(key=lambda x: x[0], reverse=True)
            top_selected = all_selected[:num_sentences]
            
            summary = ' '.join([sent for _, sent in top_selected])
            return summary, chunks_processed
        
        sentences = self._sentence_tokenize(text)
        
        if len(sentences) == 0:
            return "", 1
        
        if method == "textrank":
            ranked_sentences = self._textrank(sentences, num_sentences)
        elif method == "mmr":
            ranked_sentences = self._mmr_summarize(sentences, num_sentences)
        else:
            ranked_sentences = self._textrank(sentences, num_sentences)
        
        summary = ' '.join([sent for _, sent, _ in ranked_sentences])
        
        return summary, 1
