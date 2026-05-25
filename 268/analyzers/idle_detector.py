import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta
from .resource_analyzer import ResourceAnalyzer


class IdleResourceDetector:
    def __init__(self, config: Dict):
        self.config = config
        self.rules = config.get('optimization_rules', {})
        self.analyzer = ResourceAnalyzer(config)

    def detect_idle_ecs(self, analysis_df: pd.DataFrame) -> pd.DataFrame:
        if analysis_df.empty:
            return pd.DataFrame()

        cpu_threshold = self.rules.get('idle_resources', {}).get('cpu_threshold', 10.0)
        mem_threshold = self.rules.get('idle_resources', {}).get('memory_threshold', 20.0)
        net_threshold = self.rules.get('idle_resources', {}).get('network_threshold', 102400)

        running_df = analysis_df[analysis_df['status'] == 'Running'].copy()
        
        idle_mask = (
            (running_df['cpu_avg'] < cpu_threshold) &
            (running_df['cpu_p95'] < cpu_threshold * 2) &
            (running_df['memory_avg'] < mem_threshold) &
            (running_df['network_avg'] < net_threshold)
        )

        idle_instances = running_df[idle_mask].copy()
        
        if not idle_instances.empty:
            idle_instances['idle_score'] = self._calculate_idle_score(idle_instances)
            idle_instances['recommendation'] = 'release'
            idle_instances['reason'] = idle_instances.apply(
                lambda x: f"CPU avg: {x['cpu_avg']:.1f}% (threshold: {cpu_threshold}%), "
                         f"Memory avg: {x['memory_avg']:.1f}% (threshold: {mem_threshold}%)",
                axis=1
            )

        return idle_instances

    def detect_low_utilization_ecs(self, analysis_df: pd.DataFrame) -> pd.DataFrame:
        if analysis_df.empty:
            return pd.DataFrame()

        cpu_lower = self.rules.get('downsizing', {}).get('cpu_lower_threshold', 20.0)
        cpu_upper = self.rules.get('downsizing', {}).get('cpu_upper_threshold', 60.0)

        running_df = analysis_df[analysis_df['status'] == 'Running'].copy()
        
        low_util_mask = (
            (running_df['cpu_avg'] >= cpu_lower) &
            (running_df['cpu_avg'] < cpu_upper)
        )

        low_util_instances = running_df[low_util_mask].copy()
        
        if not low_util_instances.empty:
            low_util_instances['recommendation'] = 'monitor'
            low_util_instances['reason'] = f"CPU utilization between {cpu_lower}%-{cpu_upper}%"

        return low_util_instances

    def detect_high_utilization_ecs(self, analysis_df: pd.DataFrame) -> pd.DataFrame:
        if analysis_df.empty:
            return pd.DataFrame()

        cpu_upper = self.rules.get('downsizing', {}).get('cpu_upper_threshold', 60.0)

        running_df = analysis_df[analysis_df['status'] == 'Running'].copy()
        
        high_util_mask = running_df['cpu_avg'] >= cpu_upper

        high_util_instances = running_df[high_util_mask].copy()
        
        if not high_util_instances.empty:
            high_util_instances['recommendation'] = 'upgrade'
            high_util_instances['reason'] = high_util_instances.apply(
                lambda x: f"High CPU utilization: {x['cpu_avg']:.1f}% (threshold: {cpu_upper}%)",
                axis=1
            )

        return high_util_instances

    def detect_unused_eips(self, eip_df: pd.DataFrame) -> pd.DataFrame:
        if eip_df.empty:
            return pd.DataFrame()

        unused_eips = eip_df[eip_df['status'] != 'InUse'].copy()
        
        if not unused_eips.empty:
            unused_eips['idle_days'] = unused_eips['creation_time'].apply(
                lambda x: (pd.Timestamp.now() - pd.to_datetime(x).tz_localize(None)).days if pd.notna(x) else 0
            )
            unused_eips['recommendation'] = 'release'
            unused_eips['reason'] = 'EIP is not bound to any instance'

        return unused_eips

    def detect_stopped_instances(self, instances_df: pd.DataFrame) -> pd.DataFrame:
        if instances_df.empty:
            return pd.DataFrame()

        stopped_df = instances_df[
            instances_df['status'].isin(['Stopped', 'stopped', 'Stopping'])
        ].copy()

        if not stopped_df.empty:
            stopped_df['stopped_days'] = stopped_df['creation_time'].apply(
                lambda x: (pd.Timestamp.now() - pd.to_datetime(x).tz_localize(None)).days if pd.notna(x) else 0
            )
            stopped_df['recommendation'] = 'release'
            stopped_df['reason'] = 'Instance is stopped for a long time'

        return stopped_df

    def _calculate_idle_score(self, instances_df: pd.DataFrame) -> pd.Series:
        cpu_threshold = self.rules.get('idle_resources', {}).get('cpu_threshold', 10.0)
        mem_threshold = self.rules.get('idle_resources', {}).get('memory_threshold', 20.0)

        cpu_score = 1 - (instances_df['cpu_avg'] / (cpu_threshold * 3)).clip(0, 1)
        mem_score = 1 - (instances_df['memory_avg'] / (mem_threshold * 3)).clip(0, 1)
        
        combined_score = (cpu_score * 0.6 + mem_score * 0.4) * 100
        return combined_score.round(2)

    def detect_all_idle_resources(self, instances_df: pd.DataFrame,
                                   metrics_df: pd.DataFrame,
                                   eip_df: pd.DataFrame) -> Dict:
        analysis_df = self.analyzer.analyze_all_instances(instances_df, metrics_df)

        idle_ecs = self.detect_idle_ecs(analysis_df)
        low_util_ecs = self.detect_low_utilization_ecs(analysis_df)
        high_util_ecs = self.detect_high_utilization_ecs(analysis_df)
        stopped_ecs = self.detect_stopped_instances(instances_df)
        unused_eips = self.detect_unused_eips(eip_df)

        return {
            'idle_ecs': idle_ecs,
            'low_utilization_ecs': low_util_ecs,
            'high_utilization_ecs': high_util_ecs,
            'stopped_ecs': stopped_ecs,
            'unused_eips': unused_eips,
            'utilization_analysis': analysis_df
        }

    def get_idle_summary(self, idle_resources: Dict) -> Dict:
        return {
            'idle_ecs_count': len(idle_resources['idle_ecs']),
            'low_util_ecs_count': len(idle_resources['low_utilization_ecs']),
            'high_util_ecs_count': len(idle_resources['high_utilization_ecs']),
            'stopped_ecs_count': len(idle_resources['stopped_ecs']),
            'unused_eips_count': len(idle_resources['unused_eips']),
            'total_optimization_candidates': (
                len(idle_resources['idle_ecs']) +
                len(idle_resources['stopped_ecs']) +
                len(idle_resources['unused_eips'])
            )
        }
