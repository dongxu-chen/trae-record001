import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Table,
  Tag,
  Space,
  Alert,
  Button,
  message,
  List,
  Tooltip,
} from 'antd';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
} from 'recharts';
import { predictionAPI } from '../api/api';

function getRiskColor(level) {
  const colors = {
    high: '#cf1322',
    medium: '#faad14',
    low: '#1890ff',
    normal: '#52c41a',
    unknown: '#999',
  };
  return colors[level] || '#999';
}

function getRiskLabel(level) {
  const labels = {
    high: '高风险',
    medium: '中等风险',
    low: '低风险',
    normal: '正常',
    unknown: '未知',
  };
  return labels[level] || level;
}

function getTrendColor(direction) {
  const colors = {
    increasing: '#cf1322',
    decreasing: '#52c41a',
    stable: '#1890ff',
  };
  return colors[direction] || '#999';
}

function getTrendLabel(direction) {
  const labels = {
    increasing: '↑ 上升',
    decreasing: '↓ 下降',
    stable: '→ 稳定',
  };
  return labels[direction] || direction;
}

function Prediction() {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [hotCommands, setHotCommands] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [summaryRes, hotRes] = await Promise.all([
        predictionAPI.getSummary(),
        predictionAPI.getHotCommands(10),
      ]);

      if (summaryRes.data.success) {
        setSummary(summaryRes.data.data);
        
        const predictions = summaryRes.data.data?.trend_prediction?.predictions || [];
        setTrendData(predictions.map((p, idx) => ({
          hour: p.hour.split(' ')[1],
          predicted: p.predicted_count,
          duration: p.predicted_avg_duration,
          is_peak: p.is_peak,
        })));
      }

      if (hotRes.data.success) {
        setHotCommands(hotRes.data.data || []);
      }
    } catch (error) {
      message.error('加载预测数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '命令',
      dataIndex: 'command',
      key: 'command',
      render: (text) => <Tag color="purple">{text}</Tag>,
    },
    {
      title: '历史次数',
      dataIndex: 'historical_count',
      key: 'historical_count',
      sorter: (a, b) => a.historical_count - b.historical_count,
      render: (val) => val.toLocaleString(),
    },
    {
      title: '预测24h',
      dataIndex: 'predicted_24h_count',
      key: 'predicted_24h_count',
      sorter: (a, b) => a.predicted_24h_count - b.predicted_24h_count,
      render: (val) => val.toLocaleString(),
    },
    {
      title: '趋势',
      dataIndex: 'trend',
      key: 'trend',
      render: (val) => (
        <Tag color={getTrendColor(val)}>{getTrendLabel(val)}</Tag>
      ),
    },
    {
      title: '增长率',
      dataIndex: 'growth_rate',
      key: 'growth_rate',
      render: (val) => (
        <span style={{ color: val > 0 ? '#cf1322' : '#52c41a' }}>
          {val > 0 ? '+' : ''}{val.toFixed(1)}%
        </span>
      ),
    },
  ];

  if (!summary) {
    return (
      <Card loading={loading}>
        <Alert message="数据加载中..." type="info" />
      </Card>
    );
  }

  const risk = summary.risk_assessment || {};
  const trendPrediction = summary.trend_prediction || {};

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        <Button onClick={loadData} loading={loading} type="primary">
          刷新预测
        </Button>
      </div>

      {risk.risk_level !== 'normal' && risk.risk_level !== 'unknown' && (
        <Alert
          message="慢查询风险预警"
          description={
            <div>
              <p>
                <strong>风险等级:</strong>{' '}
                <Tag color={getRiskColor(risk.risk_level)}>
                  {getRiskLabel(risk.risk_level)}
                </Tag>
              </p>
              <p>
                <strong>预测24小时慢查询数:</strong>{' '}
                {risk.predicted_24h_count?.toLocaleString()} 次
              </p>
              <ul>
                {risk.recommendations?.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          }
          type={risk.risk_level === 'high' ? 'error' : 'warning'}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="风险等级"
              value={getRiskLabel(risk.risk_level)}
              valueStyle={{ color: getRiskColor(risk.risk_level) }}
              suffix={
                <Progress
                  type="circle"
                  percent={risk.confidence || 0}
                  size={40}
                  format={(p) => `${p}%`}
                />
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="预测24h慢查询数"
              value={risk.predicted_24h_count || 0}
              valueStyle={{ color: '#667eea' }}
              suffix="次"
            />
            <div style={{ marginTop: 8 }}>
              <Tag color={getTrendColor(trendPrediction.trend?.direction)}>
                {getTrendLabel(trendPrediction.trend?.direction)}
              </Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="预测峰值"
              value={risk.peak_count || 0}
              valueStyle={{ color: '#faad14' }}
              suffix="次/小时"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="历史数据量"
              value={trendPrediction.historical_hours || 0}
              valueStyle={{ color: '#52c41a' }}
              suffix="小时"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="24小时慢查询预测" className="chart-container" style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <RechartsTooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="predicted"
                  stroke="#667eea"
                  fill="#667eea"
                  fillOpacity={0.3}
                  name="预测次数"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="高峰时段预测" style={{ height: 320, overflow: 'auto' }}>
            {trendPrediction.seasonal_patterns?.peak_hours?.length > 0 ? (
              <List
                dataSource={trendPrediction.seasonal_patterns.peak_hours}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <Tag color="orange">{item.hour}:00 - {item.hour + 1}:00</Tag>
                      <span>平均 {Math.round(item.avg_count)} 次</span>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                暂无高峰时段数据
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="热点命令预测" className="table-container">
            <Table
              columns={columns}
              dataSource={hotCommands}
              rowKey="command"
              loading={loading}
              pagination={{
                pageSize: 10,
                showTotal: (total) => `共 ${total} 条命令`,
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="趋势说明" style={{ height: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="趋势方向"
                description={trendPrediction.trend?.description || '暂无趋势数据'}
                type="info"
                showIcon
              />
              
              {trendPrediction.seasonal_patterns?.off_peak_hours?.length > 0 && (
                <Alert
                  message="建议操作时段"
                  description={
                    <div>
                      <p>推荐在以下低峰时段执行批量操作:</p>
                      <Space wrap>
                        {trendPrediction.seasonal_patterns.off_peak_hours.slice(0, 5).map((h) => (
                          <Tag key={h.hour} color="green">
                            {h.hour}:00 - {h.hour + 1}:00
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  }
                  type="success"
                  showIcon
                />
              )}

              <Alert
                message="预测说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    <li>使用指数平滑法进行时间序列预测</li>
                    <li>考虑了每日周期性模式</li>
                    <li>置信度基于历史数据波动率计算</li>
                    <li>数据不足时置信度会降低</li>
                  </ul>
                }
                type="info"
                showIcon
              />
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Prediction;
