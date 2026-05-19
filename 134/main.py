import argparse
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from deadlock_analyzer import DeadlockAnalyzer
from sql_fingerprint import SQLFingerprint
from dependency_graph import DependencyGraph
from deadlock_report import DeadlockReport
from auto_kill import AutoKillManager
from trend_analyzer import TrendAnalyzer
from slow_sql_analyzer import SlowSQLAnalyzer
from deadlock_predictor import DeadlockPredictor
from dingtalk_alert import DingTalkAlerter
from ebpf_deadlock_detector import EBPFDeadlockDetector

def run_ebpf_detector():
    print("=" * 60)
    print("🔍 启动eBPF无侵入死锁检测器")
    print("=" * 60)
    print()
    print("⚠️  注意: 运行此命令需要root权限和以下依赖:")
    print("   - bcc (BPF Compiler Collection)")
    print("   - Linux kernel 4.15+ with eBPF support")
    print("   - psutil")
    print("   - prometheus_client (可选，用于指标输出)")
    print()
    
    detector = EBPFDeadlockDetector()
    try:
        detector.start()
        print("\n📊 检测器运行中，按 Ctrl+C 停止...\n")
        while True:
            import time
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n正在停止检测器...")
    finally:
        detector.stop()

def analyze_deadlock():
    print("=" * 60)
    print("🔍 开始分析数据库死锁...")
    print("=" * 60)
    
    analyzer = DeadlockAnalyzer()
    deadlock_data = analyzer.analyze_current_deadlock()
    
    if deadlock_data:
        print(f"✅ 发现死锁! 时间: {deadlock_data['timestamp']}")
        print(f"✅ 涉及事务数: {len(deadlock_data['transactions'])}")
        
        for i, txn in enumerate(deadlock_data['transactions'], 1):
            print(f"\n{'='*40}")
            print(f"事务 {i}:")
            print(f"  ID: {txn.get('transaction_id')}")
            print(f"  线程: {txn.get('thread_id')}")
            print(f"  持有锁: {len(txn.get('holds', []))}个")
            
            waiting = txn.get('waiting_for')
            if waiting:
                print(f"  等待锁: {waiting.get('mode')} on {waiting.get('table')}")
            
            print(f"\n  执行SQL:")
            for sql in txn.get('queries', []):
                print(f"    → {sql[:100]}{'...' if len(sql) > 100 else ''}")
            
            print(f"\n  持有锁详情:")
            for hold in txn.get('holds', []):
                print(f"    → {hold.get('mode')} on {hold.get('table')} (索引: {hold.get('index', 'N/A')})")
        
        report = DeadlockReport()
        report.add_deadlock(deadlock_data)
        print(f"\n✅ 死锁记录已保存到历史")
        
        graph = DependencyGraph()
        graph.build_graph_from_deadlock(deadlock_data)
        graph_file = graph.generate_html_svg()
        print(f"✅ 交互式依赖图已生成: {graph_file}")
        
        alerter = DingTalkAlerter()
        if alerter.enabled:
            alert_result = alerter.alert_deadlock(deadlock_data)
            if alert_result:
                print("✅ 钉钉告警已发送")
        
        return deadlock_data
    else:
        print("❌ 当前没有检测到死锁")
        return None

def generate_fingerprint(sql):
    fingerprint = SQLFingerprint()
    result = fingerprint.generate_fingerprint(sql)
    sql_hash = fingerprint.generate_hash(sql)
    tables = fingerprint.extract_tables(sql)
    qtype = fingerprint.classify_query_type(sql)
    
    print("=" * 60)
    print("🔑 SQL指纹分析结果")
    print("=" * 60)
    print(f"原始SQL: {sql}")
    print(f"\nSQL指纹: {result}")
    print(f"哈希值: {sql_hash}")
    print(f"查询类型: {qtype}")
    print(f"涉及表: {', '.join(tables) if tables else '无'}")

