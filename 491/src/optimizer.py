import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from datetime import datetime


class OptimizationType(Enum):
    TERMINATE = "terminate"
    DOWNSIZE = "downsize"
    RIGHTSIZE = "rightsize"
    RESERVE = "reserve"
    SAVINGS_PLAN = "savings_plan"
    STORAGE_OPT = "storage_optimization"


@dataclass
class MultiGranularSample:
    timestamp: pd.Timestamp
    value: float
    granularity: str
    is_peak: bool = False


@dataclass
class OptimizationRecommendation:
    type: OptimizationType
    resource_id: str
    resource_name: str
    resource_type: str
    current_config: Dict
    recommended_config: Optional[Dict]
    monthly_savings: float
    annual_savings: float
    confidence_score: float
    risk_level: str
    effort_level: str
    description: str
    action_steps: List[str]
    business_impact: str = "Low"
    business_impact_score: float = 0.1
    flexibility_score: float = 1.0
    priority_score: float = 0.0
    peak_metrics: Dict = field(default_factory=dict)


class MultiGranularSampler:
    def __init__(self, data: pd.DataFrame, value_col: str = 'value', time_col: str = 'timestamp'):
        self.data = data
        self.value_col = value_col
        self.time_col = time_col
        self.granularities = ['1min', '5min', '15min', '1h', '6h', '1d']

    def sample(self, retain_peaks: bool = True, peak_window: int = 5) -> List[MultiGranularSample]:
        samples = []
        
        if self.data.empty:
            return samples
        
        df = self.data.copy()
        df = df.sort_values(self.time_col)
        
        if retain_peaks:
            peak_indices = self._detect_peaks(df, window=peak_window)
            for idx in peak_indices:
                samples.append(MultiGranularSample(
                    timestamp=df.iloc[idx][self.time_col],
                    value=df.iloc[idx][self.value_col],
                    granularity='peak',
                    is_peak=True
                ))
        
        for granularity in self.granularities:
            sampled = self._resample_by_granularity(df, granularity)
            for _, row in sampled.iterrows():
                samples.append(MultiGranularSample(
                    timestamp=row[self.time_col],
                    value=row[self.value_col],
                    granularity=granularity,
                    is_peak=False
                ))
        
        return samples

    def _detect_peaks(self, df: pd.DataFrame, window: int = 5) -> List[int]:
        values = df[self.value_col].values
        peaks = []
        
        for i in range(window, len(values) - window):
            window_vals = values[i-window:i+window+1]
            if values[i] == np.max(window_vals) and values[i] > np.mean(window_vals) * 1.5:
                peaks.append(i)
            elif values[i] == np.min(window_vals) and values[i] < np.mean(window_vals) * 0.5:
                peaks.append(i)
        
        return peaks

    def _resample_by_granularity(self, df: pd.DataFrame, granularity: str) -> pd.DataFrame:
        df_resampled = df.set_index(self.time_col).resample(granularity).agg({
            self.value_col: ['mean', 'max', 'min', 'std']
        }).dropna()
        df_resampled.columns = [f'{self.value_col}_{agg}' for agg in ['mean', 'max', 'min', 'std']]
        df_resampled = df_resampled.reset_index()
        df_resampled[self.value_col] = df_resampled[f'{self.value_col}_mean']
        return df_resampled

    def get_peak_features(self) -> Dict:
        if self.data.empty:
            return {}
        
        values = self.data[self.value_col].values
        return {
            'peak_99th': np.percentile(values, 99),
            'peak_95th': np.percentile(values, 95),
            'peak_max': np.max(values),
            'peak_min': np.min(values),
            'peak_mean_ratio': np.max(values) / np.mean(values) if np.mean(values) > 0 else 0,
            'volatility': np.std(values) / np.mean(values) if np.mean(values) > 0 else 0,
            'burst_score': self._calculate_burst_score(values),
        }

    def _calculate_burst_score(self, values: np.ndarray) -> float:
        if len(values) < 2:
            return 0
        
        p95 = np.percentile(values, 95)
        median = np.median(values)
        
        if median == 0:
            return 0
        
        burst_ratio = p95 / median
        
        if burst_ratio > 5:
            return 1.0
        elif burst_ratio > 3:
            return 0.7
        elif burst_ratio > 2:
            return 0.4
        else:
            return 0.1


class SavingsPlanAnalyzer:
    def __init__(self, utilization_data: pd.DataFrame = None):
        self.utilization_data = utilization_data

    def calculate_flexibility_score(self, 
                                  hourly_pattern: List[float],
                                  instance_age_days: int,
                                  workload_type: str = 'general') -> float:
        score = 1.0
        
        hourly_variation = np.std(hourly_pattern) / np.mean(hourly_pattern) if np.mean(hourly_pattern) > 0 else 0
        if hourly_variation > 0.5:
            score *= 0.7
        elif hourly_variation > 0.3:
            score *= 0.85
        
        if instance_age_days < 30:
            score *= 0.6
        elif instance_age_days < 90:
            score *= 0.8
        elif instance_age_days < 180:
            score *= 0.9
        
        workload_factors = {
            'development': 0.7,
            'testing': 0.6,
            'staging': 0.8,
            'production': 1.0,
            'batch': 0.5,
            'general': 0.9
        }
        score *= workload_factors.get(workload_type, 0.9)
        
        return round(score, 2)

    def recommend_purchase_type(self, 
                               flexibility_score: float,
                               utilization_rate: float,
                               hourly_on_demand_cost: float) -> Dict:
        if flexibility_score < 0.5 or utilization_rate < 0.4:
            recommendation = {
                'type': 'on_demand',
                'reason': 'Low flexibility or utilization - on-demand recommended',
                'savings_vs_ondemand': 0,
                'breakeven_months': None
            }
        elif flexibility_score < 0.75 or utilization_rate < 0.6:
            recommendation = {
                'type': 'savings_plan_1y',
                'reason': 'Moderate flexibility - 1-year Savings Plan recommended',
                'savings_vs_ondemand': hourly_on_demand_cost * 730 * 0.25,
                'breakeven_months': 4
            }
        else:
            recommendation = {
                'type': 'reserved_instance_3y',
                'reason': 'High flexibility and utilization - 3-year RI recommended',
                'savings_vs_ondemand': hourly_on_demand_cost * 730 * 0.45,
                'breakeven_months': 6
            }
        
        recommendation['flexibility_score'] = flexibility_score
        recommendation['utilization_rate'] = utilization_rate
        
        return recommendation


class BusinessImpactAnalyzer:
    def __init__(self):
        self.impact_weights = {
            'environment': {
                'production': 1.0,
                'staging': 0.4,
                'development': 0.1,
                'testing': 0.05
            },
            'resource_criticality': {
                'database': 1.0,
                'application': 0.7,
                'web': 0.5,
                'worker': 0.4,
                'cache': 0.3,
                'general': 0.5
            },
            'user_traffic': {
                'high': 1.0,
                'medium': 0.5,
                'low': 0.1,
                'none': 0.01
            }
        }

    def calculate_business_impact(self,
                                environment: str = 'development',
                                resource_type: str = 'general',
                                has_external_dependency: bool = False,
                                user_traffic_level: str = 'low',
                                redundancy_count: int = 1) -> Dict:
        env_score = self.impact_weights['environment'].get(environment.lower(), 0.5)
        criticality_score = self.impact_weights['resource_criticality'].get(resource_type.lower(), 0.5)
        traffic_score = self.impact_weights['user_traffic'].get(user_traffic_level.lower(), 0.1)
        
        redundancy_factor = max(0.3, 1.0 - (redundancy_count - 1) * 0.2) if redundancy_count > 0 else 1.0
        dependency_factor = 1.2 if has_external_dependency else 1.0
        
        impact_score = (env_score * 0.4 + criticality_score * 0.35 + traffic_score * 0.25) * redundancy_factor * dependency_factor
        impact_score = min(1.0, impact_score)
        
        if impact_score >= 0.7:
            impact_level = 'High'
        elif impact_score >= 0.3:
            impact_level = 'Medium'
        else:
            impact_level = 'Low'
        
        return {
            'impact_score': round(impact_score, 3),
            'impact_level': impact_level,
            'components': {
                'environment_score': env_score,
                'criticality_score': criticality_score,
                'traffic_score': traffic_score,
                'redundancy_factor': redundancy_factor,
                'dependency_factor': dependency_factor
            }
        }

    def prioritize_recommendations(self, recommendations: List[OptimizationRecommendation]) -> List[OptimizationRecommendation]:
        prioritized = []
        
        for rec in recommendations:
            savings_factor = rec.monthly_savings / 1000 if rec.monthly_savings > 0 else 0
            
            effort_penalty = {
                'Low': 1.0,
                'Medium': 0.7,
                'High': 0.4
            }.get(rec.effort_level, 0.5)
            
            risk_penalty = {
                'Low': 1.0,
                'Medium': 0.8,
                'High': 0.5
            }.get(rec.risk_level, 0.5)
            
            inverse_business_impact = 1.0 - rec.business_impact_score
            
            priority = (
                savings_factor * 0.4 +
                effort_penalty * 0.25 +
                risk_penalty * 0.2 +
                inverse_business_impact * 0.15
            )
            
            rec.priority_score = round(priority, 4)
            prioritized.append(rec)
        
        prioritized.sort(key=lambda x: (-x.priority_score, -x.monthly_savings))
        
        return prioritized


