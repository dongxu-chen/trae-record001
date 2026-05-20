#!/usr/bin/env python3
"""
Terraform State 分析器
解析 tfstate 文件，提取资源信息并进行成本分析
"""
import json
import argparse
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ResourceCost:
    provider: str
    resource_type: str
    resource_name: str
    resource_address: str
    estimated_monthly_cost: float
    region: str
    tags: Dict[str, str]
    cost_components: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class TfstateAnalyzer:
    def __init__(self, state_file_path: str):
        self.state_file_path = state_file_path
        self.state_data = self._load_state()
        self.resources = []
        self.provider_mapping = {
            'aws': self._parse_aws_resource,
            'azurerm': self._parse_azure_resource,
            'google': self._parse_gcp_resource,
        }
        
        self.instance_type_prices = {
            'aws': self._get_aws_instance_prices(),
            'azure': self._get_azure_instance_prices(),
            'gcp': self._get_gcp_instance_prices(),
        }

    def _load_state(self) -> Dict:
        with open(self.state_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_resource_type(self, resource_type: str) -> str:
        if resource_type.startswith('aws_'):
            return 'aws'
        elif resource_type.startswith('azurerm_'):
            return 'azurerm'
        elif resource_type.startswith('google_'):
            return 'google'
        return 'unknown'

    def _parse_aws_resource(self, resource: Dict) -> ResourceCost:
        resource_type = resource['type']
        attributes = resource.get('instances', [{}])[0].get('attributes', {})
        region = attributes.get('region', 'us-east-1')
        tags = attributes.get('tags', {}) or {}
        
        estimated_cost = 0.0
        cost_components = []
        
        if resource_type == 'aws_instance':
            instance_type = attributes.get('instance_type', 't2.micro')
            estimated_cost, components = self._calculate_ec2_cost(instance_type, attributes)
            cost_components.extend(components)
            
        elif resource_type == 'aws_db_instance':
            instance_class = attributes.get('instance_class', 'db.t2.micro')
            storage_gb = attributes.get('allocated_storage', 20)
            estimated_cost, components = self._calculate_rds_cost(instance_class, storage_gb)
            cost_components.extend(components)
            
        elif resource_type == 'aws_s3_bucket':
            estimated_cost, components = self._calculate_s3_cost(attributes)
            cost_components.extend(components)
            
        elif resource_type == 'aws_lambda_function':
            memory_size = attributes.get('memory_size', 128)
            estimated_cost, components = self._calculate_lambda_cost(memory_size)
            cost_components.extend(components)
            
        elif resource_type == 'aws_eks_cluster':
            estimated_cost, components = self._calculate_eks_cost()
            cost_components.extend(components)
            
        elif resource_type == 'aws_ebs_volume':
            volume_type = attributes.get('volume_type', 'gp2')
            size_gb = attributes.get('size', 8)
            estimated_cost, components = self._calculate_ebs_cost(volume_type, size_gb)
            cost_components.extend(components)
            
        elif resource_type == 'aws_elasticache_cluster':
            node_type = attributes.get('node_type', 'cache.t2.micro')
            num_nodes = attributes.get('num_cache_nodes', 1)
            estimated_cost, components = self._calculate_elasticache_cost(node_type, num_nodes)
            cost_components.extend(components)
            
        else:
            estimated_cost, components = self._estimate_generic_cost(resource_type, attributes)
            cost_components.extend(components)

        return ResourceCost(
            provider='aws',
            resource_type=resource_type,
            resource_name=resource['name'],
            resource_address=f"{resource['type']}.{resource['name']}",
            estimated_monthly_cost=estimated_cost,
            region=region,
            tags=tags,
            cost_components=cost_components,
            metadata={'attributes': {k: v for k, v in attributes.items() 
                    if k in ['instance_type', 'instance_class', 'engine', 'size']}}
        )

    def _parse_azure_resource(self, resource: Dict) -> ResourceCost:
        resource_type = resource['type']
        attributes = resource.get('instances', [{}])[0].get('attributes', {})
        location = attributes.get('location', 'eastus')
        tags = attributes.get('tags', {}) or {}
        
        estimated_cost = 0.0
        cost_components = []
        
        if resource_type == 'azurerm_linux_virtual_machine' or \
           resource_type == 'azurerm_windows_virtual_machine':
            vm_size = attributes.get('vm_size', 'Standard_B1s')
            estimated_cost, components = self._calculate_azure_vm_cost(vm_size, attributes)
            cost_components.extend(components)
            
        elif resource_type == 'azurerm_storage_account':
            account_tier = attributes.get('account_tier', 'Standard')
            estimated_cost, components = self._calculate_azure_storage_cost(account_tier)
            cost_components.extend(components)
            
        elif resource_type == 'azurerm_kubernetes_cluster':
            estimated_cost, components = self._calculate_aks_cost()
            cost_components.extend(components)
            
        else:
            estimated_cost, components = self._estimate_generic_cost(resource_type, attributes)
            cost_components.extend(components)

        return ResourceCost(
            provider='azure',
            resource_type=resource_type,
            resource_name=resource['name'],
            resource_address=f"{resource['type']}.{resource['name']}",
            estimated_monthly_cost=estimated_cost,
            region=location,
            tags=tags,
            cost_components=cost_components,
            metadata={'attributes': {k: v for k, v in attributes.items() 
                    if k in ['vm_size', 'sku_name', 'account_tier']}}
        )

    def _parse_gcp_resource(self, resource: Dict) -> ResourceCost:
        resource_type = resource['type']
        attributes = resource.get('instances', [{}])[0].get('attributes', {})
        region = attributes.get('region', 'us-central1')
        labels = attributes.get('labels', {}) or {}
        
        estimated_cost = 0.0
        cost_components = []
        
        if resource_type == 'google_compute_instance':
            machine_type = attributes.get('machine_type', 'n1-standard-1')
            estimated_cost, components = self._calculate_gcp_vm_cost(machine_type, attributes)
            cost_components.extend(components)
            
        elif resource_type == 'google_storage_bucket':
            estimated_cost, components = self._calculate_gcp_storage_cost()
            cost_components.extend(components)
            
        elif resource_type == 'google_container_cluster':
            estimated_cost, components = self._calculate_gke_cost()
            cost_components.extend(components)
            
        else:
            estimated_cost, components = self._estimate_generic_cost(resource_type, attributes)
            cost_components.extend(components)

        return ResourceCost(
            provider='gcp',
            resource_type=resource_type,
            resource_name=resource['name'],
            resource_address=f"{resource['type']}.{resource['name']}",
            estimated_monthly_cost=estimated_cost,
            region=region,
            tags=labels,
            cost_components=cost_components,
            metadata={'attributes': {k: v for k, v in attributes.items() 
                    if k in ['machine_type', 'database_version', 'storage_class']}}
        )

    def _calculate_ec2_cost(self, instance_type: str, attributes: Dict) -> tuple[float, List[Dict]]:
        base_prices = {
            't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
            't3a.micro': 0.0094, 't3a.small': 0.0188, 't3a.medium': 0.0376,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
        }
        hourly_rate = base_prices.get(instance_type, 0.05)
        monthly_compute = hourly_rate * 730
        
        root_disk_size = attributes.get('root_block_device', [{}])[0].get('volume_size', 8)
        ebs_monthly = root_disk_size * 0.10
        
        total_cost = monthly_compute + ebs_monthly
        
        components = [
            {'name': 'Compute', 'cost': monthly_compute, 'unit': 'monthly'},
            {'name': 'Root EBS', 'cost': ebs_monthly, 'unit': 'monthly'},
        ]
        
        return total_cost, components

    def _calculate_rds_cost(self, instance_class: str, storage_gb: int) -> tuple[float, List[Dict]]:
        base_prices = {
            'db.t2.micro': 0.017, 'db.t2.small': 0.034, 'db.t2.medium': 0.068,
            'db.t3.micro': 0.016, 'db.t3.small': 0.032, 'db.t3.medium': 0.064,
        }
        instance_type = instance_class.replace('db.', '')
        hourly_rate = base_prices.get(instance_class, 0.10)
        monthly_compute = hourly_rate * 730
        storage_monthly = storage_gb * 0.115
        
        total_cost = monthly_compute + storage_monthly
        
        components = [
            {'name': 'Compute', 'cost': monthly_compute, 'unit': 'monthly'},
            {'name': 'Storage', 'cost': storage_monthly, 'unit': 'monthly'},
        ]
        
        return total_cost, components

    def _calculate_s3_cost(self, attributes: Dict) -> tuple[float, List[Dict]]:
        storage_gb = 50
        storage_monthly = storage_gb * 0.023
        request_monthly = 1.0
        
        total_cost = storage_monthly + request_monthly
        
        components = [
            {'name': 'Storage (50GB est.)', 'cost': storage_monthly, 'unit': 'monthly'},
            {'name': 'Requests (est.)', 'cost': request_monthly, 'unit': 'monthly'},
        ]
        
        return total_cost, components

    def _calculate_lambda_cost(self, memory_size: int) -> tuple[float, List[Dict]]:
        monthly_requests = 1000000
        avg_duration_ms = 200
        gb_seconds = (memory_size / 1024) * (avg_duration_ms / 1000) * monthly_requests
        compute_cost = max(0, (gb_seconds - 400000) * 0.00001667)
        request_cost = max(0, (monthly_requests - 1000000) * 0.0000002)
        
        total_cost = compute_cost + request_cost
        
        components = [
            {'name': 'Compute (1M invocations)', 'cost': compute_cost, 'unit': 'monthly'},
            {'name': 'Requests', 'cost': request_cost, 'unit': 'monthly'},
        ]
        
        return total_cost, components

    def _calculate_eks_cost(self) -> tuple[float, List[Dict]]:
        cluster_monthly = 0.10 * 730
        
        components = [
            {'name': 'EKS Cluster', 'cost': cluster_monthly, 'unit': 'monthly'},
        ]
        
        return cluster_monthly, components

    def _calculate_ebs_cost(self, volume_type: str, size_gb: int) -> tuple[float, List[Dict]]:
        price_per_gb = {
            'gp2': 0.10, 'gp3': 0.08, 'io1': 0.125, 'io2': 0.125,
            'st1': 0.045, 'sc1': 0.025, 'standard': 0.05
        }
        monthly_cost = size_gb * price_per_gb.get(volume_type, 0.10)
        
        components = [
            {'name': f'EBS {volume_type.upper()}', 'cost': monthly_cost, 'unit': 'monthly'},
        ]
        
        return monthly_cost, components

    def _calculate_elasticache_cost(self, node_type: str, num_nodes: int) -> tuple[float, List[Dict]]:
        base_prices = {
            'cache.t2.micro': 0.017, 'cache.t2.small': 0.034, 'cache.t2.medium': 0.068,
            'cache.t3.micro': 0.016, 'cache.t3.small': 0.032, 'cache.t3.medium': 0.064,
        }
        hourly_rate = base_prices.get(node_type, 0.05)
        total_monthly = hourly_rate * 730 * num_nodes
        
        components = [
            {'name': f'ElastiCache {node_type} x{num_nodes}', 'cost': total_monthly, 'unit': 'monthly'},
        ]
        
        return total_monthly, components

    def _calculate_azure_vm_cost(self, vm_size: str, attributes: Dict) -> tuple[float, List[Dict]]:
        base_prices = {
            'Standard_B1s': 0.006, 'Standard_B1ms': 0.012, 'Standard_B2s': 0.024,
            'Standard_D2s_v3': 0.096, 'Standard_D4s_v3': 0.192,
        }
        hourly_rate = base_prices.get(vm_size, 0.05)
        monthly_compute = hourly_rate * 730
        
        components = [
            {'name': 'Compute', 'cost': monthly_compute, 'unit': 'monthly'},
        ]
        
        return monthly_compute, components

    def _calculate_azure_storage_cost(self, account_tier: str) -> tuple[float, List[Dict]]:
        monthly_cost = 20.0 if account_tier == 'Premium' else 5.0
        
        components = [
            {'name': f'Storage Account ({account_tier})', 'cost': monthly_cost, 'unit': 'monthly'},
        ]
        
        return monthly_cost, components

    def _calculate_aks_cost(self) -> tuple[float, List[Dict]]:
        cluster_monthly = 0.0
        
        components = [
            {'name': 'AKS Cluster (free)', 'cost': cluster_monthly, 'unit': 'monthly'},
        ]
        
        return cluster_monthly, components

    def _calculate_gcp_vm_cost(self, machine_type: str, attributes: Dict) -> tuple[float, List[Dict]]:
        base_prices = {
            'n1-standard-1': 0.0475, 'n1-standard-2': 0.095, 'n1-standard-4': 0.19,
            'e2-micro': 0.008, 'e2-small': 0.016, 'e2-medium': 0.032,
        }
        hourly_rate = base_prices.get(machine_type, 0.05)
        monthly_compute = hourly_rate * 730 * 0.75
        
        components = [
            {'name': 'Compute (730h)', 'cost': monthly_compute, 'unit': 'monthly'},
        ]
        
        return monthly_compute, components

    def _calculate_gcp_storage_cost(self) -> tuple[float, List[Dict]]:
        storage_monthly = 50 * 0.026
        
        components = [
            {'name': 'GCS Storage (50GB est.)', 'cost': storage_monthly, 'unit': 'monthly'},
        ]
        
        return storage_monthly, components

    def _calculate_gke_cost(self) -> tuple[float, List[Dict]]:
        cluster_monthly = 0.10 * 730
        
        components = [
            {'name': 'GKE Cluster', 'cost': cluster_monthly, 'unit': 'monthly'},
        ]
        
        return cluster_monthly, components

    def _estimate_generic_cost(self, resource_type: str, attributes: Dict) -> tuple[float, List[Dict]]:
        cost_estimates = {
            'aws_vpc': 0.0, 'aws_subnet': 0.0, 'aws_security_group': 0.0,
            'aws_iam_role': 0.0, 'aws_iam_policy': 0.0,
            'aws_cloudwatch_metric_alarm': 0.10,
            'aws_route53_zone': 0.50,
            'aws_cloudfront_distribution': 20.0,
            'aws_alb': 16.43, 'aws_nlb': 16.43,
        }
        estimated_cost = cost_estimates.get(resource_type, 0.0)
        
        components = [
            {'name': 'Estimated cost', 'cost': estimated_cost, 'unit': 'monthly'},
        ]
        
        return estimated_cost, components

    def _get_aws_instance_prices(self) -> Dict:
        return {
            't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
        }

    def _get_azure_instance_prices(self) -> Dict:
        return {
            'Standard_B1s': 0.006, 'Standard_B1ms': 0.012,
            'Standard_D2s_v3': 0.096,
        }

    def _get_gcp_instance_prices(self) -> Dict:
        return {
            'n1-standard-1': 0.0475, 'n1-standard-2': 0.095,
            'e2-micro': 0.008, 'e2-small': 0.016,
        }

    def analyze(self) -> List[ResourceCost]:
        resources = self.state_data.get('resources', [])
        
        for resource in resources:
            provider = self._get_resource_type(resource['type'])
            parser = self.provider_mapping.get(provider)
            
            if parser:
                try:
                    resource_cost = parser(resource)
                    self.resources.append(resource_cost)
                except Exception as e:
                    print(f"Warning: Could not parse {resource['type']}.{resource['name']}: {e}")

        return self.resources

    def get_summary(self) -> Dict:
        total_cost = sum(r.estimated_monthly_cost for r in self.resources)
        
        cost_by_provider = defaultdict(float)
        cost_by_type = defaultdict(float)
        cost_by_region = defaultdict(float)
        
        for r in self.resources:
            cost_by_provider[r.provider] += r.estimated_monthly_cost
            cost_by_type[r.resource_type] += r.estimated_monthly_cost
            cost_by_region[r.region] += r.estimated_monthly_cost
        
        resources_without_tags = [
            r for r in self.resources 
            if not r.tags or len(r.tags) < 2
        ]
        
        return {
            'total_resources': len(self.resources),
            'total_monthly_cost': round(total_cost, 2),
            'total_annual_cost': round(total_cost * 12, 2),
            'cost_by_provider': dict(cost_by_provider),
            'cost_by_resource_type': dict(cost_by_type),
            'cost_by_region': dict(cost_by_region),
            'resources_without_tags': len(resources_without_tags),
            'untagged_resources': [r.resource_address for r in resources_without_tags],
            'analysis_date': datetime.now().isoformat(),
        }

    def export_json(self, output_path: str):
        summary = self.get_summary()
        resources_data = [asdict(r) for r in self.resources]
        
        result = {
            'summary': summary,
            'resources': resources_data,
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Terraform State Cost Analyzer')
    parser.add_argument('--state', required=True, help='Path to terraform.tfstate')
    parser.add_argument('--output', default='cost_analysis.json', help='Output JSON path')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    
    args = parser.parse_args()
    
    analyzer = TfstateAnalyzer(args.state)
    analyzer.analyze()
    summary = analyzer.get_summary()
    
    if args.summary:
        print("\n=== Terraform State Cost Analysis ===")
        print(f"\nTotal Resources: {summary['total_resources']}")
        print(f"Estimated Monthly Cost: ${summary['total_monthly_cost']:.2f}")
        print(f"Estimated Annual Cost: ${summary['total_annual_cost']:.2f}")
        
        print("\nCost by Provider:")
        for provider, cost in sorted(summary['cost_by_provider'].items(), key=lambda x: -x[1]):
            print(f"  {provider.upper()}: ${cost:.2f} ({cost/summary['total_monthly_cost']*100:.1f}%)")
        
        print("\nTop 5 Resource Types by Cost:")
        top_types = sorted(summary['cost_by_resource_type'].items(), key=lambda x: -x[1])[:5]
        for rtype, cost in top_types:
            if cost > 0:
                print(f"  {rtype}: ${cost:.2f}")
        
        print(f"\nResources without proper tags: {summary['resources_without_tags']}")
        if summary['untagged_resources']:
            print("  " + ", ".join(summary['untagged_resources'][:10]))
    else:
        analyzer.export_json(args.output)


if __name__ == '__main__':
    main()
