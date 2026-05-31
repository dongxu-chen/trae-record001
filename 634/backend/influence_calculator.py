import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
from models import ClusterTopic, InfluenceMetrics
from config import settings

class InfluenceCalculator:
    def __init__(self):
        self.topic_history: Dict[str, List[Dict]] = {}
    
    def calculate_metrics(self, topic: ClusterTopic) -> InfluenceMetrics:
        reach = self._calculate_reach(topic)
        engagement = self._calculate_engagement(topic)
        velocity = self._calculate_velocity(topic)
        momentum = self._calculate_momentum(topic)
        share_score = self._calculate_share_score(topic)
        
        overall = self._compute_overall_score(reach, engagement, velocity, momentum, share_score)
        
        return InfluenceMetrics(
            topic_id=topic.topic_id,
            reach=reach,
            engagement=engagement,
            velocity=velocity,
            momentum=momentum,
            share_score=share_score,
            overall_score=overall
        )
    
    def _calculate_reach(self, topic: ClusterTopic) -> int:
        return topic.size
    
    def _calculate_engagement(self, topic: ClusterTopic) -> float:
        age_hours = (datetime.now() - topic.created_at).total_seconds() / 3600
        if age_hours < 1:
            return 1.0
        
        engagement_rate = topic.size / max(age_hours, 1)
        return min(engagement_rate / 10.0, 1.0)
    
    def _calculate_velocity(self, topic: ClusterTopic) -> float:
        if topic.topic_id not in self.topic_history:
            self.topic_history[topic.topic_id] = []
        
        history = self.topic_history[topic.topic_id]
        if not history:
            velocity = 1.0
        else:
            last_size = history[-1]['size']
            time_diff = (datetime.now() - history[-1]['time']).total_seconds() / 3600
            if time_diff > 0:
                velocity = (topic.size - last_size) / time_diff
            else:
                velocity = 0
        
        self.topic_history[topic.topic_id].append({
            'time': datetime.now(),
            'size': topic.size,
            'shares': getattr(topic, 'total_shares', 0),
            'likes': getattr(topic, 'total_likes', 0),
            'comments': getattr(topic, 'total_comments', 0)
        })
        
        if len(self.topic_history[topic.topic_id]) > 10:
            self.topic_history[topic.topic_id] = self.topic_history[topic.topic_id][-10:]
        
        return max(velocity, 0)
    
    def _calculate_momentum(self, topic: ClusterTopic) -> float:
        if topic.topic_id not in self.topic_history:
            return 0.5
        
        history = self.topic_history[topic.topic_id]
        if len(history) < 3:
            return 0.5
        
        sizes = [h['size'] for h in history[-5:]]
        if len(sizes) < 2:
            return 0.5
        
        changes = [sizes[i] - sizes[i-1] for i in range(1, len(sizes))]
        momentum = sum(changes) / len(changes)
        
        return min(max(momentum / 5.0, 0), 1.0)
    
    def _calculate_share_score(self, topic: ClusterTopic) -> float:
        total_shares = getattr(topic, 'total_shares', 0)
        total_likes = getattr(topic, 'total_likes', 0)
        total_comments = getattr(topic, 'total_comments', 0)
        
        if topic.size == 0:
            return 0.0
        
        avg_shares_per_article = total_shares / topic.size
        avg_likes_per_article = total_likes / topic.size
        avg_comments_per_article = total_comments / topic.size
        
        shares_norm = min(avg_shares_per_article / 1000.0, 1.0)
        likes_norm = min(avg_likes_per_article / 5000.0, 1.0)
        comments_norm = min(avg_comments_per_article / 500.0, 1.0)
        
        social_score = (
            shares_norm * 0.5 +
            likes_norm * 0.3 +
            comments_norm * 0.2
        )
        
        history = self.topic_history.get(topic.topic_id, [])
        if len(history) >= 2:
            recent = history[-1]
            previous = history[-2]
            
            share_delta = recent.get('shares', 0) - previous.get('shares', 0)
            like_delta = recent.get('likes', 0) - previous.get('likes', 0)
            comment_delta = recent.get('comments', 0) - previous.get('comments', 0)
            
            time_diff = (recent['time'] - previous['time']).total_seconds() / 3600
            if time_diff > 0:
                share_velocity = min(share_delta / max(time_diff, 0.1) / 100.0, 1.0)
                like_velocity = min(like_delta / max(time_diff, 0.1) / 500.0, 1.0)
                comment_velocity = min(comment_delta / max(time_diff, 0.1) / 50.0, 1.0)
                
                velocity_score = (
                    share_velocity * 0.5 +
                    like_velocity * 0.3 +
                    comment_velocity * 0.2
                )
                
                social_score = social_score * 0.6 + velocity_score * 0.4
        
        return round(social_score, 4)
    
    def _compute_overall_score(self, reach: int, engagement: float, 
                               velocity: float, momentum: float,
                               share_score: float) -> float:
        reach_norm = min(reach / 100.0, 1.0)
        velocity_norm = min(velocity / 10.0, 1.0)
        
        score = (
            reach_norm * settings.REACH_WEIGHT +
            engagement * settings.ENGAGEMENT_WEIGHT +
            velocity_norm * settings.VELOCITY_WEIGHT +
            momentum * settings.MOMENTUM_WEIGHT +
            share_score * settings.SHARE_WEIGHT
        )
        
        return round(score, 4)
    
    def detect_burst(self, topic: ClusterTopic) -> bool:
        if topic.topic_id not in self.topic_history:
            return False
        
        history = self.topic_history[topic.topic_id]
        if len(history) < 3:
            return False
        
        recent_sizes = [h['size'] for h in history[-3:]]
        avg_growth = sum(
            recent_sizes[i] - recent_sizes[i-1] 
            for i in range(1, len(recent_sizes))
        ) / (len(recent_sizes) - 1)
        
        return avg_growth >= settings.BURST_THRESHOLD
    
    def detect_decay(self, topic: ClusterTopic) -> bool:
        if topic.topic_id not in self.topic_history:
            return False
        
        history = self.topic_history[topic.topic_id]
        if len(history) < 5:
            return False
        
        recent_velocity = self._calculate_velocity(topic)
        return recent_velocity < settings.DECAY_THRESHOLD
    
    def get_topic_trend(self, topic_id: str, hours: int = 24) -> List[Dict]:
        if topic_id not in self.topic_history:
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            h for h in self.topic_history[topic_id]
            if h['time'] >= cutoff
        ]
