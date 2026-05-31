import React, { useEffect, useState } from 'react';
import { Button, Card, Row, Col, Statistic, Table, Tag, Alert, Descriptions, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import { PerformanceBaseline, BaselineComparison, TestReport } from '../types';
import { getBaselineList, getBestBaseline, compareWithBaseline, deleteBaseline } from '../utils/api';
import { getReportList } from '../utils/api';

const BaselinePage: React.FC = () => {
  const [baselines, setBaselines] = useState<PerformanceBaseline[]>([]);
  const [comparison, setComparison] = useState<BaselineComparison | null>(null);
  const [reports, setReports] = useState<TestReport[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [bl, rp] = await Promise.all([getBaselineList(), getReportList()]);
        setBaselines(bl);
        setReports(rp);
      } catch (e) { console.error(e); }
    };
    fetchData();
  }, []);

  const handleCompare = async (testId: string) => {
    try {
      const result = await compareWithBaseline(testId);
      setComparison(result);
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (id: string) => {
    await deleteBaseline(id);
    setBaselines(prev => prev.filter(b => b.id !== id));
  };

  const getBaselineComparisonChart = () => {
    if (baselines.length < 2) return {};
    const sorted = [...baselines].sort((a, b) => a.createdTime - b.createdTime);
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['Avg QPS', 'Avg Latency', 'P99 Latency'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: sorted.map(b => new Date(b.createdTime).toLocaleDateString()) },
      yAxis: [
        { type: 'value', name: 'QPS' },
        { type: 'value', name: 'Latency (μs)' },
      ],
      series: [
        { name: 'Avg QPS', type: 'bar', data: sorted.map(b => b.avgQps), itemStyle: { color: '#3b82f6' } },
        { name: 'Avg Latency', type: 'line', yAxisIndex: 1, data: sorted.map(b => b.avgLatency), smooth: true, itemStyle: { color: '#10b981' } },
        { name: 'P99 Latency', type: 'line', yAxisIndex: 1, data: sorted.map(b => b.p99Latency), smooth: true, itemStyle: { color: '#ef4444' } },
      ],
    };
  };

  const baselineColumns = [
    { title: '算法', dataIndex: 'algorithm', key: 'algo', render: (a: string) => <Tag color="blue">{a}</Tag> },
    { title: '线程数', dataIndex: 'threadCount', key: 'tc' },
    { title: 'Avg QPS', dataIndex: 'avgQps', key: 'qps', render: (v: number) => <span className="font-mono">{v?.toFixed(1)}</span> },
    { title: 'Avg Latency', dataIndex: 'avgLatency', key: 'lat', render: (v: number) => <span className="font-mono">{v?.toFixed(2)} μs</span> },
    { title: 'P99', dataIndex: 'p99Latency', key: 'p99', render: (v: number) => <span className="font-mono text-orange-600">{v?.toFixed(2)} μs</span> },
    { title: '创建时间', dataIndex: 'createdTime', key: 'ct', render: (ts: number) => new Date(ts).toLocaleString() },
    { title: '最佳', dataIndex: 'isBest', key: 'best', render: (b: boolean) => b ? <Tag color="gold">🏆 最佳</Tag> : <Tag>普通</Tag> },
    { title: '操作', key: 'action', render: (_: unknown, record: PerformanceBaseline) => (
      <Button type="link" danger size="small" onClick={() => handleDelete(record.id)}>删除</Button>
    )},
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">📏 性能基线</h2>
        <p className="text-gray-500 mt-1">管理性能基线，对比历史最佳性能，检测性能退化</p>
      </div>

      {baselines.length > 0 && (
        <Row gutter={16}>
          {baselines.filter(b => b.isBest).map(best => (
            <Col span={24} key={best.id}>
              <Card className="border-2 border-yellow-400 bg-yellow-50">
                <Row gutter={16}>
                  <Col span={4} className="flex items-center justify-center">
                    <span className="text-5xl">🏆</span>
                  </Col>
                  <Col span={20}>
                    <h3 className="text-lg font-bold text-yellow-800 mb-2">历史最佳 - {best.algorithm}</h3>
                    <Row gutter={16}>
                      <Col span={6}><Statistic title="Avg QPS" value={best.avgQps?.toFixed(1)} suffix="/s" /></Col>
                      <Col span={6}><Statistic title="Avg Latency" value={best.avgLatency?.toFixed(2)} suffix="μs" /></Col>
                      <Col span={6}><Statistic title="P99 Latency" value={best.p99Latency?.toFixed(2)} suffix="μs" /></Col>
                      <Col span={6}><Statistic title="线程数" value={best.threadCount} /></Col>
                    </Row>
                  </Col>
                </Row>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {comparison && comparison.hasBaseline && (
        <Card title="📊 与基线对比" size="small">
          <Alert
            message={`总体评估: ${comparison.overallVerdict === 'IMPROVED' ? '✅ 性能提升' : comparison.overallVerdict === 'DEGRADED' ? '⚠️ 性能退化' : '➡️ 性能持平'}`}
            type={comparison.overallVerdict === 'IMPROVED' ? 'success' : comparison.overallVerdict === 'DEGRADED' ? 'warning' : 'info'}
            showIcon
            className="mb-4"
          />
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small" bordered={false} className={comparison.qpsChangePercent >= 0 ? 'bg-green-50' : 'bg-red-50'}>
                <Statistic
                  title="QPS 变化"
                  value={comparison.qpsChangePercent}
                  precision={2}
                  suffix="%"
                  prefix={comparison.qpsChangePercent >= 0 ? '↑' : '↓'}
                  valueStyle={{ color: comparison.qpsChangePercent >= 0 ? '#52c41a' : '#f5222d' }}
                />
                <div className="text-xs text-gray-500 mt-1">
                  基线: {comparison.baselineAvgQps?.toFixed(1)} → 当前: {comparison.currentAvgQps?.toFixed(1)}
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" bordered={false} className={comparison.latencyChangePercent <= 0 ? 'bg-green-50' : 'bg-red-50'}>
                <Statistic
                  title="延迟变化"
                  value={comparison.latencyChangePercent}
                  precision={2}
                  suffix="%"
                  prefix={comparison.latencyChangePercent <= 0 ? '↓' : '↑'}
                  valueStyle={{ color: comparison.latencyChangePercent <= 0 ? '#52c41a' : '#f5222d' }}
                />
                <div className="text-xs text-gray-500 mt-1">
                  基线: {comparison.baselineAvgLatency?.toFixed(2)} → 当前: {comparison.currentAvgLatency?.toFixed(2)} μs
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" bordered={false} className={comparison.p99ChangePercent <= 0 ? 'bg-green-50' : 'bg-red-50'}>
                <Statistic
                  title="P99 变化"
                  value={comparison.p99ChangePercent}
                  precision={2}
                  suffix="%"
                  prefix={comparison.p99ChangePercent <= 0 ? '↓' : '↑'}
                  valueStyle={{ color: comparison.p99ChangePercent <= 0 ? '#52c41a' : '#f5222d' }}
                />
                <div className="text-xs text-gray-500 mt-1">
                  基线: {comparison.baselineP99Latency?.toFixed(2)} → 当前: {comparison.currentP99Latency?.toFixed(2)} μs
                </div>
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      {baselines.length >= 2 && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 基线历史趋势</h3>
          <ReactECharts option={getBaselineComparisonChart()} style={{ height: '300px' }} />
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">所有基线</h3>
        <Table dataSource={baselines} columns={baselineColumns} rowKey="id" size="small" />
      </div>

      {reports.length > 0 && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">与测试报告对比</h3>
          <p className="text-sm text-gray-500 mb-4">选择一个测试报告与基线进行对比</p>
          <div className="flex flex-wrap gap-2">
            {reports.map(r => (
              <Button key={r.id} size="small" onClick={() => handleCompare(r.id)}>
                {r.config?.algorithm} | {r.summary?.avgQps?.toFixed(0)} QPS
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BaselinePage;
