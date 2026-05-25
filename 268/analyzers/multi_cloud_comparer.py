import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from enum import Enum


class CloudProvider(Enum):
    ALIYUN = "aliyun"
    AWS = "aws"
    TENCENT = "tencent"
    HUAWEI = "huawei"
    AZURE = "azure"


CLOUD_PRICING_DATA = {
    'general_purpose': {
        '1vCPU_2GB': {
            'aliyun': {'monthly': 60, 'instance_type': 'ecs.t5-lc1m2.small'},
            'aws': {'monthly': 55, 'instance_type': 't3.small'},
            'tencent': {'monthly': 58, 'instance_type': 'S5.SMALL2'},
            'huawei': {'monthly': 56, 'instance_type': 's6.small.1'},
            'azure': {'monthly': 62, 'instance_type': 'B1s'}
        },
        '2vCPU_4GB': {
            'aliyun': {'monthly': 120, 'instance_type': 'ecs.t5-lc1m2.large'},
            'aws': {'monthly': 110, 'instance_type': 't3.medium'},
            'tencent': {'monthly': 116, 'instance_type': 'S5.MEDIUM4'},
            'huawei': {'monthly': 112, 'instance_type': 's6.medium.2'},
            'azure': {'monthly': 124, 'instance_type': 'B2s'}
        },
        '4vCPU_8GB': {
            'aliyun': {'monthly': 240, 'instance_type': 'ecs.t5-c1m2.xlarge'},
            'aws': {'monthly': 220, 'instance_type': 't3.xlarge'},
            'tencent': {'monthly': 232, 'instance_type': 'S5.LARGE8'},
            'huawei': {'monthly': 224, 'instance_type': 's6.large.4'},
            'azure': {'monthly': 248, 'instance_type': 'B4ms'}
        },
        '2vCPU_8GB': {
            'aliyun': {'monthly': 280, 'instance_type': 'ecs.g6.large'},
            'aws': {'monthly': 255, 'instance_type': 'r5.large'},
            'tencent': {'monthly': 268, 'instance_type': 'M5.LARGE8'},
            'huawei': {'monthly': 260, 'instance_type': 'c6.large.4'},
            'azure': {'monthly': 290, 'instance_type': 'E2s v5'}
        },
        '4vCPU_16GB': {
            'aliyun': {'monthly': 560, 'instance_type': 'ecs.g6.xlarge'},
            'aws': {'monthly': 510, 'instance_type': 'r5.xlarge'},
            'tencent': {'monthly': 536, 'instance_type': 'M5.XLARGE16'},
            'huawei': {'monthly': 520, 'instance_type': 'c6.xlarge.4'},
            'azure': {'monthly': 580, 'instance_type': 'E4s v5'}
        },
        '8vCPU_32GB': {
            'aliyun': {'monthly': 1120, 'instance_type': 'ecs.g6.2xlarge'},
            'aws': {'monthly': 1020, 'instance_type': 'r5.2xlarge'},
            'tencent': {'monthly': 1072, 'instance_type': 'M5.2XLARGE32'},
            'huawei': {'monthly': 1040, 'instance_type': 'c6.2xlarge.4'},
            'azure': {'monthly': 1160, 'instance_type': 'E8s v5'}
        }
    },
    'compute_optimized': {
        '2vCPU_4GB': {
            'aliyun': {'monthly': 200, 'instance_type': 'ecs.c6.large'},
            'aws': {'monthly': 180, 'instance_type': 'c5.large'},
            'tencent': {'monthly': 192, 'instance_type': 'C5.LARGE4'},
            'huawei': {'monthly': 185, 'instance_type': 'c3.large.2'},
            'azure': {'monthly': 210, 'instance_type': 'F2s v2'}
        },
        '4vCPU_8GB': {
            'aliyun': {'monthly': 400, 'instance_type': 'ecs.c6.xlarge'},
            'aws': {'monthly': 360, 'instance_type': 'c5.xlarge'},
            'tencent': {'monthly': 384, 'instance_type': 'C5.XLARGE8'},
            'huawei': {'monthly': 370, 'instance_type': 'c3.xlarge.2'},
            'azure': {'monthly': 420, 'instance_type': 'F4s v2'}
        },
        '8vCPU_16GB': {
            'aliyun': {'monthly': 800, 'instance_type': 'ecs.c6.2xlarge'},
            'aws': {'monthly': 720, 'instance_type': 'c5.2xlarge'},
            'tencent': {'monthly': 768, 'instance_type': 'C5.2XLARGE16'},
            'huawei': {'monthly': 740, 'instance_type': 'c3.2xlarge.2'},
            'azure': {'monthly': 840, 'instance_type': 'F8s v2'}
        }
    },
    'memory_optimized': {
        '2vCPU_16GB': {
            'aliyun': {'monthly': 320, 'instance_type': 'ecs.r6.large'},
            'aws': {'monthly': 290, 'instance_type': 'r5.large'},
            'tencent': {'monthly': 305, 'instance_type': 'R5.LARGE16'},
            'huawei': {'monthly': 298, 'instance_type': 'm6.large.8'},
            'azure': {'monthly': 330, 'instance_type': 'E2s v5'}
        },
        '4vCPU_32GB': {
            'aliyun': {'monthly': 640, 'instance_type': 'ecs.r6.xlarge'},
            'aws': {'monthly': 580, 'instance_type': 'r5.xlarge'},
            'tencent': {'monthly': 610, 'instance_type': 'R5.XLARGE32'},
            'huawei': {'monthly': 596, 'instance_type': 'm6.xlarge.8'},
            'azure': {'monthly': 660, 'instance_type': 'E4s v5'}
        },
        '8vCPU_64GB': {
            'aliyun': {'monthly': 1280, 'instance_type': 'ecs.r6.2xlarge'},
            'aws': {'monthly': 1160, 'instance_type': 'r5.2xlarge'},
            'tencent': {'monthly': 1220, 'instance_type': 'R5.2XLARGE64'},
            'huawei': {'monthly': 1192, 'instance_type': 'm6.2xlarge.8'},
            'azure': {'monthly': 1320, 'instance_type': 'E8s v5'}
        }
    }
}


