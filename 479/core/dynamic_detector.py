import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()


class AlertType(Enum):
    NEGATIVE_TREND = "negative_trend"
    SHARP_TURN = "sharp_turn"
    HIGH_NEGATIVE = "high_negative"
    PERSISTENT_NEGATIVE = "persistent_negative"
    ANXIETY_RISING = "anxiety_rising"


@dataclass
class UserEmotionProfile:
    user_id: str
    emotion_history: List[float] = field(default_factory=list)
    mean_sentiment: float = 0.0
    std_sentiment: float = 0.0
    volatility: float = 0.0
    baseline_established: bool = False
    min_samples_for_baseline: int = 5
    
    def update(self, sentiment_score: float):
        self.emotion_history.append(sentiment_score)
        
        if len(self.emotion_history) >= self.min_samples_for_baseline:
            recent_scores = self.emotion_history[-20:]
            self.mean_sentiment = np.mean(recent_scores)
            self.std_sentiment = np.std(recent_scores)
            self.volatility = self.std_sentiment if self.std_sentiment > 0 else 0.1
            self.baseline_established = True
    
    def get_dynamic_threshold(self, base_threshold: float = 0.4) -> float:
        if not self.baseline_established:
            return base_threshold
        
        adjustment_factor = 1.0
        if self.volatility > 0.3:
            adjustment_factor = 1.3
        elif self.volatility < 0.1:
            adjustment_factor = 0.7
        
        return base_threshold * adjustment_factor
    
    def get_anomaly_score(self, sentiment_score: float) -> float:
        if not self.baseline_established or self.std_sentiment == 0:
            return 0.0
        
        z_score = (sentiment_score - self.mean_sentiment) / self.std_sentiment
        return abs(z_score)
    
    def is_significant_change(self, current_score: float, previous_score: float,
                              base_threshold: float = 0.4) -> Tuple[bool, float, str]:
        dynamic_threshold = self.get_dynamic_threshold(base_threshold)
        change = abs(current_score - previous_score)
        significance = change / dynamic_threshold
        
        if change >= dynamic_threshold:
            if current_score < previous_score:
                return True, significance, "deterioration"
            else:
                return True, significance, "improvement"
        
        return False, significance, "stable"


@dataclass
class Alert:
    alert_type: AlertType
    severity: str
    message: str
    confidence: float
    turn_index: int
    details: Dict = None
    channels: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'alert_type': self.alert_type.value,
            'severity': self.severity,
            'message': self.message,
            'confidence': self.confidence,
            'turn_index': self.turn_index,
            'details': self.details or {},
            'channels': self.channels
        }


class DynamicThresholdAnalyzer:
    def __init__(self):
        self.user_profiles: Dict[str, UserEmotionProfile] = {}
        self.negative_sentiments = ['angry', 'disappointed', 'anxious']
        
    def get_or_create_profile(self, user_id: str) -> UserEmotionProfile:
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserEmotionProfile(user_id=user_id)
        return self.user_profiles[user_id]
    
    def calculate_sentiment_score(self, sentiment_result: Dict) -> float:
        scores = sentiment_result.get('scores', {})
        positive_score = scores.get('satisfied', 0)
        negative_score = sum(scores.get(s, 0) for s in self.negative_sentiments)
        return positive_score - negative_score
    
    def detect_sharp_turn_dynamic(self, user_id: str, current_result: Dict, 
                                   previous_result: Dict) -> Tuple[bool, float, float]:
        if not previous_result:
            return False, 0.0, 0.4
        
        profile = self.get_or_create_profile(user_id)
        
        current_score = self.calculate_sentiment_score(current_result)
        previous_score = self.calculate_sentiment_score(previous_result)
        
        base_threshold = float(os.getenv('TURN_THRESHOLD', 0.4))
        is_significant, significance, direction = profile.is_significant_change(
            current_score, previous_score, base_threshold
        )
        
        dynamic_threshold = profile.get_dynamic_threshold(base_threshold)
        change = previous_score - current_score
        
        if is_significant and direction == "deterioration" and current_score < 0:
            return True, change, dynamic_threshold
        
        return False, change, dynamic_threshold
    
    def detect_high_negative_dynamic(self, user_id: str, sentiment_result: Dict) -> Tuple[bool, Dict[str, float]]:
        profile = self.get_or_create_profile(user_id)
        
        scores = sentiment_result.get('scores', {})
        high_negatives = {}
        
        base_threshold = float(os.getenv('ALERT_THRESHOLD', 0.7))
        
        if profile.baseline_established:
            adjustment = 0.1 if profile.volatility > 0.3 else 0
            threshold = base_threshold - adjustment
        else:
            threshold = base_threshold
        
        for sentiment in self.negative_sentiments:
            score = scores.get(sentiment, 0)
            if score >= threshold:
                high_negatives[sentiment] = score
                
        return len(high_negatives) > 0, high_negatives
    
    def detect_negative_trend_dynamic(self, user_id: str, sentiment_history: List[Dict],
                                       window: int = 3) -> Tuple[bool, float]:
        if len(sentiment_history) < window:
            return False, 0.0
        
        profile = self.get_or_create_profile(user_id)
        
        recent = sentiment_history[-window:]
        scores = []
        for h in recent:
            if h.get('sentiment'):
                scores.append(self.calculate_sentiment_score(h['sentiment']))
        
        if len(scores) < window:
            return False, 0.0
        
        trend = np.polyfit(range(window), scores, 1)[0]
        avg_score = np.mean(scores)
        
        trend_threshold = -0.1
        if profile.baseline_established:
            if profile.volatility > 0.3:
                trend_threshold = -0.15
            elif profile.volatility < 0.1:
                trend_threshold = -0.05
        
        if trend < trend_threshold and avg_score < 0:
            return True, abs(trend)
        return False, abs(trend)
    
    def update_profile(self, user_id: str, sentiment_result: Dict):
        score = self.calculate_sentiment_score(sentiment_result)
        profile = self.get_or_create_profile(user_id)
        profile.update(score)
    
    def get_profile_stats(self, user_id: str) -> Dict:
        profile = self.get_or_create_profile(user_id)
        return {
            'mean_sentiment': profile.mean_sentiment,
            'std_sentiment': profile.std_sentiment,
            'volatility': profile.volatility,
            'baseline_established': profile.baseline_established,
            'history_length': len(profile.emotion_history)
        }


