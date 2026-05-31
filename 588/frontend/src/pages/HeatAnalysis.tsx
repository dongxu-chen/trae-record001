import { useEffect, useState } from 'react'
import { Card, Row, Col, Table, Tag, Spin, Statistic, Tabs, Typography, Alert } from 'antd'
import { FireOutlined, InboxOutlined, CloudUploadOutlined } from '@ant-design/icons'
import { getColdNodes, getHotNodes, getHeatStats, type MigrationSuggestion, type HeatRecord } from '../services/api'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const { Text } = Typography

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const HEAT_COLORS: Record<string, string> = {
  hot: '#f5222d',
  warm: '#faad14',
  cold: '#1890ff',
}

const PIE_COLORS = ['#f5222d', '#faad14', '#1890ff']

const HeatAnalysis = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<{ hot: number; warm: number; cold: number; total: number }>({ hot: 0, warm: 0, cold: 0, total: 0 })
  const [coldNodes, setColdNodes] = useState<MigrationSuggestion[]>([])
  const [hotNodes, setHotNodes] = useState<HeatRecord[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, coldData, hotData] = await Promise.all([
        getHeatStats(),
        getColdNodes(),
        getHotNodes(20),
      ])
      setStats(statsData || { hot: 0, warm: 0, cold: 0, total: 0 })
      setColdNodes(coldData || [])
      setHotNodes(hotData || [])
    } catch (error) {
      console.error('Failed to load heat data:', error)
    } finally {
      setLoading(false)
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

  const pieData = [
    { name: '热数据', value: stats.hot, color: PIE_COLORS[0] },
    { name: '温数据', value: stats.warm, color: PIE_COLORS[1] },
    { name: '冷数据', value: stats.cold, color: PIE_COLORS[2] },
  ]

  const coldColumns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      width: 250,
      render: (text: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{text}</code>,
    },
    {
      title: '数据量',
      dataIndex: 'data_size',
      key: 'data_size',
      render: (size: number) => formatBytes(size),
    },
    {
      title: '最后访问',
      dataIndex: 'last_access',
      key: 'last_access',
    },
    {
      title: '建议存储',
      dataIndex: 'target_store',
      key: 'target_store',
      render: (store: string) => <Tag color="purple">{store}</Tag>,
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
    },
  ]

  const hotColumns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      width: 250,
      render: (text: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{text}</code>,
    },
    {
      title: '热度',
      dataIndex: 'heat_level',
      key: 'heat_level',
      render: (level: string) => (
        <Tag color={HEAT_COLORS[level]} icon={level === 'hot' ? <FireOutlined /> : level === 'cold' ? <InboxOutlined /> : undefined}>
          {level === 'hot' ? '热' : level === 'warm' ? '温' : '冷'}
        </Tag>
      ),
    },
    {
      title: '读次数',
      dataIndex: 'read_count',
      key: 'read_count',
      sorter: (a: HeatRecord, b: HeatRecord) => a.read_count - b.read_count,
    },
    {
      title: '写次数',
      dataIndex: 'write_count',
      key: 'write_count',
      sorter: (a: HeatRecord, b: HeatRecord) => a.write_count - b.write_count,
    },
    {
      title: '最后访问',
      dataIndex: 'last_access',
      key: 'last_access',
    },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>
        <FireOutlined /> 节点热度分析
      </h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} md={16}>
          <Card>
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="热数据"
                  value={stats.hot}
                  valueStyle={{ color: '#f5222d' }}
                  prefix={<FireOutlined />}
                  suffix="个"
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="温数据"
                  value={stats.warm}
                  valueStyle={{ color: '#faad14' }}
                  suffix="个"
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="冷数据"
                  value={stats.cold}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<InboxOutlined />}
                  suffix="个"
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {coldNodes.length > 0 && (
        <Alert
          message={`发现 ${coldNodes.length} 个冷数据节点，建议迁移至外部存储以释放ZooKeeper资源`}
          type="warning"
          showIcon
          icon={<CloudUploadOutlined />}
          style={{ marginBottom: 24 }}
        />
      )}

      <Card>
        <Tabs
          items={[
            {
              key: 'cold',
              label: `冷数据迁移建议 (${coldNodes.length})`,
              children: (
                <Table
                  columns={coldColumns}
                  dataSource={coldNodes}
                  rowKey="path"
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 900 }}
                />
              ),
            },
            {
              key: 'hot',
              label: `热点节点 (${hotNodes.length})`,
              children: (
                <Table
                  columns={hotColumns}
                  dataSource={hotNodes}
                  rowKey="path"
                  pagination={{ pageSize: 10 }}
                  scroll={{ x: 800 }}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default HeatAnalysis