def generate_dependency_graph(use_sample=False):
    graph = DependencyGraph()
    
    if use_sample:
        print("📝 使用示例死锁数据生成依赖图")
        sample_deadlock = {
            'transactions': [
                {
                    'transaction_id': '12345',
                    'thread_id': '100',
                    'queries': ['UPDATE users SET name = ? WHERE id = 1'],
                    'holds': [
                        {'type': 'RECORD', 'mode': 'X', 'table': 'users', 'index': 'PRIMARY'}
                    ],
                    'waiting_for': {
                        'type': 'RECORD', 'mode': 'X', 'table': 'orders', 'index': 'PRIMARY'}
                },
                {
                    'transaction_id': '12346',
                    'thread_id': '101',
                    'queries': ['UPDATE orders SET status = ? WHERE id = 100'],
                    'holds': [
                        {'type': 'RECORD', 'mode': 'X', 'table': 'orders', 'index': 'PRIMARY'}
                    ],
                    'waiting_for': {
                        'type': 'RECORD', 'mode': 'X', 'table': 'users', 'index': 'PRIMARY'}
                },
                {
                    'transaction_id': '12347',
                    'thread_id': '102',
                    'queries': ['SELECT * FROM products WHERE id = 1'],
                    'holds': [
                        {'type': 'RECORD', 'mode': 'S', 'table': 'products', 'index': 'PRIMARY'}
                    ],
                    'waiting_for': None
                }
            ]
        }
        graph.build_graph_from_deadlock(sample_deadlock)
    else:
        analyzer = DeadlockAnalyzer()
        deadlock_data = analyzer.analyze_current_deadlock()
        if deadlock_data:
            graph.build_graph_from_deadlock(deadlock_data)
        else:
            print("❌ 没有死锁数据可生成依赖图，请使用 --use-sample 参数使用示例数据")
            return
    
    output_file = graph.generate_html_svg()
    print(f"✅ 交互式依赖图已生成: {output_file}")
    print("📌 请在浏览器中打开该文件查看可视化依赖关系")

def generate_report():
    report = DeadlockReport()
    output_file = report.generate_html_report()
    
    stats = report.get_statistics()
    print("=" * 60)
    print("📊 死锁报告统计")
    print("=" * 60)
    print(f"总死锁次数: {stats['total_deadlocks']}")
    print(f"涉及表数: {len(stats['table_counts'])}")
    for table, count in stats['table_counts'].items():
        print(f"  - {table}: {count}次")
    print(f"\n✅ HTML报告已生成: {output_file}")
    print("📌 请在浏览器中打开该文件查看详细报告")

def add_sample_deadlock():
    sample_deadlock = {
        'timestamp': '2024-01-15T10:30:00',
        'transactions': [
            {
                'transaction_id': '12345',
                'thread_id': '100',
                'queries': [
                    'UPDATE users SET name = ? WHERE id = 1',
                    'SELECT * FROM orders WHERE user_id = 1'
                ],
                'holds': [
                    {'type': 'RECORD', 'mode': 'X', 'table': 'users', 'index': 'PRIMARY'}
                ],
                'waiting_for': {
                    'type': 'RECORD', 'mode': 'X', 'table': 'orders', 'index': 'PRIMARY'
                }
            },
            {
                'transaction_id': '12346',
                'thread_id': '101',
                'queries': [
                    'UPDATE orders SET status = ? WHERE id = 100',
                    'SELECT * FROM users WHERE id = 1'
                ],
                'holds': [
                    {'type': 'RECORD', 'mode': 'X', 'table': 'orders', 'index': 'PRIMARY'}
                ],
                'waiting_for': {
                    'type': 'RECORD', 'mode': 'X', 'table': 'users', 'index': 'PRIMARY'
                }
            }
        ],
        'raw_log': 'Sample deadlock log for testing'
    }
    
    report = DeadlockReport()
    report.add_deadlock(sample_deadlock)
    print("✅ 已添加示例死锁数据到历史记录")

def run_auto_kill_diagnostics():
    manager = AutoKillManager()
    manager.run_diagnostics()

