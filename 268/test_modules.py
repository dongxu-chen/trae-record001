import sys
sys.path.insert(0, 'd:\\Trae\\project\\record001\\268')

print('Testing imports...')

from cloud_collector import MockCollector
from analyzers import ResourceAnalyzer, IdleResourceDetector, CostOptimizer
from analyzers import SpotInstanceAnalyzer, WorkloadType
from analyzers import ResourcePacker, InstanceSpec
from analyzers import MultiCloudComparer, CloudProvider
from database import DatabaseManager
from webhook_manager import WebhookManager

print('All imports successful!')

import yaml
with open('d:\\Trae\\project\\record001\\268\\config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print(f'Spot instances enabled: {config.get("spot_instances", {}).get("enabled", False)}')
print(f'Resource packing enabled: {config.get("resource_packing", {}).get("enabled", False)}')
print(f'Multi cloud enabled: {config.get("multi_cloud", {}).get("enabled", False)}')
print('Config loaded successfully!')

print('\nRunning full analysis...')
collector = MockCollector(config['cloud_providers']['aliyun'])
resources = collector.collect_all_resources()
ecs_df = resources['ecs']
eip_df = resources['eip']

instance_ids = ecs_df['instance_id'].tolist()
metrics_df = collector.collect_metrics_for_instances(instance_ids, days=7)

print(f'Collected {len(ecs_df)} ECS instances')
print(f'Collected {len(metrics_df)} metric records')

analyzer = ResourceAnalyzer(config)
idle_detector = IdleResourceDetector(config)
cost_optimizer = CostOptimizer(config)
spot_analyzer = SpotInstanceAnalyzer(config)
resource_packer = ResourcePacker(config)
cloud_comparer = MultiCloudComparer(config)

idle_resources = idle_detector.detect_all_idle_resources(ecs_df, metrics_df, eip_df)
analysis_df = idle_resources['utilization_analysis']

print(f'\nIdle ECS: {len(idle_resources["idle_ecs"])}')
print(f'Unused EIP: {len(idle_resources["unused_eips"])}')

spot_df = spot_analyzer.analyze_spot_candidates(analysis_df, metrics_df)
spot_summary = spot_analyzer.get_spot_summary(spot_df)
print(f'Spot candidates: {spot_summary["recommended_count"]}')
print(f'Spot savings: ¥{spot_summary["total_monthly_savings"]:.2f}')

packing_results = resource_packer.optimize_by_family(ecs_df, analysis_df)
packing_summary = resource_packer.get_packing_summary(packing_results)
print(f'Packing bins: {packing_summary["total_bins"]}')
print(f'Packing savings: ¥{packing_summary["total_monthly_savings"]:.2f}')

workload_types = dict(zip(
    spot_df['instance_id'],
    spot_df['workload_type']
)) if not spot_df.empty else {}

migration_results = cloud_comparer.analyze_portfolio(
    ecs_df, analysis_df, workload_types
)
print(f'Migration candidates: {migration_results["migration_candidate_count"]}')
print(f'Migration savings: ¥{migration_results["total_monthly_savings"]:.2f}')

print('\n=== All tests passed! ===')
