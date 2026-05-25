from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta


class BaseCollector(ABC):
    def __init__(self, config: Dict):
        self.config = config
        self.provider_name = self.__class__.__name__.replace('Collector', '').lower()

    @abstractmethod
    def get_ecs_instances(self, region: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_eip_addresses(self, region: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_metric_data(self, instance_id: str, metric: str, 
                        start_time: datetime, end_time: datetime,
                        region: str) -> pd.DataFrame:
        pass

    def get_cpu_utilization(self, instance_id: str, days: int = 7, 
                            region: str = None) -> pd.DataFrame:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        return self.get_metric_data(instance_id, 'cpu_utilization', 
                                    start_time, end_time, region)

    def get_memory_utilization(self, instance_id: str, days: int = 7,
                               region: str = None) -> pd.DataFrame:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        return self.get_metric_data(instance_id, 'memory_utilization',
                                    start_time, end_time, region)

    def get_network_traffic(self, instance_id: str, days: int = 7,
                            region: str = None) -> pd.DataFrame:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        return self.get_metric_data(instance_id, 'network_traffic',
                                    start_time, end_time, region)

    def collect_all_resources(self) -> Dict[str, pd.DataFrame]:
        regions = self.config.get('regions', [])
        all_ecs = []
        all_eips = []

        for region in regions:
            try:
                ecs_df = self.get_ecs_instances(region)
                ecs_df['region'] = region
                ecs_df['provider'] = self.provider_name
                all_ecs.append(ecs_df)
            except Exception as e:
                print(f"Error collecting ECS from {region}: {e}")

            try:
                eip_df = self.get_eip_addresses(region)
                eip_df['region'] = region
                eip_df['provider'] = self.provider_name
                all_eips.append(eip_df)
            except Exception as e:
                print(f"Error collecting EIP from {region}: {e}")

        return {
            'ecs': pd.concat(all_ecs, ignore_index=True) if all_ecs else pd.DataFrame(),
            'eip': pd.concat(all_eips, ignore_index=True) if all_eips else pd.DataFrame()
        }

    def collect_metrics_for_instances(self, instance_ids: List[str], 
                                       days: int = 7,
                                       region: str = None) -> pd.DataFrame:
        all_metrics = []
        for instance_id in instance_ids:
            try:
                cpu_df = self.get_cpu_utilization(instance_id, days, region)
                cpu_df['instance_id'] = instance_id
                cpu_df['metric_name'] = 'cpu_utilization'
                all_metrics.append(cpu_df)

                mem_df = self.get_memory_utilization(instance_id, days, region)
                mem_df['instance_id'] = instance_id
                mem_df['metric_name'] = 'memory_utilization'
                all_metrics.append(mem_df)

                net_df = self.get_network_traffic(instance_id, days, region)
                net_df['instance_id'] = instance_id
                net_df['metric_name'] = 'network_traffic'
                all_metrics.append(net_df)
            except Exception as e:
                print(f"Error collecting metrics for {instance_id}: {e}")

        return pd.concat(all_metrics, ignore_index=True) if all_metrics else pd.DataFrame()
