import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Table, Tag, Select, Spin, Space } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  WarningOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
} from '@ant-design/icons'
import { dashboardApi } from '../services/api'

const { Option } = Select

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [days, setDays] = useState(30)

  useEffect(() => {
    loadStats()
  }, [days])

  const loadStats = async () => {
    setLoading(true)
    try {
      const data = await dashboardApi.getStats(days)
      setStats(data)
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const getRiskLevelColor = (level) => {
    switch (level) {
      case 'CRITICAL': return '#cf1322'
      case 'HIGH': return '#fa541c'
      case 'MEDIUM': return '#faad14'
      case 'LOW': return '#52c41a'
      default: return '#1890ff'
    }
  }

  const actionColumns = [
    { title: '操作类型', dataIndex: 'action', key: 'action', render: (a) => <Tag color={a === 'CREATE' ? 'green' : a === 'DELETE' ? 'red' : a === 'ROLLBACK' ? 'orange' : 'blue'}>{a}</Tag> },
    { title: '次数', dataIndex: 'count', key: 'count', render: (c) => <span style={{ fontWeight: 'bold' }}>{c}</span> },
  ]

  const nsColumns = [
    { title: '命名空间', dataIndex: 'namespace_id', key: 'namespace_id' },
    { title: '变更次数', dataIndex: 'count', key: 'count', render: (c) => <Statistic value={c} valueStyle={{ fontSize: '14px' }} /> },
  ]

  const recentColumns = [
    { title: '命名空间', dataIndex: 'namespace_id', key: 'namespace_id', width: 120, ellipsis: true },
    { title: 'DataID', dataIndex: 'data_id', key: 'data_id', width: 200, ellipsis: true },
    { title: '操作', dataIndex: 'action', key: 'action', width: 90, render: (a) => <Tag color={a === 'ROLLBACK' ? 'orange' : 'blue'}>{a}</Tag> },
    { title: '操作人', dataIndex: 'operator', key: 'operator', width: 90 },
    { title: '合规', dataIndex: 'compliance_pass', key: 'compliance_pass', width: 80, render: (p) => p ? <Tag color="green">通过</Tag> : <Tag color="red">不通过</Tag> },
    { title: '自动回滚', dataIndex: 'is_auto_rollback', key: 'is_auto_rollback', width: 90, render: (r) => r ? <Tag color="orange">是</Tag> : <Tag>否</Tag> },
  ]

  const renderBarChart = (data, maxValue) => {
    if (!data || data.length === 0) return <div style={{ textAlign: 'center', color: '#999', padding: 20 }}>暂无数据</div>
    const max = maxValue || Math.max(...data.map(d => d.count), 1)
    return (
      <div style={{ padding: '8px 0' }}>
        {data.map((item, index) => {
          const width = Math.max((item.count / max) * 100, 2)
          return (
            <div key={index} style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ width: 120, fontSize: 12, color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.date || item.namespace_id || item.action}
              </div>
              <div style={{ flex: 1, marginLeft: 8 }}>
                <div style={{
                  height: 20,
                  width: `${width}%`,
                  background: 'linear-gradient(90deg, #1890ff, #36cfc9)',
                  borderRadius: 4,
                  display: 'flex',
                  alignItems: 'center',
                  paddingLeft: 8,
                  color: 'white',
                  fontSize: 11,
                  fontWeight: 'bold',
                  minWidth: 30,
                }}>
                  {item.count}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '100px 0' }}><Spin size="large" /></div>
  }

  if (!stats) {
    return <Card>加载失败</Card>
  }

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Space style={{ marginBottom: 16 }}>
              <DashboardOutlined style={{ fontSize: 20 }} />
              <span style={{ fontSize: 18, fontWeight: 'bold' }}>审计大盘</span>
              <Select value={days} onChange={setDays} style={{ width: 120, marginLeft: 16 }}>
                <Option value={7}>最近7天</Option>
                <Option value={30}>最近30天</Option>
                <Option value={90}>最近90天</Option>
              </Select>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总变更次数"
              value={stats.total_changes}
              prefix={<ArrowUpOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="合规不通过"
              value={stats.compliance_fail_count}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="自动回滚次数"
              value={stats.auto_rollback_count}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="合规通过率"
              value={stats.total_changes > 0 ? (((stats.total_changes - stats.compliance_fail_count) / stats.total_changes) * 100).toFixed(1) : '100.0'}
              suffix="%"
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="操作类型分布" size="small">
            <Table
              columns={actionColumns}
              dataSource={stats.action_stats || []}
              rowKey="action"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="每日变更趋势" size="small">
            {renderBarChart(stats.daily_stats)}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="命名空间变更分布" size="small">
            {renderBarChart(stats.namespace_stats)}
          </Card>
        </Col>
      </Row>

      <Card title="最近变更记录" style={{ marginTop: 16 }} size="small">
        <Table
          columns={recentColumns}
          dataSource={stats.recent_changes || []}
          rowKey="id"
          pagination={false}
          size="small"
          scroll={{ x: 700 }}
        />
      </Card>
    </div>
  )
}

export default Dashboard
