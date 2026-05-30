import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import os
from dotenv import load_dotenv

from .dynamic_detector import (
    AlertType, Alert, SentimentTrendAnalyzer, DynamicThresholdAnalyzer
)
from .alert_channels import MultiChannelAlertManager, create_multi_channel_alert_manager

load_dotenv()


class AlertManager:
    def __init__(self):
        self.trend_analyzer = SentimentTrendAnalyzer()
        self.multi_channel_manager = create_multi_channel_alert_manager()
        self.alerts_history: Dict[str, List[Alert]] = {}
        self.user_profiles: Dict[str, Dict] = {}
        
    def generate_alerts(self, session_id: str, current_result: Dict,
                        sentiment_history: List[Dict], user_id: str = None) -> List[Alert]:
        alerts = []
        turn_index = len(sentiment_history)
        
        user_id = user_id or session_id
        
        self.trend_analyzer.update_user_profile(user_id, current_result)
        
        high_neg, high_neg_details = self.trend_analyzer.detect_high_negative(user_id, current_result)
        if high_neg:
            for sentiment, score in high_neg_details.items():
                sentiment_cn = {
                    'angry': '愤怒',
                    'disappointed': '失望',
                    'anxious': '焦虑'
                }
                alerts.append(Alert(
                    alert_type=AlertType.HIGH_NEGATIVE,
                    severity='high',
                    message=f"检测到高{sentiment_cn.get(sentiment, sentiment)}情绪",
                    confidence=score,
                    turn_index=turn_index,
                    details={'sentiment': sentiment, 'score': score}
                ))
        
        if len(sentiment_history) >= 2:
            previous = sentiment_history[-2].get('sentiment', {})
            sharp_turn, turn_magnitude, dynamic_threshold = self.trend_analyzer.detect_sharp_turn(
                user_id, current_result, previous
            )
            if sharp_turn:
                alerts.append(Alert(
                    alert_type=AlertType.SHARP_TURN,
                    severity='high',
                    message=f"检测到情绪急剧恶化 (阈值: {dynamic_threshold:.2f})",
                    confidence=turn_magnitude,
                    turn_index=turn_index,
                    details={
                        'change_magnitude': turn_magnitude,
                        'dynamic_threshold': dynamic_threshold
                    }
                ))
        
        neg_trend, trend_strength = self.trend_analyzer.detect_negative_trend(
            user_id, sentiment_history
        )
        if neg_trend:
            alerts.append(Alert(
                alert_type=AlertType.NEGATIVE_TREND,
                severity='medium',
                message="检测到负面情绪趋势",
                confidence=trend_strength,
                turn_index=turn_index,
                details={'trend_strength': trend_strength}
            ))
        
        persistent, count = self.trend_analyzer.detect_persistent_negative(sentiment_history)
        if persistent:
            alerts.append(Alert(
                alert_type=AlertType.PERSISTENT_NEGATIVE,
                severity='medium',
                message=f"连续{count}轮对话出现负面情绪",
                confidence=count / 3,
                turn_index=turn_index,
                details={'negative_count': count}
            ))
        
        anxiety_rising, anxiety_level = self.trend_analyzer.detect_anxiety_rising(sentiment_history)
        if anxiety_rising:
            alerts.append(Alert(
                alert_type=AlertType.ANXIETY_RISING,
                severity='medium',
                message="焦虑情绪正在上升",
                confidence=anxiety_level,
                turn_index=turn_index,
                details={'anxiety_level': anxiety_level}
            ))
        
        if alerts:
            if session_id not in self.alerts_history:
                self.alerts_history[session_id] = []
            self.alerts_history[session_id].extend(alerts)
            
            context = {
                'session_id': session_id,
                'customer_message': current_result.get('text', '')
            }
            for alert in alerts:
                alert_dict = alert.to_dict()
                channel_results = self.multi_channel_manager.send_alert(alert_dict, context)
                alert.channels = [k for k, v in channel_results.items() if v]
        
        return alerts
    
    def send_to_channels(self, alert: Dict, context: Dict = None) -> Dict[str, bool]:
        return self.multi_channel_manager.send_alert(alert, context)
    
    def get_enabled_channels(self) -> List[str]:
        return self.multi_channel_manager.get_enabled_channels()
    
    def test_alert_channel(self, channel_name: str) -> bool:
        return self.multi_channel_manager.test_channel(channel_name)
    
    def get_sentiment_trend(self, sentiment_history: List[Dict]) -> Dict:
        return self.trend_analyzer.analyze_sentiment_change(sentiment_history)
    
    def get_user_profile(self, user_id: str) -> Dict:
        return self.trend_analyzer.get_user_profile(user_id)
    
    def get_alerts(self, session_id: str) -> List[Dict]:
        return [alert.to_dict() for alert in self.alerts_history.get(session_id, [])]
    
    def clear_alerts(self, session_id: str):
        if session_id in self.alerts_history:
            self.alerts_history[session_id].clear()


def create_alert_manager() -> AlertManager:
    return AlertManager()
