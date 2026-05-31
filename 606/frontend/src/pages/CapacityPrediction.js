import React, { useState, useEffect } from 'react';
import {
  Card, Button, Table, Tag, Space, message, Statistic, Row, Col,
  Progress, Alert, List, Tooltip, Badge, Select
} from 'antd';
import {
  DashboardOutlined, TrendingUpOutlined, WarningOutlined,
  CheckCircleOutlined, BellOutlined, ThunderboltOutlined,
  BarChartOutlined, ReloadOutlined
} from '@ant-design/icons';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  Legend, ResponsiveContainer, AreaChart, Area, ReferenceLine,
  ComposedChart, Bar
} from 'recharts';
import { capacityApi } from '../services/api';

const { Option } = Select;

const CapacityPrediction = () => {
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [watermarks, setWatermarks] = useState({});
  const [horizonHours, setHorizonHours] = useState(24);

  useEffect(() => {
    loadData();
  }, [horizonHours]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [predRes, waterRes] = await Promise.all([
        capacityApi.predictCapacity('default', horizonHours),
        capacityApi.getWatermarks(1.0)
      ]);
      setPrediction(predRes.data?.data);
      setWatermarks(waterRes.data?.data || {});
    } catch (e) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'LOW': return '#52c41a';
      case 'MEDIUM': return '#1677ff';
      case 'HIGH': return '#faad14';
      case 'CRITICAL': return '#ff4d4f';
      default: return '#999';
    }
  };

  const getRiskText = (riskLevel) => {
    switch (riskLevel) {
      case 'LOW': return '低风险';
      case 'MEDIUM': return '中风险';
      case 'HIGH': return '高风险';
      case 'CRITICAL': return '严重风险';
      default: return riskLevel;
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return `${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
  };

  const renderCapacityChart = () => {
    if (!prediction) return null;

    const historical = (prediction.historicalData || []).map((p, i) => ({
      ...p,
      time: formatTime(p.timestamp),
      type: '历史',
      index: i
    }));

    const predicted = (prediction.predictedData || []).map((p, i) => ({
      ...p,
      time: formatTime(p.timestamp),
      type: '预测',
      index: historical.length + i
    }));

    const allData = [...historical, ...predicted];

    return (
      <Card 
        title={
          <Space>
            <BarChartOutlined />
            容量趋势预测
          </Space>
        } 
        size="small"
        extra={
          <Space>
            <span>预测时长:</span>
            <Select 
              value={horizonHours} 
              onChange={setHorizonHours} 
              style={{ width: 120 }}
              size="small"
            >
              <Option value={6}>6小时</Option>
              <Option value={12}>12小时</Option>
              <Option value={24}>24小时</Option>
              <Option value={48}>48小时</Option>
              <Option value={168}>7天</Option>
            </Select>
          </Space>
        }
      >
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={allData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time" 
              interval={Math.floor(allData.length / 10)}
            />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <RechartsTooltip />
            <Legend />
            
            <ReferenceLine 
              yAxisId="left"
              y={watermarks.safeWatermark} 
              stroke="#52c41a" 
              strokeDasharray="3 3" 
              label={{ value: '安全水位', fill: '#52c41a', fontSize: 10 }}
            />
            <ReferenceLine 
              yAxisId="left"
              y={watermarks.highWatermark} 
              stroke="#ff4d4f" 
              strokeDasharray="3 3" 
              label={{ value: '告警水位', fill: '#ff4d4f', fontSize: 10 }}
            />
            
            <Area 
              yAxisId="left"
              type="monotone" 
              dataKey="qps" 
              name="QPS(历史)"
              stroke="#1677ff" 
              fill="#91caff" 
              fillOpacity={0.3}
              dot={false}
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey={d => d.type === '预测' ? d.qps : null} 
              name="QPS(预测)"
              stroke="#faad14" 
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="errorRate" 
              name="错误率(%)"
              stroke="#ff4d4f" 
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>
    );
  };

  const renderResourceChart = () => {
    if (!prediction?.predictedData?.length) return null;

    const data = prediction.predictedData.map(p => ({
      ...p,
      time: formatTime(p.timestamp)
    }));

    return (
      <Card 
        title={
          <Space>
            <DashboardOutlined />
            资源使用率预测
          </Space>
        } 
        size="small"
        style={{ marginTop: 16 }}
      >
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1677ff" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#1677ff" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#52c41a" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#52c41a" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="time" 
              interval={Math.floor(data.length / 8)}
            />
            <YAxis domain={[0, 100]} />
            <RechartsTooltip formatter={(value) => `${value?.toFixed(1)}%`} />
            <Legend />
            <ReferenceLine 
              y={80} 
              stroke="#ff4d4f" 
              strokeDasharray="3 3" 
              label={{ value: '80%告警', fill: '#ff4d4f', fontSize: 10 }}
            />
            <Area 
              type="monotone" 
              dataKey="cpuUsage" 
              name="CPU使用率"
              stroke="#1677ff" 
              fill="url(#cpuGradient)" 
              strokeWidth={2}
            />
            <Area 
              type="monotone" 
              dataKey="memoryUsage" 
              name="内存使用率"
              stroke="#52c41a" 
              fill="url(#memGradient)" 
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    );
  };

  const renderWarnings = () => {
    if (!prediction?.warnings?.length && !prediction?.recommendations?.length) return null;

    return (
      <Card 
        title={
          <Space>
            <BellOutlined />
            告警与建议
          </Space>
        } 
        size="small"
        style={{ marginTop: 16 }}
      >
        {prediction.warnings?.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 500, marginBottom: 8, color: '#ff4d4f' }}>
              <WarningOutlined /> 风险告警:
            </div>
            <List
              size="small"
              dataSource={prediction.warnings}
              renderItem={(item) => (
                <List.Item>
                  <Alert message={item} type="warning" showIcon />
                </List.Item>
              )}
            />
          </div>
        )}
        
        {prediction.recommendations?.length > 0 && (
          <div>
            <div style={{ fontWeight: 500, marginBottom: 8, color: '#1677ff' }}>
              <CheckCircleOutlined /> 优化建议:
            </div>
            <List
              size="small"
              dataSource={prediction.recommendations}
              renderItem={(item) => (
                <List.Item>
                  <Alert message={item} type="info" showIcon />
                </List.Item>
              )}
            />
          </div>
        )}
      </Card>
    );
  };

  return (
    <div>
      <Card
        title={
          <Space>
            <TrendingUpOutlined />
            容量预测分析
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
            刷新预测
          </Button>
        }
      >
        {prediction && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={5}>
                <Card size="small">
                  <Statistic
                    title="当前容量"
                    value={prediction.currentCapacity?.toFixed(0)}
                    suffix="QPS"
                    prefix={<DashboardOutlined />}
                  />
                </Card>
              </Col>
              <Col span={5}>
                <Card size="small">
                  <Statistic
                    title="安全容量"
                    value={prediction.safeCapacity?.toFixed(0)}
                    suffix="QPS"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={5}>
                <Card size="small">
                  <Statistic
                    title="预测峰值"
                    value={prediction.predictedPeakQps?.toFixed(0)}
                    suffix="QPS"
                    valueStyle={{ color: '#faad14' }}
                    prefix={<ThunderboltOutlined />}
                  />
                </Card>
              </Col>
              <Col span={5}>
                <Card size="small">
                  <Statistic
                    title="容量利用率"
                    value={prediction.capacityUtilization?.toFixed(1)}
                    suffix="%"
                    valueStyle={{ 
                      color: (prediction.capacityUtilization || 0) > 80 ? '#ff4d4f' : '#52c41a' 
                    }}
                  />
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic
                    title="风险等级"
                    value={getRiskText(prediction.riskLevel)}
                    valueStyle={{ 
                      color: getRiskColor(prediction.riskLevel),
                      fontSize: 16 
                    }}
                    prefix={<Badge color={getRiskColor(prediction.riskLevel)} />}
                  />
                </Card>
              </Col>
            </Row>

            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small" title="水位线">
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ display: 'inline-block', width: 80 }}>低水位:</span>
                    <Progress percent={(watermarks.lowWatermark / (prediction.maxCapacity || 1)) * 100} size="small" strokeColor="#52c41a" />
                    <span style={{ marginLeft: 8 }}>{watermarks.lowWatermark?.toFixed(0)} QPS</span>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ display: 'inline-block', width: 80 }}>中水位:</span>
                    <Progress percent={(watermarks.midWatermark / (prediction.maxCapacity || 1)) * 100} size="small" strokeColor="#1677ff" />
                    <span style={{ marginLeft: 8 }}>{watermarks.midWatermark?.toFixed(0)} QPS</span>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ display: 'inline-block', width: 80 }}>高水位:</span>
                    <Progress percent={(watermarks.highWatermark / (prediction.maxCapacity || 1)) * 100} size="small" strokeColor="#ff4d4f" />
                    <span style={{ marginLeft: 8 }}>{watermarks.highWatermark?.toFixed(0)} QPS</span>
                  </div>
                  <div>
                    <span style={{ display: 'inline-block', width: 80 }}>安全水位:</span>
                    <Progress percent={(watermarks.safeWatermark / (prediction.maxCapacity || 1)) * 100} size="small" strokeColor="#52c41a" />
                    <span style={{ marginLeft: 8 }}>{watermarks.safeWatermark?.toFixed(0)} QPS</span>
                  </div>
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" title="预测指标">
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ display: 'inline-block', width: 100 }}>预测置信度:</span>
                    <Progress percent={(prediction.confidence * 100)?.toFixed(0)} size="small" />
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ display: 'inline-block', width: 100 }}>峰值响应时间:</span>
                    <span style={{ color: prediction.predictedPeakLatency > 500 ? '#ff4d4f' : '#52c41a' }}>
                      {prediction.predictedPeakLatency?.toFixed(0)} ms
                    </span>
                  </div>
                  <div>
                    <span style={{ display: 'inline-block', width: 100 }}>预测错误率:</span>
                    <span style={{ color: prediction.predictedErrorRate > 5 ? '#ff4d4f' : '#52c41a' }}>
                      {prediction.predictedErrorRate?.toFixed(2)} %
                    </span>
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="预测模型">
                  <div style={{ fontSize: 12, color: '#666' }}>
                    <div>趋势斜率: {prediction.predictionModel?.trendSlope?.toFixed(4)}</div>
                    <div>噪声水平: {prediction.predictionModel?.noiseLevel?.toFixed(2)}</div>
                    <div>数据点数: {prediction.predictionModel?.dataPoints}</div>
                    <div>预测周期: {prediction.predictionHorizonHours} 小时</div>
                  </div>
                </Card>
              </Col>
            </Row>

            {renderCapacityChart()}
            {renderResourceChart()}
            {renderWarnings()}
          </>
        )}

        {!prediction && !loading && (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            暂无预测数据，请先执行演练任务
          </div>
        )}
      </Card>
    </div>
  );
};

export default CapacityPrediction;
