import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from .base_collector import BaseCollector

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False


class AWSCollector(BaseCollector):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.access_key_id = config.get('access_key_id')
        self.secret_access_key = config.get('secret_access_key')
        self.clients = {}
        
        if AWS_AVAILABLE and self.access_key_id and self.secret_access_key:
            for region in config.get('regions', []):
                self.clients[region] = {
                    'ec2': boto3.client(
                        'ec2',
                        region_name=region,
                        aws_access_key_id=self.access_key_id,
                        aws_secret_access_key=self.secret_access_key
                    ),
                    'cloudwatch': boto3.client(
                        'cloudwatch',
                        region_name=region,
                        aws_access_key_id=self.access_key_id,
                        aws_secret_access_key=self.secret_access_key
                    )
                }

    def _get_client(self, region: str, service: str = 'ec2'):
        if region not in self.clients and AWS_AVAILABLE:
            self.clients[region] = {
                'ec2': boto3.client(
                    'ec2',
                    region_name=region,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key
                ),
                'cloudwatch': boto3.client(
                    'cloudwatch',
                    region_name=region,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key
                )
            }
        return self.clients.get(region, {}).get(service)

    def get_ecs_instances(self, region: str) -> pd.DataFrame:
        if not AWS_AVAILABLE:
            print("AWS SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region, 'ec2')
        if not client:
            return pd.DataFrame()

        try:
            response = client.describe_instances()
            records = []
            
            for reservation in response.get('Reservations', []):
                for inst in reservation.get('Instances', []):
                    records.append({
                        'instance_id': inst.get('InstanceId'),
                        'instance_name': next((t['Value'] for t in inst.get('Tags', []) if t['Key'] == 'Name'), ''),
                        'instance_type': inst.get('InstanceType'),
                        'status': inst.get('State', {}).get('Name'),
                        'cpu': inst.get('CpuOptions', {}).get('CoreCount', 0),
                        'memory': 0,
                        'os_name': inst.get('Platform', 'linux'),
                        'public_ip': inst.get('PublicIpAddress', ''),
                        'private_ip': inst.get('PrivateIpAddress', ''),
                        'creation_time': inst.get('LaunchTime'),
                        'expired_time': None,
                        'zone_id': inst.get('Placement', {}).get('AvailabilityZone'),
                        'tags': str(inst.get('Tags', []))
                    })
            
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error getting EC2 instances from {region}: {e}")
            return pd.DataFrame()

    def get_eip_addresses(self, region: str) -> pd.DataFrame:
        if not AWS_AVAILABLE:
            print("AWS SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region, 'ec2')
        if not client:
            return pd.DataFrame()

        try:
            response = client.describe_addresses()
            addresses = response.get('Addresses', [])
            records = []
            
            for eip in addresses:
                records.append({
                    'allocation_id': eip.get('AllocationId'),
                    'ip_address': eip.get('PublicIp'),
                    'status': 'Available' if not eip.get('InstanceId') else 'Associated',
                    'instance_id': eip.get('InstanceId', ''),
                    'instance_type': 'EC2' if eip.get('InstanceId') else '',
                    'bandwidth': 0,
                    'internet_charge_type': 'pay-as-you-go',
                    'creation_time': None,
                    'region_id': region
                })
            
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error getting EIP addresses from {region}: {e}")
            return pd.DataFrame()

    def get_metric_data(self, instance_id: str, metric: str,
                        start_time: datetime, end_time: datetime,
                        region: str) -> pd.DataFrame:
        if not AWS_AVAILABLE:
            print("AWS SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region, 'cloudwatch')
        if not client:
            return pd.DataFrame()

        metric_mapping = {
            'cpu_utilization': 'CPUUtilization',
            'memory_utilization': 'MemoryUtilization',
            'network_traffic': 'NetworkIn'
        }
        cw_metric = metric_mapping.get(metric, metric)

        try:
            response = client.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName=cw_metric,
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            datapoints = response.get('Datapoints', [])
            records = []
            
            for dp in datapoints:
                records.append({
                    'timestamp': dp.get('Timestamp'),
                    'value': dp.get('Average', 0),
                    'maximum': dp.get('Maximum', 0),
                    'minimum': dp.get('Minimum', 0)
                })
            
            df = pd.DataFrame(records)
            if not df.empty:
                df = df.sort_values('timestamp')
            
            return df
        except Exception as e:
            print(f"Error getting metric data for {instance_id}: {e}")
            return pd.DataFrame()