def run_auto_kill():
    manager = AutoKillManager()
    print("=" * 60)
    print("⚡ 执行自动终止检查...")
    print("=" * 60)
    
    killed_blocking = manager.check_and_kill_blocking()
    killed_long = manager.check_and_kill_long_running()
    
    killed_count = len(killed_blocking) + len(killed_long)
    
    if killed_count > 0:
        killed_threads = [k.get('blocking_thread_id') for k in killed_blocking] + [k.get('thread_id') for k in killed_long]
        alerter = DingTalkAlerter()
        if alerter.enabled:
            alerter.alert_auto_kill(killed_threads, f"阻塞事务超时（阈值: {manager.threshold_seconds}s）")
        
        print(f"\n✅ 完成: 终止了 {killed_count} 个事务")
    else:
        print("\n✅ 没有需要终止的事务")

def kill_transaction(thread_id):
    manager = AutoKillManager()
    manager.kill_transaction(thread_id, "手动指定终止")

def show_status():
    print("=" * 60)
    print("📈 数据库死锁诊断器状态")
    print("=" * 60)
    
    analyzer = DeadlockAnalyzer()
    report = DeadlockReport()
    auto_kill = AutoKillManager()
    
    stats = report.get_statistics()
    
    print(f"\n📊 历史数据:")
    print(f"  总死锁记录: {stats['total_deadlocks']}")
    print(f"  涉及表: {', '.join(stats['table_counts'].keys()) if stats['table_counts'] else '无'}")
    
    print(f"\n⚙️ 自动终止配置:")
    print(f"  状态: {'启用' if auto_kill.enabled else '禁用'}")
    print(f"  阈值: {auto_kill.threshold_seconds}秒")
    print(f"  排除用户: {', '.join(auto_kill.exclude_users)}")
    
    print(f"\n📁 输出文件:")
    print(f"  历史记录: deadlock_history.json")
    print(f"  依赖图: deadlock_dependency_graph.html")
    print(f"  报告: deadlock_report.html")
    print(f"  趋势报告: deadlock_trend_report.html")
    print(f"  预测报告: deadlock_prediction_report.html")

def analyze_trend():
    print("=" * 60)
    print("📈 死锁趋势分析")
    print("=" * 60)
    
    analyzer = TrendAnalyzer()
    stats = analyzer.calculate_statistics()
    heatmap = analyzer.analyze_heatmap_data()
    risk_periods = analyzer.get_risk_periods()
    
    print(f"\n📊 统计概览:")
    print(f"  总死锁次数: {stats['total']}")
    print(f"  日均死锁数: {stats['avg_daily']:.2f}")
    print(f"  近7天死锁数: {stats['recent_7_days']}")
    print(f"  趋势: {stats['trend']}")
    
    if risk_periods:
        print(f"\n⚠️ 高风险时段:")
        for period in risk_periods[:5]:
            print(f"  - {period['day']} {period['hour']}:00 ({period['count']}次)")
    
    output_file = analyzer.generate_trend_report()
    print(f"\n✅ 趋势报告已生成: {output_file}")

def analyze_slow_sql(log_file=None):
    print("=" * 60)
    print("🐢 慢查询分析")
    print("=" * 60)
    
    analyzer = SlowSQLAnalyzer()
    
    if log_file:
        print(f"📂 解析慢查询日志文件: {log_file}")
        slow_queries = analyzer.parse_slow_log_from_file(log_file)
    else:
        print("🗄️ 从数据库获取慢查询日志...")
        slow_queries = analyzer.get_slow_queries_from_db()
    
    if not slow_queries:
        print("❌ 未获取到慢查询数据")
        return
    
    print(f"✅ 解析到 {len(slow_queries)} 条慢查询")
    
    analysis = analyzer.analyze_slow_queries(slow_queries)
    
    print(f"\n📊 分析结果:")
    print(f"  平均查询时间: {analysis['avg_query_time']:.2f}秒")
    print(f"  SQL指纹数量: {len(analysis['fingerprint_stats'])}")
    
    if analysis['fingerprint_stats']:
        print(f"\n🔝 TOP SQL指纹:")
        for fp in analysis['fingerprint_stats'][:5]:
            print(f"  - 出现{fp['count']}次, 平均{fp['avg_query_time']:.2f}s: {fp['fingerprint'][:80]}...")
    
    output_file = analyzer.generate_report()
    print(f"\n✅ 慢查询报告已生成: {output_file}")

