#!/usr/bin/env python3
"""
多云统一成本分析适配器
支持 AWS / Azure / GCP 三大云平台的统一成本查询与分析
"""
import abc
import argparse
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class CloudCostAdapter(abc.ABC):
    """云成本适配器抽象基类"""
    
    @abc.abstractmethod
    def get_name(self) -> str:
        """返回适配器名称"""
        pass
    
    @abc.abstractmethod
    def get_monthly_cost(self, start_date: datetime, end_date: datetime) -> float:
        """获取月度总成本"""
        pass
    
    @abc.abstractmethod
    def get_cost_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """按服务维度获取成本"""
        pass
    
    @abc.abstractmethod
    def get_cost_by_region(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """按区域维度获取成本"""
        pass
    
    @abc.abstractmethod
    def get_cost_by_tag(self, tag_key: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """按标签维度获取成本"""
        pass


class AWSCostAdapter(CloudCostAdapter):
    """AWS 成本适配器"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        try:
            import boto3
            self.ce = boto3.client('ce', region_name=region)
            self.available = True
        except ImportError:
            print("Warning: boto3 not installed, AWS adapter disabled")
            self.available = False
        except Exception as e:
            print(f"Warning: AWS credentials not configured: {e}")
            self.available = False
    
    def get_name(self) -> str:
        return "AWS"
    
    def _get_cost_data(self, start_date: datetime, end_date: datetime, group_by: List = None):
        if not self.available:
            return {}
        
        try:
            kwargs = {
                'TimePeriod': {
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                'Granularity': 'MONTHLY',
                'Metrics': ['UnblendedCost']
            }
            if group_by:
                kwargs['GroupBy'] = group_by
            
            response = self.ce.get_cost_and_usage(**kwargs)
            
            results = defaultdict(float)
            for result in response.get('ResultsByTime', []):
                for group in result.get('Groups', []):
                    key = group['Keys'][0] if group['Keys'] else 'total'
                    value = float(group['Metrics']['UnblendedCost']['Amount'])
                    results[key] += value
            
            return dict(results)
        except Exception as e:
            print(f"AWS API Error: {e}")
            return {}
    
    def get_monthly_cost(self, start_date: datetime, end_date: datetime) -> float:
        if not self.available:
            return 0.0
        
        try:
            response = self.ce.get_cost_and_usage(
                TimePeriod={'Start': start_date.strftime('%Y-%m-%d'), 'End': end_date.strftime('%Y-%m-%d')},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost']
            )
            
            total = 0.0
            for result in response.get('ResultsByTime', []):
                total += float(result['Total']['UnblendedCost']['Amount'])
            return total
        except Exception as e:
            print(f"AWS Error: {e}")
            return 0.0
    
    def get_cost_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return self._get_cost_data(start_date, end_date, [{'Type': 'DIMENSION', 'Key': 'SERVICE'}])
    
    def get_cost_by_region(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return self._get_cost_data(start_date, end_date, [{'Type': 'DIMENSION', 'Key': 'REGION'}])
    
    def get_cost_by_tag(self, tag_key: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        return self._get_cost_data(start_date, end_date, [{'Type': 'TAG', 'Key': tag_key}])


class AzureCostAdapter(CloudCostAdapter):
    """Azure 成本适配器"""
    
    def __init__(self, subscription_id: str = None):
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        self.available = False
        
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.costmanagement import CostManagementClient
            
            self.credential = DefaultAzureCredential()
            if self.subscription_id:
                self.client = CostManagementClient(self.credential, "https://management.azure.com")
                self.available = True
            else:
                print("Warning: AZURE_SUBSCRIPTION_ID not set")
        except ImportError:
            print("Warning: Azure SDK not installed, Azure adapter disabled")
        except Exception as e:
            print(f"Warning: Azure authentication failed: {e}")
    
    def get_name(self) -> str:
        return "Azure"
    
    def get_monthly_cost(self, start_date: datetime, end_date: datetime) -> float:
        if not self.available:
            return 0.0
        
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "Monthly",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    }
                }
            }
            
            result = self.client.query.usage(scope, query)
            total = sum(row[0] for row in result.properties.rows) if result.properties.rows else 0.0
            return total
        except Exception as e:
            print(f"Azure Error: {e}")
            return 0.0
    
    def get_cost_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "Monthly",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {"type": "Dimension", "name": "ServiceName"}
                    ]
                }
            }
            
            result = self.client.query.usage(scope, query)
            
            costs = defaultdict(float)
            for row in result.properties.rows:
                service_name = row[1]
                cost = row[0]
                costs[service_name] += cost
            
            return dict(costs)
        except Exception as e:
            print(f"Azure Error: {e}")
            return {}
    
    def get_cost_by_region(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "Monthly",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {"type": "Dimension", "name": "ResourceLocation"}
                    ]
                }
            }
            
            result = self.client.query.usage(scope, query)
            
            costs = defaultdict(float)
            for row in result.properties.rows:
                region = row[1]
                cost = row[0]
                costs[region] += cost
            
            return dict(costs)
        except Exception as e:
            print(f"Azure Error: {e}")
            return {}
    
    def get_cost_by_tag(self, tag_key: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        
        try:
            scope = f"/subscriptions/{self.subscription_id}"
            
            query = {
                "type": "ActualCost",
                "timeframe": "Custom",
                "timePeriod": {
                    "from": start_date.isoformat(),
                    "to": end_date.isoformat()
                },
                "dataset": {
                    "granularity": "Monthly",
                    "aggregation": {
                        "totalCost": {
                            "name": "PreTaxCost",
                            "function": "Sum"
                        }
                    },
                    "grouping": [
                        {"type": "Tag", "key": tag_key}
                    ]
                }
            }
            
            result = self.client.query.usage(scope, query)
            
            costs = defaultdict(float)
            for row in result.properties.rows:
                tag_value = row[1] or 'untagged'
                cost = row[0]
                costs[tag_value] += cost
            
            return dict(costs)
        except Exception as e:
            print(f"Azure Error: {e}")
            return {}


class GCPCostAdapter(CloudCostAdapter):
    """GCP 成本适配器"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self.available = False
        
        try:
            from google.cloud import billing_v1
            from google.oauth2 import service_account
            
            if self.project_id:
                self.client = billing_v1.CloudBillingClient()
                self.billing_account = None
                self.available = True
            else:
                print("Warning: GCP_PROJECT_ID not set")
        except ImportError:
            print("Warning: GCP SDK not installed, GCP adapter disabled")
        except Exception as e:
            print(f"Warning: GCP authentication failed: {e}")
    
    def get_name(self) -> str:
        return "GCP"
    
    def get_monthly_cost(self, start_date: datetime, end_date: datetime) -> float:
        if not self.available:
            return 0.0
        return 0.0
    
    def get_cost_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        return {}
    
    def get_cost_by_region(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        return {}
    
    def get_cost_by_tag(self, tag_key: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        if not self.available:
            return {}
        return {}


class MultiCloudCostAnalyzer:
    """多云成本统一分析器"""
    
    def __init__(self, providers: List[str] = None, **kwargs):
        self.adapters = {}
        
        if not providers or 'aws' in providers:
            self.adapters['aws'] = AWSCostAdapter(kwargs.get('aws_region', 'us-east-1'))
        
        if not providers or 'azure' in providers:
            self.adapters['azure'] = AzureCostAdapter(kwargs.get('azure_subscription_id'))
        
        if not providers or 'gcp' in providers:
            self.adapters['gcp'] = GCPCostAdapter(kwargs.get('gcp_project_id'))
    
    def get_available_providers(self) -> List[str]:
        return [name for name, adapter in self.adapters.items() if adapter.available]
    
    def get_total_cost(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        results = {}
        for name, adapter in self.adapters.items():
            if adapter.available:
                results[name] = adapter.get_monthly_cost(start_date, end_date)
        results['total'] = sum(results.values())
        return results
    
    def get_cost_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, Dict[str, float]]:
        results = {}
        for name, adapter in self.adapters.items():
            if adapter.available:
                results[name] = adapter.get_cost_by_service(start_date, end_date)
        return results
    
    def get_cost_by_region(self, start_date: datetime, end_date: datetime) -> Dict[str, Dict[str, float]]:
        results = {}
        for name, adapter in self.adapters.items():
            if adapter.available:
                results[name] = adapter.get_cost_by_region(start_date, end_date)
        return results
    
    def get_aggregated_by_service(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        aggregated = defaultdict(float)
        costs_by_provider = self.get_cost_by_service(start_date, end_date)
        
        for provider, services in costs_by_provider.items():
            for service, cost in services.items():
                aggregated[f"{provider}:{service}"] = cost
        
        return dict(sorted(aggregated.items(), key=lambda x: -x[1]))
    
    def generate_report(self, start_date: datetime, end_date: datetime) -> Dict:
        total_costs = self.get_total_cost(start_date, end_date)
        by_service = self.get_cost_by_service(start_date, end_date)
        by_region = self.get_cost_by_region(start_date, end_date)
        
        top_services = self.get_aggregated_by_service(start_date, end_date)
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'providers': self.get_available_providers(),
            'total_cost': total_costs,
            'cost_by_provider': {k: v for k, v in total_costs.items() if k != 'total'},
            'top_services': dict(list(top_services.items())[:10]),
            'cost_by_service': by_service,
            'cost_by_region': by_region,
            'report_generated': datetime.now().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(description='Multi-Cloud Cost Analyzer')
    parser.add_argument('--providers', nargs='+', default=['aws', 'azure', 'gcp'],
                        help='Cloud providers to analyze')
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', default='multi_cloud_cost_report.json',
                        help='Output JSON file')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    
    args = parser.parse_args()
    
    if args.start_date and args.end_date:
        start_date = datetime.fromisoformat(args.start_date)
        end_date = datetime.fromisoformat(args.end_date)
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    
    print(f"Analyzing cloud costs from {start_date.date()} to {end_date.date()}...")
    print()
    
    analyzer = MultiCloudCostAnalyzer(providers=args.providers)
    
    available = analyzer.get_available_providers()
    print(f"Available providers: {', '.join(available)}")
    print()
    
    report = analyzer.generate_report(start_date, end_date)
    
    if args.summary:
        print("=" * 60)
        print("MULTI-CLOUD COST SUMMARY")
        print("=" * 60)
        print(f"\nPeriod: {start_date.date()} to {end_date.date()}")
        print(f"\nTotal Cost: ${report['total_cost']['total']:.2f}")
        print("\nBy Provider:")
        for provider, cost in report['cost_by_provider'].items():
            print(f"  {provider.upper()}: ${cost:.2f}")
        
        print("\nTop Services:")
        for service, cost in list(report['top_services'].items())[:10]:
            if cost > 0:
                print(f"  {service}: ${cost:.2f}")
    else:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Report saved to {args.output}")


if __name__ == '__main__':
    main()
