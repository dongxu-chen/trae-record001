import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class WorkloadType(Enum):
    BATCH = "batch"
    CI_CD = "ci_cd"
    DEV_TEST = "dev_test"
    WEB = "web"
    DATABASE = "database"
    STATEFUL = "stateful"
    UNKNOWN = "unknown"


class SpotInstanceAnalyzer:
    SPOT_DISCOUNT_RATES = {
        'aliyun': {
            'default': 0.3,
            'burst': 0.5,
            'stable': 0.2
        },
        'aws': {
            'default': 0.4,
            'burst': 0.6,
            'stable': 0.3
        },
        'tencent': {
            'default': 0.35,
            'burst': 0.55,
            'stable': 0.25
        }
    }

    INTERRUPTION_RISK_WEIGHTS = {
        'low': 0.1,
        'medium': 0.3,
        'high': 0.6
    }

    def __init__(self, config: Dict):
        self.config = config
        self.rules = config.get('spot_instances', {})
        self.min_savings_threshold = self.rules.get('min_savings_threshold', 0.25)
        self.max_interruption_risk = self.rules.get('max_interruption_risk', 0.4)

    def classify_workload(self, instance_data: pd.Series, metrics_df: pd.DataFrame) -> WorkloadType:
        instance_id = instance_data['instance_id']
        instance_name = str(instance_data.get('instance_name', '')).lower()
        
        name_keywords = {
            'batch': ['batch', 'worker', 'job', 'compute', 'render', 'transcode'],
            'ci_cd': ['jenkins', 'gitlab', 'ci-', 'runner', 'build'],
            'dev_test': ['dev', 'test', 'staging', 'qa', 'sandbox'],
            'web': ['web', 'nginx', 'apache', 'frontend', 'api'],
            'database': ['db', 'mysql', 'postgres', 'redis', 'mongo', 'sql'],
            'stateful': ['kafka', 'zookeeper', 'etcd', 'elastic', 'es-']
        }

        for wl_type, keywords in name_keywords.items():
            if any(k in instance_name for k in keywords):
                return WorkloadType(wl_type)

        instance_metrics = metrics_df[metrics_df['instance_id'] == instance_id]
        if len(instance_metrics) > 0:
            cpu_values = instance_metrics[instance_metrics['metric_name'] == 'cpu_utilization']['value']
            
            if len(cpu_values) > 0:
                cv = np.std(cpu_values) / (np.mean(cpu_values) + 0.001)
                
                if cv > 1.5:
                    return WorkloadType.BATCH
                elif cv > 0.8:
                    return WorkloadType.WEB

        return WorkloadType.UNKNOWN

    def calculate_spot_suitability(self, instance_data: pd.Series, 
                                    metrics_df: pd.DataFrame) -> Dict:
        instance_id = instance_data['instance_id']
        workload_type = self.classify_workload(instance_data, metrics_df)
        
        suitability_score = 0
        reasons = []
        
        workload_scores = {
            WorkloadType.BATCH: 90,
            WorkloadType.CI_CD: 85,
            WorkloadType.DEV_TEST: 80,
            WorkloadType.WEB: 50,
            WorkloadType.DATABASE: 10,
            WorkloadType.STATEFUL: 5,
            WorkloadType.UNKNOWN: 40
        }
        
        suitability_score += workload_scores[workload_type]
        reasons.append(f"Workload type: {workload_type.value}")

        instance_metrics = metrics_df[metrics_df['instance_id'] == instance_id]
        if len(instance_metrics) > 0:
            cpu_values = instance_metrics[instance_metrics['metric_name'] == 'cpu_utilization']['value']
            
            if len(cpu_values) > 0:
                cpu_mean = np.mean(cpu_values)
                cpu_std = np.std(cpu_values)
                cv = cpu_std / (cpu_mean + 0.001)
                
                if cv > 1.0:
                    suitability_score += 10
                    reasons.append("High CPU variability indicates burst workload")
                elif cv < 0.3:
                    suitability_score -= 10
                    reasons.append("Stable workload may better use on-demand")

                if cpu_mean < 30:
                    suitability_score += 5
                    reasons.append("Low average utilization")
                elif cpu_mean > 80:
                    suitability_score -= 15
                    reasons.append("High utilization not ideal for spot")

        instance_status = instance_data.get('status', '')
        if instance_status == 'Stopped':
            suitability_score -= 20
            reasons.append("Stopped instance - consider release first")

        is_periodic = instance_data.get('is_periodic', False)
        if is_periodic:
            suitability_score += 10
            reasons.append("Periodic workload suitable for spot")

        needs_buffer = instance_data.get('needs_buffer', False)
        if needs_buffer:
            suitability_score -= 15
            reasons.append("Buffer requirement increases interruption risk")

        suitability_score = max(0, min(100, suitability_score))
        
        spot_recommended = suitability_score >= 60
        
        provider = instance_data.get('provider', 'aliyun')
        spot_price_ratio = self.SPOT_DISCOUNT_RATES.get(provider, {}).get('default', 0.3)
        
        on_demand_cost = self._get_instance_cost(instance_data)
        spot_estimated_cost = on_demand_cost * (1 - spot_price_ratio)
        estimated_savings = on_demand_cost - spot_estimated_cost
        
        interruption_risk = self._estimate_interruption_risk(
            workload_type, instance_data, cpu_mean if 'cpu_mean' in locals() else 50
        )

        return {
            'instance_id': instance_id,
            'instance_name': instance_data.get('instance_name', ''),
            'workload_type': workload_type.value,
            'suitability_score': round(suitability_score, 1),
            'spot_recommended': spot_recommended and estimated_savings / (on_demand_cost + 0.001) >= self.min_savings_threshold,
            'interruption_risk': interruption_risk,
            'risk_level': 'low' if interruption_risk < 0.2 else 'medium' if interruption_risk < 0.4 else 'high',
            'on_demand_monthly_cost': round(on_demand_cost, 2),
            'estimated_spot_monthly_cost': round(spot_estimated_cost, 2),
            'estimated_monthly_savings': round(estimated_savings, 2),
            'savings_percent': round((estimated_savings / (on_demand_cost + 0.001)) * 100, 1),
            'reasons': reasons,
            'recommended_strategy': self._get_recommendation_strategy(suitability_score, workload_type)
        }

    def _get_instance_cost(self, instance_data: pd.Series) -> float:
        instance_type = instance_data.get('instance_type', '')
        
        from .cost_optimizer import INSTANCE_PRICING
        pricing = INSTANCE_PRICING.get(instance_type)
        if pricing:
            return pricing['monthly']
        
        cpu = instance_data.get('cpu', 1) or 1
        base_cost = 80 * cpu
        return base_cost

    def _estimate_interruption_risk(self, workload_type: WorkloadType, 
                                     instance_data: pd.Series, 
                                     cpu_mean: float) -> float:
        base_risk = {
            WorkloadType.BATCH: 0.15,
            WorkloadType.CI_CD: 0.15,
            WorkloadType.DEV_TEST: 0.2,
            WorkloadType.WEB: 0.3,
            WorkloadType.DATABASE: 0.5,
            WorkloadType.STATEFUL: 0.6,
            WorkloadType.UNKNOWN: 0.35
        }.get(workload_type, 0.35)

        if cpu_mean > 70:
            base_risk += 0.1
        
        instance_type = instance_data.get('instance_type', '')
        if 'large' in instance_type or 'xlarge' in instance_type:
            base_risk -= 0.05

        return min(0.9, max(0.05, base_risk))

    def _get_recommendation_strategy(self, score: float, 
                                       workload_type: WorkloadType) -> str:
        if score >= 80:
            return "Strongly recommend spot instances with diversified fleet"
        elif score >= 60:
            return "Recommend spot instances with checkpointing enabled"
        elif score >= 40:
            return "Consider spot for non-critical workloads"
        else:
            return "Not recommended for spot instances, use on-demand"

    def analyze_spot_candidates(self, instances_df: pd.DataFrame,
                                 metrics_df: pd.DataFrame) -> pd.DataFrame:
        if instances_df.empty:
            return pd.DataFrame()

        results = []
        for _, instance in instances_df.iterrows():
            if instance.get('status') != 'Running':
                continue
                
            analysis = self.calculate_spot_suitability(instance, metrics_df)
            results.append(analysis)

        return pd.DataFrame(results)

    def get_spot_summary(self, spot_df: pd.DataFrame) -> Dict:
        if spot_df.empty:
            return {
                'total_candidates': 0,
                'recommended_count': 0,
                'total_monthly_savings': 0,
                'avg_suitability_score': 0,
                'workload_distribution': {}
            }

        recommended = spot_df[spot_df['spot_recommended']]
        
        workload_dist = spot_df.groupby('workload_type').size().to_dict()
        
        return {
            'total_candidates': len(spot_df),
            'recommended_count': len(recommended),
            'total_monthly_savings': round(recommended['estimated_monthly_savings'].sum(), 2),
            'avg_suitability_score': round(spot_df['suitability_score'].mean(), 1),
            'avg_savings_percent': round(recommended['savings_percent'].mean(), 1) if len(recommended) > 0 else 0,
            'workload_distribution': workload_dist,
            'risk_distribution': spot_df.groupby('risk_level').size().to_dict()
        }
