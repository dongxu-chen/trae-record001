import logging
import os
import pickle
import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import gensim
    from gensim import corpora, models
    from gensim.models.coherencemodel import CoherenceModel
    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False
    logger.warning("Gensim not installed. Will use fallback topic modeling.")

from config import Config
from .text_processor import TextProcessor


class TopicModeler:
    def __init__(self, num_topics: int = None, num_keywords: int = None):
        self.text_processor = TextProcessor()
        self.num_keywords = num_keywords or Config.LDA_NUM_KEYWORDS
        
        self.dictionary = None
        self.lda_model = None
        self.is_trained = False
        self.optimal_num_topics = num_topics or Config.LDA_NUM_TOPICS
        self.training_metadata = {}
        
        self.model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.fallback_topics = {
            0: {'keywords': ['产品', '质量', '服务', '体验', '满意'], 'name': '产品服务'},
            1: {'keywords': ['公司', '政策', '管理', '员工', '工作'], 'name': '企业管理'},
            2: {'keywords': ['事件', '新闻', '热点', '讨论', '关注'], 'name': '热点事件'},
            3: {'keywords': ['价格', '性价比', '便宜', '贵', '优惠'], 'name': '价格讨论'},
            4: {'keywords': ['功能', '设计', '使用', '方便', '操作'], 'name': '功能体验'},
        }
        
        self.topic_coherence_history = []
    
    def _calculate_optimal_topics(self, num_docs: int) -> int:
        min_topics = max(2, int(math.log2(num_docs)))
        max_topics = min(20, int(math.sqrt(num_docs) * 2))
        
        if num_docs < 50:
            max_topics = min(10, max_topics)
        elif num_docs < 200:
            max_topics = min(15, max_topics)
        
        optimal = max(min_topics, min(max_topics, int(num_docs / 20)))
        
        logger.info(f"Calculated optimal topics: {optimal} (range: {min_topics}-{max_topics}) for {num_docs} documents")
        return optimal
    
    def _preprocess_texts(self, texts: List[str]) -> List[List[str]]:
        processed_texts = [self.text_processor.tokenize(text) for text in texts]
        processed_texts = [text for text in processed_texts if len(text) > 2]
        return processed_texts
    
    def _compute_perplexity(self, model, corpus) -> float:
        try:
            return model.log_perplexity(corpus)
        except:
            return float('inf')
    
    def _compute_coherence(self, model, texts, dictionary) -> float:
        try:
            coherence_model = CoherenceModel(
                model=model,
                texts=texts,
                dictionary=dictionary,
                coherence='c_v'
            )
            return coherence_model.get_coherence()
        except Exception as e:
            logger.warning(f"Failed to compute coherence: {e}")
            return 0.0
    
    def find_optimal_topics(
        self, 
        texts: List[str], 
        min_topics: int = None, 
        max_topics: int = None,
        step: int = 1
    ) -> Dict:
        if not GENSIM_AVAILABLE:
            logger.warning("Gensim not available, cannot find optimal topics")
            return {'optimal_num_topics': self.optimal_num_topics, 'method': 'fallback'}
        
        processed_texts = self._preprocess_texts(texts)
        if len(processed_texts) < 10:
            logger.warning("Not enough texts to find optimal topics")
            return {'optimal_num_topics': self.optimal_num_topics, 'method': 'insufficient_data'}
        
        num_docs = len(processed_texts)
        
        if min_topics is None:
            min_topics = max(2, int(math.log2(num_docs)))
        if max_topics is None:
            max_topics = min(20, int(math.sqrt(num_docs) * 2))
        
        min_topics = max(2, min_topics)
        max_topics = max(min_topics + 1, min(max_topics, 20))
        
        dictionary = corpora.Dictionary(processed_texts)
        dictionary.filter_extremes(no_below=2, no_above=0.8)
        corpus = [dictionary.doc2bow(text) for text in processed_texts]
        
        results = []
        for num_topics in range(min_topics, max_topics + 1, step):
            try:
                model = models.LdaModel(
                    corpus=corpus,
                    id2word=dictionary,
                    num_topics=num_topics,
                    random_state=42,
                    update_every=1,
                    chunksize=100,
                    passes=5,
                    alpha='auto',
                    per_word_topics=True
                )
                
                perplexity = self._compute_perplexity(model, corpus)
                coherence = self._compute_coherence(model, processed_texts, dictionary)
                
                results.append({
                    'num_topics': num_topics,
                    'perplexity': perplexity,
                    'coherence': coherence,
                    'combined_score': coherence - (perplexity / 100) if perplexity != float('inf') else coherence
                })
                
                logger.info(f"Topics: {num_topics}, Perplexity: {perplexity:.4f}, Coherence: {coherence:.4f}")
                
            except Exception as e:
                logger.warning(f"Failed to train model with {num_topics} topics: {e}")
                continue
        
        if not results:
            return {'optimal_num_topics': self.optimal_num_topics, 'method': 'fallback'}
        
        best_coherence = max(results, key=lambda x: x['coherence'])
        best_perplexity = min(results, key=lambda x: x['perplexity'])
        best_combined = max(results, key=lambda x: x['combined_score'])
        
        optimal_num_topics = best_combined['num_topics']
        
        self.topic_coherence_history = results
        
        return {
            'optimal_num_topics': optimal_num_topics,
            'method': 'grid_search',
            'best_coherence': best_coherence,
            'best_perplexity': best_perplexity,
            'best_combined': best_combined,
            'all_results': results,
            'num_docs': num_docs,
            'search_range': {'min': min_topics, 'max': max_topics}
        }
    
    def train(self, texts: List[str], save: bool = True, auto_detect_topics: bool = True):
        if not texts or len(texts) < 10:
            logger.warning("Not enough texts to train LDA model")
            return False
        
        if not GENSIM_AVAILABLE:
            logger.warning("Gensim not available, cannot train LDA model")
            return False
        
        try:
            processed_texts = self._preprocess_texts(texts)
            
            if len(processed_texts) < 5:
                logger.warning("Not enough valid texts after preprocessing")
                return False
            
            if auto_detect_topics:
                optimal_result = self.find_optimal_topics(texts)
                self.optimal_num_topics = optimal_result['optimal_num_topics']
                self.training_metadata = optimal_result
                logger.info(f"Auto-detected optimal topics: {self.optimal_num_topics}")
            else:
                self.optimal_num_topics = self._calculate_optimal_topics(len(processed_texts))
            
            self.dictionary = corpora.Dictionary(processed_texts)
            self.dictionary.filter_extremes(no_below=2, no_above=0.8)
            
            corpus = [self.dictionary.doc2bow(text) for text in processed_texts]
            
            self.lda_model = models.LdaModel(
                corpus=corpus,
                id2word=self.dictionary,
                num_topics=self.optimal_num_topics,
                random_state=42,
                update_every=1,
                chunksize=100,
                passes=10,
                alpha='auto',
                per_word_topics=True
            )
            
            self.is_trained = True
            
            if save:
                self._save_model()
            
            logger.info(f"LDA model trained with {self.optimal_num_topics} topics")
            return True
            
        except Exception as e:
            logger.error(f"Failed to train LDA model: {e}")
            return False
    
    def _save_model(self):
        try:
            if self.lda_model and self.dictionary:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                model_path = os.path.join(self.model_dir, f'lda_model_{timestamp}')
                dict_path = os.path.join(self.model_dir, f'dictionary_{timestamp}')
                
                self.lda_model.save(model_path)
                self.dictionary.save(dict_path)
                
                latest_model_path = os.path.join(self.model_dir, 'lda_model_latest')
                latest_dict_path = os.path.join(self.model_dir, 'dictionary_latest')
                
                self.lda_model.save(latest_model_path)
                self.dictionary.save(latest_dict_path)
                
                metadata_path = os.path.join(self.model_dir, f'training_metadata_{timestamp}.pkl')
                with open(metadata_path, 'wb') as f:
                    pickle.dump({
                        'optimal_num_topics': self.optimal_num_topics,
                        'training_metadata': self.training_metadata,
                        'topic_coherence_history': self.topic_coherence_history
                    }, f)
                
                logger.info(f"LDA model saved to {model_path}")
        except Exception as e:
            logger.error(f"Failed to save LDA model: {e}")
    
    def load_model(self, model_path: str = None, dict_path: str = None):
        if not GENSIM_AVAILABLE:
            logger.warning("Gensim not available, cannot load LDA model")
            return False
        
        try:
            if model_path is None:
                model_path = os.path.join(self.model_dir, 'lda_model_latest')
            if dict_path is None:
                dict_path = os.path.join(self.model_dir, 'dictionary_latest')
            
            if not os.path.exists(model_path) or not os.path.exists(dict_path):
                logger.warning("Saved LDA model not found")
                return False
            
            self.lda_model = models.LdaModel.load(model_path)
            self.dictionary = corpora.Dictionary.load(dict_path)
            self.is_trained = True
            self.optimal_num_topics = self.lda_model.num_topics
            
            logger.info(f"LDA model loaded successfully with {self.optimal_num_topics} topics")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load LDA model: {e}")
            return False
    
    def get_topics(self, text: str) -> List[Dict]:
        if not text or not text.strip():
            return []
        
        if GENSIM_AVAILABLE and self.is_trained and self.lda_model and self.dictionary:
            return self._get_topics_gensim(text)
        else:
            return self._get_topics_fallback(text)
    
    def _get_topics_gensim(self, text: str) -> List[Dict]:
        try:
            tokens = self.text_processor.tokenize(text)
            if not tokens:
                return []
            
            bow = self.dictionary.doc2bow(tokens)
            topic_distribution = self.lda_model.get_document_topics(bow)
            
            topics = []
            for topic_id, weight in topic_distribution:
                keywords = self._get_topic_keywords(topic_id)
                topics.append({
                    'topic_id': topic_id,
                    'keywords': keywords,
                    'weight': round(float(weight), 4)
                })
            
            topics.sort(key=lambda x: x['weight'], reverse=True)
            return topics
            
        except Exception as e:
            logger.error(f"Failed to get topics with gensim: {e}")
            return self._get_topics_fallback(text)
    
    def _get_topic_keywords(self, topic_id: int) -> List[str]:
        try:
            topic_terms = self.lda_model.show_topic(topic_id, topn=self.num_keywords)
            return [term for term, weight in topic_terms]
        except:
            return []
    
    def _get_topics_fallback(self, text: str) -> List[Dict]:
        tokens = self.text_processor.tokenize(text)
        if not tokens:
            return []
        
        token_set = set(tokens)
        topics = []
        
        for topic_id, topic_info in self.fallback_topics.items():
            keyword_matches = len(token_set & set(topic_info['keywords']))
            if keyword_matches > 0:
                weight = keyword_matches / len(topic_info['keywords'])
                topics.append({
                    'topic_id': topic_id,
                    'keywords': topic_info['keywords'],
                    'weight': round(weight, 4),
                    'name': topic_info['name']
                })
        
        topics.sort(key=lambda x: x['weight'], reverse=True)
        return topics[:3]
    
    def get_batch_topics(self, texts: List[str]) -> List[List[Dict]]:
        return [self.get_topics(text) for text in texts]
    
    def get_all_topics(self) -> List[Dict]:
        if GENSIM_AVAILABLE and self.is_trained and self.lda_model:
            topics = []
            for topic_id in range(self.optimal_num_topics):
                keywords = self._get_topic_keywords(topic_id)
                topics.append({
                    'topic_id': topic_id,
                    'keywords': keywords,
                    'name': f'主题_{topic_id + 1}'
                })
            return topics
        else:
            return [
                {'topic_id': tid, 'keywords': info['keywords'], 'name': info['name']}
                for tid, info in self.fallback_topics.items()
            ]
    
    def extract_keywords(self, texts: List[str], top_k: int = 20) -> List[Tuple[str, int]]:
        all_tokens = []
        for text in texts:
            tokens = self.text_processor.tokenize(text)
            all_tokens.extend(tokens)
        
        word_freq = {}
        for token in all_tokens:
            word_freq[token] = word_freq.get(token, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:top_k]
    
    def get_topic_coherence(self, texts: List[str]) -> float:
        if not GENSIM_AVAILABLE or not self.is_trained or not self.lda_model:
            return 0.0
        
        try:
            processed_texts = self._preprocess_texts(texts)
            processed_texts = [text for text in processed_texts if len(text) > 0]
            
            if not processed_texts:
                return 0.0
            
            coherence_model = CoherenceModel(
                model=self.lda_model,
                texts=processed_texts,
                dictionary=self.dictionary,
                coherence='c_v'
            )
            return coherence_model.get_coherence()
        except Exception as e:
            logger.error(f"Failed to compute topic coherence: {e}")
            return 0.0
    
    def get_topic_distribution(self, texts: List[str]) -> Dict:
        if not self.is_trained or not self.lda_model:
            return {}
        
        topic_counts = defaultdict(int)
        
        for text in texts:
            topics = self.get_topics(text)
            if topics:
                top_topic = topics[0]
                topic_counts[top_topic['topic_id']] += 1
        
        total = sum(topic_counts.values())
        if total == 0:
            return {}
        
        return {
            f'topic_{tid}': {
                'count': count,
                'percentage': round(count / total, 4)
            }
            for tid, count in topic_counts.items()
        }
    
    def merge_topics(self, texts: List[str], threshold: float = 0.7) -> List[Dict]:
        if not self.is_trained or not self.lda_model:
            return []
        
        all_topics = self.get_all_topics()
        if len(all_topics) < 2:
            return all_topics
        
        topic_similarities = []
        
        for i, topic1 in enumerate(all_topics):
            for j, topic2 in enumerate(all_topics):
                if i >= j:
                    continue
                
                keywords1 = set(topic1['keywords'])
                keywords2 = set(topic2['keywords'])
                
                if keywords1 and keywords2:
                    similarity = len(keywords1 & keywords2) / len(keywords1 | keywords2)
                    topic_similarities.append({
                        'topic1': i,
                        'topic2': j,
                        'similarity': similarity
                    })
        
        mergeable = [s for s in topic_similarities if s['similarity'] >= threshold]
        
        return {
            'total_topics': len(all_topics),
            'mergeable_pairs': mergeable,
            'similarity_matrix': topic_similarities
        }
