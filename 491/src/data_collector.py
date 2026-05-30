import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random


class CloudResourceDataCollector:
    def __init__(self, cloud_provider: str = "aws"):
        self.cloud_provider = cloud_provider.lower()
        self.instance_types = {
            "aws": {
                "t2.micro": {"vcpu": 1, "memory_gb": 1, "ondemand_price": 0.0116, "ri_price_1y": 0.0058, "ri_price_3y": 0.0035},
                "t2.small": {"vcpu": 1, "memory_gb": 2, "ondemand_price": 0.023, "ri_price_1y": 0.0115, "ri_price_3y": 0.007},
                "t2.medium": {"vcpu": 2, "memory_gb": 4, "ondemand_price": 0.0464, "ri_price_1y": 0.0232, "ri_price_3y": 0.014},
                "t2.large": {"vcpu": 2, "memory_gb": 8, "ondemand_price": 0.0928, "ri_price_1y": 0.0464, "ri_price_3y": 0.028},
                "m5.large": {"vcpu": 2, "memory_gb": 8, "ondemand_price": 0.096, "ri_price_1y": 0.048, "ri_price_3y": 0.029},
                "m5.xlarge": {"vcpu": 4, "memory_gb": 16, "ondemand_price": 0.192, "ri_price_1y": 0.096, "ri_price_3y": 0.058},
                "m5.2xlarge": {"vcpu": 8, "memory_gb": 32, "ondemand_price": 0.384, "ri_price_1y": 0.192, "ri_price_3y": 0.116},
                "c5.large": {"vcpu": 2, "memory_gb": 4, "ondemand_price": 0.085, "ri_price_1y": 0.0425, "ri_price_3y": 0.0255},
                "c5.xlarge": {"vcpu": 4, "memory_gb": 8, "ondemand_price": 0.17, "ri_price_1y": 0.085, "ri_price_3y": 0.051},
                "r5.large": {"vcpu": 2, "memory_gb": 16, "ondemand_price": 0.126, "ri_price_1y": 0.063, "ri_price_3y": 0.038},
            },
            "azure": {
                "Standard_B1s": {"vcpu": 1, "memory_gb": 1, "ondemand_price": 0.0107, "ri_price_1y": 0.0054, "ri_price_3y": 0.0032},
                "Standard_B2s": {"vcpu": 2, "memory_gb": 4, "ondemand_price": 0.0428, "ri_price_1y": 0.0214, "ri_price_3y": 0.0128},
                "Standard_D2s_v3": {"vcpu": 2, "memory_gb": 8, "ondemand_price": 0.096, "ri_price_1y": 0.048, "ri_price_3y": 0.029},
                "Standard_D4s_v3": {"vcpu": 4, "memory_gb": 16, "ondemand_price": 0.192, "ri_price_1y": 0.096, "ri_price_3y": 0.058},
            },
            "gcp": {
                "e2-micro": {"vcpu": 2, "memory_gb": 1, "ondemand_price": 0.0085, "ri_price_1y": 0.00425, "ri_price_3y": 0.00255},
                "e2-small": {"vcpu": 2, "memory_gb": 2, "ondemand_price": 0.017, "ri_price_1y": 0.0085, "ri_price_3y": 0.0051},
                "e2-medium": {"vcpu": 2, "memory_gb": 4, "ondemand_price": 0.034, "ri_price_1y": 0.017, "ri_price_3y": 0.0102},
                "n1-standard-1": {"vcpu": 1, "memory_gb": 3.75, "ondemand_price": 0.0475, "ri_price_1y": 0.02375, "ri_price_3y": 0.01425},
            }
        }

    def generate_historical_cost_data(self, days: int = 90) -> pd.DataFrame:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        base_cost = random.uniform(5000, 15000)
        trend = np.linspace(0, random.uniform(0.1, 0.3), len(dates))
        weekly_seasonality = np.array([1.1 if d.weekday() < 5 else 0.85 for d in dates])
        noise = np.random.normal(0, 0.05, len(dates))
        
        daily_costs = base_cost * (1 + trend) * weekly_seasonality * (1 + noise)
        
        services = ['EC2', 'S3', 'RDS', 'Lambda', 'EBS', 'CloudWatch', 'DataTransfer']
        service_distribution = np.random.dirichlet([3, 1.5, 2, 1, 1.5, 0.5, 0.5])
        
        data = []
        for i, date in enumerate(dates):
            for j, service in enumerate(services):
                data.append({
                    'date': date,
                    'service': service,
                    'cost': daily_costs[i] * service_distribution[j],
                    'region': random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']),
                    'account': random.choice(['prod-account', 'dev-account', 'staging-account'])
                })
        
        return pd.DataFrame(data)

    def generate_instance_data(self, num_instances: int = 50) -> pd.DataFrame:
        instances = []
        instance_type_list = list(self.instance_types[self.cloud_provider].keys())
        
        for i in range(num_instances):
            instance_type = random.choice(instance_type_list)
            instance_info = self.instance_types[self.cloud_provider][instance_type]
            
            avg_cpu = random.betavariate(2, 5) * 100
            avg_memory = random.betavariate(3, 4) * 100
            avg_network = random.betavariate(1, 3) * 100
            
            running_hours = int(random.uniform(24 * 7, 24 * 30))
            
            instances.append({
                'instance_id': f'i-{random.randint(10000000, 99999999):08d}',
                'instance_type': instance_type,
                'vcpu': instance_info['vcpu'],
                'memory_gb': instance_info['memory_gb'],
                'region': np.random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-northeast-1']),
                'availability_zone': np.random.choice(['a', 'b', 'c']),
                'state': np.random.choice(['running', 'stopped', 'terminated'], p=[0.8, 0.15, 0.05]),
                'launch_time': datetime.now() - timedelta(days=random.randint(1, 365)),
                'name': f'server-{chr(65 + i % 26)}{i // 26 + 1}',
                'environment': np.random.choice(['production', 'development', 'staging'], p=[0.5, 0.3, 0.2]),
                'avg_cpu_7d': avg_cpu,
                'avg_memory_7d': avg_memory,
                'avg_network_7d': avg_network,
                'max_cpu_7d': min(100, avg_cpu * random.uniform(1.5, 2.5)),
                'max_memory_7d': min(100, avg_memory * random.uniform(1.3, 2.0)),
                'p95_cpu_7d': min(100, avg_cpu * random.uniform(1.3, 1.8)),
                'p95_memory_7d': min(100, avg_memory * random.uniform(1.2, 1.6)),
                'running_hours_30d': running_hours,
                'ondemand_cost_30d': instance_info['ondemand_price'] * running_hours,
                'purchase_type': np.random.choice(['on_demand', 'reserved', 'spot'], p=[0.6, 0.3, 0.1]),
            })
        
        return pd.DataFrame(instances)

    def generate_ebs_data(self, num_volumes: int = 30) -> pd.DataFrame:
        volumes = []
        volume_types = ['gp2', 'gp3', 'io1', 'st1', 'sc1']
        
        for i in range(num_volumes):
            volume_type = random.choice(volume_types)
            size_gb = random.choice([8, 16, 32, 64, 128, 256, 512, 1024])
            
            volumes.append({
                'volume_id': f'vol-{random.randint(10000000, 99999999):08d}',
                'volume_type': volume_type,
                'size_gb': size_gb,
                'state': np.random.choice(['in-use', 'available'], p=[0.7, 0.3]),
                'attached_instance': f'i-{random.randint(10000000, 99999999):08d}' if random.random() < 0.7 else None,
                'create_time': datetime.now() - timedelta(days=random.randint(1, 365)),
                'iops': random.randint(100, 10000) if volume_type in ['gp3', 'io1'] else None,
                'throughput': random.randint(125, 1000) if volume_type == 'gp3' else None,
                'monthly_cost': self._calculate_ebs_cost(volume_type, size_gb),
                'avg_read_ops': random.uniform(0, 1000),
                'avg_write_ops': random.uniform(0, 500),
                'avg_read_bytes': random.uniform(0, 10**9),
                'avg_write_bytes': random.uniform(0, 5 * 10**8),
            })
        
        return pd.DataFrame(volumes)

    def _calculate_ebs_cost(self, volume_type: str, size_gb: int) -> float:
        pricing = {
            'gp2': 0.10,
            'gp3': 0.08,
            'io1': 0.125,
            'st1': 0.045,
            'sc1': 0.025,
        }
        return pricing.get(volume_type, 0.10) * size_gb

    def generate_reservation_recommendations(self) -> Dict:
        instance_types = list(self.instance_types[self.cloud_provider].keys())
        recommendations = []
        
        for _ in range(10):
            instance_type = random.choice(instance_types)
            info = self.instance_types[self.cloud_provider][instance_type]
            ondemand_hours = random.randint(500, 720)
            
            savings_1y = (info['ondemand_price'] - info['ri_price_1y']) * ondemand_hours
            savings_3y = (info['ondemand_price'] - info['ri_price_3y']) * ondemand_hours
            
            recommendations.append({
                'instance_type': instance_type,
                'region': random.choice(['us-east-1', 'us-west-2', 'eu-west-1']),
                'current_instances': random.randint(2, 10),
                'recommended_count': random.randint(1, 5),
                'utilization_rate': random.uniform(0.7, 0.95),
                'breakeven_months_1y': random.uniform(3, 6),
                'breakeven_months_3y': random.uniform(6, 12),
                'monthly_savings_1y': savings_1y,
                'monthly_savings_3y': savings_3y,
                'yearly_savings_1y': savings_1y * 12,
                'yearly_savings_3y': savings_3y * 12,
                'upfront_cost_1y': info['ri_price_1y'] * 24 * 365,
                'upfront_cost_3y': info['ri_price_3y'] * 24 * 365 * 3,
            })
        
        return {
            'recommendations': recommendations,
            'total_monthly_savings_1y': sum(r['monthly_savings_1y'] for r in recommendations),
            'total_monthly_savings_3y': sum(r['monthly_savings_3y'] for r in recommendations),
            'total_yearly_savings_1y': sum(r['yearly_savings_1y'] for r in recommendations),
            'total_yearly_savings_3y': sum(r['yearly_savings_3y'] for r in recommendations),
        }

    def get_all_data(self) -> Dict:
        return {
            'historical_costs': self.generate_historical_cost_data(),
            'instances': self.generate_instance_data(),
            'ebs_volumes': self.generate_ebs_data(),
            'reservation_recs': self.generate_reservation_recommendations(),
            'cloud_provider': self.cloud_provider,
        }
