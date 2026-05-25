import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from itertools import combinations
from dataclasses import dataclass
import math


@dataclass
class InstanceSpec:
    instance_type: str
    vcpu: int
    memory_gb: float
    monthly_cost: float
    provider: str = 'aliyun'

    def cost_per_vcpu(self) -> float:
        return self.monthly_cost / self.vcpu if self.vcpu > 0 else float('inf')

    def cost_per_gb(self) -> float:
        return self.monthly_cost / self.memory_gb if self.memory_gb > 0 else float('inf')


INSTANCE_SPECS = [
    InstanceSpec('ecs.t5-lc1m2.small', 1, 2, 60, 'aliyun'),
    InstanceSpec('ecs.t5-lc1m2.large', 2, 4, 120, 'aliyun'),
    InstanceSpec('ecs.t5-c1m2.xlarge', 4, 8, 240, 'aliyun'),
    InstanceSpec('ecs.g6.large', 2, 8, 280, 'aliyun'),
    InstanceSpec('ecs.g6.xlarge', 4, 16, 560, 'aliyun'),
    InstanceSpec('ecs.g6.2xlarge', 8, 32, 1120, 'aliyun'),
    InstanceSpec('ecs.g6.4xlarge', 16, 64, 2240, 'aliyun'),
    InstanceSpec('ecs.c6.large', 2, 4, 200, 'aliyun'),
    InstanceSpec('ecs.c6.xlarge', 4, 8, 400, 'aliyun'),
    InstanceSpec('ecs.c6.2xlarge', 8, 16, 800, 'aliyun'),
    InstanceSpec('ecs.c6.4xlarge', 16, 32, 1600, 'aliyun'),
    InstanceSpec('ecs.r6.large', 2, 16, 320, 'aliyun'),
    InstanceSpec('ecs.r6.xlarge', 4, 32, 640, 'aliyun'),
    InstanceSpec('ecs.r6.2xlarge', 8, 64, 1280, 'aliyun'),
]


