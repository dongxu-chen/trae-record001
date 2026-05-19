import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
from config import DATA_DIR

ALERT_HISTORY_PATH = os.path.join(DATA_DIR, 'alert_history.json')


class AlertSystem:
    def __init__(self):
        self.alert_history = self._load_alert_history()
        self.alert_rules = {
            'negative_spike': {
                'name': '负面评价突增',
                'description': '单日负面评价占比超过阈值',
                'threshold': 0.3,
                'window_days': 7,
                'min_comments': 10
            },
            'score_drop': {
                'name': '情感分骤降',
                'description': '连续多日情感分下降',
                'threshold': 0.1,
                'consecutive_days': 3
            },
            'aspect_negative': {
                'name': '特定方面负面突增',
                'description': '某个方面的负面评价占比超过阈值',
                'threshold': 0.4,
                'aspects': ['价格', '质量', '物流', '服务']
            },
            'low_rating': {
                'name': '低分预警',
                'description': '单日平均评分低于阈值',
                'threshold': 3.0,
                'min_comments': 5
            }
        }
    
    def _load_alert_history(self):
        if os.path.exists(ALERT_HISTORY_PATH):
            with open(ALERT_HISTORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_alert_history(self):
        with open(ALERT_HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.alert_history, f, ensure_ascii=False, indent=2)
    
    def _add_alert(self, alert_type, severity, message, details=None):
        alert = {
            'id': f'ALERT_{datetime.now().strftime("%Y%m%d%H%M%S")}_{len(self.alert_history)+1}',
            'type': alert_type,
            'type_name': self.alert_rules[alert_type]['name'],
            'severity': severity,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'read': False
        }
        
        for existing in self.alert_history:
            if (existing['type'] == alert_type and 
                existing['severity'] == severity and
                existing['message'] == message and
                (datetime.now() - datetime.strptime(existing['timestamp'], '%Y-%m-%d %H:%M:%S')) < timedelta(hours=1)):
                return None
        
        self.alert_history.insert(0, alert)
        self._save_alert_history()
        return alert
    
    def check_alerts(self, df):
        if len(df) == 0:
            return []
        
        alerts = []
        
        spike_alert = self._check_negative_spike(df)
        if spike_alert:
            alerts.append(spike_alert)
        
        score_alert = self._check_score_drop(df)
        if score_alert:
            alerts.append(score_alert)
        
        aspect_alerts = self._check_aspect_negative(df)
        alerts.extend(aspect_alerts)
        
        rating_alert = self._check_low_rating(df)
        if rating_alert:
            alerts.append(rating_alert)
        
        return alerts
    
    def _check_negative_spike(self, df):
        df['date'] = pd.to_datetime(df['comment_time']).dt.date
        
        rule = self.alert_rules['negative_spike']
        
        daily_stats = df.groupby('date').agg({
            'comment_id': 'count',
            'sentiment_label': lambda x: (x == 'negative').sum()
        }).reset_index()
        
        daily_stats.columns = ['date', 'total', 'negative']
        daily_stats['negative_rate'] = daily_stats['negative'] / daily_stats['total']
        daily_stats = daily_stats.sort_values('date', ascending=False)
        
        if len(daily_stats) == 0:
            return None
        
        latest = daily_stats.iloc[0]
        
        if latest['total'] >= rule['min_comments'] and latest['negative_rate'] > rule['threshold']:
            baseline = daily_stats.iloc[1:rule['window_days']+1]['negative_rate'].mean()
            increase = (latest['negative_rate'] - baseline) / baseline if baseline > 0 else latest['negative_rate']
            
            severity = 'high' if increase > 1 else 'medium'
            
            return self._add_alert(
                'negative_spike',
                severity,
                f'{latest["date"].strftime("%Y-%m-%d")} 负面评价占比达到 {latest["negative_rate"]*100:.1f}%，较基准线上升 {increase*100:.1f}%',
                {
                    'date': latest['date'].strftime('%Y-%m-%d'),
                    'negative_rate': round(latest['negative_rate'] * 100, 2),
                    'baseline': round(baseline * 100, 2),
                    'increase': round(increase * 100, 2),
                    'total_comments': int(latest['total']),
                    'negative_comments': int(latest['negative'])
                }
            )
        
        return None
    
    def _check_score_drop(self, df):
        df['date'] = pd.to_datetime(df['comment_time']).dt.date
        
        rule = self.alert_rules['score_drop']
        
        daily_scores = df.groupby('date')['sentiment_score'].mean().reset_index()
        daily_scores = daily_scores.sort_values('date', ascending=False)
        
        if len(daily_scores) < rule['consecutive_days']:
            return None
        
        recent = daily_scores.head(rule['consecutive_days'])
        scores = recent['sentiment_score'].tolist()
        
        is_dropping = all(scores[i] > scores[i+1] for i in range(len(scores)-1))
        total_drop = scores[0] - scores[-1]
        
        if is_dropping and total_drop > rule['threshold']:
            return self._add_alert(
                'score_drop',
                'high',
                f'情感分连续 {rule["consecutive_days"]} 天下降，累计下降 {total_drop:.3f}',
                {
                    'days': rule['consecutive_days'],
                    'total_drop': round(total_drop, 4),
                    'scores': [round(s, 4) for s in scores]
                }
            )
        
        return None
    
    def _check_aspect_negative(self, df):
        df['date'] = pd.to_datetime(df['comment_time']).dt.date
        
        rule = self.alert_rules['aspect_negative']
        alerts = []
        
        latest_date = df['date'].max()
        latest_df = df[df['date'] == latest_date]
        
        for aspect in rule['aspects']:
            aspect_df = latest_df[latest_df['aspects'].str.contains(aspect, na=False)]
            if len(aspect_df) >= 5:
                negative_count = (aspect_df['sentiment_label'] == 'negative').sum()
                negative_rate = negative_count / len(aspect_df)
                
                if negative_rate > rule['threshold']:
                    severity = 'high' if negative_rate > 0.6 else 'medium'
                    
                    alert = self._add_alert(
                        'aspect_negative',
                        severity,
                        f'{latest_date.strftime("%Y-%m-%d")} {aspect} 方面负面占比达到 {negative_rate*100:.1f}%',
                        {
                            'aspect': aspect,
                            'date': latest_date.strftime('%Y-%m-%d'),
                            'negative_rate': round(negative_rate * 100, 2),
                            'total_comments': len(aspect_df),
                            'negative_comments': int(negative_count)
                        }
                    )
                    if alert:
                        alerts.append(alert)
        
        return alerts
    
    def _check_low_rating(self, df):
        df['date'] = pd.to_datetime(df['comment_time']).dt.date
        
        rule = self.alert_rules['low_rating']
        
        daily_ratings = df.groupby('date').agg({
            'comment_id': 'count',
            'rating': 'mean'
        }).reset_index()
        
        daily_ratings.columns = ['date', 'total', 'avg_rating']
        daily_ratings = daily_ratings.sort_values('date', ascending=False)
        
        if len(daily_ratings) == 0:
            return None
        
        latest = daily_ratings.iloc[0]
        
        if latest['total'] >= rule['min_comments'] and latest['avg_rating'] < rule['threshold']:
            severity = 'high' if latest['avg_rating'] < 2.0 else 'medium'
            
            return self._add_alert(
                'low_rating',
                severity,
                f'{latest["date"].strftime("%Y-%m-%d")} 平均评分仅 {latest["avg_rating"]:.1f} 分',
                {
                    'date': latest['date'].strftime('%Y-%m-%d'),
                    'avg_rating': round(latest['avg_rating'], 2),
                    'total_comments': int(latest['total'])
                }
            )
        
        return None
    
    def get_alerts(self, unread_only=False, limit=20):
        alerts = self.alert_history
        if unread_only:
            alerts = [a for a in alerts if not a['read']]
        return alerts[:limit]
    
    def mark_as_read(self, alert_id):
        for alert in self.alert_history:
            if alert['id'] == alert_id:
                alert['read'] = True
                self._save_alert_history()
                return True
        return False
    
    def mark_all_as_read(self):
        for alert in self.alert_history:
            alert['read'] = True
        self._save_alert_history()
        return True
    
    def get_alert_summary(self):
        total = len(self.alert_history)
        unread = sum(1 for a in self.alert_history if not a['read'])
        high_severity = sum(1 for a in self.alert_history if a['severity'] == 'high' and not a['read'])
        
        return {
            'total': total,
            'unread': unread,
            'high_severity': high_severity
        }


_alert_system = None


def get_alert_system():
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem()
    return _alert_system


if __name__ == '__main__':
    from data_processor import load_all_comments
    
    df = load_all_comments()
    if len(df) > 0:
        system = get_alert_system()
        alerts = system.check_alerts(df)
        
        print(f'检测到 {len(alerts)} 条预警:')
        for alert in alerts:
            if alert:
                print(f'[{alert["severity"].upper()}] {alert["type_name"]}: {alert["message"]}')
        
        summary = system.get_alert_summary()
        print(f'\n预警汇总: 共{summary["total"]}条，未读{summary["unread"]}条，高危{summary["high_severity"]}条')
