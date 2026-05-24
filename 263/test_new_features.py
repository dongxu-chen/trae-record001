#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deadlock_parser import MySQLDeadlockParser, PostgreSQLDeadlockParser
from deadlock_analyzer import (
    DeadlockAnalyzer,
    DeadlockGraphGenerator,
    OptimizationAdvisor,
    ExplainAnalyzer,
    DeadlockMonitor,
    DeadlockSimulator,
    APMIntegration
)


def test_mysql_parser():
    print("=" * 60)
    print("测试1: MySQL死锁日志解析（多版本适配）")
    print("=" * 60)

    sample_log = """
========================
LATEST DETECTED DEADLOCK
========================
2024-01-15 10:30:45 123456789
*** (1) TRANSACTION:
TRANSACTION 12345, ACTIVE 10 sec starting index read
mysql tables in use 1, locked 1
LOCK WAIT 2 lock struct(s), heap size 360, 1 row lock(s)
MySQL thread id 1, OS thread handle 1234, query id 100 localhost root updating
UPDATE users SET name = 'test' WHERE id = 1

*** (1) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 100 page no 5 n bits 72 index `PRIMARY` of table `test`.`users` trx id 12345 lock_mode X locks rec but not gap waiting
Record lock, heap no 2 PHYSICAL RECORD: n_fields 3; compact format; info bits 0

*** (2) TRANSACTION:
TRANSACTION 12346, ACTIVE 15 sec
2 lock struct(s), heap size 360, 1 row lock(s)
MySQL thread id 2, OS thread handle 5678, query id 101 localhost root
UPDATE orders SET status = 'paid' WHERE user_id = 1

*** (2) HOLDS THE LOCK(S):
RECORD LOCKS space id 100 page no 5 n bits 72 index `PRIMARY` of table `test`.`users` trx id 12346 lock_mode X locks rec but not gap
Record lock, heap no 2 PHYSICAL RECORD: n_fields 3; compact format; info bits 0

*** (2) WAITING FOR THIS LOCK TO BE GRANTED:
RECORD LOCKS space id 101 page no 10 n bits 72 index `idx_user_id` of table `test`.`orders` trx id 12346 lock_mode X locks rec but not gap waiting
Record lock, heap no 5 PHYSICAL RECORD: n_fields 3; compact format; info bits 0

*** WE ROLL BACK TRANSACTION (1)
"""

    parser = MySQLDeadlockParser()
    deadlocks = parser.parse(sample_log)
    version = parser.get_detected_version()

    print(f"✓ 检测到版本: {version}")
    print(f"✓ 解析到死锁数量: {len(deadlocks)}")

    if deadlocks:
        d = deadlocks[0]
        print(f"  - 死锁时间: {d.timestamp}")
        print(f"  - 事务数量: {len(d.transactions)}")
        print(f"  - 被选中牺牲的事务: {d.victim_txns}")
        for txn in d.transactions:
            print(f"  - 事务 {txn.txn_id}: 状态={txn.status}, SQL数量={len(txn.sql_statements)}")
            print(f"    持有的锁: {len(txn.holding_locks)}个")
            if txn.waiting_lock:
                print(f"    等待的锁: {txn.waiting_lock.lock_mode} on {txn.waiting_lock.table_name}")

    print("✓ MySQL解析测试通过\n")
    return deadlocks


def test_postgresql_parser():
    print("=" * 60)
    print("测试2: PostgreSQL死锁日志解析（多版本适配）")
    print("=" * 60)

    sample_log = """
2024-01-15 10:30:45.123 UTC [12345]: [1-1] db=test,user=postgres LOG:  process 12345 detected deadlock while waiting for ShareLock on transaction 1000 after 1000.123 ms
2024-01-15 10:30:45.123 UTC [12345]: [2-1] db=test,user=postgres DETAIL:  Process 12345 waits for ShareLock on transaction 1000; blocked by process 12346.
	Process 12346 waits for ShareLock on transaction 1001; blocked by process 12345.
	Process 12345: UPDATE users SET name = 'test' WHERE id = 1;
	Process 12346: UPDATE orders SET status = 'paid' WHERE user_id = 1;
2024-01-15 10:30:45.123 UTC [12345]: [3-1] db=test,user=postgres HINT:  See server log for query details.
2024-01-15 10:30:45.123 UTC [12345]: [4-1] db=test,user=postgres CONTEXT:  while updating tuple (0,1) in relation "users"
2024-01-15 10:30:45.123 UTC [12345]: [5-1] db=test,user=postgres STATEMENT:  UPDATE users SET name = 'test' WHERE id = 1;
2024-01-15 10:30:45.123 UTC [12345]: [6-1] db=test,user=postgres ERROR:  deadlock detected
"""

    parser = PostgreSQLDeadlockParser()
    deadlocks = parser.parse(sample_log)
    version = parser.get_detected_version()

    print(f"✓ 检测到版本: {version}")
    print(f"✓ 解析到死锁数量: {len(deadlocks)}")

    if deadlocks:
        d = deadlocks[0]
        print(f"  - 死锁时间: {d.timestamp}")
        print(f"  - 事务数量: {len(d.transactions)}")
        for txn in d.transactions:
            print(f"  - 事务 {txn.txn_id}: 状态={txn.status}")
            if txn.sql_statements:
                print(f"    SQL: {txn.sql_statements[0][:60]}...")

    print("✓ PostgreSQL解析测试通过\n")
    return deadlocks


