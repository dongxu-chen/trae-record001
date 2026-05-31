import re
import nltk
import numpy as np
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict, Counter


nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


class TopicExtractor:
    def __init__(self, max_topics: int = 5, min_sentences_per_topic: int = 2):
        self.max_topics = max_topics
        self.min_sentences_per_topic = min_sentences_per_topic
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> set:
        try:
            from nltk.corpus import stopwords
            return set(stopwords.words('english'))
        except:
            return {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were'
            }

    def _sentence_tokenize(self, text: str) -> List[str]:
        try:
            sentences = nltk.sent_tokenize(text)
        except:
            sentences = re.split(r'(?<=[.!?。！？])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        return ' '.join(words)

    def _extract_topic_keywords(self, sentences: List[str], top_k: int = 5) -> List[str]:
        if not sentences:
            return []
        
        try:
            tfidf = TfidfVectorizer(
                stop_words='english',
                max_features=50,
                ngram_range=(1, 2)
            )
            tfidf_matrix = tfidf.fit_transform(sentences)
            feature_names = tfidf.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            keyword_scores = list(zip(feature_names, scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [word for word, _ in keyword_scores[:top_k]]
        except:
            words = []
            for s in sentences:
                words.extend(self._clean_text(s).split())
            return [word for word, _ in Counter(words).most_common(top_k)]

    def extract_topics_lda(
        self,
        sentences: List[str],
        num_topics: Optional[int] = None
    ) -> List[Dict]:
        if len(sentences) < self.min_sentences_per_topic * 2:
            return [{
                'topic_id': 0,
                'keywords': self._extract_topic_keywords(sentences),
                'sentences': sentences,
                'sentence_indices': list(range(len(sentences))),
                'size': len(sentences)
            }]
        
        n_topics = num_topics or min(self.max_topics, max(2, len(sentences) // 3))
        
        try:
            vectorizer = CountVectorizer(
                stop_words='english',
                max_features=1000,
                min_df=1
            )
            doc_term_matrix = vectorizer.fit_transform(sentences)
            
            lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42,
                max_iter=100
            )
            topic_distributions = lda.fit_transform(doc_term_matrix)
            
            feature_names = vectorizer.get_feature_names_out()
            sentence_topics = np.argmax(topic_distributions, axis=1)
            
            topics = defaultdict(list)
            for idx, topic_id in enumerate(sentence_topics):
                topics[topic_id].append((idx, sentences[idx]))
            
            result = []
            for topic_id, sents in topics.items():
                if len(sents) >= self.min_sentences_per_topic:
                    indices = [i for i, _ in sents]
                    sent_texts = [s for _, s in sents]
                    result.append({
                        'topic_id': topic_id,
                        'keywords': self._extract_topic_keywords(sent_texts),
                        'sentences': sent_texts,
                        'sentence_indices': indices,
                        'size': len(sents)
                    })
            
            result.sort(key=lambda x: x['size'], reverse=True)
            return result[:self.max_topics]
            
        except Exception as e:
            print(f"LDA extraction error: {e}")
            return self.extract_topics_kmeans(sentences, n_topics)

    def extract_topics_kmeans(
        self,
        sentences: List[str],
        num_topics: Optional[int] = None
    ) -> List[Dict]:
        if len(sentences) < self.min_sentences_per_topic * 2:
            return [{
                'topic_id': 0,
                'keywords': self._extract_topic_keywords(sentences),
                'sentences': sentences,
                'sentence_indices': list(range(len(sentences))),
                'size': len(sentences)
            }]
        
        n_topics = num_topics or min(self.max_topics, max(2, len(sentences) // 3))
        
        try:
            tfidf = TfidfVectorizer(
                stop_words='english',
                max_features=1000
            )
            tfidf_matrix = tfidf.fit_transform(sentences)
            
            kmeans = KMeans(
                n_clusters=n_topics,
                random_state=42,
                n_init=10
            )
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            topics = defaultdict(list)
            for idx, label in enumerate(cluster_labels):
                topics[label].append((idx, sentences[idx]))
            
            result = []
            for topic_id, sents in topics.items():
                if len(sents) >= self.min_sentences_per_topic:
                    indices = [i for i, _ in sents]
                    sent_texts = [s for _, s in sents]
                    result.append({
                        'topic_id': topic_id,
                        'keywords': self._extract_topic_keywords(sent_texts),
                        'sentences': sent_texts,
                        'sentence_indices': indices,
                        'size': len(sents)
                    })
            
            result.sort(key=lambda x: x['size'], reverse=True)
            return result[:self.max_topics]
            
        except Exception as e:
            print(f"KMeans extraction error: {e}")
            return [{
                'topic_id': 0,
                'keywords': self._extract_topic_keywords(sentences),
                'sentences': sentences,
                'sentence_indices': list(range(len(sentences))),
                'size': len(sentences)
            }]

    def extract_topics(
        self,
        text: str,
        method: str = 'kmeans',
        num_topics: Optional[int] = None
    ) -> List[Dict]:
        sentences = self._sentence_tokenize(text)
        
        if method == 'lda':
            return self.extract_topics_lda(sentences, num_topics)
        else:
            return self.extract_topics_kmeans(sentences, num_topics)

    def generate_topic_aware_summary(
        self,
        text: str,
        summarizer_fn,
        method: str = 'kmeans',
        num_topics: Optional[int] = None,
        **summary_kwargs
    ) -> Dict:
        topics = self.extract_topics(text, method, num_topics)
        
        topic_summaries = []
        for topic in topics:
            topic_text = ' '.join(topic['sentences'])
            if len(topic_text) < 50:
                continue
            
            try:
                topic_summary = summarizer_fn(topic_text, **summary_kwargs)
                if isinstance(topic_summary, tuple):
                    topic_summary = topic_summary[0]
            except Exception as e:
                topic_summary = topic['sentences'][0] if topic['sentences'] else ''
            
            topic_summaries.append({
                'topic_id': topic['topic_id'],
                'keywords': topic['keywords'],
                'topic_summary': topic_summary,
                'topic_text': topic_text,
                'num_sentences': topic['size']
            })
        
        return {
            'topics': topic_summaries,
            'num_topics': len(topic_summaries),
            'method': method
        }