class ResourcePacker:
    def __init__(self, config: Dict):
        self.config = config
        self.packer_config = config.get('resource_packing', {})
        self.utilization_headroom = self.packer_config.get('utilization_headroom', 0.3)
        self.min_savings_threshold = self.packer_config.get('min_savings_threshold', 0.1)
        self.min_instances_to_merge = self.packer_config.get('min_instances_to_merge', 2)
        self.max_vcpu_per_bin = self.packer_config.get('max_vcpu_per_bin', 64)
        
        self.specs = {s.instance_type: s for s in INSTANCE_SPECS}

    def get_instance_spec(self, instance_type: str) -> InstanceSpec:
        if instance_type in self.specs:
            return self.specs[instance_type]
        
        if 'large' in instance_type:
            vcpu = 2
        elif 'xlarge' in instance_type:
            vcpu = 4
        elif '2xlarge' in instance_type:
            vcpu = 8
        elif '4xlarge' in instance_type:
            vcpu = 16
        else:
            vcpu = 1
        
        memory = vcpu * 4
        cost = vcpu * 80
        
        return InstanceSpec(instance_type, vcpu, memory, cost)

    def calculate_merged_requirements(self, instances: pd.DataFrame, 
                                       analysis_df: pd.DataFrame) -> Dict:
        total_vcpu = 0
        total_memory = 0
        total_cost = 0
        instance_specs = []

        for _, instance in instances.iterrows():
            instance_id = instance['instance_id']
            spec = self.get_instance_spec(instance['instance_type'])
            
            instance_analysis = analysis_df[analysis_df['instance_id'] == instance_id]
            if not instance_analysis.empty:
                cpu_util = instance_analysis.iloc[0].get('cpu_avg', 50) / 100
                mem_util = instance_analysis.iloc[0].get('memory_avg', 50) / 100
            else:
                cpu_util = 0.5
                mem_util = 0.5

            required_vcpu = spec.vcpu * cpu_util * (1 + self.utilization_headroom)
            required_memory = spec.memory_gb * mem_util * (1 + self.utilization_headroom)

            total_vcpu += required_vcpu
            total_memory += required_memory
            total_cost += spec.monthly_cost
            
            instance_specs.append({
                'instance_id': instance_id,
                'instance_name': instance.get('instance_name', ''),
                'spec': spec,
                'cpu_util': cpu_util,
                'mem_util': mem_util
            })

        return {
            'total_vcpu': total_vcpu,
            'total_memory': total_memory,
            'total_cost': total_cost,
            'instance_count': len(instances),
            'instance_specs': instance_specs
        }

    def find_optimal_instance_type(self, required_vcpu: float, 
                                    required_memory: float) -> Tuple[InstanceSpec, Dict]:
        target_vcpu = math.ceil(required_vcpu)
        target_memory = math.ceil(required_memory)
        
        candidates = []
        for spec in self.specs.values():
            if spec.vcpu >= target_vcpu and spec.memory_gb >= target_memory:
                if spec.vcpu <= self.max_vcpu_per_bin:
                    candidates.append(spec)
        
        if not candidates:
            candidates = list(self.specs.values())
            candidates.sort(key=lambda s: (
                max(0, target_vcpu - s.vcpu) * 1000 + 
                max(0, target_memory - s.memory_gb) * 100 +
                s.monthly_cost
            ))
            return candidates[0] if candidates else self.specs.get('ecs.g6.2xlarge')
        
        candidates.sort(key=lambda s: s.monthly_cost)
        optimal = candidates[0]
        
        waste_vcpu = optimal.vcpu - required_vcpu
        waste_memory = optimal.memory_gb - required_memory
        
        return optimal, {
            'waste_vcpu': waste_vcpu,
            'waste_memory': waste_memory,
            'vcpu_utilization': required_vcpu / optimal.vcpu if optimal.vcpu > 0 else 0,
            'memory_utilization': required_memory / optimal.memory_gb if optimal.memory_gb > 0 else 0
        }

    def pack_instances_first_fit(self, instances: pd.DataFrame, 
                                  analysis_df: pd.DataFrame) -> List[Dict]:
        if len(instances) < self.min_instances_to_merge:
            return []

        bins = []
        
        for _, instance in instances.iterrows():
            instance_id = instance['instance_id']
            spec = self.get_instance_spec(instance['instance_type'])
            
            instance_analysis = analysis_df[analysis_df['instance_id'] == instance_id]
            if not instance_analysis.empty:
                cpu_util = instance_analysis.iloc[0].get('cpu_avg', 50) / 100
                mem_util = instance_analysis.iloc[0].get('memory_avg', 50) / 100
            else:
                cpu_util = 0.5
                mem_util = 0.5

            req_vcpu = spec.vcpu * cpu_util * (1 + self.utilization_headroom)
            req_memory = spec.memory_gb * mem_util * (1 + self.utilization_headroom)

            placed = False
            for bin_info in bins:
                new_vcpu = bin_info['used_vcpu'] + req_vcpu
                new_memory = bin_info['used_memory'] + req_memory
                bin_spec = bin_info['target_spec']
                
                if new_vcpu <= bin_spec.vcpu and new_memory <= bin_spec.memory_gb:
                    bin_info['used_vcpu'] = new_vcpu
                    bin_info['used_memory'] = new_memory
                    bin_info['instances'].append({
                        'instance_id': instance_id,
                        'instance_name': instance.get('instance_name', ''),
                        'instance_type': instance['instance_type'],
                        'req_vcpu': req_vcpu,
                        'req_memory': req_memory
                    })
                    bin_info['original_cost'] += spec.monthly_cost
                    placed = True
                    break

            if not placed:
                optimal_spec, _ = self.find_optimal_instance_type(req_vcpu, req_memory)
                bins.append({
                    'bin_id': f'bin-{len(bins)+1}',
                    'target_spec': optimal_spec,
                    'used_vcpu': req_vcpu,
                    'used_memory': req_memory,
                    'instances': [{
                        'instance_id': instance_id,
                        'instance_name': instance.get('instance_name', ''),
                        'instance_type': instance['instance_type'],
                        'req_vcpu': req_vcpu,
                        'req_memory': req_memory
                    }],
                    'original_cost': spec.monthly_cost
                })

        return self._generate_bins_report(bins)

    def _generate_bins_report(self, bins: List[Dict]) -> List[Dict]:
        report = []
        
        for bin_info in bins:
            if len(bin_info['instances']) < self.min_instances_to_merge:
                continue
                
            target_spec = bin_info['target_spec']
            original_cost = bin_info['original_cost']
            new_cost = target_spec.monthly_cost
            savings = original_cost - new_cost
            savings_pct = (savings / original_cost * 100) if original_cost > 0 else 0

            if savings_pct < self.min_savings_threshold * 100:
                continue

            report.append({
                'bin_id': bin_info['bin_id'],
                'target_instance_type': target_spec.instance_type,
                'target_vcpu': target_spec.vcpu,
                'target_memory_gb': target_spec.memory_gb,
                'instances_count': len(bin_info['instances']),
                'instances': bin_info['instances'],
                'original_monthly_cost': round(original_cost, 2),
                'new_monthly_cost': round(new_cost, 2),
                'monthly_savings': round(savings, 2),
                'savings_percent': round(savings_pct, 1),
                'vcpu_utilization': round(bin_info['used_vcpu'] / target_spec.vcpu * 100, 1),
                'memory_utilization': round(bin_info['used_memory'] / target_spec.memory_gb * 100, 1)
            })

        return report

    def optimize_by_family(self, instances_df: pd.DataFrame, 
                            analysis_df: pd.DataFrame) -> Dict:
        results = {
            'by_provider': {},
            'total_original_cost': 0,
            'total_optimized_cost': 0,
            'total_savings': 0,
            'recommendations': []
        }

        running_instances = instances_df[instances_df['status'] == 'Running']
        
        if running_instances.empty:
            return results

        providers = running_instances['provider'].unique()
        
        for provider in providers:
            provider_instances = running_instances[running_instances['provider'] == provider]
            
            bins = self.pack_instances_first_fit(provider_instances, analysis_df)
            
            provider_savings = sum(b['monthly_savings'] for b in bins)
            provider_original = sum(b['original_monthly_cost'] for b in bins)
            provider_new = sum(b['new_monthly_cost'] for b in bins)
            
            results['by_provider'][provider] = {
                'bins': bins,
                'bins_count': len(bins),
                'instances_merged': sum(b['instances_count'] for b in bins),
                'original_cost': provider_original,
                'optimized_cost': provider_new,
                'savings': provider_savings
            }
            
            results['recommendations'].extend(bins)
            results['total_original_cost'] += provider_original
            results['total_optimized_cost'] += provider_new
            results['total_savings'] += provider_savings

        results['total_savings_percent'] = round(
            (results['total_savings'] / results['total_original_cost'] * 100) 
            if results['total_original_cost'] > 0 else 0, 1
        )

        return results

    def get_packing_summary(self, packing_results: Dict) -> Dict:
        recs = packing_results.get('recommendations', [])
        
        total_instances = sum(b['instances_count'] for b in recs)
        total_bins = len(recs)
        
        return {
            'total_bins': total_bins,
            'instances_merged': total_instances,
            'consolidation_ratio': round(total_instances / total_bins, 2) if total_bins > 0 else 0,
            'total_monthly_savings': packing_results.get('total_savings', 0),
            'savings_percent': packing_results.get('total_savings_percent', 0),
            'by_provider': {
                p: {
                    'bins': len(v['bins']),
                    'instances': v['instances_merged'],
                    'savings': v['savings']
                }
                for p, v in packing_results.get('by_provider', {}).items()
            }
        }
