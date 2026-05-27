#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kafka集群巡检工具
=================

功能：
1. Broker健康状态检查
2. ISR副本状态检查
3. 消费者积压检查
4. Topic分区分布检查
5. JMX指标收集（CPU、内存、磁盘、网络）
6. Prometheus指标收集
7. 性能瓶颈分析
8. Topic分区分配建议
9. 多格式巡检报告输出（HTML、JSON、Markdown）
10. Grafana仪表板可视化

作者：Kafka Inspector Team
版本：1.0.0
"""

import os
import sys
import logging
import argparse
import yaml
import json
from datetime import datetime
from typing import Dict, Any

from kafka_inspector.kafka_admin_check import KafkaAdminChecker
from kafka_inspector.jmx_collector import JMXCollector
from kafka_inspector.prometheus_collector import PrometheusCollector
from kafka_inspector.bottleneck_analyzer import BottleneckAnalyzer
from kafka_inspector.partition_advisor import PartitionAdvisor
from kafka_inspector.report_generator import ReportGenerator
from kafka_inspector.consumer_lag_analyzer import ConsumerLagAnalyzer
from kafka_inspector.auto_rebalancer import AutoRebalancer
from kafka_inspector.compression_advisor import CompressionAdvisor


def setup_logging(config: Dict[str, Any]) -> None:
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO').upper(), logging.INFO)
    log_file = log_config.get('file', './logs/kafka_inspector.log')
    
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info(f"配置文件加载成功: {config_path}")
        return config
    except Exception as e:
        logging.error(f"配置文件加载失败: {str(e)}")
        sys.exit(1)


def run_inspection(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    logging.info("=" * 60)
    logging.info("开始执行Kafka集群巡检")
    logging.info("=" * 60)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'kafka_admin': {},
        'jmx': {},
        'prometheus': {},
        'bottleneck_analysis': {},
        'partition_suggestions': {},
        'consumer_lag_analysis': {},
        'auto_rebalance': {},
        'compression_analysis': {}
    }
    
    if not args.skip_kafka:
        logging.info("\n[1/8] 开始Kafka Admin API检查...")
        try:
            kafka_checker = KafkaAdminChecker(config)
            results['kafka_admin'] = kafka_checker.run_all_checks()
            logging.info("Kafka Admin API检查完成")
        except Exception as e:
            logging.error(f"Kafka Admin API检查失败: {str(e)}")
            results['kafka_admin'] = {'error': str(e)}
    else:
        logging.info("[1/8] 跳过Kafka Admin API检查")
    
    if not args.skip_jmx:
        logging.info("\n[2/8] 开始JMX指标收集...")
        try:
            jmx_collector = JMXCollector(config)
            results['jmx'] = jmx_collector.collect_all()
            logging.info("JMX指标收集完成")
        except Exception as e:
            logging.error(f"JMX指标收集失败: {str(e)}")
            results['jmx'] = {'error': str(e)}
    else:
        logging.info("[2/8] 跳过JMX指标收集")
    
    if not args.skip_prometheus:
        logging.info("\n[3/8] 开始Prometheus指标收集...")
        try:
            prom_collector = PrometheusCollector(config)
            results['prometheus'] = prom_collector.collect_all()
            logging.info("Prometheus指标收集完成")
        except Exception as e:
            logging.error(f"Prometheus指标收集失败: {str(e)}")
            results['prometheus'] = {'error': str(e)}
    else:
        logging.info("[3/8] 跳过Prometheus指标收集")
    
    if not args.skip_analysis:
        logging.info("\n[4/8] 开始性能瓶颈分析...")
        try:
            analyzer = BottleneckAnalyzer(config)
            results['bottleneck_analysis'] = analyzer.analyze(results)
            logging.info("性能瓶颈分析完成")
        except Exception as e:
            logging.error(f"性能瓶颈分析失败: {str(e)}")
            results['bottleneck_analysis'] = {'error': str(e)}
    else:
        logging.info("[4/8] 跳过性能瓶颈分析")
    
    if not args.skip_suggestions:
        logging.info("\n[5/8] 开始生成优化建议...")
        try:
            advisor = PartitionAdvisor(config)
            results['partition_suggestions'] = advisor.generate_suggestions(results)
            logging.info("优化建议生成完成")
        except Exception as e:
            logging.error(f"优化建议生成失败: {str(e)}")
            results['partition_suggestions'] = {'error': str(e)}
    else:
        logging.info("[5/8] 跳过优化建议生成")

    if not args.skip_analysis:
        logging.info("\n[6/8] 开始消费延迟趋势分析...")
        try:
            lag_analyzer = ConsumerLagAnalyzer(config)
            consumer_lag = results.get('kafka_admin', {}).get('consumer_lag', {})
            prom_data = results.get('prometheus', {})
            results['consumer_lag_analysis'] = lag_analyzer.analyze_lag_trend(
                consumer_lag, prom_data
            )
            logging.info("消费延迟趋势分析完成")
        except Exception as e:
            logging.error(f"消费延迟趋势分析失败: {str(e)}")
            results['consumer_lag_analysis'] = {'error': str(e)}
    else:
        logging.info("[6/8] 跳过消费延迟趋势分析")

    if not args.skip_analysis:
        logging.info("\n[7/8] 开始热点Topic自动再平衡分析...")
        try:
            rebalancer = AutoRebalancer(config)
            topic_partitions = results.get('kafka_admin', {}).get('topic_partitions', {})
            prom_data = results.get('prometheus', {})
            jmx_data = results.get('jmx', {})
            consumer_lag = results.get('kafka_admin', {}).get('consumer_lag', {})
            results['auto_rebalance'] = rebalancer.analyze_hot_topics(
                topic_partitions, prom_data, jmx_data, consumer_lag
            )
            logging.info("热点Topic自动再平衡分析完成")
        except Exception as e:
            logging.error(f"热点Topic自动再平衡分析失败: {str(e)}")
            results['auto_rebalance'] = {'error': str(e)}
    else:
        logging.info("[7/8] 跳过热点Topic自动再平衡分析")

    if not args.skip_analysis:
        logging.info("\n[8/8] 开始数据压缩收益分析...")
        try:
            compression_advisor = CompressionAdvisor(config)
            topic_partitions = results.get('kafka_admin', {}).get('topic_partitions', {})
            prom_data = results.get('prometheus', {})
            jmx_data = results.get('jmx', {})
            results['compression_analysis'] = compression_advisor.analyze_compression_opportunities(
                topic_partitions, prom_data, jmx_data
            )
            logging.info("数据压缩收益分析完成")
        except Exception as e:
            logging.error(f"数据压缩收益分析失败: {str(e)}")
            results['compression_analysis'] = {'error': str(e)}
    else:
        logging.info("[8/8] 跳过数据压缩收益分析")
    
    logging.info("\n" + "=" * 60)
    logging.info("Kafka集群巡检执行完成")
    logging.info("=" * 60)
    
    return results


def print_summary(results: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("巡检结果摘要")
    print("=" * 60)
    
    kafka_status = results.get('kafka_admin', {}).get('broker_health', {}).get('status', 'UNKNOWN')
    isr_status = results.get('kafka_admin', {}).get('isr_status', {}).get('status', 'UNKNOWN')
    lag_status = results.get('kafka_admin', {}).get('consumer_lag', {}).get('status', 'UNKNOWN')
    jmx_status = results.get('jmx', {}).get('status', 'UNKNOWN')
    bottleneck_rating = results.get('bottleneck_analysis', {}).get('overall_rating', 'UNKNOWN')
    
    print(f"Broker健康状态: {kafka_status}")
    print(f"ISR副本状态: {isr_status}")
    print(f"消费者积压: {lag_status}")
    print(f"JMX指标状态: {jmx_status}")
    print(f"性能瓶颈评级: {bottleneck_rating}")

    isr_history = results.get('kafka_admin', {}).get('isr_status', {}).get('isr_history', {})
    if isr_history and isr_history.get('status') != 'DISABLED':
        print(f"\nISR历史记录:")
        print(f"  历史缩容事件数: {isr_history.get('total_shrink_events', 0)}")
        print(f"  当前活跃缩容数: {isr_history.get('active_shrinks_count', 0)}")
        recovery_stats = isr_history.get('recovery_statistics', {})
        if recovery_stats:
            print(f"  平均恢复时长: {recovery_stats.get('avg_seconds', 0)}秒")
            print(f"  P95恢复时长: {recovery_stats.get('p95_seconds', 0)}秒")

    rack_distribution = results.get('kafka_admin', {}).get('rack_distribution', {})
    if rack_distribution and rack_distribution.get('enabled'):
        print(f"\n机架分布:")
        print(f"  机架数量: {len(rack_distribution.get('racks', {}))}")
        print(f"  跨机架副本分布率: {rack_distribution.get('cross_rack_replication_score', 0)}%")
        single_rack = rack_distribution.get('single_rack_topics', [])
        if single_rack:
            print(f"  单机架副本Topic: {len(single_rack)}个")
            for topic_info in single_rack[:3]:
                print(f"    - {topic_info['topic']}: {topic_info['rack']}")

    consumer_lag = results.get('kafka_admin', {}).get('consumer_lag', {})
    if consumer_lag:
        high_priority_groups = [
            g for g in consumer_lag.get('groups', [])
            if g.get('overall_priority') == 'high' and g.get('status') in ('WARNING', 'CRITICAL')
        ]
        if high_priority_groups:
            print(f"\n高优Topic消费组告警:")
            for group in high_priority_groups[:3]:
                print(f"  - {group['group_id']}: {group['total_lag']:,} 积压 (状态: {group['status']})")
    
    bottleneck = results.get('bottleneck_analysis', {})
    if bottleneck:
        print(f"\n检测到 {bottleneck.get('bottleneck_count', 0)} 个性能瓶颈:")
        print(f"  - 严重: {bottleneck.get('critical_count', 0)}")
        print(f"  - 警告: {bottleneck.get('warning_count', 0)}")
    
    suggestions = results.get('partition_suggestions', {})
    if suggestions and suggestions.get('suggestions'):
        print(f"\n生成 {len(suggestions['suggestions'])} 条优化建议")

    lag_analysis = results.get('consumer_lag_analysis', {})
    if lag_analysis and lag_analysis.get('status') != 'DISABLED':
        print(f"\n消费延迟分析:")
        if lag_analysis.get('slow_consumers'):
            print(f"  消费速度较慢的消费组: {len(lag_analysis['slow_consumers'])}个")
            for slow in lag_analysis['slow_consumers'][:3]:
                print(f"    - {slow['group_id']}: 消费比 {slow.get('consumption_ratio', 0)*100:.1f}%")
        if lag_analysis.get('growing_lag_groups'):
            print(f"  积压持续增长的消费组: {len(lag_analysis['growing_lag_groups'])}个")
            for growing in lag_analysis['growing_lag_groups'][:3]:
                print(f"    - {growing['group_id']}: 增长 {growing.get('growth_rate', 0):.0f} 条/秒")
        if lag_analysis.get('critical_eta_groups'):
            print(f"  预计无法在72小时内消化的消费组: {len(lag_analysis['critical_eta_groups'])}个")
            for eta in lag_analysis['critical_eta_groups'][:3]:
                eta_hours = eta.get('eta_hours', 0)
                if eta_hours == float('inf'):
                    print(f"    - {eta['group_id']}: 积压将持续存在")
                else:
                    print(f"    - {eta['group_id']}: 预计 {eta_hours:.1f} 小时消化完")

    auto_rebalance = results.get('auto_rebalance', {})
    if auto_rebalance and auto_rebalance.get('status') != 'DISABLED':
        print(f"\n自动再平衡分析:")
        if auto_rebalance.get('hot_topics'):
            print(f"  检测到热点Topic: {len(auto_rebalance['hot_topics'])}个")
            for hot in auto_rebalance['hot_topics'][:3]:
                print(f"    - {hot['topic']}: {hot['messages_in_per_sec']:.0f} msg/s")
        if auto_rebalance.get('scale_up_suggestions'):
            print(f"  建议扩容的Topic: {len(auto_rebalance['scale_up_suggestions'])}个")
            for scale in auto_rebalance['scale_up_suggestions'][:3]:
                print(f"    - {scale['topic']}: {scale['current_partitions']} -> {scale['recommended_partitions']} 分区")

    compression = results.get('compression_analysis', {})
    if compression and compression.get('status') != 'DISABLED':
        print(f"\n压缩收益分析:")
        summary = compression.get('cluster_compression_summary', {})
        if summary:
            print(f"  已启用压缩Topic占比: {summary.get('compression_adoption_rate', 0)}%")
            print(f"  未压缩Topic: {summary.get('uncompressed_topics_count', 0)}个")
        if compression.get('compression_candidates'):
            print(f"  建议启用压缩的Topic: {len(compression['compression_candidates'])}个")
            print(f"  预计可节省磁盘空间: {compression.get('total_potential_savings_gb', 0):.1f} GB")
            for candidate in compression['compression_candidates'][:3]:
                print(f"    - {candidate['topic']}: 建议 {candidate['recommended_compression'].upper()} "
                      f"节省 {candidate['estimated_savings_gb']:.1f} GB ({candidate['savings_percent']:.1f}%)")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Kafka集群巡检工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置执行完整巡检
  python main.py
  
  # 指定配置文件
  python main.py --config /path/to/config.yaml
  
  # 跳过JMX收集
  python main.py --skip-jmx
  
  # 仅输出JSON报告
  python main.py --format json
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='配置文件路径 (默认: config.yaml)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['html', 'json', 'markdown', 'all'],
        default='all',
        help='报告输出格式 (默认: all)'
    )
    
    parser.add_argument(
        '--skip-kafka',
        action='store_true',
        help='跳过Kafka Admin API检查'
    )
    
    parser.add_argument(
        '--skip-jmx',
        action='store_true',
        help='跳过JMX指标收集'
    )
    
    parser.add_argument(
        '--skip-prometheus',
        action='store_true',
        help='跳过Prometheus指标收集'
    )
    
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='跳过性能瓶颈分析'
    )
    
    parser.add_argument(
        '--skip-suggestions',
        action='store_true',
        help='跳过优化建议生成'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='报告输出目录 (覆盖配置文件中的设置)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅加载配置，不执行实际检查'
    )
    
    parser.add_argument(
        '--suggest-partition',
        type=str,
        metavar='MSG_RATE',
        help='根据预期消息速率(条/秒)推荐分区数，如: --suggest-partition 10000'
    )
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    setup_logging(config)
    
    if args.output_dir:
        config['output']['report_dir'] = args.output_dir
    
    if args.format != 'all':
        config['output']['format'] = [args.format]
    
    if args.suggest_partition:
        try:
            msg_rate = float(args.suggest_partition)
            advisor = PartitionAdvisor(config)
            suggestion = advisor.suggest_partition_count(msg_rate)
            print("\n" + "=" * 60)
            print("分区数推荐")
            print("=" * 60)
            print(f"预期消息速率: {msg_rate:,.0f} 条/秒")
            print(f"推荐分区数: {suggestion['recommended_partitions']}")
            print(f"推荐副本数: {suggestion['recommended_replicas']}")
            print(f"预估最大吞吐量: {suggestion['estimated_max_throughput_mbs']} MB/s")
            print("=" * 60)
            return
        except ValueError:
            logging.error("消息速率必须是数字")
            sys.exit(1)
    
    if args.dry_run:
        logging.info("Dry run模式，配置加载完成，不执行巡检")
        print("配置文件验证通过！")
        print(f"Kafka集群: {config['kafka']['bootstrap_servers']}")
        print(f"JMX主机: {', '.join(config['jmx']['jmx_hosts'])}")
        print(f"Prometheus: {config['prometheus']['url']}")
        print(f"报告格式: {', '.join(config['output']['format'])}")
        print(f"报告目录: {config['output']['report_dir']}")
        return
    
    results = run_inspection(config, args)
    
    print_summary(results)
    
    logging.info("\n开始生成报告...")
    report_generator = ReportGenerator(config)
    report_files = report_generator.generate_all(results)
    
    print("\n报告已生成:")
    for fmt, path in report_files.items():
        print(f"  {fmt.upper()}: {path}")
    
    logging.info("巡检任务完成！")


if __name__ == '__main__':
    main()
