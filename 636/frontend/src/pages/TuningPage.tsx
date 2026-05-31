import React, { useEffect, useState } from 'react';
import { Button, Card, Row, Col, Statistic, Table, Tag, Select, InputNumber, Slider, Steps, Alert, Descriptions, Empty } from 'antd';
import ReactECharts from 'echarts-for-react';
import { IdAlgorithm, AutoTuningConfig, AutoTuningReport, TuningRoundResult, ParamSuggestion } from '../types';
import { startAutoTuning, stopAutoTuning, getTuningReportList } from '../utils/api';

const { Option } = Select;

const TuningPage: React.FC = () => {
  const [algorithm, setAlgorithm] = useState<IdAlgorithm>('SNOWFLAKE');
  const [maxRounds, setMaxRounds] = useState(20);
  const [testDuration, setTestDuration] = useState(10);
  const [target, setTarget] = useState('BALANCED');
  const [threadMin, setThreadMin] = useState(1);
  const [threadMax, setThreadMax] = useState(64);
  const [threadStep, setThreadStep] = useState(4);
  const [loading, setLoading] = useState(false);
  const [tuningId, setTuningId] = useState<string | null>(null);
  const [reports, setReports] = useState<AutoTuningReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<AutoTuningReport | null>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const list = await getTuningReportList();
        setReports(list);
      } catch (e) { console.error(e); }
    };
    fetchReports();
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      const config: AutoTuningConfig = {
        algorithm,
        maxRounds,
        testDurationSeconds: testDuration,
        optimizationTarget: target,
        threadCountRange: { min: threadMin, max: threadMax, step: threadStep },
        algorithmParamRanges: algorithm === 'SEGMENT' ? {
          segmentSize: { min: 100, max: 10000, step: 500 },
        } : undefined,
      };
      const result = await startAutoTuning(config);
      setTuningId(result.tuningId);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const handleStop = async () => {
    if (tuningId) {
      await stopAutoTuning(tuningId);
      setTuningId(null);
    }
  };

  const getRoundChartOption = (rounds: TuningRoundResult[]) => {
    if (!rounds || rounds.length === 0) return {};
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['评分', 'Avg QPS', 'P99 Latency'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: rounds.map(r => `Round ${r.round}`) },
      yAxis: [
        { type: 'value', name: '评分/QPS' },
        { type: 'value', name: 'Latency (μs)' },
      ],
      series: [
        { name: '评分', type: 'line', data: rounds.map(r => r.score), smooth: true, itemStyle: { color: '#8b5cf6' }, lineStyle: { width: 3 } },
        { name: 'Avg QPS', type: 'bar', data: rounds.map(r => r.avgQps), itemStyle: { color: '#3b82f6' } },
        { name: 'P99 Latency', type: 'line', yAxisIndex: 1, data: rounds.map(r => r.p99Latency), smooth: true, itemStyle: { color: '#ef4444' } },
      ],
    };
  };

  const roundColumns = [
    { title: '轮次', dataIndex: 'round', key: 'round', render: (r: number) => <span className="font-mono">#{r}</span> },
    { title: '线程数', key: 'tc', render: (_: unknown, r: TuningRoundResult) => r.config?.threadCount },
    { title: '评分', dataIndex: 'score', key: 'score', render: (s: number) => <span className="font-mono font-bold text-purple-600">{s.toFixed(2)}</span> },
    { title: 'Avg QPS', dataIndex: 'avgQps', key: 'qps', render: (v: number) => <span className="font-mono">{v?.toFixed(0)}</span> },
    { title: 'Avg Latency', dataIndex: 'avgLatency', key: 'lat', render: (v: number) => <span className="font-mono">{v?.toFixed(2)}μs</span> },
    { title: 'P99', dataIndex: 'p99Latency', key: 'p99', render: (v: number) => <span className="font-mono text-orange-600">{v?.toFixed(2)}μs</span> },
    { title: '错误率', dataIndex: 'errorRate', key: 'err', render: (v: number) => <span className="font-mono">{(v * 100).toFixed(3)}%</span> },
    { title: '唯一性', dataIndex: 'uniquenessPassed', key: 'uniq', render: (p: boolean) => <Tag color={p ? 'green' : 'red'}>{p ? '✓' : '✗'}</Tag> },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">🔧 自动调参</h2>
        <p className="text-gray-500 mt-1">自动搜索最优配置参数，多轮迭代+贝叶斯优化</p>
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
                <label className="block text-sm font-medium text-gray-700 mb-1">优化目标</label>
                <Select value={target} onChange={setTarget} style={{ width: '100%' }}>
                  <Option value="THROUGHPUT">吞吐量优先</Option>
                  <Option value="LATENCY">延迟优先</Option>
                  <Option value="BALANCED">均衡模式</Option>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">每轮测试时长 (秒)</label>
                <InputNumber min={5} max={120} value={testDuration} onChange={v => setTestDuration(v || 10)} style={{ width: '100%' }} />
              </div>
            </div>
          </Col>
          <Col span={8}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">最大迭代轮数</label>
                <Slider min={5} max={50} value={maxRounds} onChange={setMaxRounds} marks={{ 5: '5', 20: '20', 50: '50' }} />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">线程数搜索范围</label>
                <Row gutter={8}>
                  <Col span={8}><InputNumber min={1} value={threadMin} onChange={v => setThreadMin(v || 1)} placeholder="最小" style={{ width: '100%' }} /></Col>
                  <Col span={8}><InputNumber min={1} value={threadMax} onChange={v => setThreadMax(v || 64)} placeholder="最大" style={{ width: '100%' }} /></Col>
                  <Col span={8}><InputNumber min={1} value={threadStep} onChange={v => setThreadStep(v || 4)} placeholder="步长" style={{ width: '100%' }} /></Col>
                </Row>
              </div>
            </div>
          </Col>
          <Col span={8} className="flex flex-col justify-end space-y-3">
            <Card size="small" bordered={false} className="bg-purple-50">
              <Statistic title="预计测试组合" value={Math.min(Math.floor((threadMax - threadMin) / threadStep) + 1, maxRounds)} suffix="组" />
            </Card>
            <Card size="small" bordered={false} className="bg-blue-50">
              <Statistic title="预计耗时" value={Math.min(Math.floor((threadMax - threadMin) / threadStep) + 1, maxRounds) * testDuration} suffix="秒" />
            </Card>
            <Button type="primary" size="large" block loading={loading} onClick={handleStart} disabled={!!tuningId}>
              🔧 开始自动调参
            </Button>
            {tuningId && (
              <Button danger size="large" block onClick={handleStop}>⏹ 停止调参</Button>
            )}
          </Col>
        </Row>
      </div>

      {tuningId && (
        <Alert message="调参进行中..." description={`调参ID: ${tuningId.slice(0, 12)}...，贝叶斯优化正在搜索最优参数`} type="info" showIcon />
      )}

      {selectedReport && (
        <div className="space-y-4">
          {selectedReport.bestResult && (
            <Card className="border-2 border-purple-400 bg-purple-50">
              <Row gutter={16}>
                <Col span={3} className="flex items-center justify-center">
                  <span className="text-5xl">🎯</span>
                </Col>
                <Col span={21}>
                  <h3 className="text-lg font-bold text-purple-800 mb-3">最优配置</h3>
                  <Row gutter={16}>
                    <Col span={6}><Statistic title="综合评分" value={selectedReport.bestResult.bestScore?.toFixed(2)} valueStyle={{ color: '#7c3aed' }} /></Col>
                    <Col span={6}><Statistic title="最佳QPS" value={selectedReport.bestResult.bestAvgQps?.toFixed(1)} suffix="/s" /></Col>
                    <Col span={6}><Statistic title="最佳延迟" value={selectedReport.bestResult.bestAvgLatency?.toFixed(2)} suffix="μs" /></Col>
                    <Col span={6}><Statistic title="最佳P99" value={selectedReport.bestResult.bestP99Latency?.toFixed(2)} suffix="μs" /></Col>
                  </Row>
                  {selectedReport.bestResult.bestParams && (
                    <Descriptions size="small" column={4} className="mt-3">
                      {Object.entries(selectedReport.bestResult.bestParams).map(([k, v]) => (
                        <Descriptions.Item key={k} label={k}><span className="font-mono font-bold">{String(v)}</span></Descriptions.Item>
                      ))}
                    </Descriptions>
                  )}
                </Col>
              </Row>
            </Card>
          )}

          {selectedReport.suggestions && selectedReport.suggestions.length > 0 && (
            <Card title="💡 调参建议" size="small">
              {selectedReport.suggestions.map((s, i) => (
                <Alert key={i} message={`${s.paramName}: ${String(s.recommendedValue)}`} description={s.reason} type="success" showIcon className="mb-2" />
              ))}
            </Card>
          )}

          {selectedReport.roundResults && selectedReport.roundResults.length > 0 && (
            <>
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 调参过程</h3>
                <ReactECharts option={getRoundChartOption(selectedReport.roundResults)} style={{ height: '300px' }} />
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">各轮结果</h3>
                <Table dataSource={selectedReport.roundResults} columns={roundColumns} rowKey="round" size="small" pagination={{ pageSize: 10 }} />
              </div>
            </>
          )}
        </div>
      )}

      {reports.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">历史调参记录</h3>
          <Table
            dataSource={reports}
            columns={[
              { title: 'ID', dataIndex: 'id', key: 'id', render: (id: string) => id.slice(0, 12) + '...' },
              { title: '算法', dataIndex: ['config', 'algorithm'], key: 'algo', render: (a: string) => <Tag color="blue">{a}</Tag> },
              { title: '轮次', key: 'rounds', render: (_: unknown, r: AutoTuningReport) => `${r.completedRounds}/${r.totalRounds}` },
              { title: '最佳评分', key: 'score', render: (_: unknown, r: AutoTuningReport) => r.bestResult?.bestScore?.toFixed(2) || '-' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'COMPLETED' ? 'green' : 'blue'}>{s}</Tag> },
              { title: '操作', key: 'action', render: (_: unknown, r: AutoTuningReport) => (
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

export default TuningPage;
