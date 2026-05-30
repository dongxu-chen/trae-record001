import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message, Input, Select, Card } from 'antd'
import { PlusOutlined, ReloadOutlined, DeleteOutlined, RollbackOutlined, EditOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { ruleApi } from '../services/api'

const { Search } = Input

const RULE_TYPE_MAP = {
  DROOLS: { color: 'blue', label: 'Drools' },
  GROOVY: { color: 'green', label: 'Groovy' },
  HYBRID: { color: 'purple', label: '混合' },
}

export default function RuleList() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      setLoading(true)
      const data = await ruleApi.getAll()
      setRules(data || [])
    } catch (e) {
      message.error('加载规则失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await ruleApi.delete(id)
      message.success('规则已删除')
      loadRules()
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleHotReload = async () => {
    try {
      await ruleApi.hotReload()
      message.success('规则热更新成功')
    } catch (e) {
      message.error('热更新失败')
    }
  }

  const handleRollback = async (record) => {
    try {
      const versions = await ruleApi.getVersions(record.id)
      if (versions && versions.length > 1) {
        const prevVersion = versions[1].version
        await ruleApi.rollback(record.id, prevVersion)
        message.success(`已回滚至版本 ${prevVersion}`)
        loadRules()
      } else {
        message.warning('没有可回滚的版本')
      }
    } catch (e) {
      message.error('回滚失败')
    }
  }

  const filteredRules = rules.filter(r =>
    !searchText ||
    r.ruleCode?.toLowerCase().includes(searchText.toLowerCase()) ||
    r.ruleName?.toLowerCase().includes(searchText.toLowerCase())
  )

  const columns = [
    {
      title: '规则编码',
      dataIndex: 'ruleCode',
      key: 'ruleCode',
      width: 160,
      render: (text) => <span style={{ fontFamily: 'monospace', color: '#1677ff' }}>{text}</span>,
    },
    {
      title: '规则名称',
      dataIndex: 'ruleName',
      key: 'ruleName',
      width: 180,
    },
    {
      title: '类型',
      dataIndex: 'ruleType',
      key: 'ruleType',
      width: 100,
      render: (type) => {
        const config = RULE_TYPE_MAP[type] || { color: 'default', label: type }
        return <Tag color={config.color}>{config.label}</Tag>
      },
    },
    {
      title: '场景',
      dataIndex: 'sceneCode',
      key: 'sceneCode',
      width: 120,
      render: (text) => text ? <Tag>{text}</Tag> : '-',
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
      width: 170,
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => navigate(`/rules/edit/${record.id}`)}
          >
            编辑
          </Button>
          <Popconfirm title="确定回滚到上一版本？" onConfirm={() => handleRollback(record)}>
            <Button type="link" size="small" icon={<RollbackOutlined />}>
              回滚
            </Button>
          </Popconfirm>
          <Popconfirm title="确定删除此规则？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="规则管理"
      extra={
        <Space>
          <Search
            placeholder="搜索规则"
            allowClear
            style={{ width: 200 }}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Button icon={<ReloadOutlined />} onClick={handleHotReload}>
            热更新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/rules/create')}>
            新建规则
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={filteredRules}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 条` }}
      />
    </Card>
  )
}
