import { useEffect, useState } from 'react'
import { Card, Table, Tag, Spin, Button, Switch, Modal, Form, InputNumber, Input, message, Typography, List, Badge } from 'antd'
import { DeleteOutlined, ClockCircleOutlined, ClearOutlined, PlusOutlined } from '@ant-design/icons'
import {
  getTTLRecords,
  getTTLCleanHistory,
  registerTTL,
  triggerClean,
  setTTLEnabled,
  type TTLRecord,
  type CleanResult,
} from '../services/api'

const { Text } = Typography

const TTLCleaner = () => {
  const [loading, setLoading] = useState(true)
  const [records, setRecords] = useState<TTLRecord[]>([])
  const [history, setHistory] = useState<CleanResult[]>([])
  const [enabled, setEnabledState] = useState(true)
  const [registerModalVisible, setRegisterModalVisible] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    try {
      setLoading(true)
      const [recordsData, historyData] = await Promise.all([
        getTTLRecords(),
        getTTLCleanHistory(),
      ])
      setRecords(recordsData || [])
      setHistory(historyData || [])
    } catch (error) {
      console.error('Failed to load TTL data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRegisterTTL = async (values: { path: string; ttl: number }) => {
    try {
      await registerTTL(values.path, values.ttl)
      message.success(`已注册TTL: ${values.path}`)
      setRegisterModalVisible(false)
      form.resetFields()
      loadData()
    } catch (error) {
      message.error('注册失败')
    }
  }

  const handleTriggerClean = async () => {
    try {
      const result = await triggerClean()
      message.success(`清理完成: 扫描 ${result.scanned} 个节点，删除 ${result.deleted_count} 个`)
      loadData()
    } catch (error) {
      message.error('清理失败')
    }
  }

  const handleToggleEnabled = async (checked: boolean) => {
    try {
      await setTTLEnabled(checked)
      setEnabledState(checked)
      message.success(checked ? '自动清理已启用' : '自动清理已禁用')
    } catch (error) {
      message.error('操作失败')
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const now = new Date()

  const ttlColumns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      width: 300,
      render: (text: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{text}</code>,
    },
    {
      title: 'TTL(秒)',
      dataIndex: 'ttl',
      key: 'ttl',
      render: (ttl: number) => {
        if (ttl >= 86400) return `${(ttl / 86400).toFixed(1)}天`
        if (ttl >= 3600) return `${(ttl / 3600).toFixed(1)}小时`
        return `${ttl}秒`
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => new Date(t).toLocaleString(),
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (t: string) => {
        const expires = new Date(t)
        const isExpired = expires < now
        return (
          <span>
            {expires.toLocaleString()}
            {isExpired && <Tag color="red" style={{ marginLeft: 8 }}>已过期</Tag>}
          </span>
        )
      },
    },
    {
      title: '状态',
      key: 'status',
      render: (_: any, record: TTLRecord) => {
        const expires = new Date(record.expires_at)
        const remaining = expires.getTime() - now.getTime()
        if (remaining <= 0) return <Tag color="red">已过期</Tag>
        if (remaining < 3600000) return <Tag color="orange">即将过期</Tag>
        return <Tag color="green">正常</Tag>
      },
    },
  ]

  const totalDeleted = history.reduce((sum: number, r: CleanResult) => sum + r.deleted_count, 0)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>
          <ClockCircleOutlined /> TTL自动清理
        </h2>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <span>自动清理：</span>
          <Switch checked={enabled} onChange={handleToggleEnabled} />
          <Button icon={<PlusOutlined />} onClick={() => setRegisterModalVisible(true)}>
            注册TTL
          </Button>
          <Button danger icon={<ClearOutlined />} onClick={handleTriggerClean}>
            立即清理
          </Button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <Card style={{ flex: 1, textAlign: 'center' }}>
          <Badge count={records.length} showZero overflowCount={999}>
            <div>
              <Text type="secondary">TTL记录数</Text>
              <div style={{ fontSize: 28, fontWeight: 'bold' }}>{records.length}</div>
            </div>
          </Badge>
        </Card>
        <Card style={{ flex: 1, textAlign: 'center' }}>
          <div>
            <Text type="secondary">累计清理次数</Text>
            <div style={{ fontSize: 28, fontWeight: 'bold' }}>{history.length}</div>
          </div>
        </Card>
        <Card style={{ flex: 1, textAlign: 'center' }}>
          <div>
            <Text type="secondary">累计删除节点</Text>
            <div style={{ fontSize: 28, fontWeight: 'bold', color: '#f5222d' }}>{totalDeleted}</div>
          </div>
        </Card>
      </div>

      <Card title="TTL注册记录" style={{ marginBottom: 24 }}>
        {records.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
            <ClockCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <p>暂无TTL注册记录</p>
            <p>点击"注册TTL"按钮添加节点TTL</p>
          </div>
        ) : (
          <Table
            columns={ttlColumns}
            dataSource={records}
            rowKey="path"
            pagination={{ pageSize: 10 }}
          />
        )}
      </Card>

      <Card title="清理历史">
        <List
          dataSource={history.slice().reverse().slice(0, 20)}
          renderItem={(item: CleanResult) => (
            <List.Item>
              <List.Item.Meta
                avatar={<DeleteOutlined style={{ fontSize: 20, color: item.deleted_count > 0 ? '#f5222d' : '#52c41a' }} />}
                title={
                  <span>
                    {new Date(item.timestamp).toLocaleString()}
                    <Tag color={item.deleted_count > 0 ? 'red' : 'green'} style={{ marginLeft: 8 }}>
                      删除 {item.deleted_count} 个
                    </Tag>
                    <Tag>扫描 {item.scanned} 个</Tag>
                  </span>
                }
                description={
                  item.deleted.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary">已删除：</Text>
                      {item.deleted.slice(0, 5).map((p: string, i: number) => (
                        <Tag key={i} style={{ marginBottom: 2 }}><code>{p}</code></Tag>
                      ))}
                      {item.deleted.length > 5 && <Tag>等 {item.deleted.length - 5} 个</Tag>}
                    </div>
                  )
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <Modal
        title="注册TTL"
        open={registerModalVisible}
        onCancel={() => setRegisterModalVisible(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleRegisterTTL} layout="vertical">
          <Form.Item name="path" label="节点路径" rules={[{ required: true, message: '请输入节点路径' }]}>
            <Input placeholder="/config/cache" />
          </Form.Item>
          <Form.Item name="ttl" label="TTL（秒）" rules={[{ required: true, message: '请输入TTL' }]}>
            <InputNumber min={1} style={{ width: '100%' }} placeholder="86400" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              注册
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default TTLCleaner
