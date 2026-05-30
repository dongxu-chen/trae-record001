import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import calculate_statistics
from app_resource_manager import AppResourceManager, Application


@dataclass
class IdleResource:
    app_id: str
    app_name: str
    resource_type: str
    idle_hours: float
    avg_usage: float
    peak_usage: float
    max_usage: float
    current_allocation: float
    suggested_allocation: float
    potential_savings_percent: float
    severity: str
    recommendation: str


@dataclass
class OptimizationSuggestion:
    suggestion_id: str
    category: str
    priority: int
    resource_type: str
    app_id: Optional[str] = None
    app_name: Optional[str] = None
    description: str = ""
    expected_impact: str = ""
    estimated_savings: float = 0.0
    implementation_effort: str = "medium"
    status: str = "pending"


class ResourceOptimizer:
    def __init__(self):
        self.idle_threshold = config.idle_threshold_percent
        self.idle_detection_hours = config.idle_detection_hours
        self.downscale_suggestion_percent = config.idle_downscale_suggestion_percent
        self.app_manager = AppResourceManager()

    def detect_idle_resources(self, df: pd.DataFrame) -> List[IdleResource]:
        idle_resources = []

        cutoff_time = df['ds'].max() - timedelta(hours=self.idle_detection_hours)
        recent_data = df[df['ds'] >= cutoff_time]

        for app_id, app in self.app_manager.apps.items():
            app_data = self.app_manager.generate_app_resource_data(df, app_id)
            recent_app_data = app_data[app_data['ds'] >= cutoff_time]

            if len(recent_app_data) == 0:
                continue

            for resource_type in config.resources.keys():
                values = recent_app_data[resource_type]
                stats = calculate_statistics(values)

                max_hours = self.idle_detection_hours
                idle_periods = 0
                points_per_hour = 60 // config.data_frequency_minutes

                for i in range(0, len(values), points_per_hour):
                    hour_block = values[i:i + points_per_hour]
                    if len(hour_block) > 0 and hour_block.mean() < self.idle_threshold:
                        idle_periods += 1

                if idle_periods >= max_hours * 0.5 and stats['mean'] < self.idle_threshold * 1.5:
                    if stats['p95'] < self.idle_threshold * 2:
                        current_alloc = app.resource_share.get(resource_type, 0.25) * 100
                        suggested_alloc = current_alloc * (1 - self.downscale_suggestion_percent / 100)
                        savings = current_alloc - suggested_alloc

                        if stats['mean'] < self.idle_threshold * 0.3:
                            severity = 'critical'
                        elif stats['mean'] < self.idle_threshold * 0.6:
                            severity = 'high'
                        else:
                            severity = 'medium'

                        recommendation = self._generate_idle_recommendation(
                            app, resource_type, stats, severity, suggested_alloc)

                        idle_resource = IdleResource(
                            app_id=app_id,
                            app_name=app.name,
                            resource_type=resource_type,
                            idle_hours=float(idle_periods),
                            avg_usage=round(stats['mean'], 2),
                            peak_usage=round(stats['p95'], 2),
                            max_usage=round(stats['max'], 2),
                            current_allocation=round(current_alloc, 2),
                            suggested_allocation=round(suggested_alloc, 2),
                            potential_savings_percent=round(savings / current_alloc * 100, 2),
                            severity=severity,
                            recommendation=recommendation
                        )
                        idle_resources.append(idle_resource)

        return sorted(idle_resources, key=lambda x: x.potential_savings_percent, reverse=True)

    def _generate_idle_recommendation(self, app: Application, resource_type: str,
                                       stats: Dict, severity: str,
                                       suggested_alloc: float) -> str:
        res_name = config.resources[resource_type].name

        if severity == 'critical':
            return (f"🔴 {app.name} 的{res_name}严重闲置（均值 {stats['mean']:.1f}% < {self.idle_threshold}%），"
                    f"建议立即降配至 {suggested_alloc:.1f}%，或考虑关闭该资源。")
        elif severity == 'high':
            return (f"🟠 {app.name} 的{res_name}明显闲置（均值 {stats['mean']:.1f}%），"
                    f"建议降配至 {suggested_alloc:.1f}%，预计节省 {self.downscale_suggestion_percent}% 成本。")
        else:
            return (f"🟡 {app.name} 的{res_name}轻度闲置（均值 {stats['mean']:.1f}%），"
                    f"可考虑降配至 {suggested_alloc:.1f}%，观察一段时间后再调整。")

    def generate_optimization_suggestions(self, df: pd.DataFrame,
                                           forecast_summaries: Dict[str, Dict],
                                           idle_resources: List[IdleResource]) -> List[OptimizationSuggestion]:
        suggestions = []

        for idle in idle_resources:
            sug = OptimizationSuggestion(
                suggestion_id=f"idle_{idle.app_id}_{idle.resource_type}_{int(datetime.now().timestamp())}",
                category="idle_resource",
                priority=1 if idle.severity == 'critical' else (2 if idle.severity == 'high' else 3),
                resource_type=idle.resource_type,
                app_id=idle.app_id,
                app_name=idle.app_name,
                description=idle.recommendation,
                expected_impact=f"预计节省 {idle.potential_savings_percent:.1f}% 的{config.resources[idle.resource_type].name}",
                estimated_savings=idle.potential_savings_percent,
                implementation_effort="low"
            )
            suggestions.append(sug)

        for resource_type, res_config in config.resources.items():
            forecast = forecast_summaries[resource_type]

            if forecast['mean_predicted'] < 30 and not forecast['will_exceed_warning']:
                sug = OptimizationSuggestion(
                    suggestion_id=f"scale_down_{resource_type}_{int(datetime.now().timestamp())}",
                    category="over_provisioned",
                    priority=3,
                    resource_type=resource_type,
                    description=(f"整体{res_config.name}使用率较低（均值 {forecast['mean_predicted']:.1f}%），"
                                 f"且无预警风险，建议整体缩容 10-20%。"),
                    expected_impact=f"节省约 10-20% 的{res_config.name}成本",
                    estimated_savings=15.0,
                    implementation_effort="medium"
                )
                suggestions.append(sug)

        suggestions.extend(self._generate_scheduling_optimizations(df))
        suggestions.extend(self._generate_storage_optimizations(df))
        suggestions.extend(self._generate_network_optimizations())

        return sorted(suggestions, key=lambda x: (x.priority, -x.estimated_savings))

    def _generate_scheduling_optimizations(self, df: pd.DataFrame) -> List[OptimizationSuggestion]:
        suggestions = []

        peak_hours = set()
        valley_hours = set()

        for resource_type in config.resources.keys():
            values = df[resource_type]
            timestamps = df['ds']
            hourly_avg = values.groupby(timestamps.dt.hour).mean()
            threshold = hourly_avg.mean()
            for h in range(24):
                if hourly_avg[h] > threshold * 1.3:
                    peak_hours.add(h)
                elif hourly_avg[h] < threshold * 0.7:
                    valley_hours.add(h)

        if peak_hours and valley_hours:
            peak_str = ', '.join([f"{h}:00" for h in sorted(peak_hours)])
            valley_str = ', '.join([f"{h}:00" for h in sorted(valley_hours)])

            sug = OptimizationSuggestion(
                suggestion_id=f"schedule_{int(datetime.now().timestamp())}",
                category="scheduling",
                priority=2,
                resource_type="cpu",
                description=(f"检测到明显的使用峰谷。高峰时段: {peak_str}，低谷时段: {valley_str}。"
                             f"建议将批处理、备份等非实时任务调度至低谷时段执行。"),
                expected_impact="平滑资源曲线，提高整体利用率 15-25%",
                estimated_savings=20.0,
                implementation_effort="medium"
            )
            suggestions.append(sug)

        return suggestions

    def _generate_storage_optimizations(self, df: pd.DataFrame) -> List[OptimizationSuggestion]:
        suggestions = []
        disk_values = df['disk']

        stats = calculate_statistics(disk_values)

        if stats['mean'] > 60 and stats['p95'] > 75:
            growth_rate = (disk_values.iloc[-1] - disk_values.iloc[0]) / disk_values.iloc[0] * 100
            days = (df['ds'].iloc[-1] - df['ds'].iloc[0]).days
            monthly_growth = growth_rate / days * 30

            sug = OptimizationSuggestion(
                suggestion_id=f"storage_cleanup_{int(datetime.now().timestamp())}",
                category="storage",
                priority=2,
                resource_type="disk",
                description=(f"磁盘使用率较高（均值 {stats['mean']:.1f}%，P95 {stats['p95']:.1f}%），"
                             f"月增长率约 {monthly_growth:.1f}%。建议进行磁盘清理，"
                             f"删除过期日志、临时文件和历史快照。"),
                expected_impact=f"预计释放 10-25% 的磁盘空间，延缓扩容需求",
                estimated_savings=15.0,
                implementation_effort="low"
            )
            suggestions.append(sug)

        if stats['max'] < 40 and stats['mean'] < 30:
            sug = OptimizationSuggestion(
                suggestion_id=f"storage_compress_{int(datetime.now().timestamp())}",
                category="storage",
                priority=3,
                resource_type="disk",
                description=(f"磁盘使用率较低（均值 {stats['mean']:.1f}%）。"
                             f"建议启用数据压缩和重复数据删除功能，"
                             f"或考虑更换为更低成本的存储介质。"),
                expected_impact="降低存储成本 20-40%",
                estimated_savings=30.0,
                implementation_effort="high"
            )
            suggestions.append(sug)

        return suggestions

    def _generate_network_optimizations(self) -> List[OptimizationSuggestion]:
        sug = OptimizationSuggestion(
            suggestion_id=f"cdn_cache_{int(datetime.now().timestamp())}",
            category="network",
            priority=3,
            resource_type="cpu",
            description=("建议启用CDN缓存静态资源，减少源站请求压力。"
                         "包括图片、CSS/JS、API响应等可缓存内容。"),
            expected_impact="降低服务器 CPU 和带宽负载 20-40%",
            estimated_savings=25.0,
            implementation_effort="medium"
        )
        return [sug]

    def get_optimization_summary(self, suggestions: List[OptimizationSuggestion]) -> Dict[str, any]:
        category_stats = {}
        priority_stats = {1: 0, 2: 0, 3: 0}
        total_savings = 0.0

        for sug in suggestions:
            if sug.category not in category_stats:
                category_stats[sug.category] = {'count': 0, 'savings': 0.0}
            category_stats[sug.category]['count'] += 1
            category_stats[sug.category]['savings'] += sug.estimated_savings

            if sug.priority in priority_stats:
                priority_stats[sug.priority] += 1

            total_savings += sug.estimated_savings

        return {
            'total_suggestions': len(suggestions),
            'by_category': category_stats,
            'by_priority': priority_stats,
            'estimated_total_savings_percent': round(total_savings, 2),
            'high_priority_count': priority_stats.get(1, 0),
            'medium_priority_count': priority_stats.get(2, 0),
            'low_priority_count': priority_stats.get(3, 0)
        }

    def generate_optimization_report(self, df: pd.DataFrame,
                                      forecast_summaries: Dict[str, Dict]) -> Dict[str, any]:
        idle_resources = self.detect_idle_resources(df)
        suggestions = self.generate_optimization_suggestions(df, forecast_summaries, idle_resources)
        summary = self.get_optimization_summary(suggestions)

        return {
            'timestamp': datetime.now(),
            'idle_resources': idle_resources,
            'suggestions': suggestions,
            'summary': summary
        }

    def get_resource_usage_distribution(self, df: pd.DataFrame) -> pd.DataFrame:
        all_app_data = self.app_manager.generate_all_apps_data(df)

        distribution = []
        for app_id in self.app_manager.apps.keys():
            app = self.app_manager.apps[app_id]
            app_data = all_app_data[all_app_data['app_id'] == app_id]

            row = {
                'app_id': app_id,
                'app_name': app.name,
                'priority': app.priority,
                'sla': app.sla_requirement
            }

            for resource_type in config.resources.keys():
                stats = calculate_statistics(app_data[resource_type])
                row[f'{resource_type}_mean'] = stats['mean']
                row[f'{resource_type}_peak'] = stats['p95']
                row[f'{resource_type}_max'] = stats['max']
                row[f'{resource_type}_allocation'] = app.resource_share.get(resource_type, 0.25) * 100

            distribution.append(row)

        return pd.DataFrame(distribution)

    def simulate_optimization_impact(self, df: pd.DataFrame,
                                      suggestion: OptimizationSuggestion) -> Dict[str, any]:
        if suggestion.category == 'idle_resource' and suggestion.app_id:
            app_id = suggestion.app_id
            resource_type = suggestion.resource_type

            app_data = self.app_manager.generate_app_resource_data(df, app_id)
            current_stats = calculate_statistics(app_data[resource_type])

            reduction = suggestion.estimated_savings / 100
            simulated_values = app_data[resource_type] * (1 - reduction)
            new_stats = calculate_statistics(simulated_values)

            impact = {
                'current_mean': current_stats['mean'],
                'simulated_mean': new_stats['mean'],
                'current_peak': current_stats['p95'],
                'simulated_peak': new_stats['p95'],
                'reduction_percent': suggestion.estimated_savings,
                'is_safe': new_stats['max'] < 80,
                'recommendation': '可以安全执行' if new_stats['max'] < 70 else '建议先观察再执行'
            }
            return impact

        return {'note': '此类型建议暂不支持模拟'}
