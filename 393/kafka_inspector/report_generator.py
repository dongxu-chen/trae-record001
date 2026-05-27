import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from tabulate import tabulate

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_config = config.get('output', {})
        self.report_dir = self.output_config.get('report_dir', './reports')
        self.formats = self.output_config.get('format', ['html', 'json'])
        
        os.makedirs(self.report_dir, exist_ok=True)

    def _get_status_color(self, status: str) -> str:
        colors = {
            'HEALTHY': '#28a745',
            'WARNING': '#ffc107',
            'CRITICAL': '#dc3545',
            'ERROR': '#6c757d',
            'NO_DATA': '#6c757d',
            'SKIPPED': '#6c757d',
            'UNKNOWN': '#6c757d'
        }
        return colors.get(status, '#6c757d')

    def _get_overall_status(self, results: Dict[str, Any]) -> str:
        statuses = []
        for key, value in results.items():
            if isinstance(value, dict) and 'status' in value:
                statuses.append(value['status'])
        
        if 'CRITICAL' in statuses:
            return 'CRITICAL'
        elif 'ERROR' in statuses:
            return 'ERROR'
        elif 'WARNING' in statuses:
            return 'WARNING'
        elif 'HEALTHY' in statuses:
            return 'HEALTHY'
        return 'UNKNOWN'

    def generate_json_report(self, results: Dict[str, Any]) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"kafka_inspection_report_{timestamp}.json"
        filepath = os.path.join(self.report_dir, filename)
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': self._get_overall_status(results),
            'results': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report generated: {filepath}")
        return filepath

    def generate_markdown_report(self, results: Dict[str, Any]) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"kafka_inspection_report_{timestamp}.md"
        filepath = os.path.join(self.report_dir, filename)
        
        overall_status = self._get_overall_status(results)
        
        md_content = f"""# Kafka集群巡检报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**整体状态**: {overall_status}

---

## 目录
1. [Broker健康状态](#broker健康状态)
2. [ISR副本状态](#isr副本状态)
3. [ISR历史记录](#isr历史记录)
4. [消费者积压状态](#消费者积压状态)
5. [消费延迟趋势分析](#消费延迟趋势分析)
6. [Topic分区分布](#topic分区分布)
7. [机架分布分析](#机架分布分析)
8. [热点Topic自动再平衡](#热点topic自动再平衡)
9. [数据压缩收益分析](#数据压缩收益分析)
10. [JMX指标](#jmx指标)
11. [Prometheus指标](#prometheus指标)
12. [性能瓶颈分析](#性能瓶颈分析)
13. [优化建议](#优化建议)

---

## Broker健康状态
"""
        
        broker_health = results.get('kafka_admin', {}).get('broker_health', {})
        if broker_health:
            md_content += f"""
**状态**: {broker_health.get('status', 'UNKNOWN')}
**Broker总数**: {broker_health.get('total_brokers', 0)}
**在线Broker**: {broker_health.get('online_brokers', 0)}
**离线Broker**: {broker_health.get('offline_brokers', 0)}

### Broker详情
"""
            broker_table = []
            for broker in broker_health.get('brokers', []):
                broker_table.append([
                    broker.get('id'),
                    broker.get('host'),
                    broker.get('port'),
                    broker.get('status'),
                    '是' if broker.get('is_controller') else '否'
                ])
            
            md_content += tabulate(
                broker_table,
                headers=['ID', 'Host', 'Port', '状态', '是否Controller'],
                tablefmt='pipe'
            )
            
            if broker_health.get('issues'):
                md_content += "\n\n### 问题\n"
                for issue in broker_health['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## ISR副本状态\n"
        
        isr_status = results.get('kafka_admin', {}).get('isr_status', {})
        if isr_status:
            md_content += f"""
**状态**: {isr_status.get('status', 'UNKNOWN')}
**Topic总数**: {isr_status.get('total_topics', 0)}
**分区总数**: {isr_status.get('total_partitions', 0)}
**副本不足分区**: {isr_status.get('under_replicated_partitions', 0)}
"""
            if isr_status.get('issues'):
                md_content += "\n### 问题\n"
                for issue in isr_status['issues']:
                    md_content += f"- {issue}\n"

            if isr_status.get('topics_with_issues'):
                md_content += "\n### 有问题的Topic\n"
                for topic in isr_status['topics_with_issues']:
                    md_content += f"- **{topic['topic']}**: {topic['under_replicated_count']}个分区副本不足\n"

        md_content += "\n---\n\n## ISR历史记录\n"

        isr_history = isr_status.get('isr_history', {})
        if isr_history and isr_history.get('status') != 'DISABLED':
            md_content += f"""
**状态**: {isr_history.get('status', 'UNKNOWN')}
**历史缩容事件总数**: {isr_history.get('total_shrink_events', 0)}
**当前活跃缩容数**: {isr_history.get('active_shrinks_count', 0)}
"""
            recovery_stats = isr_history.get('recovery_statistics', {})
            if recovery_stats:
                md_content += f"""
### 恢复时长统计
- **平均恢复时长**: {recovery_stats.get('avg_seconds', 0)}秒
- **中位数(P50)**: {recovery_stats.get('p50_seconds', 0)}秒
- **P95恢复时长**: {recovery_stats.get('p95_seconds', 0)}秒
- **P99恢复时长**: {recovery_stats.get('p99_seconds', 0)}秒
- **总恢复事件数**: {recovery_stats.get('total_recovery_events', 0)}
"""
            if isr_history.get('recent_shrinks'):
                md_content += "\n### 最近缩容事件\n"
                event_table = []
                for event in isr_history['recent_shrinks'][:10]:
                    event_table.append([
                        f"{event.get('topic', '')}-{event.get('partition', '')}",
                        event.get('shrink_time', '')[:19],
                        event.get('recovery_time', '')[:19],
                        f"{event.get('duration_seconds', 0)}秒",
                        f"{event.get('isr_count', 0)}/{event.get('replica_count', 0)}"
                    ])
                md_content += tabulate(
                    event_table,
                    headers=['分区', '缩容时间', '恢复时间', '恢复时长', 'ISR/副本'],
                    tablefmt='pipe'
                )

        md_content += "\n---\n\n## 消费者积压状态\n"
        
        consumer_lag = results.get('kafka_admin', {}).get('consumer_lag', {})
        if consumer_lag:
            md_content += f"""
**状态**: {consumer_lag.get('status', 'UNKNOWN')}
**消费组总数**: {consumer_lag.get('total_groups', 0)}
**有积压的消费组**: {consumer_lag.get('groups_with_lag', 0)}
**总积压消息数**: {consumer_lag.get('total_lag', 0):,}
"""
            if consumer_lag.get('groups'):
                md_content += "\n### Top 10 积压消费组\n"
                lag_table = []
                sorted_groups = sorted(
                    consumer_lag['groups'],
                    key=lambda x: x.get('total_lag', 0),
                    reverse=True
                )[:10]
                for group in sorted_groups:
                    priority = group.get('overall_priority', 'default')
                    priority_label = {
                        'high': '高优',
                        'medium': '中优',
                        'low': '低优',
                        'default': '默认'
                    }.get(priority, priority)
                    lag_table.append([
                        group.get('group_id'),
                        f"{group.get('total_lag', 0):,}",
                        group.get('members', 0),
                        priority_label,
                        group.get('state', 'UNKNOWN'),
                        group.get('status')
                    ])
                
                md_content += tabulate(
                    lag_table,
                    headers=['消费组ID', '总积压', '成员数', '优先级', '状态', '健康状态'],
                    tablefmt='pipe'
                )

            if consumer_lag.get('issues'):
                md_content += "\n\n### 问题\n"
                for issue in consumer_lag['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## 消费延迟趋势分析\n"

        lag_analysis = results.get('consumer_lag_analysis', {})
        if lag_analysis and lag_analysis.get('status') != 'DISABLED':
            md_content += f"""
**状态**: {lag_analysis.get('status', 'UNKNOWN')}
**分析消费组数量**: {lag_analysis.get('total_groups_analyzed', 0)}
**慢消费组数量**: {len(lag_analysis.get('slow_consumers', []))}
**积压增长组数量**: {len(lag_analysis.get('growing_lag_groups', []))}
**无法按时消化组数量**: {len(lag_analysis.get('critical_eta_groups', []))}
"""
            if lag_analysis.get('slow_consumers'):
                md_content += "\n### 慢消费组 (消费速度 < 生产速度的50%)\n"
                slow_table = []
                for slow in lag_analysis['slow_consumers'][:10]:
                    details = lag_analysis.get('group_details', {}).get(slow['group_id'], {})
                    slow_table.append([
                        slow['group_id'],
                        f"{slow.get('consume_rate', 0):.0f}",
                        f"{slow.get('produce_rate', 0):.0f}",
                        f"{slow.get('consumption_ratio', 0)*100:.1f}%",
                        details.get('eta_hours', 'N/A')
                    ])
                md_content += tabulate(
                    slow_table,
                    headers=['消费组ID', '消费速度(msg/s)', '生产速度(msg/s)', '消费比', '预计消化时间'],
                    tablefmt='pipe'
                )

            if lag_analysis.get('growing_lag_groups'):
                md_content += "\n### 积压持续增长的消费组\n"
                growth_table = []
                for growing in lag_analysis['growing_lag_groups'][:10]:
                    growth_table.append([
                        growing['group_id'],
                        f"{growing.get('growth_rate', 0):.0f}"
                    ])
                md_content += tabulate(
                    growth_table,
                    headers=['消费组ID', '积压增长速度(条/秒)'],
                    tablefmt='pipe'
                )

            if lag_analysis.get('issues'):
                md_content += "\n### 问题\n"
                for issue in lag_analysis['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## Topic分区分布\n"
        
        topic_partitions = results.get('kafka_admin', {}).get('topic_partitions', {})
        if topic_partitions:
            md_content += f"""
**状态**: {topic_partitions.get('status', 'UNKNOWN')}
**Topic总数**: {topic_partitions.get('total_topics', 0)}
**分区总数**: {topic_partitions.get('total_partitions', 0)}
"""
            if topic_partitions.get('broker_partition_distribution'):
                md_content += "\n### Broker分区分布\n"
                dist_table = []
                for broker_id, count in topic_partitions['broker_partition_distribution'].items():
                    dist_table.append([broker_id, count])
                
                md_content += tabulate(
                    dist_table,
                    headers=['Broker ID', '分区数'],
                    tablefmt='pipe'
                )

            if topic_partitions.get('issues'):
                md_content += "\n\n### 问题\n"
                for issue in topic_partitions['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## 机架分布分析\n"

        rack_distribution = results.get('kafka_admin', {}).get('rack_distribution', {})
        if rack_distribution and rack_distribution.get('enabled'):
            racks = rack_distribution.get('racks', {})
            md_content += f"""
**状态**: {rack_distribution.get('status', 'UNKNOWN')}
**机架数量**: {len(racks)}
**跨机架副本分布率**: {rack_distribution.get('cross_rack_replication_score', 0)}%
"""
            if racks:
                md_content += "\n### 机架详情\n"
                rack_table = []
                for rack_name, brokers in racks.items():
                    rack_table.append([
                        rack_name,
                        len(brokers),
                        ', '.join(str(b) for b in brokers)
                    ])
                md_content += tabulate(
                    rack_table,
                    headers=['机架名称', 'Broker数量', 'Broker ID'],
                    tablefmt='pipe'
                )

            single_rack = rack_distribution.get('single_rack_topics', [])
            if single_rack:
                md_content += "\n### 单机架副本Topic\n"
                for topic_info in single_rack:
                    md_content += f"- **{topic_info['topic']}**: 所有副本在 {topic_info['rack']}\n"

            if rack_distribution.get('issues'):
                md_content += "\n### 问题\n"
                for issue in rack_distribution['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## 热点Topic自动再平衡\n"

        auto_rebalance = results.get('auto_rebalance', {})
        if auto_rebalance and auto_rebalance.get('status') != 'DISABLED':
            md_content += f"""
**状态**: {auto_rebalance.get('status', 'UNKNOWN')}
**热点Topic数量**: {len(auto_rebalance.get('hot_topics', []))}
**建议扩容Topic数量**: {len(auto_rebalance.get('scale_up_suggestions', []))}
"""
            cluster_load = auto_rebalance.get('cluster_load_status', {})
            if cluster_load:
                md_content += f"""
### 集群负载状态
- **平均CPU使用率**: {cluster_load.get('avg_cpu_usage', 0)}%
- **平均网络流入**: {cluster_load.get('avg_network_in_mbs', 0)} MB/s
- **CPU负载过高**: {'是' if cluster_load.get('is_cpu_heavy') else '否'}
"""

            if auto_rebalance.get('scale_up_suggestions'):
                md_content += "\n### 分区扩容建议\n"
                scale_table = []
                for scale in auto_rebalance['scale_up_suggestions'][:10]:
                    improvement = scale.get('estimated_improvement', {})
                    scale_table.append([
                        scale['topic'],
                        scale['current_partitions'],
                        scale['recommended_partitions'],
                        f"{scale.get('increase_percent', 0)}%",
                        improvement.get('msg_load_reduction_percent', 'N/A')
                    ])
                md_content += tabulate(
                    scale_table,
                    headers=['Topic', '当前分区', '建议分区', '扩容幅度', '预计负载降低'],
                    tablefmt='pipe'
                )

            if auto_rebalance.get('issues'):
                md_content += "\n### 问题\n"
                for issue in auto_rebalance['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## 数据压缩收益分析\n"

        compression = results.get('compression_analysis', {})
        if compression and compression.get('status') != 'DISABLED':
            summary = compression.get('cluster_compression_summary', {})
            md_content += f"""
**状态**: {compression.get('status', 'UNKNOWN')}
**分析Topic数量**: {compression.get('topics_analyzed', 0)}
**未压缩Topic数量**: {len(compression.get('uncompressed_topics', []))}
**已压缩Topic数量**: {len(compression.get('already_compressed_topics', []))}
**压缩建议Topic数量**: {len(compression.get('compression_candidates', []))}
**预计节省磁盘空间**: {compression.get('total_potential_savings_gb', 0):.1f} GB
"""
            if summary:
                md_content += f"""
### 集群压缩概况
- **压缩采用率**: {summary.get('compression_adoption_rate', 0)}%
- **Topic总预估大小**: {summary.get('total_estimated_size_gb', 0):.1f} GB
"""

            if compression.get('compression_candidates'):
                md_content += "\n### 压缩建议\n"
                comp_table = []
                for candidate in compression['compression_candidates'][:10]:
                    comp_table.append([
                        candidate['topic'],
                        f"{candidate.get('estimated_size_gb', 0):.1f}",
                        candidate.get('recommended_compression', '').upper(),
                        f"{candidate.get('estimated_savings_gb', 0):.1f} GB",
                        f"{candidate.get('savings_percent', 0):.1f}%"
                    ])
                md_content += tabulate(
                    comp_table,
                    headers=['Topic', '预估大小(GB)', '建议压缩', '预计节省', '节省比例'],
                    tablefmt='pipe'
                )

            if compression.get('issues'):
                md_content += "\n### 问题\n"
                for issue in compression['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## JMX指标\n"
        
        jmx_metrics = results.get('jmx', {})
        if jmx_metrics:
            md_content += f"""
**状态**: {jmx_metrics.get('status', 'UNKNOWN')}
**Broker总数**: {jmx_metrics.get('total_brokers', 0)}
**健康Broker**: {jmx_metrics.get('healthy_brokers', 0)}
**警告Broker**: {jmx_metrics.get('warning_brokers', 0)}
**严重Broker**: {jmx_metrics.get('critical_brokers', 0)}
"""
            aggregated = jmx_metrics.get('aggregated_metrics', {})
            if aggregated:
                md_content += "\n### 聚合指标\n"
                md_content += f"- **平均CPU使用率**: {aggregated.get('avg_cpu_usage', 'N/A')}%\n"
                md_content += f"- **最高CPU使用率**: {aggregated.get('max_cpu_usage', 'N/A')}%\n"
                md_content += f"- **平均内存使用率**: {aggregated.get('avg_memory_usage_percent', 'N/A')}%\n"
                md_content += f"- **消息流入速率**: {aggregated.get('total_messages_in_per_sec', 'N/A')} msg/s\n"
                md_content += f"- **副本不足分区总数**: {aggregated.get('total_under_replicated_partitions', 0)}\n"

            if jmx_metrics.get('issues'):
                md_content += "\n### 问题\n"
                for issue in jmx_metrics['issues']:
                    md_content += f"- {issue}\n"

        md_content += "\n---\n\n## Prometheus指标\n"
        
        prom_metrics = results.get('prometheus', {})
        if prom_metrics:
            broker_metrics = prom_metrics.get('broker_metrics', {})
            md_content += f"""
**状态**: {broker_metrics.get('status', 'UNKNOWN')}
"""
            if broker_metrics.get('aggregated'):
                agg = broker_metrics['aggregated']
                md_content += f"- **消息流入速率**: {agg.get('total_messages_in_per_sec', 'N/A')} msg/s\n"
                md_content += f"- **分区总数**: {agg.get('total_partitions', 0)}\n"
                md_content += f"- **副本不足分区**: {agg.get('total_under_replicated_partitions', 0)}\n"

        md_content += "\n---\n\n## 性能瓶颈分析\n"
        
        bottleneck = results.get('bottleneck_analysis', {})
        if bottleneck:
            md_content += f"**整体评级**: {bottleneck.get('overall_rating', 'UNKNOWN')}\n\n"
            
            if bottleneck.get('bottlenecks'):
                md_content += "### 检测到的瓶颈\n"
                for bn in bottleneck['bottlenecks']:
                    md_content += f"""
- **{bn.get('type', 'Unknown')}** (严重程度: {bn.get('severity', 'UNKNOWN')})
  - 描述: {bn.get('description', '')}
  - 影响: {bn.get('impact', '')}
"""

        md_content += "\n---\n\n## 优化建议\n"
        
        suggestions = results.get('partition_suggestions', {})
        if suggestions:
            if suggestions.get('imbalanced_topics'):
                md_content += "### 分区不平衡的Topic\n"
                for topic in suggestions['imbalanced_topics'][:5]:
                    md_content += f"- **{topic.get('topic')}**: 建议检查分区分布\n"
            
            if suggestions.get('suggestions'):
                md_content += "\n### 具体建议\n"
                for suggestion in suggestions['suggestions'][:10]:
                    md_content += f"- {suggestion}\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"Markdown report generated: {filepath}")
        return filepath

    def generate_html_report(self, results: Dict[str, Any]) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"kafka_inspection_report_{timestamp}.html"
        filepath = os.path.join(self.report_dir, filename)
        
        overall_status = self._get_overall_status(results)
        status_color = self._get_status_color(overall_status)
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kafka集群巡检报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 16px;
            background-color: {status_color};
            color: white;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .metric-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-card .label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #667eea;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .issues {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 15px;
            border-radius: 4px;
        }}
        .issues h3 {{
            color: #856404;
            margin-bottom: 10px;
        }}
        .issues ul {{
            margin-left: 20px;
        }}
        .status-healthy {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-critical {{ color: #dc3545; }}
        .status-error {{ color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Kafka集群巡检报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>整体状态: <span class="status-badge">{overall_status}</span></p>
        </div>
"""
        
        broker_health = results.get('kafka_admin', {}).get('broker_health', {})
        if broker_health:
            html_content += f"""
        <div class="section">
            <h2>💻 Broker健康状态</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{broker_health.get('total_brokers', 0)}</div>
                    <div class="label">Broker总数</div>
                </div>
                <div class="metric-card">
                    <div class="value status-healthy">{broker_health.get('online_brokers', 0)}</div>
                    <div class="label">在线Broker</div>
                </div>
                <div class="metric-card">
                    <div class="value status-critical">{broker_health.get('offline_brokers', 0)}</div>
                    <div class="label">离线Broker</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(broker_health.get('status', 'UNKNOWN'))}">{broker_health.get('status', 'UNKNOWN')}</div>
                    <div class="label">状态</div>
                </div>
            </div>
"""
            if broker_health.get('brokers'):
                html_content += """
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Host</th>
                        <th>Port</th>
                        <th>状态</th>
                        <th>Controller</th>
                    </tr>
                </thead>
                <tbody>
"""
                for broker in broker_health['brokers']:
                    status_class = f"status-{broker.get('status', '').lower()}"
                    html_content += f"""
                    <tr>
                        <td>{broker.get('id')}</td>
                        <td>{broker.get('host')}</td>
                        <td>{broker.get('port')}</td>
                        <td class="{status_class}">{broker.get('status')}</td>
                        <td>{'✅' if broker.get('is_controller') else '-'}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            if broker_health.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in broker_health['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""
            html_content += "</div>"

        isr_status = results.get('kafka_admin', {}).get('isr_status', {})
        if isr_status:
            html_content += f"""
        <div class="section">
            <h2>📊 ISR副本状态</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{isr_status.get('total_topics', 0)}</div>
                    <div class="label">Topic总数</div>
                </div>
                <div class="metric-card">
                    <div class="value">{isr_status.get('total_partitions', 0)}</div>
                    <div class="label">分区总数</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{isr_status.get('under_replicated_partitions', 0)}</div>
                    <div class="label">副本不足分区</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(isr_status.get('status', 'UNKNOWN'))}">{isr_status.get('status', 'UNKNOWN')}</div>
                    <div class="label">状态</div>
                </div>
            </div>
"""
            if isr_status.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in isr_status['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""

            isr_history = isr_status.get('isr_history', {})
            if isr_history and isr_history.get('status') != 'DISABLED':
                html_content += f"""
            <h3>📜 ISR历史记录</h3>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{isr_history.get('total_shrink_events', 0)}</div>
                    <div class="label">历史缩容事件</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{isr_history.get('active_shrinks_count', 0)}</div>
                    <div class="label">当前活跃缩容</div>
                </div>
                <div class="metric-card">
                    <div class="value">{isr_history.get('average_recovery_seconds', 0)}s</div>
                    <div class="label">平均恢复时长</div>
                </div>
            </div>
"""
                recovery_stats = isr_history.get('recovery_statistics', {})
                if recovery_stats:
                    html_content += """
            <table>
                <thead>
                    <tr>
                        <th>统计指标</th>
                        <th>值(秒)</th>
                    </tr>
                </thead>
                <tbody>
"""
                    stats_rows = [
                        ('平均恢复时长', recovery_stats.get('avg_seconds', 0)),
                        ('中位数(P50)', recovery_stats.get('p50_seconds', 0)),
                        ('P95恢复时长', recovery_stats.get('p95_seconds', 0)),
                        ('P99恢复时长', recovery_stats.get('p99_seconds', 0)),
                        ('最短恢复时长', recovery_stats.get('min_seconds', 0)),
                        ('最长恢复时长', recovery_stats.get('max_seconds', 0))
                    ]
                    for name, value in stats_rows:
                        html_content += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{value}</td>
                    </tr>
"""
                    html_content += """
                </tbody>
            </table>
"""
                if isr_history.get('recent_shrinks'):
                    html_content += """
            <h3>最近缩容事件</h3>
            <table>
                <thead>
                    <tr>
                        <th>分区</th>
                        <th>缩容时间</th>
                        <th>恢复时间</th>
                        <th>恢复时长</th>
                        <th>ISR/副本</th>
                    </tr>
                </thead>
                <tbody>
"""
                    for event in isr_history['recent_shrinks'][:10]:
                        html_content += f"""
                    <tr>
                        <td>{event.get('topic', '')}-{event.get('partition', '')}</td>
                        <td>{event.get('shrink_time', '')[:19]}</td>
                        <td>{event.get('recovery_time', '')[:19]}</td>
                        <td>{event.get('duration_seconds', 0)}s</td>
                        <td>{event.get('isr_count', 0)}/{event.get('replica_count', 0)}</td>
                    </tr>
"""
                    html_content += """
                </tbody>
            </table>
"""
            html_content += "</div>"

        consumer_lag = results.get('kafka_admin', {}).get('consumer_lag', {})
        if consumer_lag:
            html_content += f"""
        <div class="section">
            <h2>⏳ 消费者积压状态</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{consumer_lag.get('total_groups', 0)}</div>
                    <div class="label">消费组总数</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{consumer_lag.get('groups_with_lag', 0)}</div>
                    <div class="label">有积压的消费组</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{consumer_lag.get('total_lag', 0):,}</div>
                    <div class="label">总积压消息数</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(consumer_lag.get('status', 'UNKNOWN'))}">{consumer_lag.get('status', 'UNKNOWN')}</div>
                    <div class="label">状态</div>
                </div>
            </div>
"""
            if consumer_lag.get('groups'):
                html_content += """
            <h3>Top 10 积压消费组</h3>
            <table>
                <thead>
                    <tr>
                        <th>消费组ID</th>
                        <th>总积压</th>
                        <th>成员数</th>
                        <th>优先级</th>
                        <th>状态</th>
                        <th>健康状态</th>
                    </tr>
                </thead>
                <tbody>
"""
                sorted_groups = sorted(
                    consumer_lag['groups'],
                    key=lambda x: x.get('total_lag', 0),
                    reverse=True
                )[:10]
                for group in sorted_groups:
                    status_class = f"status-{group.get('status', '').lower()}"
                    priority = group.get('overall_priority', 'default')
                    priority_label = {
                        'high': '<span style="color:#dc3545;">高优</span>',
                        'medium': '<span style="color:#ffc107;">中优</span>',
                        'low': '<span style="color:#28a745;">低优</span>',
                        'default': '<span style="color:#6c757d;">默认</span>'
                    }.get(priority, priority)
                    html_content += f"""
                    <tr>
                        <td>{group.get('group_id')}</td>
                        <td>{group.get('total_lag', 0):,}</td>
                        <td>{group.get('members', 0)}</td>
                        <td>{priority_label}</td>
                        <td>{group.get('state', 'UNKNOWN')}</td>
                        <td class="{status_class}">{group.get('status')}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            html_content += "</div>"

        lag_analysis = results.get('consumer_lag_analysis', {})
        if lag_analysis and lag_analysis.get('status') != 'DISABLED':
            html_content += f"""
        <div class="section">
            <h2>📈 消费延迟趋势分析</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{lag_analysis.get('total_groups_analyzed', 0)}</div>
                    <div class="label">分析消费组</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{len(lag_analysis.get('slow_consumers', []))}</div>
                    <div class="label">慢消费组</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{len(lag_analysis.get('growing_lag_groups', []))}</div>
                    <div class="label">积压增长组</div>
                </div>
                <div class="metric-card">
                    <div class="value status-critical">{len(lag_analysis.get('critical_eta_groups', []))}</div>
                    <div class="label">预计超时组</div>
                </div>
            </div>
"""
            if lag_analysis.get('slow_consumers'):
                html_content += """
            <h3>慢消费组 (消费速度 < 生产速度的50%)</h3>
            <table>
                <thead>
                    <tr>
                        <th>消费组ID</th>
                        <th>消费速度(msg/s)</th>
                        <th>生产速度(msg/s)</th>
                        <th>消费比</th>
                        <th>预计消化时间</th>
                    </tr>
                </thead>
                <tbody>
"""
                for slow in lag_analysis['slow_consumers'][:10]:
                    details = lag_analysis.get('group_details', {}).get(slow['group_id'], {})
                    eta = details.get('eta_hours', 'N/A')
                    eta_display = f"{eta}小时" if eta != float('inf') and eta != 'N/A' else "持续存在"
                    html_content += f"""
                    <tr>
                        <td>{slow['group_id']}</td>
                        <td>{slow.get('consume_rate', 0):.0f}</td>
                        <td>{slow.get('produce_rate', 0):.0f}</td>
                        <td>{slow.get('consumption_ratio', 0)*100:.1f}%</td>
                        <td>{eta_display}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            if lag_analysis.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in lag_analysis['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""
            html_content += "</div>"

        rack_distribution = results.get('kafka_admin', {}).get('rack_distribution', {})
        if rack_distribution and rack_distribution.get('enabled'):
            racks = rack_distribution.get('racks', {})
            html_content += f"""
        <div class="section">
            <h2>🏗️ 机架分布分析</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{len(racks)}</div>
                    <div class="label">机架数量</div>
                </div>
                <div class="metric-card">
                    <div class="value">{rack_distribution.get('cross_rack_replication_score', 0)}%</div>
                    <div class="label">跨机架副本分布率</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{len(rack_distribution.get('single_rack_topics', []))}</div>
                    <div class="label">单机架副本Topic</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(rack_distribution.get('status', 'UNKNOWN'))}">{rack_distribution.get('status', 'UNKNOWN')}</div>
                    <div class="label">状态</div>
                </div>
            </div>
"""
            if racks:
                html_content += """
            <h3>机架详情</h3>
            <table>
                <thead>
                    <tr>
                        <th>机架名称</th>
                        <th>Broker数量</th>
                        <th>Broker ID</th>
                    </tr>
                </thead>
                <tbody>
"""
                for rack_name, brokers in racks.items():
                    html_content += f"""
                    <tr>
                        <td>{rack_name}</td>
                        <td>{len(brokers)}</td>
                        <td>{', '.join(str(b) for b in brokers)}</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            single_rack = rack_distribution.get('single_rack_topics', [])
            if single_rack:
                html_content += """
            <div class="issues">
                <h3>⚠️ 单机架副本Topic</h3>
                <ul>
"""
                for topic_info in single_rack:
                    html_content += f"<li><strong>{topic_info['topic']}</strong>: 所有副本在 {topic_info['rack']}</li>"
                html_content += """
                </ul>
            </div>
"""
            if rack_distribution.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in rack_distribution['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""
            html_content += "</div>"

        auto_rebalance = results.get('auto_rebalance', {})
        if auto_rebalance and auto_rebalance.get('status') != 'DISABLED':
            html_content += f"""
        <div class="section">
            <h2>⚖️ 热点Topic自动再平衡</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{len(auto_rebalance.get('hot_topics', []))}</div>
                    <div class="label">热点Topic</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{len(auto_rebalance.get('scale_up_suggestions', []))}</div>
                    <div class="label">建议扩容</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(auto_rebalance.get('status', 'UNKNOWN'))}">{auto_rebalance.get('status', 'UNKNOWN')}</div>
                    <div class="label">状态</div>
                </div>
            </div>
"""
            cluster_load = auto_rebalance.get('cluster_load_status', {})
            if cluster_load:
                html_content += f"""
            <h3>集群负载状态</h3>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>平均CPU使用率</td>
                        <td>{cluster_load.get('avg_cpu_usage', 0)}%</td>
                    </tr>
                    <tr>
                        <td>平均网络流入</td>
                        <td>{cluster_load.get('avg_network_in_mbs', 0)} MB/s</td>
                    </tr>
                    <tr>
                        <td>CPU负载过高</td>
                        <td>{'是' if cluster_load.get('is_cpu_heavy') else '否'}</td>
                    </tr>
                </tbody>
            </table>
"""
            if auto_rebalance.get('scale_up_suggestions'):
                html_content += """
            <h3>分区扩容建议</h3>
            <table>
                <thead>
                    <tr>
                        <th>Topic</th>
                        <th>当前分区</th>
                        <th>建议分区</th>
                        <th>扩容幅度</th>
                        <th>预计负载降低</th>
                    </tr>
                </thead>
                <tbody>
"""
                for scale in auto_rebalance['scale_up_suggestions'][:10]:
                    improvement = scale.get('estimated_improvement', {})
                    html_content += f"""
                    <tr>
                        <td>{scale['topic']}</td>
                        <td>{scale['current_partitions']}</td>
                        <td>{scale['recommended_partitions']}</td>
                        <td>{scale.get('increase_percent', 0)}%</td>
                        <td>{improvement.get('msg_load_reduction_percent', 'N/A')}%</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            if auto_rebalance.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in auto_rebalance['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""
            html_content += "</div>"

        compression = results.get('compression_analysis', {})
        if compression and compression.get('status') != 'DISABLED':
            html_content += f"""
        <div class="section">
            <h2>🗜️ 数据压缩收益分析</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value">{compression.get('topics_analyzed', 0)}</div>
                    <div class="label">分析Topic</div>
                </div>
                <div class="metric-card">
                    <div class="value">{len(compression.get('uncompressed_topics', []))}</div>
                    <div class="label">未压缩Topic</div>
                </div>
                <div class="metric-card">
                    <div class="value status-warning">{len(compression.get('compression_candidates', []))}</div>
                    <div class="label">建议压缩Topic</div>
                </div>
                <div class="metric-card">
                    <div class="value" style="color: #28a745;">{compression.get('total_potential_savings_gb', 0):.1f} GB</div>
                    <div class="label">预计节省空间</div>
                </div>
            </div>
"""
            summary = compression.get('cluster_compression_summary', {})
            if summary:
                html_content += f"""
            <h3>集群压缩概况</h3>
            <table>
                <thead>
                    <tr>
                        <th>指标</th>
                        <th>值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>压缩采用率</td>
                        <td>{summary.get('compression_adoption_rate', 0)}%</td>
                    </tr>
                    <tr>
                        <td>Topic总预估大小</td>
                        <td>{summary.get('total_estimated_size_gb', 0):.1f} GB</td>
                    </tr>
                </tbody>
            </table>
"""
            if compression.get('compression_candidates'):
                html_content += """
            <h3>压缩建议</h3>
            <table>
                <thead>
                    <tr>
                        <th>Topic</th>
                        <th>预估大小(GB)</th>
                        <th>建议压缩</th>
                        <th>预计节省</th>
                        <th>节省比例</th>
                    </tr>
                </thead>
                <tbody>
"""
                for candidate in compression['compression_candidates'][:10]:
                    html_content += f"""
                    <tr>
                        <td>{candidate['topic']}</td>
                        <td>{candidate.get('estimated_size_gb', 0):.1f}</td>
                        <td><strong>{candidate.get('recommended_compression', '').upper()}</strong></td>
                        <td>{candidate.get('estimated_savings_gb', 0):.1f} GB</td>
                        <td>{candidate.get('savings_percent', 0):.1f}%</td>
                    </tr>
"""
                html_content += """
                </tbody>
            </table>
"""
            if compression.get('issues'):
                html_content += """
            <div class="issues">
                <h3>⚠️ 问题</h3>
                <ul>
"""
                for issue in compression['issues']:
                    html_content += f"<li>{issue}</li>"
                html_content += """
                </ul>
            </div>
"""
            html_content += "</div>"

        bottleneck = results.get('bottleneck_analysis', {})
        if bottleneck:
            html_content += f"""
        <div class="section">
            <h2>🔧 性能瓶颈分析</h2>
            <div class="metric-cards">
                <div class="metric-card">
                    <div class="value" style="color: {self._get_status_color(bottleneck.get('overall_rating', 'UNKNOWN'))}">{bottleneck.get('overall_rating', 'UNKNOWN')}</div>
                    <div class="label">整体评级</div>
                </div>
                <div class="metric-card">
                    <div class="value">{len(bottleneck.get('bottlenecks', []))}</div>
                    <div class="label">检测到的瓶颈数</div>
                </div>
            </div>
"""
            if bottleneck.get('bottlenecks'):
                html_content += "<h3>检测到的瓶颈</h3>"
                for bn in bottleneck['bottlenecks']:
                    severity_color = self._get_status_color(bn.get('severity', 'UNKNOWN'))
                    html_content += f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {severity_color};">
                <h4 style="color: {severity_color}; margin-bottom: 8px;">{bn.get('type', 'Unknown')} - {bn.get('severity', 'UNKNOWN')}</h4>
                <p><strong>描述:</strong> {bn.get('description', '')}</p>
                <p><strong>影响:</strong> {bn.get('impact', '')}</p>
            </div>
"""
            html_content += "</div>"

        suggestions = results.get('partition_suggestions', {})
        if suggestions:
            html_content += """
        <div class="section">
            <h2>💡 优化建议</h2>
"""
            if suggestions.get('suggestions'):
                html_content += "<ul style='margin-left: 20px;'>"
                for suggestion in suggestions['suggestions'][:15]:
                    html_content += f"<li style='margin-bottom: 8px;'>{suggestion}</li>"
                html_content += "</ul>"
            html_content += "</div>"

        html_content += """
    </div>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {filepath}")
        return filepath

    def generate_all(self, results: Dict[str, Any]) -> Dict[str, str]:
        generated_files = {}
        
        if 'json' in self.formats:
            generated_files['json'] = self.generate_json_report(results)
        if 'markdown' in self.formats or 'md' in self.formats:
            generated_files['markdown'] = self.generate_markdown_report(results)
        if 'html' in self.formats:
            generated_files['html'] = self.generate_html_report(results)
        
        return generated_files
