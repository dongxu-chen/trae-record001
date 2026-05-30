import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import json
import os


@dataclass
class DailyStats:
    date: str
    total_conversations: int = 0
    total_messages: int = 0
    avg_sentiment_score: float = 0.0
    sentiment_distribution: Dict[str, int] = field(default_factory=lambda: {
        'satisfied': 0, 'angry': 0, 'disappointed': 0, 'anxious': 0
    })
    positive_rate: float = 0.0
    negative_rate: float = 0.0
    alert_count: int = 0
    avg_response_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'total_conversations': self.total_conversations,
            'total_messages': self.total_messages,
            'avg_sentiment_score': self.avg_sentiment_score,
            'sentiment_distribution': self.sentiment_distribution,
            'positive_rate': self.positive_rate,
            'negative_rate': self.negative_rate,
            'alert_count': self.alert_count,
            'avg_response_time': self.avg_response_time
        }


@dataclass
class WeeklyStats:
    week_start: str
    week_end: str
    daily_stats: List[DailyStats] = field(default_factory=list)
    total_conversations: int = 0
    total_messages: int = 0
    avg_sentiment_score: float = 0.0
    sentiment_distribution: Dict[str, int] = field(default_factory=lambda: {
        'satisfied': 0, 'angry': 0, 'disappointed': 0, 'anxious': 0
    })
    trend_direction: str = 'stable'
    top_issues: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'week_start': self.week_start,
            'week_end': self.week_end,
            'daily_stats': [d.to_dict() for d in self.daily_stats],
            'total_conversations': self.total_conversations,
            'total_messages': self.total_messages,
            'avg_sentiment_score': self.avg_sentiment_score,
            'sentiment_distribution': self.sentiment_distribution,
            'trend_direction': self.trend_direction,
            'top_issues': self.top_issues
        }


