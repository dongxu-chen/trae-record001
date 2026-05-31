import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Spin, Tag } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons'
import { getPredictions, type Prediction } from '../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const getTrendIcon = (trend: string) => {
  switch (trend) {
    case 'increasing':
      return <ArrowUpOutlined style={{ color: '#f5222d' }} />
    case 'decreasing':
      return <ArrowDownOutlined style={{ color: '#52c41a' }} />
    default:
      return <MinusOutlined style={{ color: '#1890ff' }} />
  }
}

const getTrendTag = (trend: string) => {
  const colors: Record<string, string> = {
    increasing: 'red',
    decreasing: 'green',
    stable: 'blue',
    insufficient_data: 'default',
  }
  const labels: Record<string, string> = {
    increasing: '增长趋势',
    decreasing: '下降趋势',
    stable: '稳定',
    insufficient_data: '数据不足',
  }
  return <Tag color={colors[trend]}>{labels[trend] || trend}</Tag>
}

const Trends = () => {
  const [loading, setLoading] = useState(true)
  const [predictions, setPredictions] = useState<Record<string, Prediction>>({})

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getPredictions()
      setPredictions(data || {})
    } catch (error) {
      console.error('Failed to load predictions:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 300000)
    return () => clearInterval(interval)
  }, [])

  const formatChartData = (pred: Prediction) => {
    const historical = (pred.historical_data || []).map(d => ({
      ...d,
      type: '历史',
    }))
    const predicted = (pred.predicted_data || []).map(d => ({
      ...d,
      type: '预测',
    }))
    return [...historical, ...predicted]
  }

  const getSeasonLabel = (seasonType: string) => {
    const labels: Record<string, string> = {
      daily: '日周期',
      weekly: '周周期',
      half_daily: '半日周期',
      quarter_daily: '6小时周期',
      none: '无明显周期',
    }
    return labels[seasonType] || seasonType
  }

  const metricLabels: Record<string, string> = {
    total_nodes: '总节点数',
    total_size: '总数据量',
    max_depth: '最大深度',
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>趋势预测</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {Object.entries(predictions).map(([key, pred]) => (
          <Col xs={24} md={8} key={key}>
            <Card>
              <Statistic
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    {metricLabels[key] || key}
                    {getTrendTag(pred.trend)}
                    <Tag color="purple">{getSeasonLabel(pred.season_type || 'none')}</Tag>
                  </div>
                }
                value={key === 'total_size' ? formatBytes(pred.predicted_value_7d || 0) : Math.round(pred.predicted_value_7d || 0)}
                prefix={getTrendIcon(pred.trend)}
                precision={key === 'total_size' ? 0 : 0}
              />
              <div style={{ marginTop: 16 }}>
                <small>增长率: {pred.growth_rate?.toFixed(2) || 0}%</small>
                <br />
                <small>7天预测值</small>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        {Object.entries(predictions).map(([key, pred]) => (
          <Col xs={24} lg={12} key={key}>
            <Card title={`${metricLabels[key] || key}趋势图`}>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={formatChartData(pred)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                  <YAxis
                    tickFormatter={key === 'total_size' ? (value) => formatBytes(value) : undefined}
                  />
                  <Tooltip
                    formatter={key === 'total_size' ? (value: number) => [formatBytes(value), ''] : undefined}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="历史数据"
                    stroke="#1890ff"
                    strokeWidth={2}
                    dot={false}
                    connectNulls
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    name="预测数据"
                    stroke="#ff7a45"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    connectNulls
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}

export default Trends
