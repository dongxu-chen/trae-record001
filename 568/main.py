#!/usr/bin/env python3
"""
慢SQL自动重写工具 - 命令行入口
支持MySQL和PostgreSQL，自动分析执行计划并重写SQL
"""

import argparse
import sys
import json
from typing import Optional

from config import AppConfig, DatabaseConfig, RewriteConfig
from sql_analyzer import SQLParser
from rewriter import SQLRewriter, RewriteResult
from performance import PerformanceComparator, PerformanceComparisonResult
from execution_plan import (
    MySQLExecutionPlanAnalyzer,
    PostgreSQLExecutionPlanAnalyzer,
    PlanAnalysis,
)
from db_connector import MySQLConnector, PostgreSQLConnector


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║             ⚡  慢SQL自动重写工具  v1.0                     ║
║  智能分析执行计划 | 自动应用优化规则 | 性能对比验证          ║
║  支持 MySQL / PostgreSQL                                    ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def parse_args():
    parser = argparse.ArgumentParser(
        description="慢SQL自动重写工具 - 分析执行计划，自动优化SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 仅解析SQL
  python main.py parse -s "SELECT * FROM orders WHERE status = 'pending'"

  # 仅重写SQL（不连接数据库）
  python main.py rewrite -s "SELECT * FROM orders o WHERE o.customer_id IN (SELECT id FROM customers)"

  # 完整流程：连接数据库 -> 获取执行计划 -> 重写 -> 性能对比
  python main.py full -s "SELECT * FROM orders" --db-type mysql --host localhost --user root --password pass --db test

  # 启动Web界面
  python main.py web
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="操作命令")

    parse_parser = subparsers.add_parser("parse", help="解析SQL结构")
    parse_parser.add_argument("-s", "--sql", required=True, help="SQL语句")
    parse_parser.add_argument("--dialect", default="mysql", choices=["mysql", "postgresql"], help="SQL方言")

    rewrite_parser = subparsers.add_parser("rewrite", help="重写SQL（无需数据库连接）")
    rewrite_parser.add_argument("-s", "--sql", required=True, help="SQL语句")
    rewrite_parser.add_argument("--dialect", default="mysql", choices=["mysql", "postgresql"], help="SQL方言")
    rewrite_parser.add_argument("--output", "-o", help="输出文件路径")
    rewrite_parser.add_argument("--rules", nargs="*", default=["all"], help="应用的规则，默认全部")

    full_parser = subparsers.add_parser("full", help="完整优化流程（需要数据库连接）")
    full_parser.add_argument("-s", "--sql", required=True, help="SQL语句")
    full_parser.add_argument("--db-type", required=True, choices=["mysql", "postgresql"], help="数据库类型")
    full_parser.add_argument("--host", default="localhost", help="数据库主机")
    full_parser.add_argument("--port", type=int, help="数据库端口")
    full_parser.add_argument("--user", required=True, help="用户名")
    full_parser.add_argument("--password", required=True, help="密码")
    full_parser.add_argument("--db", required=True, help="数据库名")
    full_parser.add_argument("--iterations", type=int, default=3, help="性能测试迭代次数")
    full_parser.add_argument("--output", "-o", help="输出报告文件路径")

    web_parser = subparsers.add_parser("web", help="启动Streamlit Web界面")
    web_parser.add_argument("--port", type=int, default=8501, help="Web服务端口")
    web_parser.add_argument("--host", default="0.0.0.0", help="Web服务主机")

    parser.add_argument("--json", action="store_true", help="以JSON格式输出结果")

    return parser.parse_args()


