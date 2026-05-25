import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


INSTANCE_PRICING = {
    'ecs.t5-lc1m2.small': {'cpu': 1, 'mem': 2, 'monthly': 60},
    'ecs.t5-lc1m2.large': {'cpu': 2, 'mem': 4, 'monthly': 120},
    'ecs.t5-c1m2.xlarge': {'cpu': 4, 'mem': 8, 'monthly': 240},
    'ecs.g6.large': {'cpu': 2, 'mem': 8, 'monthly': 280},
    'ecs.g6.xlarge': {'cpu': 4, 'mem': 16, 'monthly': 560},
    'ecs.c6.large': {'cpu': 2, 'mem': 4, 'monthly': 200},
    'ecs.c6.xlarge': {'cpu': 4, 'mem': 8, 'monthly': 400},
    'ecs.r6.large': {'cpu': 2, 'mem': 16, 'monthly': 320},
    'ecs.r6.xlarge': {'cpu': 4, 'mem': 32, 'monthly': 640}
}

DOWNSIZE_MAP = {
    'ecs.g6.xlarge': 'ecs.g6.large',
    'ecs.c6.xlarge': 'ecs.c6.large',
    'ecs.r6.xlarge': 'ecs.r6.large',
    'ecs.t5-c1m2.xlarge': 'ecs.t5-lc1m2.large',
    'ecs.t5-lc1m2.large': 'ecs.t5-lc1m2.small'
}


