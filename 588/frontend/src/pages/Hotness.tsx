import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tabs,
  Tag,
  Row,
  Col,
  Statistic,
  Spin,
  Progress,
  List,
  Button,
  Space,
} from 'antd'
import {
  FireOutlined,
  SnowflakeOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ImportOutlined,
} from '@ant-design/icons'
import {
  getHotnessStats,
  getHotNodes,
  getColdNodes,
  getMigrationSuggestions,
  type NodeHotness,
  type HotnessStats,
  type MigrationSuggestion,
} from '../services/api'

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const Hotness = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<HotnessStats | null>(null)
  const [hotNodes, setHotNodes] = useState<NodeHotness[]>([])
  const [coldNodes, setColdNodes] = useState<NodeHotness[]>([])
  const [migrationSuggestions, setMigrationSuggestions] = useState<MigrationSuggestion[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, hotData, coldData, migrationData] = await Promise.all([
        getHotnessStats(),
        getHotNodes(20),
        getColdNodes(0),
        getMigrationSuggestions(),
      ])
      setStats(statsData)
      setHotNodes(hotData)
      setColdNodes(coldData)
      setMigrationSuggestions(migrationData)
    } catch (error) {
      console.error('Failed to load hotness data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const hotColumns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (text: string) => (
        <code style={{ background: '#fff1f0', padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>
          {text}
        </code>
      ),
    },
    {
      title: '热度评分',
      dataIndex: 'hotness_score',
      key: 'hotness_score',
      render: (score: number) => (
        <Progress
          percent={Math.min(100, score)}
          size="small"
          strokeColor="#ff7a45"
          format={(percent) => `${percent?.toFixed(1)}`}
        />
      ),
    },
    {
      title: '读次数',
      dataIndex: 'read_count',
      key: 'read_count',
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '写次数',
      dataIndex: 'write_count',
      key: 'write_count',
      render: (count: number) => <Tag color="red">{count}</Tag>,
    },
    {
      title: '总访问',
      dataIndex: 'total_access',
      key: 'total_access',
      render: (count: number) => <Tag color="purple">{count}</Tag>,
    },
  ]

  const coldColumns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (text: string) => (
        <code style={{ background: '#e6f7ff', padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>
          {text}
        </code>
      ),
    },
    {
      title: '未访问天数',
      dataIndex: 'days_since_access',
      key: 'days_since_access',
      render: (days: number) => (
        <Tag color={days > 30 ? 'red' : days > 7 ? 'orange' : 'blue'}>
          {days.toFixed(1)} 天
        </Tag>
      ),
    },
    {
      title: '总访问',
      dataIndex: 'total_access',
      key: 'total_access',
      render: (count: number) => count,
    },
    {
      title: '状态',
      dataIndex: 'cold_data',
      key: 'cold_data',
      render: (cold: boolean) =>
        cold ? (
          <Tag icon={<SnowflakeOutlined />} color="cyan">
            冷数据
          </Tag>
        ) : (
          <Tag icon={<FireOutlined />} color="orange">
            热数据
          </Tag>
        ),
    },
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const tabItems = [
    {
      key: 'hot',
      label: (
        <span>
          <FireOutlined style={{ color: '#ff7a45' }} /> 热门节点 Top 20
        </span>
      ),
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
    {
      key: 'cold',
      label: (
        <span>
          <SnowflakeOutlined style={{ color: '#1890ff' }} /> 冷数据节点
        </span>
      ),
      children: (
        <Table
          columns={coldColumns}
          dataSource={coldNodes}
          rowKey="path"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      ),
    },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>节点访问热度分析</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="已追踪节点数"
              value={stats?.total_tracked_nodes || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="热门节点数"
              value={stats?.hot_node_count || 0}
              valueStyle={{ color: '#ff7a45' }}
              prefix={<FireOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="冷数据节点数"
              value={stats?.cold_node_count || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SnowflakeOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {migrationSuggestions.length > 0 && (
        <Card
          title={
            <span>
              <DatabaseOutlined style={{ marginRight: 8 }} />
              冷数据迁移建议
            </span>
          }
          style={{ marginBottom: 24 }}
        >
          <List
            dataSource={migrationSuggestions}
            renderItem={(item) => (
              <List.Item
                actions={[
                  <Button type="primary" size="small" icon={<ImportOutlined />}>
                    查看详情
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
                        {item.prefix}
                      </code>
                      <Tag color="orange">{item.cold_node_count} 个冷节点</Tag>
                      <Tag color="blue">{formatBytes(item.total_data_size)}</Tag>
                      <Tag>平均 {item.avg_cold_days.toFixed(1)} 天未访问</Tag>
                    </Space>
                  }
                  description={
                    <div>
                      <p style={{ marginBottom: 8 }}>
                        <strong>建议措施：</strong>
                        {item.suggested_action}
                      </p>
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        {item.recommendations.slice(0, 2).map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      <Card>
        <Tabs defaultActiveKey="hot" items={tabItems} />
      </Card>
    </div>
  )
}

export default Hotness
