import { useEffect, useState } from 'react'
import { Row, Col, Card, Button, Spin, message, Progress, Tag } from 'antd'
import {
  ReloadOutlined,
  ClusterOutlined,
  FileTextOutlined,
  BarsOutlined,
  WarningOutlined,
  HeartOutlined,
  FireOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import { getOverview, getTimeSeries, triggerCollection } from '../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell } from 'recharts'

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const gradeColors: Record<string, string> = {
  A: '#52c41a',
  B: '#1890ff',
  C: '#faad14',
  D: '#fa8c16',
  F: '#f5222d',
}

const PIE_COLORS = ['#f5222d', '#faad14', '#1890ff']

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<any>(null)
  const [nodeData, setNodeData] = useState<any[]>([])
  const [sizeData, setSizeData] = useState<any[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const overviewData = await getOverview()
      setOverview(overviewData)

      const nodeSeries = await getTimeSeries('total_nodes', '24h')
      const sizeSeries = await getTimeSeries('total_size', '24h')

      setNodeData(nodeSeries.map(d => ({ ...d, value: d.value })))
      setSizeData(sizeSeries.map(d => ({ ...d, value: d.value })))
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCollect = async () => {
    try {
      await triggerCollection()
      message.success('数据采集成功')
      loadData()
    } catch (error) {
      message.error('数据采集失败')
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const stats = [
    {
      title: '总节点数',
      value: overview?.total_nodes || 0,
      icon: <ClusterOutlined style={{ fontSize: 32 }} />,
      className: 'stat-card',
    },
    {
      title: '总数据量',
      value: formatBytes(overview?.total_size || 0),
      icon: <FileTextOutlined style={{ fontSize: 32 }} />,
      className: 'stat-card-green',
    },
    {
      title: '最大深度',
      value: overview?.max_depth || 0,
      icon: <BarsOutlined style={{ fontSize: 32 }} />,
      className: 'stat-card-orange',
    },
    {
      title: '预警数量',
      value: overview?.alert_count || 0,
      icon: <WarningOutlined style={{ fontSize: 32 }} />,
      className: 'stat-card-blue',
    },
  ]

  const healthScore = overview?.health_score || 0
  const healthGrade = overview?.health_grade || 'N/A'
  const heatStats = overview?.heat_stats || { hot: 0, warm: 0, cold: 0, total: 0 }

  const heatPieData = [
    { name: '热数据', value: heatStats.hot || 0 },
    { name: '温数据', value: heatStats.warm || 0 },
    { name: '冷数据', value: heatStats.cold || 0 },
  ].filter(d => d.value > 0)

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>系统总览</h2>
        <Button type="primary" icon={<ReloadOutlined />} onClick={handleCollect}>
          立即采集
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {stats.map((stat, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <Card className={stat.className} bordered={false}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ color: 'rgba(255,255,255,0.8)', marginBottom: 8 }}>{stat.title}</p>
                  <p style={{ fontSize: 28, fontWeight: 'bold', marginBottom: 0 }}>{stat.value}</p>
                </div>
                {stat.icon}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card title={<span><HeartOutlined /> 健康评分</span>}>
            <div style={{ textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={Math.round(healthScore)}
                strokeColor={gradeColors[healthGrade] || '#1890ff'}
                format={() => (
                  <div>
                    <div style={{ fontSize: 32, fontWeight: 'bold', color: gradeColors[healthGrade] || '#1890ff' }}>
                      {healthGrade}
                    </div>
                    <div style={{ fontSize: 12, color: '#999' }}>{Math.round(healthScore)}分</div>
                  </div>
                )}
                size={150}
              />
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title={<span><FireOutlined /> 数据热度分布</span>}>
            {heatPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={heatPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, value }) => `${name}:${value}`}
                  >
                    {heatPieData.map((_, index) => (
                      <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: 30, color: '#999' }}>
                <InboxOutlined style={{ fontSize: 40 }} />
                <p>暂无热度数据</p>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 8 }}>
              <Tag color="red"><FireOutlined /> 热 {heatStats.hot || 0}</Tag>
              <Tag color="orange">温 {heatStats.warm || 0}</Tag>
              <Tag color="blue"><InboxOutlined /> 冷 {heatStats.cold || 0}</Tag>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title="快速摘要">
            <div style={{ fontSize: 14, lineHeight: '2.2' }}>
              <div>📊 节点总数：<strong>{overview?.total_nodes || 0}</strong></div>
              <div>💾 总数据量：<strong>{formatBytes(overview?.total_size || 0)}</strong></div>
              <div>🌲 最大深度：<strong>{overview?.max_depth || 0}</strong></div>
              <div>⚠️ 预警数量：<strong style={{ color: (overview?.alert_count || 0) > 0 ? '#f5222d' : '#52c41a' }}>{overview?.alert_count || 0}</strong></div>
              <div>❤️ 健康等级：<strong style={{ color: gradeColors[healthGrade] || '#999' }}>{healthGrade}</strong></div>
              <div>🔥 冷数据：<strong style={{ color: '#1890ff' }}>{heatStats.cold || 0}</strong> 个</div>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="节点数量趋势（24小时）">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={nodeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#1890ff" fill="#1890ff" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="数据量趋势（24小时）">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={sizeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                <YAxis tickFormatter={(value) => formatBytes(value)} />
                <Tooltip formatter={(value: number) => formatBytes(value)} />
                <Line type="monotone" dataKey="value" stroke="#52c41a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