def predict_deadlock(train=False):
    print("=" * 60)
    print("🔮 死锁预测分析")
    print("=" * 60)
    
    predictor = DeadlockPredictor()
    report = DeadlockReport()
    history = report.get_history()
    
    if train and len(history) >= 10:
        print("🎯 开始训练预测模型...")
        metrics = predictor.train_model(history)
        if metrics:
            print(f"✅ 模型训练完成!")
            print(f"   准确率: {metrics['accuracy']:.2%}")
            print(f"   精确率: {metrics['precision']:.2%}")
            print(f"   召回率: {metrics['recall']:.2%}")
            print(f"   F1分数: {metrics['f1']:.2%}")
    elif train:
        print("⚠️ 历史数据不足（需要至少10条），跳过模型训练")
    
    prediction = predictor.predict(history)
    
    risk_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}
    print(f"\n📊 预测结果:")
    print(f"  风险等级: {risk_emoji[prediction['risk_level']]} {prediction['risk_level'].upper()}")
    print(f"  风险概率: {prediction['probability']:.1%}")
    print(f"  预测方法: {prediction['method']}")
    
    print(f"\n💡 风险因素:")
    explanations = predictor.get_prediction_explanation(prediction)
    for exp in explanations:
        print(f"  - {exp}")
    
    if prediction['risk_level'] == 'high':
        alerter = DingTalkAlerter()
        if alerter.enabled:
            alerter.alert_high_risk_prediction(prediction)
            print("✅ 高风险预警已发送到钉钉")
    
    output_file = predictor.generate_prediction_report(history)
    print(f"\n✅ 预测报告已生成: {output_file}")

def send_test_alert():
    print("=" * 60)
    print("🔔 发送测试钉钉告警")
    print("=" * 60)
    
    alerter = DingTalkAlerter()
    if not alerter.enabled:
        print("⚠️ 钉钉告警功能未启用，请在.env中配置 DINGTALK_ENABLED=true")
        return
    
    test_data = {
        'timestamp': '2024-01-15T10:30:00',
        'transactions': [
            {'transaction_id': '12345', 'thread_id': '100'},
            {'transaction_id': '12346', 'thread_id': '101'}
        ]
    }
    
    result = alerter.alert_deadlock(test_data)
    if result:
        print("✅ 测试告警发送成功!")
    else:
        print("❌ 测试告警发送失败!")

