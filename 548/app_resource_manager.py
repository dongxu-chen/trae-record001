import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import calculate_statistics


@dataclass
class Application:
    app_id: str
    name: str
    priority: int = 1
    resource_share: Dict[str, float] = field(default_factory=lambda: {'cpu': 0.25, 'memory': 0.25, 'disk': 0.25})
    sla_requirement: float = 99.9
    description: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ResourceCompetition:
    resource_type: str
    competing_apps: List[str]
    correlation: float
    impact_score: float
    recommendation: str


class AppResourceManager:
    def __init__(self):
        self.apps: Dict[str, Application] = {}
        self._initialize_default_apps()

    def _initialize_default_apps(self):
        self.apps = {
            'web_app': Application(
                app_id='web_app',
                name='Web 前端服务',
                priority=1,
                resource_share={'cpu': 0.35, 'memory': 0.30, 'disk': 0.20},
                sla_requirement=99.95,
                description='面向用户的Web界面服务，对延迟敏感',
                tags=['customer-facing', 'latency-sensitive']
            ),
            'api_service': Application(
                app_id='api_service',
                name='API 网关服务',
                priority=1,
                resource_share={'cpu': 0.30, 'memory': 0.25, 'disk': 0.15},
                sla_requirement=99.99,
                description='核心API网关，处理所有业务请求',
                tags=['core', 'customer-facing']
            ),
            'backend_job': Application(
                app_id='backend_job',
                name='后台批处理服务',
                priority=3,
                resource_share={'cpu': 0.20, 'memory': 0.25, 'disk': 0.35},
                sla_requirement=95.0,
                description='异步批处理任务，对延迟不敏感',
                tags=['batch', 'non-critical']
            ),
            'database': Application(
                app_id='database',
                name='数据库服务',
                priority=1,
                resource_share={'cpu': 0.15, 'memory': 0.20, 'disk': 0.30},
                sla_requirement=99.999,
                description='主数据库集群，存储核心业务数据',
                tags=['core', 'database', 'data']
            )
        }

    def add_app(self, app: Application) -> None:
        self.apps[app.app_id] = app

    def remove_app(self, app_id: str) -> None:
        if app_id in self.apps:
            del self.apps[app_id]

    def generate_app_resource_data(self, df: pd.DataFrame,
                                     app_id: str) -> pd.DataFrame:
        if app_id not in self.apps:
            raise ValueError(f"应用 {app_id} 不存在")

        app = self.apps[app_id]
        result = pd.DataFrame({'ds': df['ds']})

        for resource_type in config.resources.keys():
            share = app.resource_share.get(resource_type, 0.25)
            base_noise = np.random.normal(0, 2, len(df))
            result[resource_type] = (df[resource_type] * share) + base_noise
            result[resource_type] = result[resource_type].clip(0, 100)

        result['app_id'] = app_id
        result['app_name'] = app.name
        return result

    def generate_all_apps_data(self, df: pd.DataFrame) -> pd.DataFrame:
        all_data = []
        for app_id in self.apps.keys():
            app_data = self.generate_app_resource_data(df, app_id)
            all_data.append(app_data)
        return pd.concat(all_data, ignore_index=True)

    def calculate_cross_app_correlation(self, df: pd.DataFrame,
                                         resource_type: str) -> pd.DataFrame:
        all_app_data = self.generate_all_apps_data(df)
        app_pivot = all_app_data.pivot(index='ds', columns='app_id', values=resource_type)
        correlation_matrix = app_pivot.corr()
        return correlation_matrix

    def detect_resource_competition(self, df: pd.DataFrame,
                                     resource_type: str) -> List[ResourceCompetition]:
        correlation_matrix = self.calculate_cross_app_correlation(df, resource_type)
        competitions = []
        threshold = config.cross_app_correlation_threshold

        app_ids = list(self.apps.keys())
        for i in range(len(app_ids)):
            for j in range(i + 1, len(app_ids)):
                app1, app2 = app_ids[i], app_ids[j]
                corr = correlation_matrix.loc[app1, app2]

                if abs(corr) >= threshold:
                    app1_priority = self.apps[app1].priority
                    app2_priority = self.apps[app2].priority
                    priority_diff = abs(app1_priority - app2_priority)

                    impact_score = abs(corr) * (1 + priority_diff * 0.1)

                    if corr > 0:
                        recommendation = self._generate_positive_competition_recommendation(
                            app1, app2, corr)
                    else:
                        recommendation = self._generate_negative_competition_recommendation(
                            app1, app2, corr)

                    competitions.append(ResourceCompetition(
                        resource_type=resource_type,
                        competing_apps=[app1, app2],
                        correlation=round(float(corr), 4),
                        impact_score=round(float(impact_score), 4),
                        recommendation=recommendation
                    ))

        return sorted(competitions, key=lambda x: x.impact_score, reverse=True)

    def _generate_positive_competition_recommendation(self, app1_id: str,
                                                       app2_id: str,
                                                       correlation: float) -> str:
        app1 = self.apps[app1_id]
        app2 = self.apps[app2_id]

        if app1.priority == 1 and app2.priority == 1:
            return (f"⚠️ 高优先级应用 [{app1.name}] 和 [{app2.name}] 存在强资源竞争 "
                    f"(相关系数 {correlation:.2f})，建议进行资源隔离，"
                    f"或错峰调度以避免相互影响。")
        elif app1.priority < app2.priority:
            return (f"📊 [{app1.name}](优先级 {app1.priority}) 和 [{app2.name}] "
                    f"(优先级 {app2.priority}) 资源使用正相关 ({correlation:.2f})，"
                    f"建议优先保障 [{app1.name}] 的资源配额。")
        elif app2.priority < app1.priority:
            return (f"📊 [{app2.name}](优先级 {app2.priority}) 和 [{app1.name}] "
                    f"(优先级 {app1.priority}) 资源使用正相关 ({correlation:.2f})，"
                    f"建议优先保障 [{app2.name}] 的资源配额。")
        else:
            return (f"📊 [{app1.name}] 和 [{app2.name}] 资源使用模式正相关 "
                    f"({correlation:.2f})，可考虑合并部署或统一调度。")

    def _generate_negative_competition_recommendation(self, app1_id: str,
                                                       app2_id: str,
                                                       correlation: float) -> str:
        app1 = self.apps[app1_id]
        app2 = self.apps[app2_id]
        return (f"💡 [{app1.name}] 和 [{app2.name}] 资源使用负相关 "
                f"({correlation:.2f})，峰谷互补，适合共享资源池，"
                f"可在同一主机上部署以提高资源利用率。")

    def analyze_app_water_level_impact(self, df: pd.DataFrame,
                                        forecast_summaries: Dict[str, Dict]) -> Dict:
        impact_analysis = {}

        for resource_type in config.resources.keys():
            forecast = forecast_summaries[resource_type]
            competitions = self.detect_resource_competition(df, resource_type)

            high_risk_apps = []
            for comp in competitions:
                if comp.impact_score >= 0.7:
                    for app_id in comp.competing_apps:
                        if app_id not in high_risk_apps:
                            high_risk_apps.append(app_id)

            impact_analysis[resource_type] = {
                'resource_type': resource_type,
                'overall_utilization': forecast['mean_predicted'],
                'will_exceed_warning': forecast['will_exceed_warning'],
                'will_exceed_critical': forecast['will_exceed_critical'],
                'high_risk_applications': high_risk_apps,
                'competitions': competitions,
                'app_resource_usage': self._get_app_resource_usage(df, resource_type)
            }

        return impact_analysis

    def _get_app_resource_usage(self, df: pd.DataFrame, resource_type: str) -> Dict[str, Dict]:
        all_app_data = self.generate_all_apps_data(df)
        usage = {}

        for app_id in self.apps.keys():
            app_data = all_app_data[all_app_data['app_id'] == app_id][resource_type]
            stats = calculate_statistics(app_data)
            usage[app_id] = {
                'app_name': self.apps[app_id].name,
                'priority': self.apps[app_id].priority,
                'share': self.apps[app_id].resource_share.get(resource_type, 0.25),
                'mean': stats['mean'],
                'peak': stats['p95'],
                'max': stats['max']
            }

        return usage

    def get_app_priority_order(self) -> List[Application]:
        return sorted(self.apps.values(), key=lambda x: (x.priority, -x.sla_requirement))

    def simulate_resource_allocation(self, total_resources: Dict[str, float],
                                      df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        allocation = {}
        priority_order = self.get_app_priority_order()

        for app in priority_order:
            allocation[app.app_id] = {}
            for resource_type in config.resources.keys():
                total = total_resources.get(resource_type, 100)
                min_allocation = total * app.resource_share.get(resource_type, 0.1) * 0.5

                app_data = self.generate_app_resource_data(df, app.app_id)
                peak_usage = calculate_statistics(app_data[resource_type])['p95']
                suggested_allocation = max(min_allocation, peak_usage * 1.2)
                suggested_allocation = min(suggested_allocation, total * 0.5)

                allocation[app.app_id][resource_type] = round(suggested_allocation, 2)

        return allocation

    def get_resource_contention_radar(self, df: pd.DataFrame) -> pd.DataFrame:
        all_app_data = self.generate_all_apps_data(df)
        radar_data = []

        for app_id in self.apps.keys():
            app_data = all_app_data[all_app_data['app_id'] == app_id]
            app = self.apps[app_id]
            row = {'app_id': app_id, 'app_name': app.name, 'priority': app.priority}
            for resource_type in config.resources.keys():
                stats = calculate_statistics(app_data[resource_type])
                row[resource_type] = stats['mean']
            radar_data.append(row)

        return pd.DataFrame(radar_data)