class CloudOptimizer:
    def __init__(self, data: Dict):
        self.historical_costs = data.get('historical_costs', pd.DataFrame())
        self.instances = data.get('instances', pd.DataFrame())
        self.ebs_volumes = data.get('ebs_volumes', pd.DataFrame())
        self.reservation_recs = data.get('reservation_recs', {})
        self.cloud_provider = data.get('cloud_provider', 'aws')
        
        self.instance_hierarchy = self._get_instance_hierarchy()
        self.sampler = MultiGranularSampler(self.historical_costs, value_col='cost', time_col='date') if not self.historical_costs.empty else None
        self.savings_analyzer = SavingsPlanAnalyzer()
        self.impact_analyzer = BusinessImpactAnalyzer()
        self.price_comparator = CloudPriceComparator()
        self.anomaly_detector = CostAnomalyDetector(self.historical_costs)
        self.budget_forecaster = BudgetForecaster(self.historical_costs)

    def _get_instance_hierarchy(self) -> Dict[str, List[str]]:
        if self.cloud_provider == 'aws':
            return {
                't2': ['t2.micro', 't2.small', 't2.medium', 't2.large'],
                'm5': ['m5.large', 'm5.xlarge', 'm5.2xlarge', 'm5.4xlarge'],
                'c5': ['c5.large', 'c5.xlarge', 'c5.2xlarge', 'c5.4xlarge'],
                'r5': ['r5.large', 'r5.xlarge', 'r5.2xlarge', 'r5.4xlarge'],
            }
        elif self.cloud_provider == 'azure':
            return {
                'B': ['Standard_B1s', 'Standard_B1ms', 'Standard_B2s', 'Standard_B2ms'],
                'Dsv3': ['Standard_D2s_v3', 'Standard_D4s_v3', 'Standard_D8s_v3'],
            }
        else:
            return {
                'e2': ['e2-micro', 'e2-small', 'e2-medium', 'e2-standard-2'],
                'n1': ['n1-standard-1', 'n1-standard-2', 'n1-standard-4'],
            }

    def _find_downsize_target(self, instance_type: str, reduction_factor: float = 0.5) -> Optional[str]:
        for family, types in self.instance_hierarchy.items():
            if instance_type in types:
                current_idx = types.index(instance_type)
                if current_idx > 0:
                    new_idx = max(0, int(current_idx * reduction_factor))
                    return types[new_idx]
        return None

    def _get_instance_cost(self, instance_type: str) -> Dict:
        pricing = {
            'aws': {
                't2.micro': {'hourly': 0.0116, 'monthly': 8.47},
                't2.small': {'hourly': 0.023, 'monthly': 16.79},
                't2.medium': {'hourly': 0.0464, 'monthly': 33.87},
                't2.large': {'hourly': 0.0928, 'monthly': 67.74},
                'm5.large': {'hourly': 0.096, 'monthly': 70.08},
                'm5.xlarge': {'hourly': 0.192, 'monthly': 140.16},
                'm5.2xlarge': {'hourly': 0.384, 'monthly': 280.32},
                'c5.large': {'hourly': 0.085, 'monthly': 62.05},
                'c5.xlarge': {'hourly': 0.17, 'monthly': 124.10},
                'r5.large': {'hourly': 0.126, 'monthly': 91.98},
            }
        }
        return pricing.get(self.cloud_provider, pricing['aws']).get(instance_type, {'hourly': 0.1, 'monthly': 73})

    def get_multi_granular_analysis(self) -> Dict:
        if self.sampler is None:
            return {}
        
        samples = self.sampler.sample(retain_peaks=True)
        peak_features = self.sampler.get_peak_features()
        
        samples_by_granularity = defaultdict(list)
        for s in samples:
            samples_by_granularity[s.granularity].append(s)
        
        return {
            'total_samples': len(samples),
            'peak_count': sum(1 for s in samples if s.is_peak),
            'samples_by_granularity': {k: len(v) for k, v in samples_by_granularity.items()},
            'peak_features': peak_features,
            'samples': samples
        }

    def generate_termination_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        
        if self.instances.empty:
            return recommendations
        
        running_instances = self.instances[self.instances['state'] == 'running']
        
        idle_instances = running_instances[
            (running_instances['avg_cpu_7d'] < 3) &
            (running_instances['avg_memory_7d'] < 5) &
            (running_instances['avg_network_7d'] < 2)
        ]
        
        for _, instance in idle_instances.iterrows():
            monthly_savings = instance['ondemand_cost_30d']
            
            impact = self.impact_analyzer.calculate_business_impact(
                environment=instance.get('environment', 'development'),
                resource_type='general',
                user_traffic_level='low',
                redundancy_count=2
            )
            
            recommendations.append(OptimizationRecommendation(
                type=OptimizationType.TERMINATE,
                resource_id=instance['instance_id'],
                resource_name=instance['name'],
                resource_type='EC2 Instance',
                current_config={'instance_type': instance['instance_type']},
                recommended_config=None,
                monthly_savings=monthly_savings,
                annual_savings=monthly_savings * 12,
                confidence_score=0.95,
                risk_level='Low',
                effort_level='Low',
                business_impact=impact['impact_level'],
                business_impact_score=impact['impact_score'],
                flexibility_score=1.0,
                description=f"Instance {instance['name']} has been idle with <3% CPU and <5% memory usage.",
                action_steps=[
                    "1. Create snapshot of instance volumes",
                    "2. Verify no critical workloads depend on this instance",
                    "3. Terminate the instance",
                    "4. Release associated Elastic IPs and EBS volumes if not needed"
                ]
            ))
        
        stopped_instances = self.instances[self.instances['state'] == 'stopped']
        for _, instance in stopped_instances.iterrows():
            ebs_cost = 10
            
            impact = self.impact_analyzer.calculate_business_impact(
                environment=instance.get('environment', 'development'),
                resource_type='general',
                user_traffic_level='none',
                redundancy_count=1
            )
            
            recommendations.append(OptimizationRecommendation(
                type=OptimizationType.TERMINATE,
                resource_id=instance['instance_id'],
                resource_name=instance['name'],
                resource_type='Stopped EC2 Instance',
                current_config={'instance_type': instance['instance_type'], 'state': 'stopped'},
                recommended_config=None,
                monthly_savings=ebs_cost,
                annual_savings=ebs_cost * 12,
                confidence_score=0.85,
                risk_level='Medium',
                effort_level='Low',
                business_impact=impact['impact_level'],
                business_impact_score=impact['impact_score'],
                flexibility_score=1.0,
                description=f"Instance {instance['name']} has been stopped and is still incurring storage costs.",
                action_steps=[
                    "1. Verify instance is no longer needed",
                    "2. Create final AMI backup if required for compliance",
                    "3. Terminate the instance",
                    "4. Delete any associated EBS volumes"
                ]
            ))
        
        return recommendations

    def generate_downsize_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        
        if self.instances.empty:
            return recommendations
        
        running_instances = self.instances[self.instances['state'] == 'running'].copy()
        
        underutilized = running_instances[
            (running_instances['avg_cpu_7d'] < 25) &
            (running_instances['p95_cpu_7d'] < 40) &
            (running_instances['avg_memory_7d'] < 30) &
            (running_instances['p95_memory_7d'] < 50)
        ]
        
        for _, instance in underutilized.iterrows():
            current_type = instance['instance_type']
            target_type = self._find_downsize_target(current_type)
            
            if target_type and target_type != current_type:
                current_cost = instance['ondemand_cost_30d']
                target_cost = current_cost * 0.5
                monthly_savings = current_cost - target_cost
                
                impact = self.impact_analyzer.calculate_business_impact(
                    environment=instance.get('environment', 'development'),
                    resource_type='application',
                    user_traffic_level='medium' if instance.get('environment') == 'production' else 'low',
                    redundancy_count=2
                )
                
                peak_metrics = {
                    'peak_cpu': instance['max_cpu_7d'],
                    'peak_memory': instance['max_memory_7d'],
                    'p95_cpu': instance['p95_cpu_7d'],
                    'p95_memory': instance['p95_memory_7d']
                }
                
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.DOWNSIZE,
                    resource_id=instance['instance_id'],
                    resource_name=instance['name'],
                    resource_type='EC2 Instance',
                    current_config={
                        'instance_type': current_type,
                        'vcpu': instance['vcpu'],
                        'memory_gb': instance['memory_gb'],
                        'avg_cpu': f"{instance['avg_cpu_7d']:.1f}%",
                        'avg_memory': f"{instance['avg_memory_7d']:.1f}%"
                    },
                    recommended_config={'instance_type': target_type},
                    monthly_savings=monthly_savings,
                    annual_savings=monthly_savings * 12,
                    confidence_score=0.80,
                    risk_level='Medium',
                    effort_level='Medium',
                    business_impact=impact['impact_level'],
                    business_impact_score=impact['impact_score'],
                    flexibility_score=0.9,
                    peak_metrics=peak_metrics,
                    description=f"Instance {instance['name']} is consistently underutilized. Downsizing recommended.",
                    action_steps=[
                        "1. Review application performance baseline",
                        "2. Test downsized instance type in staging environment",
                        "3. Create AMI backup of current instance",
                        "4. Stop instance, change instance type, restart",
                        "5. Monitor application performance for 48 hours"
                    ]
                ))
        
        return recommendations

    def generate_storage_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        
        if self.ebs_volumes.empty:
            return recommendations
        
        unused_volumes = self.ebs_volumes[self.ebs_volumes['state'] == 'available']
        for _, volume in unused_volumes.iterrows():
            impact = self.impact_analyzer.calculate_business_impact(
                environment='development',
                resource_type='storage',
                user_traffic_level='none',
                redundancy_count=1
            )
            
            recommendations.append(OptimizationRecommendation(
                type=OptimizationType.STORAGE_OPT,
                resource_id=volume['volume_id'],
                resource_name=f"EBS-{volume['volume_id'][-8:]}",
                resource_type='EBS Volume',
                current_config={
                    'size_gb': volume['size_gb'],
                    'volume_type': volume['volume_type'],
                    'state': 'available'
                },
                recommended_config=None,
                monthly_savings=volume['monthly_cost'],
                annual_savings=volume['monthly_cost'] * 12,
                confidence_score=0.90,
                risk_level='Low',
                effort_level='Low',
                business_impact=impact['impact_level'],
                business_impact_score=impact['impact_score'],
                flexibility_score=1.0,
                description="Unattached EBS volume detected. Consider deleting or snapshotting and deleting.",
                action_steps=[
                    "1. Create snapshot of the volume for backup",
                    "2. Verify volume is not referenced in any automation",
                    "3. Delete the volume",
                    "4. Archive snapshot to S3 Glacier for long-term storage"
                ]
            ))
        
        gp2_volumes = self.ebs_volumes[self.ebs_volumes['volume_type'] == 'gp2']
        for _, volume in gp2_volumes.iterrows():
            current_cost = volume['monthly_cost']
            gp3_cost = volume['size_gb'] * 0.08
            monthly_savings = current_cost - gp3_cost
            
            if monthly_savings > 0:
                impact = self.impact_analyzer.calculate_business_impact(
                    environment='staging',
                    resource_type='storage',
                    user_traffic_level='low',
                    redundancy_count=2
                )
                
                recommendations.append(OptimizationRecommendation(
                    type=OptimizationType.STORAGE_OPT,
                    resource_id=volume['volume_id'],
                    resource_name=f"EBS-{volume['volume_id'][-8:]}",
                    resource_type='EBS Volume',
                    current_config={
                        'size_gb': volume['size_gb'],
                        'volume_type': 'gp2'
                    },
                    recommended_config={'volume_type': 'gp3'},
                    monthly_savings=monthly_savings,
                    annual_savings=monthly_savings * 12,
                    confidence_score=0.95,
                    risk_level='Low',
                    effort_level='Low',
                    business_impact=impact['impact_level'],
                    business_impact_score=impact['impact_score'],
                    flexibility_score=1.0,
                    description="Upgrade gp2 volume to gp3 for better performance and lower cost.",
                    action_steps=[
                        "1. Modify volume type from gp2 to gp3 via AWS console/API",
                        "2. No downtime required, modification occurs in background",
                        "3. Adjust IOPS and throughput settings if needed"
                    ]
                ))
        
        return recommendations

    def generate_savings_plan_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        
        if self.instances.empty:
            return recommendations
        
        running_on_demand = self.instances[
            (self.instances['state'] == 'running') &
            (self.instances['purchase_type'] == 'on_demand')
        ]
        
        instance_type_groups = running_on_demand.groupby(['instance_type', 'environment'])
        
        for (instance_type, environment), group in instance_type_groups:
            count = len(group)
            if count < 1:
                continue
            
            avg_utilization = group['avg_cpu_7d'].mean() / 100
            avg_age_days = (datetime.now() - group['launch_time']).dt.days.mean()
            
            hourly_pattern = np.random.normal(0.7, 0.15, 24).clip(0, 1)
            
            flexibility_score = self.savings_analyzer.calculate_flexibility_score(
                hourly_pattern=hourly_pattern,
                instance_age_days=avg_age_days,
                workload_type=environment
            )
            
            hourly_cost = self._get_instance_cost(instance_type).get('hourly', 0.1)
            
            purchase_rec = self.savings_analyzer.recommend_purchase_type(
                flexibility_score=flexibility_score,
                utilization_rate=avg_utilization,
                hourly_on_demand_cost=hourly_cost
            )
            
            monthly_savings = purchase_rec['savings_vs_ondemand'] * count
            
            impact = self.impact_analyzer.calculate_business_impact(
                environment=environment,
                resource_type='general',
                user_traffic_level='high' if environment == 'production' else 'low',
                redundancy_count=count
            )
            
            if purchase_rec['type'] == 'on_demand':
                continue
            
            recommendations.append(OptimizationRecommendation(
                type=OptimizationType.SAVINGS_PLAN,
                resource_id=f"SP-{instance_type}-{environment}",
                resource_name=f"{instance_type} Savings Plan",
                resource_type='Savings Plan',
                current_config={
                    'purchase_type': 'on_demand',
                    'instance_type': instance_type,
                    'count': count,
                    'environment': environment
                },
                recommended_config={
                    'purchase_type': purchase_rec['type'],
                    'flexibility_score': flexibility_score,
                    'recommended_count': max(1, int(count * 0.7))
                },
                monthly_savings=monthly_savings,
                annual_savings=monthly_savings * 12,
                confidence_score=min(0.95, avg_utilization + 0.2),
                risk_level='Medium' if purchase_rec['type'] == 'reserved_instance_3y' else 'Low',
                effort_level='Low',
                business_impact=impact['impact_level'],
                business_impact_score=impact['impact_score'],
                flexibility_score=flexibility_score,
                description=f"{purchase_rec['reason']} for {count} instances. Flexibility: {flexibility_score:.2f}",
                action_steps=[
                    f"1. Review {count} {instance_type} instances in {environment}",
                    f"2. Evaluate {purchase_rec['type']} commitment",
                    f"3. Estimated breakeven: {purchase_rec.get('breakeven_months', 'N/A')} months",
                    "4. Purchase and apply to instances"
                ]
            ))
        
        return recommendations

    def generate_reservation_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        
        recs = self.reservation_recs.get('recommendations', [])
        
        for rec in recs:
            flexibility_score = max(0.5, rec['utilization_rate'])
            
            impact = self.impact_analyzer.calculate_business_impact(
                environment='production',
                resource_type='general',
                user_traffic_level='high',
                redundancy_count=rec['current_instances']
            )
            
            recommendations.append(OptimizationRecommendation(
                type=OptimizationType.RESERVE,
                resource_id=f"RES-{rec['instance_type']}-{rec['region']}",
                resource_name=f"{rec['instance_type']} RI",
                resource_type='Reserved Instance',
                current_config={
                    'purchase_type': 'on_demand',
                    'instance_type': rec['instance_type'],
                    'region': rec['region'],
                    'count': rec['current_instances']
                },
                recommended_config={
                    'purchase_type': 'reserved',
                    'term_years': 1,
                    'count': rec['recommended_count'],
                    'flexibility_score': flexibility_score
                },
                monthly_savings=rec['monthly_savings_1y'],
                annual_savings=rec['yearly_savings_1y'],
                confidence_score=rec['utilization_rate'],
                risk_level='Medium',
                effort_level='Low',
                business_impact=impact['impact_level'],
                business_impact_score=impact['impact_score'],
                flexibility_score=flexibility_score,
                description=f"Purchase 1-year reserved instances for {rec['recommended_count']} {rec['instance_type']} instances with {rec['utilization_rate']:.0%} utilization.",
                action_steps=[
                    f"1. Review utilization history for {rec['instance_type']} in {rec['region']}",
                    f"2. Purchase {rec['recommended_count']} 1-year Convertible Reserved Instances",
                    "3. Apply to running instances automatically",
                    "4. Monitor RI utilization monthly"
                ]
            ))
        
        return recommendations

    def generate_all_recommendations(self) -> Dict:
        termination_recs = self.generate_termination_recommendations()
        downsize_recs = self.generate_downsize_recommendations()
        storage_recs = self.generate_storage_recommendations()
        reserve_recs = self.generate_reservation_recommendations()
        savings_plan_recs = self.generate_savings_plan_recommendations()
        
        all_recs = (
            termination_recs + 
            downsize_recs + 
            storage_recs + 
            reserve_recs +
            savings_plan_recs
        )
        
        prioritized_recs = self.impact_analyzer.prioritize_recommendations(all_recs)
        
        total_monthly = sum(r.monthly_savings for r in all_recs)
        total_annual = sum(r.annual_savings for r in all_recs)
        
        by_type = {
            'terminate': termination_recs,
            'downsize': downsize_recs,
            'storage': storage_recs,
            'reserve': reserve_recs,
            'savings_plan': savings_plan_recs
        }
        
        savings_by_type = {
            'termination': sum(r.monthly_savings for r in termination_recs),
            'downsizing': sum(r.monthly_savings for r in downsize_recs),
            'storage': sum(r.monthly_savings for r in storage_recs),
            'reserved_instances': sum(r.monthly_savings for r in reserve_recs),
            'savings_plans': sum(r.monthly_savings for r in savings_plan_recs)
        }
        
        low_impact_recs = [r for r in prioritized_recs if r.business_impact_score < 0.3]
        medium_impact_recs = [r for r in prioritized_recs if 0.3 <= r.business_impact_score < 0.7]
        high_impact_recs = [r for r in prioritized_recs if r.business_impact_score >= 0.7]
        
        low_flexibility_recs = [r for r in prioritized_recs if r.flexibility_score < 0.5]
        
        return {
            'all_recommendations': prioritized_recs,
            'by_type': by_type,
            'savings_by_type': savings_by_type,
            'total_monthly_savings': total_monthly,
            'total_annual_savings': total_annual,
            'count_by_type': {k: len(v) for k, v in by_type.items()},
            'by_business_impact': {
                'low': low_impact_recs,
                'medium': medium_impact_recs,
                'high': high_impact_recs
            },
            'low_flexibility_recommendations': low_flexibility_recs,
            'high_priority': [r for r in prioritized_recs if r.risk_level == 'Low' and r.monthly_savings > 50],
            'quick_wins': [r for r in prioritized_recs if r.effort_level == 'Low' and r.business_impact_score < 0.3],
            'multi_granular_analysis': self.get_multi_granular_analysis()
        }

    def get_cloud_price_comparison(self, instance_type: str = None, vcpu: int = None, memory: int = None) -> Dict:
        if instance_type:
            comparison = self.price_comparator.compare_instance_prices(
                self.cloud_provider,
                instance_type
            )
            instance_specs = self.price_comparator.INSTANCE_MAPPING[self.cloud_provider].get(instance_type, {})
            return {
                'comparison': comparison,
                'price_matrix': self.price_comparator.get_price_matrix(
                    instance_specs.get('vcpu', 4),
                    instance_specs.get('memory', 16)
                )
            }
        elif vcpu and memory:
            return {
                'price_matrix': self.price_comparator.get_price_matrix(vcpu, memory)
            }
        else:
            instances = self.instances[self.instances['state'] == 'running'].head(10)
            batch_comparisons = self.price_comparator.batch_compare([
                {
                    'cloud_provider': self.cloud_provider,
                    'instance_type': row['instance_type']
                }
                for _, row in instances.iterrows()
            ])
            total_savings = sum(c.annual_savings for c in batch_comparisons if c.best_cloud != self.cloud_provider)
            return {
                'batch_comparisons': batch_comparisons,
                'total_potential_annual_savings': total_savings,
                'current_cloud': self.cloud_provider
            }

    def detect_cost_anomalies(self, threshold: float = 0.2) -> Dict:
        anomalies = self.anomaly_detector.detect_anomalies(threshold=threshold)
        summary = self.anomaly_detector.get_anomaly_summary(anomalies)
        return {
            'anomalies': anomalies,
            'summary': summary
        }

    def forecast_budget(self, annual_budget: float = None, forecast_months: int = 12) -> Dict:
        if self.historical_costs is None or self.historical_costs.empty:
            return {'error': 'No historical cost data available'}
        
        monthly_budget = annual_budget / 12 if annual_budget else None
        
        forecast = self.budget_forecaster.forecast_budget(
            budget_amount=annual_budget,
            forecast_months=forecast_months
        )
        
        scenarios = self.budget_forecaster.multi_scenario_forecast(
            budget_amount=annual_budget,
            forecast_months=forecast_months
        )
        
        alert_thresholds = self.budget_forecaster.get_budget_alert_thresholds(
            monthly_budget if monthly_budget else forecast.projected_cost / forecast_months
        )
        
        return {
            'forecast': forecast,
            'scenarios': scenarios,
            'alert_thresholds': alert_thresholds
        }

    def generate_execution_plan(self, recommendations: List[OptimizationRecommendation]) -> Dict:
        low_impact = [r for r in recommendations if r.business_impact_score < 0.3]
        medium_impact = [r for r in recommendations if 0.3 <= r.business_impact_score < 0.7]
        high_impact = [r for r in recommendations if r.business_impact_score >= 0.7]
        
        immediate = [r for r in low_impact if r.effort_level == 'Low']
        short_term = low_impact + [r for r in medium_impact if r.effort_level == 'Low']
        long_term = high_impact + [r for r in medium_impact if r.effort_level in ['Medium', 'High']]
        
        return {
            'immediate': {
                'items': immediate,
                'timeframe': '0-7 days',
                'monthly_savings': sum(r.monthly_savings for r in immediate),
                'description': 'Low business impact, low effort - execute immediately',
                'avg_impact_score': np.mean([r.business_impact_score for r in immediate]) if immediate else 0
            },
            'short_term': {
                'items': short_term,
                'timeframe': '1-4 weeks',
                'monthly_savings': sum(r.monthly_savings for r in short_term),
                'description': 'Low/Medium business impact, some planning required',
                'avg_impact_score': np.mean([r.business_impact_score for r in short_term]) if short_term else 0
            },
            'long_term': {
                'items': long_term,
                'timeframe': '1-3 months',
                'monthly_savings': sum(r.monthly_savings for r in long_term),
                'description': 'High business impact, requires significant planning and testing',
                'avg_impact_score': np.mean([r.business_impact_score for r in long_term]) if long_term else 0
            }
        }

    def calculate_roi(self, recommendations: List[OptimizationRecommendation]) -> Dict:
        total_savings = sum(r.monthly_savings for r in recommendations)
        
        effort_costs = {
            'Low': 100,
            'Medium': 500,
            'High': 2000
        }
        
        implementation_cost = sum(effort_costs.get(r.effort_level, 100) for r in recommendations)
        
        if implementation_cost > 0:
            roi_months = implementation_cost / total_savings if total_savings > 0 else float('inf')
        else:
            roi_months = 0
        
        avg_flexibility = np.mean([r.flexibility_score for r in recommendations]) if recommendations else 0
        avg_business_impact = np.mean([r.business_impact_score for r in recommendations]) if recommendations else 0
        
        return {
            'total_monthly_savings': total_savings,
            'estimated_implementation_cost': implementation_cost,
            'roi_months': roi_months,
            'first_year_net_savings': (total_savings * 12) - implementation_cost,
            'payback_period': f"< 1 month" if roi_months < 1 else f"{roi_months:.1f} months",
            'avg_flexibility_score': avg_flexibility,
            'avg_business_impact_score': avg_business_impact
        }


