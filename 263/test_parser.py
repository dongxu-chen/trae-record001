#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试死锁解析器功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deadlock_parser import MySQLDeadlockParser, PostgreSQLDeadlockParser
from deadlock_analyzer import DeadlockAnalyzer, DeadlockGraphGenerator, OptimizationAdvisor


def test_mysql_parser():
    print("=" * 60)
    print("测试 MySQL 死锁解析器")
    print("=" * 60)

    sample_file = os.path.join('sample_logs', 'mysql_sample.log')
    with open(sample_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    parser = MySQLDeadlockParser()
    deadlocks = parser.parse(log_content)

    print(f"解析到 {len(deadlocks)} 个死锁\n")

    for i, deadlock in enumerate(deadlocks, 1):
        print(f"--- 死锁 #{i} ---")
        print(f"  时间戳: {deadlock.timestamp}")
        print(f"  涉及事务数: {len(deadlock.transactions)}")
        print(f"  被选中牺牲的事务: {deadlock.victim_txns}")

        for txn in deadlock.transactions:
            print(f"  事务 {txn.txn_id}:")
            print(f"    状态: {txn.status}")
            print(f"    等待时间: {txn.wait_time}秒")
            print(f"    持有的锁: {len(txn.holding_locks)}个")
            for lock in txn.holding_locks:
                print(f"      - {lock.lock_mode} on {lock.table_name} (索引: {lock.index_name})")
            if txn.waiting_lock:
                print(f"    等待的锁: {txn.waiting_lock.lock_mode} on {txn.waiting_lock.table_name}")
            print(f"    SQL语句: {len(txn.sql_statements)}个")
            for sql in txn.sql_statements:
                print(f"      - {sql[:80]}...")
        print()


def test_postgresql_parser():
    print("=" * 60)
    print("测试 PostgreSQL 死锁解析器")
    print("=" * 60)

    sample_file = os.path.join('sample_logs', 'postgresql_sample.log')
    with open(sample_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    parser = PostgreSQLDeadlockParser()
    deadlocks = parser.parse(log_content)

    print(f"解析到 {len(deadlocks)} 个死锁\n")

    for i, deadlock in enumerate(deadlocks, 1):
        print(f"--- 死锁 #{i} ---")
        print(f"  时间戳: {deadlock.timestamp}")
        print(f"  涉及事务数: {len(deadlock.transactions)}")
        print(f"  被选中牺牲的事务: {deadlock.victim_txns}")

        for txn in deadlock.transactions:
            print(f"  事务 {txn.txn_id}:")
            print(f"    状态: {txn.status}")
            print(f"    持有的锁: {len(txn.holding_locks)}个")
            for lock in txn.holding_locks:
                print(f"      - {lock.lock_mode} on {lock.table_name}")
            if txn.waiting_lock:
                print(f"    等待的锁: {txn.waiting_lock.lock_mode} on {txn.waiting_lock.table_name}")
            print(f"    SQL语句: {len(txn.sql_statements)}个")
            for sql in txn.sql_statements:
                print(f"      - {sql[:80]}...")
        print()


def test_analyzer():
    print("=" * 60)
    print("测试 死锁分析器")
    print("=" * 60)

    sample_file = os.path.join('sample_logs', 'mysql_sample.log')
    with open(sample_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    parser = MySQLDeadlockParser()
    deadlocks = parser.parse(log_content)

    analyzer = DeadlockAnalyzer()
    stats = analyzer.analyze(deadlocks)

    print(f"总死锁数: {stats.total_deadlocks}")
    print(f"涉及的表: {stats.involved_tables}")
    print(f"平均等待时间: {stats.average_wait_time:.2f}秒")
    print()

    print("按表统计:")
    for table, count in stats.table_stats.most_common():
        print(f"  {table}: {count}次")
    print()

    print("按SQL模式统计 (TOP 5):")
    for pattern, count in stats.sql_pattern_stats.most_common(5):
        print(f"  [{count}次] {pattern[:100]}...")
    print()

    print("锁模式分布:")
    for mode, count in stats.lock_mode_stats.items():
        print(f"  {mode}: {count}")
    print()

    print("时间段分布:")
    for period, count in stats.time_distribution.items():
        print(f"  {period}: {count}")
    print()

    print("TOP 热点表:")
    for table, count in analyzer.get_top_tables(5):
        print(f"  {table}: {count}次")
    print()


def test_graph_generator():
    print("=" * 60)
    print("测试 关系图生成器")
    print("=" * 60)

    sample_file = os.path.join('sample_logs', 'mysql_sample.log')
    with open(sample_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    parser = MySQLDeadlockParser()
    deadlocks = parser.parse(log_content)

    graph_gen = DeadlockGraphGenerator()
    graph = graph_gen.generate_graph(deadlocks)

    stats = graph_gen.get_graph_statistics(graph)
    print(f"图统计:")
    print(f"  节点数: {stats['nodes']}")
    print(f"  边数: {stats['edges']}")
    print(f"  事务节点: {stats['transactions']}")
    print(f"  锁节点: {stats['locks']}")
    print(f"  死锁节点: {stats['deadlocks']}")
    print(f"  环数: {stats['cycles']}")
    print()

    cycles = graph_gen.detect_cycles(graph)
    if cycles:
        print(f"检测到 {len(cycles)} 个环:")
        for i, cycle in enumerate(cycles[:3], 1):
            print(f"  环 #{i}: {' -> '.join(cycle[:5])}...")
    print()

    cy_json = graph_gen.to_cytoscape_json(graph)
    print(f"Cytoscape JSON 元素数: {len(cy_json['elements'])}")
    print()


def test_optimizer():
    print("=" * 60)
    print("测试 优化建议生成器")
    print("=" * 60)

    sample_file = os.path.join('sample_logs', 'mysql_sample.log')
    with open(sample_file, 'r', encoding='utf-8') as f:
        log_content = f.read()

    parser = MySQLDeadlockParser()
    deadlocks = parser.parse(log_content)

    analyzer = DeadlockAnalyzer()
    stats = analyzer.analyze(deadlocks)

    optimizer = OptimizationAdvisor()
    suggestions = optimizer.analyze(deadlocks, stats)

    print(f"生成 {len(suggestions)} 条优化建议\n")

    for i, suggestion in enumerate(suggestions, 1):
        priority = {"high": "高", "medium": "中", "low": "低"}[suggestion.priority]
        print(f"--- 建议 #{i} [{priority}优先级] ---")
        print(f"  分类: {suggestion.category}")
        print(f"  标题: {suggestion.title}")
        print(f"  描述: {suggestion.description[:100]}...")
        if suggestion.affected_tables:
            print(f"  受影响的表: {', '.join(suggestion.affected_tables)}")
        print(f"  预期影响: {suggestion.estimated_impact}")
        print()


if __name__ == '__main__':
    try:
        test_mysql_parser()
        test_postgresql_parser()
        test_analyzer()
        test_graph_generator()
        test_optimizer()

        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