def cmd_parse(args):
    """解析SQL命令"""
    print(f"\n📋 正在解析SQL (方言: {args.dialect})...")
    print("-" * 60)

    parser = SQLParser(dialect=args.dialect)
    parsed = parser.parse(args.sql)

    if not parsed.is_valid:
        print(f"❌ SQL解析失败: {parsed.error}")
        return 1

    print("✅ SQL解析成功!")
    print(f"   SQL类型: {parsed.sql_type}")
    print(f"   涉及表: {', '.join(parsed.tables) if parsed.tables else '无'}")
    print(f"   涉及列: {len(parsed.columns)} 个")
    print(f"   子查询数: {len(parsed.subqueries)}")

    if parsed.joins:
        print(f"\n🔗 JOIN信息:")
        for join in parsed.joins:
            print(f"   - {join['type']} JOIN {join['table']} ON {join['on']}")

    if parsed.where_conditions:
        print(f"\n📋 WHERE条件:")
        for cond in parsed.where_conditions:
            print(f"   - {cond}")

    features = []
    if parsed.has_order_by:
        features.append("ORDER BY (可能需要filesort)")
    if parsed.has_group_by:
        features.append("GROUP BY (可能需要临时表)")
    if parsed.has_having:
        features.append("HAVING (可考虑下推)")
    if parsed.has_limit:
        features.append("LIMIT (可尝试下推)")
    if parsed.has_distinct:
        features.append("DISTINCT (可能影响性能)")
    if parsed.has_union:
        features.append("UNION (考虑UNION ALL)")

    if features:
        print(f"\n⚠️  检测到的性能特征:")
        for f in features:
            print(f"   - {f}")

    if args.json:
        print("\n" + json.dumps(parsed.to_dict(), indent=2, ensure_ascii=False))

    return 0


