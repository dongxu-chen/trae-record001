#!/usr/bin/env python3
"""
MySQL主从延迟修复工具
功能：
- 主从延迟监控与分析
- 延迟趋势预测
- 大事务检测
- 并行复制配置推荐
- 规则引擎自动优化
- 主从故障切换演练
- 回放分析
- 主从一致性校验
"""

import os
import sys
import time
import json
import yaml
import logging
import signal
import argparse
from datetime import datetime
from typing import Dict, Any

from mysql_replication_tool.mysql_connection import MySQLConnection
from mysql_replication_tool.monitor import Monitor
from mysql_replication_tool.latency_analyzer import LatencyAnalyzer
from mysql_replication_tool.predictor import LatencyPredictor
from mysql_replication_tool.large_transaction_detector import LargeTransactionDetector
from mysql_replication_tool.parallel_replication_optimizer import ParallelReplicationOptimizer
from mysql_replication_tool.rule_engine import RuleEngine, RuleAction, ActionType
from mysql_replication_tool.failover_drill import FailoverDrill
from mysql_replication_tool.replay_analyzer import ReplayAnalyzer
from mysql_replication_tool.consistency_checker import ConsistencyChecker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('replication_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class ReplicationMonitorTool:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.running = False
        self._init_components()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件加载成功: {config_path}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise

    def _init_components(self) -> None:
        logger.info("正在初始化组件...")

        mysql_config = self.config.get('mysql', {})
        self.master_conn = MySQLConnection(
            host=mysql_config['master']['host'],
            port=mysql_config['master']['port'],
            user=mysql_config['master']['user'],
            password=mysql_config['master']['password'],
            database=mysql_config['master'].get('database', 'mysql')
        )

        self.slave_conn = MySQLConnection(
            host=mysql_config['slave']['host'],
            port=mysql_config['slave']['port'],
            user=mysql_config['slave']['user'],
            password=mysql_config['slave']['password'],
            database=mysql_config['slave'].get('database', 'mysql')
        )

        self.monitor = Monitor(self.master_conn, self.slave_conn, self.config)
        self.analyzer = LatencyAnalyzer(self.master_conn, self.slave_conn, self.config)
        self.predictor = LatencyPredictor(self.config)
        self.transaction_detector = LargeTransactionDetector(
            self.master_conn, self.slave_conn, self.config)
        self.parallel_optimizer = ParallelReplicationOptimizer(self.slave_conn, self.config)
        self.rule_engine = RuleEngine(self.config)
        self.failover_drill = FailoverDrill(self.master_conn, self.slave_conn, self.config)
        self.replay_analyzer = ReplayAnalyzer(self.master_conn, self.slave_conn, self.config)
        self.consistency_checker = ConsistencyChecker(self.master_conn, self.slave_conn, self.config)

        logger.info("所有组件初始化完成")

    def _setup_signal_handlers(self) -> None:
        def signal_handler(signum, frame):
            logger.info("收到停止信号，正在优雅关闭...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def run_once(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info(f"开始执行检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        metrics = self.monitor.collect_metrics()
        self.predictor.add_history(metrics.seconds_behind_master, metrics.timestamp)
        self.predictor.add_network_latency(metrics.network_latency_ms)
        prediction = self.predictor.predict()
        analysis = self.analyzer.analyze(metrics)
        large_transactions = self.transaction_detector.detect_large_transactions()
        parallel_config = self.parallel_optimizer.analyze_and_recommend()

        context = {
            'metrics': metrics,
            'analysis': analysis,
            'prediction': prediction,
            'large_transactions': large_transactions,
            'parallel_config': parallel_config
        }

        actions = self.rule_engine.evaluate(context)

        for action in actions:
            self._execute_action(action)

        result = self._generate_report(metrics, analysis, prediction,
                                        large_transactions, parallel_config, actions)

        logger.info("检查完成")
        logger.info("=" * 60)
        return result

    def _execute_action(self, action: RuleAction) -> None:
        logger.info(f"执行动作: {action.action_type.value} - {action.reason}")

        if action.action_type == ActionType.ALERT:
            self._send_alert(action)
        elif action.action_type == ActionType.KILL_TRANSACTION:
            self._kill_transactions(action)
        elif action.action_type == ActionType.ADJUST_PARALLEL_WORKERS:
            self._adjust_parallel_workers(action)
        elif action.action_type == ActionType.AUTO_RESTART_REPLICATION:
            self._restart_replication(action)

    def _send_alert(self, action: RuleAction) -> None:
        params = action.parameters
        level = params.get('level', 'WARNING')
        message = params.get('message', '未知告警')

        if level == 'CRITICAL':
            logger.critical(f"[ALERT CRITICAL] {message}")
        else:
            logger.warning(f"[ALERT {level}] {message}")

        if self.config.get('alerts', {}).get('enabled', False):
            pass

    def _kill_transactions(self, action: RuleAction) -> None:
        thread_ids = action.parameters.get('thread_ids', [])
        for tid in thread_ids:
            try:
                logger.info(f"尝试KILL事务线程: {tid}")
                self.master_conn.execute_update(f"KILL {tid}")
                logger.info(f"成功KILL线程: {tid}")
            except Exception as e:
                logger.error(f"KILL线程 {tid} 失败: {str(e)}")

    def _adjust_parallel_workers(self, action: RuleAction) -> None:
        changes = action.parameters.get('configuration_changes', [])
        for change in changes:
            try:
                sql = change['sql_command']
                logger.info(f"执行配置调整: {sql}")
                self.slave_conn.execute_update(sql)
                logger.info("配置调整成功")
            except Exception as e:
                logger.error(f"配置调整失败: {str(e)}")

    def _restart_replication(self, action: RuleAction) -> None:
        try:
            logger.info("正在重启复制进程...")
            self.slave_conn.execute_update("STOP SLAVE")
            time.sleep(2)
            self.slave_conn.execute_update("START SLAVE")
            logger.info("复制进程重启成功")
        except Exception as e:
            logger.error(f"重启复制失败: {str(e)}")

    def _generate_report(self, metrics, analysis, prediction,
                          large_transactions, parallel_config, actions) -> Dict[str, Any]:
        perf = parallel_config.slave_performance
        report = {
            'timestamp': datetime.now().isoformat(),
            'status_summary': self.monitor.get_replication_status_summary(),
            'latency_analysis': self.analyzer.get_detailed_diagnosis(analysis),
            'prediction': self.predictor.get_prediction_summary(prediction) if prediction else None,
            'large_transactions': self.transaction_detector.get_transaction_summary(large_transactions),
            'parallel_replication': {
                'current_workers': parallel_config.current_workers,
                'recommended_workers': parallel_config.recommended_workers,
                'changes_count': len(parallel_config.configuration_changes),
                'expected_improvement': parallel_config.expected_improvement,
                'performance_level': perf.performance_level.value,
                'performance_score': perf.performance_score,
                'cpu_cores': perf.cpu_core_count,
                'buffer_pool_hit_rate': perf.buffer_pool_hit_rate
            },
            'actions_taken': [
                {
                    'type': a.action_type.value,
                    'reason': a.reason,
                    'executed': a.executed
                }
                for a in actions
            ]
        }
        return report

    def run_continuous(self) -> None:
        self.running = True
        self._setup_signal_handlers()

        check_interval = self.config.get('monitoring', {}).get('check_interval', 30)
        logger.info(f"开始持续监控，检查间隔: {check_interval}秒")

        while self.running:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"检查周期出错: {str(e)}", exc_info=True)

            for _ in range(check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self) -> None:
        self.running = False
        logger.info("正在关闭连接...")
        self.master_conn.close()
        self.slave_conn.close()
        logger.info("工具已停止")

    def analyze_only(self) -> Dict[str, Any]:
        logger.info("执行一次性分析...")
        return self.run_once()

    def run_failover_drill(self, dry_run: bool = True) -> Dict[str, Any]:
        logger.info(f"执行主从切换演练 (dry_run={dry_run})...")
        result = self.failover_drill.run_drill()
        report = self.failover_drill.get_drill_report(result)
        self._print_failover_report(report)
        return report

    def run_replay_analysis(self, dry_run: bool = True) -> Dict[str, Any]:
        logger.info(f"执行回放分析 (dry_run={dry_run})...")
        statements = self.replay_analyzer.analyze_from_slow_log()
        if not statements:
            statements = self.replay_analyzer.analyze_from_binlog()
        result = self.replay_analyzer.replay_statements(statements, dry_run=dry_run)
        report = self.replay_analyzer.get_replay_report(result)
        self._print_replay_report(report)
        return report

    def run_consistency_check(self) -> Dict[str, Any]:
        logger.info("执行主从一致性校验...")
        result = self.consistency_checker.run_full_check()
        report = self.consistency_checker.get_check_report(result)
        self._print_consistency_report(report)
        return report

    def print_report(self, report: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("MySQL主从延迟修复工具 - 分析报告")
        print("=" * 60)

        status = report['status_summary']
        print(f"\n【复制状态】")
        print(f"  状态: {status['status']}")
        print(f"  延迟: {status['seconds_behind_master']:.2f} 秒")
        print(f"  IO线程运行: {'是' if status['slave_io_running'] else '否'}")
        print(f"  SQL线程运行: {'是' if status['slave_sql_running'] else '否'}")

        analysis = report['latency_analysis']
        print(f"\n【延迟分析】")
        print(f"  主要原因: {analysis['primary_cause']}")
        print(f"  置信度: {analysis['confidence']:.2%}")
        print(f"  所有原因: {', '.join([f'{k}({v:.2f})' for k, v in analysis['all_causes'].items()])}")

        print(f"\n【优化建议】")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"  {i}. {rec}")

        if report['prediction']:
            pred = report['prediction']
            print(f"\n【延迟预测】")
            print(f"  趋势: {pred['trend']}")
            print(f"  趋势强度: {pred['trend_strength']:.4f}")
            print(f"  预测将超标: {'是' if pred['will_exceed_threshold'] else '否'}")
            print(f"  最大预测值(原始): {pred['max_predicted']:.2f} 秒")
            print(f"  最大预测值(修正): {pred['max_predicted_adjusted']:.2f} 秒")
            print(f"  网络抖动因子: {pred['network_jitter_factor']:.4f}")
            print(f"  抖动影响: {pred['jitter_impact_percent']:.2f}%")

        lt = report['large_transactions']
        print(f"\n【大事务检测】")
        print(f"  大事务数量: {lt['count']}")
        print(f"  最长运行时间: {lt['max_duration']} 秒")
        print(f"  最大影响行数: {lt['max_rows_affected']}")
        print(f"  最大估算字节: {lt['max_bytes']:,} bytes")
        print(f"  最高风险评分: {lt['max_score']:.1f} 分")
        print(f"  大小分布: {', '.join([f'{k}={v}' for k, v in lt.get('size_distribution', {}).items()])}")
        print(f"  阻塞事务数: {lt['blocking_count']}")
        print(f"  高风险事务: {lt['high_risk_count']}")

        pr = report['parallel_replication']
        print(f"\n【并行复制优化】")
        print(f"  从库性能等级: {pr['performance_level'].upper()} ({pr['performance_score']:.0f}分)")
        print(f"  CPU核心数: {pr['cpu_cores']}")
        print(f"  缓冲池命中率: {pr['buffer_pool_hit_rate']:.2f}%")
        print(f"  当前Worker数: {pr['current_workers']}")
        print(f"  推荐Worker数: {pr['recommended_workers']}")
        print(f"  配置变更数: {pr['changes_count']}")
        print(f"  预期性能提升: {pr['expected_improvement']:.1f}%")

        print(f"\n【执行动作】")
        if report['actions_taken']:
            for action in report['actions_taken']:
                print(f"  - {action['type']}: {action['reason']}")
        else:
            print(f"  无")

        print("\n" + "=" * 60 + "\n")

    def _print_failover_report(self, report: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("主从切换演练报告")
        print("=" * 60)
        print(f"\n  演练ID: {report['drill_id']}")
        print(f"  状态: {report['status']}")
        print(f"  模式: {'模拟' if report['dry_run'] else '实机'}")
        print(f"  总耗时: {report['total_duration_ms']:.0f}ms")
        print(f"  可回滚: {'是' if report['can_rollback'] else '否'}")
        print(f"\n  【步骤详情】")
        for step in report['steps']:
            status_icon = "✓" if step['status'] == 'success' else "✗"
            print(f"    {status_icon} {step['step']}: {step['status']} ({step['duration_ms']:.0f}ms)")
            if step.get('error'):
                print(f"       错误: {step['error']}")
        print(f"\n  【原始拓扑】")
        om = report.get('original_master', {})
        os_info = report.get('original_slave', {})
        print(f"    主库: {om.get('host', '')}:{om.get('port', '')}")
        print(f"    从库: {os_info.get('host', '')}:{os_info.get('port', '')}")
        print(f"\n  {report.get('summary', '')}")
        print("=" * 60 + "\n")

    def _print_replay_report(self, report: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("回放分析报告")
        print("=" * 60)
        print(f"\n  总语句数: {report['total_statements']}")
        print(f"  成功: {report['successful_statements']}")
        print(f"  失败: {report['failed_statements']}")
        print(f"  最大延迟增长: {report['max_delay_increase_sec']:.2f}秒")
        print(f"  平均延迟增长: {report['avg_delay_increase_sec']:.2f}秒")
        print(f"  总影响行数: {report['total_rows_affected']}")
        print(f"  总估算字节: {report['total_estimated_bytes']:,}")
        print(f"\n  【延迟影响曲线】")
        curve = report.get('delay_impact_curve', [])
        for idx, delay in curve[:10]:
            bar = "█" * min(int(delay), 50)
            print(f"    语句{idx}: {delay:.2f}s {bar}")
        print(f"\n  【瓶颈分析】")
        ba = report.get('bottleneck_analysis', {})
        if ba.get('worst_type'):
            print(f"    最影响延迟的事务类型: {ba['worst_type']} (总延迟: {ba.get('worst_type_delay', 0):.2f}s)")
        print(f"\n  【建议】")
        for rec in report.get('recommendations', []):
            print(f"    - {rec}")
        print("=" * 60 + "\n")

    def _print_consistency_report(self, report: Dict[str, Any]) -> None:
        print("\n" + "=" * 60)
        print("主从一致性校验报告")
        print("=" * 60)
        print(f"\n  校验ID: {report['check_id']}")
        print(f"  总表数: {report['tables_checked']}")
        print(f"  一致: {report['tables_consistent']}")
        print(f"  不一致: {report['tables_inconsistent']}")
        print(f"  错误: {report['tables_error']}")
        print(f"  跳过: {report['tables_skipped']}")
        print(f"  一致率: {report['consistency_rate']:.1f}%")
        if report.get('gtid_consistent') is not None:
            print(f"  GTID一致性: {'是' if report['gtid_consistent'] else '否'}")
        if report.get('inconsistent_tables'):
            print(f"\n  【不一致的表】")
            for t in report['inconsistent_tables']:
                print(f"    - {t['database']}.{t['table']} (方法: {t['method']})", end="")
                if t.get('master_count', -1) >= 0:
                    print(f" 主库:{t['master_count']} 从库:{t['slave_count']}", end="")
                if t.get('sample_mismatches', 0) > 0:
                    print(f" 抽样不匹配:{t['sample_mismatches']}/{t['sample_total']}", end="")
                print()
        if report.get('recommendations'):
            print(f"\n  【建议】")
            for rec in report['recommendations']:
                print(f"    - {rec}")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='MySQL主从延迟修复工具')
    parser.add_argument('-c', '--config', default='config/config.yaml',
                        help='配置文件路径')
    parser.add_argument('-m', '--mode',
                        choices=['once', 'daemon', 'analyze', 'failover', 'failover-live',
                                 'replay', 'replay-live', 'consistency'],
                        default='analyze', help='运行模式')
    parser.add_argument('--output', help='报告输出文件路径')

    args = parser.parse_args()

    if not os.path.exists(args.config):
        logger.error(f"配置文件不存在: {args.config}")
        sys.exit(1)

    try:
        tool = ReplicationMonitorTool(args.config)

        if args.mode == 'daemon':
            tool.run_continuous()
        elif args.mode == 'once':
            tool.run_once()
            tool.stop()
        elif args.mode == 'failover':
            report = tool.run_failover_drill(dry_run=True)
            tool.stop()
        elif args.mode == 'failover-live':
            report = tool.run_failover_drill(dry_run=False)
            tool.stop()
        elif args.mode == 'replay':
            report = tool.run_replay_analysis(dry_run=True)
            tool.stop()
        elif args.mode == 'replay-live':
            report = tool.run_replay_analysis(dry_run=False)
            tool.stop()
        elif args.mode == 'consistency':
            report = tool.run_consistency_check()
            tool.stop()
        else:
            report = tool.analyze_only()
            tool.print_report(report)
            tool.stop()

        if args.output and 'report' in dir():
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"报告已保存到: {args.output}")

    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
