import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Spin,
  Alert,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Collapse,
  Progress,
  Empty,
  Tooltip,
  Tabs,
  Table,
  Switch,
} from 'antd';
import {
  BugOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  BarChartOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { FailureCase, FailureCaseStratifiedSample, ModelInfo } from '@/types';
import { getFailureCases, getFailureCasesStratified, getModels } from '@/services/api';

const { Option } = Select;
const { Panel } = Collapse;
const { TabPane } = Tabs;

const FAILURE_REASON_LABELS: Record<string, string> = {
  complete_failure: '完全失败',
  mixed_failure: '混合失败',
  low_recall_high_precision: '低召回高精',
  high_recall_low_precision: '高召回低精',
  severe_missing: '严重遗漏',
  severe_irrelevant: '严重不相关',
  moderate_failure: '中等失败',
  unknown: '未知原因',
};

const FAILURE_SEVERITY_LABELS: Record<string, string> = {
  critical: '致命',
  high: '严重',
  medium: '中等',
  low: '轻微',
};

const QUERY_TYPE_LABELS: Record<string, string> = {
  informational: '信息查询',
  navigational: '导航查询',
  transactional: '事务查询',
  exploratory: '探索查询',
  unknown: '未知类型',
};

const FAILURE_REASON_COLORS: Record<string, string> = {
  complete_failure: '#ff4d4f',
  mixed_failure: '#fa8c16',
  low_recall_high_precision: '#faad14',
  high_recall_low_precision: '#a0d911',
  severe_missing: '#f5222d',
  severe_irrelevant: '#eb2f96',
  moderate_failure: '#1890ff',
  unknown: '#8c8c8c',
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

const FailureCasesPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<FailureCase[]>([]);
  const [stratifiedData, setStratifiedData] = useState<FailureCaseStratifiedSample | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState('default');
  const [k, setK] = useState(10);
  const [minRecall, setMinRecall] = useState(0.8);
  const [samplesPerStratum, setSamplesPerStratum] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [useStratified, setUseStratified] = useState(true);
  const [filterQueryType, setFilterQueryType] = useState<string | null>(null);
  const [filterFailureReason, setFilterFailureReason] = useState<string | null>(null);

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    loadData();
  }, [selectedModel, k, minRecall, samplesPerStratum, useStratified]);

  const loadModels = async () => {
    try {
      const res = await getModels();
      setModels(res.data);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      if (useStratified) {
        const res = await getFailureCasesStratified(selectedModel, k, minRecall, samplesPerStratum);
        setStratifiedData(res.data);
        setData(res.data.cases);
      } else {
        const res = await getFailureCases(selectedModel, k, minRecall);
        setData(res.data);
        setStratifiedData(null);
      }
    } catch (err: any) {
      setError('加载失败案例数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const getDisplayData = () => {
    let displayData = data;

    if (filterQueryType) {
      displayData = displayData.filter(c => c.query_type === filterQueryType);
    }
    if (filterFailureReason) {
      displayData = displayData.filter(c => c.failure_reason === filterFailureReason);
    }

    return displayData;
  };

  const getDistributionChartOption = () => {
    if (data.length === 0) return {};

    const recallBuckets = [0, 0.2, 0.4, 0.6, 0.8, 1.0];
    const bucketCounts = new Array(recallBuckets.length - 1).fill(0);

    data.forEach(item => {
      const recall = item.metrics.recall_at_k;
      for (let i = 0; i < recallBuckets.length - 1; i++) {
        if (recall >= recallBuckets[i] && recall < recallBuckets[i + 1]) {
          bucketCounts[i]++;
          break;
        }
      }
    });

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
      },
      yAxis: {
        type: 'value',
        name: '案例数',
      },
      series: [
        {
          name: '失败案例数',
          type: 'bar',
          data: bucketCounts.map((count, index) => ({
            value: count,
            itemStyle: {
              color: index < 2 ? '#ff4d4f' : index < 3 ? '#faad14' : '#52c41a',
            },
          })),
          label: {
            show: true,
            position: 'top',
          },
          barWidth: '50%',
        },
      ],
    };
  };

  const getFailureReasonChartOption = () => {
    if (data.length === 0) return {};

    const reasonCounts: Record<string, number> = {};
    data.forEach(item => {
      const reason = item.failure_reason || 'unknown';
      reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
    });

    const chartData = Object.entries(reasonCounts).map(([reason, count]) => ({
      value: count,
      name: FAILURE_REASON_LABELS[reason] || reason,
      itemStyle: { color: FAILURE_REASON_COLORS[reason] || '#8c8c8c' },
    }));

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
      },
      series: [
        {
          name: '失败原因',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['40%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: '{b}: {c}',
          },
          data: chartData,
        },
      ],
    };
  };

  const getQueryTypeDistributionOption = () => {
    if (data.length === 0) return {};

    const typeCounts: Record<string, number> = {};
    data.forEach(item => {
      const qt = item.query_type || 'unknown';
      typeCounts[qt] = (typeCounts[qt] || 0) + 1;
    });

    const chartData = Object.entries(typeCounts).map(([type, count]) => ({
      value: count,
      name: QUERY_TYPE_LABELS[type] || type,
    }));

    return {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        bottom: 0,
      },
      series: [
        {
          name: '查询类型',
          type: 'pie',
          radius: '60%',
          center: ['50%', '50%'],
          label: {
            show: true,
            formatter: '{b}: {c}',
          },
          data: chartData,
        },
      ],
    };
  };

  const getStratificationBarChartOption = () => {
    if (!stratifiedData || stratifiedData.strata.length === 0) return {};

    const categories = stratifiedData.strata.map(s =>
      `${QUERY_TYPE_LABELS[s.query_type] || s.query_type} - ${FAILURE_REASON_LABELS[s.failure_reason] || s.failure_reason}`
    );
    const totalCounts = stratifiedData.strata.map(s => s.total_count);
    const sampledCounts = stratifiedData.strata.map(s => s.sampled_count);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        data: ['总案例数', '采样数'],
        top: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
          interval: 0,
          rotate: 30,
          fontSize: 10,
        },
      },
      yAxis: {
        type: 'value',
        name: '案例数',
      },
      series: [
        {
          name: '总案例数',
          type: 'bar',
          data: totalCounts,
          itemStyle: { color: '#1677ff' },
        },
        {
          name: '采样数',
          type: 'bar',
          data: sampledCounts,
          itemStyle: { color: '#52c41a' },
        },
      ],
    };
  };

  const avgMetrics = () => {
    if (data.length === 0) return null;

    const totalRecall = data.reduce((sum, item) => sum + item.metrics.recall_at_k, 0);
    const totalPrecision = data.reduce((sum, item) => sum + item.metrics.precision_at_k, 0);
    const totalF1 = data.reduce((sum, item) => sum + item.metrics.f1_at_k, 0);
    const totalNdcg = data.reduce((sum, item) => sum + item.metrics.ndcg_at_k, 0);

    return {
      recall: totalRecall / data.length,
      precision: totalPrecision / data.length,
      f1: totalF1 / data.length,
      ndcg: totalNdcg / data.length,
    };
  };

  const avg = avgMetrics();
  const displayData = getDisplayData();

  const strataColumns = [
    {
      title: '查询类型',
      dataIndex: 'query_type',
      key: 'query_type',
      render: (type: string) => (
        <Tag color="blue">{QUERY_TYPE_LABELS[type] || type}</Tag>
      ),
    },
    {
      title: '失败原因',
      dataIndex: 'failure_reason',
      key: 'failure_reason',
      render: (reason: string) => (
        <Tag color={FAILURE_REASON_COLORS[reason] || 'default'}>
          {FAILURE_REASON_LABELS[reason] || reason}
        </Tag>
      ),
    },
    {
      title: '总案例数',
      dataIndex: 'total_count',
      key: 'total_count',
    },
    {
      title: '采样数',
      dataIndex: 'sampled_count',
      key: 'sampled_count',
      render: (count: number, record: any) => (
        <span>
          {count} / {record.total_count}
          <Progress
            percent={Math.round((count / record.total_count) * 100)}
            size="small"
            style={{ marginTop: 4 }}
          />
        </span>
      ),
    },
  ];

  const getFailureReasonTags = () => {
    const reasons = new Set(data.map(d => d.failure_reason || 'unknown'));
    return Array.from(reasons);
  };

  const getQueryTypeTags = () => {
    const types = new Set(data.map(d => d.query_type || 'unknown'));
    return Array.from(types);
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>失败案例分析</h2>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap size="large" style={{ width: '100%' }}>
          <Space>
            <span style={{ color: '#666' }}>
              <InfoCircleOutlined /> 检索模型：
            </span>
            <Select
              value={selectedModel}
              onChange={setSelectedModel}
              style={{ width: 200 }}
            >
              {models.map(model => (
                <Option key={model.model_name} value={model.model_name}>
                  {model.model_name}
                </Option>
              ))}
            </Select>
          </Space>

          <Space>
            <span style={{ color: '#666' }}>
              <InfoCircleOutlined /> Top-K：
            </span>
            <Select value={k} onChange={setK} style={{ width: 120 }}>
              {[1, 3, 5, 10, 20, 30, 50].map(val => (
                <Option key={val} value={val}>Top {val}</Option>
              ))}
            </Select>
          </Space>

          <Space>
            <span style={{ color: '#666' }}>
              <InfoCircleOutlined /> 最小召回率：
            </span>
            <Select value={minRecall} onChange={setMinRecall} style={{ width: 120 }}>
              {[0.3, 0.5, 0.6, 0.7, 0.8, 0.9].map(val => (
                <Option key={val} value={val}>{(val * 100).toFixed(0)}%</Option>
              ))}
            </Select>
          </Space>

          <Space>
            <span style={{ color: '#666' }}>
              <AppstoreOutlined /> 分层采样：
            </span>
            <Switch checked={useStratified} onChange={setUseStratified} />
            {useStratified && (
              <>
                <span style={{ color: '#666' }}>每层采样：</span>
                <Select value={samplesPerStratum} onChange={setSamplesPerStratum} style={{ width: 100 }}>
                  {[1, 2, 3, 5, 10].map(val => (
                    <Option key={val} value={val}>{val} 条</Option>
                  ))}
                </Select>
              </>
            )}
          </Space>

          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>
      </Card>

      {error && (
        <Alert message={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '100px' }}>
          <Spin size="large" />
        </div>
      ) : data.length > 0 ? (
        <div>
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title={
                    <span>
                      <BugOutlined style={{ color: '#ff4d4f' }} /> 失败案例数
                    </span>
                  }
                  value={data.length}
                  valueStyle={{ color: '#ff4d4f' }}
                  suffix={stratifiedData ? ` / ${stratifiedData.total_cases}` : ''}
                />
                {stratifiedData && (
                  <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
                    分层采样: {stratifiedData.sampled_cases} 条
                  </div>
                )}
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="平均召回率"
                  value={(avg?.recall || 0) * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="平均精确率"
                  value={(avg?.precision || 0) * 100}
                  suffix="%"
                  precision={2}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="metric-card">
                <Statistic
                  title="平均 NDCG"
                  value={avg?.ndcg || 0}
                  precision={4}
                  valueStyle={{ color: '#1677ff' }}
                />
              </Card>
            </Col>
          </Row>

          {useStratified && stratifiedData && (
            <Card
              title={
                <Space>
                  <BarChartOutlined style={{ color: '#1677ff' }} />
                  <span>分层采样统计</span>
                  <Tag color="blue">{stratifiedData.strata.length} 个层级</Tag>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  <ReactECharts option={getStratificationBarChartOption()} style={{ height: 350 }} />
                </Col>
                <Col xs={24} lg={12}>
                  <Table
                    columns={strataColumns}
                    dataSource={stratifiedData.strata}
                    rowKey={(record: any) => `${record.query_type}_${record.failure_reason}`}
                    pagination={false}
                    size="small"
                  />
                </Col>
              </Row>
            </Card>
          )}

          <Card style={{ marginBottom: 24 }}>
            <Tabs defaultActiveKey="distribution">
              <TabPane
                tab={
                  <Space>
                    <BarChartOutlined /> 分布视图
                  </Space>
                }
                key="distribution"
              >
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card title="召回率分布" size="small">
                      <ReactECharts option={getDistributionChartOption()} style={{ height: 280 }} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={8}>
                    <Card title="失败原因分布" size="small">
                      <ReactECharts option={getFailureReasonChartOption()} style={{ height: 280 }} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={8}>
                    <Card title="查询类型分布" size="small">
                      <ReactECharts option={getQueryTypeDistributionOption()} style={{ height: 280 }} />
                    </Card>
                  </Col>
                </Row>
              </TabPane>

              <TabPane
                tab={
                  <Space>
                    <AppstoreOutlined /> 分类筛选
                  </Space>
                }
                key="filter"
              >
                <Space wrap size="large" style={{ width: '100%', padding: '16px 0' }}>
                  <Space>
                    <span style={{ color: '#666' }}>查询类型：</span>
                    <Select
                      value={filterQueryType}
                      onChange={setFilterQueryType}
                      style={{ width: 180 }}
                      allowClear
                      placeholder="选择查询类型"
                    >
                      {getQueryTypeTags().map(type => (
                        <Option key={type} value={type}>
                          {QUERY_TYPE_LABELS[type] || type}
                        </Option>
                      ))}
                    </Select>
                  </Space>
                  <Space>
                    <span style={{ color: '#666' }}>失败原因：</span>
                    <Select
                      value={filterFailureReason}
                      onChange={setFilterFailureReason}
                      style={{ width: 180 }}
                      allowClear
                      placeholder="选择失败原因"
                    >
                      {getFailureReasonTags().map(reason => (
                        <Option key={reason} value={reason}>
                          {FAILURE_REASON_LABELS[reason] || reason}
                        </Option>
                      ))}
                    </Select>
                  </Space>
                  <Button onClick={() => { setFilterQueryType(null); setFilterFailureReason(null); }}>
                    清除筛选
                  </Button>
                  <Tag color="blue">显示 {displayData.length} / {data.length} 条</Tag>
                </Space>
              </TabPane>
            </Tabs>
          </Card>

          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#faad14' }} />
                <span>失败案例详情</span>
                <Tag color="red">共 {displayData.length} 条</Tag>
                {(filterQueryType || filterFailureReason) && (
                  <Tag color="blue">已筛选</Tag>
                )}
              </Space>
            }
          >
            {displayData.length > 0 ? (
              <Collapse
                accordion
                items={displayData.map((item, index) => ({
                  key: item.query_id,
                  label: (
                    <Space wrap>
                      <Tag color="red">#{index + 1}</Tag>
                      <span style={{ fontWeight: 500 }}>{item.query_text}</span>
                      {item.query_type && (
                        <Tag color="blue">
                          {QUERY_TYPE_LABELS[item.query_type] || item.query_type}
                        </Tag>
                      )}
                      {item.failure_reason && (
                        <Tag color={FAILURE_REASON_COLORS[item.failure_reason] || 'default'}>
                          {FAILURE_REASON_LABELS[item.failure_reason] || item.failure_reason}
                        </Tag>
                      )}
                      {item.failure_severity && (
                        <Tag color={SEVERITY_COLORS[item.failure_severity] || 'default'}>
                          {FAILURE_SEVERITY_LABELS[item.failure_severity] || item.failure_severity}
                        </Tag>
                      )}
                      <Tag color={item.metrics.recall_at_k < 0.3 ? 'error' : 'warning'}>
                        召回率: {(item.metrics.recall_at_k * 100).toFixed(1)}%
                      </Tag>
                    </Space>
                  ),
                  children: (
                    <div style={{ padding: '16px 0' }}>
                      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                        <Col xs={12} sm={6}>
                          <Progress
                            type="dashboard"
                            percent={item.metrics.recall_at_k * 100}
                            status={item.metrics.recall_at_k < 0.5 ? 'exception' : 'normal'}
                            format={percent => `召回率 ${percent}%`}
                          />
                        </Col>
                        <Col xs={12} sm={6}>
                          <Progress
                            type="dashboard"
                            percent={item.metrics.precision_at_k * 100}
                            format={percent => `精确率 ${percent}%`}
                          />
                        </Col>
                        <Col xs={12} sm={6}>
                          <Progress
                            type="dashboard"
                            percent={item.metrics.f1_at_k * 100}
                            format={percent => `F1 ${percent}%`}
                          />
                        </Col>
                        <Col xs={12} sm={6}>
                          <Progress
                            type="dashboard"
                            percent={item.metrics.ndcg_at_k * 100}
                            format={percent => `NDCG ${percent}%`}
                          />
                        </Col>
                      </Row>

                      {item.missing_docs.length > 0 && (
                        <Card
                          size="small"
                          title={
                            <Space>
                              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                              <span>遗漏的相关文档 ({item.missing_docs.length})</span>
                            </Space>
                          }
                          style={{ marginBottom: 16, background: '#fff1f0' }}
                        >
                          {item.missing_docs.map((doc, i) => (
                            <div key={doc.doc_id} style={{ padding: '8px 0', borderBottom: i < item.missing_docs.length - 1 ? '1px dashed #ffa39e' : 'none' }}>
                              <div style={{ fontWeight: 500, color: '#cf1322' }}>
                                {doc.title || doc.doc_id}
                              </div>
                              {doc.content && (
                                <div style={{ color: '#666', fontSize: 12 }}>{doc.content}</div>
                              )}
                              <div style={{ color: '#999', fontSize: 11 }}>doc_id: {doc.doc_id}</div>
                            </div>
                          ))}
                        </Card>
                      )}

                      {item.irrelevant_docs.length > 0 && (
                        <Card
                          size="small"
                          title={
                            <Space>
                              <WarningOutlined style={{ color: '#faad14' }} />
                              <span>不相关的返回结果 ({item.irrelevant_docs.length})</span>
                            </Space>
                          }
                          style={{ marginBottom: 16, background: '#fffbe6' }}
                        >
                          {item.irrelevant_docs.map((doc, i) => (
                            <div key={(doc as any).doc_id} style={{ padding: '8px 0', borderBottom: i < item.irrelevant_docs.length - 1 ? '1px dashed #ffe58f' : 'none' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <div style={{ fontWeight: 500, color: '#d46b08' }}>
                                  #{(doc as any).rank} {(doc as any).title || (doc as any).doc_id}
                                </div>
                                <Tag color="warning">得分: {(doc as any).score?.toFixed(3)}</Tag>
                              </div>
                              {(doc as any).content && (
                                <div style={{ color: '#666', fontSize: 12 }}>{(doc as any).content}</div>
                              )}
                            </div>
                          ))}
                        </Card>
                      )}

                      <Card
                        size="small"
                        title={
                          <Space>
                            <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            <span>期望的相关文档</span>
                          </Space>
                        }
                        style={{ background: '#f6ffed' }}
                      >
                        <Space wrap>
                          {item.expected_docs.map(docId => (
                            <Tag key={docId} color="success">{docId}</Tag>
                          ))}
                        </Space>
                      </Card>
                    </div>
                  ),
                }))}
              />
            ) : (
              <Empty description="没有符合筛选条件的案例" />
            )}
          </Card>
        </div>
      ) : (
        <Card>
          <Empty
            description={
              <div>
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 48, marginBottom: 16 }} />
                <p style={{ color: '#52c41a', fontSize: 16 }}>太棒了！没有发现失败案例</p>
                <p style={{ color: '#999' }}>所有查询的召回率都超过了 {minRecall * 100}%</p>
              </div>
            }
          />
        </Card>
      )}
    </div>
  );
};

export default FailureCasesPage;
