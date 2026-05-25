import pandas as pd
from datetime import datetime, timedelta
from typing import Dict
from .base_collector import BaseCollector

try:
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.acs_exception.exceptions import ClientException
    from aliyunsdkcore.acs_exception.exceptions import ServerException
    from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
    from aliyunsdkvpc.request.v20160428.DescribeEipAddressesRequest import DescribeEipAddressesRequest
    from aliyunsdkcms.request.v20190101.DescribeMetricListRequest import DescribeMetricListRequest
    import json
    ALIYUN_AVAILABLE = True
except ImportError:
    ALIYUN_AVAILABLE = False


class AliyunCollector(BaseCollector):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.access_key_id = config.get('access_key_id')
        self.access_key_secret = config.get('access_key_secret')
        self.clients = {}
        
        if ALIYUN_AVAILABLE and self.access_key_id and self.access_key_secret:
            for region in config.get('regions', []):
                self.clients[region] = AcsClient(
                    self.access_key_id,
                    self.access_key_secret,
                    region
                )

    def _get_client(self, region: str):
        if region not in self.clients and ALIYUN_AVAILABLE:
            self.clients[region] = AcsClient(
                self.access_key_id,
                self.access_key_secret,
                region
            )
        return self.clients.get(region)

    def get_ecs_instances(self, region: str) -> pd.DataFrame:
        if not ALIYUN_AVAILABLE:
            print("Aliyun SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region)
        if not client:
            return pd.DataFrame()

        try:
            request = DescribeInstancesRequest()
            request.set_PageSize(100)
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            instances = data.get('Instances', {}).get('Instance', [])
            records = []
            
            for inst in instances:
                records.append({
                    'instance_id': inst.get('InstanceId'),
                    'instance_name': inst.get('InstanceName'),
                    'instance_type': inst.get('InstanceType'),
                    'status': inst.get('Status'),
                    'cpu': inst.get('Cpu'),
                    'memory': inst.get('Memory'),
                    'os_name': inst.get('OSName'),
                    'public_ip': ','.join(inst.get('PublicIpAddress', {}).get('IpAddress', [])),
                    'private_ip': ','.join(inst.get('VpcAttributes', {}).get('PrivateIpAddress', {}).get('IpAddress', [])),
                    'creation_time': inst.get('CreationTime'),
                    'expired_time': inst.get('ExpiredTime'),
                    'zone_id': inst.get('ZoneId'),
                    'tags': str(inst.get('Tags', {}).get('Tag', []))
                })
            
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error getting ECS instances from {region}: {e}")
            return pd.DataFrame()

    def get_eip_addresses(self, region: str) -> pd.DataFrame:
        if not ALIYUN_AVAILABLE:
            print("Aliyun SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region)
        if not client:
            return pd.DataFrame()

        try:
            request = DescribeEipAddressesRequest()
            request.set_PageSize(100)
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            
            eips = data.get('EipAddresses', {}).get('EipAddress', [])
            records = []
            
            for eip in eips:
                records.append({
                    'allocation_id': eip.get('AllocationId'),
                    'ip_address': eip.get('IpAddress'),
                    'status': eip.get('Status'),
                    'instance_id': eip.getInstanceId(),
                    'instance_type': eip.getInstanceType(),
                    'bandwidth': eip.get('Bandwidth'),
                    'internet_charge_type': eip.get('InternetChargeType'),
                    'creation_time': eip.get('AllocationTime'),
                    'region_id': eip.get('RegionId')
                })
            
            return pd.DataFrame(records)
        except Exception as e:
            print(f"Error getting EIP addresses from {region}: {e}")
            return pd.DataFrame()

    def get_metric_data(self, instance_id: str, metric: str,
                        start_time: datetime, end_time: datetime,
                        region: str) -> pd.DataFrame:
        if not ALIYUN_AVAILABLE:
            print("Aliyun SDK not available, returning empty DataFrame")
            return pd.DataFrame()

        client = self._get_client(region)
        if not client:
            return pd.DataFrame()

        metric_mapping = {
            'cpu_utilization': 'CPUUtilization',
            'memory_utilization': 'MemoryUtilization',
            'network_traffic': 'InternetTrafficRate'
        }
        cms_metric = metric_mapping.get(metric, metric)

        try:
            request = DescribeMetricListRequest()
            request.set_Namespace('acs_ecs_dashboard')
            request.set_MetricName(cms_metric)
            request.set_Dimensions(json.dumps([{"instanceId": instance_id}]))
            request.set_StartTime(start_time.strftime('%Y-%m-%d %H:%M:%S'))
            request.set_EndTime(end_time.strftime('%Y-%m-%d %H:%M:%S'))
            request.set_Period('300')
            
            response = client.do_action_with_exception(request)
            data = json.loads(response)
            datapoints = json.loads(data.get('Datapoints', '[]'))
            
            records = []
            for dp in datapoints:
                records.append({
                    'timestamp': dp.get('timestamp'),
                    'value': dp.get('Average', dp.get('Value', 0)),
                    'maximum': dp.get('Maximum', 0),
                    'minimum': dp.get('Minimum', 0)
                })
            
            df = pd.DataFrame(records)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            print(f"Error getting metric data for {instance_id}: {e}")
            return pd.DataFrame()
