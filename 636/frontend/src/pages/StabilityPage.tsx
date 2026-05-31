import React, { useState, useEffect } from 'react';
import { InputNumber, Button, Alert, Card, Row, Col, Statistic, Table, Tag, Switch, Slider, Select } from 'antd';
import ReactECharts from 'echarts-for-react';
import { IdAlgorithm, StabilityTestConfig, StabilityTestReport, StabilityCheckpoint, AnomalyEvent } from '../types';
import { startStabilityTest, stopStabilityTest, getStabilityReportList } from '../utils/api';

const { Option } = Select;

const StabilityPage: React.FC = () => {
  const [algorithm, setAlgorithm] = useState<IdAlgorithm>('SNOWFLAKE');
  const [threadCount, setThreadCount] = useState(10);
  const [durationHours, setDurationHours] = useState(168);
  const [checkpointMinutes, setCheckpointMinutes] = useState(5);
  const [autoRecovery, setAutoRecovery] = useState(true);
  const [qpsThreshold, setQpsThreshold] = useState(0.2);
  const [latencyThreshold, setLatencyThreshold] = useState(0.3);
  const [errorThreshold, setErrorThreshold] = useState(0.01);
  const [loading, setLoading] = useState(false);
  const [runningTestId, setRunningTestId] = useState<string | null>(null);
  const [reports, setReports] = useState<StabilityTestReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<StabilityTestReport | null>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const list = await getStabilityReportList();
        setReports(list);
      } catch (e) { console.error(e); }
    };
    fetchReports();
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      const config: StabilityTestConfig = {
        algorithm,
        threadCount,
        durationHours,
        checkpointIntervalMinutes: checkpointMinutes,
        autoRecovery,
        qpsDegradationThreshold: qpsThreshold,
        latencySpikeThreshold: latencyThreshold,
        errorRateThreshold: errorThreshold,
        snowflakeConfig: algorithm === 'SNOWFLAKE' ? { workerId: 1, datacenterId: 1, clockMode: 'NORMAL', clockOffsetMs: 10, clockBackProbability: 0.001 } : undefined,
        segmentConfig: algorithm === 'SEGMENT' ? { segmentSize: 1000 } : undefined,
      };
      const result = await startStabilityTest(config);
      setRunningTestId(result.testId);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleStop = async () => {
    if (runningTestId) {
      await stopStabilityTest(runningTestId);
      setRunningTestId(null);
    }
  };

  const formatDuration = (ms: number) => {
    const hours = Math.floor(ms / 3600000);
    const mins = Math.floor((ms % 3600000) / 60000);
    return `${hours}h ${mins}m`;
  };

  const getCheckpointChartOption = (checkpoints: StabilityCheckpoint[]) => {
    const times = checkpoints.map(c => new Date(c.timestamp).toLocaleTimeString());
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['QPS', 'Avg Latency', 'P99 Latency'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: times },
      yAxis: [
        { type: 'value', name: 'QPS' },
        { type: 'value', name: 'Latency (μs)' },
      ],
      series: [
        { name: 'QPS', type: 'line', data: checkpoints.map(c => c.avgQps), smooth: true, itemStyle: { color: '#3b82f6' } },
        { name: 'Avg Latency', type: 'line', yAxisIndex: 1, data: checkpoints.map(c => c.avgLatency), smooth: true, itemStyle: { color: '#10b981' } },
        { name: 'P99 Latency', type: 'line', yAxisIndex: 1, data: checkpoints.map(c => c.p99Latency), smooth: true, itemStyle: { color: '#ef4444' } },
      ],
    };
  };

  const anomalyColumns = [
    { title: '时间', dataIndex: 'timestamp', key: 'timestamp', render: (ts: number) => new Date(ts).toLocaleTimeString() },
    { title: '类型', dataIndex: 'type', key: 'type', render: (t: string) => {
      const colors: Record<string, string> = { QPS_DEGRADATION: 'orange', LATENCY_SPIKE: 'red', HIGH_ERROR_RATE: 'red' };
      return <Tag color={colors[t] || 'blue'}>{t}</Tag>;
    }},
    { title: '严重性', dataIndex: 'severity', key: 'severity', render: (s: string) => <Tag color={s === 'CRITICAL' ? 'red' : 'orange'}>{s}</Tag> },
    { title: '消息', dataIndex: 'message', key: 'message' },
    { title: '观测值', dataIndex: 'observedValue', key: 'observedValue', render: (v: number) => v.toFixed(2) },
    { title: '阈值', dataIndex: 'thresholdValue', key: 'thresholdValue', render: (v: number) => v.toFixed(2) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">🛡️ 长稳测试 (7×24)</h2>
        <p className="text-gray-500 mt-1">长时间持续压测，检测性能衰减、内存泄漏和稳定性问题</p>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <Row gutter={24}>
          <Col span={8}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">算法</label>
                <Select value={algorithm} onChange={setAlgorithm} style={{ width: '100%' }}>
                  <Option value="SNOWFLAKE">雪花算法</Option>
                  <Option value="SEGMENT">号段模式</Option>
                  <Option value="RANDOM">随机ID</Option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">并发线程数</label>
                <InputNumber min={1} max={100} value={threadCount} onChange={v => setThreadCount(v || 10)} style={{ width: '100%' }} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">测试时长 (小时)</label>
                <Slider min={1} max={720} value={durationHours} onChange={v => setDurationHours(v)} marks={{ 1: '1h', 24: '1天', 168: '7天', 720: '30天' }} />
                <div className="text-center text-sm font-mono text-primary">{durationHours} 小时 ({(durationHours / 24).toFixed(1)} 天)</div>
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">检查点间隔 (分钟)</label>
                <InputNumber min={1} max={60} value={checkpointMinutes} onChange={v => setCheckpointMinutes(v || 5)} style={{ width: '100%' }} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">QPS下降告警阈值</label>
                <Slider min={0.05} max={0.5} step={0.05} value={qpsThreshold} onChange={setQpsThreshold}
                  tooltip={{ formatter: v => `${((v || 0) * 100).toFixed(0)}%` }} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">延迟升高告警阈值</label>
                <Slider min={0.1} max={1} step={0.1} value={latencyThreshold} onChange={setLatencyThreshold}
                  tooltip={{ formatter: v => `${((v || 0) * 100).toFixed(0)}%` }} />
              </div>
              <div className="flex items-center space-x-2">
                <Switch checked={autoRecovery} onChange={setAutoRecovery} />
                <span className="text-sm text-gray-700">异常自动恢复</span>
              </div>
            </div>
          </Col>
          <Col span={8} className="flex flex-col justify-end space-y-3">
            <Card size="small" bordered={false} className="bg-blue-50">
              <Statistic title="预计检查点数" value={Math.floor(durationHours * 60 / checkpointMinutes)} />
            </Card>
            <Card size="small" bordered={false} className="bg-green-50">
              <Statistic title="预计运行时长" value={formatDuration(durationHours * 3600000)} />
            </Card>
            <Button type="primary" size="large" block loading={loading} onClick={handleStart} disabled={!!runningTestId}>
              🚀 启动长稳测试
            </Button>
            {runningTestId && (
              <Button danger size="large" block onClick={handleStop}>⏹ 停止测试</Button>
            )}
          </Col>
        </Row>
      </div>

      {selectedReport && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card size="small"><Statistic title="总运行时长" value={formatDuration(selectedReport.totalDurationMs)} /></Card>
            <Card size="small"><Statistic title="生成总数" value={selectedReport.totalGenerated?.toLocaleString()} /></Card>
            <Card size="small"><Statistic title="平均QPS" value={selectedReport.overallAvgQps?.toFixed(1)} /></Card>
            <Card size="small"><Statistic title="唯一性" value={selectedReport.uniquenessPassed ? '✓ 通过' : '✗ 失败'}
              valueStyle={{ color: selectedReport.uniquenessPassed ? '#52c41a' : '#f5222d' }} /></Card>
            <Card size="small">
              <Statistic title="性能趋势" value={
                selectedReport.performanceTrend?.qpsDegraded ? '⚠ QPS下降' :
                selectedReport.performanceTrend?.latencyDegraded ? '⚠ 延迟升高' : '✓ 稳定'
              } valueStyle={{
                color: selectedReport.performanceTrend?.qpsDegraded || selectedReport.performanceTrend?.latencyDegraded ? '#fa8c16' : '#52c41a'
              }} />
            </Card>
          </div>

          {selectedReport.checkpoints && selectedReport.checkpoints.length > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 性能趋势</h3>
              <ReactECharts option={getCheckpointChartOption(selectedReport.checkpoints)} style={{ height: '350px' }} />
            </div>
          )}

          {selectedReport.anomalies && selectedReport.anomalies.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">⚠️ 异常事件 ({selectedReport.anomalies.length})</h3>
              <Table dataSource={selectedReport.anomalies} columns={anomalyColumns} rowKey="timestamp" size="small" pagination={{ pageSize: 10 }} />
            </div>
          )}
        </div>
      )}

      {reports.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">历史长稳测试</h3>
          <Table
            dataSource={reports}
            columns={[
              { title: '测试ID', dataIndex: 'id', key: 'id', render: (id: string) => id.slice(0, 12) + '...' },
              { title: '算法', dataIndex: ['config', 'algorithm'], key: 'algo', render: (a: string) => <Tag color="blue">{a}</Tag> },
              { title: '运行时长', key: 'dur', render: (_: unknown, r: StabilityTestReport) => formatDuration(r.totalDurationMs) },
              { title: '平均QPS', dataIndex: 'overallAvgQps', key: 'qps', render: (v: number) => v?.toFixed(1) },
              { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'COMPLETED' ? 'green' : 'blue'}>{s}</Tag> },
              { title: '操作', key: 'action', render: (_: unknown, r: StabilityTestReport) => (
                <Button type="link" size="small" onClick={() => setSelectedReport(r)}>查看详情</Button>
              )},
            ]}
            rowKey="id"
            size="small"
          />
        </div>
      )}
    </div>
  );
};

export default StabilityPage;
