import numpy as np
import uuid
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
from models import ClusterTopic, TopicWarning, TopicLifeCycle
from config import settings
import logging

logger = logging.getLogger(__name__)

class TopicWarningSystem:
    def __init__(self):
        self.topic_history: Dict[str, deque] = {}
        self.active_warnings: Dict[str, TopicWarning] = {}
        self.warning_history: List[TopicWarning] = []
        self.max_history_size = 50
        
    def record_topic_state(self, topic: ClusterTopic, influence_metrics: Dict):
        topic_id = topic.topic_id
        if topic_id not in self.topic_history:
            self.topic_history[topic_id] = deque(maxlen=self.max_history_size)
        
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
        
    def detect_burst_warning(self, topic: ClusterTopic, influence_metrics: Dict) -> Optional[TopicWarning]:
        topic_id = topic.topic_id
        
        if topic.lifecycle in [TopicLifeCycle.BURSTING, TopicLifeCycle.DECLINING]:
            return None
            
        history = self.topic_history.get(topic_id, deque())
        if len(history) < 3:
            return None
            
        warning_signals = []
        warning_confidence = 0.0
        
        size_growth_rate = self._calculate_growth_rate([h['size'] for h in history])
        if size_growth_rate > settings.WARNING_SIZE_GROWTH_THRESHOLD:
            warning_signals.append(f"规模快速增长 ({size_growth_rate:.2f}x)")
            warning_confidence += min(size_growth_rate / 5.0, 0.3)
            
        velocity = influence_metrics.get('velocity', 0)
        if velocity > settings.WARNING_VELOCITY_THRESHOLD:
            warning_signals.append(f"增长速度加快 (velocity: {velocity:.2f})")
            warning_confidence += min(velocity / 20.0, 0.25)
            
        momentum = influence_metrics.get('momentum', 0)
        if momentum > settings.WARNING_MOMENTUM_THRESHOLD:
            warning_signals.append(f"增长动量强劲 (momentum: {momentum:.2f})")
            warning_confidence += min(momentum / 2.0, 0.25)
            
        share_score = influence_metrics.get('share_score', 0)
        if share_score > settings.WARNING_SOCIAL_THRESHOLD:
            warning_signals.append(f"社交热度飙升 (share_score: {share_score:.2f})")
            warning_confidence += min(share_score / 1.5, 0.2)
            
        social_acceleration = self._calculate_social_acceleration(history)
        if social_acceleration > settings.WARNING_SOCIAL_ACCELERATION_THRESHOLD:
            warning_signals.append(f"社交指标加速增长")
            warning_confidence += 0.15
            
        lifecycle_transition_prob = self._predict_lifecycle_transition(topic, history)
        if lifecycle_transition_prob > 0.6:
            warning_signals.append(f"高概率进入爆发期 (prob: {lifecycle_transition_prob:.2f})")
            warning_confidence += lifecycle_transition_prob * 0.2
            
        if warning_confidence >= settings.WARNING_MIN_CONFIDENCE and len(warning_signals) >= 2:
            warning_level = self._determine_warning_level(warning_confidence)
            predicted_burst_time = self._predict_burst_time(history, velocity)
            
            warning = TopicWarning(
                warning_id=str(uuid.uuid4()),
                topic_id=topic_id,
                topic_name=topic.name,
                warning_level=warning_level,
                warning_type="burst_imminent",
                confidence=round(warning_confidence, 3),
                predicted_burst_time=predicted_burst_time,
                current_metrics={
                    "size": topic.size,
                    "velocity": velocity,
                    "momentum": momentum,
                    "share_score": share_score
                },
                historical_trend=list(history)[-10:],
                created_at=datetime.now(),
                message=f"话题「{topic.name}」可能即将爆发！预警信号：{'; '.join(warning_signals[:3])}"
            )
            
            self.active_warnings[topic_id] = warning
            self.warning_history.append(warning)
            
            logger.info(f"⚠️ 话题预警: {topic.name} (confidence: {warning_confidence:.2f}, level: {warning_level})")
            return warning
            
        return None
        
    def _calculate_growth_rate(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        recent = values[-3:] if len(values) >= 3 else values
        older = values[:-3] if len(values) > 3 else values[:1]
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older) if older else 1.0
        
        if older_avg == 0:
            return 10.0
        return recent_avg / max(older_avg, 1)
        
    def _calculate_social_acceleration(self, history: List[Dict]) -> float:
        if len(history) < 4:
            return 0.0
            
        recent_social = [
            h['total_shares'] + h['total_likes'] * 0.3 + h['total_comments'] * 0.5
            for h in history[-4:]
        ]
        
        if len(recent_social) < 4:
            return 0.0
            
        recent_velocity = np.diff(recent_social)
        if len(recent_velocity) < 2:
            return 0.0
            
        acceleration = np.diff(recent_velocity)
        return float(np.mean(acceleration)) if len(acceleration) > 0 else 0.0
        
    def _predict_lifecycle_transition(self, topic: ClusterTopic, history: List[Dict]) -> float:
        if topic.lifecycle != TopicLifeCycle.GROWING:
            return 0.0
            
        if len(history) < 5:
            return 0.5
            
        recent = history[-5:]
        size_trend = [h['size'] for h in recent]
        trend_scores = [h['trend_score'] for h in recent]
        
        size_growing = all(size_trend[i] < size_trend[i+1] for i in range(len(size_trend)-1))
        trend_rising = all(trend_scores[i] <= trend_scores[i+1] for i in range(len(trend_scores)-1))
        
        prob = 0.5
        if size_growing:
            prob += 0.2
        if trend_rising:
            prob += 0.15
        if topic.trend_score > 2.0:
            prob += 0.15
            
        return min(prob, 1.0)
        
    def _determine_warning_level(self, confidence: float) -> str:
        if confidence >= 0.8:
            return "critical"
        elif confidence >= 0.6:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
            
    def _predict_burst_time(self, history: List[Dict], velocity: float) -> Optional[datetime]:
        if velocity <= 0 or len(history) < 2:
            return None
            
        current_size = history[-1]['size']
        target_size = settings.BURST_TARGET_SIZE
        
        if current_size >= target_size:
            return datetime.now()
            
        hours_to_burst = max(0, (target_size - current_size) / max(velocity, 0.1))
        return datetime.now() + timedelta(hours=min(hours_to_burst, 72))
        
    def get_active_warnings(self, min_level: str = None) -> List[TopicWarning]:
        warnings = list(self.active_warnings.values())
        
        level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if min_level and min_level in level_order:
            min_level_value = level_order[min_level]
            warnings = [w for w in warnings if level_order.get(w.warning_level, 0) >= min_level_value]
            
        return sorted(warnings, key=lambda w: w.confidence, reverse=True)
        
    def acknowledge_warning(self, topic_id: str) -> bool:
        if topic_id in self.active_warnings:
            del self.active_warnings[topic_id]
            return True
        return False
        
    def get_warning_history(self, limit: int = 20) -> List[TopicWarning]:
        return sorted(self.warning_history, key=lambda w: w.created_at, reverse=True)[:limit]