@dataclass
class CloudPriceComparison:
    instance_type: str
    current_cloud: str
    current_price: float
    best_cloud: str
    best_price: float
    monthly_savings: float
    annual_savings: float
    price_difference_pct: float
    equivalent_instances: Dict[str, float]
    migration_complexity: str
    migration_effort_months: float


@dataclass
class CostAnomaly:
    timestamp: pd.Timestamp
    service: str
    region: str
    actual_cost: float
    expected_cost: float
    deviation_pct: float
    anomaly_type: str
    root_cause: str
    root_cause_confidence: float
    contributing_factors: List[Dict]
    severity: str
    recommended_action: str


@dataclass
class BudgetForecast:
    forecast_period: str
    forecast_start_date: pd.Timestamp
    forecast_end_date: pd.Timestamp
    projected_cost: float
    budget_amount: float
    budget_variance: float
    budget_variance_pct: float
    over_budget_risk: float
    risk_level: str
    monthly_forecast: pd.DataFrame
    key_drivers: List[Dict]
    mitigation_recommendations: List[str]


class CloudPriceComparator:
    CLOUD_PROVIDERS = ['aws', 'azure', 'gcp']
    
    INSTANCE_MAPPING = {
        'aws': {
            't2.micro': {'vcpu': 1, 'memory': 1, 'family': 'burstable'},
            't2.small': {'vcpu': 1, 'memory': 2, 'family': 'burstable'},
            't2.medium': {'vcpu': 2, 'memory': 4, 'family': 'burstable'},
            't2.large': {'vcpu': 2, 'memory': 8, 'family': 'burstable'},
            'm5.large': {'vcpu': 2, 'memory': 8, 'family': 'general'},
            'm5.xlarge': {'vcpu': 4, 'memory': 16, 'family': 'general'},
            'm5.2xlarge': {'vcpu': 8, 'memory': 32, 'family': 'general'},
            'c5.large': {'vcpu': 2, 'memory': 4, 'family': 'compute'},
            'c5.xlarge': {'vcpu': 4, 'memory': 8, 'family': 'compute'},
            'c5.2xlarge': {'vcpu': 8, 'memory': 16, 'family': 'compute'},
            'r5.large': {'vcpu': 2, 'memory': 16, 'family': 'memory'},
            'r5.xlarge': {'vcpu': 4, 'memory': 32, 'family': 'memory'},
            'r5.2xlarge': {'vcpu': 8, 'memory': 64, 'family': 'memory'},
        },
        'azure': {
            'Standard_B1s': {'vcpu': 1, 'memory': 1, 'family': 'burstable'},
            'Standard_B1ms': {'vcpu': 1, 'memory': 2, 'family': 'burstable'},
            'Standard_B2s': {'vcpu': 2, 'memory': 4, 'family': 'burstable'},
            'Standard_B2ms': {'vcpu': 2, 'memory': 8, 'family': 'burstable'},
            'Standard_D2s_v3': {'vcpu': 2, 'memory': 8, 'family': 'general'},
            'Standard_D4s_v3': {'vcpu': 4, 'memory': 16, 'family': 'general'},
            'Standard_D8s_v3': {'vcpu': 8, 'memory': 32, 'family': 'general'},
            'Standard_F2s_v2': {'vcpu': 2, 'memory': 4, 'family': 'compute'},
            'Standard_F4s_v2': {'vcpu': 4, 'memory': 8, 'family': 'compute'},
            'Standard_F8s_v2': {'vcpu': 8, 'memory': 16, 'family': 'compute'},
            'Standard_E2s_v3': {'vcpu': 2, 'memory': 16, 'family': 'memory'},
            'Standard_E4s_v3': {'vcpu': 4, 'memory': 32, 'family': 'memory'},
            'Standard_E8s_v3': {'vcpu': 8, 'memory': 64, 'family': 'memory'},
        },
        'gcp': {
            'e2-micro': {'vcpu': 2, 'memory': 1, 'family': 'burstable'},
            'e2-small': {'vcpu': 2, 'memory': 2, 'family': 'burstable'},
            'e2-medium': {'vcpu': 2, 'memory': 4, 'family': 'burstable'},
            'e2-standard-2': {'vcpu': 2, 'memory': 8, 'family': 'general'},
            'e2-standard-4': {'vcpu': 4, 'memory': 16, 'family': 'general'},
            'e2-standard-8': {'vcpu': 8, 'memory': 32, 'family': 'general'},
            'n2-standard-2': {'vcpu': 2, 'memory': 8, 'family': 'general'},
            'n2-standard-4': {'vcpu': 4, 'memory': 16, 'family': 'general'},
            'c2-standard-4': {'vcpu': 4, 'memory': 16, 'family': 'compute'},
            'c2-standard-8': {'vcpu': 8, 'memory': 32, 'family': 'compute'},
            'm2-ultramem-8': {'vcpu': 8, 'memory': 128, 'family': 'memory'},
        }
    }
    
    PRICING_DATA = {
        'aws': {
            't2.micro': {'hourly': 0.0116, 'monthly': 8.47},
            't2.small': {'hourly': 0.023, 'monthly': 16.79},
            't2.medium': {'hourly': 0.0464, 'monthly': 33.87},
            't2.large': {'hourly': 0.0928, 'monthly': 67.74},
            'm5.large': {'hourly': 0.096, 'monthly': 70.08},
            'm5.xlarge': {'hourly': 0.192, 'monthly': 140.16},
            'm5.2xlarge': {'hourly': 0.384, 'monthly': 280.32},
            'c5.large': {'hourly': 0.085, 'monthly': 62.05},
            'c5.xlarge': {'hourly': 0.17, 'monthly': 124.10},
            'c5.2xlarge': {'hourly': 0.34, 'monthly': 248.20},
            'r5.large': {'hourly': 0.126, 'monthly': 91.98},
            'r5.xlarge': {'hourly': 0.252, 'monthly': 183.96},
            'r5.2xlarge': {'hourly': 0.504, 'monthly': 367.92},
        },
        'azure': {
            'Standard_B1s': {'hourly': 0.0106, 'monthly': 7.74},
            'Standard_B1ms': {'hourly': 0.0212, 'monthly': 15.48},
            'Standard_B2s': {'hourly': 0.0424, 'monthly': 30.96},
            'Standard_B2ms': {'hourly': 0.0847, 'monthly': 61.83},
            'Standard_D2s_v3': {'hourly': 0.092, 'monthly': 67.16},
            'Standard_D4s_v3': {'hourly': 0.184, 'monthly': 134.32},
            'Standard_D8s_v3': {'hourly': 0.368, 'monthly': 268.64},
            'Standard_F2s_v2': {'hourly': 0.072, 'monthly': 52.56},
            'Standard_F4s_v2': {'hourly': 0.144, 'monthly': 105.12},
            'Standard_F8s_v2': {'hourly': 0.288, 'monthly': 210.24},
            'Standard_E2s_v3': {'hourly': 0.134, 'monthly': 97.82},
            'Standard_E4s_v3': {'hourly': 0.268, 'monthly': 195.64},
            'Standard_E8s_v3': {'hourly': 0.536, 'monthly': 391.28},
        },
        'gcp': {
            'e2-micro': {'hourly': 0.0085, 'monthly': 6.20},
            'e2-small': {'hourly': 0.017, 'monthly': 12.41},
            'e2-medium': {'hourly': 0.034, 'monthly': 24.82},
            'e2-standard-2': {'hourly': 0.067, 'monthly': 48.91},
            'e2-standard-4': {'hourly': 0.134, 'monthly': 97.82},
            'e2-standard-8': {'hourly': 0.268, 'monthly': 195.64},
            'n2-standard-2': {'hourly': 0.077, 'monthly': 56.21},
            'n2-standard-4': {'hourly': 0.154, 'monthly': 112.42},
            'c2-standard-4': {'hourly': 0.17, 'monthly': 124.10},
            'c2-standard-8': {'hourly': 0.34, 'monthly': 248.20},
            'm2-ultramem-8': {'hourly': 0.628, 'monthly': 458.44},
        }
    }
    
    def __init__(self):
        self.discount_factors = {
            'aws': {'ri_1y': 0.6, 'ri_3y': 0.45, 'sp_1y': 0.7, 'sp_3y': 0.55},
            'azure': {'ri_1y': 0.65, 'ri_3y': 0.5, 'sp_1y': 0.72, 'sp_3y': 0.58},
            'gcp': {'ri_1y': 0.62, 'ri_3y': 0.47, 'sp_1y': 0.7, 'sp_3y': 0.55},
        }
    
    def _find_equivalent_instances(self, vcpu: int, memory: int, family: str) -> Dict[str, str]:
        equivalents = {}
        for provider in self.CLOUD_PROVIDERS:
            best_match = None
            best_score = float('inf')
            for instance_type, specs in self.INSTANCE_MAPPING[provider].items():
                if specs['family'] != family:
                    continue
                vcpu_diff = abs(specs['vcpu'] - vcpu)
                memory_diff = abs(specs['memory'] - memory)
                score = vcpu_diff * 2 + memory_diff
                if score < best_score:
                    best_score = score
                    best_match = instance_type
            if best_match:
                equivalents[provider] = best_match
        return equivalents
    
    def compare_instance_prices(self, 
                                  current_cloud: str, 
                                  instance_type: str,
                                  monthly_hours: int = 730,
                                  purchase_type: str = 'on_demand') -> CloudPriceComparison:
        if current_cloud not in self.INSTANCE_MAPPING:
            raise ValueError(f"Unsupported cloud provider: {current_cloud}")
        
        if instance_type not in self.INSTANCE_MAPPING[current_cloud]:
            raise ValueError(f"Unknown instance type: {instance_type} for {current_cloud}")
        
        current_specs = self.INSTANCE_MAPPING[current_cloud][instance_type]
        equivalents = self._find_equivalent_instances(
            current_specs['vcpu'], 
            current_specs['memory'], 
            current_specs['family']
        )
        
        prices = {}
        for provider, equivalent_type in equivalents.items():
            base_price = self.PRICING_DATA[provider][equivalent_type]['monthly']
            if purchase_type == 'ri_1y':
                price = base_price * self.discount_factors[provider]['ri_1y']
            elif purchase_type == 'ri_3y':
                price = base_price * self.discount_factors[provider]['ri_3y']
            elif purchase_type == 'sp_1y':
                price = base_price * self.discount_factors[provider]['sp_1y']
            elif purchase_type == 'sp_3y':
                price = base_price * self.discount_factors[provider]['sp_3y']
            else:
                price = base_price
            prices[provider] = price
        
        current_price = prices.get(current_cloud, 0)
        best_cloud = min(prices, key=prices.get)
        best_price = prices[best_cloud]
        
        monthly_savings = current_price - best_price
        annual_savings = monthly_savings * 12
        price_difference_pct = ((current_price - best_price) / current_price * 100) if current_price > 0 else 0
        
        if price_difference_pct > 20:
            migration_complexity = 'High'
            migration_effort = 3.0
        elif price_difference_pct > 10:
            migration_complexity = 'Medium'
            migration_effort = 1.5
        else:
            migration_complexity = 'Low'
            migration_effort = 0.5
        
        return CloudPriceComparison(
            instance_type=instance_type,
            current_cloud=current_cloud,
            current_price=current_price,
            best_cloud=best_cloud,
            best_price=best_price,
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            price_difference_pct=price_difference_pct,
            equivalent_instances=equivalents,
            migration_complexity=migration_complexity,
            migration_effort_months=migration_effort
        )
    
    def batch_compare(self, instances: List[Dict]) -> List[CloudPriceComparison]:
        results = []
        for instance in instances:
            try:
                comparison = self.compare_instance_prices(
                    instance.get('cloud_provider', 'aws'),
                    instance.get('instance_type'),
                    instance.get('monthly_hours', 730),
                    instance.get('purchase_type', 'on_demand')
                )
                results.append(comparison)
            except (ValueError, KeyError):
                continue
        return results
    
    def get_price_matrix(self, vcpu: int, memory: int) -> pd.DataFrame:
        equivalents = self._find_equivalent_instances(vcpu, memory, 'general')
        data = []
        for provider, instance_type in equivalents.items():
            pricing = self.PRICING_DATA[provider].get(instance_type, {})
            data.append({
                'Provider': provider.upper(),
                'Instance Type': instance_type,
                'Hourly ($)': pricing.get('hourly', 0),
                'Monthly ($)': pricing.get('monthly', 0),
                '1y RI Monthly ($)': pricing.get('monthly', 0) * self.discount_factors[provider]['ri_1y'],
                '3y RI Monthly ($)': pricing.get('monthly', 0) * self.discount_factors[provider]['ri_3y'],
            })
        return pd.DataFrame(data)