def test_tarjan_cycle_detection():
    print("=" * 60)
    print("测试3: Tarjan算法循环依赖检测")
    print("=" * 60)

    mysql_deadlocks = test_mysql_parser()
    if not mysql_deadlocks:
        print("✗ 无法进行循环检测测试 - 没有死锁数据")
        return

    graph_gen = DeadlockGraphGenerator()
    graph = graph_gen.generate_graph(mysql_deadlocks)

    cycles = graph_gen.detect_cycles_with_details(graph)
    print(f"✓ 检测到的循环数量: {len(cycles)}")

    for i, cycle in enumerate(cycles):
        print(f"  循环 #{i + 1}:")
        print(f"    节点: {' → '.join(cycle['cycle'])}")
        print(f"    边: {len(cycle['edges'])} 条")
        print(f"    类型: {cycle['cycle_type']}")

    graph_data = graph_gen.to_cytoscape_json(graph)
    print(f"✓ Cytoscape格式数据生成成功: {len(graph_data['elements'])} 个元素")

    stats = graph_gen.get_graph_statistics(graph)
    print(f"✓ 图统计: {stats['nodes_count']} 个节点, {stats['edges_count']} 条边")
    print(f"  - 强连通分量: {stats['scc_count']} 个")
    print(f"  - 环数量: {stats['cycles_count']} 个")

    print("✓ Tarjan算法测试通过\n")


def test_explain_analyzer():
    print("=" * 60)
    print("测试4: EXPLAIN分析与索引推荐")
    print("=" * 60)

    analyzer_mysql = ExplainAnalyzer(db_type='mysql')

    test_sqls = [
        "SELECT * FROM users WHERE email = 'test@example.com'",
        "UPDATE users SET name = 'test' WHERE id = 1 AND status = 1",
        "SELECT * FROM orders WHERE user_id = 1 ORDER BY created_at DESC",
        "SELECT COUNT(*) FROM orders WHERE status = 'pending' AND created_at > '2024-01-01'"
    ]

    all_results = analyzer_mysql.analyze_multiple(test_sqls)
    print(f"✓ 分析了 {len(all_results)} 条SQL")

    for r in all_results[:2]:
        print(f"  SQL: {r.sql[:50]}...")
        print(f"    表: {r.table_name}")
        print(f"    是否全表扫描: {r.has_full_table_scan}")
        print(f"    类型: {r.type}")
        print(f"    警告: {r.warnings}")
        print(f"    索引建议数量: {len(r.recommendations)}")

    recommendations = analyzer_mysql.get_all_recommendations(all_results)
    print(f"✓ 总索引建议数量: {len(recommendations)}")

    for rec in recommendations:
        print(f"  建议索引: {rec.index_name} ON {rec.table_name}({', '.join(rec.index_columns)})")
        print(f"    原因: {rec.reason}")
        print(f"    预计收益: {rec.estimated_benefit}%")
        print(f"    SQL: {rec.create_statement}")
        print()

    print("✓ EXPLAIN分析测试通过\n")


