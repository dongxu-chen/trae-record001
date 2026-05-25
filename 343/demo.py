"""
快速演示脚本 - Quick Demo
生成模拟数据并输出完整报告
"""
import os
import sys

# 确保模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from txn_analyzer.config import PGConfig
from txn_analyzer.parsers.pg_parser import PostgresWALParser
from txn_analyzer.analysis.stats import compute_statistics
from txn_analyzer.analysis.hotspots import HotspotAnalyzer
from txn_analyzer.analysis.locks import LockConflictAnalyzer, LockHierarchyBuilder
from txn_analyzer.analysis.large_txn import LargeTxnDetector
from txn_analyzer.analysis.rollback import RollbackPatternAnalyzer
from txn_analyzer.analysis.idle_txn import IdleTxnDetector
from txn_analyzer.analysis.impact_predictor import TxnImpactPredictor
from txn_analyzer.visualization.echarts import generate_report
from txn_analyzer.logger import setup_logger

logger = setup_logger("demo", "INFO")


def main():
    logger.info("=" * 60)
    logger.info("  🚀 数据库事务分析工具 - 演示模式")
    logger.info("=" * 60)

    # 1. 生成模拟数据
    logger.info("\n📦 生成模拟事务数据 (100 条)...")
    pg_parser = PostgresWALParser(PGConfig())
    txns = pg_parser.generate_mock_data(count=100)

    logger.info("✅ 生成完成: %d 条事务, %d 条锁事件, %d 条死锁事件",
                len(txns), len(pg_parser.lock_events), len(pg_parser.deadlock_events))

    # 2. 统计分析
    logger.info("\n📈 执行统计分析...")
    stats = compute_statistics(txns)
    logger.info("  总事务: %d | 提交率: %.1f%% | P95: %.0fms | P99: %.0fms",
                stats.total_txn_count, stats.commit_rate * 100,
                stats.duration_p95, stats.duration_p99)

    # 3. 热点分析
    hotspot = HotspotAnalyzer(top_n=20).analyze(txns)
    logger.info("  TOP 热点表: %s",
                ", ".join(t.table_name for t in hotspot.top_tables[:5]))

    # 4. 锁冲突分析
    lock_result = LockConflictAnalyzer(lock_wait_threshold_ms=100).analyze(
        txns, pg_parser.lock_events, pg_parser.deadlock_events
    )
    logger.info("  锁冲突对象: %d | 死锁: %d",
                len(lock_result.conflicts), len(lock_result.deadlock_events))

    # 4b. 锁继承关系构建
    hierarchy = LockHierarchyBuilder().build(txns, pg_parser.lock_events)
    logger.info("  锁继承层级: %d 个 Schema, %d 个表",
                len(hierarchy.children),
                sum(len(t.children) for t in hierarchy.children))

    # 5. 大事务检测（双重阈值模式）
    large_txn = LargeTxnDetector(
        bytes_threshold=10 * 1024 * 1024,
        row_ops_threshold=100,
        dual_threshold=True,
    ).detect(txns)
    logger.info("  大事务: %d | 双重阈值命中: %d | 长事务: %d | 高锁等待: %d | 回滚: %d",
                large_txn.risk_summary["total_large"],
                large_txn.risk_summary["total_dual_threshold"],
                large_txn.risk_summary["total_long_running"],
                large_txn.risk_summary["total_high_lock"],
                large_txn.risk_summary["total_rollback"])

    # 6. 回滚模式分析
    rollback_result = RollbackPatternAnalyzer(
        min_rollback_count=1, rollback_rate_threshold=0.1
    ).analyze(txns)
    logger.info("  回滚模式: %d 个高风险模式 | 整体回滚率: %.1f%% | 死锁受害者: %d",
                rollback_result.summary["total_high_risk_patterns"],
                rollback_result.summary["overall_rollback_rate"] * 100,
                rollback_result.summary["deadlock_victim"])

    # 7. 空闲事务检测
    idle_result = IdleTxnDetector(
        idle_threshold_ms=1000, critical_threshold_ms=5000,
    ).detect(txns)
    logger.info("  空闲事务: %d 个告警 | 严重: %d | 受影响连接: %d",
                idle_result.summary["total_long_idle"],
                idle_result.summary["total_critical"],
                idle_result.summary["affected_connections"])

    # 8. 事务影响预测
    impact_result = TxnImpactPredictor(top_n_tables=10).predict(txns)
    logger.info("  影响预估: %d 行 | %.1f MB | 热点表: %d 个 | 建议: %s",
                impact_result.summary["total_rows_estimated"],
                impact_result.summary["total_bytes_estimated"] / 1024 / 1024,
                impact_result.summary["hot_table_count"],
                impact_result.change_recommendation[:60] + ("..." if len(impact_result.change_recommendation) > 60 else ""))

    # 9. 生成可视化报告
    logger.info("\n🎨 生成 ECharts 可视化报告...")
    report_path = generate_report(
        stats=stats,
        hotspot=hotspot,
        lock_conflict=lock_result,
        large_txn=large_txn,
        rollback=rollback_result,
        idle_txn=idle_result,
        impact=impact_result,
        output_dir="./reports",
        source_type="Mock (100 txns)",
    )
    logger.info("✅ 报告已生成: %s", os.path.abspath(report_path))

    # 7. 打印摘要
    print("\n" + "=" * 60)
    print("  📊 分析摘要")
    print("=" * 60)
    print(f"  事务总数:     {stats.total_txn_count}")
    print(f"  提交:         {stats.commit_count} ({stats.commit_rate:.1%})")
    print(f"  回滚:         {stats.rollback_count} ({stats.rollback_rate:.1%})")
    print(f"  P95 持续:     {stats.duration_p95:.0f} ms")
    print(f"  P99 持续:     {stats.duration_p99:.0f} ms")
    print(f"  大事务:       {large_txn.risk_summary['total_large']}")
    print(f"  双重阈值命中: {large_txn.risk_summary['total_dual_threshold']}")
    print(f"  回滚率:       {rollback_result.summary['overall_rollback_rate']:.1%}")
    print(f"  空闲告警:     {idle_result.summary['total_long_idle']} (严重: {idle_result.summary['total_critical']})")
    print(f"  影响预估:     {impact_result.summary['total_rows_estimated']} 行 / {impact_result.summary['total_bytes_estimated'] / 1024 / 1024:.1f} MB")
    print(f"  死锁:         {len(lock_result.deadlock_events)}")
    print("=" * 60)
    print(f"\n  📂 报告文件: {os.path.abspath(report_path)}")
    print("  请在浏览器中打开查看完整的交互式图表报告\n")

    return report_path


if __name__ == "__main__":
    main()