class TrendDataCollector:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or 'data/trend_data.json'
        self.daily_data: Dict[str, DailyStats] = {}
        self.session_timestamps: Dict[str, List[float]] = {}
        self.session_sentiments: Dict[str, List[Dict]] = {}
        self.session_alerts: Dict[str, int] = {}
        
        self._ensure_storage()
        self._load_data()
        
    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            self._save_data()
    
    def _load_data(self):
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for date_str, stats in data.get('daily_data', {}).items():
                        ds = DailyStats(date=date_str)
                        ds.total_conversations = stats.get('total_conversations', 0)
                        ds.total_messages = stats.get('total_messages', 0)
                        ds.avg_sentiment_score = stats.get('avg_sentiment_score', 0.0)
                        ds.sentiment_distribution = stats.get('sentiment_distribution', ds.sentiment_distribution)
                        ds.positive_rate = stats.get('positive_rate', 0.0)
                        ds.negative_rate = stats.get('negative_rate', 0.0)
                        ds.alert_count = stats.get('alert_count', 0)
                        ds.avg_response_time = stats.get('avg_response_time', 0.0)
                        self.daily_data[date_str] = ds
        except Exception as e:
            print(f"Warning: Failed to load trend data: {e}")
    
    def _save_data(self):
        try:
            data = {
                'daily_data': {k: v.to_dict() for k, v in self.daily_data.items()},
                'last_updated': datetime.now().isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save trend data: {e}")
    
    def _get_date_str(self, timestamp: float = None) -> str:
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        return datetime.now().strftime('%Y-%m-%d')
    
    def record_message(self, session_id: str, text: str, speaker: str, 
                       sentiment_result: Dict, timestamp: float = None):
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        
        date_str = self._get_date_str(timestamp)
        
        if date_str not in self.daily_data:
            self.daily_data[date_str] = DailyStats(date=date_str)
        
        daily = self.daily_data[date_str]
        daily.total_messages += 1
        
        if session_id not in self.session_timestamps:
            self.session_timestamps[session_id] = []
            self.session_sentiments[session_id] = []
            self.session_alerts[session_id] = 0
            daily.total_conversations += 1
        
        self.session_timestamps[session_id].append(timestamp)
        
        if speaker == 'customer' and sentiment_result:
            self.session_sentiments[session_id].append(sentiment_result)
            label = sentiment_result.get('predicted_label')
            if label in daily.sentiment_distribution:
                daily.sentiment_distribution[label] += 1
        
        self._update_daily_metrics(date_str)
        self._save_data()
    
    def record_alert(self, session_id: str):
        date_str = self._get_date_str()
        
        if date_str not in self.daily_data:
            self.daily_data[date_str] = DailyStats(date=date_str)
        
        self.daily_data[date_str].alert_count += 1
        self.session_alerts[session_id] = self.session_alerts.get(session_id, 0) + 1
        self._save_data()
    
    def _update_daily_metrics(self, date_str: str):
        daily = self.daily_data[date_str]
        
        all_sentiments = []
        for session_id, sentiments in self.session_sentiments.items():
            if self._get_date_str(self.session_timestamps[session_id][0]) == date_str:
                all_sentiments.extend(sentiments)
        
        if all_sentiments:
            scores = []
            for s in all_sentiments:
                sc = s.get('scores', {})
                score = sc.get('satisfied', 0) - (sc.get('angry', 0) + sc.get('disappointed', 0) + sc.get('anxious', 0))
                scores.append(score)
            
            daily.avg_sentiment_score = float(np.mean(scores)) if scores else 0.0
            
            total = len(all_sentiments)
            positive = sum(1 for s in all_sentiments if s.get('predicted_label') == 'satisfied')
            negative = sum(1 for s in all_sentiments if s.get('predicted_label') in ['angry', 'disappointed', 'anxious'])
            daily.positive_rate = positive / total if total > 0 else 0.0
            daily.negative_rate = negative / total if total > 0 else 0.0
        
        response_times = []
        for session_id, timestamps in self.session_timestamps.items():
            if self._get_date_str(timestamps[0]) == date_str and len(timestamps) >= 3:
                for i in range(1, len(timestamps), 2):
                    if i + 1 < len(timestamps):
                        rt = timestamps[i + 1] - timestamps[i]
                        if rt < 600:
                            response_times.append(rt)
        
        daily.avg_response_time = float(np.mean(response_times)) if response_times else 0.0
    
    def get_daily_stats(self, date: str = None) -> Optional[DailyStats]:
        if date is None:
            date = self._get_date_str()
        return self.daily_data.get(date)
    
    def get_date_range_stats(self, start_date: str, end_date: str) -> List[DailyStats]:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        stats = []
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            if date_str in self.daily_data:
                stats.append(self.daily_data[date_str])
            else:
                stats.append(DailyStats(date=date_str))
            current += timedelta(days=1)
        
        return stats
    
    def get_weekly_stats(self, base_date: str = None) -> WeeklyStats:
        if base_date is None:
            base_date = self._get_date_str()
        
        base = datetime.strptime(base_date, '%Y-%m-%d')
        week_start = base - timedelta(days=base.weekday())
        week_end = week_start + timedelta(days=6)
        
        daily_stats = self.get_date_range_stats(
            week_start.strftime('%Y-%m-%d'),
            week_end.strftime('%Y-%m-%d')
        )
        
        weekly = WeeklyStats(
            week_start=week_start.strftime('%Y-%m-%d'),
            week_end=week_end.strftime('%Y-%m-%d'),
            daily_stats=daily_stats
        )
        
        for ds in daily_stats:
            weekly.total_conversations += ds.total_conversations
            weekly.total_messages += ds.total_messages
            for k, v in ds.sentiment_distribution.items():
                weekly.sentiment_distribution[k] += v
        
        if daily_stats:
            scores = [ds.avg_sentiment_score for ds in daily_stats if ds.total_messages > 0]
            weekly.avg_sentiment_score = float(np.mean(scores)) if scores else 0.0
            
            if len(scores) >= 3:
                first_half = scores[:len(scores)//2]
                second_half = scores[len(scores)//2:]
                if np.mean(second_half) > np.mean(first_half) + 0.1:
                    weekly.trend_direction = 'improving'
                elif np.mean(second_half) < np.mean(first_half) - 0.1:
                    weekly.trend_direction = 'deteriorating'
                else:
                    weekly.trend_direction = 'stable'
        
        weekly.top_issues = self._get_top_issues(daily_stats)
        
        return weekly
    
    def _get_top_issues(self, daily_stats: List[DailyStats]) -> List[Dict]:
        issues = defaultdict(int)
        
        for ds in daily_stats:
            for sentiment, count in ds.sentiment_distribution.items():
                if sentiment in ['angry', 'disappointed', 'anxious']:
                    issues[sentiment] += count
        
        sorted_issues = sorted(issues.items(), key=lambda x: x[1], reverse=True)
        sentiment_cn = {
            'angry': '愤怒',
            'disappointed': '失望',
            'anxious': '焦虑'
        }
        
        return [
            {'issue': sentiment_cn.get(k, k), 'count': v, 'sentiment': k}
            for k, v in sorted_issues[:5]
        ]
    
    def get_trend_analysis(self, period: str = '7d') -> Dict:
        end_date = datetime.now()
        
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        daily_stats = self.get_date_range_stats(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        scores = [ds.avg_sentiment_score for ds in daily_stats if ds.total_messages > 0]
        if len(scores) >= 2:
            trend = np.polyfit(range(len(scores)), scores, 1)[0]
            if trend > 0.05:
                direction = 'improving'
            elif trend < -0.05:
                direction = 'deteriorating'
            else:
                direction = 'stable'
        else:
            direction = 'stable'
            trend = 0.0
        
        return {
            'period': period,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'daily_data': [ds.to_dict() for ds in daily_stats],
            'trend_direction': direction,
            'trend_slope': float(trend),
            'avg_sentiment': float(np.mean(scores)) if scores else 0.0,
            'total_conversations': sum(ds.total_conversations for ds in daily_stats),
            'total_alerts': sum(ds.alert_count for ds in daily_stats)
        }
    
    def get_hourly_distribution(self, date: str = None) -> Dict:
        if date is None:
            date = self._get_date_str()
        
        hourly = {h: {'count': 0, 'scores': []} for h in range(24)}
        
        for session_id, timestamps in self.session_timestamps.items():
            for i, ts in enumerate(timestamps):
                if self._get_date_str(ts) == date:
                    hour = datetime.fromtimestamp(ts).hour
                    hourly[hour]['count'] += 1
                    
                    if session_id in self.session_sentiments and i < len(self.session_sentiments[session_id]):
                        s = self.session_sentiments[session_id][i]
                        sc = s.get('scores', {})
                        score = sc.get('satisfied', 0) - (sc.get('angry', 0) + sc.get('disappointed', 0) + sc.get('anxious', 0))
                        hourly[hour]['scores'].append(score)
        
        result = {}
        for h, data in hourly.items():
            result[str(h)] = {
                'message_count': data['count'],
                'avg_sentiment': float(np.mean(data['scores'])) if data['scores'] else 0.0
            }
        
        return result


def create_trend_collector() -> TrendDataCollector:
    return TrendDataCollector()