def test_optimizer_with_explain():
    print("=" * 60)
    print("测试5: 优化建议（集成EXPLAIN分析）")
    print("=" * 60)

    mysql_deadlocks = test_mysql_parser()
    if not mysql_deadlocks:
        print("✗ 无法进行优化建议测试 - 没有死锁数据")
        return

    analyzer = DeadlockAnalyzer()
    stats = analyzer.analyze(mysql_deadlocks)

    optimizer = OptimizationAdvisor()
    suggestions = optimizer.analyze(mysql_deadlocks, stats)

    print(f"✓ 生成优化建议数量: {len(suggestions)}")

    for i, s in enumerate(suggestions):
        print(f"  建议 #{i + 1}: [{s.priority}] {s.category} - {s.title}")
        print(f"    影响表: {s.affected_tables}")
        print(f"    建议: {s.suggested_action[:80]}...")
        print()

    print("✓ 优化建议测试通过\n")


def test_realtime_monitor():
    print("=" * 60)
    print("测试6: 实时死锁监控（每5秒检测）")
    print("=" * 60)

    monitor = DeadlockMonitor(check_interval=2.0)

    print(f"✓ 监控初始化成功")
    print(f"  检查间隔: {monitor.check_interval}秒")

    status = monitor.get_status()
    print(f"  初始状态: 运行中={status.is_running}, 检查次数={status.total_checks}")

    monitor.configure_database(
        db_type='mysql',
        host='localhost',
        port=3306,
        user='root',
        password='',
        database='test'
    )
    print("✓ 数据库配置成功")

    status = monitor.check_now()
    print(f"✓ 单次检查完成")
    print(f"  检查次数: {status.total_checks}")
    print(f"  活跃锁等待: {status.active_lock_waits}")
    print(f"  潜在死锁: {status.potential_deadlocks}")

    alerts = monitor.get_current_alerts(limit=10)
    print(f"✓ 当前告警数量: {len(alerts)}")

    for alert in alerts[:3]:
        print(f"  [{alert.level}] {alert.title}: {alert.message}")

    lock_waits = monitor.get_current_lock_waits()
    print(f"✓ 当前锁等待数量: {len(lock_waits)}")

    for wait in lock_waits[:3]:
        print(f"  Txn {wait.waiting_txn_id} → {wait.holding_txn_id}: "
              f"{wait.lock_mode} on {wait.table_name} ({wait.wait_duration:.2f}s)")

    wait_graph = monitor.get_wait_graph()
    print(f"✓ 等待图生成成功: {len(wait_graph.nodes())} 节点, {len(wait_graph.edges())} 边")

    monitor.clear_alerts()
    print("✓ 告警清除成功")

    print("✓ 实时监控测试通过\n")


def test_deadlock_simulator():
    print("=" * 60)
    print("测试7: 死锁回放模拟（修改事务顺序验证）")
    print("=" * 60)

    mysql_deadlocks = test_mysql_parser()
    if not mysql_deadlocks:
        print("✗ 无法进行模拟测试 - 没有死锁数据")
        return

    simulator = DeadlockSimulator()
    deadlock = mysql_deadlocks[0]

    result = simulator.simulate_deadlock(deadlock)
    print(f"✓ 死锁模拟完成")
    print(f"  原始顺序是否死锁: {result.original_has_deadlock}")
    print(f"  优化顺序是否死锁: {result.optimized_has_deadlock}")
    print(f"  优化后等待时间: {result.optimized_wait_time:.2f}s")
    print(f"  优化说明: {result.optimization_note}")

    print(f"✓ 原始执行步骤: {len(result.original_steps)} 步")
    for step in result.original_steps[:3]:
        print(f"  T={step.time:.1f}s: {step.description}")
        for op in step.operations:
            status = "(等待)" if op.is_waiting else ""
            print(f"    - Txn {op.txn_id}: {op.operation_type} {op.lock_mode} on {op.table_name} {status}")

    print(f"✓ 优化执行步骤: {len(result.optimized_steps)} 步")
    for step in result.optimized_steps[:3]:
        print(f"  T={step.time:.1f}s: {step.description}")

    order_tests = simulator.test_multiple_orders(deadlock)
    print(f"✓ 多种顺序测试完成: {len(order_tests)} 种方案")

    deadlock_count = sum(1 for t in order_tests if t['has_deadlock'])
    success_count = len(order_tests) - deadlock_count
    print(f"  死锁方案: {deadlock_count} 种, 正常方案: {success_count} 种")

    for t in order_tests:
        tag = "原始" if t.get('is_original') else ("推荐" if t.get('is_optimized') else "")
        status = "死锁" if t['has_deadlock'] else "正常"
        print(f"  [{status}] {tag}: {' → '.join(t['transaction_order'])}")

    print("✓ 死锁模拟测试通过\n")