def cmd_rewrite(args):
    """重写SQL命令"""
    print(f"\n✨ 正在重写SQL (方言: {args.dialect})...")
    print("-" * 60)

    rewrite_config = RewriteConfig()
    rewriter = SQLRewriter(dialect=args.dialect, config=rewrite_config)

    print(f"\n📋 可用的重写规则:")
    for rule in rewriter.get_available_rules():
        print(f"   ✅ {rule['name']}: {rule['description']}")

    print(f"\n🔄 开始重写...")
    result = rewriter.rewrite(args.sql)

    if result.error:
        print(f"❌ 重写失败: {result.error}")
        return 1

    print(f"\n📊 重写统计:")
    print(f"   应用规则数: {result.rules_applied}")
    print(f"   是否重写: {'是' if result.is_rewritten else '否'}")

    if result.steps:
        print(f"\n📝 重写步骤:")
        for i, step in enumerate(result.steps):
            if step.applied:
                print(f"   ✅ {i+1}. {step.rule_name}: {', '.join(step.changes)}")

    print(f"\n{'='*60}")
    print("🔴 原始SQL:")
    print(f"{'='*60}")
    print(result.original_sql)

    if result.is_rewritten:
        print(f"\n{'='*60}")
        print("🟢 重写后SQL:")
        print(f"{'='*60}")
        print(result.rewritten_sql)

        is_valid, msg = rewriter.validate_rewrite(result.original_sql, result.rewritten_sql)
        if is_valid:
            print(f"\n✅ 重写验证通过: {msg}")
        else:
            print(f"\n⚠️  重写验证警告: {msg}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result.rewritten_sql)
            print(f"\n💾 重写后SQL已保存到: {args.output}")

        if args.json:
            print("\n" + json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"\nℹ️  SQL已是最优，无需重写")

    return 0


def cmd_full(args):
    """完整优化流程"""
    print_banner()
    print(f"\n🚀 开始完整优化流程...")
    print("-" * 60)

    port = args.port or (3306 if args.db_type == "mysql" else 5432)

    db_config = DatabaseConfig(
        host=args.host,
        port=port,
        user=args.user,
        password=args.password,
        database=args.db,
        db_type=args.db_type,
    )

    app_config = AppConfig(database=db_config)

    print(f"\n📡 连接到 {args.db_type} 数据库 {args.host}:{port}/{args.db}...")

    try:
        comparator = PerformanceComparator(db_config, app_config)

        if not comparator.connector.connect():
            print("❌ 数据库连接失败")
            return 1

        print("✅ 数据库连接成功!")

        print(f"\n📊 分析原始SQL执行计划...")
        original_perf = comparator.benchmark_query(args.sql, iterations=args.iterations)

        if not original_perf.success:
            print(f"❌ 原始SQL执行失败: {original_perf.error}")
            comparator.close()
            return 1

        print(f"   原始执行时间: {original_perf.avg_time_ms:.2f} ms")
        print(f"   返回行数: {original_perf.rows_returned}")

        if original_perf.plan_analysis:
            plan = original_perf.plan_analysis
            print(f"   预估成本: {plan.total_cost:.2f}")
            if plan.has_full_table_scan:
                print("   ⚠️  检测到全表扫描!")
            if plan.potential_problems:
                print(f"   发现 {len(plan.potential_problems)} 个潜在问题")

        print(f"\n✨ 开始自动重写SQL...")
        rewrite_config = RewriteConfig()
        rewriter = SQLRewriter(dialect=args.db_type, config=rewrite_config)

        rewrite_result = rewriter.rewrite_with_plan(
            args.sql,
            plan_analysis=original_perf.plan_analysis,
        )

        if rewrite_result.error:
            print(f"❌ 重写失败: {rewrite_result.error}")
            comparator.close()
            return 1

        print(f"   应用了 {rewrite_result.rules_applied} 条重写规则")

        if not rewrite_result.is_rewritten:
            print("\nℹ️  SQL已是最优，无需重写")
            comparator.close()
            return 0

        print(f"\n📊 对比重写后SQL性能...")
        comparison = comparator.compare(
            original_sql=args.sql,
            rewritten_sql=rewrite_result.rewritten_sql,
            rewrite_result=rewrite_result,
            iterations=args.iterations,
        )

        print(f"\n{'='*60}")
        print("📊 性能对比结果")
        print(f"{'='*60}")
        print(f"   原始耗时: {comparison.original.avg_time_ms:.2f} ms")
        print(f"   重写耗时: {comparison.rewritten.avg_time_ms:.2f} ms")

        if comparison.is_faster:
            print(f"   ✅ 性能提升: {comparison.improvement_percent:.1f}% 🎉")
        else:
            print(f"   ⚠️  性能变化: {comparison.improvement_percent:.1f}%")

        print(f"   结果验证: {'✅ 通过' if comparison.validation_passed else '❌ 失败'}")
        if not comparison.validation_passed:
            print(f"     原因: {comparison.validation_message}")

        print(f"\n{'='*60}")
        print("🔴 原始SQL:")
        print(f"{'='*60}")
        print(args.sql)

        print(f"\n{'='*60}")
        print("🟢 重写后SQL:")
        print(f"{'='*60}")
        print(rewrite_result.rewritten_sql)

        if rewrite_result.steps:
            print(f"\n{'='*60}")
            print("📝 重写规则应用详情:")
            print(f"{'='*60}")
            for i, step in enumerate(rewrite_result.steps):
                if step.applied:
                    print(f"   ✅ {i+1}. {step.rule_name}")
                    for change in step.changes:
                        print(f"      - {change}")

        report = {
            "original_sql": args.sql,
            "rewritten_sql": rewrite_result.rewritten_sql,
            "performance": comparison.to_dict(),
            "rewrite_steps": [s.to_dict() for s in rewrite_result.steps if s.applied],
        }

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n💾 完整报告已保存到: {args.output}")

        if args.json:
            print("\n" + json.dumps(report, indent=2, ensure_ascii=False))

        comparator.close()
        print(f"\n✨ 优化完成!")
        return 0

    except Exception as e:
        print(f"❌ 执行错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_web(args):
    """启动Web界面"""
    print_banner()
    print(f"🌐 启动Streamlit Web界面...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   按 Ctrl+C 停止服务\n")

    try:
        import streamlit.web.cli as stcli
        sys.argv = [
            "streamlit",
            "run",
            "app.py",
            f"--server.port={args.port}",
            f"--server.address={args.host}",
            "--server.headless=true",
        ]
        sys.exit(stcli.main())
    except ImportError:
        print("❌ 未安装streamlit，请先运行: pip install streamlit")
        return 1
    except Exception as e:
        print(f"❌ 启动失败: {str(e)}")
        return 1


def main():
    args = parse_args()

    commands = {
        "parse": cmd_parse,
        "rewrite": cmd_rewrite,
        "full": cmd_full,
        "web": cmd_web,
    }

    if args.command in commands:
        return commands[args.command](args)
    else:
        print(f"❌ 未知命令: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
