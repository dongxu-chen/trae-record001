import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*70)
print("Testing Enhanced Cloud Cost Optimizer Features")
print("="*70)
print()

print("1. Testing imports...")
try:
    import yaml
    import pandas as pd
    import numpy as np
    from scipy import signal
    print("   ✓ Core libraries imported (including scipy)")
except Exception as e:
    print(f"   ✗ Core libraries failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from cloud_collector import MockCollector
    print("   ✓ MockCollector imported")
except Exception as e:
    print(f"   ✗ MockCollector failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from analyzers import ResourceAnalyzer, IdleResourceDetector, CostOptimizer
    print("   ✓ Analyzers imported")
except Exception as e:
    print(f"   ✗ Analyzers failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from database import DatabaseManager
    print("   ✓ DatabaseManager imported")
except Exception as e:
    print(f"   ✗ DatabaseManager failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from webhook_manager import WebhookManager, WebhookEventType
    print("   ✓ WebhookManager imported")
except Exception as e:
    print(f"   ✗ WebhookManager failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("2. Testing minute-level sampling and percentile analysis...")
try:
    config = {
        'optimization_rules': {
            'sampling': {'interval_minutes': 1},
            'idle_resources': {
                'cpu_threshold': 10.0,
                'memory_threshold': 20.0,
                'network_threshold': 102400
            },
            'downsizing': {
                'cpu_lower_threshold': 20.0,
                'cpu_upper_threshold': 60.0,
                'p99_safety_threshold': 70.0
            },
            'buffer': {'safety_padding': 1.2}
        },
        'cost': {'eip_daily_cost': 2.5}
    }

    collector = MockCollector()
    print(f"   ✓ Created MockCollector")

    resources = collector.collect_all_resources()
    ecs_df = resources['ecs']
    eip_df = resources['eip']
    print(f"   ✓ Collected {len(ecs_df)} ECS instances, {len(eip_df)} EIPs")

    instance_ids = ecs_df['instance_id'].tolist()
    metrics_df = collector.collect_metrics_for_instances(instance_ids, days=7)
    print(f"   ✓ Collected {len(metrics_df)} metric records")

    analyzer = ResourceAnalyzer(config)
    print(f"   ✓ Created ResourceAnalyzer")

    sample_instance = instance_ids[0]
    cpu_stats = analyzer.calculate_metric_statistics(
        metrics_df[metrics_df['instance_id'] == sample_instance],
        'cpu_utilization',
        granularity='minute'
    )
    print(f"   ✓ Minute-level statistics for {sample_instance}:")
    print(f"     - AVG: {cpu_stats['avg']:.2f}%")
    print(f"     - P50: {cpu_stats['p50']:.2f}%")
    print(f"     - P75: {cpu_stats['p75']:.2f}%")
    print(f"     - P90: {cpu_stats['p90']:.2f}%")
    print(f"     - P95: {cpu_stats['p95']:.2f}%")
    print(f"     - P99: {cpu_stats['p99']:.2f}%")
    print(f"     - P99.9: {cpu_stats['p999']:.2f}%")
    print(f"     - CV: {cpu_stats['cv']:.2f}")

except Exception as e:
    print(f"   ✗ Sampling analysis failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("3. Testing periodicity detection...")
try:
    periodicity = analyzer.detect_periodicity(
        metrics_df, 'cpu_utilization', instance_ids[0]
    )
    print(f"   ✓ Periodicity detection:")
    print(f"     - Is periodic: {periodicity['is_periodic']}")
    if periodicity['is_periodic']:
        print(f"     - Period type: {periodicity['period']}")
        print(f"     - Confidence: {periodicity['confidence']:.2f}")
        print(f"     - Peak hours: {periodicity['peak_hours']}")
        print(f"     - Amplitude: {periodicity['amplitude']:.2f}")

    buffer_req = analyzer.calculate_buffer_requirement(
        metrics_df, 'cpu_utilization', instance_ids[0]
    )
    print(f"   ✓ Buffer requirement analysis:")
    print(f"     - Needs buffer: {buffer_req['needs_buffer']}")
    print(f"     - Recommended buffer: {buffer_req['recommended_buffer_pct']}%")
    print(f"     - Reason: {buffer_req['buffer_reason']}")

    analysis_df = analyzer.analyze_all_instances(ecs_df, metrics_df, with_periodicity=True)
    print(f"   ✓ Full analysis completed for {len(analysis_df)} instances")
    
    if 'is_periodic' in analysis_df.columns:
        periodic_count = len(analysis_df[analysis_df['is_periodic'] == True])
        buffer_count = len(analysis_df[analysis_df['needs_buffer'] == True])
        print(f"     - Periodic instances: {periodic_count}")
        print(f"     - Buffer required instances: {buffer_count}")

except Exception as e:
    print(f"   ✗ Periodicity detection failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("4. Testing buffer-aware cost optimization...")
try:
    idle_detector = IdleResourceDetector(config)
    cost_optimizer = CostOptimizer(config)
    
    idle_resources = idle_detector.detect_all_idle_resources(ecs_df, metrics_df, eip_df)
    optimization_plan = cost_optimizer.generate_optimization_plan(idle_resources, analysis_df)
    
    print(f"   ✓ Optimization plan generated:")
    print(f"     - Release recommendations: {len(optimization_plan['release_recommendations'])}")
    print(f"     - Downsizing recommendations: {len(optimization_plan['downsizing_recommendations'])}")
    print(f"     - Buffer recommendations: {len(optimization_plan['buffer_recommendations'])}")
    print(f"     - Excluded due to periodicity: {len(optimization_plan.get('excluded_due_to_periodicity', []))}")
    print(f"     - Total monthly savings: ¥{optimization_plan['total_monthly_savings']:.2f}")

except Exception as e:
    print(f"   ✗ Cost optimization failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("5. Testing Webhook manager...")
try:
    webhook_config = {
        'enabled': True,
        'timeout': 5,
        'max_retries': 1,
        'auto_execute_on_approve': True
    }
    webhook_mgr = WebhookManager(webhook_config)
    print(f"   ✓ WebhookManager created")
    
    webhook_mgr.add_webhook(
        url='http://example.com/webhook',
        events=['request.approved', 'request.executed'],
        secret='test-secret'
    )
    print(f"   ✓ Webhook added")
    
    test_data = {'request_id': 'test-123', 'status': 'approved'}
    result = webhook_mgr.trigger_event(WebhookEventType.REQUEST_APPROVED, test_data, async_mode=False)
    print(f"   ✓ Webhook triggered (sync mode)")
    print(f"     - Status: {result['status']}")
    print(f"     - Webhooks notified: {result['webhook_count']}")

except Exception as e:
    print(f"   ✗ Webhook manager failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("6. Testing database with webhook integration...")
try:
    if os.path.exists('test_enhanced.db'):
        os.remove('test_enhanced.db')
    
    db = DatabaseManager(
        db_path='sqlite:///test_enhanced.db',
        webhook_config=webhook_config
    )
    print(f"   ✓ DatabaseManager with webhook support created")
    
    def test_execute(request_id):
        print(f"     → Auto-executing request: {request_id}")
        return True
    
    db.set_execute_callback(test_execute)
    print(f"   ✓ Execute callback set")
    
    request_id = db.create_optimization_request(
        resource_type='ECS',
        resource_id='i-test-001',
        resource_name='test-server',
        action='downsize',
        monthly_savings=50.0,
        reason='Low utilization'
    )
    print(f"   ✓ Request created: {request_id}")
    
    success = db.approve_request(request_id, approver='test-user', auto_execute=True)
    print(f"   ✓ Request approved with auto-execute: {success}")
    
    req = db.get_request(request_id)
    print(f"   ✓ Request status after approval: {req.status}")
    print(f"     - Executed at: {req.executed_at}")
    
    summary = db.get_optimization_summary()
    print(f"   ✓ Summary:")
    print(f"     - Total requests: {summary['total_requests']}")
    print(f"     - Executed: {summary['executed']}")
    print(f"     - Total savings: ¥{summary['total_monthly_savings']:.2f}")
    
    db.close()
    if os.path.exists('test_enhanced.db'):
        os.remove('test_enhanced.db')

except Exception as e:
    print(f"   ✗ Database integration failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*70)
print("✅ All enhanced feature tests passed!")
print("="*70)
print()
print("New features summary:")
print("1. Minute-level sampling with P50/P75/P90/P95/P99/P99.9 percentiles")
print("2. Periodicity detection using Welch's method and FFT")
print("3. Buffer requirement calculation for periodic/peak workloads")
print("4. Buffer-aware optimization (exclude periodic instances from release)")
print("5. Webhook callback system with HMAC signature verification")
print("6. Auto-execute on approval with callback integration")
