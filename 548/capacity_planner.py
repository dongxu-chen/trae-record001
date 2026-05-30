import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression

from config import config
from utils import calculate_statistics, detect_peak_hours


class CapacityPlanner:
    def __init__(self):
        self.resource_costs = {
            'cpu': 100,
            'memory': 80,
            'disk': 50
        }
        self.safety_buffer = config.safety_buffer_percent

    def analyze_resource_trend(self, df: pd.DataFrame, resource_type: str) -> Dict[str, any]:
        data = df[['ds', resource_type]].copy()
        data['days_passed'] = (data['ds'] - data['ds'].min()).dt.total_seconds() / (24 * 3600)

        X = data[['days_passed']].values
        y = data[resource_type].values

        model = LinearRegression()
        model.fit(X, y)

        slope = model.coef_[0]
        intercept = model.intercept_
        r_squared = model.score(X, y)

        current_value = y[-1]
        res_config = config.resources[resource_type]

        warning_with_buffer = res_config.warning_threshold * (1 - self.safety_buffer / 100)
        critical_with_buffer = res_config.critical_threshold * (1 - self.safety_buffer / 100)

        days_to_warning = None
        days_to_critical = None

        if slope > 0:
            if warning_with_buffer > current_value:
                days_to_warning = (warning_with_buffer - intercept) / slope - data['days_passed'].max()
                if days_to_warning < 0:
                    days_to_warning = 0

            if critical_with_buffer > current_value:
                days_to_critical = (critical_with_buffer - intercept) / slope - data['days_passed'].max()
                if days_to_critical < 0:
                    days_to_critical = 0

        predicted_30d = round(model.predict([[data['days_passed'].max() + 30]])[0], 2)
        predicted_90d = round(model.predict([[data['days_passed'].max() + 90]])[0], 2)

        buffer_30d = predicted_30d * (1 + self.safety_buffer / 100)
        buffer_90d = predicted_90d * (1 + self.safety_buffer / 100)

        return {
            'resource_type': resource_type,
            'slope_per_day': round(slope, 4),
            'intercept': round(intercept, 2),
            'r_squared': round(r_squared, 4),
            'current_value': round(current_value, 2),
            'trend_direction': 'increasing' if slope > 0.01 else ('decreasing' if slope < -0.01 else 'stable'),
            'days_to_warning': round(days_to_warning, 1) if days_to_warning is not None else None,
            'days_to_critical': round(days_to_critical, 1) if days_to_critical is not None else None,
            'warning_threshold_with_buffer': round(warning_with_buffer, 2),
            'critical_threshold_with_buffer': round(critical_with_buffer, 2),
            'predicted_30d': predicted_30d,
            'predicted_90d': predicted_90d,
            'predicted_30d_with_buffer': round(buffer_30d, 2),
            'predicted_90d_with_buffer': round(buffer_90d, 2)
        }

    def calculate_capacity_headroom(self, df: pd.DataFrame, resource_type: str) -> Dict[str, any]:
        res_config = config.resources[resource_type]
        values = df[resource_type]

        stats = calculate_statistics(values)

        headroom_current = res_config.max_capacity - stats['mean']
        headroom_peak = res_config.max_capacity - stats['p95']

        effective_headroom_current = headroom_current - self.safety_buffer
        effective_headroom_peak = headroom_peak - self.safety_buffer

        warning_buffer = res_config.warning_threshold - stats['p95'] - self.safety_buffer
        critical_buffer = res_config.critical_threshold - stats['p99'] - self.safety_buffer

        effective_warning_threshold = res_config.warning_threshold - self.safety_buffer
        effective_critical_threshold = res_config.critical_threshold - self.safety_buffer

        return {
            'resource_type': resource_type,
            'headroom_average': round(headroom_current, 2),
            'headroom_peak': round(headroom_peak, 2),
            'effective_headroom_average': round(effective_headroom_current, 2),
            'effective_headroom_peak': round(effective_headroom_peak, 2),
            'warning_buffer': round(warning_buffer, 2),
            'critical_buffer': round(critical_buffer, 2),
            'utilization_current': round(stats['mean'], 2),
            'utilization_peak': round(stats['p95'], 2),
            'max_observed': round(stats['max'], 2),
            'safety_buffer_percent': self.safety_buffer,
            'effective_warning_threshold': round(effective_warning_threshold, 2),
            'effective_critical_threshold': round(effective_critical_threshold, 2)
        }

    def get_peak_hour_analysis(self, df: pd.DataFrame, resource_type: str) -> Dict[str, any]:
        peak_hours = detect_peak_hours(df, resource_type)

        df_hourly = df.copy()
        df_hourly['hour'] = df_hourly['ds'].dt.hour
        df_hourly['is_weekday'] = df_hourly['ds'].dt.dayofweek < 5

        weekday_peak = df_hourly[df_hourly['is_weekday']].groupby('hour')[resource_type].mean()
        weekend_peak = df_hourly[~df_hourly['is_weekday']].groupby('hour')[resource_type].mean()

        return {
            'resource_type': resource_type,
            'peak_hours': peak_hours,
            'off_peak_hours': [h for h in range(24) if h not in peak_hours],
            'weekday_hourly_avg': weekday_peak.round(2).to_dict(),
            'weekend_hourly_avg': weekend_peak.round(2).to_dict(),
            'peak_value_weekday': round(weekday_peak.max(), 2),
            'peak_value_weekend': round(weekend_peak.max(), 2),
            'peak_reduction_percent': round(((weekday_peak.max() - weekend_peak.max()) / weekday_peak.max() * 100), 2),
            'recommended_capacity_weekday': round(weekday_peak.max() * (1 + self.safety_buffer / 100), 2),
            'recommended_capacity_weekend': round(weekend_peak.max() * (1 + self.safety_buffer / 100), 2)
        }

    def generate_scaling_recommendations(self, trend_analysis: Dict,
                                          headroom: Dict,
                                          forecast_summary: Dict) -> Dict[str, any]:
        resource_type = trend_analysis['resource_type']
        res_config = config.resources[resource_type]

        recommendations = []
        urgency = 'low'
        risk_level = 'low'

        effective_warning = headroom.get('effective_warning_threshold',
                                          res_config.warning_threshold - self.safety_buffer)
        effective_critical = headroom.get('effective_critical_threshold',
                                           res_config.critical_threshold - self.safety_buffer)

        if forecast_summary['will_exceed_critical']:
            urgency = 'critical'
            risk_level = 'critical'
            recommendations.append({
                'priority': 1,
                'type': 'immediate',
                'action': f'立即评估并增加{res_config.name}容量（含{self.safety_buffer}%安全缓冲）',
                'reason': f'预计未来24小时内{res_config.name}将超过{res_config.critical_threshold}%，'
                          f'含安全缓冲后有效危险阈值为{effective_critical}%',
                'impact': '高 - 可能导致服务中断'
            })
        elif forecast_summary['will_exceed_warning']:
            urgency = 'high'
            risk_level = 'medium'
            recommendations.append({
                'priority': 1,
                'type': 'urgent',
                'action': f'尽快安排{res_config.name}扩容（含{self.safety_buffer}%安全缓冲）',
                'reason': f'预计未来24小时内{res_config.name}将超过{res_config.warning_threshold}%，'
                          f'含安全缓冲后有效警告阈值为{effective_warning}%',
                'impact': '中 - 可能影响服务性能'
            })

        effective_headroom_peak = headroom.get('effective_headroom_peak',
                                                headroom['headroom_peak'] - self.safety_buffer)
        if effective_headroom_peak < 10:
            urgency = max(urgency, 'high')
            risk_level = max(risk_level, 'medium')
            recommendations.append({
                'priority': 2,
                'type': 'capacity',
                'action': f'规划{res_config.name}扩容，预留{self.safety_buffer}%安全缓冲+15%峰值余量',
                'reason': f'当前有效峰值余量仅为{effective_headroom_peak}%（已扣除{self.safety_buffer}%安全缓冲），低于安全阈值10%',
                'impact': '中 - 资源紧张'
            })

        if trend_analysis['trend_direction'] == 'increasing':
            if trend_analysis['days_to_critical'] is not None and trend_analysis['days_to_critical'] < 30:
                urgency = max(urgency, 'high')
                recommendations.append({
                    'priority': 3,
                    'type': 'trend',
                    'action': f'在{trend_analysis["days_to_critical"]}天内完成{res_config.name}扩容（含安全缓冲）',
                    'reason': f'按当前增长趋势（含{self.safety_buffer}%安全缓冲），{trend_analysis["days_to_critical"]}天后将达到有效危险阈值',
                    'impact': '中 - 需要提前规划'
                })
            elif trend_analysis['days_to_warning'] is not None and trend_analysis['days_to_warning'] < 90:
                urgency = max(urgency, 'medium')
                recommendations.append({
                    'priority': 4,
                    'type': 'trend',
                    'action': f'在{trend_analysis["days_to_warning"]}天内规划{res_config.name}扩容（含安全缓冲）',
                    'reason': f'按当前增长趋势（含{self.safety_buffer}%安全缓冲），{trend_analysis["days_to_warning"]}天后将达到有效警告阈值',
                    'impact': '低 - 有充足规划时间'
                })

        if len(recommendations) == 0:
            recommendations.append({
                'priority': 1,
                'type': 'maintenance',
                'action': f'维持当前{res_config.name}配置，定期监控（已预留{self.safety_buffer}%安全缓冲）',
                'reason': f'{res_config.name}使用率稳定在安全范围内，安全缓冲充足',
                'impact': '低 - 无需立即操作'
            })

        estimated_cost = self._estimate_scaling_cost(resource_type, headroom, trend_analysis)

        return {
            'resource_type': resource_type,
            'urgency': urgency,
            'risk_level': risk_level,
            'recommendations': sorted(recommendations, key=lambda x: x['priority']),
            'estimated_cost': estimated_cost,
            'safety_buffer_percent': self.safety_buffer
        }

    def _estimate_scaling_cost(self, resource_type: str, headroom: Dict,
                                trend_analysis: Dict) -> Dict[str, float]:
        base_cost = self.resource_costs[resource_type]

        current_utilization = headroom['utilization_current']
        target_utilization = (100 - self.safety_buffer) * 0.7

        if current_utilization <= target_utilization:
            scaling_factor = 0
        else:
            scaling_factor = (current_utilization / target_utilization) - 1

        if trend_analysis['trend_direction'] == 'increasing':
            predicted_with_buffer = trend_analysis.get('predicted_30d_with_buffer',
                                                        trend_analysis['predicted_30d'] * (1 + self.safety_buffer / 100))
            predicted_increase = predicted_with_buffer - trend_analysis['current_value']
            if predicted_increase > 5:
                scaling_factor = max(scaling_factor, 0.2 + self.safety_buffer / 100)

        return {
            'monthly_current': round(base_cost, 2),
            'monthly_proposed': round(base_cost * (1 + scaling_factor), 2),
            'monthly_increase': round(base_cost * scaling_factor, 2),
            'annual_increase': round(base_cost * scaling_factor * 12, 2),
            'scaling_factor_percent': round(scaling_factor * 100, 2),
            'safety_buffer_cost': round(base_cost * self.safety_buffer / 100, 2)
        }

    def generate_full_capacity_report(self, df: pd.DataFrame, resource_type: str,
                                       forecast_summary: Dict) -> Dict[str, any]:
        trend = self.analyze_resource_trend(df, resource_type)
        headroom = self.calculate_capacity_headroom(df, resource_type)
        peak_analysis = self.get_peak_hour_analysis(df, resource_type)
        recommendations = self.generate_scaling_recommendations(trend, headroom, forecast_summary)

        return {
            'resource_type': resource_type,
            'trend_analysis': trend,
            'capacity_headroom': headroom,
            'peak_hour_analysis': peak_analysis,
            'recommendations': recommendations,
            'safety_buffer_percent': self.safety_buffer
        }

    def get_overall_capacity_summary(self, df: pd.DataFrame,
                                      forecast_summaries: Dict[str, Dict]) -> Dict[str, any]:
        reports = {}
        overall_risk = 'low'
        overall_urgency = 'low'

        for resource_type in config.resources.keys():
            report = self.generate_full_capacity_report(df, resource_type, forecast_summaries[resource_type])
            reports[resource_type] = report

            risk_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            current_risk = report['recommendations']['risk_level']
            current_urgency = report['recommendations']['urgency']

            if risk_order[current_risk] > risk_order[overall_risk]:
                overall_risk = current_risk
            if risk_order[current_urgency] > risk_order[overall_urgency]:
                overall_urgency = current_urgency

        return {
            'overall_risk': overall_risk,
            'overall_urgency': overall_urgency,
            'reports': reports,
            'summary_timestamp': datetime.now(),
            'safety_buffer_percent': self.safety_buffer
        }
