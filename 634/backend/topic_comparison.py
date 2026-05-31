import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from models import ClusterTopic, TopicComparisonResult, TopicComparisonItem
from config import settings
import logging

logger = logging.getLogger(__name__)

class TopicComparisonEngine:
    def __init__(self):
        self.topic_history: Dict[str, List[Dict]] = defaultdict(list)
        
    def record_topic_state(self, topic: ClusterTopic, influence_metrics: Dict):
        topic_id = topic.topic_id
        state = {
            "timestamp": datetime.now(),
            "size": topic.size,
            "lifecycle": topic.lifecycle.value,
            "influence_score": topic.influence_score,
            "trend_score": topic.trend_score,
            "total_shares": getattr(topic, 'total_shares', 0),
            "total_likes": getattr(topic, 'total_likes', 0),
            "total_comments": getattr(topic, 'total_comments', 0),
            "velocity": influence_metrics.get('velocity', 0),
            "momentum": influence_metrics.get('momentum', 0),
            "share_score": influence_metrics.get('share_score', 0)
        }
        self.topic_history[topic_id].append(state)
        
    def compare_topics(self, topic_ids: List[str], 
                        time_range_hours: Optional[int] = None) -> Optional[TopicComparisonResult]:
        if len(topic_ids) < 2:
            return None
            
        topics_data = []
        for topic_id in topic_ids:
            if topic_id not in self.topic_history:
                continue
                
            history = self.topic_history[topic_id]
            if not history:
                continue
                
            if time_range_hours:
                cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
                history = [h for h in history if h["timestamp"] >= cutoff_time]
                
            if not history:
                continue
                
            comparison_item = self._build_comparison_item(topic_id, history)
            topics_data.append(comparison_item)
            
        if len(topics_data) < 2:
            return None
            
        time_range_start = min(
            (item.lifecycle_timeline[0]["timestamp"] for item in topics_data if item.lifecycle_timeline),
            default=datetime.now()
        )
        time_range_end = max(
            (item.lifecycle_timeline[-1]["timestamp"] for item in topics_data if item.lifecycle_timeline),
            default=datetime.now()
        )
        
        metrics = self._calculate_comparison_metrics(topics_data)
        
        result = TopicComparisonResult(
            comparison_id=str(uuid.uuid4()),
            topics=topics_data,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            metrics=metrics,
            created_at=datetime.now()
        )
        
        return result
        
    def _build_comparison_item(self, topic_id: str, history: List[Dict]) -> TopicComparisonItem:
        lifecycle_timeline = []
        size_history = []
        influence_history = []
        social_history = []
        
        current_lifecycle = None
        for state in history:
            timestamp = state["timestamp"]
            
            if state["lifecycle"] != current_lifecycle:
                current_lifecycle = state["lifecycle"]
                lifecycle_timeline.append({
                    "timestamp": timestamp,
                    "lifecycle": current_lifecycle
                })
                
            size_history.append({
                "timestamp": timestamp,
                "value": state["size"]
            })
            
            influence_history.append({
                "timestamp": timestamp,
                "value": state["influence_score"]
            })
            
            social_total = state["total_shares"] + state["total_likes"] * 0.3 + state["total_comments"] * 0.5
            social_history.append({
                "timestamp": timestamp,
                "value": social_total,
                "shares": state["total_shares"],
                "likes": state["total_likes"],
                "comments": state["total_comments"]
            })
            
        peak_size = max((h["size"] for h in history), default=0)
        peak_time = None
        for h in history:
            if h["size"] == peak_size:
                peak_time = h["timestamp"]
                break
                
        if len(history) >= 2:
            start_time = history[0]["timestamp"]
            end_time = history[-1]["timestamp"]
            duration_hours = (end_time - start_time).total_seconds() / 3600
        else:
            duration_hours = 0
            
        return TopicComparisonItem(
            topic_id=topic_id,
            topic_name=history[-1].get("name", topic_id[:8]),
            lifecycle_timeline=lifecycle_timeline,
            size_history=size_history,
            influence_history=influence_history,
            social_history=social_history,
            peak_time=peak_time,
            peak_size=peak_size,
            total_duration_hours=round(duration_hours, 2)
        )
        
    def _calculate_comparison_metrics(self, topics: List[TopicComparisonItem]) -> Dict:
        metrics = {}
        
        topic_names = {item.topic_id: item.topic_name for item in topics}
        
        peak_sizes = {
            topic_id: item.peak_size 
            for item in topics 
            for topic_id in [item.topic_id]
        }
        metrics["peak_size_ranking"] = sorted(
            peak_sizes.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        durations = {
            topic_id: item.total_duration_hours 
            for item in topics 
            for topic_id in [item.topic_id]
        }
        metrics["duration_ranking"] = sorted(
            durations.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        growth_rates = {}
        for item in topics:
            if item.total_duration_hours > 0:
                growth_rate = item.peak_size / max(item.total_duration_hours, 1)
                growth_rates[item.topic_id] = growth_rate
            else:
                growth_rates[item.topic_id] = 0
        metrics["growth_rate_ranking"] = sorted(
            growth_rates.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        lifecycle_counts = defaultdict(lambda: defaultdict(int))
        for item in topics:
            for event in item.lifecycle_timeline:
                lifecycle_counts[item.topic_id][event["lifecycle"]] += 1
        metrics["lifecycle_distribution"] = dict(lifecycle_counts)
        
        avg_social = {}
        for item in topics:
            if item.social_history:
                last_social = item.social_history[-1]
                avg_social[item.topic_id] = last_social["value"]
            else:
                avg_social[item.topic_id] = 0
        metrics["social_score_ranking"] = sorted(
            avg_social.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return metrics
        
    def get_comparable_topics(self, min_history_points: int = 5) -> List[str]:
        return [
            topic_id 
            for topic_id, history in self.topic_history.items()
            if len(history) >= min_history_points
        ]
        
    def find_similar_topics(self, target_topic_id: str, 
                            similarity_threshold: float = 0.5) -> List[str]:
        if target_topic_id not in self.topic_history:
            return []
            
        target_history = self.topic_history[target_topic_id]
        if len(target_history) < 3:
            return []
            
        similar_topics = []
        target_pattern = self._extract_pattern(target_history)
        
        for topic_id, history in self.topic_history.items():
            if topic_id == target_topic_id:
                continue
            if len(history) < 3:
                continue
                
            pattern = self._extract_pattern(history)
            similarity = self._calculate_pattern_similarity(target_pattern, pattern)
            
            if similarity >= similarity_threshold:
                similar_topics.append((topic_id, similarity))
                
        similar_topics.sort(key=lambda x: x[1], reverse=True)
        return [topic_id for topic_id, _ in similar_topics]
        
    def _extract_pattern(self, history: List[Dict]) -> Dict:
        if not history:
            return {}
            
        sizes = [h["size"] for h in history]
        influences = [h["influence_score"] for h in history]
        
        size_diffs = [sizes[i+1] - sizes[i] for i in range(len(sizes)-1)]
        avg_growth = sum(size_diffs) / len(size_diffs) if size_diffs else 0
        
        lifecycles = [h["lifecycle"] for h in history]
        lifecycle_transitions = sum(
            1 for i in range(len(lifecycles)-1) 
            if lifecycles[i] != lifecycles[i+1]
        )
        
        return {
            "avg_growth": avg_growth,
            "max_size": max(sizes),
            "min_size": min(sizes),
            "avg_influence": sum(influences) / len(influences),
            "lifecycle_transitions": lifecycle_transitions,
            "history_length": len(history)
        }
        
    def _calculate_pattern_similarity(self, pattern1: Dict, pattern2: Dict) -> float:
        if not pattern1 or not pattern2:
            return 0.0
            
        scores = []
        
        max_len = max(pattern1.get("history_length", 1), pattern2.get("history_length", 1))
        len_sim = 1.0 - abs(pattern1.get("history_length", 0) - pattern2.get("history_length", 0)) / max_len
        scores.append(len_sim * 0.2)
        
        max_size = max(pattern1.get("max_size", 1), pattern2.get("max_size", 1))
        size_sim = 1.0 - abs(pattern1.get("max_size", 0) - pattern2.get("max_size", 0)) / max_size
        scores.append(size_sim * 0.3)
        
        inf_sim = 1.0 - abs(pattern1.get("avg_influence", 0) - pattern2.get("avg_influence", 0))
        scores.append(max(inf_sim, 0) * 0.25)
        
        max_trans = max(pattern1.get("lifecycle_transitions", 1), pattern2.get("lifecycle_transitions", 1))
        trans_sim = 1.0 - abs(pattern1.get("lifecycle_transitions", 0) - pattern2.get("lifecycle_transitions", 0)) / max_trans
        scores.append(trans_sim * 0.25)
        
        return sum(scores)
