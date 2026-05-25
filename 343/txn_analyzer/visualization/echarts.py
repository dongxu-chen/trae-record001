"""
ECharts Report Generator - ECharts 报告生成器
生成包含多种图表的 HTML 分析报告。
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..analysis.stats import TxnStatistics
from ..analysis.hotspots import HotspotResult
from ..analysis.locks import LockConflictResult, LockHierarchyBuilder
from ..analysis.large_txn import LargeTxnResult
from ..analysis.rollback import RollbackAnalysisResult
from ..analysis.idle_txn import IdleTxnResult
from ..analysis.impact_predictor import TxnImpactPrediction
from ..logger import setup_logger

logger = setup_logger("echarts")


class EChartsReportGenerator:
    """ECharts HTML 报告生成器"""

    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        stats: TxnStatistics,
        hotspot: HotspotResult,
        lock_conflict: LockConflictResult,
        large_txn: LargeTxnResult,
        rollback: Optional[RollbackAnalysisResult] = None,
        idle_txn: Optional[IdleTxnResult] = None,
        impact: Optional[TxnImpactPrediction] = None,
        source_type: str = "Unknown",
        filename: Optional[str] = None,
    ) -> str:
        """生成完整的 HTML 分析报告"""
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"txn_report_{ts}.html"

        filepath = os.path.join(self.output_dir, filename)

        html = self._build_html(
            stats=stats,
            hotspot=hotspot,
            lock_conflict=lock_conflict,
            large_txn=large_txn,
            rollback=rollback,
            idle_txn=idle_txn,
            impact=impact,
            source_type=source_type,
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("报告已生成: %s", filepath)
        return filepath

    # ------------------------------------------------------------------
    #  HTML 构建
    # ------------------------------------------------------------------

    def _build_html(
        self,
        stats: TxnStatistics,
        hotspot: HotspotResult,
        lock_conflict: LockConflictResult,
        large_txn: LargeTxnResult,
        rollback: Optional[RollbackAnalysisResult],
        idle_txn: Optional[IdleTxnResult],
        impact: Optional[TxnImpactPrediction],
        source_type: str,
    ) -> str:
        """构建完整 HTML 页面"""
        report_data = self._build_report_data(
            stats, hotspot, lock_conflict, large_txn, rollback, idle_txn, impact
        )

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库事务分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
                         'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: #0f1117;
            color: #e0e0e0;
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
            padding: 24px 40px;
            border-bottom: 1px solid #2d3748;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 8px;
        }}
        .header .meta {{
            color: #a0aec0;
            font-size: 14px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 24px 40px;
        }}
        .section {{
            background: #1a1f2e;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid #2d3748;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #3182ce;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-title::before {{
            content: '';
            width: 4px;
            height: 20px;
            background: #3182ce;
            border-radius: 2px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: #2d3748;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            border: 1px solid #4a5568;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(49, 130, 206, 0.3);
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: 700;
            color: #63b3ed;
            margin-bottom: 8px;
        }}
        .metric-label {{
            font-size: 13px;
            color: #a0aec0;
        }}
        .chart-container {{
            width: 100%;
            height: 400px;
            margin-bottom: 16px;
        }}
        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }}
        .chart-row .chart-container {{
            height: 350px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #2d3748;
        }}
        th {{
            background: #2d3748;
            color: #a0aec0;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #2d3748;
        }}
        .risk-critical {{ color: #f56565; font-weight: 600; }}
        .risk-high {{ color: #ed8936; font-weight: 600; }}
        .risk-medium {{ color: #ecc94b; font-weight: 600; }}
        .risk-low {{ color: #68d391; font-weight: 600; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-commit {{ background: #22543d; color: #68d391; }}
        .badge-rollback {{ background: #742a2a; color: #f56565; }}
        .tab-nav {{
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .tab-btn {{
            background: #2d3748;
            border: 1px solid #4a5568;
            color: #a0aec0;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }}
        .tab-btn:hover {{ background: #4a5568; color: #fff; }}
        .tab-btn.active {{ background: #3182ce; border-color: #3182ce; color: #fff; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🗄️ 数据库事务分析报告</h1>
        <div class="meta">
            数据源: <strong>{source_type}</strong> |
            生成时间: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong> |
            分析范围: <strong>{stats.time_start or 'N/A'} ~ {stats.time_end or 'N/A'}</strong>
        </div>
    </div>
    <div class="container">
        {self._build_summary_section(stats, large_txn)}
        {self._build_distribution_section(stats)}
        {self._build_hotspot_section(hotspot)}
        {self._build_lock_section(lock_conflict)}
        {self._build_large_txn_section(large_txn)}
        {self._build_rollback_section(rollback) if rollback else ""}
        {self._build_idle_section(idle_txn) if idle_txn else ""}
        {self._build_impact_section(impact) if impact else ""}
        {self._build_deadlock_section(lock_conflict)}
    </div>

    <script>
        const reportData = {json.dumps(report_data, default=str)};

        // ======= 通用配置 =======
        const baseOption = {{
            textStyle: {{ color: '#a0aec0', fontFamily: 'inherit' }},
            backgroundColor: 'transparent',
        }};

        // ======= 指标概览图表 =======
        function renderSummaryCharts() {{
            const txnStatusChart = echarts.init(document.getElementById('chart-txn-status'));
            txnStatusChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} ({{d}}%)' }},
                series: [{{
                    type: 'pie',
                    radius: ['50%', '75%'],
                    avoidLabelOverlap: false,
                    itemStyle: {{ borderRadius: 8, borderColor: '#1a1f2e', borderWidth: 2 }},
                    label: {{ show: true, formatter: '{{b}}\\n{{c}}', color: '#e0e0e0', fontSize: 12 }},
                    data: [
                        {{ value: {stats.commit_count}, name: '提交', itemStyle: {{ color: '#68d391' }} }},
                        {{ value: {stats.rollback_count}, name: '回滚', itemStyle: {{ color: '#f56565' }} }},
                        {{ value: {stats.in_progress_count}, name: '进行中', itemStyle: {{ color: '#f6ad55' }} }},
                    ],
                }}],
            }});

            const riskChart = echarts.init(document.getElementById('chart-risk'));
            riskChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'item', formatter: '{{b}}: {{c}} ({{d}}%)' }},
                series: [{{
                    type: 'pie',
                    radius: ['50%', '75%'],
                    itemStyle: {{ borderRadius: 8, borderColor: '#1a1f2e', borderWidth: 2 }},
                    label: {{ show: true, formatter: '{{b}}\\n{{c}}', color: '#e0e0e0', fontSize: 12 }},
                    data: [
                        {{ value: {large_txn.risk_summary.get('critical_count', 0)}, name: '严重', itemStyle: {{ color: '#f56565' }} }},
                        {{ value: {large_txn.risk_summary.get('high_count', 0)}, name: '高', itemStyle: {{ color: '#ed8936' }} }},
                        {{ value: {large_txn.risk_summary.get('medium_count', 0)}, name: '中', itemStyle: {{ color: '#ecc94b' }} }},
                        {{ value: {large_txn.risk_summary.get('low_count', 0)}, name: '低', itemStyle: {{ color: '#68d391' }} }},
                    ],
                }}],
            }});
        }}

        // ======= 分布图 =======
        function renderDistributionCharts() {{
            const durationChart = echarts.init(document.getElementById('chart-duration'));
            durationChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {json.dumps([d["range"] for d in stats.duration_distribution])},
                    axisLabel: {{ color: '#a0aec0', rotate: 30 }},
                }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ lineStyle: {{ color: '#2d3748' }} }} }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps([d["count"] for d in stats.duration_distribution])},
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#63b3ed' }},
                            {{ offset: 1, color: '#3182ce' }},
                        ]),
                        borderRadius: [4, 4, 0, 0],
                    }},
                }}],
            }});

            const lockChart = echarts.init(document.getElementById('chart-lock'));
            lockChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {json.dumps([d["range"] for d in stats.lock_wait_distribution])},
                    axisLabel: {{ color: '#a0aec0', rotate: 30 }},
                }},
                yAxis: {{ type: 'value', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ lineStyle: {{ color: '#2d3748' }} }} }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps([d["count"] for d in stats.lock_wait_distribution])},
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            {{ offset: 0, color: '#f6ad55' }},
                            {{ offset: 1, color: '#ed8936' }},
                        ]),
                        borderRadius: [4, 4, 0, 0],
                    }},
                }}],
            }});
        }}

        // ======= 热点图表 =======
        function renderHotspotCharts() {{
            const tableChart = echarts.init(document.getElementById('chart-hot-tables'));
            tableChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', containLabel: true }},
                xAxis: {{
                    type: 'value',
                    axisLabel: {{ color: '#a0aec0' }},
                    splitLine: {{ lineStyle: {{ color: '#2d3748' }} }},
                }},
                yAxis: {{
                    type: 'category',
                    data: {json.dumps([t.table_name for t in hotspot.top_tables[:15]])},
                    axisLabel: {{ color: '#a0aec0' }},
                }},
                series: [{{
                    type: 'bar',
                    data: {json.dumps([t.total_ops for t in hotspot.top_tables[:15]])},
                    itemStyle: {{
                        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                            {{ offset: 0, color: '#805ad5' }},
                            {{ offset: 1, color: '#d53f8c' }},
                        ]),
                        borderRadius: [0, 4, 4, 0],
                    }},
                }}],
            }});

            const heatChart = echarts.init(document.getElementById('chart-heatmap'));
            const schemas = [...new Set({json.dumps([h["schema"] for h in hotspot.table_heatmap_data])})].slice(0, 10);
            const tables = [...new Set({json.dumps([h["table"] for h in hotspot.table_heatmap_data])})].slice(0, 10);
            const heatData = {json.dumps(self._build_heatmap_data(hotspot))};

            heatChart.setOption({{
                ...baseOption,
                tooltip: {{ position: 'top', formatter: p => `Schema: ${{schemas[p.value[0]]}}<br/>Table: ${{tables[p.value[1]]}}<br/>Ops: ${{p.value[2]}}` }},
                grid: {{ left: '15%', right: '10%', top: '5%', bottom: '15%' }},
                xAxis: {{
                    type: 'category',
                    data: tables,
                    axisLabel: {{ color: '#a0aec0', rotate: 45, fontSize: 10 }},
                    splitArea: {{ show: true }},
                }},
                yAxis: {{
                    type: 'category',
                    data: schemas,
                    axisLabel: {{ color: '#a0aec0', fontSize: 10 }},
                    splitArea: {{ show: true }},
                }},
                visualMap: {{
                    min: 0,
                    max: Math.max(...heatData.map(d => d[2]), 1),
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '0%',
                    inRange: {{ color: ['#1a1f2e', '#3182ce', '#d53f8c'] }},
                    textStyle: {{ color: '#a0aec0' }},
                }},
                series: [{{
                    type: 'heatmap',
                    data: heatData,
                    label: {{ show: true, color: '#fff', fontSize: 10 }},
                    emphasis: {{ itemStyle: {{ shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }} }},
                }}],
            }});
        }}

        // ======= 锁冲突图表 =======
        function renderLockCharts() {{
            const conflictChart = echarts.init(document.getElementById('chart-lock-conflict'));
            conflictChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                legend: {{ data: ['等待次数', '总等待时间(ms)'], textStyle: {{ color: '#a0aec0' }}, top: 0 }},
                grid: {{ left: '3%', right: '4%', bottom: '3%', top: '15%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: {json.dumps([c.table_name for c in lock_conflict.conflicts[:10]])},
                    axisLabel: {{ color: '#a0aec0', rotate: 30, fontSize: 10 }},
                }},
                yAxis: [
                    {{ type: 'value', name: '等待次数', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ lineStyle: {{ color: '#2d3748' }} }} }},
                    {{ type: 'value', name: '等待时间(ms)', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ show: false }} }},
                ],
                series: [
                    {{
                        type: 'bar',
                        name: '等待次数',
                        data: {json.dumps([c.wait_count for c in lock_conflict.conflicts[:10]])},
                        itemStyle: {{ color: '#f56565', borderRadius: [4, 4, 0, 0] }},
                    }},
                    {{
                        type: 'line',
                        yAxisIndex: 1,
                        name: '总等待时间(ms)',
                        data: {json.dumps([c.total_wait_ms for c in lock_conflict.conflicts[:10]])},
                        smooth: true,
                        lineStyle: {{ color: '#f6ad55', width: 3 }},
                        itemStyle: {{ color: '#f6ad55' }},
                    }},
                ],
            }});

            // 锁继承关系旭日图
            if (reportData.lock_hierarchy && reportData.lock_hierarchy.children && reportData.lock_hierarchy.children.length > 0) {{
                const hierarchyChart = echarts.init(document.getElementById('chart-lock-hierarchy'));
                hierarchyChart.setOption({{
                    ...baseOption,
                    tooltip: {{
                        formatter: p => {{
                            const path = p.treePathInfo ? p.treePathInfo.map(n => n.name).join(' → ') : p.name;
                            return `路径: ${{path}}<br/>事件数: ${{p.data.event_count || p.value}}<br/>等待次数: ${{p.data.wait_count || 0}}<br/>总等待: ${{p.data.total_wait_ms || 0}}ms`;
                        }},
                    }},
                    series: [{{
                        type: 'sunburst',
                        data: reportData.lock_hierarchy.children.map(s => ({{
                            name: s.name,
                            value: s.event_count,
                            event_count: s.event_count,
                            wait_count: s.wait_count,
                            total_wait_ms: s.total_wait_ms,
                            children: s.children.map(t => ({{
                                name: t.name,
                                value: t.event_count,
                                event_count: t.event_count,
                                wait_count: t.wait_count,
                                total_wait_ms: t.total_wait_ms,
                                children: t.children.map(m => ({{
                                    name: m.name,
                                    value: m.event_count,
                                    event_count: m.event_count,
                                    wait_count: m.wait_count,
                                    total_wait_ms: m.total_wait_ms,
                                    itemStyle: {{
                                        color: m.total_wait_ms > 5000 ? '#c53030'
                                             : m.total_wait_ms > 1000 ? '#ed8936'
                                             : m.total_wait_ms > 100 ? '#ecc94b'
                                             : '#68d391',
                                    }},
                                }})),
                            }})),
                        }})),
                        radius: [0, '95%'],
                        sort: null,
                        emphasis: {{ focus: 'ancestor' }},
                        levels: [
                            {{
                                itemStyle: {{ color: '#3182ce', borderWidth: 2, borderColor: '#1a1f2e' }},
                                label: {{ color: '#fff', fontSize: 12, fontWeight: 600, rotate: 0 }},
                            }},
                            {{
                                itemStyle: {{ borderWidth: 1, borderColor: '#2d3748' }},
                                label: {{ color: '#fff', fontSize: 10, rotate: 45 }},
                            }},
                            {{
                                itemStyle: {{ borderWidth: 0.5, borderColor: '#4a5568' }},
                                label: {{ color: '#fff', fontSize: 9, rotate: 90 }},
                            }},
                        ],
                    }}],
                }});
            }}

            // 锁时间线
            if (reportData.lock_timeline && reportData.lock_timeline.length > 0) {{
                const timelineChart = echarts.init(document.getElementById('chart-lock-timeline'));
                timelineChart.setOption({{
                    ...baseOption,
                    tooltip: {{
                        trigger: 'item',
                        formatter: p => `
                            时间: ${{p.value[0]}}<br/>
                            XID: ${{p.data.xid}}<br/>
                            表: ${{p.data.table}}<br/>
                            锁模式: ${{p.data.lock_mode}}<br/>
                            等待: ${{p.data.wait_ms}}ms
                        `,
                    }},
                    grid: {{ left: '3%', right: '4%', bottom: '12%', containLabel: true }},
                    xAxis: {{
                        type: 'time',
                        axisLabel: {{ color: '#a0aec0' }},
                        splitLine: {{ lineStyle: {{ color: '#2d3748' }} }},
                    }},
                    yAxis: {{
                        type: 'category',
                        data: [...new Set(reportData.lock_timeline.map(l => l.table))].slice(0, 20),
                        axisLabel: {{ color: '#a0aec0', fontSize: 10 }},
                    }},
                    series: [{{
                        type: 'scatter',
                        symbolSize: v => Math.min(Math.max(v[2] / 10, 8), 50),
                        data: reportData.lock_timeline.map(l => ({{
                            value: [l.timestamp, l.table, l.wait_ms],
                            xid: l.xid,
                            table: l.table,
                            lock_mode: l.lock_mode,
                            wait_ms: l.wait_ms,
                        }})),
                        itemStyle: {{
                            color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.5, [
                                {{ offset: 0, color: '#f56565' }},
                                {{ offset: 1, color: '#c53030' }},
                            ]),
                            shadowBlur: 10,
                            shadowColor: 'rgba(245, 101, 101, 0.5)',
                        }},
                    }}],
                }});
            }}
        }}

        // ======= 大事务图表 =======
        function renderLargeTxnCharts() {{
            const treemapChart = echarts.init(document.getElementById('chart-treemap'));
            if (reportData.large_txns && reportData.large_txns.length > 0) {{
                treemapChart.setOption({{
                    ...baseOption,
                    tooltip: {{
                        formatter: p => `
                            XID: ${{p.data.xid}}<br/>
                            Schema: ${{p.data.schema}}<br/>
                            持续: ${{p.data.duration_ms}}ms<br/>
                            行操作: ${{p.data.row_ops_count}}<br/>
                            写入: ${{(p.data.bytes_written / 1024 / 1024).toFixed(2)}}MB<br/>
                            风险: ${{p.data.risk_level}}
                        `,
                    }},
                    series: [{{
                        type: 'treemap',
                        roam: false,
                        breadcrumb: {{ show: false }},
                        label: {{ show: true, formatter: p => p.data.xid, color: '#fff', fontSize: 10 }},
                        upperLabel: {{ show: true, color: '#fff', fontSize: 11, fontWeight: 600 }},
                        itemStyle: {{ borderColor: '#1a1f2e', borderWidth: 2, gapWidth: 2 }},
                        levels: [
                            {{
                                itemStyle: {{ borderColor: '#1a1f2e', borderWidth: 0, gapWidth: 1 }},
                                upperLabel: {{ show: false }},
                            }},
                            {{
                                itemStyle: {{ borderColor: '#4a5568', borderWidth: 5, gapWidth: 1 }},
                                colorSaturation: [0.3, 0.6],
                            }},
                            {{
                                colorSaturation: [0.3, 0.6],
                                itemStyle: {{ borderWidth: 1, gapWidth: 1, borderColorSaturation: 0.6 }},
                            }},
                        ],
                        data: reportData.large_txns.map(t => ({{
                            name: t.xid,
                            value: t.bytes_written,
                            ...t,
                            itemStyle: {{
                                color: t.risk_level === 'critical' ? '#c53030'
                                     : t.risk_level === 'high' ? '#ed8936'
                                     : t.risk_level === 'medium' ? '#ecc94b'
                                     : '#68d391',
                            }},
                        }})),
                    }}],
                }});
            }}
        }}

        // ======= 回滚分析图表 =======
        function renderRollbackCharts() {{
            if (!reportData.rollback) return;
            const rbEl = document.getElementById('chart-rollback-schema');
            if (!rbEl) return;
            const rbData = reportData.rollback.schema_patterns || [];
            if (rbData.length === 0) return;
            const rbChart = echarts.init(rbEl);
            rbChart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                grid: {{ left: '3%', right: '4%', bottom: '10%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: rbData.map(d => d.pattern_key),
                    axisLabel: {{ color: '#a0aec0', rotate: 30, fontSize: 11 }},
                }},
                yAxis: {{ type: 'value', name: '回滚次数', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ lineStyle: {{ color: '#2d3748' }} }} }},
                series: [
                    {{
                        type: 'bar',
                        name: '回滚次数',
                        data: rbData.map(d => d.rollback_count),
                        itemStyle: {{ color: '#f56565', borderRadius: [4, 4, 0, 0] }},
                    }},
                    {{
                        type: 'line',
                        name: '回滚率(%)',
                        yAxisIndex: 0,
                        data: rbData.map(d => Math.round(d.rollback_rate * 1000) / 10),
                        smooth: true,
                        lineStyle: {{ color: '#ecc94b', width: 2 }},
                        itemStyle: {{ color: '#ecc94b' }},
                    }},
                ],
            }});
        }}

        // ======= 影响预测图表 =======
        function renderImpactCharts() {{
            if (!reportData.impact) return;
            const el = document.getElementById('chart-impact-bars');
            if (!el) return;
            const tables = reportData.impact.top_tables || [];
            if (tables.length === 0) return;
            const chart = echarts.init(el);
            chart.setOption({{
                ...baseOption,
                tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'shadow' }} }},
                legend: {{ data: ['预估行数', '预估写入(MB)'], textStyle: {{ color: '#a0aec0' }}, top: 0 }},
                grid: {{ left: '3%', right: '4%', bottom: '10%', top: '15%', containLabel: true }},
                xAxis: {{
                    type: 'category',
                    data: tables.map(t => t.table_name),
                    axisLabel: {{ color: '#a0aec0', rotate: 30, fontSize: 11 }},
                }},
                yAxis: [
                    {{ type: 'value', name: '行数', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ lineStyle: {{ color: '#2d3748' }} }} }},
                    {{ type: 'value', name: 'MB', axisLabel: {{ color: '#a0aec0' }}, splitLine: {{ show: false }} }},
                ],
                series: [
                    {{
                        name: '预估行数',
                        type: 'bar',
                        data: tables.map(t => t.total_ops),
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#63b3ed' }},
                                {{ offset: 1, color: '#3182ce' }},
                            ]),
                            borderRadius: [4, 4, 0, 0],
                        }},
                    }},
                    {{
                        name: '预估写入(MB)',
                        type: 'bar',
                        yAxisIndex: 1,
                        data: tables.map(t => Math.round(t.estimated_bytes_total / 1024 / 1024 * 100) / 100),
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#f6ad55' }},
                                {{ offset: 1, color: '#ed8936' }},
                            ]),
                            borderRadius: [4, 4, 0, 0],
                        }},
                    }},
                ],
            }});
        }}

        // ======= 初始化 =======
        window.addEventListener('load', () => {{
            renderSummaryCharts();
            renderDistributionCharts();
            renderHotspotCharts();
            renderLockCharts();
            renderLargeTxnCharts();
            renderRollbackCharts();
            renderImpactCharts();

            window.addEventListener('resize', () => {{
                ['chart-txn-status', 'chart-risk', 'chart-duration', 'chart-lock',
                 'chart-hot-tables', 'chart-heatmap', 'chart-lock-conflict',
                 'chart-lock-timeline', 'chart-lock-hierarchy', 'chart-treemap',
                 'chart-rollback-schema', 'chart-impact-bars'].forEach(id => {{
                    const el = document.getElementById(id);
                    if (el) {{
                        const inst = echarts.getInstanceByDom(el);
                        if (inst) inst.resize();
                    }}
                }});
            }});
        }});

        // Tab 切换
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>"""
        return html

    def _build_summary_section(
        self, stats: TxnStatistics, large_txn: LargeTxnResult
    ) -> str:
        """构建指标概览 section"""
        return f"""
        <div class="section">
            <div class="section-title">📊 核心指标概览</div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{stats.total_txn_count}</div>
                    <div class="metric-label">事务总数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.commit_count}</div>
                    <div class="metric-label">提交事务</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.rollback_count}</div>
                    <div class="metric-label">回滚事务</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.commit_rate:.1%}</div>
                    <div class="metric-label">提交率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.duration_p95:.0f}ms</div>
                    <div class="metric-label">P95 持续时间</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.duration_p99:.0f}ms</div>
                    <div class="metric-label">P99 持续时间</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{stats.lock_wait_p95:.0f}ms</div>
                    <div class="metric-label">P95 锁等待</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{large_txn.risk_summary.get('total_large', 0)}</div>
                    <div class="metric-label">大事务数</div>
                </div>
            </div>
            <div class="chart-row">
                <div id="chart-txn-status" class="chart-container"></div>
                <div id="chart-risk" class="chart-container"></div>
            </div>
        </div>"""

    def _build_distribution_section(self, stats: TxnStatistics) -> str:
        """构建分布图 section"""
        return f"""
        <div class="section">
            <div class="section-title">📈 事务分布</div>
            <div class="chart-row">
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">事务持续时间分布 (ms)</div>
                    <div id="chart-duration" class="chart-container"></div>
                </div>
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">锁等待时间分布 (ms)</div>
                    <div id="chart-lock" class="chart-container"></div>
                </div>
            </div>
        </div>"""

    def _build_hotspot_section(self, hotspot: HotspotResult) -> str:
        """构建热点 section"""
        top_tables_rows = ""
        for t in hotspot.top_tables[:10]:
            top_tables_rows += f"""
                <tr>
                    <td>{t.table_name}</td>
                    <td>{t.total_ops}</td>
                    <td>{t.txn_count}</td>
                    <td>{t.total_lock_wait_ms:.1f}</td>
                    <td>{t.max_lock_wait_ms:.1f}</td>
                    <td>{t.avg_duration_ms:.1f}</td>
                </tr>"""

        top_txn_rows = ""
        for t in hotspot.top_txns[:10]:
            status_badge = (
                '<span class="badge badge-commit">提交</span>' if t["status"] == "COMMIT"
                else '<span class="badge badge-rollback">回滚</span>'
            )
            top_txn_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{t['xid']}</code></td>
                    <td>{t['schema']}</td>
                    <td>{status_badge}</td>
                    <td>{t['duration_ms']:.0f}</td>
                    <td>{t['row_ops']}</td>
                    <td>{t['total_lock_wait_ms']:.0f}</td>
                    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{t['query']}</td>
                </tr>"""

        return f"""
        <div class="section">
            <div class="section-title">🔥 事务热点</div>
            <div class="chart-row">
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">TOP 操作热点表</div>
                    <div id="chart-hot-tables" class="chart-container"></div>
                </div>
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">Schema × Table 操作热力图</div>
                    <div id="chart-heatmap" class="chart-container"></div>
                </div>
            </div>

            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab('tab-tables')">热点表</button>
                <button class="tab-btn" onclick="switchTab('tab-txns')">热点事务</button>
            </div>
            <div id="tab-tables" class="tab-content active">
                <table>
                    <thead>
                        <tr><th>表名</th><th>总操作数</th><th>事务数</th><th>总锁等待(ms)</th><th>最大锁等待(ms)</th><th>平均持续(ms)</th></tr>
                    </thead>
                    <tbody>{top_tables_rows}</tbody>
                </table>
            </div>
            <div id="tab-txns" class="tab-content">
                <table>
                    <thead>
                        <tr><th>XID</th><th>Schema</th><th>状态</th><th>持续(ms)</th><th>行操作</th><th>锁等待(ms)</th><th>SQL</th></tr>
                    </thead>
                    <tbody>{top_txn_rows}</tbody>
                </table>
            </div>
        </div>"""

    def _build_lock_section(self, lock_conflict: LockConflictResult) -> str:
        """构建锁冲突 section"""
        conflict_rows = ""
        for c in lock_conflict.conflicts[:10]:
            conflict_rows += f"""
                <tr>
                    <td>{c.table_name}</td>
                    <td>{c.lock_mode}</td>
                    <td>{c.total_events}</td>
                    <td>{c.wait_count}</td>
                    <td>{c.total_wait_ms:.1f}</td>
                    <td>{c.max_wait_ms:.1f}</td>
                    <td>{c.avg_wait_ms:.1f}</td>
                </tr>"""

        return f"""
        <div class="section">
            <div class="section-title">🔒 锁冲突分析</div>
            <div class="chart-row">
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">TOP 锁等待对象</div>
                    <div id="chart-lock-conflict" class="chart-container"></div>
                </div>
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">锁继承关系 (Schema → Table → Mode)</div>
                    <div id="chart-lock-hierarchy" class="chart-container"></div>
                </div>
            </div>
            <div class="chart-row">
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">锁等待时间线</div>
                    <div id="chart-lock-timeline" class="chart-container"></div>
                </div>
                <div>
                    <div style="color:#a0aec0;font-size:13px;margin-bottom:8px;">锁嵌套关系说明</div>
                    <div class="chart-container" style="display:flex;align-items:center;justify-content:center;background:#2d3748;border-radius:8px;padding:20px;">
                        <div style="text-align:center;color:#a0aec0;line-height:2;">
                            <div style="font-size:16px;color:#63b3ed;margin-bottom:12px;">🔗 锁嵌套规则</div>
                            <div><code>IS</code> → 允许 <code>RS</code> / <code>S</code></div>
                            <div><code>IX</code> → 允许 <code>RX</code> / <code>X</code> / <code>AUTO_INC</code></div>
                            <div><code>S</code> → 包含 <code>RS</code></div>
                            <div><code>X</code> → 包含 <code>RX</code> / <code>AUTO_INC</code></div>
                            <div style="margin-top:10px;font-size:11px;color:#718096;">
                                旭日图扇区大小 = 锁事件数量<br/>
                                颜色深浅 = 等待时间严重程度
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>对象</th><th>锁模式</th><th>总事件</th><th>等待次数</th><th>总等待(ms)</th><th>最大等待(ms)</th><th>平均等待(ms)</th></tr>
                </thead>
                <tbody>{conflict_rows}</tbody>
            </table>
        </div>"""

    def _build_large_txn_section(self, large_txn: LargeTxnResult) -> str:
        """构建大事务 section"""
        large_txn_rows = ""
        for t in large_txn.large_txns[:15]:
            risk_class = f"risk-{t.risk_level}"
            large_txn_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{t.xid}</code></td>
                    <td>{t.schema or 'N/A'}</td>
                    <td>{t.duration_ms:.0f}</td>
                    <td>{t.row_ops_count}</td>
                    <td>{t.bytes_written / 1024 / 1024:.2f}</td>
                    <td>{t.total_lock_wait_ms:.0f}</td>
                    <td>{', '.join(t.tables[:3])}</td>
                    <td class="{risk_class}">{t.risk_level.upper()}</td>
                </tr>"""

        long_running_rows = ""
        for t in large_txn.long_running_txns[:10]:
            long_running_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{t.xid}</code></td>
                    <td>{t.schema or 'N/A'}</td>
                    <td>{t.duration_ms:.0f}</td>
                    <td>{t.row_ops_count}</td>
                    <td>{t.total_lock_wait_ms:.0f}</td>
                    <td>{', '.join(t.tables[:3])}</td>
                </tr>"""

        dual_rows = ""
        for t in large_txn.dual_threshold_txns[:10]:
            risk_class = f"risk-{t.risk_level}"
            dual_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{t.xid}</code></td>
                    <td>{t.schema or 'N/A'}</td>
                    <td>{t.duration_ms:.0f}</td>
                    <td>{t.row_ops_count}</td>
                    <td>{t.bytes_written / 1024 / 1024:.2f}</td>
                    <td>{t.total_lock_wait_ms:.0f}</td>
                    <td class="{risk_class}">{t.risk_level.upper()}</td>
                </tr>"""

        dual_summary = f" (双重阈值: ≥{large_txn.risk_summary.get('bytes_threshold', 0) / 1024 / 1024:.0f}MB 且 ≥{large_txn.risk_summary.get('row_ops_threshold', 0)}行)"

        return f"""
        <div class="section">
            <div class="section-title">⚠️ 大事务检测{dual_summary}</div>
            <div id="chart-treemap" class="chart-container" style="height:300px;"></div>

            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab('tab-large')">按写入量</button>
                <button class="tab-btn" onclick="switchTab('tab-dual')">双重阈值</button>
                <button class="tab-btn" onclick="switchTab('tab-long')">长事务</button>
            </div>
            <div id="tab-large" class="tab-content active">
                <table>
                    <thead>
                        <tr><th>XID</th><th>Schema</th><th>持续(ms)</th><th>行操作</th><th>写入(MB)</th><th>锁等待(ms)</th><th>涉及表</th><th>风险等级</th></tr>
                    </thead>
                    <tbody>{large_txn_rows}</tbody>
                </table>
            </div>
            <div id="tab-dual" class="tab-content">
                <table>
                    <thead>
                        <tr><th>XID</th><th>Schema</th><th>持续(ms)</th><th>行操作</th><th>写入(MB)</th><th>锁等待(ms)</th><th>风险等级</th></tr>
                    </thead>
                    <tbody>{dual_rows if dual_rows else '<tr><td colspan="7" style="text-align:center;color:#a0aec0;padding:20px;">无满足双重阈值的事务</td></tr>'}</tbody>
                </table>
            </div>
            <div id="tab-long" class="tab-content">
                <table>
                    <thead>
                        <tr><th>XID</th><th>Schema</th><th>持续(ms)</th><th>行操作</th><th>锁等待(ms)</th><th>涉及表</th></tr>
                    </thead>
                    <tbody>{long_running_rows}</tbody>
                </table>
            </div>
        </div>"""

    def _build_rollback_section(self, rollback: RollbackAnalysisResult) -> str:
        """构建回滚分析 section"""
        pattern_rows = ""
        for p in rollback.high_risk_patterns[:15]:
            risk_class = f"risk-{p.risk_level}"
            pattern_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{p.pattern_key}</code></td>
                    <td>{p.pattern_type}</td>
                    <td>{p.rollback_count}</td>
                    <td>{p.rollback_rate * 100:.1f}%</td>
                    <td>{p.total_txn_count}</td>
                    <td>{p.avg_duration_ms:.0f}</td>
                    <td>{p.deadlock_victim_count}</td>
                    <td class="{risk_class}">{p.risk_level.upper()}</td>
                </tr>"""

        if not pattern_rows:
            pattern_rows = '<tr><td colspan="8" style="text-align:center;color:#68d391;padding:20px;">✅ 未检测到高频回滚模式</td></tr>'

        summary = rollback.summary
        return f"""
        <div class="section">
            <div class="section-title">🔄 回滚模式分析</div>
            <div class="metrics-grid" style="margin-bottom:16px;">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_rollback', 0)}</div>
                    <div class="metric-label">回滚总数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('overall_rollback_rate', 0) * 100:.1f}%</div>
                    <div class="metric-label">整体回滚率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('deadlock_victim', 0)}</div>
                    <div class="metric-label">死锁受害者</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_high_risk_patterns', 0)}</div>
                    <div class="metric-label">高风险模式</div>
                </div>
            </div>
            <div id="chart-rollback-schema" class="chart-container" style="height:280px;"></div>
            <div class="tab-nav">
                <button class="tab-btn active" onclick="switchTab('tab-rb-patterns')">高风险模式</button>
                <button class="tab-btn" onclick="switchTab('tab-rb-tables')">按表</button>
                <button class="tab-btn" onclick="switchTab('tab-rb-time')">时间段</button>
            </div>
            <div id="tab-rb-patterns" class="tab-content active">
                <table>
                    <thead>
                        <tr><th>模式标识</th><th>类型</th><th>回滚次数</th><th>回滚率</th><th>总事务</th><th>平均时长(ms)</th><th>死锁受害</th><th>风险</th></tr>
                    </thead>
                    <tbody>{pattern_rows}</tbody>
                </table>
            </div>
            <div id="tab-rb-tables" class="tab-content"></div>
            <div id="tab-rb-time" class="tab-content"></div>
        </div>"""

    def _build_idle_section(self, idle_txn: IdleTxnResult) -> str:
        """构建空闲事务检测 section"""
        alert_rows = ""
        for a in idle_txn.alerts[:20]:
            level_class = "risk-critical" if a.alert_level == "critical" else "risk-high"
            alert_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{a.xid}</code></td>
                    <td>{a.user or 'N/A'}@{a.host or 'N/A'}</td>
                    <td>{a.schema or 'N/A'}</td>
                    <td>{a.idle_ms / 1000:.0f}s</td>
                    <td>{a.row_ops_count}</td>
                    <td>{a.total_lock_wait_ms:.0f}</td>
                    <td class="{level_class}">{a.reason}</td>
                    <td class="{level_class}">{a.alert_level.upper()}</td>
                </tr>"""

        if not alert_rows:
            alert_rows = '<tr><td colspan="8" style="text-align:center;color:#68d391;padding:20px;">✅ 未检测到空闲事务</td></tr>'

        summary = idle_txn.summary
        return f"""
        <div class="section">
            <div class="section-title">⏱️ 空闲事务检测</div>
            <div class="metrics-grid" style="margin-bottom:16px;">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_in_progress', 0)}</div>
                    <div class="metric-label">进行中事务</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_long_idle', 0)}</div>
                    <div class="metric-label">长时间空闲</div>
                </div>
                <div class="metric-card" style="border-color:#f56565;">
                    <div class="metric-value" style="color:#f56565;">{summary.get('total_critical', 0)}</div>
                    <div class="metric-label">严重告警</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('affected_connections', 0)}</div>
                    <div class="metric-label">受影响连接</div>
                </div>
            </div>
            <table>
                <thead>
                    <tr><th>XID</th><th>用户@主机</th><th>Schema</th><th>空闲时长</th><th>行操作</th><th>锁等待(ms)</th><th>告警原因</th><th>级别</th></tr>
                </thead>
                <tbody>{alert_rows}</tbody>
            </table>
        </div>"""

    def _build_impact_section(self, impact: TxnImpactPrediction) -> str:
        """构建事务影响预测 section"""
        table_rows = ""
        for t in impact.top_affected_tables:
            risk_class = f"risk-{t.risk_level}"
            table_rows += f"""
                <tr>
                    <td><code style="color:#63b3ed">{t.table_name}</code></td>
                    <td>{t.total_ops}</td>
                    <td>{t.txn_count}</td>
                    <td>{t.avg_rows_per_txn:.1f}</td>
                    <td>{t.p95_rows_per_txn:.1f}</td>
                    <td>{t.estimated_bytes_total / 1024 / 1024:.2f}</td>
                    <td>{t.avg_lock_wait_ms:.0f}</td>
                    <td class="{risk_class}">{t.risk_level.upper()}</td>
                </tr>"""

        if not table_rows:
            table_rows = '<tr><td colspan="8" style="text-align:center;color:#a0aec0;padding:20px;">无数据</td></tr>'

        summary = impact.summary
        return f"""
        <div class="section">
            <div class="section-title">📊 事务影响预测</div>
            <div class="metrics-grid" style="margin-bottom:16px;">
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_rows_estimated', 0):,}</div>
                    <div class="metric-label">预估影响行数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_bytes_estimated', 0) / 1024 / 1024:.1f}MB</div>
                    <div class="metric-label">预估写入量</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('total_lock_wait_ms', 0):.0f}ms</div>
                    <div class="metric-label">总锁等待预估</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary.get('hot_table_count', 0)}</div>
                    <div class="metric-label">热点表数量</div>
                </div>
            </div>
            <div style="background:#2d3748;border-radius:8px;padding:16px;margin-bottom:16px;border-left:4px solid #ecc94b;">
                <strong style="color:#ecc94b;">💡 变更建议：</strong>
                <span style="color:#e0e0e0;">{impact.change_recommendation or '无'}</span>
            </div>
            <div id="chart-impact-bars" class="chart-container" style="height:300px;"></div>
            <table>
                <thead>
                    <tr><th>表名</th><th>总操作数</th><th>事务数</th><th>平均行数</th><th>P95行数</th><th>预估写入(MB)</th><th>平均锁等待(ms)</th><th>风险</th></tr>
                </thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>"""

    def _build_deadlock_section(self, lock_conflict: LockConflictResult) -> str:
        """构建死锁事件 section"""
        deadlock_rows = ""
        for d in lock_conflict.deadlock_events:
            deadlock_rows += f"""
                <tr>
                    <td>{d['timestamp']}</td>
                    <td><code style="color:#63b3ed">{d['txn1_xid']}</code></td>
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d['txn1_query']}</td>
                    <td>{d['txn1_lock']}</td>
                    <td><code style="color:#63b3ed">{d['txn2_xid']}</code></td>
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{d['txn2_query']}</td>
                    <td>{d['txn2_lock']}</td>
                    <td><code style="color:#f56565">{d['victim']}</code></td>
                </tr>"""

        if not deadlock_rows:
            deadlock_rows = '<tr><td colspan="8" style="text-align:center;color:#68d391;padding:20px;">✅ 未检测到死锁事件</td></tr>'

        return f"""
        <div class="section">
            <div class="section-title">💀 死锁事件 ({len(lock_conflict.deadlock_events)})</div>
            <table>
                <thead>
                    <tr>
                        <th>时间</th><th>事务1 XID</th><th>事务1 SQL</th><th>事务1 锁</th>
                        <th>事务2 XID</th><th>事务2 SQL</th><th>事务2 锁</th><th>被回滚</th>
                    </tr>
                </thead>
                <tbody>{deadlock_rows}</tbody>
            </table>
        </div>"""

    @staticmethod
    def _build_heatmap_data(hotspot: HotspotResult) -> list:
        """预计算热力图数据，避免 JS 端变量引用问题"""
        schemas = list(dict.fromkeys([h["schema"] for h in hotspot.table_heatmap_data]))[:10]
        tables = list(dict.fromkeys([h["table"] for h in hotspot.table_heatmap_data]))[:10]
        data = []
        for h in hotspot.table_heatmap_data:
            if h["schema"] in schemas and h["table"] in tables:
                data.append(
                    [schemas.index(h["schema"]), tables.index(h["table"]), h["ops"]]
                )
        return data

    def _build_report_data(
        self,
        stats: TxnStatistics,
        hotspot: HotspotResult,
        lock_conflict: LockConflictResult,
        large_txn: LargeTxnResult,
        rollback: Optional[RollbackAnalysisResult] = None,
        idle_txn: Optional[IdleTxnResult] = None,
        impact: Optional[TxnImpactPrediction] = None,
    ) -> Dict[str, Any]:
        """构建 JS 端使用的数据"""
        hierarchy_builder = LockHierarchyBuilder()
        lock_hierarchy = hierarchy_builder.build_from_conflicts(lock_conflict.conflicts)

        data: Dict[str, Any] = {
            "lock_timeline": lock_conflict.lock_timeline,
            "large_txns": [t.to_dict() for t in large_txn.large_txns[:50]],
            "lock_hierarchy": lock_hierarchy.to_dict(),
            "dual_threshold_txns": [t.to_dict() for t in large_txn.dual_threshold_txns[:20]],
        }

        if rollback:
            data["rollback"] = {
                "summary": rollback.summary,
                "schema_patterns": [p.to_dict() for p in rollback.schema_patterns[:15]],
                "table_patterns": [p.to_dict() for p in rollback.table_patterns[:15]],
                "query_patterns": [p.to_dict() for p in rollback.query_patterns[:15]],
                "time_patterns": [p.to_dict() for p in rollback.time_patterns[:20]],
                "high_risk": [p.to_dict() for p in rollback.high_risk_patterns[:15]],
            }
        if idle_txn:
            data["idle"] = {
                "summary": idle_txn.summary,
                "alerts": [a.to_dict() for a in idle_txn.alerts[:30]],
                "connection_stats": idle_txn.connection_stats,
                "schema_stats": idle_txn.schema_stats,
            }
        if impact:
            data["impact"] = {
                "summary": impact.summary,
                "top_tables": [t.to_dict() for t in impact.top_affected_tables],
                "hot_tables": [t.to_dict() for t in impact.hot_table_patterns],
                "recommendation": impact.change_recommendation,
            }

        return data


def generate_report(
    stats: TxnStatistics,
    hotspot: HotspotResult,
    lock_conflict: LockConflictResult,
    large_txn: LargeTxnResult,
    rollback: Optional[RollbackAnalysisResult] = None,
    idle_txn: Optional[IdleTxnResult] = None,
    impact: Optional[TxnImpactPrediction] = None,
    output_dir: str = "./reports",
    source_type: str = "Unknown",
    filename: Optional[str] = None,
) -> str:
    """便捷函数：生成报告"""
    generator = EChartsReportGenerator(output_dir)
    return generator.generate(stats, hotspot, lock_conflict, large_txn, rollback, idle_txn, impact, source_type, filename)
