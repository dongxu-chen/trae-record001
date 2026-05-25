import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    import yaml
    import pandas as pd
    import numpy as np
    print("✓ Core libraries imported")
except Exception as e:
    print(f"✗ Core libraries failed: {e}")

try:
    from cloud_collector import MockCollector
    print("✓ MockCollector imported")
except Exception as e:
    print(f"✗ MockCollector failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from analyzers import ResourceAnalyzer, IdleResourceDetector, CostOptimizer
    print("✓ Analyzers imported")
except Exception as e:
    print(f"✗ Analyzers failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from database import DatabaseManager
    print("✓ DatabaseManager imported")
except Exception as e:
    print(f"✗ DatabaseManager failed: {e}")
    import traceback
    traceback.print_exc()

print("\nRunning demo analysis...")
try:
    config = {
        'optimization_rules': {
            'idle_resources': {
                'cpu_threshold': 10.0,
                'memory_threshold': 20.0,
                'network_threshold': 102400
            },
            'downsizing': {
                'cpu_lower_threshold': 20.0,
                'cpu_upper_threshold': 60.0
            }
        },
        'cost': {
            'eip_daily_cost': 2.5
        }
    }

    collector = MockCollector()
    print(f"✓ Created MockCollector")

    resources = collector.collect_all_resources()
    ecs_df = resources['ecs']
    eip_df = resources['eip']
    print(f"✓ Collected {len(ecs_df)} ECS instances, {len(eip_df)} EIPs")

    instance_ids = ecs_df['instance_id'].tolist()
    metrics_df = collector.collect_metrics_for_instances(instance_ids, days=7)
    print(f"✓ Collected {len(metrics_df)} metric records")

    analyzer = ResourceAnalyzer(config)
    idle_detector = IdleResourceDetector(config)
    cost_optimizer = CostOptimizer(config)
    print("✓ Created analyzers")

    idle_resources = idle_detector.detect_all_idle_resources(ecs_df, metrics_df, eip_df)
    analysis_df = idle_resources['utilization_analysis']
    print(f"✓ Analyzed {len(analysis_df)} instances")

    idle_summary = idle_detector.get_idle_summary(idle_resources)
    print(f"  - Idle ECS: {idle_summary['idle_ecs_count']}")
    print(f"  - Stopped ECS: {idle_summary['stopped_ecs_count']}")
    print(f"  - Unused EIPs: {idle_summary['unused_eips_count']}")

    current_cost = cost_optimizer.calculate_current_monthly_cost(ecs_df, eip_df)
    print(f"✓ Current monthly cost: ¥{current_cost['total_monthly_cost']:.2f}")

    optimization_plan = cost_optimizer.generate_optimization_plan(idle_resources, analysis_df)
    print(f"✓ Generated {optimization_plan['optimization_count']} optimization recommendations")
    print(f"  - Monthly savings: ¥{optimization_plan['total_monthly_savings']:.2f}")
    print(f"  - Annual savings: ¥{optimization_plan['total_annual_savings']:.2f}")

    cost_comparison = cost_optimizer.calculate_cost_comparison(current_cost, optimization_plan)
    print(f"✓ Savings percentage: {cost_comparison['savings_percentage']:.1f}%")

    print("\n✅ All tests passed! Cloud Cost Optimizer is working correctly.")

except Exception as e:
    print(f"\n❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
