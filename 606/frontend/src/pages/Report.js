import React, { useState, useEffect } from 'react';
import {
  Card, Table, Tag, Button, Modal, Descriptions, Row, Col, Progress, Space, message,
  Tabs, Badge, Statistic, Divider, Empty, Alert, Tooltip, Drawer
} from 'antd';
import {
  FileTextOutlined, EyeOutlined, TrophyOutlined, DownOutlined,
  UpOutlined, ClockCircleOutlined, DashboardOutlined, ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend,
  ResponsiveContainer, BarChart, Bar, AreaChart, Area,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ComposedChart, Cell
} from 'recharts';
import { reportApi } from '../services/api';

const { TabPane } = Tabs;

const Report = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [drillDownVisible, setDrillDownVisible] = useState(false);
  const [drillDownData, setDrillDownData] = useState(null);
  const [drillDownTitle, setDrillDownTitle] = useState('');

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await reportApi.list();
      setReports(res.data?.data || []);
    } catch (e) {
      message.error('加载报告列表失败');
    } finally {
      setLoading(false);
    }
  };

  const showDetail = (report) => {
    setSelectedReport(report);
    setDetailVisible(true);
  };

  const getScoreLevel = (score) => {
    if (score >= 90) return { label: '优秀', color: '#52c41a' };
    if (score >= 75) return { label: '良好', color: '#1677ff' };
    if (score >= 60) return { label: '一般', color: '#faad14' };
    return { label: '较差', color: '#ff4d4f' };
  };

  const columns = [
    { title: '任务名称', dataIndex: 'taskName', key: 'taskName', ellipsis: true, width: 180 },
    {
      title: '综合评分',
      dataIndex: ['result', 'score'],
      key: 'score',
      width: 140,
      sorter: (a, b) => (a.result?.score || 0) - (b.result?.score || 0),
      render: (score) => {
        const level = getScoreLevel(score || 0);
        return (
          <Space>
            <TrophyOutlined style={{ color: level.color }} />
            <span style={{ color: level.color, fontWeight: 'bold', fontSize: 16 }}>
              {score?.toFixed(1) || '-'}
            </span>
            <Tag color={level.color === '#52c41a' ? 'success' : level.color === '#1677ff' ? 'processing' : level.color === '#faad14' ? 'warning' : 'error'}>
              {level.label}
            </Tag>
          </Space>
        );
      },
    },
    { title: '恢复时间', key: 'recoveryTime', width: 100,
      render: (_, r) => r.result?.recoveryTimeMs ? `${r.result.recoveryTimeMs}ms` : '-' },
    { title: '错误抖动', key: 'jitter', width: 100,
      render: (_, r) => r.result?.errorRateJitter ? r.result.errorRateJitter.toFixed(2) : '-' },
    { title: '拦截率', key: 'blockRate', width: 90,
      render: (_, r) => r.result ? `${r.result.blockRate?.toFixed(1)}%` : '-' },
    { title: '错误率', key: 'errorRate', width: 90,
      render: (_, r) => r.result ? `${r.result.errorRate?.toFixed(1)}%` : '-' },
    { title: 'P95', key: 'p95', width: 100,
      render: (_, r) => r.result ? `${r.result.p95ResponseTimeMs} ms` : '-' },
    { title: '生成时间', dataIndex: 'generateTime', key: 'generateTime', width: 170 },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(record)}>
          查看详情
        </Button>
      ),
    },
  ];

  const handleChartClick = (data, index, chartType) => {
    if (!data || !data.payload) return;
    setDrillDownData(data.payload);
    setDrillDownTitle(`${chartType} - 第${index}秒`);
    setDrillDownVisible(true);
  };

  const renderRadarChart = (scoreDetail) => {
    if (!scoreDetail) return null;
    const data = [
      { subject: '可用性', score: scoreDetail.availabilityScore || 0, fullMark: 100 },
      { subject: '响应时间', score: scoreDetail.responseTimeScore || 0, fullMark: 100 },
      { subject: '稳定性', score: scoreDetail.stabilityScore || 0, fullMark: 100 },
      { subject: '降级效果', score: scoreDetail.degradationEffectScore || 0, fullMark: 100 },
      { subject: '恢复能力', score: scoreDetail.recoveryScore || 0, fullMark: 100 },
      { subject: '恢复速度', score: scoreDetail.recoveryTimeScore || 0, fullMark: 100 },
      { subject: '抖动控制', score: scoreDetail.jitterScore || 0, fullMark: 100 },
      { subject: '阈值控制', score: scoreDetail.overThresholdScore || 0, fullMark: 100 },
      { subject: '一致性', score: scoreDetail.consistencyScore || 0, fullMark: 100 },
    ];
    return (
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" />
          <PolarRadiusAxis angle={90} domain={[0, 100]} />
          <Radar name="得分" dataKey="score" stroke="#1677ff" fill="#1677ff" fillOpacity={0.5} />
        </RadarChart>
      </ResponsiveContainer>
    );
  };

  const renderScoreBarChart = (scoreDetail) => {
    if (!scoreDetail) return null;
    const data = [
      { name: '可用性', score: scoreDetail.availabilityScore?.toFixed(1), color: '#1677ff', fullMark: 100, desc: '系统可用程度，成功请求占比' },
      { name: '响应时间', score: scoreDetail.responseTimeScore?.toFixed(1), color: '#52c41a', fullMark: 100, desc: '请求响应速度评分' },
      { name: '稳定性', score: scoreDetail.stabilityScore?.toFixed(1), color: '#faad14', fullMark: 100, desc: '系统波动情况评分' },
      { name: '降级效果', score: scoreDetail.degradationEffectScore?.toFixed(1), color: '#722ed1', fullMark: 100, desc: '降级策略生效程度' },
      { name: '恢复能力', score: scoreDetail.recoveryScore?.toFixed(1), color: '#13c2c2', fullMark: 100, desc: '系统恢复正常的能力' },
      { name: '恢复速度', score: scoreDetail.recoveryTimeScore?.toFixed(1), color: '#eb2f96', fullMark: 100, desc: '从异常中恢复的速度' },
      { name: '抖动控制', score: scoreDetail.jitterScore?.toFixed(1), color: '#fa8c16', fullMark: 100, desc: '错误率波动控制程度' },
      { name: '阈值控制', score: scoreDetail.overThresholdScore?.toFixed(1), color: '#a0d911', fullMark: 100, desc: '超阈值持续时间控制' },
      { name: '一致性', score: scoreDetail.consistencyScore?.toFixed(1), color: '#f5222d', fullMark: 100, desc: '各阶段表现一致性' },
    ];
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis domain={[0, 100]} />
          <RechartsTooltip />
          <Bar 
            dataKey="score" 
            radius={[4, 4, 0, 0]}
            onClick={(d) => {
              setDrillDownData(d);
              setDrillDownTitle(`评分维度 - ${d.name}`);
              setDrillDownVisible(true);
            }}
            cursor="pointer"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };

  const renderQpsChart = (realtimeMetrics) => {
    if (!realtimeMetrics || realtimeMetrics.length === 0) return <Empty description="暂无数据" />;
    const data = realtimeMetrics.map((m, i) => ({
      name: `${i}s`,
      QPS: m.qps,
      拦截率: m.blockRate,
      错误率: m.errorRate,
      成功: m.successCount,
      拦截: m.blockedCount,
      失败: m.failedCount,
      phase: m.phase,
      secondOffset: m.secondOffset,
      ...m
    }));
    return (
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <RechartsTooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const d = payload[0].payload;
                return (
                  <div style={{ background: 'white', padding: '12px', border: '1px solid #e8e8e8', borderRadius: '4px' }}>
                    <p style={{ margin: 0, fontWeight: 'bold' }}>第{d.secondOffset}秒 - {d.phase}</p>
                    {payload.map((entry, index) => (
                      <p key={index} style={{ margin: 0, color: entry.color }}>
                        {entry.name}: {entry.name === 'QPS' ? entry.value?.toFixed(1) : entry.value?.toFixed(1) + '%'}
                      </p>
                    ))}
                  </div>
                );
              }
              return null;
            }}
          />
          <Legend />
          <Area yAxisId="left" type="monotone" dataKey="QPS" fill="#91caff" stroke="#1677ff" strokeWidth={2} name="QPS" />
          <Line yAxisId="right" type="monotone" dataKey="拦截率" stroke="#faad14" strokeWidth={2} dot={false} name="拦截率(%)" />
          <Line yAxisId="right" type="monotone" dataKey="错误率" stroke="#ff4d4f" strokeWidth={2} dot={false} name="错误率(%)" />
        </ComposedChart>
      </ResponsiveContainer>
    );
  };

  const renderLatencyChart = (realtimeMetrics) => {
    if (!realtimeMetrics || realtimeMetrics.length === 0) return <Empty description="暂无数据" />;
    const data = realtimeMetrics.map((m, i) => ({
      name: `${i}s`,
      响应时间: m.responseTimeMs,
      QPS: m.qps,
      ...m
    }));
    return (
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorResp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#52c41a" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#52c41a" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Area type="monotone" dataKey="响应时间" stroke="#52c41a" strokeWidth={2} fillOpacity={1} fill="url(#colorResp)" name="响应时间(ms)" />
        </AreaChart>
      </ResponsiveContainer>
    );
  };

  const renderPhaseAnalysis = (timeBuckets) => {
    if (!timeBuckets || timeBuckets.length === 0) return <Empty description="暂无数据" />;
    const phases = { RAMP_UP: '爬坡期', SUSTAIN: '高峰期', RAMP_DOWN: '下降期' };
    const phaseData = Object.keys(phases).map(phase => {
      const buckets = timeBuckets.filter(b => b.phase === phase);
      if (buckets.length === 0) return null;
      const totalReq = buckets.reduce((sum, b) => sum + b.totalRequests, 0);
      const avgErr = totalReq > 0 ? buckets.reduce((sum, b) => sum + b.errorRate, 0) / buckets.length : 0;
      const avgBlock = totalReq > 0 ? buckets.reduce((sum, b) => sum + b.blockRate, 0) / buckets.length : 0;
      const avgResp = totalReq > 0 ? buckets.reduce((sum, b) => sum + b.avgResponseTimeMs, 0) / buckets.length : 0;
      return {
        phase: phases[phase],
        duration: buckets.length,
        totalRequests: totalReq,
        avgErrorRate: avgErr,
        avgBlockRate: avgBlock,
        avgRespTime: avgResp,
        maxErrorRate: Math.max(...buckets.map(b => b.errorRate)),
      };
    }).filter(Boolean);
    return (
      <Table
        dataSource={phaseData}
        rowKey="phase"
        size="small"
        pagination={false}
        columns={[
          { title: '阶段', dataIndex: 'phase' },
          { title: '持续(秒)', dataIndex: 'duration' },
          { title: '总请求', dataIndex: 'totalRequests' },
          { title: '平均错误率(%)', dataIndex: 'avgErrorRate', render: v => v?.toFixed(2) },
          { title: '平均拦截率(%)', dataIndex: 'avgBlockRate', render: v => v?.toFixed(2) },
          { title: '平均响应(ms)', dataIndex: 'avgRespTime', render: v => v?.toFixed(0) },
          { title: '峰值错误率(%)', dataIndex: 'maxErrorRate', render: v => v?.toFixed(2) },
        ]}
      />
    );
  };

  const renderTimeBuckets = (timeBuckets) => {
    if (!timeBuckets || timeBuckets.length === 0) return <Empty description="暂无数据" />;
    const columns = [
      { title: '时间(秒)', dataIndex: 'bucketId', width: 80 },
      { title: '阶段', dataIndex: 'phase', width: 80,
        render: v => {
        const map = { RAMP_UP: '爬坡', SUSTAIN: '高峰', RAMP_DOWN: '下降' };
        return map[v] || v;
      }},
      { title: '总请求', dataIndex: 'totalRequests' },
      { title: '成功', dataIndex: 'successRequests', render: v => <span style={{color: '#52c41a'}}>{v}</span> },
      { title: '拦截', dataIndex: 'blockedRequests', render: v => <span style={{color: '#faad14'}}>{v}</span> },
      { title: '失败', dataIndex: 'failedRequests', render: v => <span style={{color: '#ff4d4f'}}>{v}</span> },
      { title: '错误率(%)', dataIndex: 'errorRate', render: v => v?.toFixed(2)},
      { title: '拦截率(%)', dataIndex: 'blockRate', render: v => v?.toFixed(2)},
      { title: '平均响应(ms)', dataIndex: 'avgResponseTimeMs', render: v => v?.toFixed(0) },
    ];
    return (
      <Table
        dataSource={timeBuckets}
        rowKey="bucketId"
        size="small"
        scroll={{ y: 300 }}
        pagination={{ pageSize: 20 }}
        columns={columns}
        onRow={(record) => ({
          onClick: () => {
            setDrillDownData(record);
            setDrillDownTitle(`秒级详情 - 第${record.bucketId}秒`);
            setDrillDownVisible(true);
          },
          style: { cursor: 'pointer' },
        })}
      />
    );
  };

  const renderDetailModal = () => {
    if (!selectedReport) return null;
    const r = selectedReport.result;
    const level = getScoreLevel(r?.score || 0);
    return (
      <Modal
        title={<Space><FileTextOutlined />演练报告 - {selectedReport.taskName}</Space>}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={1000}
        bodyStyle={{ maxHeight: '80vh', overflowY: 'auto' }}
      >
        <Alert
          message={r?.recoveryTimeMs ? `恢复时间: ${r.recoveryTimeMs}ms` : '恢复时间: 未检测'}
          description={`错误抖动: ${r?.errorRateJitter?.toFixed(2)} | 超阈值: ${r?.overThresholdSeconds}秒 | 自动恢复: ${r?.autoRecovered ? '是' : '否'}`}
          type={r?.autoRecovered ? 'success' : 'info'}
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={5} style={{ textAlign: 'center' }}>
            <Progress
              type="dashboard"
              percent={r?.score || 0}
              strokeColor={level.color}
              format={p => (
                <div>
                  <div style={{ fontSize: 28, fontWeight: 'bold', color: level.color }}>{p}</div>
                  <div style={{ fontSize: 12, color: '#999' }}>{level.label}</div>
                </div>
              )}
            />
          </Col>
          <Col span={19}>
            <Row gutter={[8, 8]}>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="恢复时间" value={r?.recoveryTimeMs || 0} suffix="ms" />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="错误抖动" value={r?.errorRateJitter || 0} precision={2} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="超阈值时长" value={r?.overThresholdSeconds || 0} suffix="秒" />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="响应标准差" value={r?.responseTimeStdDev?.toFixed(1)} suffix="ms" />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="峰值错误率" value={r?.peakErrorRate?.toFixed(1)} suffix="%" />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic title="自动恢复" value={r?.autoRecovered ? '是' : '否'} />
                </Card>
              </Col>
            </Row>
            <Descriptions bordered size="small" column={3} style={{ marginTop: 12 }}>
              <Descriptions.Item label="总请求">{r?.totalRequests}</Descriptions.Item>
              <Descriptions.Item label="成功">{r?.successRequests}</Descriptions.Item>
              <Descriptions.Item label="拦截">{r?.blockedRequests}</Descriptions.Item>
              <Descriptions.Item label="失败">{r?.failedRequests}</Descriptions.Item>
              <Descriptions.Item label="降级">{r?.degradedRequests}</Descriptions.Item>
              <Descriptions.Item label="实际QPS">{r?.actualQps?.toFixed(1)}</Descriptions.Item>
              <Descriptions.Item label="P50">{r?.p50ResponseTimeMs} ms</Descriptions.Item>
              <Descriptions.Item label="P95">{r?.p95ResponseTimeMs} ms</Descriptions.Item>
              <Descriptions.Item label="P99">{r?.p99ResponseTimeMs} ms</Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>

        <Tabs defaultActiveKey="1">
          <TabPane tab="综合评分" key="1">
            <Row gutter={16}>
              <Col span={12}>
                <Card title="评分雷达图" size="small">
                  {renderRadarChart(r?.scoreDetail)}
                </Card>
              </Col>
              <Col span={12}>
                <Card title="各维度得分" size="small">
                  {renderScoreBarChart(r?.scoreDetail)}
                </Card>
              </Col>
            </Row>
          </TabPane>
          <TabPane tab="QPS趋势" key="2">
            <Card
              title="QPS / 拦截率 / 错误率趋势（点击数据点可下钻分析）" size="small" extra={<Badge status="processing" text="实时指标" />}>
              {renderQpsChart(r?.realtimeMetrics)}
            </Card>
          </TabPane>
          <TabPane tab="响应时间" key="3">
            <Card title="响应时间趋势" size="small">
              {renderLatencyChart(r?.realtimeMetrics)}
            </Card>
          </TabPane>
          <TabPane tab="分阶段分析" key="4">
            <Card title="各阶段表现对比" size="small">
              {renderPhaseAnalysis(r?.timeBuckets)}
            </Card>
          </TabPane>
          <TabPane tab="秒级明细" key="5">
            <Card title="每秒详细数据（点击行查看下钻）" size="small" extra={<Tooltip title="点击任意一行查看该秒的详细数据">
              <InfoCircleOutlined />
            </Tooltip>}>
              {renderTimeBuckets(r?.timeBuckets)}
            </Card>
          </TabPane>
        </Tabs>

        {selectedReport.conclusion && (
          <Card title="演练结论" size="small" style={{ marginTop: 12 }}>
            <p style={{ margin: 0, lineHeight: 1.8 }}>{selectedReport.conclusion}</p>
          </Card>
        )}

        {selectedReport.recommendation && (
          <Card title="优化建议" size="small" style={{ marginTop: 12 }}>
            <p style={{ margin: 0, lineHeight: 1.8, color: '#1677ff' }}>{selectedReport.recommendation}</p>
          </Card>
        )}

        {selectedReport.strategy && (
          <Card title="策略信息" size="small" style={{ marginTop: 12 }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="策略名称">{selectedReport.strategy.name}</Descriptions.Item>
              <Descriptions.Item label="策略类型">{selectedReport.strategy.type}</Descriptions.Item>
              <Descriptions.Item label="限流阈值">{selectedReport.strategy.threshold} QPS</Descriptions.Item>
              <Descriptions.Item label="超时时间">{selectedReport.strategy.timeoutMs} ms</Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Modal>
    );
  };

  const renderDrillDownDrawer = () => {
    if (!drillDownData) return null;
    return (
      <Drawer
        title={drillDownTitle}
        placement="right"
        onClose={() => setDrillDownVisible(false)}
        open={drillDownVisible}
        width={400}
      >
        <Descriptions bordered size="small" column={1}>
          {Object.keys(drillDownData).map(key => (
            <Descriptions.Item label={key}>
              {typeof drillDownData[key] === 'number'
                ? drillDownData[key].toFixed(2)
                : String(drillDownData[key])}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Drawer>
    );
  };

  return (
    <div>
      <Card
        title="演练报告"
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadReports}>刷新</Button>
        }
      >
        <Table
          columns={columns}
          dataSource={reports}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: '暂无演练报告，请先执行演练任务' }}
        />
      </Card>

      {renderDetailModal()}
      {renderDrillDownDrawer()}
    </div>
  );
};

export default Report;
