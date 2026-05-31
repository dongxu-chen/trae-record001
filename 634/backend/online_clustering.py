import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid
from config import settings
from models import ClusterTopic, TopicLifeCycle, NewsArticle
from text_embedding import TextEmbedding

class OnlineTopicCluster:
    def __init__(self, embedding_model: TextEmbedding):
        self.embedding = embedding_model
        self.topics: Dict[str, ClusterTopic] = {}
        self.article_vectors: Dict[str, np.ndarray] = {}
        self.article_topic_map: Dict[str, str] = {}
        self.topic_density_cache: Dict[str, float] = {}
    
    def calculate_topic_density(self, topic_id: str) -> float:
        if topic_id in self.topic_density_cache:
            return self.topic_density_cache[topic_id]
        
        topic = self.topics.get(topic_id)
        if not topic or topic.size < 2:
            density = 0.5
            self.topic_density_cache[topic_id] = density
            return density
        
        vectors = [
            self.article_vectors[aid] 
            for aid in topic.articles 
            if aid in self.article_vectors
        ]
        
        if len(vectors) < 2:
            density = 0.5
            self.topic_density_cache[topic_id] = density
            return density
        
        centroid = np.array(topic.centroid)
        similarities = [
            self.embedding.cosine_similarity(vec, centroid)
            for vec in vectors
        ]
        
        density = np.mean(similarities)
        self.topic_density_cache[topic_id] = density
        return density
    
    def get_adaptive_threshold(self, topic: ClusterTopic) -> float:
        if not settings.ADAPTIVE_THRESHOLD_ENABLED:
            return settings.CLUSTER_THRESHOLD
        
        base_threshold = settings.CLUSTER_THRESHOLD
        
        size_factor = min(topic.size / 50.0, 1.0)
        density = self.calculate_topic_density(topic.topic_id)
        density_factor = density
        
        lifecycle_factor = 0.5
        if topic.lifecycle == TopicLifeCycle.EMERGING:
            lifecycle_factor = 0.0
        elif topic.lifecycle == TopicLifeCycle.GROWING:
            lifecycle_factor = 0.3
        elif topic.lifecycle == TopicLifeCycle.BURSTING:
            lifecycle_factor = 0.5
        elif topic.lifecycle == TopicLifeCycle.STABLE:
            lifecycle_factor = 0.7
        elif topic.lifecycle == TopicLifeCycle.DECLINING:
            lifecycle_factor = 0.9
        
        adjustment = (
            size_factor * settings.ADAPTIVE_SIZE_WEIGHT +
            density_factor * settings.ADAPTIVE_DENSITY_WEIGHT +
            lifecycle_factor * settings.ADAPTIVE_LIFECYCLE_WEIGHT
        )
        
        threshold_range = settings.ADAPTIVE_THRESHOLD_MAX - settings.ADAPTIVE_THRESHOLD_MIN
        adaptive_threshold = settings.ADAPTIVE_THRESHOLD_MIN + adjustment * threshold_range
        
        return adaptive_threshold
        
    def _generate_topic_name(self, keywords: List[str]) -> str:
        if len(keywords) >= 2:
            return f"{keywords[0]}_{keywords[1]}"
        return keywords[0] if keywords else "unknown_topic"
    
    def _calculate_trend_score(self, topic: ClusterTopic) -> float:
        time_diff = (datetime.now() - topic.created_at).total_seconds() / 3600
        if time_diff < 1:
            return 1.0
        growth_rate = topic.size / max(time_diff, 1)
        return min(growth_rate, 5.0)
    
    def _update_lifecycle(self, topic: ClusterTopic) -> TopicLifeCycle:
        age_hours = (datetime.now() - topic.created_at).total_seconds() / 3600
        recent_growth = topic.burst_count
        
        if age_hours < 2 and topic.size < 10:
            return TopicLifeCycle.EMERGING
        elif recent_growth >= settings.BURST_THRESHOLD * topic.size:
            return TopicLifeCycle.BURSTING
        elif topic.trend_score > 1.5:
            return TopicLifeCycle.GROWING
        elif topic.trend_score < settings.DECAY_THRESHOLD:
            return TopicLifeCycle.DECLINING
        else:
            return TopicLifeCycle.STABLE
    
    def find_closest_topic(self, vector: np.ndarray) -> Tuple[Optional[str], float, float]:
        best_topic_id = None
        best_similarity = 0
        best_threshold = settings.CLUSTER_THRESHOLD
        
        for topic_id, topic in self.topics.items():
            sim = self.embedding.cosine_similarity(vector, np.array(topic.centroid))
            adaptive_threshold = self.get_adaptive_threshold(topic)
            if sim > best_similarity:
                best_similarity = sim
                best_topic_id = topic_id
                best_threshold = adaptive_threshold
        
        return best_topic_id, best_similarity, best_threshold
    
    def add_article(self, article: NewsArticle) -> Optional[str]:
        text = f"{article.title} {article.content}"
        vector = self.embedding.get_embedding(text)
        
        self.article_vectors[article.id] = vector
        
        closest_topic_id, similarity, threshold = self.find_closest_topic(vector)
        
        if closest_topic_id and similarity >= threshold:
            self._add_to_topic(closest_topic_id, article, vector)
            return closest_topic_id
        else:
            new_topic_id = self._create_new_topic(article, vector)
            return new_topic_id
    
    def _add_to_topic(self, topic_id: str, article: NewsArticle, vector: np.ndarray):
        topic = self.topics[topic_id]
        
        topic.articles.append(article.id)
        topic.size = len(topic.articles)
        
        topic.total_shares += getattr(article, 'share_count', 0)
        topic.total_likes += getattr(article, 'like_count', 0)
        topic.total_comments += getattr(article, 'comment_count', 0)
        
        n = len(topic.articles)
        old_centroid = np.array(topic.centroid)
        new_centroid = (old_centroid * (n - 1) + vector) / n
        topic.centroid = new_centroid.tolist()
        
        topic.updated_at = datetime.now()
        topic.burst_count += 1
        
        article_texts = [article.title + " " + article.content]
        for aid in topic.articles[-5:]:
            if aid in self.article_vectors:
                pass
        topic.keywords = self.embedding.get_keywords_tfidf(
            article_texts, settings.TOPIC_KEYWORDS_COUNT
        )
        topic.name = self._generate_topic_name(topic.keywords)
        
        topic.trend_score = self._calculate_trend_score(topic)
        topic.lifecycle = self._update_lifecycle(topic)
        topic.influence_score = self._calculate_influence(topic)
        
        if topic_id in self.topic_density_cache:
            del self.topic_density_cache[topic_id]
        
        self.article_topic_map[article.id] = topic_id
    
    def _create_new_topic(self, article: NewsArticle, vector: np.ndarray) -> str:
        topic_id = str(uuid.uuid4())
        
        article_texts = [article.title + " " + article.content]
        keywords = self.embedding.get_keywords_tfidf(
            article_texts, settings.TOPIC_KEYWORDS_COUNT
        )
        
        topic = ClusterTopic(
            topic_id=topic_id,
            name=self._generate_topic_name(keywords),
            keywords=keywords,
            articles=[article.id],
            centroid=vector.tolist(),
            size=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            lifecycle=TopicLifeCycle.EMERGING,
            influence_score=0.1,
            trend_score=1.0,
            burst_count=1,
            total_shares=getattr(article, 'share_count', 0),
            total_likes=getattr(article, 'like_count', 0),
            total_comments=getattr(article, 'comment_count', 0)
        )
        
        self.topics[topic_id] = topic
        self.article_topic_map[article.id] = topic_id
        
        return topic_id
    
    def _calculate_influence(self, topic: ClusterTopic) -> float:
        size_factor = min(topic.size / 100.0, 1.0)
        recency_factor = 1.0 / (1.0 + (datetime.now() - topic.updated_at).total_seconds() / 86400)
        trend_factor = min(topic.trend_score / 2.0, 1.0)
        
        influence = (size_factor * 0.4 + recency_factor * 0.3 + trend_factor * 0.3)
        return influence
    
    def get_topic_articles(self, topic_id: str) -> List[str]:
        if topic_id in self.topics:
            return self.topics[topic_id].articles
        return []
    
    def get_active_topics(self, min_size: int = None) -> List[ClusterTopic]:
        min_size = min_size or settings.MIN_CLUSTER_SIZE
        return [t for t in self.topics.values() if t.size >= min_size]
    
    def merge_small_topics(self):
        topics_list = list(self.topics.values())
        merged = set()
        
        for i, t1 in enumerate(topics_list):
            if t1.topic_id in merged:
                continue
            for t2 in topics_list[i+1:]:
                if t2.topic_id in merged:
                    continue
                
                sim = self.embedding.cosine_similarity(
                    np.array(t1.centroid), np.array(t2.centroid)
                )
                
                threshold_t1 = self.get_adaptive_threshold(t1)
                threshold_t2 = self.get_adaptive_threshold(t2)
                merge_threshold = min(threshold_t1, threshold_t2)
                
                if sim >= merge_threshold:
                    self._merge_topics(t1.topic_id, t2.topic_id)
                    merged.add(t2.topic_id)
    
    def _merge_topics(self, t1_id: str, t2_id: str):
        t1 = self.topics[t1_id]
        t2 = self.topics[t2_id]
        
        for aid in t2.articles:
            if aid not in t1.articles:
                t1.articles.append(aid)
                self.article_topic_map[aid] = t1_id
        
        t1.size = len(t1.articles)
        
        t1.total_shares += t2.total_shares
        t1.total_likes += t2.total_likes
        t1.total_comments += t2.total_comments
        
        v1 = np.array(t1.centroid)
        v2 = np.array(t2.centroid)
        t1.centroid = ((v1 * t1.size) + (v2 * t2.size)) / (t1.size + t2.size)
        t1.centroid = t1.centroid.tolist()
        
        all_keywords = list(set(t1.keywords + t2.keywords))
        t1.keywords = all_keywords[:settings.TOPIC_KEYWORDS_COUNT]
        
        t1.updated_at = max(t1.updated_at, t2.updated_at)
        t1.burst_count += t2.burst_count
        t1.trend_score = self._calculate_trend_score(t1)
        t1.lifecycle = self._update_lifecycle(t1)
        t1.influence_score = self._calculate_influence(t1)
        
        if t1_id in self.topic_density_cache:
            del self.topic_density_cache[t1_id]
        if t2_id in self.topic_density_cache:
            del self.topic_density_cache[t2_id]
        
        del self.topics[t2_id]