class CostAnomalyDetector:
    ANOMALY_THRESHOLDS = {
        'critical': 0.5,
        'high': 0.3,
        'medium': 0.2,
        'low': 0.1
    }
    
    ROOT_CAUSE_PATTERNS = {
        'unexpected_traffic_spike': {
            'keywords': ['traffic', 'request', 'load', 'usage', 'bandwidth'],
            'services': ['EC2', 'Lambda', 'API Gateway', 'CloudFront', 'DataTransfer'],
            'confidence': 0.85
        },
        'new_resources_deployed': {
            'keywords': ['new', 'deploy', 'create', 'launch', 'provision'],
            'services': ['EC2', 'RDS', 'EBS', 'S3', 'Redshift'],
            'confidence': 0.75
        },
        'misconfiguration': {
            'keywords': ['config', 'setting', 'parameter', 'auto-scaling', 'provisioned'],
            'services': ['RDS', 'DynamoDB', 'ECS', 'Kubernetes'],
            'confidence': 0.7
        },
        'storage_growth': {
            'keywords': ['storage', 'volume', 'snapshot', 'backup', 'archive'],
            'services': ['S3', 'EBS', 'RDS', 'Glacier', 'Backup'],
            'confidence': 0.8
        },
        'price_increase': {
            'keywords': ['price', 'rate', 'fee', 'charge', 'premium'],
            'services': ['All'],
            'confidence': 0.65
        },
        'reserved_instance_expiry': {
            'keywords': ['expire', 'end', 'terminate', 'expiry'],
            'services': ['EC2', 'RDS', 'Redshift'],
            'confidence': 0.9
        }
    }
    
    def __init__(self, historical_costs: pd.DataFrame = None):
        self.historical_costs = historical_costs
        self.baseline_model = None
        self.seasonality_patterns = {}
        
    def _calculate_statistical_baseline(self, 
                                         time_series: pd.Series, 
                                         window: int = 7) -> Tuple[pd.Series, pd.Series, pd.Series]:
        rolling_mean = time_series.rolling(window=window, min_periods=3).mean()
        rolling_std = time_series.rolling(window=window, min_periods=3).std()
        
        expected = rolling_mean
        upper_bound = rolling_mean + 2 * rolling_std
        lower_bound = rolling_mean - 2 * rolling_std
        
        return expected, upper_bound, lower_bound
    
    def _detect_seasonality(self, time_series: pd.Series) -> Dict:
        if len(time_series) < 14:
            return {'weekly': 0, 'daily': 0, 'has_seasonality': False}
        
        daily_pattern = time_series.groupby(time_series.index.dayofweek).mean()
        weekly_variation = daily_pattern.std() / daily_pattern.mean() if daily_pattern.mean() > 0 else 0
        
        hourly_pattern = time_series.groupby(time_series.index.hour).mean()
        daily_variation = hourly_pattern.std() / hourly_pattern.mean() if hourly_pattern.mean() > 0 else 0
        
        return {
            'weekly': weekly_variation,
            'daily': daily_variation,
            'has_seasonality': weekly_variation > 0.1 or daily_variation > 0.1
        }
    
    def _identify_root_cause(self, 
                               anomaly: Dict, 
                               service_history: pd.DataFrame) -> Dict:
        service = anomaly.get('service', 'Unknown')
        region = anomaly.get('region', 'Unknown')
        
        best_cause = None
        best_confidence = 0
        contributing_factors = []
        
        recent_history = service_history.tail(14)
        cost_change = (recent_history.iloc[-1] - recent_history.iloc[0]) / recent_history.iloc[0] if recent_history.iloc[0] > 0 else 0
        
        for cause_name, cause_pattern in self.ROOT_CAUSE_PATTERNS.items():
            if service in cause_pattern['services'] or cause_pattern['services'] == ['All']:
                confidence = cause_pattern['confidence']
                
                if cause_name == 'storage_growth' and cost_change > 0.3:
                    confidence += 0.1
                    contributing_factors.append({
                        'factor': 'Rapid storage growth',
                        'impact': f'{cost_change:.1%} increase in 14 days'
                    })
                
                if cause_name == 'unexpected_traffic_spike' and anomaly.get('deviation_pct', 0) > 0.5:
                    confidence += 0.05
                    contributing_factors.append({
                        'factor': 'Large cost deviation',
                        'impact': f'{anomaly.get("deviation_pct", 0):.1%} above expected'
                    })
                
                confidence = min(1.0, confidence)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_cause = cause_name
        
        if best_cause is None:
            best_cause = 'unknown'
            best_confidence = 0.3
        
        cause_descriptions = {
            'unexpected_traffic_spike': 'Unexpected traffic spike caused increased resource consumption',
            'new_resources_deployed': 'New resources were deployed without proper cost tracking',
            'misconfiguration': 'Resource misconfiguration leading to over-provisioning',
            'storage_growth': 'Uncontrolled storage growth including snapshots and backups',
            'price_increase': 'Cloud service price increase or change in pricing tier',
            'reserved_instance_expiry': 'Reserved instances expired and workloads moved to on-demand pricing',
            'unknown': 'Unable to determine root cause with high confidence'
        }
        
        recommended_actions = {
            'unexpected_traffic_spike': [
                'Analyze access logs to identify traffic source',
                'Consider implementing auto-scaling with cost limits',
                'Review CDN and caching strategies'
            ],
            'new_resources_deployed': [
                'Implement infrastructure-as-code with cost approval workflows',
                'Tag all resources for cost allocation',
                'Set up budget alerts for new deployments'
            ],
            'misconfiguration': [
                'Review resource configuration settings',
                'Implement automated configuration auditing',
                'Consider using cost optimization tools'
            ],
            'storage_growth': [
                'Implement lifecycle policies for data retention',
                'Delete unused volumes and snapshots',
                'Consider archiving cold data to cheaper storage tiers'
            ],
            'price_increase': [
                'Review new pricing terms and discounts',
                'Consider negotiating enterprise agreements',
                'Evaluate alternative cloud providers'
            ],
            'reserved_instance_expiry': [
                'Purchase new reserved instances or savings plans',
                'Review instance utilization before committing',
                'Consider convertible RIs for flexibility'
            ],
            'unknown': [
                'Enable detailed cost logging and monitoring',
                'Review all recent changes in the environment',
                'Consider engaging FinOps team for deeper analysis'
            ]
        }
        
        return {
            'root_cause': best_cause,
            'root_cause_description': cause_descriptions[best_cause],
            'root_cause_confidence': best_confidence,
            'contributing_factors': contributing_factors,
            'recommended_actions': recommended_actions[best_cause]
        }
    
    def detect_anomalies(self, 
                          cost_data: pd.DataFrame = None,
                          threshold: float = 0.2,
                          min_days_baseline: int = 7) -> List[CostAnomaly]:
        if cost_data is None:
            cost_data = self.historical_costs
            
        if cost_data is None or cost_data.empty:
            return []
        
        anomalies = []
        
        daily_totals = cost_data.groupby('date')['cost'].sum()
        
        if len(daily_totals) < min_days_baseline + 1:
            return []
        
        expected, upper_bound, lower_bound = self._calculate_statistical_baseline(daily_totals)
        
        for i in range(min_days_baseline, len(daily_totals)):
            actual = daily_totals.iloc[i]
            exp = expected.iloc[i]
            date = daily_totals.index[i]
            
            if exp <= 0:
                continue
                
            deviation_pct = (actual - exp) / exp
            
            if abs(deviation_pct) >= threshold:
                anomaly_type = 'spike' if deviation_pct > 0 else 'drop'
                
                if deviation_pct >= self.ANOMALY_THRESHOLDS['critical']:
                    severity = 'Critical'
                elif deviation_pct >= self.ANOMALY_THRESHOLDS['high']:
                    severity = 'High'
                elif deviation_pct >= self.ANOMALY_THRESHOLDS['medium']:
                    severity = 'Medium'
                else:
                    severity = 'Low'
                
                day_data = cost_data[cost_data['date'] == date]
                service_breakdown = day_data.groupby('service')['cost'].sum()
                top_service = service_breakdown.idxmax() if not service_breakdown.empty else 'Unknown'
                top_region = day_data.groupby('region')['cost'].sum().idxmax() if not day_data.empty else 'Unknown'
                
                service_history = cost_data[cost_data['service'] == top_service].groupby('date')['cost'].sum()
                
                root_cause_analysis = self._identify_root_cause({
                    'service': top_service,
                    'region': top_region,
                    'deviation_pct': deviation_pct,
                    'date': date
                }, service_history)
                
                anomalies.append(CostAnomaly(
                    timestamp=pd.Timestamp(date),
                    service=top_service,
                    region=top_region,
                    actual_cost=actual,
                    expected_cost=exp,
                    deviation_pct=deviation_pct,
                    anomaly_type=anomaly_type,
                    root_cause=root_cause_analysis['root_cause_description'],
                    root_cause_confidence=root_cause_analysis['root_cause_confidence'],
                    contributing_factors=root_cause_analysis['contributing_factors'],
                    severity=severity,
                    recommended_action=root_cause_analysis['recommended_actions'][0]
                ))
        
        anomalies.sort(key=lambda x: (-abs(x.deviation_pct), -x.timestamp.timestamp()))
        
        return anomalies
    
    def get_anomaly_summary(self, anomalies: List[CostAnomaly]) -> Dict:
        if not anomalies:
            return {'total': 0, 'by_severity': {}, 'by_type': {}, 'estimated_impact': 0}
        
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        estimated_impact = 0
        
        for anomaly in anomalies:
            by_severity[anomaly.severity] += 1
            by_type[anomaly.anomaly_type] += 1
            if anomaly.anomaly_type == 'spike':
                estimated_impact += anomaly.actual_cost - anomaly.expected_cost
        
        return {
            'total': len(anomalies),
            'by_severity': dict(by_severity),
            'by_type': dict(by_type),
            'estimated_impact': estimated_impact,
            'critical_count': by_severity.get('Critical', 0),
            'high_count': by_severity.get('High', 0)
        }


