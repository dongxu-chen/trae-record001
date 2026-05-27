import React, { useState, useEffect } from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Progress, message } from 'antd'
import {
  GlobalOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const Dashboard = () => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await api.getDashboard()
      setData(res.data)
    } catch (error) {
      message.error('获取仪表盘数据失败')
    } finally {
      setLoading(false)
    }
  }

  const alertColumns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '告警级别',
      dataIndex: 'level',
      key: 'level',
      render: (level) => {
        const levelMap = {
          critical: { color: 'red', text: '严重' },
          warning: { color: 'orange', text: '警告' },
          error: { color: 'red', text: '错误' },
          info: { color: 'blue', text: '信息' },
        }
        const config = levelMap[level] || { color: 'default', text: level }
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ]

  if (!data) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card" loading={loading}>
            <Statistic
              title="域名总数"
              value={data.total_domains}
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card" loading={loading}>
            <Statistic
              title="正常证书"
              value={data.valid_certs}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card" loading={loading}>
            <Statistic
              title="即将过期"
              value={data.warning_certs + data.critical_certs}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card" loading={loading}>
            <Statistic
              title="已过期"
              value={data.expired_certs}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={8}>
          <Card title="证书状态分布" loading={loading}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>正常</span>
                  <span>{data.valid_certs}</span>
                </div>
                <Progress
                  percent={data.total_domains > 0 ? (data.valid_certs / data.total_domains * 100 : 0}
                  strokeColor="#52c41a"
                  showInfo={false}
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>即将过期</span>
                  <span>{data.warning_certs + data.critical_certs}</span>
                </div>
                <Progress
                  percent={data.total_domains > 0 ? ((data.warning_certs + data.critical_certs) / data.total_domains * 100) : 0}
                  strokeColor="#faad14"
                  showInfo={false}
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>已过期</span>
                  <span>{data.expired_certs}</span>
                </div>
                <Progress
                  percent={data.total_domains > 0 ? (data.expired_certs / data.total_domains * 100) : 0}
                  strokeColor="#ff4d4f"
                  showInfo={false}
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>检查失败</span>
                  <span>{data.error_certs}</span>
                </div>
                <Progress
                  percent={data.total_domains > 0 ? (data.error_certs / data.total_domains * 100) : 0}
                  strokeColor="#8c8c8c"
                  showInfo={false}
                />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={16}>
          <Card title="最近告警" loading={loading}>
            <Table
              columns={alertColumns}
              dataSource={data.recent_alerts || []}
              pagination={false}
              size="small"
              locale={{ emptyText: '暂无告警记录' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
