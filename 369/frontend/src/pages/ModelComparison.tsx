import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Button,
  Spin,
  Alert,
  Space,
  Tag,
  Checkbox,
  Row,
  Col,
  Statistic,
  Tooltip,
  Modal,
  Breadcrumb,
  Empty,
} from 'antd';
import {
  LineChartOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ArrowLeftOutlined,
  BarChartOutlined,
  DownOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ModelComparisonData, ModelInfo, ModelComparisonDrillDown, QueryTypeStats } from '@/types';
import { getModelComparison, getModelComparisonDrilldown, getModels, getQueryTypeStats } from '@/services/api';

const { Option } = Select;

const METRIC_COLORS: Record<string, string> = {
  recall: '#1677ff',
  precision: '#52c41a',
  f1: '#fa8c16',
  hit_rate: '#722ed1',
  ndcg: '#13c2c2',
};

const MODEL_COLORS = ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96', '#13c2c2', '#faad14'];

const QUERY_TYPE_LABELS: Record<string, string> = {
  informational: '信息查询',
  navigational: '导航查询',
  transactional: '事务查询',
  exploratory: '探索查询',
  unknown: '未知类型',
};

const ModelComparisonPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ModelComparisonData[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>(['default']);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['recall', 'precision', 'f1', 'ndcg']);
  const [kValues, setKValues] = useState<number[]>([1, 3, 5, 10, 20, 30]);
  const [error, setError] = useState<string | null>(null);
  const [drilldownData, setDrilldownData] = useState<ModelComparisonDrillDown[]>([]);
  const [queryTypeStats, setQueryTypeStats] = useState<QueryTypeStats[]>([]);
  const [selectedQueryType, setSelectedQueryType] = useState<string | null>(null);
  const [drilldownModalVisible, setDrilldownModalVisible] = useState(false);
  const [drilldownMetric, setDrilldownMetric] = useState<string>('recall');
  const [queryTypeFilter, setQueryTypeFilter] = useState<string | null>(null);

  const metricsOptions = [
    { label: '召回率 (Recall)', value: 'recall' },
    { label: '精确率 (Precision)', value: 'precision' },
    { label: 'F1 Score', value: 'f1' },
    { label: '命中率 (Hit Rate)', value: 'hit_rate' },
    { label: 'NDCG', value: 'ndcg' },
  ];

  const queryTypeOptions = [
    { label: '全部类型', value: null },
    { label: '信息查询 (Informational)', value: 'informational' },
    { label: '导航查询 (Navigational)', value: 'navigational' },
    { label: '事务查询 (Transactional)', value: 'transactional' },
    { label: '探索查询 (Exploratory)', value: 'exploratory' },
  ];

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedModels.length > 0) {
      loadData();
      loadQueryTypeStats();
      loadDrilldownData();
    }
  }, [selectedModels, kValues, queryTypeFilter]);

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
      const res = await getModelComparison(selectedModels, kValues, queryTypeFilter || undefined);
      setData(res.data);
    } catch (err: any) {
      setError('加载模型对比数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadDrilldownData = async () => {
    try {
      const res = await getModelComparisonDrilldown(selectedModels, kValues);
      setDrilldownData(res.data);
    } catch (err) {
      console.error('Failed to load drilldown data:', err);
    }
  };

  const loadQueryTypeStats = async () => {
    try {
      const res = await getQueryTypeStats('default', 10);
      setQueryTypeStats(res.data);
    } catch (err) {
      console.error('Failed to load query type stats:', err);
    }
  };

  const handleChartClick = (metric: string) => {
    setDrilldownMetric(metric);
    setDrilldownModalVisible(true);
  };

  const getLineChartOption = (metric: string, drilldown?: ModelComparisonDrillDown) => {
    const chartData = drilldown ? drilldown.comparisons : data;
    if (chartData.length === 0) return {};

    const metricKeyMap: Record<string, string> = {
      recall: 'recall_scores',
      precision: 'precision_scores',
      f1: 'f1_scores',
      hit_rate: 'hit_rates',
      ndcg: 'ndcg_scores',
    };

    const metricLabelMap: Record<string, string> = {
      recall: '召回率',
      precision: '精确率',
      f1: 'F1 Score',
      hit_rate: '命中率',
      ndcg: 'NDCG',
    };

    const kVals = drilldown ? drilldown.comparisons[0]?.k_values || kValues : kValues;

    const series = chartData.map((modelData, index) => ({
      name: modelData.model_name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 10,
      data: modelData[metricKeyMap[metric] as keyof ModelComparisonData] as number[],
      lineStyle: {
        width: 3,
        color: MODEL_COLORS[index % MODEL_COLORS.length],
      },
      itemStyle: {
        color: MODEL_COLORS[index % MODEL_COLORS.length],
      },
      emphasis: {
        focus: 'series',
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)',
        },
      },
    }));

    return {
      title: {
        text: drilldown
          ? `${QUERY_TYPE_LABELS[drilldown.query_type] || drilldown.query_type} - ${metricLabelMap[metric]} 对比`
          : `${metricLabelMap[metric]} 对比`,
        left: 'center',
        textStyle: { fontSize: 14 },
        subtext: drilldown ? '' : '点击曲线可下钻查看各查询类型详情',
        subtextStyle: { fontSize: 11, color: '#999' },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          let result = params[0].axisValue + '<br/>';
          params.forEach((param: any) => {
            result += `${param.marker} ${param.seriesName}: ${(param.value * 100).toFixed(2)}%<br/>`;
          });
          return result;
        },
      },
      legend: {
        data: chartData.map(d => d.model_name),
        bottom: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '18%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: kVals.map(k => `K=${k}`),
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#ddd' } },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 1,
        axisLabel: {
          formatter: (value: number) => (value * 100).toFixed(0) + '%',
        },
        splitLine: { lineStyle: { color: '#f0f0f0' } },
      },
      series,
    };
  };

  const getDrilldownBarChartOption = () => {
    if (queryTypeStats.length === 0) return {};

    const metricKeyMap: Record<string, keyof QueryTypeStats> = {
      recall: 'avg_recall',
      precision: 'avg_precision',
      f1: 'avg_f1',
      hit_rate: 'avg_recall',
      ndcg: 'avg_ndcg',
    };

    const metricLabelMap: Record<string, string> = {
      recall: '召回率',
      precision: '精确率',
      f1: 'F1 Score',
      hit_rate: '命中率',
      ndcg: 'NDCG',
    };

    return {
      title: {
        text: `各查询类型${metricLabelMap[drilldownMetric]}对比`,
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const param = params[0];
          return `${param.name}<br/>${param.marker} ${metricLabelMap[drilldownMetric]}: ${(param.value * 100).toFixed(2)}%`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: queryTypeStats.map(s => QUERY_TYPE_LABELS[s.query_type] || s.query_type),
        axisLabel: { interval: 0, rotate: 0 },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 1,
        axisLabel: {
          formatter: (value: number) => (value * 100).toFixed(0) + '%',
        },
      },
      series: [
        {
          name: metricLabelMap[drilldownMetric],
          type: 'bar',
          data: queryTypeStats.map((s, i) => ({
            value: s[metricKeyMap[drilldownMetric]],
            itemStyle: {
              color: MODEL_COLORS[i % MODEL_COLORS.length],
              borderRadius: [4, 4, 0, 0],
            },
          })),
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => (params.value * 100).toFixed(1) + '%',
          },
          barWidth: '50%',
        },
      ],
    };
  };

  const getRadarChartOption = () => {
    if (data.length === 0) return {};

    const indicators = [
      { name: '召回率', max: 1 },
      { name: '精确率', max: 1 },
      { name: 'F1 Score', max: 1 },
      { name: '命中率', max: 1 },
      { name: 'NDCG', max: 1 },
    ];

    const series = data.map((modelData, index) => {
      const avgRecall = modelData.recall_scores.reduce((a, b) => a + b, 0) / modelData.recall_scores.length;
      const avgPrecision = modelData.precision_scores.reduce((a, b) => a + b, 0) / modelData.precision_scores.length;
      const avgF1 = modelData.f1_scores.reduce((a, b) => a + b, 0) / modelData.f1_scores.length;
      const avgHitRate = modelData.hit_rates.reduce((a, b) => a + b, 0) / modelData.hit_rates.length;
      const avgNdcg = modelData.ndcg_scores.reduce((a, b) => a + b, 0) / modelData.ndcg_scores.length;

      return {
        name: modelData.model_name,
        type: 'radar',
        data: [
          {
            value: [avgRecall, avgPrecision, avgF1, avgHitRate, avgNdcg],
            name: modelData.model_name,
          },
        ],
        lineStyle: {
          width: 2,
          color: MODEL_COLORS[index % MODEL_COLORS.length],
        },
        itemStyle: {
          color: MODEL_COLORS[index % MODEL_COLORS.length],
        },
        areaStyle: {
          color: MODEL_COLORS[index % MODEL_COLORS.length],
          opacity: 0.1,
        },
      };
    });

    return {
      title: {
        text: '综合指标雷达图 (平均值)',
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          let result = `${params.name}<br/>`;
          const values = params.value;
          indicators.forEach((ind, i) => {
            result += `${ind.name}: ${(values[i] * 100).toFixed(2)}%<br/>`;
          });
          return result;
        },
      },
      legend: {
        data: data.map(d => d.model_name),
        bottom: 0,
      },
      radar: {
        indicator: indicators,
        radius: '60%',
        axisName: {
          formatter: (value: string) => value,
        },
      },
      series,
    };
  };

  const getBestModelForMetric = (metric: string): { name: string; value: number } | null => {
    if (data.length === 0) return null;

    const metricKeyMap: Record<string, string> = {
      recall: 'recall_scores',
      precision: 'precision_scores',
      f1: 'f1_scores',
      hit_rate: 'hit_rates',
      ndcg: 'ndcg_scores',
    };

    let bestModel = '';
    let bestValue = -1;

    data.forEach(modelData => {
      const scores = modelData[metricKeyMap[metric] as keyof ModelComparisonData] as number[];
      const avg = scores.reduce((a: number, b: number) => a + b, 0) / scores.length;
      if (avg > bestValue) {
        bestValue = avg;
        bestModel = modelData.model_name;
      }
    });

    return { name: bestModel, value: bestValue };
  };

  const getQueryTypeLabel = (type: string) => QUERY_TYPE_LABELS[type] || type;

  const onEvents = (metric: string) => ({
    click: () => handleChartClick(metric),
  });

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>多模型对比分析</h2>

      {selectedQueryType && (
        <Breadcrumb style={{ marginBottom: 16 }}>
          <Breadcrumb.Item>
            <a onClick={() => { setSelectedQueryType(null); setQueryTypeFilter(null); }}>
              <ArrowLeftOutlined /> 全部查询类型
            </a>
          </Breadcrumb.Item>
          <Breadcrumb.Item>{getQueryTypeLabel(selectedQueryType)}</Breadcrumb.Item>
        </Breadcrumb>
      )}

      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Space wrap>
              <span style={{ color: '#666' }}>
                <InfoCircleOutlined /> 选择模型：
              </span>
              <Select
                mode="multiple"
                value={selectedModels}
                onChange={setSelectedModels}
                style={{ minWidth: 300 }}
                placeholder="选择要对比的模型"
                maxTagCount={5}
              >
                {models.map(model => (
                  <Option key={model.model_name} value={model.model_name}>
                    {model.model_name}
                    {model.description && ` - ${model.description}`}
                  </Option>
                ))}
              </Select>
            </Space>
          </div>

          <div>
            <Space wrap>
              <span style={{ color: '#666' }}>
                <InfoCircleOutlined /> 查询类型：
              </span>
              <Select
                value={queryTypeFilter}
                onChange={setQueryTypeFilter}
                style={{ width: 220 }}
                placeholder="选择查询类型"
              >
                {queryTypeOptions.map(opt => (
                  <Option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Space>
          </div>

          <div>
            <Space wrap>
              <span style={{ color: '#666' }}>
                <InfoCircleOutlined /> K 值：
              </span>
              <Select
                mode="multiple"
                value={kValues}
                onChange={setKValues}
                style={{ minWidth: 300 }}
                placeholder="选择 K 值"
              >
                {[1, 3, 5, 10, 15, 20, 30, 50].map(k => (
                  <Option key={k} value={k}>Top {k}</Option>
                ))}
              </Select>
            </Space>
          </div>

          <div>
            <Space wrap>
              <span style={{ color: '#666' }}>
                <InfoCircleOutlined /> 展示指标：
              </span>
              <Checkbox.Group value={selectedMetrics} onChange={setSelectedMetrics}>
                <Space>
                  {metricsOptions.map(opt => (
                    <Checkbox key={opt.value} value={opt.value}>
                      <Tag color={METRIC_COLORS[opt.value]}>{opt.label}</Tag>
                    </Checkbox>
                  ))}
                </Space>
              </Checkbox.Group>
            </Space>
          </div>

          <div>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadData}>
                刷新数据
              </Button>
              <Tooltip title="点击曲线上的数据点可以下钻查看各查询类型的详细对比">
                <Button icon={<DownOutlined />} onClick={() => handleChartClick('recall')}>
                  下钻分析
                </Button>
              </Tooltip>
            </Space>
          </div>
        </Space>
      </Card>

      {queryTypeStats.length > 0 && (
        <Card title="查询类型统计" style={{ marginBottom: 24 }}>
          <Row gutter={[16, 16]}>
            {queryTypeStats.map((stat, index) => (
              <Col xs={12} sm={6} key={stat.query_type}>
                <Card
                  className="metric-card"
                  hoverable
                  onClick={() => {
                    setQueryTypeFilter(stat.query_type);
                    setSelectedQueryType(stat.query_type);
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <Statistic
                    title={
                      <div>
                        <BarChartOutlined style={{ color: MODEL_COLORS[index % MODEL_COLORS.length] }} />
                        {' '}{getQueryTypeLabel(stat.query_type)}
                        <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                          {stat.count} 个查询
                        </div>
                      </div>
                    }
                    value={stat.avg_recall * 100}
                    suffix="%"
                    precision={1}
                    valueStyle={{ color: MODEL_COLORS[index % MODEL_COLORS.length] }}
                  />
                  <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                    <div>精确率: {(stat.avg_precision * 100).toFixed(1)}%</div>
                    <div>NDCG: {stat.avg_ndcg.toFixed(4)}</div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

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
            {selectedMetrics.includes('recall') && (
              <Col xs={12} sm={8}>
                <Card className="metric-card">
                  <Statistic
                    title={
                      <Tooltip title="平均召回率最高的模型">
                        <span>最优召回率模型</span>
                      </Tooltip>
                    }
                    value={getBestModelForMetric('recall')?.name || '-'}
                    suffix={
                      <Tag color="#1677ff">
                        {((getBestModelForMetric('recall')?.value || 0) * 100).toFixed(1)}%
                      </Tag>
                    }
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('precision') && (
              <Col xs={12} sm={8}>
                <Card className="metric-card">
                  <Statistic
                    title={
                      <Tooltip title="平均精确率最高的模型">
                        <span>最优精确率模型</span>
                      </Tooltip>
                    }
                    value={getBestModelForMetric('precision')?.name || '-'}
                    suffix={
                      <Tag color="#52c41a">
                        {((getBestModelForMetric('precision')?.value || 0) * 100).toFixed(1)}%
                      </Tag>
                    }
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('ndcg') && (
              <Col xs={12} sm={8}>
                <Card className="metric-card">
                  <Statistic
                    title={
                      <Tooltip title="平均 NDCG 最高的模型">
                        <span>最优 NDCG 模型</span>
                      </Tooltip>
                    }
                    value={getBestModelForMetric('ndcg')?.name || '-'}
                    suffix={
                      <Tag color="#13c2c2">
                        {(getBestModelForMetric('ndcg')?.value || 0).toFixed(4)}
                      </Tag>
                    }
                  />
                </Card>
              </Col>
            )}
          </Row>

          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            {selectedMetrics.includes('recall') && (
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts
                    option={getLineChartOption('recall')}
                    style={{ height: 350 }}
                    onEvents={onEvents('recall')}
                    opts={{ renderer: 'canvas' }}
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('precision') && (
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts
                    option={getLineChartOption('precision')}
                    style={{ height: 350 }}
                    onEvents={onEvents('precision')}
                    opts={{ renderer: 'canvas' }}
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('f1') && (
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts
                    option={getLineChartOption('f1')}
                    style={{ height: 350 }}
                    onEvents={onEvents('f1')}
                    opts={{ renderer: 'canvas' }}
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('hit_rate') && (
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts
                    option={getLineChartOption('hit_rate')}
                    style={{ height: 350 }}
                    onEvents={onEvents('hit_rate')}
                    opts={{ renderer: 'canvas' }}
                  />
                </Card>
              </Col>
            )}
            {selectedMetrics.includes('ndcg') && (
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts
                    option={getLineChartOption('ndcg')}
                    style={{ height: 350 }}
                    onEvents={onEvents('ndcg')}
                    opts={{ renderer: 'canvas' }}
                  />
                </Card>
              </Col>
            )}
          </Row>

          <Card>
            <ReactECharts option={getRadarChartOption()} style={{ height: 450 }} />
          </Card>

          {drilldownData.length > 0 && (
            <Card
              title={
                <Space>
                  <DownOutlined style={{ color: '#1677ff' }} />
                  <span>各查询类型对比 (下钻视图)</span>
                </Space>
              }
              style={{ marginTop: 24 }}
            >
              {selectedMetrics.slice(0, 2).map(metric => (
                <Row gutter={[16, 16]} key={metric} style={{ marginBottom: 16 }}>
                  {drilldownData.map((dd, index) => (
                    <Col xs={24} lg={12} key={dd.query_type}>
                      <Card
                        size="small"
                        onClick={() => {
                          setQueryTypeFilter(dd.query_type);
                          setSelectedQueryType(dd.query_type);
                        }}
                        style={{ cursor: 'pointer' }}
                        hoverable
                      >
                        <ReactECharts
                          option={getLineChartOption(metric, dd)}
                          style={{ height: 280 }}
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>
              ))}
            </Card>
          )}
        </div>
      ) : (
        <Alert message="请选择至少一个模型进行对比" type="info" showIcon />
      )}

      <Modal
        title={
          <Space>
            <DownOutlined style={{ color: '#1677ff' }} />
            <span>指标下钻分析</span>
          </Space>
        }
        open={drilldownModalVisible}
        width={1000}
        onCancel={() => setDrilldownModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDrilldownModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Space>
              <span style={{ color: '#666' }}>选择指标：</span>
              <Select value={drilldownMetric} onChange={setDrilldownMetric} style={{ width: 200 }}>
                {metricsOptions.map(opt => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Space>
          </Card>

          {queryTypeStats.length > 0 ? (
            <>
              <Card>
                <ReactECharts option={getDrilldownBarChartOption()} style={{ height: 350 }} />
              </Card>

              <Card title="各查询类型详细对比">
                {drilldownData.length > 0 ? (
                  <Row gutter={[16, 16]}>
                    {drilldownData.map(dd => (
                      <Col xs={24} lg={12} key={dd.query_type}>
                        <Card size="small">
                          <ReactECharts option={getLineChartOption(drilldownMetric, dd)} style={{ height: 280 }} />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                ) : (
                  <Empty description="暂无下钻数据" />
                )}
              </Card>
            </>
          ) : (
            <Empty description="暂无查询类型统计数据" />
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default ModelComparisonPage;