class BudgetForecaster:
    RISK_LEVELS = {
        'critical': (0.8, 1.0, '🔴 Critical'),
        'high': (0.5, 0.8, '🟠 High'),
        'medium': (0.2, 0.5, '🟡 Medium'),
        'low': (0.0, 0.2, '🟢 Low')
    }
    
    GROWTH_SCENARIOS = {
        'conservative': 0.05,
        'moderate': 0.10,
        'aggressive': 0.20
    }
    
    def __init__(self, historical_costs: pd.DataFrame = None):
        self.historical_costs = historical_costs
        self.service_cost_trends = {}
        
    def _calculate_monthly_totals(self, cost_data: pd.DataFrame) -> pd.Series:
        if cost_data is None or cost_data.empty:
            return pd.Series()
        
        monthly = cost_data.groupby(cost_data['date'].dt.to_period('M'))['cost'].sum()
        monthly.index = monthly.index.to_timestamp()
        return monthly.sort_index()
    
    def _calculate_growth_rate(self, time_series: pd.Series) -> Dict:
        if len(time_series) < 2:
            return {'monthly_growth': 0, 'annual_growth': 0, 'trend': 'stable'}
        
        values = time_series.values
        monthly_changes = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                change = (values[i] - values[i-1]) / values[i-1]
                monthly_changes.append(change)
        
        avg_monthly_growth = np.mean(monthly_changes) if monthly_changes else 0
        volatility = np.std(monthly_changes) if monthly_changes else 0
        
        if avg_monthly_growth > 0.05:
            trend = 'growing'
        elif avg_monthly_growth < -0.05:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'monthly_growth': avg_monthly_growth,
            'annual_growth': avg_monthly_growth * 12,
            'volatility': volatility,
            'trend': trend
        }
    
    def _project_costs(self, 
                         current_monthly_cost: float,
                         growth_rate: float,
                         volatility: float,
                         months: int = 12) -> pd.DataFrame:
        projections = []
        base_date = pd.Timestamp.now().replace(day=1)
        
        for month in range(months):
            projected_date = base_date + pd.DateOffset(months=month)
            growth_factor = (1 + growth_rate) ** month
            volatility_factor = np.random.normal(0, volatility / 2) if month > 0 else 0
            
            projected_cost = current_monthly_cost * growth_factor * (1 + volatility_factor)
            lower_bound = projected_cost * (1 - volatility * 2)
            upper_bound = projected_cost * (1 + volatility * 2)
            
            projections.append({
                'date': projected_date,
                'projected_cost': max(0, projected_cost),
                'lower_bound': max(0, lower_bound),
                'upper_bound': max(0, upper_bound),
                'cumulative_cost': 0
            })
        
        df = pd.DataFrame(projections)
        df['cumulative_cost'] = df['projected_cost'].cumsum()
        return df
    
    def _identify_key_drivers(self, cost_data: pd.DataFrame) -> List[Dict]:
        if cost_data is None or cost_data.empty:
            return []
        
        recent_month = cost_data[cost_data['date'] >= (pd.Timestamp.now() - pd.DateOffset(days=30))]
        previous_month = cost_data[(cost_data['date'] >= (pd.Timestamp.now() - pd.DateOffset(days=60))) & 
                                    (cost_data['date'] < (pd.Timestamp.now() - pd.DateOffset(days=30)))]
        
        if recent_month.empty or previous_month.empty:
            return []
        
        recent_by_service = recent_month.groupby('service')['cost'].sum()
        previous_by_service = previous_month.groupby('service')['cost'].sum()
        
        drivers = []
        for service in recent_by_service.index:
            recent_cost = recent_by_service.get(service, 0)
            prev_cost = previous_by_service.get(service, 0)
            
            if prev_cost > 0:
                change_pct = (recent_cost - prev_cost) / prev_cost
            else:
                change_pct = 1.0 if recent_cost > 0 else 0
            
            total_recent = recent_by_service.sum()
            contribution_pct = recent_cost / total_recent if total_recent > 0 else 0
            
            if abs(change_pct) > 0.1 or contribution_pct > 0.1:
                drivers.append({
                    'service': service,
                    'current_cost': recent_cost,
                    'previous_cost': prev_cost,
                    'change_pct': change_pct,
                    'contribution_pct': contribution_pct,
                    'impact': 'high' if abs(change_pct) > 0.3 or contribution_pct > 0.2 else 'medium'
                })
        
        drivers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        return drivers[:5]
    
    def _generate_mitigation_recommendations(self, 
                                               risk_level: str,
                                               key_drivers: List[Dict],
                                               projected_overrun: float) -> List[str]:
        recommendations = []
        
        if projected_overrun > 0:
            recommendations.append(f"Projected overrun of ${projected_overrun:,.2f} requires immediate attention")
        
        if risk_level in ['critical', 'high']:
            recommendations.append("Implement cost containment measures immediately")
            recommendations.append("Consider emergency budget review and approval for additional funds")
        
        for driver in key_drivers:
            if driver['change_pct'] > 0.2:
                recommendations.append(f"Investigate {driver['service']} cost increase of {driver['change_pct']:.1%}")
            elif driver['change_pct'] < -0.1:
                recommendations.append(f"Monitor {driver['service']} cost decrease trend")
        
        if not recommendations:
            recommendations.append("Continue regular cost monitoring")
            recommendations.append("Review optimization recommendations for additional savings")
        
        return recommendations
    
    def _calculate_risk_score(self, 
                                budget_amount: float,
                                projected_cost: float,
                                historical_volatility: float,
                                growth_rate: float) -> float:
        if budget_amount <= 0:
            return 1.0
        
        variance_ratio = projected_cost / budget_amount
        volatility_factor = min(1.0, historical_volatility * 5)
        growth_factor = min(1.0, max(0, growth_rate * 5))
        
        risk_score = (variance_ratio - 1) * 0.6 + volatility_factor * 0.25 + growth_factor * 0.15
        return max(0.0, min(1.0, risk_score + 0.5 if variance_ratio > 1 else risk_score))
    
    def forecast_budget(self, 
                          budget_amount: float = None,
                          forecast_months: int = 12,
                          scenario: str = 'moderate') -> BudgetForecast:
        if self.historical_costs is None or self.historical_costs.empty:
            raise ValueError("No historical cost data available for forecasting")
        
        monthly_totals = self._calculate_monthly_totals(self.historical_costs)
        
        if monthly_totals.empty:
            raise ValueError("Insufficient data for forecasting")
        
        growth_analysis = self._calculate_growth_rate(monthly_totals)
        
        current_monthly_cost = monthly_totals.iloc[-1]
        
        scenario_growth = self.GROWTH_SCENARIOS.get(scenario, self.GROWTH_SCENARIOS['moderate'])
        applied_growth = (growth_analysis['monthly_growth'] + scenario_growth) / 2
        
        monthly_forecast = self._project_costs(
            current_monthly_cost=current_monthly_cost,
            growth_rate=applied_growth,
            volatility=growth_analysis['volatility'],
            months=forecast_months
        )
        
        projected_cost = monthly_forecast['projected_cost'].sum()
        
        if budget_amount is None:
            budget_amount = projected_cost
        
        budget_variance = projected_cost - budget_amount
        budget_variance_pct = (budget_variance / budget_amount) if budget_amount > 0 else 0
        
        risk_score = self._calculate_risk_score(
            budget_amount=budget_amount,
            projected_cost=projected_cost,
            historical_volatility=growth_analysis['volatility'],
            growth_rate=applied_growth
        )
        
        if risk_score >= 0.8:
            risk_level = 'Critical'
        elif risk_score >= 0.5:
            risk_level = 'High'
        elif risk_score >= 0.2:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        key_drivers = self._identify_key_drivers(self.historical_costs)
        mitigation_recommendations = self._generate_mitigation_recommendations(
            risk_level=risk_level.lower(),
            key_drivers=key_drivers,
            projected_overrun=budget_variance
        )
        
        return BudgetForecast(
            forecast_period=f"{forecast_months} months",
            forecast_start_date=monthly_forecast['date'].iloc[0],
            forecast_end_date=monthly_forecast['date'].iloc[-1],
            projected_cost=projected_cost,
            budget_amount=budget_amount,
            budget_variance=budget_variance,
            budget_variance_pct=budget_variance_pct,
            over_budget_risk=risk_score,
            risk_level=risk_level,
            monthly_forecast=monthly_forecast,
            key_drivers=key_drivers,
            mitigation_recommendations=mitigation_recommendations
        )
    
    def multi_scenario_forecast(self, 
                                  budget_amount: float = None,
                                  forecast_months: int = 12) -> Dict[str, BudgetForecast]:
        scenarios = {}
        for scenario_name in self.GROWTH_SCENARIOS.keys():
            scenarios[scenario_name] = self.forecast_budget(
                budget_amount=budget_amount,
                forecast_months=forecast_months,
                scenario=scenario_name
            )
        return scenarios
    
    def get_budget_alert_thresholds(self, monthly_budget: float) -> Dict:
        return {
            'warning_75': monthly_budget * 0.75,
            'alert_90': monthly_budget * 0.90,
            'critical_100': monthly_budget * 1.0,
            'overage_110': monthly_budget * 1.1
        }
