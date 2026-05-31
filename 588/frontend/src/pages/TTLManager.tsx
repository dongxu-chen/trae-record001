import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  Tag,
  Space,
  message,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Spin,
} from 'antd'
import {
  ClockCircleOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  getTTLStats,
  getTTLNodes,
  setTTL,
  removeTTL,
  triggerCleanup,
  type TTLInfo,
  type TTLStats,
} from '../services/api'

const formatTTL = (seconds: number) => {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

const TTLManager = () => {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<TTLStats | null>(null)
  const [nodes, setNodes] = useState<TTLInfo[]>([])
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    try {
      setLoading(true)
      const [statsData, nodesData] = await Promise.all([getTTLStats(), getTTLNodes()])
      setStats(statsData)
      setNodes(nodesData)
    } catch (error) {
      console.error('Failed to load TTL data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleSetTTL = async (values: any) => {
    try {
      await setTTL(values.path, values.ttl_seconds, values.auto_delete)
      message.success('TTL设置成功')
      setModalVisible(false)
      form.resetFields()
      loadData()
    } catch (error) {
      message.error('TTL设置失败')
    }
  }

  const handleRemoveTTL = async (path: string) => {
    try {
      await removeTTL(path)
      message.success('TTL已移除')
      loadData()
    } catch (error) {
      message.error('移除TTL失败')
    }
  }

  const handleCleanup = async () => {
    try {
      const result = await triggerCleanup()
      message.success(`清理完成，删除了 ${result.deleted} 个过期节点`)
      loadData()
    } catch (error) {
      message.error('清理失败')
    }
  }

  const isExpired = (expireAt: string) => {
    return new Date(expireAt) < new Date()
  }

  const columns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      render: (text: string) => (
        <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>
          {text}
        </code>
      ),
    },
    {
      title: 'TTL时长',
      dataIndex: 'ttl_seconds',
      key: 'ttl_seconds',
      render: (seconds: number) => formatTTL(seconds),
    },
    {
      title: '过期时间',
      dataIndex: 'expire_at',
      key: 'expire_at',
      render: (expireAt: string) => {
        const expired = isExpired(expireAt)
        return (
          <Space>
            {expired ? (
              <Tag color="red">
                <WarningOutlined /> 已过期
              </Tag>
            ) : (
              <Tag color="green">
                <CheckCircleOutlined /> 有效
              </Tag>
            )}
            {new Date(expireAt).toLocaleString()}
          </Space>
        )
      },
    },
    {
      title: '自动删除',
      dataIndex: 'auto_delete',
      key: 'auto_delete',
      render: (auto: boolean) => (auto ? <Tag color="blue">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: TTLInfo) => (
        <Popconfirm
          title="确定要移除该节点的TTL吗？"
          onConfirm={() => handleRemoveTTL(record.path)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="link" danger size="small" icon={<DeleteOutlined />}>
            移除
          </Button>
        </Popconfirm>
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

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>TTL 自动清理管理</h2>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            设置TTL
          </Button>
          <Button
            danger
            icon={<PlayCircleOutlined />}
            onClick={handleCleanup}
          >
            立即清理过期节点
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="TTL节点总数"
              value={stats?.total_ttl_nodes || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="自动删除节点数"
              value={stats?.auto_delete_count || 0}
              valueStyle={{ color: '#1890ff' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="已过期节点数"
              value={stats?.expired_count || 0}
              valueStyle={{ color: '#f5222d' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="TTL节点列表">
        <Table
          columns={columns}
          dataSource={nodes}
          rowKey="path"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="设置节点TTL"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSetTTL}>
          <Form.Item
            name="path"
            label="节点路径"
            rules={[{ required: true, message: '请输入节点路径' }]}
          >
            <Input placeholder="/path/to/node" />
          </Form.Item>
          <Form.Item
            name="ttl_seconds"
            label="TTL时长（秒）"
            rules={[{ required: true, message: '请输入TTL时长' }]}
          >
            <InputNumber
              min={1}
              placeholder="86400 (1天)"
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item name="auto_delete" label="自动删除" valuePropName="checked">
            <Switch defaultChecked />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" style={{ width: '100%' }}>
              设置TTL
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TTLManager
