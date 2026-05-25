import yaml
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

from cloud_collector import MockCollector, AliyunCollector, AWSCollector
from analyzers import ResourceAnalyzer, IdleResourceDetector, CostOptimizer
from database import DatabaseManager


def load_config(config_path='config.yaml'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
    return None


def get_collector(config, provider='mock'):
    if provider == 'aliyun':
        return AliyunCollector(config['cloud_providers']['aliyun'])
    elif provider == 'aws':
        return AWSCollector(config['cloud_providers']['aws'])
    else:
        return MockCollector()


def run_full_analysis(config, collector, db=None):
    print("="*60)
    print("云成本优化工具 - 完整分析报告")
    print("="*60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("1. 收集云资源数据...")
    resources = collector.collect_all_resources()
    ecs_df = resources['ecs']
    eip_df = resources['eip']
    
    print(f"   - ECS实例数量: {len(ecs_df)}")
    print(f"   - EIP数量: {len(eip_df)}")
    print()

    print("2. 收集监控指标数据...")
    instance_ids = ecs_df['instance_id'].tolist()
    metrics_df = collector.collect_metrics_for_instances(instance_ids, days=7)
    print(f"   - 收集了 {len(metrics_df)} 条指标记录")
    print()

    print("3. 分析资源利用率...")
    analyzer = ResourceAnalyzer(config)
    idle_detector = IdleResourceDetector(config)
    cost_optimizer = CostOptimizer(config)
    
    idle_resources = idle_detector.detect_all_idle_resources(ecs_df, metrics_df, eip_df)
    analysis_df = idle_resources['utilization_analysis']
    
    summary = analyzer.get_utilization_summary(analysis_df)
    print(f"   - 运行中实例平均CPU利用率: {summary['avg_cpu_utilization']:.1f}%")
    print(f"   - 运行中实例平均内存利用率: {summary['avg_memory_utilization']:.1f}%")
    print(f"   - 高CPU实例数: {summary['high_cpu_count']}")
    print(f"   - 低CPU实例数: {summary['low_cpu_count']}")
    print()

    print("4. 检测闲置资源...")
    idle_summary = idle_detector.get_idle_summary(idle_resources)
    print(f"   - 闲置ECS实例: {idle_summary['idle_ecs_count']} 个")
    print(f"   - 已停止ECS实例: {idle_summary['stopped_ecs_count']} 个")
    print(f"   - 未使用EIP: {idle_summary['unused_eips_count']} 个")
    print(f"   - 低利用率ECS实例: {idle_summary['low_util_ecs_count']} 个")
    print()

    print("5. 计算当前成本...")
    current_cost = cost_optimizer.calculate_current_monthly_cost(ecs_df, eip_df)
    cost_breakdown = cost_optimizer.get_cost_breakdown(ecs_df, eip_df)
    print(f"   - 月度总成本: ¥{current_cost['total_monthly_cost']:.2f}")
    print(f"   - ECS月度成本: ¥{current_cost['ecs_monthly_cost']:.2f}")
    print(f"   - EIP月度成本: ¥{current_cost['eip_monthly_cost']:.2f}")
    print()

    print("6. 生成优化方案...")
    optimization_plan = cost_optimizer.generate_optimization_plan(idle_resources, analysis_df)
    print(f"   - 优化项数量: {optimization_plan['optimization_count']}")
    print(f"   - 月度节省: ¥{optimization_plan['total_monthly_savings']:.2f}")
    print(f"   - 年度节省: ¥{optimization_plan['total_annual_savings']:.2f}")
    print()

    print("7. 成本对比分析...")
    cost_comparison = cost_optimizer.calculate_cost_comparison(current_cost, optimization_plan)
    print(f"   - 当前月度成本: ¥{cost_comparison['current_monthly_cost']:.2f}")
    print(f"   - 优化后月度成本: ¥{cost_comparison['optimized_monthly_cost']:.2f}")
    print(f"   - 月度节省: ¥{cost_comparison['monthly_savings']:.2f}")
    print(f"   - 节省比例: {cost_comparison['savings_percentage']:.1f}%")
    print()

    print("8. 优化建议详情:")
    print("-" * 60)
    
    release_recs = optimization_plan['release_recommendations']
    if not release_recs.empty:
        print("\n   释放建议:")
        for _, rec in release_recs.iterrows():
            print(f"   - [{rec['resource_type']}] {rec['resource_name']} "
                  f"(节省: ¥{rec['monthly_savings']:.2f}/月")
            print(f"     原因: {rec['reason']}")
    
    downsize_recs = optimization_plan['downsizing_recommendations']
    if not downsize_recs.empty:
        print("\n   降配建议:")
        for _, rec in downsize_recs.iterrows():
            print(f"   - [{rec['resource_type']}] {rec['resource_name']} "
                  f"(节省: ¥{rec['monthly_savings']:.2f}/月)")
            print(f"     详情: {rec.get('details', '')}")
    
    print()
    print("="*60)

    if db:
        print("9. 创建优化审批请求...")
        all_recs = optimization_plan['all_recommendations']
        if not all_recs.empty:
            request_ids = db.batch_create_requests(all_recs)
            print(f"   - 已创建 {len(request_ids)} 个优化请求")
        print()

    return {
        'ecs_df': ecs_df,
        'eip_df': eip_df,
        'metrics_df': metrics_df,
        'analysis_df': analysis_df,
        'idle_resources': idle_resources,
        'current_cost': current_cost,
        'optimization_plan': optimization_plan,
        'cost_comparison': cost_comparison
    }


def show_pending_requests(db):
    print("\n待审批的优化请求:")
    print("-" * 60)
    requests = db.get_all_requests(status='pending')
    if not requests:
        print("  暂无待审批请求")
        return
    
    for req in requests:
        print(f"  ID: {req.request_id}")
        print(f"  资源: {req.resource_type} - {req.resource_name}")
        print(f"  操作: {req.action}")
        print(f"  月度节省: ¥{req.monthly_savings:.2f}")
        print(f"  原因: {req.reason}")
        print()


def export_report(results, output_dir='output'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    results['ecs_df'].to_csv(f'{output_dir}/ecs_instances_{timestamp}.csv', index=False)
    results['eip_df'].to_csv(f'{output_dir}/eip_addresses_{timestamp}.csv', index=False)
    results['analysis_df'].to_csv(f'{output_dir}/utilization_analysis_{timestamp}.csv', index=False)
    results['optimization_plan']['all_recommendations'].to_csv(
        f'{output_dir}/optimization_recommendations_{timestamp}.csv', index=False
    )
    
    with open(f'{output_dir}/cost_summary_{timestamp}.txt', 'w', encoding='utf-8') as f:
        f.write("云成本优化报告\n")
        f.write("="*50 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        cc = results['cost_comparison']
        f.write(f"当前月度成本: ¥{cc['current_monthly_cost']:.2f}\n")
        f.write(f"优化后月度成本: ¥{cc['optimized_monthly_cost']:.2f}\n")
        f.write(f"月度节省: ¥{cc['monthly_savings']:.2f}\n")
        f.write(f"年度节省: ¥{cc['annual_savings']:.2f}\n")
        f.write(f"节省比例: {cc['savings_percentage']:.1f}%\n")
    
    print(f"报告已导出到 {output_dir}/ 目录")


def main():
    parser = argparse.ArgumentParser(description='云成本优化工具')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--provider', default='mock', choices=['mock', 'aliyun', 'aws'], help='云服务商')
    parser.add_argument('--export', action='store_true', help='导出分析报告')
    parser.add_argument('--db', action='store_true', help='启用数据库')
    parser.add_argument('--show-requests', action='store_true', help='显示待审批请求')
    parser.add_argument('--api', action='store_true', help='启动API服务器')
    parser.add_argument('--port', type=int, default=5000, help='API端口')
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    if not config:
        print("无法加载配置文件")
        sys.exit(1)
    
    db = DatabaseManager() if args.db else None
    
    if args.show_requests and db:
        show_pending_requests(db)
        return
    
    if args.api:
        from api.app import app, run_analysis
        run_analysis()
        print(f"启动API服务器在端口 {args.port}")
        app.run(host='0.0.0.0', port=args.port, debug=True)
        return
    
    collector = get_collector(config, args.provider)
    results = run_full_analysis(config, collector, db)
    
    if args.export:
        export_report(results)
    
    if db:
        db.close()


if __name__ == '__main__':
    main()
