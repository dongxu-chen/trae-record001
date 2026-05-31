import { useEffect, useState } from 'react'
import { Card, Table, Tag, Spin, Badge } from 'antd'
import { WarningOutlined, ExclamationCircleOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { getAlerts, type Alert } from '../services/api'

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const Alerts = () => {
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState<Alert[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getAlerts()
      setAlerts(data || [])
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ExclamationCircleOutlined style={{ color: '#f5222d', fontSize: 16 }} />
      case 'warning':
        return <WarningOutlined style={{ color: '#faad14', fontSize: 16 }} />
      case 'info':
        return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 16 }} />
      default:
        return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 16 }} />
    }
  }

  const getSeverityTag = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'red',
      warning: 'orange',
      info: 'blue',
    }
    const labels: Record<string, string> = {
      critical: '严重',
      warning: '警告',
      info: '信息',
    }
    return <Tag color={colors[severity]}>{labels[severity] || severity}</Tag>
  }

  const getTypeTag = (type: string) => {
    const colors: Record<string, string> = {
      large_data: 'purple',
      many_children: 'cyan',
      deep_path: 'green',
    }
    const labels: Record<string, string> = {
      large_data: '数据过大',
      many_children: '子节点过多',
      deep_path: '路径过深',
    }
    return <Tag color={colors[type]}>{labels[type] || type}</Tag>
  }

  const formatValue = (type: string, value: number) => {
    if (type === 'large_data') {
      return formatBytes(value)
    }
    return value
  }

  const columns = [
    {
      title: '级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (severity: string) => (
        <div style={{ textAlign: 'center' }}>
          {getSeverityIcon(severity)}
          <div style={{ marginTop: 4 }}>{getSeverityTag(severity)}</div>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => getTypeTag(type),
    },
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
      title: '消息',
      dataIndex: 'message',
      key: 'message',
    },
    {
      title: '当前值',
      dataIndex: 'value',
      key: 'value',
      render: (value: number, record: Alert) => formatValue(record.type, value),
    },
    {
      title: '阈值',
      dataIndex: 'threshold',
      key: 'threshold',
      render: (value: number, record: Alert) => formatValue(record.type, value),
    },
  ]

  const alertCounts = {
    critical: alerts.filter(a => a.severity === 'critical').length,
    warning: alerts.filter(a => a.severity === 'warning').length,
    info: alerts.filter(a => a.severity === 'info').length,
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
      <h2 style={{ marginBottom: 24 }}>预警中心</h2>

      <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
        <Badge count={alertCounts.critical} size="small" showZero>
          <Card style={{ width: 150, textAlign: 'center', background: '#fff1f0', borderColor: '#ffa39e' }}>
            <div style={{ color: '#f5222d', fontSize: 24, fontWeight: 'bold' }}>{alertCounts.critical}</div>
            <div style={{ color: '#f5222d' }}>严重</div>
          </Card>
        </Badge>
        <Badge count={alertCounts.warning} size="small" showZero>
          <Card style={{ width: 150, textAlign: 'center', background: '#fffbe6', borderColor: '#ffe58f' }}>
            <div style={{ color: '#faad14', fontSize: 24, fontWeight: 'bold' }}>{alertCounts.warning}</div>
            <div style={{ color: '#faad14' }}>警告</div>
          </Card>
        </Badge>
        <Badge count={alertCounts.info} size="small" showZero>
          <Card style={{ width: 150, textAlign: 'center', background: '#e6f7ff', borderColor: '#91d5ff' }}>
            <div style={{ color: '#1890ff', fontSize: 24, fontWeight: 'bold' }}>{alertCounts.info}</div>
            <div style={{ color: '#1890ff' }}>信息</div>
          </Card>
        </Badge>
      </div>

      <Card title={`预警列表 (共 ${alerts.length} 条)`}>
        {alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#52c41a' }}>
            <InfoCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <p>当前没有预警，系统运行正常</p>
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={alerts}
            rowKey={(record) => `${record.path}-${record.type}`}
            pagination={{ pageSize: 10 }}
            scroll={{ x: 900 }}
          />
        )}
      </Card>
    </div>
  )
}

export default Alerts
