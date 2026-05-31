import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import nltk


nltk.download('punkt', quiet=True)


class MultiDocSummarizer:
    def __init__(self, max_summary_length: int = 300):
        self.max_summary_length = max_summary_length
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        try:
            from nltk.corpus import stopwords
            return set(stopwords.words('english'))
        except:
            return set()

    def _sentence_tokenize(self, text: str) -> List[str]:
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _compute_centroid(self, tfidf_matrix):
        return np.mean(tfidf_matrix, axis=0)

    def _compute_sentence_scores(
        self,
        sentences: List[str],
        doc_ids: List[int],
        method: str = 'centroid'
    ) -> List[Tuple[int, float]]:
        if len(sentences) == 0:
            return []
        
        try:
            tfidf = TfidfVectorizer(
                stop_words='english',
                max_features=1000,
                ngram_range=(1, 2)
            )
            tfidf_matrix = tfidf.fit_transform(sentences)
            
            if method == 'centroid':
                centroid = self._compute_centroid(tfidf_matrix)
                scores = cosine_similarity(tfidf_matrix, centroid.reshape(1, -1)).flatten()
            elif method == 'tfidf_sum':
                scores = np.sum(tfidf_matrix, axis=1).A1
            else:
                scores = np.ones(len(sentences))
            
            return list(enumerate(scores))
            
        except Exception as e:
            print(f"Scoring error: {e}")
            return [(i, 1.0) for i in range(len(sentences))]

    def _reduce_redundancy(
        self,
        sentences: List[str],
        scores: List[Tuple[int, float]],
        threshold: float = 0.7
    ) -> List[int]:
        if len(sentences) == 0:
            return []
        
        try:
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(sentences)
            
            scores.sort(key=lambda x: x[1], reverse=True)
            
            selected_indices = []
            selected_vectors = []
            
            for idx, score in scores:
                if len(selected_indices) == 0:
                    selected_indices.append(idx)
                    selected_vectors.append(tfidf_matrix[idx])
                    continue
                
                current_vector = tfidf_matrix[idx]
                if selected_vectors:
                    selected_matrix = np.vstack(selected_vectors)
                    max_sim = np.max(cosine_similarity(current_vector, selected_matrix))
                    
                    if max_sim < threshold:
                        selected_indices.append(idx)
                        selected_vectors.append(current_vector)
            
            return selected_indices
            
        except Exception as e:
            print(f"Redundancy reduction error: {e}")
            return [idx for idx, _ in scores[:10]]

    def _mmr_selection(
        self,
        sentences: List[str],
        scores: List[Tuple[int, float]],
        lambda_param: float = 0.7,
        top_n: int = 10
    ) -> List[int]:
        if len(sentences) == 0:
            return []
        
        try:
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(sentences)
            
            score_dict = {idx: score for idx, score in scores}
            
            selected_indices = []
            remaining_indices = [idx for idx, _ in scores]
            
            for _ in range(min(top_n, len(remaining_indices))):
                best_idx = -1
                best_mmr = -1
                
                for idx in remaining_indices:
                    relevance = score_dict.get(idx, 0)
                    
                    redundancy = 0
                    if selected_indices:
                        selected_matrix = tfidf_matrix[selected_indices]
                        redundancy = np.max(cosine_similarity(tfidf_matrix[idx], selected_matrix))
                    
                    mmr = lambda_param * relevance - (1 - lambda_param) * redundancy
                    
                    if mmr > best_mmr:
                        best_mmr = mmr
                        best_idx = idx
                
                if best_idx >= 0:
                    selected_indices.append(best_idx)
                    remaining_indices.remove(best_idx)
            
            return selected_indices
            
        except Exception as e:
            print(f"MMR selection error: {e}")
            return [idx for idx, _ in scores[:top_n]]

    def _cluster_sentences(
        self,
        sentences: List[str],
        n_clusters: int = 5
    ) -> Dict[int, List[int]]:
        if len(sentences) < n_clusters:
            n_clusters = max(1, len(sentences) // 2)
        
        try:
            from sklearn.cluster import KMeans
            
            tfidf = TfidfVectorizer(stop_words='english')
            tfidf_matrix = tfidf.fit_transform(sentences)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(tfidf_matrix)
            
            clusters = defaultdict(list)
            for idx, label in enumerate(labels):
                clusters[label].append(idx)
            
            return clusters
            
        except Exception as e:
            print(f"Clustering error: {e}")
            return {0: list(range(len(sentences)))}

    def summarize_extractive(
        self,
        documents: List[str],
        num_sentences: int = 8,
        method: str = 'mmr',
        reduce_redundancy: bool = True
    ) -> Dict:
        all_sentences = []
        doc_sentence_ranges = []
        
        for doc_idx, doc in enumerate(documents):
            sentences = self._sentence_tokenize(doc)
            start_idx = len(all_sentences)
            all_sentences.extend(sentences)
            doc_sentence_ranges.append((start_idx, len(all_sentences)))
        
        if len(all_sentences) == 0:
            return {
                'summary': '',
                'sentences': [],
                'num_docs': len(documents),
                'method': method
            }
        
        scores = self._compute_sentence_scores(
            all_sentences,
            [i for i, _ in enumerate(documents) for _ in doc_sentence_ranges[i]],
            method='centroid'
        )
        
        if method == 'mmr':
            selected_indices = self._mmr_selection(
                all_sentences,
                scores,
                lambda_param=0.7,
                top_n=num_sentences
            )
        else:
            if reduce_redundancy:
                selected_indices = self._reduce_redundancy(
                    all_sentences,
                    scores,
                    threshold=0.6
                )[:num_sentences]
            else:
                scores.sort(key=lambda x: x[1], reverse=True)
                selected_indices = [idx for idx, _ in scores[:num_sentences]]
        
        selected_indices.sort()
        selected_sentences = [all_sentences[idx] for idx in selected_indices]
        
        doc_contributions = []
        for doc_idx, (start, end) in enumerate(doc_sentence_ranges):
            count = sum(1 for idx in selected_indices if start <= idx < end)
            doc_contributions.append({
                'doc_id': doc_idx,
                'sentences_used': count,
                'total_sentences': end - start
            })
        
        return {
            'summary': ' '.join(selected_sentences),
            'sentences': selected_sentences,
            'sentence_indices': selected_indices,
            'num_docs': len(documents),
            'method': method,
            'doc_contributions': doc_contributions,
            'total_sentences': len(all_sentences)
        }

    def summarize_abstractive(
        self,
        documents: List[str],
        abstractive_summarizer,
        model_type: str = 'bart',
        max_length: int = 300,
        min_length: int = 100,
        intermediate_summary_length: int = 150
    ) -> Dict:
        intermediate_summaries = []
        
        for doc_idx, doc in enumerate(documents):
            if len(doc.strip()) < 50:
                continue
            
            try:
                doc_summary, _ = abstractive_summarizer.summarize(
                    text=doc,
                    model_type=model_type,
                    max_length=intermediate_summary_length,
                    min_length=50,
                    preserve_keywords=True,
                    enable_sliding_window=True
                )
                intermediate_summaries.append(doc_summary)
            except Exception as e:
                print(f"Error summarizing doc {doc_idx}: {e}")
                if len(doc) > intermediate_summary_length:
                    intermediate_summaries.append(doc[:intermediate_summary_length] + "...")
                else:
                    intermediate_summaries.append(doc)
        
        if not intermediate_summaries:
            return {
                'summary': '',
                'intermediate_summaries': [],
                'num_docs': len(documents)
            }
        
        combined_text = "\n\n".join([
            f"Document {i+1} Summary: {s}"
            for i, s in enumerate(intermediate_summaries)
        ])
        
        comprehensive_prompt = (
            f"Based on the following summaries from multiple documents, "
            f"create a comprehensive and coherent summary that integrates all key information. "
            f"Focus on cross-document themes and important findings:\n\n{combined_text}"
        )
        
        try:
            final_summary, _ = abstractive_summarizer.summarize(
                text=comprehensive_prompt,
                model_type=model_type,
                max_length=max_length,
                min_length=min_length,
                preserve_keywords=True,
                enable_sliding_window=True
            )
        except Exception as e:
            print(f"Error generating final summary: {e}")
            final_summary = ' '.join(intermediate_summaries)[:max_length]
        
        return {
            'summary': final_summary,
            'intermediate_summaries': intermediate_summaries,
            'num_docs': len(documents),
            'model': model_type
        }

    def summarize(
        self,
        documents: List[str],
        summary_type: str = 'extractive',
        abstractive_summarizer=None,
        **kwargs
    ) -> Dict:
        if len(documents) == 0:
            raise ValueError("No documents provided")
        
        if summary_type == 'abstractive' and abstractive_summarizer is not None:
            return self.summarize_abstractive(
                documents,
                abstractive_summarizer,
                **kwargs
            )
        else:
            return self.summarize_extractive(
                documents,
                **kwargs
            )
