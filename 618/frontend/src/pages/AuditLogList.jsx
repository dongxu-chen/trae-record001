import React, { useState, useEffect } from 'react'
import {
  Table,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Popconfirm,
  message,
  Card,
  Tooltip,
} from 'antd'
import {
  EyeOutlined,
  RollbackOutlined,
  SearchOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { auditApi, namespaceApi } from '../services/api'

const { Option } = Select

function AuditLogList() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [namespaces, setNamespaces] = useState([])
  const [filters, setFilters] = useState({
    namespace_id: '',
    group: '',
    data_id: '',
    page: 1,
    page_size: 20,
  })

  useEffect(() => {
    loadNamespaces()
  }, [])

  useEffect(() => {
    loadLogs()
  }, [filters])

  const loadNamespaces = async () => {
    try {
      const data = await namespaceApi.getNamespaces()
      setNamespaces(data || [])
    } catch (error) {
      console.error('Failed to load namespaces:', error)
    }
  }

  const loadLogs = async () => {
    setLoading(true)
    try {
      const data = await auditApi.getLogs(filters)
      setLogs(data?.list || [])
      setTotal(data?.total || 0)
    } catch (error) {
      message.error('加载审计日志失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleRollback = async (id) => {
    try {
      await auditApi.rollback(id, 'admin')
      message.success('回滚成功')
      loadLogs()
    } catch (error) {
      message.error('回滚失败: ' + error.message)
    }
  }

  const handleQuickRollback = async (record) => {
    try {
      await auditApi.quickRollback({
        namespace_id: record.namespace_id,
        group: record.group,
        data_id: record.data_id,
        operator: 'admin',
      })
      message.success('一键回滚成功')
      loadLogs()
    } catch (error) {
      message.error('一键回滚失败: ' + error.message)
    }
  }

  const getActionColor = (action) => {
    switch (action) {
      case 'CREATE':
        return 'success'
      case 'UPDATE':
        return 'processing'
      case 'DELETE':
        return 'error'
      case 'ROLLBACK':
        return 'warning'
      default:
        return 'default'
    }
  }

  const columns = [
    {
      title: '命名空间',
      dataIndex: 'namespace_id',
      key: 'namespace_id',
      width: 120,
      ellipsis: true,
    },
    {
      title: '分组',
      dataIndex: 'group',
      key: 'group',
      width: 120,
      ellipsis: true,
    },
    {
      title: 'DataID',
      dataIndex: 'data_id',
      key: 'data_id',
      width: 200,
      ellipsis: true,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => (
        <Tag color={getActionColor(action)}>{action}</Tag>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
      width: 100,
    },
    {
      title: '合规检查',
      dataIndex: 'compliance_pass',
      key: 'compliance_pass',
      width: 100,
      render: (pass) => {
        if (pass === null || pass === undefined) {
          return <Tag color="default">未检查</Tag>
        }
        return pass ? (
          <Tag color="success" icon="✓">通过</Tag>
        ) : (
          <Tag color="error" icon="✗">不通过</Tag>
        )
      },
    },
    {
      title: '自动回滚',
      dataIndex: 'is_auto_rollback',
      key: 'is_auto_rollback',
      width: 90,
      render: (v, record) => v ? (
        <Tooltip title={record.rollback_reason}>
          <Tag color="orange" icon={<ThunderboltOutlined />}>自动</Tag>
        </Tooltip>
      ) : null,
    },
    {
      title: '变更时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/logs/${record.id}`)}
          >
            详情
          </Button>
          {record.action !== 'ROLLBACK' && (
            <Popconfirm
              title="确认回滚"
              description="确定要将配置回滚到此版本吗？"
              onConfirm={() => handleRollback(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" danger icon={<RollbackOutlined />}>
                回滚
              </Button>
            </Popconfirm>
          )}
          {record.action !== 'ROLLBACK' && !record.is_auto_rollback && (
            <Popconfirm
              title="一键回滚到上一个版本"
              description="将此配置快速回滚到最近的上一个版本，是否继续？"
              onConfirm={() => handleQuickRollback(record)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" icon={<WarningOutlined />} style={{ color: '#fa8c16' }}>
                一键回滚
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card title="变更历史" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="选择命名空间"
            style={{ width: 200 }}
            allowClear
            value={filters.namespace_id || undefined}
            onChange={(v) => setFilters({ ...filters, namespace_id: v || '', page: 1 })}
          >
            {namespaces.map((ns) => (
              <Option key={ns.id} value={ns.id}>
                {ns.name || ns.id}
              </Option>
            ))}
          </Select>
          <Input
            placeholder="分组"
            style={{ width: 150 }}
            value={filters.group}
            onChange={(e) => setFilters({ ...filters, group: e.target.value, page: 1 })}
            prefix={<SearchOutlined />}
          />
          <Input
            placeholder="DataID"
            style={{ width: 200 }}
            value={filters.data_id}
            onChange={(e) => setFilters({ ...filters, data_id: e.target.value, page: 1 })}
            prefix={<SearchOutlined />}
          />
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={loadLogs}
          >
            刷新
          </Button>
        </Space>

        <Table
          className="audit-log-table"
          columns={columns}
          dataSource={logs}
          rowKey="id"
          loading={loading}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            total: total,
            onChange: (page, pageSize) =>
              setFilters({ ...filters, page, page_size: pageSize }),
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 1000 }}
        />
      </Card>
    </div>
  )
}

export default AuditLogList