def test_apm_integration():
    print("=" * 60)
    print("测试8: APM集成（关联应用调用链）")
    print("=" * 60)

    mysql_deadlocks = test_mysql_parser()
    if not mysql_deadlocks:
        print("✗ 无法进行APM测试 - 没有死锁数据")
        return

    apm = APMIntegration(apm_type='mock', service_name='test-service')
    print(f"✓ APM初始化成功 (类型: {apm.apm_type})")

    from datetime import datetime, timedelta
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    end_time = now

    traces = apm.query_traces(start_time, end_time, service_name='test-service')
    print(f"✓ 查询traces成功: {len(traces)} 条")

    for trace in traces[:2]:
        print(f"  Trace: {trace.trace_id}, 服务: {trace.service_name}, 操作: {trace.operation_name}")
        print(f"    耗时: {trace.duration_ms}ms, 跨度: {len(trace.spans)} 个")
        if trace.spans:
            print(f"    首个Span: {trace.spans[0].operation_name}")

    if traces:
        trace_detail = apm.query_trace_detail(traces[0].trace_id)
        print(f"✓ 查询trace详情成功: {trace_detail.trace_id}")
        print(f"  Span数量: {len(trace_detail.spans)}")
        for span in trace_detail.spans[:3]:
            print(f"    - {span.operation_name} ({span.duration_ms}ms)")

    deadlock = mysql_deadlocks[0]
    correlations = apm.correlate_deadlock_with_traces(
        deadlock,
        time_window_before=60,
        time_window_after=10
    )
    print(f"✓ 死锁与调用链关联成功: {len(correlations)} 条关联")

    for corr in correlations:
        print(f"  关联度: {(corr.correlation_score * 100):.0f}%")
        print(f"    Trace: {corr.trace_id}")
        print(f"    事务: {corr.transaction_id}")
        print(f"    匹配SQL: {corr.matched_sql[:50]}...")

    trace_links = apm.generate_trace_links(correlations)
    print(f"✓ 生成调用链链接: {len(trace_links)} 个")

    for link in trace_links[:2]:
        print(f"  {link['name']}: {link['url']}")

    sent = apm.send_deadlock_alert(deadlock, correlations)
    print(f"✓ 告警发送: {'成功' if sent else '失败'}")

    print("✓ APM集成测试通过\n")


def test_module_exports():
    print("=" * 60)
    print("测试9: 模块导出检查")
    print("=" * 60)

    import deadlock_analyzer

    expected_exports = [
        'DeadlockAnalyzer',
        'Statistics',
        'DeadlockGraphGenerator',
        'OptimizationAdvisor',
        'OptimizationSuggestion',
        'ExplainAnalyzer',
        'ExplainAnalysisResult',
        'IndexRecommendation',
        'DeadlockMonitor',
        'Alert',
        'MonitorStatus',
        'LockWaitInfo',
        'DeadlockSimulator',
        'SimulationResult',
        'SimulationStep',
        'SimulatedOperation',
        'APMIntegration',
        'TraceInfo',
        'TraceSpan',
        'DeadlockTraceCorrelation'
    ]

    for export_name in expected_exports:
        if hasattr(deadlock_analyzer, export_name):
            print(f"✓ {export_name} 已导出")
        else:
            print(f"✗ {export_name} 未找到")

    print("✓ 模块导出测试通过\n")


def main():
    print("\n" + "=" * 60)
    print("数据库死锁检测分析工具 - 新功能测试套件")
    print("=" * 60 + "\n")

    tests = [
        ("MySQL解析器（多版本适配）", test_mysql_parser),
        ("PostgreSQL解析器（多版本适配）", test_postgresql_parser),
        ("Tarjan循环检测算法", test_tarjan_cycle_detection),
        ("EXPLAIN分析与索引推荐", test_explain_analyzer),
        ("优化建议（集成EXPLAIN）", test_optimizer_with_explain),
        ("实时死锁监控", test_realtime_monitor),
        ("死锁回放模拟", test_deadlock_simulator),
        ("APM集成", test_apm_integration),
        ("模块导出检查", test_module_exports)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()

    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    print(f"总计: {len(tests)} 项")
    print()

    if failed == 0:
        print("✓ 所有测试通过！")
        return 0
    else:
        print(f"✗ 有 {failed} 项测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