class SentimentTrendAnalyzer:
    def __init__(self):
        self.dynamic_analyzer = DynamicThresholdAnalyzer()
        self.negative_sentiments = ['angry', 'disappointed', 'anxious']
        
    def calculate_sentiment_score(self, sentiment_result: Dict) -> float:
        return self.dynamic_analyzer.calculate_sentiment_score(sentiment_result)
    
    def detect_sharp_turn(self, user_id: str, current_result: Dict, 
                          previous_result: Dict) -> Tuple[bool, float, float]:
        return self.dynamic_analyzer.detect_sharp_turn_dynamic(user_id, current_result, previous_result)
    
    def detect_high_negative(self, user_id: str, sentiment_result: Dict) -> Tuple[bool, Dict[str, float]]:
        return self.dynamic_analyzer.detect_high_negative_dynamic(user_id, sentiment_result)
    
    def detect_negative_trend(self, user_id: str, sentiment_history: List[Dict],
                              window: int = 3) -> Tuple[bool, float]:
        return self.dynamic_analyzer.detect_negative_trend_dynamic(user_id, sentiment_history, window)
    
    def detect_persistent_negative(self, sentiment_history: List[Dict],
                                    window: int = 3, threshold: int = 2) -> Tuple[bool, int]:
        if len(sentiment_history) < window:
            return False, 0
            
        recent = sentiment_history[-window:]
        negative_count = 0
        
        for h in recent:
            if not h.get('sentiment'):
                continue
            label = h['sentiment'].get('predicted_label')
            if label in self.negative_sentiments:
                negative_count += 1
                
        return negative_count >= threshold, negative_count
    
    def detect_anxiety_rising(self, sentiment_history: List[Dict],
                               window: int = 3) -> Tuple[bool, float]:
        if len(sentiment_history) < window:
            return False, 0.0
            
        recent = sentiment_history[-window:]
        anxiety_scores = [
            h['sentiment'].get('scores', {}).get('anxious', 0)
            for h in recent if h.get('sentiment')
        ]
        
        if len(anxiety_scores) < window:
            return False, 0.0
            
        trend = np.polyfit(range(window), anxiety_scores, 1)[0]
        avg_anxiety = np.mean(anxiety_scores)
        
        if trend > 0.1 and avg_anxiety > 0.5:
            return True, avg_anxiety
        return False, avg_anxiety
    
    def analyze_sentiment_change(self, sentiment_history: List[Dict]) -> Dict:
        if len(sentiment_history) < 2:
            return {
                'trend': 'stable',
                'change_magnitude': 0.0,
                'current_score': 0.0,
                'previous_score': 0.0
            }
            
        current = sentiment_history[-1]['sentiment']
        previous = sentiment_history[-2]['sentiment']
        
        current_score = self.calculate_sentiment_score(current)
        previous_score = self.calculate_sentiment_score(previous)
        change = current_score - previous_score
        
        if change > 0.2:
            trend = 'improving'
        elif change < -0.2:
            trend = 'deteriorating'
        else:
            trend = 'stable'
            
        return {
            'trend': trend,
            'change_magnitude': abs(change),
            'current_score': current_score,
            'previous_score': previous_score
        }
    
    def update_user_profile(self, user_id: str, sentiment_result: Dict):
        self.dynamic_analyzer.update_profile(user_id, sentiment_result)
    
    def get_user_profile(self, user_id: str) -> Dict:
        return self.dynamic_analyzer.get_profile_stats(user_id)