class CostOptimizer:
    def __init__(self, config: Dict):
        self.config = config
        self.cost_config = config.get('cost', {})
        self.rules = config.get('optimization_rules', {})

    def calculate_instance_monthly_cost(self, instance_type: str) -> float:
        pricing = INSTANCE_PRICING.get(instance_type)
        if pricing:
            return pricing['monthly']
        
        cpu = int(instance_type.split('.')[-1].split('x')[0]) if 'x' in instance_type else 1
        base_cost = 80 * cpu
        return base_cost

    def calculate_eip_monthly_cost(self, eip: pd.Series) -> float:
        daily_cost = self.cost_config.get('eip_daily_cost', 2.5)
        return daily_cost * 30

    def calculate_current_monthly_cost(self, instances_df: pd.DataFrame,
                                        eip_df: pd.DataFrame) -> Dict:
        total_ecs_cost = 0.0
        ecs_costs = []

        for _, instance in instances_df.iterrows():
            cost = self.calculate_instance_monthly_cost(instance.get('instance_type', ''))
            ecs_costs.append({
                'instance_id': instance.get('instance_id'),
                'instance_name': instance.get('instance_name'),
                'instance_type': instance.get('instance_type'),
                'monthly_cost': cost,
                'status': instance.get('status')
            })
            if instance.get('status') == 'Running':
                total_ecs_cost += cost

        total_eip_cost = 0.0
        eip_costs = []

        for _, eip in eip_df.iterrows():
            cost = self.calculate_eip_monthly_cost(eip)
            eip_costs.append({
                'allocation_id': eip.get('allocation_id'),
                'ip_address': eip.get('ip_address'),
                'monthly_cost': cost,
                'status': eip.get('status')
            })
            total_eip_cost += cost

        return {
            'total_monthly_cost': total_ecs_cost + total_eip_cost,
            'ecs_monthly_cost': total_ecs_cost,
            'eip_monthly_cost': total_eip_cost,
            'ecs_costs': pd.DataFrame(ecs_costs),
            'eip_costs': pd.DataFrame(eip_costs)
        }

    def recommend_downsizing(self, analysis_df: pd.DataFrame) -> pd.DataFrame:
        if analysis_df.empty:
            return pd.DataFrame()

        cpu_threshold = self.rules.get('downsizing', {}).get('cpu_lower_threshold', 20.0)
        p99_safety_threshold = self.rules.get('downsizing', {}).get('p99_safety_threshold', 70.0)
        buffer_padding = self.rules.get('buffer', {}).get('safety_padding', 1.2)

        candidates = analysis_df[
            (analysis_df['status'] == 'Running')
        ].copy()

        recommendations = []
        for _, instance in candidates.iterrows():
            current_type = instance.get('instance_type', '')
            target_type = DOWNSIZE_MAP.get(current_type)
            
            if not target_type:
                continue

            cpu_avg = instance.get('cpu_avg', 0)
            cpu_p99 = instance.get('cpu_p99', cpu_avg * 2)
            is_periodic = instance.get('is_periodic', False)
            needs_buffer = instance.get('needs_buffer', False)
            recommended_buffer_pct = instance.get('recommended_buffer_pct', 10)
            
            effective_p99 = cpu_p99 * buffer_padding if needs_buffer else cpu_p99
            
            can_downsize = (
                cpu_avg < cpu_threshold and 
                effective_p99 < p99_safety_threshold
            )
            
            if can_downsize:
                current_cost = self.calculate_instance_monthly_cost(current_type)
                target_cost = self.calculate_instance_monthly_cost(target_type)
                savings = current_cost - target_cost
                savings_pct = (savings / current_cost * 100) if current_cost > 0 else 0

                reason_parts = []
                reason_parts.append(f"Avg CPU: {cpu_avg:.1f}% (threshold: {cpu_threshold}%)")
                reason_parts.append(f"P99 CPU: {cpu_p99:.1f}%")
                
                if is_periodic:
                    reason_parts.append(f"Periodic pattern detected (conservative estimate)")
                if needs_buffer:
                    reason_parts.append(f"With {recommended_buffer_pct}% buffer safety margin")

                recommendations.append({
                    'instance_id': instance['instance_id'],
                    'instance_name': instance.get('instance_name', ''),
                    'current_type': current_type,
                    'recommended_type': target_type,
                    'current_monthly_cost': current_cost,
                    'recommended_monthly_cost': target_cost,
                    'monthly_savings': savings,
                    'savings_percent': round(savings_pct, 2),
                    'current_cpu_avg': round(cpu_avg, 2),
                    'current_cpu_p99': round(cpu_p99, 2),
                    'is_periodic': is_periodic,
                    'needs_buffer': needs_buffer,
                    'buffer_pct': recommended_buffer_pct,
                    'reason': "; ".join(reason_parts)
                })

        return pd.DataFrame(recommendations)

    def recommend_rightsizing_with_buffer(self, analysis_df: pd.DataFrame) -> pd.DataFrame:
        if analysis_df.empty:
            return pd.DataFrame()

        rightsizing_recs = []
        
        for _, instance in analysis_df.iterrows():
            if instance.get('status') != 'Running':
                continue

            cpu_avg = instance.get('cpu_avg', 0)
            cpu_p99 = instance.get('cpu_p99', 0)
            is_periodic = instance.get('is_periodic', False)
            needs_buffer = instance.get('needs_buffer', False)
            
            if needs_buffer or is_periodic:
                buffer_factor = 1.3 if is_periodic else 1.2
                target_utilization = cpu_p99 * buffer_factor
                
                current_type = instance.get('instance_type', '')
                current_pricing = INSTANCE_PRICING.get(current_type, {})
                current_cpu = current_pricing.get('cpu', 1)
                
                target_cpu = max(1, int(current_cpu * (target_utilization / 100)))
                
                rightsizing_recs.append({
                    'instance_id': instance['instance_id'],
                    'instance_name': instance.get('instance_name', ''),
                    'current_type': current_type,
                    'recommendation': 'keep_or_upgrade',
                    'reason': f"Buffer required for {'periodic' if is_periodic else 'peak'} load",
                    'target_utilization_pct': round(target_utilization, 1),
                    'recommended_buffer_pct': instance.get('recommended_buffer_pct', 0),
                    'peak_hours': instance.get('peak_hours', '[]')
                })

        return pd.DataFrame(rightsizing_recs)

    def generate_optimization_plan(self, idle_resources: Dict,
                                    analysis_df: pd.DataFrame) -> Dict:
        idle_ecs = idle_resources.get('idle_ecs', pd.DataFrame())
        stopped_ecs = idle_resources.get('stopped_ecs', pd.DataFrame())
        unused_eips = idle_resources.get('unused_eips', pd.DataFrame())

        release_recommendations = []
        excluded_from_release = set()

        for _, instance in idle_ecs.iterrows():
            instance_id = instance['instance_id']
            instance_analysis = analysis_df[analysis_df['instance_id'] == instance_id]
            
            if not instance_analysis.empty:
                is_periodic = instance_analysis.iloc[0].get('is_periodic', False)
                needs_buffer = instance_analysis.iloc[0].get('needs_buffer', False)
                
                if is_periodic or needs_buffer:
                    excluded_from_release.add(instance_id)
                    continue

            cost = self.calculate_instance_monthly_cost(instance.get('instance_type', ''))
            release_recommendations.append({
                'resource_type': 'ECS',
                'resource_id': instance_id,
                'resource_name': instance.get('instance_name', ''),
                'action': 'release',
                'monthly_savings': cost,
                'reason': instance.get('reason', 'Idle resource'),
                'idle_score': instance.get('idle_score', 0)
            })

        for _, instance in stopped_ecs.iterrows():
            cost = self.calculate_instance_monthly_cost(instance.get('instance_type', ''))
            release_recommendations.append({
                'resource_type': 'ECS',
                'resource_id': instance['instance_id'],
                'resource_name': instance.get('instance_name', ''),
                'action': 'release',
                'monthly_savings': cost * 0.5,
                'reason': 'Stopped instance - consider releasing if not needed',
                'idle_score': 90
            })

        for _, eip in unused_eips.iterrows():
            cost = self.calculate_eip_monthly_cost(eip)
            release_recommendations.append({
                'resource_type': 'EIP',
                'resource_id': eip['allocation_id'],
                'resource_name': eip.get('ip_address', ''),
                'action': 'release',
                'monthly_savings': cost,
                'reason': 'Unused EIP',
                'idle_score': 95
            })

        downsizing_recs = self.recommend_downsizing(analysis_df)
        downsizing_recommendations = []

        for _, rec in downsizing_recs.iterrows():
            if rec['instance_id'] in excluded_from_release:
                continue
                
            downsizing_recommendations.append({
                'resource_type': 'ECS',
                'resource_id': rec['instance_id'],
                'resource_name': rec.get('instance_name', ''),
                'action': 'downsize',
                'monthly_savings': rec['monthly_savings'],
                'reason': rec['reason'],
                'details': f"{rec['current_type']} -> {rec['recommended_type']}"
            })

        rightsizing_recs = self.recommend_rightsizing_with_buffer(analysis_df)
        buffer_recommendations = []
        
        for _, rec in rightsizing_recs.iterrows():
            buffer_recommendations.append({
                'resource_type': 'ECS',
                'resource_id': rec['instance_id'],
                'resource_name': rec.get('instance_name', ''),
                'action': 'keep_with_buffer',
                'monthly_savings': 0,
                'reason': rec['reason'],
                'details': f"Recommended buffer: {rec['recommended_buffer_pct']}%, Peak hours: {rec['peak_hours']}"
            })

        all_recommendations = release_recommendations + downsizing_recommendations
        total_savings = sum(r['monthly_savings'] for r in all_recommendations)

        return {
            'release_recommendations': pd.DataFrame(release_recommendations),
            'downsizing_recommendations': pd.DataFrame(downsizing_recommendations),
            'buffer_recommendations': pd.DataFrame(buffer_recommendations),
            'all_recommendations': pd.DataFrame(all_recommendations),
            'excluded_due_to_periodicity': list(excluded_from_release),
            'total_monthly_savings': total_savings,
            'total_annual_savings': total_savings * 12,
            'optimization_count': len(all_recommendations),
            'buffer_aware_count': len(buffer_recommendations)
        }

    def calculate_cost_comparison(self, current_cost: Dict,
                                   optimization_plan: Dict) -> Dict:
        current_monthly = current_cost.get('total_monthly_cost', 0)
        optimized_monthly = current_monthly - optimization_plan.get('total_monthly_savings', 0)
        savings_pct = (optimization_plan.get('total_monthly_savings', 0) / current_monthly * 100) if current_monthly > 0 else 0

        return {
            'current_monthly_cost': current_monthly,
            'optimized_monthly_cost': max(0, optimized_monthly),
            'monthly_savings': optimization_plan.get('total_monthly_savings', 0),
            'annual_savings': optimization_plan.get('total_annual_savings', 0),
            'savings_percentage': round(savings_pct, 2),
            'ecs_current': current_cost.get('ecs_monthly_cost', 0),
            'eip_current': current_cost.get('eip_monthly_cost', 0),
            'ecs_savings': sum(
                r['monthly_savings'] for r in optimization_plan.get('all_recommendations', pd.DataFrame()).to_dict('records')
                if r['resource_type'] == 'ECS'
            ),
            'eip_savings': sum(
                r['monthly_savings'] for r in optimization_plan.get('all_recommendations', pd.DataFrame()).to_dict('records')
                if r['resource_type'] == 'EIP'
            )
        }

    def get_cost_breakdown(self, instances_df: pd.DataFrame,
                            eip_df: pd.DataFrame) -> Dict:
        cost_data = self.calculate_current_monthly_cost(instances_df, eip_df)
        
        ecs_costs = cost_data['ecs_costs']
        if not ecs_costs.empty:
            by_type = ecs_costs.groupby('instance_type')['monthly_cost'].sum().to_dict()
            by_status = ecs_costs.groupby('status')['monthly_cost'].sum().to_dict()
        else:
            by_type = {}
            by_status = {}

        return {
            'total_cost': cost_data['total_monthly_cost'],
            'ecs_cost': cost_data['ecs_monthly_cost'],
            'eip_cost': cost_data['eip_monthly_cost'],
            'cost_by_instance_type': by_type,
            'cost_by_status': by_status,
            'instance_count': len(instances_df),
            'eip_count': len(eip_df)
        }
