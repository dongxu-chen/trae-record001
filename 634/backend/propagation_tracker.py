import numpy as np
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from models import ClusterTopic, NewsArticle, PropagationPath, PropagationNode
from config import settings
import logging

logger = logging.getLogger(__name__)

class PropagationTracker:
    def __init__(self):
        self.article_details: Dict[str, NewsArticle] = {}
        self.topic_articles: Dict[str, List[str]] = defaultdict(list)
        self.propagation_cache: Dict[str, PropagationPath] = {}
        
    def add_article(self, article: NewsArticle, topic_id: str):
        self.article_details[article.id] = article
        self.topic_articles[topic_id].append(article.id)
        
    def analyze_propagation_path(self, topic_id: str, topic: ClusterTopic) -> Optional[PropagationPath]:
        if topic_id not in self.topic_articles:
            return None
            
        article_ids = self.topic_articles[topic_id]
        if len(article_ids) < 2:
            return None
            
        articles = [
            self.article_details[aid] 
            for aid in article_ids 
            if aid in self.article_details
        ]
        
        if not articles:
            return None
            
        sorted_articles = sorted(articles, key=lambda a: a.publish_time)
        
        ignition_points = self._identify_ignition_points(sorted_articles)
        propagation_tree = self._build_propagation_tree(sorted_articles, ignition_points)
        key_influencers = self._identify_key_influencers(sorted_articles)
        
        max_depth = max(
            (node.get('level', 0) for node in propagation_tree),
            default=0
        )
        
        propagation_path = PropagationPath(
            topic_id=topic_id,
            topic_name=topic.name,
            ignition_points=[
                PropagationNode(
                    article_id=a.id,
                    title=a.title,
                    source=a.source,
                    publish_time=a.publish_time,
                    share_count=a.share_count,
                    like_count=a.like_count,
                    comment_count=a.comment_count,
                    influence_score=self._calculate_article_influence(a),
                    is_ignition_point=True,
                    propagation_level=0
                )
                for a in ignition_points
            ],
            propagation_tree=propagation_tree,
            total_propagation_depth=max_depth,
            key_influencers=key_influencers,
            analyzed_at=datetime.now()
        )
        
        self.propagation_cache[topic_id] = propagation_path
        return propagation_path
        
    def _identify_ignition_points(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        if len(articles) < 2:
            return articles
            
        time_diffs = []
        for i in range(1, len(articles)):
            diff = (articles[i].publish_time - articles[i-1].publish_time).total_seconds()
            time_diffs.append(diff)
            
        if not time_diffs:
            return [articles[0]]
            
        mean_diff = np.mean(time_diffs)
        std_diff = np.std(time_diffs) if len(time_diffs) > 1 else 1
        
        ignition_points = []
        potential_ignitions = [articles[0]]
        
        for i, diff in enumerate(time_diffs, 1):
            if diff > mean_diff + std_diff * 2:
                ignition_points.extend(potential_ignitions)
                potential_ignitions = [articles[i]]
            else:
                potential_ignitions.append(articles[i])
                
        ignition_points.extend(potential_ignitions)
        
        ignition_points_with_score = []
        for article in ignition_points:
            early_bonus = 1.0 if article == articles[0] else 0.5
            social_score = (
                article.share_count + 
                article.like_count * 0.3 + 
                article.comment_count * 0.5
            )
            total_score = social_score * early_bonus
            ignition_points_with_score.append((total_score, article))
            
        ignition_points_with_score.sort(key=lambda x: x[0], reverse=True)
        
        top_count = min(3, len(ignition_points_with_score))
        return [a for _, a in ignition_points_with_score[:top_count]]
        
    def _build_propagation_tree(self, articles: List[NewsArticle], 
                                 ignition_points: List[NewsArticle]) -> List[Dict]:
        tree = []
        ignition_ids = {a.id for a in ignition_points}
        
        for level, article in enumerate(articles):
            is_ignition = article.id in ignition_ids
            actual_level = 0 if is_ignition else level
            
            influence = self._calculate_article_influence(article)
            
            node = {
                "article_id": article.id,
                "title": article.title,
                "source": article.source,
                "publish_time": article.publish_time.isoformat(),
                "share_count": article.share_count,
                "like_count": article.like_count,
                "comment_count": article.comment_count,
                "influence_score": influence,
                "level": actual_level,
                "is_ignition": is_ignition,
                "children": []
            }
            tree.append(node)
            
        for i, node in enumerate(tree):
            if node["is_ignition"]:
                continue
                
            publish_time = datetime.fromisoformat(node["publish_time"])
            
            best_parent = None
            best_score = -1
            
            for j, parent in enumerate(tree[:i]):
                parent_time = datetime.fromisoformat(parent["publish_time"])
                time_diff = (publish_time - parent_time).total_seconds()
                
                if time_diff <= 0:
                    continue
                    
                influence_similarity = (
                    1.0 / (1.0 + abs(node["influence_score"] - parent["influence_score"]))
                )
                time_factor = 1.0 / (1.0 + time_diff / 3600)
                
                score = influence_similarity * time_factor
                
                if score > best_score:
                    best_score = score
                    best_parent = j
                    
            if best_parent is not None and best_score > 0.1:
                tree[best_parent]["children"].append(node["article_id"])
                
        return tree
        
    def _identify_key_influencers(self, articles: List[NewsArticle]) -> List[Dict]:
        if not articles:
            return []
            
        influencer_scores = []
        for article in articles:
            influence = self._calculate_article_influence(article)
            
            time_position = (article.publish_time - articles[0].publish_time).total_seconds()
            total_duration = (articles[-1].publish_time - articles[0].publish_time).total_seconds()
            early_factor = 1.0 - (time_position / max(total_duration, 1))
            
            final_score = influence * (0.7 + early_factor * 0.3)
            
            influencer_scores.append({
                "article_id": article.id,
                "title": article.title,
                "source": article.source,
                "publish_time": article.publish_time.isoformat(),
                "influence_score": influence,
                "final_score": final_score,
                "share_count": article.share_count,
                "like_count": article.like_count,
                "comment_count": article.comment_count
            })
            
        influencer_scores.sort(key=lambda x: x["final_score"], reverse=True)
        return influencer_scores[:5]
        
    def _calculate_article_influence(self, article: NewsArticle) -> float:
        shares = article.share_count
        likes = article.like_count
        comments = article.comment_count
        
        share_norm = min(shares / 1000.0, 1.0)
        like_norm = min(likes / 5000.0, 1.0)
        comment_norm = min(comments / 500.0, 1.0)
        
        influence = share_norm * 0.5 + like_norm * 0.3 + comment_norm * 0.2
        return round(influence, 4)
        
    def get_propagation_path(self, topic_id: str) -> Optional[PropagationPath]:
        return self.propagation_cache.get(topic_id)
        
    def get_ignition_articles(self, topic_id: str) -> List[NewsArticle]:
        if topic_id not in self.topic_articles:
            return []
            
        article_ids = self.topic_articles[topic_id]
        articles = [
            self.article_details[aid] 
            for aid in article_ids 
            if aid in self.article_details
        ]
        
        if len(articles) < 2:
            return articles
            
        return self._identify_ignition_points(articles)
