import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict
from .base_collector import BaseCollector


class MockCollector(BaseCollector):
    def __init__(self, config: Dict = None):
        if config is None:
            config = {'regions': ['cn-hangzhou', 'cn-beijing']}
        super().__init__(config)
        self._mock_instances = self._generate_mock_instances()
        self._mock_eips = self._generate_mock_eips()

    def _generate_mock_instances(self) -> pd.DataFrame:
        instance_types = [
            ('ecs.t5-lc1m2.small', 1, 2048),
            ('ecs.t5-lc1m2.large', 2, 4096),
            ('ecs.t5-c1m2.xlarge', 4, 8192),
            ('ecs.g6.large', 2, 8192),
            ('ecs.g6.xlarge', 4, 16384),
            ('ecs.c6.large', 2, 4096),
            ('ecs.r6.large', 2, 16384)
        ]
        
        names = ['web-server', 'app-server', 'db-server', 'cache-server', 
                 'test-server', 'dev-server', 'api-gateway', 'worker-node',
                 'jenkins', 'gitlab-runner', 'monitoring', 'logging']
        
        statuses = ['Running', 'Running', 'Running', 'Running', 'Stopped']
        
        records = []
        for i in range(15):
            itype, cpu, mem = instance_types[np.random.randint(0, len(instance_types))]
            status = statuses[np.random.randint(0, len(statuses))]
            region = self.config['regions'][i % len(self.config['regions'])]
            
            records.append({
                'instance_id': f'i-mock{str(i).zfill(5)}',
                'instance_name': f'{names[i % len(names)]}-{i+1}',
                'instance_type': itype,
                'status': status,
                'cpu': cpu,
                'memory': mem,
                'os_name': 'CentOS 7.9' if i % 2 == 0 else 'Ubuntu 20.04',
                'public_ip': f'{np.random.randint(1,255)}.{np.random.randint(1,255)}.{np.random.randint(1,255)}.{np.random.randint(1,255)}',
                'private_ip': f'192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}',
                'creation_time': (datetime.now() - timedelta(days=np.random.randint(1, 365))).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'expired_time': '',
                'zone_id': f'{region}-{["a", "b", "c"][i % 3]}',
                'tags': str([{'TagKey': 'Environment', 'TagValue': ['prod', 'test', 'dev'][i % 3]}])
            })
        
        return pd.DataFrame(records)

    def _generate_mock_eips(self) -> pd.DataFrame:
        records = []
        for i in range(8):
            region = self.config['regions'][i % len(self.config['regions'])]
            is_bound = i < 5
            
            records.append({
                'allocation_id': f'eip-mock{str(i).zfill(5)}',
                'ip_address': f'{np.random.randint(1,255)}.{np.random.randint(1,255)}.{np.random.randint(1,255)}.{np.random.randint(1,255)}',
                'status': 'InUse' if is_bound else 'Available',
                'instance_id': f'i-mock{str(i).zfill(5)}' if is_bound else '',
                'instance_type': 'EcsInstance' if is_bound else '',
                'bandwidth': np.random.choice([5, 10, 20, 50, 100]),
                'internet_charge_type': 'PayByBandwidth' if i % 2 == 0 else 'PayByTraffic',
                'creation_time': (datetime.now() - timedelta(days=np.random.randint(1, 180))).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'region_id': region
            })
        
        return pd.DataFrame(records)

    def _generate_metric_timeseries(self, pattern: str, days: int = 7) -> pd.DataFrame:
        end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(days=days)
        
        timestamps = pd.date_range(start=start_time, end=end_time, freq='5min')
        n_points = len(timestamps)
        
        if pattern == 'idle':
            values = np.random.normal(3, 2, n_points)
            values = np.clip(values, 0, 15)
        elif pattern == 'low':
            values = np.random.normal(15, 8, n_points)
            values = np.clip(values, 0, 35)
        elif pattern == 'medium':
            values = np.random.normal(45, 15, n_points)
            values = np.clip(values, 10, 80)
        elif pattern == 'high':
            values = np.random.normal(75, 10, n_points)
            values = np.clip(values, 50, 100)
        elif pattern == 'spike':
            values = np.random.normal(20, 10, n_points)
            spike_indices = np.random.choice(n_points, size=int(n_points * 0.05), replace=False)
            values[spike_indices] = np.random.normal(80, 10, len(spike_indices))
            values = np.clip(values, 0, 100)
        else:
            values = np.random.normal(30, 15, n_points)
            values = np.clip(values, 0, 100)
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'value': values,
            'maximum': values + np.random.normal(5, 2, n_points),
            'minimum': values - np.random.normal(5, 2, n_points)
        })

    def get_ecs_instances(self, region: str) -> pd.DataFrame:
        if self._mock_instances.empty:
            return pd.DataFrame()
        return self._mock_instances[self._mock_instances['zone_id'].str.startswith(region)].copy()

    def get_eip_addresses(self, region: str) -> pd.DataFrame:
        if self._mock_eips.empty:
            return pd.DataFrame()
        return self._mock_eips[self._mock_eips['region_id'] == region].copy()

    def get_metric_data(self, instance_id: str, metric: str,
                        start_time: datetime, end_time: datetime,
                        region: str) -> pd.DataFrame:
        instance_idx = int(instance_id.replace('i-mock', '')) if instance_id.startswith('i-mock') else 0
        days = (end_time - start_time).days
        
        patterns = ['idle', 'low', 'medium', 'high', 'spike']
        pattern = patterns[instance_idx % len(patterns)]
        
        if metric == 'network_traffic':
            df = self._generate_metric_timeseries(pattern, days)
            df['value'] = df['value'] * 10240
            df['maximum'] = df['maximum'] * 10240
            df['minimum'] = df['minimum'] * 10240
        else:
            df = self._generate_metric_timeseries(pattern, days)
        
        return df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
