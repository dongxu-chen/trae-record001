import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  DatePicker,
  Button,
  Space,
  Spin,
  Tag,
  Statistic,
  Descriptions,
  Table,
  Switch,
  message,
  Alert,
} from 'antd';
import {
  LineChartOutlined,
  FireOutlined,
  ToolOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import dayjs, { Dayjs } from 'dayjs';
import {
  analyticsApi,
  PredictionResult,
  RepairResult,
  TimelineResult,
  HeatmapData,
  SankeyData,
  RepairCapabilities,
} from '@/api/analytics';
import { deadLetterApi } from '@/api/deadLetter';
import { MqType } from '@/types/enums';

const { RangePicker } = DatePicker;
const { Option } = Select;

const Analytics: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [tabKey, setTabKey] = useState('prediction');
  const [mqType, setMqType] = useState<MqType | undefined>(undefined);
  const [topic, setTopic] = useState<string | undefined>(undefined);
  const [forecastDays, setForecastDays] = useState(7);
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);
  const [interval, setInterval] = useState('hourly');
  const [autoRepairEnabled, setAutoRepairEnabled] = useState(false);

  const [predictionData, setPredictionData] = useState<PredictionResult | null>(null);
  const [timelineData, setTimelineData] = useState<TimelineResult | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null);
  const [sankeyData, setSankeyData] = useState<SankeyData | null>(null);
  const [repairCapabilities, setRepairCapabilities] = useState<RepairCapabilities | null>(null);
  const [repairResult, setRepairResult] = useState<RepairResult | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState('');
  const [topicList, setTopicList] = useState<string[]>([]);

  const fetchTopics = async () => {
    try {
      const result = await deadLetterApi.getAggregation({ groupBy: 'topic' });
      if (result && result.data) {
        const topics = result.data.map((item: any) => item.key);
        setTopicList(topics);
      }
    } catch (error) {
      console.error('Failed to fetch topics:', error);
    }
  };

  const fetchPrediction = async () => {
    setLoading(true);
    try {
      const result = await analyticsApi.predictTrend({
        topic,
        mqType,
        forecastDays,
        startTime: dateRange[0]?.format('YYYY-MM-DD HH:mm:ss'),
        endTime: dateRange[1]?.format('YYYY-MM-DD HH:mm:ss'),
      });
      setPredictionData(result);
    } catch (error) {
      console.error('Failed to fetch prediction:', error);
      message.error('获取预测数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchVisualization = async () => {
    setLoading(true);
    try {
      const [timelineRes, heatmapRes, sankeyRes] = await Promise.all([
        analyticsApi.getTimeline({
          topic,
          mqType,
          interval,
          startTime: dateRange[0]?.format('YYYY-MM-DD HH:mm:ss'),
          endTime: dateRange[1]?.format('YYYY-MM-DD HH:mm:ss'),
        }),
        analyticsApi.getHeatmap({
          topic,
          mqType,
          startTime: dateRange[0]?.format('YYYY-MM-DD HH:mm:ss'),
          endTime: dateRange[1]?.format('YYYY-MM-DD HH:mm:ss'),
        }),
        analyticsApi.getSankey({
          topic,
          mqType,
          startTime: dateRange[0]?.format('YYYY-MM-DD HH:mm:ss'),
          endTime: dateRange[1]?.format('YYYY-MM-DD HH:mm:ss'),
        }),
      ]);

      if (timelineRes.success && timelineRes.data) {
        setTimelineData(timelineRes.data.timeline || null);
      }
      if (heatmapRes.success && heatmapRes.data) {
        setHeatmapData(heatmapRes.data.heatmap || null);
      }
      if (sankeyRes.success && sankeyRes.data) {
        setSankeyData(sankeyRes.data.sankey || null);
      }
    } catch (error) {
      console.error('Failed to fetch visualization:', error);
      message.error('获取可视化数据失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchRepairCapabilities = async () => {
    try {
      const result = await analyticsApi.getRepairCapabilities();
      setRepairCapabilities(result);
    } catch (error) {
      console.error('Failed to fetch repair capabilities:', error);
    }
  };

  const handleAutoRepair = async () => {
    if (!selectedMessageId.trim()) {
      message.warning('请输入消息ID');
      return;
    }

    setLoading(true);
    try {
      const result = await analyticsApi.autoRepair(selectedMessageId, autoRepairEnabled);
      setRepairResult(result);
      if (result.repaired) {
        message.success('自动修复成功');
      } else {
        message.info('未能自动修复');
      }
    } catch (error) {
      console.error('Auto repair failed:', error);
      message.error('自动修复失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopics();
    fetchRepairCapabilities();
  }, []);

  useEffect(() => {
    if (tabKey === 'prediction') {
      fetchPrediction();
    } else if (tabKey === 'visualization') {
      fetchVisualization();
    }
  }, [tabKey, mqType, topic, forecastDays, interval, dateRange]);

  const getTrendChartOption = () => {
    if (!predictionData?.data?.dailyPredictions) return {};

    const predictions = predictionData.data.dailyPredictions;
    const times = predictions.map((p) => dayjs(p.time).format('MM-DD'));

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: ['预测值', '置信区间上界', '置信区间下界'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: times },
      yAxis: { type: 'value' },
      series: [
        {
          name: '预测值',
          type: 'line',
          smooth: true,
          data: predictions.map((p) => p.predicted),
          lineStyle: { color: '#1890ff', width: 3 },
          itemStyle: { color: '#1890ff' },
        },
        {
          name: '置信区间上界',
          type: 'line',
          lineStyle: { type: 'dashed', color: '#52c41a' },
          data: predictions.map((p) => p.upperBound),
        },
        {
          name: '置信区间下界',
          type: 'line',
          lineStyle: { type: 'dashed', color: '#fa8c16' },
          data: predictions.map((p) => p.lowerBound),
        },
      ],
    };
  };

  const getTimelineChartOption = () => {
    if (!timelineData?.data) return {};

    const data = timelineData.data;
    const times = data.map((d) => dayjs(d.timestamp).format('MM-DD HH:mm'));

    return {
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: times },
      yAxis: { type: 'value' },
      series: [
        {
          name: '死信数量',
          type: 'line',
          smooth: true,
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(114, 46, 209, 0.3)' },
                { offset: 1, color: 'rgba(114, 46, 209, 0.05)' },
              ],
            },
          },
          lineStyle: { color: '#722ed1', width: 2 },
          itemStyle: { color: '#722ed1' },
          data: data.map((d) => d.count),
        },
      ],
    };
  };

  const getHeatmapChartOption = () => {
    if (!heatmapData?.cells) return {};

    return {
      tooltip: { position: 'top' },
      grid: { height: '50%', top: '10%' },
      xAxis: { type: 'category', data: heatmapData.xLabels, splitArea: { show: true } },
      yAxis: { type: 'category', data: heatmapData.yLabels, splitArea: { show: true } },
      visualMap: {
        min: heatmapData.minValue,
        max: heatmapData.maxValue,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '5%',
        inRange: { color: ['#fff7e6', '#ff7c00', '#750e0e'] },
      },
      series: [
        {
          name: '死信数量',
          type: 'heatmap',
          data: heatmapData.cells.map((c) => [c.x, c.y, c.value]),
          label: { show: true },
        },
      ],
    };
  };

  const getSankeyChartOption = () => {
    if (!sankeyData?.nodes || !sankeyData?.links) return {};

    return {
      tooltip: { trigger: 'item', triggerOn: 'mousemove' },
      series: [
        {
          type: 'sankey',
          layout: 'none',
          emphasis: { focus: 'adjacency' },
          lineStyle: { color: 'gradient', curveness: 0.5 },
          data: sankeyData.nodes,
          links: sankeyData.links.map((l) => ({
            source: sankeyData.nodes[l.source].name,
            target: sankeyData.nodes[l.target].name,
            value: l.value,
          })),
        },
      ],
    };
  };

  const getTrendName = (trend: string) => {
    const map: Record<string, { name: string; color: string }> = {
      INCREASING: { name: '增长', color: 'red' },
      DECREASING: { name: '下降', color: 'green' },
      STABLE: { name: '稳定', color: 'blue' },
      UNKNOWN: { name: '未知', color: 'default' },
    };
    return map[trend] || map.UNKNOWN;
  };

  const getAlertLevelName = (level: string) => {
    const map: Record<string, string> = {
      NORMAL: '正常', INFO: '提示', WARNING: '警告', CRITICAL: '严重',
    };
    return map[level] || level;
  };

  const repairColumns = [
    { title: '修复类型', dataIndex: 'type', key: 'type' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (value: number) => (
        <Tag color={value >= 0.7 ? 'green' : value >= 0.5 ? 'orange' : 'red'}>
          {(value * 100).toFixed(0)}%
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        tabList={[
          {
            key: 'prediction',
            tab: (
              <span>
                <LineChartOutlined /> 趋势预测
              </span>
            ),
          },
          {
            key: 'visualization',
            tab: (
              <span>
                <FireOutlined /> 可视化分析
              </span>
            ),
          },
          {
            key: 'auto-repair',
            tab: (
              <span>
                <ToolOutlined /> 自动修复
              </span>
            ),
          },
        ]}
        activeTabKey={tabKey}
        onTabChange={setTabKey}
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              if (tabKey === 'prediction') fetchPrediction();
              else if (tabKey === 'visualization') fetchVisualization();
            }}
          >
            刷新
          </Button>
        }
      >
        <Space style={{ marginBottom: 16, flexWrap: 'wrap' }}>
          <Select
            placeholder="选择MQ类型"
            style={{ width: 150 }}
            allowClear
            value={mqType}
            onChange={setMqType}
          >
            <Option value="RABBITMQ">RabbitMQ</Option>
            <Option value="ROCKETMQ">RocketMQ</Option>
            <Option value="KAFKA">Kafka</Option>
          </Select>

          <Select
            placeholder="选择Topic"
            style={{ width: 200 }}
            allowClear
            showSearch
            value={topic}
            onChange={setTopic}
          >
            {topicList.map((t) => (
              <Option key={t} value={t}>{t}</Option>
            ))}
          </Select>

          <RangePicker showTime value={dateRange} onChange={setDateRange} />

          {tabKey === 'prediction' && (
            <Select style={{ width: 150 }} value={forecastDays} onChange={setForecastDays}>
              <Option value={3}>预测3天</Option>
              <Option value={7}>预测7天</Option>
              <Option value={14}>预测14天</Option>
              <Option value={30}>预测30天</Option>
            </Select>
          )}

          {tabKey === 'visualization' && (
            <Select style={{ width: 150 }} value={interval} onChange={setInterval}>
              <Option value="hourly">按小时</Option>
              <Option value="daily">按天</Option>
              <Option value="weekly">按周</Option>
              <Option value="monthly">按月</Option>
            </Select>
          )}
        </Space>

        <Spin spinning={loading}>
          {tabKey === 'prediction' && (
            <div>
              {predictionData?.success && predictionData.data ? (
                <Row gutter={[16, 16]}>
                  <Col xs={24}>
                    <Card title="趋势预测结果">
                      <Row gutter={16}>
                        <Col span={6}>
                          <Statistic
                            title="预测趋势"
                            value={getTrendName(predictionData.data.trend).name}
                            valueStyle={{ color: getTrendName(predictionData.data.trend).color }}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic title="增长率" value={predictionData.data.growthRate} />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title={`预测${forecastDays}天总数`}
                            value={predictionData.data.predictedTotal}
                          />
                        </Col>
                        <Col span={6}>
                          <Statistic
                            title="告警级别"
                            value={getAlertLevelName(predictionData.data.alertLevel)}
                          />
                        </Col>
                      </Row>

                      {predictionData.data.alertMessage && (
                        <Alert
                          message={predictionData.data.alertMessage}
                          type={predictionData.data.alertLevel === 'WARNING' ? 'warning' : 'info'}
                          showIcon
                          style={{ marginTop: 16 }}
                        />
                      )}
                    </Card>
                  </Col>

                  <Col xs={24}>
                    <Card title="预测图表">
                      <ReactECharts option={getTrendChartOption()} style={{ height: 400 }} />
                    </Card>
                  </Col>

                  <Col xs={24}>
                    <Card title="预测详情">
                      <Descriptions bordered column={2}>
                        <Descriptions.Item label="历史数据点">
                          {predictionData.historicalDataPoints}
                        </Descriptions.Item>
                        <Descriptions.Item label="预测天数">{forecastDays}天</Descriptions.Item>
                        <Descriptions.Item label="历史均值">
                          {predictionData.data.metrics?.historicalAvg}
                        </Descriptions.Item>
                        <Descriptions.Item label="历史最大值">
                          {predictionData.data.metrics?.historicalMax}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                </Row>
              ) : (
                <Card>
                  <Alert message={predictionData?.message || '暂无数据'} type="info" />
                </Card>
              )}
            </div>
          )}

          {tabKey === 'visualization' && (
            <Row gutter={[16, 16]}>
              <Col xs={24}>
                <Card title="时间线分布">
                  <ReactECharts option={getTimelineChartOption()} style={{ height: 350 }} />
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="周-小时热力图">
                  <ReactECharts option={getHeatmapChartOption()} style={{ height: 400 }} />
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="流向分析（桑基图）">
                  <ReactECharts option={getSankeyChartOption()} style={{ height: 400 }} />
                </Card>
              </Col>
            </Row>
          )}

          {tabKey === 'auto-repair' && (
            <Row gutter={[16, 16]}>
              <Col xs={24}>
                <Card title="自动修复">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <Select
                        placeholder="输入消息ID"
                        style={{ width: 300 }}
                        showSearch
                        allowClear
                        value={selectedMessageId}
                        onChange={setSelectedMessageId}
                      />
                      <Switch
                        checkedChildren="自动重放"
                        unCheckedChildren="仅修复"
                        checked={autoRepairEnabled}
                        onChange={setAutoRepairEnabled}
                      />
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleAutoRepair}
                      >
                        执行修复
                      </Button>
                    </Space>

                    {repairResult && (
                      <Card title="修复结果" type="inner" style={{ marginTop: 16 }}>
                        <Descriptions bordered column={1}>
                          <Descriptions.Item label="修复成功">
                            {repairResult.repaired ? (
                              <Tag color="green">是</Tag>
                            ) : (
                              <Tag color="red">否</Tag>
                            )}
                          </Descriptions.Item>
                          {repairResult.repairType && (
                            <Descriptions.Item label="修复类型">
                              {repairResult.repairType}
                            </Descriptions.Item>
                          )}
                          {repairResult.confidence && (
                            <Descriptions.Item label="置信度">
                              {(repairResult.confidence * 100).toFixed(2)}%
                            </Descriptions.Item>
                          )}
                          {repairResult.repairSteps && repairResult.repairSteps.length > 0 && (
                            <Descriptions.Item label="修复步骤">
                              <ul>
                                {repairResult.repairSteps.map((step, idx) => (
                                  <li key={idx}>{step}</li>
                                ))}
                              </ul>
                            </Descriptions.Item>
                          )}
                          {repairResult.originalError && (
                            <Descriptions.Item label="原始错误">
                              {repairResult.originalError}
                            </Descriptions.Item>
                          )}
                          {repairResult.autoReplayResult && (
                            <Descriptions.Item label="自动重放结果">
                              <Tag color="green">已重放</Tag>
                            </Descriptions.Item>
                          )}
                          {repairResult.autoReplaySkipped && (
                            <Descriptions.Item label="自动重放跳过原因">
                              {repairResult.skipReason}
                            </Descriptions.Item>
                          )}
                        </Descriptions>
                      </Card>
                    )}
                  </Space>
                </Card>
              </Col>

              <Col xs={24}>
                <Card title="支持的修复策略">
                  <Table
                    dataSource={repairCapabilities?.strategies}
                    columns={repairColumns}
                    rowKey="type"
                    pagination={false}
                  />
                </Card>
              </Col>
            </Row>
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default Analytics;