MIGRATION_COMPLEXITY = {
    'low': {
        'score': 1,
        'time_weeks': 1,
        'description': 'Stateless web/app servers, CI/CD runners'
    },
    'medium': {
        'score': 2,
        'time_weeks': 2,
        'description': 'Application servers with configuration, batch processing'
    },
    'high': {
        'score': 3,
        'time_weeks': 4,
        'description': 'Stateful services, databases, specialized workloads'
    }
}


class MultiCloudComparer:
    def __init__(self, config: Dict):
        self.config = config
        self.compare_config = config.get('multi_cloud', {})
        self.min_savings_threshold = self.compare_config.get('min_savings_threshold', 0.1)
        self.max_migration_risk = self.compare_config.get('max_migration_risk', 0.5)
        self.include_hidden_costs = self.compare_config.get('include_hidden_costs', True)
        
        self.pricing_data = CLOUD_PRICING_DATA

    def get_instance_family(self, instance_type: str) -> str:
        itype = instance_type.lower()
        
        if 't5' in itype or 't3' in itype or 's5' in itype or 's6' in itype or 'b1' in itype:
            return 'general_purpose'
        elif 'c6' in itype or 'c5' in itype or 'c3' in itype or 'f2' in itype:
            return 'compute_optimized'
        elif 'r6' in itype or 'r5' in itype or 'm6' in itype or 'e2' in itype:
            return 'memory_optimized'
        elif 'g6' in itype or 'm5' in itype:
            return 'general_purpose'
        
        return 'general_purpose'

    def get_size_key(self, vcpu: int, memory: float) -> str:
        combinations = [
            (1, 2, '1vCPU_2GB'),
            (2, 4, '2vCPU_4GB'),
            (4, 8, '4vCPU_8GB'),
            (2, 8, '2vCPU_8GB'),
            (4, 16, '4vCPU_16GB'),
            (8, 32, '8vCPU_32GB'),
            (2, 16, '2vCPU_16GB'),
            (4, 32, '4vCPU_32GB'),
            (8, 64, '8vCPU_64GB'),
            (2, 4, '2vCPU_4GB'),
            (4, 8, '4vCPU_8GB'),
            (8, 16, '8vCPU_16GB'),
        ]
        
        for target_vcpu, target_mem, key in combinations:
            if vcpu <= target_vcpu and memory <= target_mem:
                return key
        
        return '4vCPU_8GB'

    def estimate_migration_complexity(self, instance_data: pd.Series, 
                                       workload_type: str = 'unknown') -> Dict:
        instance_name = str(instance_data.get('instance_name', '')).lower()
        
        stateful_keywords = ['db', 'mysql', 'postgres', 'redis', 'mongo', 
                            'kafka', 'zookeeper', 'etcd', 'elastic', 'es-',
                            'storage', 'data']
        
        if any(k in instance_name for k in stateful_keywords):
            return MIGRATION_COMPLEXITY['high']
        
        app_keywords = ['web', 'app', 'api', 'nginx', 'apache']
        if any(k in instance_name for k in app_keywords):
            return MIGRATION_COMPLEXITY['medium']
        
        stateless_keywords = ['worker', 'batch', 'job', 'runner', 'ci', 'build']
        if any(k in instance_name for k in stateless_keywords):
            return MIGRATION_COMPLEXITY['low']
        
        if workload_type in ['batch', 'ci_cd', 'dev_test']:
            return MIGRATION_COMPLEXITY['low']
        elif workload_type in ['web']:
            return MIGRATION_COMPLEXITY['medium']
        elif workload_type in ['database', 'stateful']:
            return MIGRATION_COMPLEXITY['high']
        
        return MIGRATION_COMPLEXITY['medium']

    def calculate_hidden_costs(self, current_provider: str, 
                                target_provider: str,
                                complexity: Dict) -> float:
        if not self.include_hidden_costs:
            return 0
        
        egress_costs = {
            ('aliyun', 'aws'): 100,
            ('aliyun', 'tencent'): 50,
            ('aws', 'aliyun'): 120,
            ('aws', 'tencent'): 100,
            ('tencent', 'aliyun'): 60,
            ('tencent', 'aws'): 80,
        }
        
        data_egress = egress_costs.get((current_provider, target_provider), 80)
        
        labor_cost = complexity['time_weeks'] * 500
        
        risk_premium = complexity['score'] * 100
        
        total_hidden = data_egress + labor_cost + risk_premium
        
        return total_hidden

    def compare_instance_pricing(self, instance_data: pd.Series, 
                                  instance_spec: Dict,
                                  workload_type: str = 'unknown') -> pd.DataFrame:
        current_provider = instance_data.get('provider', 'aliyun')
        vcpu = instance_data.get('cpu', instance_spec.get('vcpu', 2))
        memory = instance_data.get('memory', instance_spec.get('memory_gb', 4)) / 1024 if instance_data.get('memory', 0) > 100 else instance_data.get('memory', 4)
        
        family = self.get_instance_family(instance_data.get('instance_type', ''))
        size_key = self.get_size_key(vcpu, memory)
        
        if family not in self.pricing_data:
            family = 'general_purpose'
        
        family_pricing = self.pricing_data.get(family, {})
        size_pricing = family_pricing.get(size_key, {})
        
        if not size_pricing:
            return pd.DataFrame()

        comparisons = []
        current_price = size_pricing.get(current_provider, {}).get('monthly', 0)
        
        migration_complexity = self.estimate_migration_complexity(instance_data, workload_type)
        
        for provider, pricing in size_pricing.items():
            if provider == current_provider:
                continue
                
            target_price = pricing.get('monthly', 0)
            savings = current_price - target_price
            savings_pct = (savings / current_price * 100) if current_price > 0 else 0
            
            hidden_costs = self.calculate_hidden_costs(current_provider, provider, migration_complexity)
            net_savings = savings - hidden_costs / 12
            
            payback_months = hidden_costs / savings if savings > 0 else float('inf')
            
            risk_score = migration_complexity['score'] * 0.3 + (1 - savings_pct / 100) * 0.7
            
            recommended = (
                savings_pct >= self.min_savings_threshold * 100 and
                risk_score <= self.max_migration_risk * 2 and
                payback_months <= 6
            )
            
            comparisons.append({
                'instance_id': instance_data.get('instance_id', ''),
                'instance_name': instance_data.get('instance_name', ''),
                'current_provider': current_provider,
                'target_provider': provider,
                'instance_family': family,
                'instance_size': size_key,
                'current_monthly_cost': round(current_price, 2),
                'target_monthly_cost': round(target_price, 2),
                'monthly_savings': round(savings, 2),
                'savings_percent': round(savings_pct, 1),
                'hidden_costs_annual': round(hidden_costs, 2),
                'net_monthly_savings': round(net_savings, 2),
                'payback_months': round(payback_months, 1),
                'migration_complexity': migration_complexity['score'],
                'migration_time_weeks': migration_complexity['time_weeks'],
                'migration_description': migration_complexity['description'],
                'risk_score': round(risk_score, 2),
                'target_instance_type': pricing.get('instance_type', ''),
                'migration_recommended': recommended and net_savings > 0
            })

        return pd.DataFrame(comparisons)

    def analyze_portfolio(self, instances_df: pd.DataFrame,
                           analysis_df: pd.DataFrame,
                           workload_types: Dict = None) -> Dict:
        if instances_df.empty:
            return {
                'total_instances': 0,
                'migration_candidates': [],
                'total_savings': 0,
                'provider_summary': {},
                'recommendations': pd.DataFrame()
            }

        all_comparisons = []
        workload_types = workload_types or {}

        for _, instance in instances_df.iterrows():
            if instance.get('status') != 'Running':
                continue

            instance_id = instance['instance_id']
            workload_type = workload_types.get(instance_id, 'unknown')
            
            from .resource_packer import InstanceSpec
            from .cost_optimizer import INSTANCE_PRICING
            
            instance_type = instance.get('instance_type', '')
            pricing = INSTANCE_PRICING.get(instance_type, {})
            spec = {
                'vcpu': pricing.get('cpu', 2),
                'memory_gb': pricing.get('mem', 4)
            }
            
            comparisons = self.compare_instance_pricing(
                instance, spec, workload_type
            )
            
            if not comparisons.empty:
                all_comparisons.append(comparisons)

        if not all_comparisons:
            return {
                'total_instances': len(instances_df),
                'migration_candidates': [],
                'total_savings': 0,
                'provider_summary': {},
                'recommendations': pd.DataFrame()
            }

        all_comparisons_df = pd.concat(all_comparisons, ignore_index=True)
        
        recommended = all_comparisons_df[all_comparisons_df['migration_recommended']]
        
        provider_summary = {}
        for provider in all_comparisons_df['target_provider'].unique():
            provider_recs = recommended[recommended['target_provider'] == provider]
            provider_summary[provider] = {
                'candidate_count': len(provider_recs),
                'total_monthly_savings': round(provider_recs['monthly_savings'].sum(), 2),
                'avg_savings_percent': round(provider_recs['savings_percent'].mean(), 1) if len(provider_recs) > 0 else 0
            }

        best_options = all_comparisons_df.sort_values('net_monthly_savings', ascending=False)
        best_options = best_options.drop_duplicates(subset=['instance_id'], keep='first')

        return {
            'total_instances': len(instances_df[instances_df['status'] == 'Running']),
            'migration_candidate_count': len(recommended['instance_id'].unique()),
            'total_monthly_savings': round(recommended['monthly_savings'].sum(), 2),
            'total_net_savings': round(recommended['net_monthly_savings'].sum(), 2),
            'provider_summary': provider_summary,
            'recommendations': recommended,
            'best_migration_options': best_options,
            'all_comparisons': all_comparisons_df
        }

    def get_migration_plan(self, portfolio_analysis: Dict, 
                            target_provider: str = None) -> Dict:
        recs = portfolio_analysis.get('recommendations', pd.DataFrame())
        
        if recs.empty:
            return {'plan': [], 'total_savings': 0}

        if target_provider:
            recs = recs[recs['target_provider'] == target_provider]

        recs_sorted = recs.sort_values(['migration_complexity', 'savings_percent'], 
                                       ascending=[True, False])

        phases = {
            'phase1_easy': recs_sorted[recs_sorted['migration_complexity'] == 1].to_dict('records'),
            'phase2_medium': recs_sorted[recs_sorted['migration_complexity'] == 2].to_dict('records'),
            'phase3_complex': recs_sorted[recs_sorted['migration_complexity'] == 3].to_dict('records')
        }

        return {
            'phases': phases,
            'total_savings': round(recs_sorted['monthly_savings'].sum(), 2),
            'estimated_time_weeks': {
                'phase1': max([r['migration_time_weeks'] for r in phases['phase1_easy']]) if phases['phase1_easy'] else 0,
                'phase2': max([r['migration_time_weeks'] for r in phases['phase2_medium']]) if phases['phase2_medium'] else 0,
                'phase3': max([r['migration_time_weeks'] for r in phases['phase3_complex']]) if phases['phase3_complex'] else 0
            }
        }
