"""
CLI Entry Point - CLI 入口
提供命令行接口来运行数据库事务分析工具。
"""
import argparse
import json
import sys
from typing import List

from .config import AppConfig, MySQLConfig, PGConfig, AnalysisConfig
from .logger import setup_logger
from .parsers.mysql_parser import MySQLBinlogParser
from .parsers.pg_parser import PostgresWALParser
from .parsers.base import TxnRecord
from .analysis.stats import compute_statistics
from .analysis.hotspots import HotspotAnalyzer
from .analysis.locks import LockConflictAnalyzer
from .analysis.large_txn import LargeTxnDetector
from .analysis.rollback import RollbackPatternAnalyzer
from .analysis.idle_txn import IdleTxnDetector
from .analysis.impact_predictor import TxnImpactPredictor
from .visualization.echarts import generate_report


logger = setup_logger("cli")


def build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="txn-analyzer",
        description="数据库事务分析工具 - 解析 binlog/WAL，分析事务热点、锁冲突、大事务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用模拟数据生成报告
  txn-analyzer --mock --mock-count 100

  # 解析 MySQL binlog 文件（需要先用 mysqlbinlog 导出）
  txn-analyzer --mysql --binlog-file mysql-bin.000001.txt

  # 解析多个 MySQL binlog 文件（支持跨文件事务重建）
  txn-analyzer --mysql --binlog-files mysql-bin.000001.txt mysql-bin.000002.txt mysql-bin.000003.txt

  # 在线连接 MySQL 实时解析
  txn-analyzer --mysql --host 127.0.0.1 --port 3306 --user root --password xxx

  # 解析 PostgreSQL WAL 文件
  txn-analyzer --postgres --wal-file pg_wal/000000010000000000000001 --pg-waldump-path /usr/bin/pg_waldump

  # 解析 PostgreSQL 日志中的死锁
  txn-analyzer --postgres --pg-log /var/log/postgresql/postgresql.log

  # 同时分析 MySQL 和 PostgreSQL
  txn-analyzer --mysql --binlog-file binlog.txt --postgres --wal-file pg_wal/0001

  # 自定义分析参数（双重阈值：写入量≥50MB 且 行数≥500 行才判定为大事务）
  txn-analyzer --mock --large-threshold 52428800 --row-ops-threshold 500 --lock-threshold 50 --top-n 30

  # 关闭双重阈值，使用 OR 模式
  txn-analyzer --mock --no-dual-threshold --large-threshold 104857600
        """,
    )

    # 数据源选择
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--mysql", action="store_true",
        help="解析 MySQL binlog",
    )
    source_group.add_argument(
        "--postgres", action="store_true",
        help="解析 PostgreSQL WAL",
    )
    source_group.add_argument(
        "--mock", action="store_true",
        help="使用模拟数据生成报告（用于演示/测试）",
    )

    # MySQL 参数
    mysql_group = parser.add_argument_group("MySQL 选项")
    mysql_group.add_argument("--host", default="127.0.0.1", help="MySQL 主机地址")
    mysql_group.add_argument("--port", type=int, default=3306, help="MySQL 端口")
    mysql_group.add_argument("--user", default="root", help="MySQL 用户名")
    mysql_group.add_argument("--password", default="", help="MySQL 密码")
    mysql_group.add_argument("--server-id", type=int, default=100, help="MySQL slave server ID")
    mysql_group.add_argument("--binlog-file", help="离线 binlog 文件路径（mysqlbinlog 导出的文本）")
    mysql_group.add_argument("--binlog-files", nargs="*", help="多个离线 binlog 文件路径（按顺序解析以支持跨文件事务重建）")
    mysql_group.add_argument("--binlog-pos", type=int, default=4, help="binlog 起始位置")
    mysql_group.add_argument("--only-schemas", nargs="*", help="只解析指定 schema")
    mysql_group.add_argument("--only-tables", nargs="*", help="只解析指定表")

    # PostgreSQL 参数
    pg_group = parser.add_argument_group("PostgreSQL 选项")
    pg_group.add_argument("--pg-host", default="127.0.0.1", help="PG 主机地址")
    pg_group.add_argument("--pg-port", type=int, default=5432, help="PG 端口")
    pg_group.add_argument("--pg-user", default="postgres", help="PG 用户名")
    pg_group.add_argument("--pg-password", default="", help="PG 密码")
    pg_group.add_argument("--pg-dbname", default="postgres", help="PG 数据库名")
    pg_group.add_argument("--wal-file", help="WAL 文件路径")
    pg_group.add_argument("--pg-waldump-path", default="pg_waldump", help="pg_waldump 工具路径")
    pg_group.add_argument("--pg-log", help="PostgreSQL 日志文件路径（用于死锁检测）")

    # 分析参数
    analysis_group = parser.add_argument_group("分析选项")
    analysis_group.add_argument(
        "--large-threshold", type=int, default=10 * 1024 * 1024,
        help="大事务阈值（字节），默认 10MB",
    )
    analysis_group.add_argument(
        "--row-ops-threshold", type=int, default=1000,
        help="大事务行操作阈值，默认 1000 行",
    )
    analysis_group.add_argument(
        "--no-dual-threshold", action="store_true",
        help="禁用双重阈值模式（改为 OR 模式：满足写入量或行数任一即判定）",
    )
    analysis_group.add_argument(
        "--lock-threshold", type=int, default=100,
        help="锁等待阈值（毫秒），默认 100ms",
    )
    analysis_group.add_argument(
        "--duration-threshold", type=int, default=5000,
        help="长事务持续时间阈值（毫秒），默认 5000ms",
    )
    analysis_group.add_argument(
        "--top-n", type=int, default=20,
        help="热点排名显示数量，默认 20",
    )
    analysis_group.add_argument(
        "--no-viz", action="store_true",
        help="不生成可视化 HTML 报告",
    )
    analysis_group.add_argument(
        "--idle-threshold-ms", type=int, default=60000,
        help="空闲事务告警阈值（毫秒），默认 60s",
    )
    analysis_group.add_argument(
        "--idle-critical-ms", type=int, default=300000,
        help="空闲事务严重告警阈值（毫秒），默认 5min",
    )
    analysis_group.add_argument(
        "--rollback-min-count", type=int, default=2,
        help="回滚模式最小回滚次数，默认 2",
    )
    analysis_group.add_argument(
        "--rollback-rate-threshold", type=float, default=0.15,
        help="回滚模式回滚率阈值，默认 0.15",
    )

    # 输出选项
    output_group = parser.add_argument_group("输出选项")
    output_group.add_argument(
        "--output-dir", default="./reports",
        help="报告输出目录，默认 ./reports",
    )
    output_group.add_argument(
        "--json", action="store_true",
        help="同时输出 JSON 格式报告到标准输出",
    )
    output_group.add_argument(
        "--log-file", help="日志文件路径",
    )
    output_group.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别，默认 INFO",
    )

    # 模拟数据
    mock_group = parser.add_argument_group("模拟数据选项")
    mock_group.add_argument(
        "--mock-count", type=int, default=50,
        help="模拟事务数量，默认 50",
    )

    return parser


def run_analysis(args: argparse.Namespace) -> dict:
    """运行完整分析流程，返回结果字典"""
    # 初始化配置
    config = AppConfig(
        analysis=AnalysisConfig(
            large_txn_threshold_bytes=args.large_threshold,
            lock_wait_threshold_ms=args.lock_threshold,
            hotspot_top_n=args.top_n,
            report_output_dir=args.output_dir,
            enable_visualization=not args.no_viz,
        ),
        log_level=args.log_level,
        log_file=args.log_file,
    )
    config.ensure_dirs()

    all_txns: List[TxnRecord] = []
    all_lock_events = []
    all_deadlock_events = []
    source_type = []

    # ---- MySQL 解析 ----
    if args.mysql:
        mysql_cfg = MySQLConfig(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            server_id=args.server_id,
            binlog_file=args.binlog_file,
            binlog_pos=args.binlog_pos,
            only_schemas=args.only_schemas,
            only_tables=args.only_tables,
        )
        mysql_parser = MySQLBinlogParser(mysql_cfg)
        if args.binlog_files:
            txns = mysql_parser.parse_files(args.binlog_files)
        else:
            txns = mysql_parser.parse()
        all_txns.extend(txns)
        all_lock_events.extend(mysql_parser.lock_events)
        all_deadlock_events.extend(mysql_parser.deadlock_events)
        source_type.append("MySQL")
        connections = mysql_parser.get_connections()
        if connections:
            logger.info("  MySQL 连接上下文: %d 个活跃连接", len(connections))

    # ---- PostgreSQL 解析 ----
    if args.postgres:
        pg_cfg = PGConfig(
            host=args.pg_host,
            port=args.pg_port,
            user=args.pg_user,
            password=args.pg_password,
            dbname=args.pg_dbname,
            wal_file=args.wal_file,
            pg_waldump_path=args.pg_waldump_path,
        )
        pg_parser = PostgresWALParser(pg_cfg)

        if args.wal_file:
            txns = pg_parser.parse()
            all_txns.extend(txns)
            all_lock_events.extend(pg_parser.lock_events)

        if args.pg_log:
            pg_parser.parse_deadlocks_from_log(args.pg_log)
            all_deadlock_events.extend(pg_parser.deadlock_events)

        source_type.append("PostgreSQL")

    # ---- 模拟数据 ----
    if args.mock:
        pg_parser = PostgresWALParser(PGConfig())
        txns = pg_parser.generate_mock_data(args.mock_count)
        all_txns.extend(txns)
        all_lock_events.extend(pg_parser.lock_events)
        all_deadlock_events.extend(pg_parser.deadlock_events)
        source_type.append("Mock")

    if not all_txns:
        logger.warning("未解析到任何事务数据，请检查数据源配置")
        return {"error": "no data"}

    logger.info("共解析 %d 条事务记录，%d 条锁事件，%d 条死锁事件",
                len(all_txns), len(all_lock_events), len(all_deadlock_events))

    # ---- 统计分析 ----
    stats = compute_statistics(all_txns)

    # ---- 热点分析 ----
    hotspot = HotspotAnalyzer(top_n=args.top_n).analyze(all_txns)

    # ---- 锁冲突分析 ----
    lock_result = LockConflictAnalyzer(
        lock_wait_threshold_ms=args.lock_threshold
    ).analyze(all_txns, all_lock_events, all_deadlock_events)

    # ---- 大事务检测 ----
    large_txn = LargeTxnDetector(
        bytes_threshold=args.large_threshold,
        row_ops_threshold=args.row_ops_threshold,
        duration_threshold_ms=args.duration_threshold,
        lock_wait_threshold_ms=args.lock_threshold,
        dual_threshold=not args.no_dual_threshold,
    ).detect(all_txns)

    # ---- 回滚分析 ----
    rollback_result = RollbackPatternAnalyzer(
        min_rollback_count=args.rollback_min_count,
        rollback_rate_threshold=args.rollback_rate_threshold,
    ).analyze(all_txns)

    # ---- 空闲事务检测 ----
    idle_result = IdleTxnDetector(
        idle_threshold_ms=args.idle_threshold_ms,
        critical_threshold_ms=args.idle_critical_ms,
    ).detect(all_txns)

    # ---- 事务影响预测 ----
    impact_result = TxnImpactPredictor(top_n_tables=args.top_n).predict(all_txns)

    # ---- 生成可视化报告 ----
    report_path = None
    if not args.no_viz:
        report_path = generate_report(
            stats=stats,
            hotspot=hotspot,
            lock_conflict=lock_result,
            large_txn=large_txn,
            rollback=rollback_result,
            idle_txn=idle_result,
            impact=impact_result,
            output_dir=args.output_dir,
            source_type=" + ".join(source_type),
        )

    # ---- 组装结果 ----
    result = {
        "summary": {
            "total_transactions": stats.total_txn_count,
            "commit_count": stats.commit_count,
            "rollback_count": stats.rollback_count,
            "commit_rate": round(stats.commit_rate, 4),
            "duration_p95_ms": round(stats.duration_p95, 2),
            "duration_p99_ms": round(stats.duration_p99, 2),
            "lock_wait_p95_ms": round(stats.lock_wait_p95, 2),
            "large_txn_count": large_txn.risk_summary.get("total_large", 0),
            "dual_threshold_count": large_txn.risk_summary.get("total_dual_threshold", 0),
            "deadlock_count": len(all_deadlock_events),
            "rollback_rate": rollback_result.overall_rollback_rate,
            "idle_txn_count": idle_result.total_long_idle,
            "idle_critical_count": idle_result.total_critical,
            "impact_estimated_rows": impact_result.estimated_total_rows,
            "impact_estimated_bytes": impact_result.estimated_total_bytes,
            "time_range": {
                "start": stats.time_start.isoformat() if stats.time_start else None,
                "end": stats.time_end.isoformat() if stats.time_end else None,
            },
        },
        "top_tables": [t.to_dict() for t in hotspot.top_tables[:10]],
        "top_txns": hotspot.top_txns[:10],
        "lock_conflicts": [c.to_dict() for c in lock_result.conflicts[:10]],
        "deadlocks": lock_result.deadlock_events,
        "large_transactions": [t.to_dict() for t in large_txn.large_txns[:10]],
        "risk_summary": large_txn.risk_summary,
        "rollback_patterns": [p.to_dict() for p in rollback_result.high_risk_patterns[:10]],
        "rollback_summary": rollback_result.summary,
        "idle_alerts": [a.to_dict() for a in idle_result.alerts[:10]],
        "idle_summary": idle_result.summary,
        "impact_prediction": {
            "top_affected_tables": [t.to_dict() for t in impact_result.top_affected_tables],
            "hot_table_patterns": [t.to_dict() for t in impact_result.hot_table_patterns],
            "change_recommendation": impact_result.change_recommendation,
            "summary": impact_result.summary,
        },
        "report_path": report_path,
    }

    return result


def main():
    """CLI 主入口"""
    parser = build_arg_parser()
    args = parser.parse_args()

    if not any([args.mysql, args.postgres, args.mock]):
        parser.print_help()
        print("\n⚠️  请指定至少一个数据源: --mysql, --postgres, 或 --mock")
        sys.exit(1)

    result = run_analysis(args)

    if args.json:
        print(json.dumps(result, indent=2, default=str))

    # 打印摘要
    if "summary" in result:
        s = result["summary"]
        print("\n" + "=" * 60)
        print("  📊 事务分析摘要")
        print("=" * 60)
        print(f"  事务总数:           {s['total_transactions']}")
        print(f"  提交事务:           {s['commit_count']} ({s['commit_rate']:.1%})")
        print(f"  回滚事务:           {s['rollback_count']} ({1 - s['commit_rate']:.1%})")
        print(f"  P95 持续时间:       {s['duration_p95_ms']:.0f} ms")
        print(f"  P99 持续时间:       {s['duration_p99_ms']:.0f} ms")
        print(f"  P95 锁等待:         {s['lock_wait_p95_ms']:.0f} ms")
        print(f"  大事务数:           {s['large_txn_count']}")
        print(f"  双重阈值命中:       {s['dual_threshold_count']}")
        print(f"  死锁事件:           {s['deadlock_count']}")
        print(f"  回滚率:             {s.get('rollback_rate', 0):.1%}")
        print(f"  空闲事务告警:       {s.get('idle_txn_count', 0)} (严重: {s.get('idle_critical_count', 0)})")
        print(f"  影响预估:           {s.get('impact_estimated_rows', 0)} 行 / {s.get('impact_estimated_bytes', 0) / 1024 / 1024:.1f} MB")
        if s["time_range"]["start"]:
            print(f"  时间范围:           {s['time_range']['start']} ~ {s['time_range']['end']}")
        print(f"  报告路径:           {result.get('report_path', 'N/A') or 'N/A'}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
