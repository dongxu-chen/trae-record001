import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Table, Tag, Empty, Card, Row, Col, Statistic, Progress, Alert, Tabs, Descriptions, List } from 'antd';
import MetricsCard from '../components/MetricsCard';
import QpsChart from '../components/QpsChart';
import LatencyChart from '../components/LatencyChart';
import { useTestStore } from '../store/testStore';
import { getReportList, exportReport } from '../utils/api';
import { TestReport, SampledMetrics, DuplicateDetail } from '../types';

const { TabPane } = Tabs;

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB';
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
};

const ReportPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentReport, reportList, setReportList } = useTestStore();
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const reports = await getReportList();
        setReportList(reports);
      } catch (err) {
        console.error('Failed to fetch reports:', err);
      }
    };
    fetchReports();
  }, []);

  const displayReport = currentReport;
  const displayMetrics: SampledMetrics[] = displayReport?.sampledMetrics || [];

  const handleExport = async (format: 'json' | 'csv') => {
    const reportId = selectedReportId || displayReport?.id;
    if (reportId) {
      await exportReport(reportId, format);
    }
  };

  const columns = [
    {
      title: '测试ID',
      dataIndex: 'id',
      key: 'id',
      render: (id: string) => <span className="font-mono text-sm">{id.slice(0, 12)}...</span>,
    },
    {
      title: '算法',
      dataIndex: ['config', 'algorithm'],
      key: 'algorithm',
      render: (algo: string) => <Tag color="blue">{algo}</Tag>,
    },
    {
      title: '线程数',
      dataIndex: ['config', 'threadCount'],
      key: 'threadCount',
    },
    {
      title: '生成总数',
      dataIndex: ['summary', 'totalGenerated'],
      key: 'totalGenerated',
      render: (val: number) => val?.toLocaleString(),
    },
    {
      title: '平均QPS',
      dataIndex: ['summary', 'avgQps'],
      key: 'avgQps',
      render: (val: number) => Math.round(val || 0).toLocaleString(),
    },
    {
      title: '唯一性',
      dataIndex: ['uniquenessCheck', 'isUnique'],
      key: 'uniquenessCheck',
      render: (isUnique: boolean) => (
        <Tag color={isUnique ? 'success' : 'error'}>
          {isUnique ? '✓ 通过' : '✗ 失败'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: TestReport) => (
        <Button type="link" size="small" onClick={() => setSelectedReportId(record.id)}>
          查看详情
        </Button>
      ),
    },
  ];

  const renderUniquenessCheckSection = (check: TestReport['uniquenessCheck']) => {
    if (!check) return null;

    return (
      <Card title="🔍 唯一性校验 (布隆过滤器 + 抽样)" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small" bordered={false} className={check.isUnique ? 'bg-green-50' : 'bg-red-50'}>
              <Statistic
                title="校验结果"
                value={check.isUnique ? '通过' : '失败'}
                valueStyle={{ color: check.isUnique ? '#52c41a' : '#f5222d' }}
                prefix={check.isUnique ? '✓' : '✗'}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Statistic
              title="布隆过滤器检测重复"
              value={check.bloomFilterDuplicates?.toLocaleString()}
              className="text-sm"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="抽样检测重复"
              value={check.sampleDuplicates?.toLocaleString()}
              className="text-sm"
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="抽样数量"
              value={check.sampleSize?.toLocaleString()}
              className="text-sm"
            />
          </Col>
        </Row>

        <div className="mt-4">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="估计重复率">
              <span className="font-mono">{(check.estimatedDuplicateRate * 100).toFixed(6)}%</span>
            </Descriptions.Item>
            <Descriptions.Item label="抽样重复率">
              <span className="font-mono">{(check.sampleDuplicateRate * 100).toFixed(6)}%</span>
            </Descriptions.Item>
            <Descriptions.Item label="调整后重复率">
              <span className="font-mono font-bold text-primary">{(check.adjustedDuplicateRate * 100).toFixed(6)}%</span>
            </Descriptions.Item>
            <Descriptions.Item label="误判数">
              <span className="font-mono">{check.falsePositives?.toLocaleString()}</span>
            </Descriptions.Item>
            <Descriptions.Item label="内存占用">
              <span className="font-mono text-green-600">{formatBytes(check.memoryUsageBytes || 0)}</span>
            </Descriptions.Item>
            <Descriptions.Item label="采样ID">
              <span className="text-gray-500">{check.sampleIds?.length || 0} 个 (最多展示100个)</span>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {!check.isUnique && check.duplicateDetails && check.duplicateDetails.length > 0 && (
          <div className="mt-4">
            <Alert
              message="发现重复ID"
              description={`检测到 ${check.duplicateDetails.length} 个重复ID（最多显示100个）`}
              type="error"
              showIcon
            />
            <Table<DuplicateDetail>
              size="small"
              dataSource={check.duplicateDetails.slice(0, 20)}
              columns={[
                { title: 'ID', dataIndex: 'id', key: 'id', className: 'font-mono text-xs' },
                { title: '重复次数', dataIndex: 'count', key: 'count', width: 100 },
              ]}
              pagination={false}
              className="mt-2"
            />
          </div>
        )}

        {check.sampleIds && check.sampleIds.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">抽样ID示例 (最多展示50个)</h4>
            <div className="bg-gray-50 p-3 rounded-lg max-h-40 overflow-y-auto">
              <div className="flex flex-wrap gap-2">
                {check.sampleIds.slice(0, 50).map((id, idx) => (
                  <span key={idx} className="font-mono text-xs bg-white px-2 py-1 rounded border">
                    {id}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </Card>
    );
  };

  const renderClockStatsSection = (clockStats: TestReport['clockStats']) => {
    if (!clockStats || !clockStats.enabled) return null;

    return (
      <Card title="⏰ 时钟模拟统计" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="时钟模式"
              value={clockStats.mode}
              className="text-sm"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="时钟漂移次数"
              value={clockStats.clockDriftCount?.toLocaleString()}
              className="text-sm"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="时钟回拨次数"
              value={clockStats.clockBackwardCount?.toLocaleString()}
              className="text-sm"
              valueStyle={{ color: '#fa8c16' }}
            />
          </Col>
        </Row>

        <div className="mt-4">
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="总漂移量">
              <span className="font-mono">{clockStats.totalDriftApplied?.toLocaleString()} ms</span>
            </Descriptions.Item>
            <Descriptions.Item label="总回拨量">
              <span className="font-mono text-orange-600">{clockStats.totalBackwardApplied?.toLocaleString()} ms</span>
            </Descriptions.Item>
            <Descriptions.Item label="强制等待次数">
              <span className="font-mono">{clockStats.forcedWaitCount?.toLocaleString()}</span>
            </Descriptions.Item>
            <Descriptions.Item label="总等待时间">
              <span className="font-mono">{clockStats.totalWaitTimeMs?.toLocaleString()} ms</span>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {clockStats.clockBackwardCount > 0 && (
          <Alert
            message="时钟回拨场景已触发"
            description="雪花算法检测到时钟回拨事件，已记录等待和恢复情况"
            type="warning"
            showIcon
            className="mt-4"
          />
        )}
      </Card>
    );
  };

  const renderMemoryStatsSection = (memoryStats: TestReport['memoryStats']) => {
    if (!memoryStats) return null;

    const savedPercent = memoryStats.estimatedMemorySavedBytes > 0
      ? Math.round((memoryStats.estimatedMemorySavedBytes / (memoryStats.avgMemoryBytes + memoryStats.estimatedMemorySavedBytes)) * 100)
      : 0;

    return (
      <Card title="💾 内存使用统计" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="峰值内存"
              value={formatBytes(memoryStats.peakMemoryBytes || 0)}
              className="text-sm"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="平均内存"
              value={formatBytes(memoryStats.avgMemoryBytes || 0)}
              className="text-sm"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="节省内存"
              value={formatBytes(memoryStats.estimatedMemorySavedBytes || 0)}
              className="text-sm"
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
        </Row>

        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">内存优化率</span>
            <span className="font-mono font-bold text-green-600">{savedPercent}%</span>
          </div>
          <Progress percent={savedPercent} status="success" strokeColor="#52c41a" />
        </div>

        <div className="mt-4 bg-green-50 p-3 rounded-lg">
          <p className="text-xs text-green-700">
            💡 通过布隆过滤器 + 抽样校验的方案，相比全量ID存储，
            节省了约 <span className="font-bold">{savedPercent}%</span> 的内存占用，
            同时保持了较高的唯一性检测准确率。
          </p>
        </div>
      </Card>
    );
  };

  const renderSummarySection = (summary: TestReport['summary']) => {
    if (!summary) return null;

    return (
      <Card title="📊 性能汇总" size="small" className="mb-4">
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small" bordered={false} className="bg-blue-50">
              <Statistic
                title="生成总数"
                value={summary.totalGenerated?.toLocaleString()}
                suffix="个"
                className="text-sm"
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} className="bg-green-50">
              <Statistic
                title="成功数"
                value={summary.successCount?.toLocaleString()}
                suffix="个"
                className="text-sm"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} className="bg-red-50">
              <Statistic
                title="失败数"
                value={summary.errorCount?.toLocaleString()}
                suffix="个"
                className="text-sm"
                valueStyle={{ color: '#f5222d' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" bordered={false} className="bg-purple-50">
              <Statistic
                title="测试时长"
                value={summary.durationSeconds}
                suffix="秒"
                className="text-sm"
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16} className="mt-4">
          <Col span={8}>
            <Statistic
              title="平均 QPS"
              value={Math.round(summary.avgQps || 0).toLocaleString()}
              suffix="/s"
              className="text-sm"
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="峰值 QPS"
              value={summary.peakQps?.toLocaleString()}
              suffix="/s"
              className="text-sm"
              valueStyle={{ color: '#722ed1' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="QPS 标准差"
              value={summary.stdDevQps?.toFixed(2)}
              className="text-sm"
            />
          </Col>
        </Row>

        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-600">QPS 波动范围</span>
            <span className="font-mono">
              {summary.minQps?.toLocaleString()} - {summary.peakQps?.toLocaleString()} /s
            </span>
          </div>
        </div>
      </Card>
    );
  };

  const renderLatencySection = (latencyStats: TestReport['latencyStats']) => {
    if (!latencyStats) return null;

    return (
      <Card title="⏱️ 延迟统计 (μs)" size="small" className="mb-4">
        <Row gutter={8}>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-green-50 text-center">
              <p className="text-xs text-gray-500 mb-1">最小值</p>
              <p className="text-xl font-bold font-mono text-green-600">
                {latencyStats.min?.toFixed(2)}
              </p>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-blue-50 text-center">
              <p className="text-xs text-gray-500 mb-1">平均值</p>
              <p className="text-xl font-bold font-mono text-blue-600">
                {latencyStats.avg?.toFixed(2)}
              </p>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-blue-50 text-center">
              <p className="text-xs text-gray-500 mb-1">P50</p>
              <p className="text-xl font-bold font-mono text-blue-500">
                {latencyStats.p50?.toFixed(2)}
              </p>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-yellow-50 text-center">
              <p className="text-xs text-gray-500 mb-1">P95</p>
              <p className="text-xl font-bold font-mono text-yellow-600">
                {latencyStats.p95?.toFixed(2)}
              </p>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-orange-50 text-center">
              <p className="text-xs text-gray-500 mb-1">P99</p>
              <p className="text-xl font-bold font-mono text-orange-600">
                {latencyStats.p99?.toFixed(2)}
              </p>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" bordered={false} className="bg-red-50 text-center">
              <p className="text-xs text-gray-500 mb-1">P999</p>
              <p className="text-xl font-bold font-mono text-red-600">
                {latencyStats.p999?.toFixed(2)}
              </p>
            </Card>
          </Col>
        </Row>

        <div className="mt-4">
          <Descriptions size="small" column={3} bordered>
            <Descriptions.Item label="最大值">
              <span className="font-mono text-red-600">{latencyStats.max?.toFixed(2)} μs</span>
            </Descriptions.Item>
            <Descriptions.Item label="P90">
              <span className="font-mono">{latencyStats.p90?.toFixed(2)} μs</span>
            </Descriptions.Item>
            <Descriptions.Item label="标准差">
              <span className="font-mono">{latencyStats.stdDev?.toFixed(2)} μs</span>
            </Descriptions.Item>
          </Descriptions>
        </div>
      </Card>
    );
  };

  if (!displayReport && reportList.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-gray-900">测试报告</h2>
        </div>
        <Empty description="暂无测试报告" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        <div className="flex justify-center">
          <Button type="primary" onClick={() => navigate('/')}>
            去创建测试
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">测试报告</h2>
          <p className="text-gray-500 mt-1">
            测试ID: <span className="font-mono">{displayReport?.id?.slice(0, 12)}...</span>
          </p>
        </div>
        <div className="space-x-2">
          <Button onClick={() => handleExport('json')}>导出 JSON</Button>
          <Button onClick={() => handleExport('csv')}>导出 CSV</Button>
          <Button type="primary" onClick={() => navigate('/')}>
            新建测试
          </Button>
        </div>
      </div>

      {displayReport && (
        <>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center space-x-4">
                <Tag color="blue">{displayReport.config?.algorithm}</Tag>
                <span className="text-gray-500 text-sm">
                  {displayReport.config?.threadCount} 线程
                </span>
                <span className="text-gray-400">|</span>
                <span className="text-gray-500 text-sm">
                  测试时长: {displayReport.summary?.durationSeconds}秒
                </span>
                {displayReport.clockStats?.enabled && (
                  <>
                    <span className="text-gray-400">|</span>
                    <Tag color="orange">⏰ {displayReport.clockStats.mode}</Tag>
                  </>
                )}
              </div>
              {displayReport.uniquenessCheck?.isUnique ? (
                <Tag color="success">✓ 唯一性校验通过</Tag>
              ) : (
                <Tag color="error">✗ 发现重复ID</Tag>
              )}
            </div>
          </div>

          <Tabs defaultActiveKey="1" className="bg-white rounded-xl">
            <TabPane tab="📊 总览" key="1">
              <div className="p-4">
                {renderSummarySection(displayReport.summary)}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-4">
                  <QpsChart data={displayMetrics.map(m => ({
                    timestamp: m.timestamp,
                    qps: m.qps,
                    avgLatency: m.avgLatency,
                    p50Latency: m.p50Latency,
                    p95Latency: m.p95Latency,
                    p99Latency: m.p99Latency,
                    generatedCount: m.generatedCount,
                    progress: m.progress,
                  }))} />
                  <LatencyChart data={displayMetrics.map(m => ({
                    timestamp: m.timestamp,
                    qps: m.qps,
                    avgLatency: m.avgLatency,
                    p50Latency: m.p50Latency,
                    p95Latency: m.p95Latency,
                    p99Latency: m.p99Latency,
                    generatedCount: m.generatedCount,
                    progress: m.progress,
                  }))} />
                </div>

                {renderLatencySection(displayReport.latencyStats)}
              </div>
            </TabPane>

            <TabPane tab="🔍 唯一性校验" key="2">
              <div className="p-4">
                {renderUniquenessCheckSection(displayReport.uniquenessCheck)}
              </div>
            </TabPane>

            <TabPane tab="⏰ 时钟模拟" key="3">
              <div className="p-4">
                {displayReport.clockStats?.enabled ? (
                  renderClockStatsSection(displayReport.clockStats)
                ) : (
                  <Empty description="本次测试未启用心跳模拟功能" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </div>
            </TabPane>

            <TabPane tab="💾 内存使用" key="4">
              <div className="p-4">
                {renderMemoryStatsSection(displayReport.memoryStats)}
              </div>
            </TabPane>

            <TabPane tab="📋 采样数据" key="5">
              <div className="p-4">
                <Card title="📈 性能指标采样数据" size="small">
                  <p className="text-sm text-gray-500 mb-4">
                    共 {displayMetrics.length} 条采样数据（最多保留60条）
                  </p>
                  <Table<SampledMetrics>
                    size="small"
                    dataSource={displayMetrics}
                    columns={[
                      {
                        title: '时间',
                        dataIndex: 'timestamp',
                        key: 'timestamp',
                        render: (ts: number) => new Date(ts).toLocaleTimeString(),
                        width: 100,
                      },
                      {
                        title: 'QPS',
                        dataIndex: 'qps',
                        key: 'qps',
                        render: (v: number) => <span className="font-mono">{v?.toLocaleString()}</span>,
                        width: 100,
                      },
                      {
                        title: '平均延迟',
                        dataIndex: 'avgLatency',
                        key: 'avgLatency',
                        render: (v: number) => <span className="font-mono">{v?.toFixed(2)}μs</span>,
                        width: 100,
                      },
                      {
                        title: 'P50',
                        dataIndex: 'p50Latency',
                        key: 'p50Latency',
                        render: (v: number) => <span className="font-mono">{v?.toFixed(2)}μs</span>,
                        width: 100,
                      },
                      {
                        title: 'P95',
                        dataIndex: 'p95Latency',
                        key: 'p95Latency',
                        render: (v: number) => <span className="font-mono text-yellow-600">{v?.toFixed(2)}μs</span>,
                        width: 100,
                      },
                      {
                        title: 'P99',
                        dataIndex: 'p99Latency',
                        key: 'p99Latency',
                        render: (v: number) => <span className="font-mono text-red-600">{v?.toFixed(2)}μs</span>,
                        width: 100,
                      },
                      {
                        title: '进度',
                        dataIndex: 'progress',
                        key: 'progress',
                        render: (v: number) => (
                          <Progress percent={v} size="small" showInfo={false} width={80} />
                        ),
                        width: 100,
                      },
                    ]}
                    pagination={{ pageSize: 20 }}
                  />
                </Card>
              </div>
            </TabPane>
          </Tabs>
        </>
      )}

      {reportList.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <h3 className="text-lg font-semibold text-gray-800 p-6 border-b">历史测试报告</h3>
          <Table
            dataSource={reportList}
            columns={columns}
            rowKey="id"
            pagination={false}
          />
        </div>
      )}
    </div>
  );
};

export default ReportPage;