def full_analysis():
    print("=" * 60)
    print("🚀 执行完整死锁分析流程")
    print("=" * 60)
    
    print("\n[1/6] 分析当前死锁...")
    deadlock_data = analyze_deadlock()
    
    print("\n[2/6] 生成趋势分析报告...")
    analyze_trend()
    
    print("\n[3/6] 死锁风险预测...")
    predict_deadlock()
    
    print("\n[4/6] 分析慢查询...")
    try:
        analyze_slow_sql()
    except Exception as e:
        print(f"⚠️ 慢查询分析跳过: {e}")
    
    print("\n[5/6] 事务阻塞诊断...")
    run_auto_kill_diagnostics()
    
    print("\n[6/6] 生成完整报告...")
    generate_report()
    
    print("\n" + "=" * 60)
    print("✅ 完整分析流程已完成!")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(
        description='🔐 数据库死锁自动诊断器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py analyze                           # 分析当前死锁
  python main.py fingerprint "SELECT * FROM users WHERE id = 1"  # 生成SQL指纹
  python main.py graph --use-sample                # 使用示例数据生成依赖图
  python main.py report                            # 生成历史死锁报告
  python main.py add-sample                        # 添加示例死锁数据
  python main.py status                            # 显示诊断器状态
  python main.py trend                             # 生成死锁趋势分析报告
  python main.py slow-sql                          # 分析慢查询日志
  python main.py predict                           # 死锁风险预测
  python main.py predict --train                   # 训练预测模型并预测
  python main.py test-alert                        # 发送测试钉钉告警
  python main.py auto-kill --diagnose              # 诊断事务状态
  python main.py auto-kill --execute               # 执行自动终止
  python main.py full                              # 执行完整分析流程
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    subparsers.add_parser('analyze', help='分析当前死锁')
    
    fingerprint_parser = subparsers.add_parser('fingerprint', help='生成SQL指纹')
    fingerprint_parser.add_argument('sql', help='要分析的SQL语句')
    
    graph_parser = subparsers.add_parser('graph', help='生成死锁依赖图')
    graph_parser.add_argument('--use-sample', action='store_true', help='使用示例数据生成依赖图')
    
    subparsers.add_parser('report', help='生成历史死锁报告')
    
    subparsers.add_parser('add-sample', help='添加示例死锁数据')
    
    subparsers.add_parser('status', help='显示诊断器状态')
    
    auto_kill_parser = subparsers.add_parser('auto-kill', help='自动终止阻塞事务')
    auto_kill_group = auto_kill_parser.add_mutually_exclusive_group()
    auto_kill_group.add_argument('--diagnose', action='store_true', help='仅诊断，不执行终止')
    auto_kill_group.add_argument('--execute', action='store_true', help='执行自动终止')
    auto_kill_parser.add_argument('--kill', type=int, help='终止指定的线程ID')
    
    subparsers.add_parser('trend', help='生成死锁趋势分析报告')
    
    slow_sql_parser = subparsers.add_parser('slow-sql', help='分析慢查询日志')
    slow_sql_parser.add_argument('--log-file', help='慢查询日志文件路径')
    
    predict_parser = subparsers.add_parser('predict', help='死锁风险预测')
    predict_parser.add_argument('--train', action='store_true', help='训练预测模型')
    
    subparsers.add_parser('test-alert', help='发送测试钉钉告警')
    
    ebpf_parser = subparsers.add_parser('ebpf', help='启动eBPF无侵入死锁检测器')
    ebpf_parser.add_argument('--pid', type=int, nargs='*', help='指定监控的MySQL PID(可多个)')
    ebpf_parser.add_argument('--no-mysql-filter', action='store_true', help='不过滤MySQL进程，监控所有进程')
    ebpf_parser.add_argument('--stats-interval', type=int, default=10, help='打印统计信息的间隔(秒)')
    
    subparsers.add_parser('full', help='执行完整分析流程')
    
    args = parser.parse_args()
    
    if args.command == 'analyze':
        analyze_deadlock()
    
    elif args.command == 'fingerprint':
        generate_fingerprint(args.sql)
    
    elif args.command == 'graph':
        generate_dependency_graph(args.use_sample)
    
    elif args.command == 'report':
        generate_report()
    
    elif args.command == 'add-sample':
        add_sample_deadlock()
    
    elif args.command == 'status':
        show_status()
    
    elif args.command == 'auto-kill':
        if args.diagnose:
            run_auto_kill_diagnostics()
        elif args.execute:
            run_auto_kill()
        elif args.kill:
            kill_transaction(args.kill)
        else:
            run_auto_kill_diagnostics()
    
    elif args.command == 'trend':
        analyze_trend()
    
    elif args.command == 'slow-sql':
        analyze_slow_sql(args.log_file)
    
    elif args.command == 'predict':
        predict_deadlock(args.train)
    
    elif args.command == 'test-alert':
        send_test_alert()
    
    elif args.command == 'ebpf':
        run_ebpf_detector()
    
    elif args.command == 'full':
        full_analysis()
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
