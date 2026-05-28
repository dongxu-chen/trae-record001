import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)

from config import Config
from database import get_session, save_alert, Alert


class AlertManager:
    def __init__(self, kafka_manager=None):
        self.kafka_manager = kafka_manager
        self.alert_callbacks = []
        self.alert_history = []
        self.max_history = 1000
        
        self.config = Config.ALERT_CONFIG
    
    def add_alert_callback(self, callback: Callable):
        self.alert_callbacks.append(callback)
    
    def check_alerts(self, sentiment_data: List[Dict], platform: str = 'all') -> List[Dict]:
        if not sentiment_data:
            return []
        
        triggered_alerts = []
        
        negative_ratio_alert = self._check_negative_ratio(sentiment_data, platform)
        if negative_ratio_alert:
            triggered_alerts.append(negative_ratio_alert)
        
        volume_spike_alert = self._check_volume_spike(sentiment_data, platform)
        if volume_spike_alert:
            triggered_alerts.append(volume_spike_alert)
        
        sentiment_shift_alert = self._check_sentiment_shift(sentiment_data, platform)
        if sentiment_shift_alert:
            triggered_alerts.append(sentiment_shift_alert)
        
        for alert in triggered_alerts:
            self._process_alert(alert)
        
        return triggered_alerts
    
    def _check_negative_ratio(self, sentiment_data: List[Dict], platform: str) -> Optional[Dict]:
        total = len(sentiment_data)
        if total < 10:
            return None
        
        negative_count = sum(1 for s in sentiment_data if s.get('sentiment') == 'negative')
        negative_ratio = negative_count / total
        
        threshold = self.config.get('negative_ratio_threshold', 0.3)
        
        if negative_ratio >= threshold:
            severity = 'high' if negative_ratio >= threshold * 1.5 else 'medium'
            
            return {
                'alert_type': 'negative_ratio_exceeded',
                'severity': severity,
                'title': f'负面情绪占比过高 - {platform}',
                'description': f'检测到负面情绪占比达到 {negative_ratio:.2%}，超过阈值 {threshold:.2%}',
                'platform': platform,
                'related_post_ids': ','.join([str(s.get('post_id', '')) for s in sentiment_data if s.get('sentiment') == 'negative'][:10]),
                'metrics': json.dumps({
                    'negative_ratio': negative_ratio,
                    'threshold': threshold,
                    'total_posts': total,
                    'negative_count': negative_count
                }, ensure_ascii=False)
            }
        
        return None
    
    def _check_volume_spike(self, sentiment_data: List[Dict], platform: str) -> Optional[Dict]:
        if len(sentiment_data) < 2:
            return None
        
        timestamps = []
        for s in sentiment_data:
            ts = s.get('timestamp')
            if isinstance(ts, str):
                try:
                    timestamps.append(datetime.fromisoformat(ts))
                except:
                    timestamps.append(datetime.utcnow())
            elif isinstance(ts, datetime):
                timestamps.append(ts)
            else:
                timestamps.append(datetime.utcnow())
        
        if not timestamps:
            return None
        
        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 60 if len(timestamps) > 1 else 1
        current_volume = len(sentiment_data) / max(time_span, 1)
        
        expected_volume = len(sentiment_data) / (time_span * 2) if time_span > 0 else 1
        
        spike_ratio = current_volume / max(expected_volume, 1)
        threshold = self.config.get('volume_spike_threshold', 2.0)
        
        if spike_ratio >= threshold:
            severity = 'high' if spike_ratio >= threshold * 2 else 'medium'
            
            return {
                'alert_type': 'volume_spike',
                'severity': severity,
                'title': f'讨论量激增 - {platform}',
                'description': f'检测到讨论量激增，当前速率 {current_volume:.2f} 条/分钟，是预期的 {spike_ratio:.2f} 倍',
                'platform': platform,
                'related_post_ids': ','.join([str(s.get('post_id', '')) for s in sentiment_data[:10]]),
                'metrics': json.dumps({
                    'spike_ratio': spike_ratio,
                    'threshold': threshold,
                    'current_volume': current_volume,
                    'expected_volume': expected_volume
                }, ensure_ascii=False)
            }
        
        return None
    
    def _check_sentiment_shift(self, sentiment_data: List[Dict], platform: str) -> Optional[Dict]:
        if len(sentiment_data) < 20:
            return None
        
        mid = len(sentiment_data) // 2
        first_half = sentiment_data[:mid]
        second_half = sentiment_data[mid:]
        
        first_avg = self._calculate_sentiment_score(first_half)
        second_avg = self._calculate_sentiment_score(second_half)
        
        shift = abs(second_avg - first_avg)
        
        if shift >= 0.2:
            direction = 'negative' if second_avg < first_avg else 'positive'
            severity = 'high' if shift >= 0.4 else 'medium'
            
            return {
                'alert_type': 'sentiment_shift',
                'severity': severity,
                'title': f'情绪快速{direction}转变 - {platform}',
                'description': f'检测到情绪从 {first_avg:.3f} 快速转变为 {second_avg:.3f}，变化幅度 {shift:.3f}',
                'platform': platform,
                'related_post_ids': ','.join([str(s.get('post_id', '')) for s in sentiment_data[-10:]]),
                'metrics': json.dumps({
                    'shift_magnitude': shift,
                    'first_half_score': first_avg,
                    'second_half_score': second_avg,
                    'direction': direction
                }, ensure_ascii=False)
            }
        
        return None
    
    def _calculate_sentiment_score(self, sentiments: List[Dict]) -> float:
        if not sentiments:
            return 0.5
        
        total_score = 0
        for s in sentiments:
            if s.get('sentiment') == 'positive':
                total_score += s.get('positive', 0.5)
            elif s.get('sentiment') == 'negative':
                total_score += s.get('negative', 0.5) * -1
            else:
                total_score += 0
        
        return total_score / len(sentiments)
    
    def _process_alert(self, alert_data: Dict):
        try:
            session = get_session()
            save_alert(session, alert_data)
            session.close()
        except Exception as e:
            logger.error(f"Failed to save alert to database: {e}")
        
        if self.kafka_manager and self.kafka_manager.enabled:
            self.kafka_manager.send_alert(alert_data)
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        self.alert_history.append({
            **alert_data,
            'triggered_at': datetime.utcnow().isoformat()
        })
        
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        logger.warning(f"Alert triggered: {alert_data['alert_type']} - {alert_data['severity']} - {alert_data['title']}")
    
    def get_recent_alerts(self, limit: int = 20, severity: str = None) -> List[Dict]:
        try:
            session = get_session()
            query = session.query(Alert).order_by(Alert.triggered_at.desc())
            
            if severity:
                query = query.filter(Alert.severity == severity)
            
            alerts = query.limit(limit).all()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert.id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'description': alert.description,
                    'platform': alert.platform,
                    'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                    'acknowledged': alert.acknowledged == 1
                })
            
            session.close()
            return result
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        try:
            session = get_session()
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.acknowledged = 1
                alert.acknowledged_at = datetime.utcnow()
                session.commit()
                session.close()
                return True
            session.close()
            return False
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    def get_alert_summary(self, hours: int = 24) -> Dict:
        try:
            session = get_session()
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            alerts = session.query(Alert).filter(Alert.triggered_at >= cutoff_time).all()
            
            summary = {
                'total': len(alerts),
                'by_severity': {'high': 0, 'medium': 0, 'low': 0},
                'by_type': defaultdict(int),
                'by_platform': defaultdict(int),
                'unacknowledged': 0
            }
            
            for alert in alerts:
                summary['by_severity'][alert.severity] = summary['by_severity'].get(alert.severity, 0) + 1
                summary['by_type'][alert.alert_type] += 1
                if alert.platform:
                    summary['by_platform'][alert.platform] += 1
                if alert.acknowledged == 0:
                    summary['unacknowledged'] += 1
            
            session.close()
            return summary
        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {'total': 0, 'by_severity': {}, 'by_type': {}, 'by_platform': {}, 'unacknowledged': 0}
