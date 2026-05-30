from collections import deque, defaultdict
from datetime import datetime, timedelta
import math
from app.redis_client import get_redis


class SlowLogPredictor:
    def __init__(self, history_window_hours=24):
        self.redis = get_redis()
        self.history_window_hours = history_window_hours
        self.time_series_data = deque(maxlen=history_window_hours * 60)
        self.hourly_stats = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'max_duration': 0,
            'commands': defaultdict(int)
        })

    def collect_historical_data(self, hours=24):
        try:
            logs = self.redis.execute_command('SLOWLOG GET', 10000)
            self._process_logs(logs)
            return len(logs)
        except Exception as e:
            print(f"Error collecting historical data: {e}")
            return 0

    def _process_logs(self, logs):
        current_time = datetime.now()
        self.time_series_data.clear()
        self.hourly_stats.clear()

        for log in logs:
            log_id = log[0]
            timestamp = log[1]
            duration = log[2] / 1000
            command = log[3][0] if len(log) > 3 and log[3] else 'UNKNOWN'
            
            log_time = datetime.fromtimestamp(timestamp)
            hour_key = log_time.strftime('%Y-%m-%d %H:00')
            
            self.hourly_stats[hour_key]['count'] += 1
            self.hourly_stats[hour_key]['total_duration'] += duration
            self.hourly_stats[hour_key]['avg_duration'] = (
                self.hourly_stats[hour_key]['total_duration'] / 
                self.hourly_stats[hour_key]['count']
            )
            self.hourly_stats[hour_key]['max_duration'] = max(
                self.hourly_stats[hour_key]['max_duration'],
                duration
            )
            self.hourly_stats[hour_key]['commands'][command] += 1

            self.time_series_data.append({
                'timestamp': timestamp,
                'datetime': log_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'command': command
            })

    def predict_slowlog_trend(self, hours_ahead=24):
        hourly_counts = self._get_hourly_counts()
        
        if len(hourly_counts) < 3:
            return {
                'error': 'Insufficient data for prediction',
                'predictions': [],
                'confidence': 0
            }

        trend = self._calculate_trend(hourly_counts)
        seasonal = self._calculate_seasonal(hourly_counts)
        predictions = self._exponential_smoothing_forecast(
            hourly_counts, hours_ahead, trend, seasonal
        )

        confidence = self._calculate_confidence(hourly_counts, predictions)

        return {
            'predictions': predictions,
            'trend': trend,
            'seasonal_patterns': seasonal,
            'confidence': confidence,
            'historical_hours': len(hourly_counts),
            'total_slowlogs': sum(h['count'] for h in hourly_counts)
        }

    def _get_hourly_counts(self):
        counts = []
        sorted_hours = sorted(self.hourly_stats.keys())
        for hour in sorted_hours:
            stats = self.hourly_stats[hour]
            counts.append({
                'hour': hour,
                'count': stats['count'],
                'avg_duration': stats['avg_duration'],
                'max_duration': stats['max_duration']
            })
        return counts

    def _calculate_trend(self, hourly_counts):
        if len(hourly_counts) < 2:
            return {'slope': 0, 'direction': 'stable'}
        
        x = list(range(len(hourly_counts)))
        y = [h['count'] for h in hourly_counts]
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        
        if slope > 0.5:
            direction = 'increasing'
        elif slope < -0.5:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'slope': slope,
            'direction': direction,
            'description': self._get_trend_description(direction, slope)
        }

    def _get_trend_description(self, direction, slope):
        descriptions = {
            'increasing': f'慢查询数量呈上升趋势，每小时增加约{abs(slope):.1f}次',
            'decreasing': f'慢查询数量呈下降趋势，每小时减少约{abs(slope):.1f}次',
            'stable': '慢查询数量保持稳定'
        }
        return descriptions[direction]

    def _calculate_seasonal(self, hourly_counts):
        hour_of_day_pattern = defaultdict(list)
        
        for h in hourly_counts:
            hour = datetime.strptime(h['hour'], '%Y-%m-%d %H:00').hour
            hour_of_day_pattern[hour].append(h['count'])
        
        seasonal = []
        for hour in range(24):
            counts = hour_of_day_pattern.get(hour, [])
            if counts:
                avg_count = sum(counts) / len(counts)
                seasonal.append({
                    'hour': hour,
                    'avg_count': avg_count,
                    'peak': avg_count > (sum(counts) / len(counts) if counts else 0) * 1.5
                })
        
        peak_hours = sorted([s for s in seasonal if s['peak']], key=lambda x: x['avg_count'], reverse=True)
        
        return {
            'hourly_pattern': seasonal,
            'peak_hours': peak_hours[:5],
            'off_peak_hours': sorted([s for s in seasonal if not s['peak']], key=lambda x: x['avg_count'])[:5]
        }

    def _exponential_smoothing_forecast(self, hourly_counts, hours_ahead, trend, seasonal):
        alpha = 0.3
        beta = 0.1
        gamma = 0.1
        
        counts = [h['count'] for h in hourly_counts]
        durations = [h['avg_duration'] for h in hourly_counts]
        
        level = counts[0]
        trend_component = trend['slope']
        last_hour = datetime.strptime(hourly_counts[-1]['hour'], '%Y-%m-%d %H:00')
        
        predictions = []
        seasonal_hours = {s['hour']: s['avg_count'] for s in seasonal['hourly_pattern']}
        
        for i in range(hours_ahead):
            prediction_hour = last_hour + timedelta(hours=i + 1)
            hour_idx = prediction_hour.hour
            
            seasonal_factor = seasonal_hours.get(hour_idx, 1)
            
            if i == 0:
                level = alpha * counts[-1] + (1 - alpha) * (level + trend_component)
                trend_component = beta * (level - counts[-1]) + (1 - beta) * trend_component
            
            forecast = (level + trend_component * (i + 1)) * (seasonal_factor / max(seasonal_factor, 1))
            forecast = max(0, forecast)
            
            avg_duration = durations[-1] if durations else 0
            
            predictions.append({
                'hour': prediction_hour.strftime('%Y-%m-%d %H:00'),
                'predicted_count': round(forecast),
                'predicted_avg_duration': round(avg_duration, 2),
                'predicted_total_duration': round(forecast * avg_duration, 2),
                'hour_of_day': hour_idx,
                'is_peak': seasonal_factor > 1.2
            })
        
        return predictions

    def _calculate_confidence(self, hourly_counts, predictions):
        if len(hourly_counts) < 5:
            return 50
        
        counts = [h['count'] for h in hourly_counts]
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)
        
        cv = std_dev / mean if mean > 0 else 1
        
        if cv < 0.2:
            base_confidence = 90
        elif cv < 0.5:
            base_confidence = 75
        elif cv < 1.0:
            base_confidence = 60
        else:
            base_confidence = 40
        
        data_factor = min(len(hourly_counts) / 24, 1)
        
        confidence = base_confidence * data_factor
        return round(min(confidence, 95))

    def predict_hot_commands(self, top_n=10):
        command_trends = defaultdict(list)
        
        sorted_hours = sorted(self.hourly_stats.keys())
        for hour in sorted_hours:
            for cmd, count in self.hourly_stats[hour]['commands'].items():
                command_trends[cmd].append({
                    'hour': hour,
                    'count': count
                })
        
        predictions = []
        for cmd, history in command_trends.items():
            if len(history) >= 3:
                counts = [h['count'] for h in history]
                trend = self._calculate_simple_trend(counts)
                forecast = self._simple_forecast(counts, 24)
                
                predictions.append({
                    'command': cmd,
                    'historical_count': sum(counts),
                    'predicted_24h_count': forecast,
                    'trend': trend,
                    'growth_rate': (forecast - counts[-1]) / max(counts[-1], 1) * 100
                })
        
        return sorted(predictions, key=lambda x: x['predicted_24h_count'], reverse=True)[:top_n]

    def _calculate_simple_trend(self, counts):
        if len(counts) < 2:
            return 'stable'
        
        first_half = sum(counts[:len(counts)//2]) / max(len(counts)//2, 1)
        second_half = sum(counts[len(counts)//2:]) / max(len(counts) - len(counts)//2, 1)
        
        if second_half > first_half * 1.2:
            return 'increasing'
        elif second_half < first_half * 0.8:
            return 'decreasing'
        else:
            return 'stable'

    def _simple_forecast(self, counts, periods):
        if not counts:
            return 0
        
        recent_avg = sum(counts[-min(3, len(counts)):]) / min(3, len(counts))
        total = recent_avg * periods
        return round(total)

    def get_risk_assessment(self):
        prediction = self.predict_slowlog_trend(24)
        
        if 'error' in prediction:
            return {
                'risk_level': 'unknown',
                'message': '数据不足，无法评估风险'
            }
        
        total_predicted = sum(p['predicted_count'] for p in prediction['predictions'])
        trend = prediction['trend']
        confidence = prediction['confidence']
        
        if trend['direction'] == 'increasing' and total_predicted > 100:
            risk_level = 'high'
            severity = '严重'
        elif trend['direction'] == 'increasing' or total_predicted > 50:
            risk_level = 'medium'
            severity = '中等'
        elif total_predicted > 20:
            risk_level = 'low'
            severity = '低'
        else:
            risk_level = 'normal'
            severity = '正常'
        
        return {
            'risk_level': risk_level,
            'severity': severity,
            'confidence': confidence,
            'predicted_24h_count': total_predicted,
            'trend': trend,
            'peak_count': max(p['predicted_count'] for p in prediction['predictions']) if prediction['predictions'] else 0,
            'recommendations': self._get_risk_recommendations(risk_level, prediction)
        }

    def _get_risk_recommendations(self, risk_level, prediction):
        recommendations = []
        
        if risk_level in ['high', 'medium']:
            recommendations.append('建议增加Redis实例资源或优化慢查询命令')
            
            peak_hours = prediction.get('seasonal_patterns', {}).get('peak_hours', [])
            if peak_hours:
                peak_times = ', '.join([f"{p['hour']:02d}:00" for p in peak_hours[:3]])
                recommendations.append(f'高峰时段 {peak_times} 建议减少批量操作')
        
        if prediction['trend']['direction'] == 'increasing':
            recommendations.append('慢查询呈上升趋势，建议排查近期代码变更')
        
        if not recommendations:
            recommendations.append('当前慢查询情况良好，继续保持监控')
        
        return recommendations

    def get_prediction_summary(self):
        trend_prediction = self.predict_slowlog_trend(24)
        hot_commands = self.predict_hot_commands(5)
        risk = self.get_risk_assessment()
        
        return {
            'trend_prediction': trend_prediction,
            'hot_commands_prediction': hot_commands,
            'risk_assessment': risk,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
