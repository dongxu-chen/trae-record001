import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class CostAnalyzer:
    def __init__(self, data: Dict):
        self.historical_costs = data.get('historical_costs', pd.DataFrame())
        self.instances = data.get('instances', pd.DataFrame())
        self.ebs_volumes = data.get('ebs_volumes', pd.DataFrame())
        self.cloud_provider = data.get('cloud_provider', 'aws')

    def get_cost_summary(self) -> Dict:
        if self.historical_costs.empty:
            return {}
        
        total_cost = self.historical_costs['cost'].sum()
        last_30d_cost = self.historical_costs[
            self.historical_costs['date'] >= datetime.now() - timedelta(days=30)
        ]['cost'].sum()
        last_7d_cost = self.historical_costs[
            self.historical_costs['date'] >= datetime.now() - timedelta(days=7)
        ]['cost'].sum()
        
        by_service = self.historical_costs.groupby('service')['cost'].sum().sort_values(ascending=False)
        by_region = self.historical_costs.groupby('region')['cost'].sum().sort_values(ascending=False)
        by_account = self.historical_costs.groupby('account')['cost'].sum().sort_values(ascending=False)
        
        daily_costs = self.historical_costs.groupby('date')['cost'].sum()
        monthly_trend = daily_costs.resample('M').sum()
        
        return {
            'total_cost': total_cost,
            'last_30d_cost': last_30d_cost,
            'last_7d_cost': last_7d_cost,
            'daily_avg_30d': last_30d_cost / 30,
            'by_service': by_service.to_dict(),
            'by_region': by_region.to_dict(),
            'by_account': by_account.to_dict(),
            'daily_costs': daily_costs,
            'monthly_trend': monthly_trend,
            'top_5_services': by_service.head(5).to_dict(),
        }

    def analyze_instance_utilization(self) -> Dict:
        if self.instances.empty:
            return {}
        
        running_instances = self.instances[self.instances['state'] == 'running'].copy()
        
        if running_instances.empty:
            return {}
        
        running_instances['utilization_score'] = (
            running_instances['avg_cpu_7d'] * 0.4 +
            running_instances['avg_memory_7d'] * 0.4 +
            running_instances['avg_network_7d'] * 0.2
        )
        
        running_instances['utilization_category'] = pd.cut(
            running_instances['utilization_score'],
            bins=[0, 20, 50, 80, 100],
            labels=['Underutilized', 'Low', 'Moderate', 'High']
        )
        
        underutilized = running_instances[running_instances['utilization_category'] == 'Underutilized']
        low_util = running_instances[running_instances['utilization_category'] == 'Low']
        
        idle_instances = running_instances[
            (running_instances['avg_cpu_7d'] < 5) &
            (running_instances['avg_memory_7d'] < 10)
        ]
        
        stopped_instances = self.instances[self.instances['state'] == 'stopped']
        
        return {
            'total_running': len(running_instances),
            'total_stopped': len(stopped_instances),
            'underutilized_count': len(underutilized),
            'low_util_count': len(low_util),
            'idle_count': len(idle_instances),
            'avg_utilization': running_instances['utilization_score'].mean(),
            'avg_cpu': running_instances['avg_cpu_7d'].mean(),
            'avg_memory': running_instances['avg_memory_7d'].mean(),
            'underutilized_instances': underutilized,
            'idle_instances': idle_instances,
            'stopped_instances': stopped_instances,
            'utilization_by_env': running_instances.groupby('environment')['utilization_score'].mean().to_dict(),
            'monthly_cost_underutilized': underutilized['ondemand_cost_30d'].sum() if len(underutilized) > 0 else 0,
            'monthly_cost_idle': idle_instances['ondemand_cost_30d'].sum() if len(idle_instances) > 0 else 0,
            'instances': running_instances,
        }

    def analyze_storage_optimization(self) -> Dict:
        if self.ebs_volumes.empty:
            return {}
        
        unused_volumes = self.ebs_volumes[self.ebs_volumes['state'] == 'available']
        gp2_volumes = self.ebs_volumes[self.ebs_volumes['volume_type'] == 'gp2']
        
        gp2_upgrade_savings = 0
        if len(gp2_volumes) > 0:
            gp2_cost = gp2_volumes['monthly_cost'].sum()
            gp3_cost = (gp2_volumes['size_gb'] * 0.08).sum()
            gp2_upgrade_savings = gp2_cost - gp3_cost
        
        low_io_volumes = self.ebs_volumes[
            (self.ebs_volumes['avg_read_ops'] + self.ebs_volumes['avg_write_ops'] < 10) &
            (self.ebs_volumes['state'] == 'in-use')
        ]
        
        return {
            'total_volumes': len(self.ebs_volumes),
            'unused_count': len(unused_volumes),
            'gp2_count': len(gp2_volumes),
            'total_storage_gb': self.ebs_volumes['size_gb'].sum(),
            'unused_storage_gb': unused_volumes['size_gb'].sum() if len(unused_volumes) > 0 else 0,
            'monthly_cost_unused': unused_volumes['monthly_cost'].sum() if len(unused_volumes) > 0 else 0,
            'gp2_upgrade_savings': gp2_upgrade_savings,
            'low_io_volumes_count': len(low_io_volumes),
            'by_type': self.ebs_volumes.groupby('volume_type').agg({
                'size_gb': 'sum',
                'monthly_cost': 'sum',
                'volume_id': 'count'
            }).rename(columns={'volume_id': 'count'}).to_dict('index'),
            'unused_volumes': unused_volumes,
        }

    def get_cost_trend_analysis(self) -> Dict:
        if self.historical_costs.empty:
            return {}
        
        daily = self.historical_costs.groupby('date')['cost'].sum().reset_index()
        daily['cost'] = pd.to_numeric(daily['cost'], errors='coerce')
        
        weekly_avg = daily['cost'].rolling(7).mean()
        monthly_avg = daily['cost'].rolling(30).mean()
        
        recent_7d = daily.tail(7)['cost'].mean()
        prior_7d = daily.iloc[-14:-7]['cost'].mean()
        weekly_change = ((recent_7d - prior_7d) / prior_7d * 100) if prior_7d > 0 else 0
        
        recent_30d = daily.tail(30)['cost'].mean()
        prior_30d = daily.iloc[-60:-30]['cost'].mean()
        monthly_change = ((recent_30d - prior_30d) / prior_30d * 100) if prior_30d > 0 else 0
        
        daily['day_of_week'] = daily['date'].dt.day_name()
        day_of_week_avg = daily.groupby('day_of_week')['cost'].mean().sort_values(
            key=lambda x: x.index.map({
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            })
        )
        
        return {
            'daily_costs': daily,
            'weekly_moving_avg': weekly_avg,
            'monthly_moving_avg': monthly_avg,
            'weekly_change_pct': weekly_change,
            'monthly_change_pct': monthly_change,
            'day_of_week_pattern': day_of_week_avg.to_dict(),
            'highest_cost_day': daily.loc[daily['cost'].idxmax(), 'date'],
            'lowest_cost_day': daily.loc[daily['cost'].idxmin(), 'date'],
        }

    def generate_cost_insights(self) -> List[Dict]:
        insights = []
        util_analysis = self.analyze_instance_utilization()
        storage_analysis = self.analyze_storage_optimization()
        trend_analysis = self.get_cost_trend_analysis()
        
        if util_analysis.get('underutilized_count', 0) > 0:
            insights.append({
                'type': 'warning',
                'category': 'Compute',
                'title': f"{util_analysis['underutilized_count']} Underutilized Instances",
                'description': f"Found {util_analysis['underutilized_count']} instances with utilization below 20%. Consider downsizing or terminating.",
                'impact': f"${util_analysis.get('monthly_cost_underutilized', 0):,.2f}/month",
                'severity': 'high' if util_analysis['underutilized_count'] > 10 else 'medium'
            })
        
        if util_analysis.get('idle_count', 0) > 0:
            insights.append({
                'type': 'danger',
                'category': 'Compute',
                'title': f"{util_analysis['idle_count']} Idle Instances Detected",
                'description': f"{util_analysis['idle_count']} instances are running with almost no activity (<5% CPU, <10% memory).",
                'impact': f"${util_analysis.get('monthly_cost_idle', 0):,.2f}/month",
                'severity': 'high'
            })
        
        if util_analysis.get('total_stopped', 0) > 0:
            insights.append({
                'type': 'info',
                'category': 'Compute',
                'title': f"{util_analysis['total_stopped']} Stopped Instances",
                'description': "Stopped instances still incur EBS volume charges. Consider terminating if not needed.",
                'impact': "Review EBS costs",
                'severity': 'low'
            })
        
        if storage_analysis.get('unused_count', 0) > 0:
            insights.append({
                'type': 'danger',
                'category': 'Storage',
                'title': f"{storage_analysis['unused_count']} Unused EBS Volumes",
                'description': f"{storage_analysis['unused_count']} volumes are not attached to any instance.",
                'impact': f"${storage_analysis.get('monthly_cost_unused', 0):,.2f}/month",
                'severity': 'high'
            })
        
        if storage_analysis.get('gp2_upgrade_savings', 0) > 0:
            insights.append({
                'type': 'success',
                'category': 'Storage',
                'title': "Upgrade gp2 to gp3 Volumes",
                'description': f"{storage_analysis['gp2_count']} gp2 volumes can be upgraded to gp3 for better performance at lower cost.",
                'impact': f"${storage_analysis['gp2_upgrade_savings']:,.2f}/month",
                'severity': 'low'
            })
        
        if trend_analysis.get('weekly_change_pct', 0) > 10:
            insights.append({
                'type': 'warning',
                'category': 'Trend',
                'title': "Costs Increasing Rapidly",
                'description': f"Weekly costs increased by {trend_analysis['weekly_change_pct']:.1f}% compared to previous week.",
                'impact': "Investigate recent changes",
                'severity': 'medium'
            })
        
        return insights
