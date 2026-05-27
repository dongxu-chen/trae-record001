import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Statistic,
  Button,
  Space,
  Table,
  Tag,
  Progress,
  message,
} from 'antd'
import {
  DownloadOutlined,
  ReloadOutlined,
  GlobalOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const Report = () => {
  const [report, setReport] = useState(null)
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [reportRes, certsRes] = await Promise.all([
        api.getReport(),
        api.getCertRecords({ page: 1, page_size: 100 }),
      ])
      setReport(reportRes.data)
      setRecords(certsRes.data.records)
    } catch (error) {
      message.error('获取报告数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = () => {
    api.exportReport()
  }

  const getStatusColor = (status) => {
    const colors = {
      valid: 'green',
      warning: 'orange',
      critical: 'red',
      expired: 'default',
      error: 'red',
    }
    return colors[status] || 'default'
  }

  const getStatusText = (status) => {
    const texts = {
      valid: '正常',
      warning: '即将过期',
      critical: '严重',
      expired: '已过期',
      error: '检查失败',
    }
    return texts[status] || status
  }

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '剩余天数',
      dataIndex: 'days_left',
      key: 'days_left',
      render: (days, record) => (
        <span className={`status-${record.status}`}>{days} 天</span>
      ),
    },
    {
      title: '签发机构',
      dataIndex: 'issuer',
      key: 'issuer',
    },
    {
      title: '有效期至',
      dataIndex: 'not_after',
      key: 'not_after',
      render: (time) => dayjs(time).format('YYYY-MM-DD'),
    },
    {
      title: '加密算法',
      dataIndex: 'public_key_algo',
      key: 'public_key_algo',
    },
    {
      title: '签名算法',
      dataIndex: 'signature_algo',
      key: 'signature_algo',
    },
  ]

  if (!report) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col style={{ flex: 1 }}>
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
            >
              导出CSV报告
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchData}
            >
              刷新
            </Button>
          </Space>
        </Col>
        <Col>
          <Tag color="blue">
            最后扫描时间: {report.last_scan_time ? dayjs(report.last_scan_time).format('YYYY-MM-DD HH:mm:ss') : '暂无'}
          </Tag>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="域名总数"
              value={report.total_domains}
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="正常证书"
              value={report.valid_certs}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="即将过期"
              value={report.expiring_soon}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card className="stat-card">
            <Statistic
              title="已过期/失败"
              value={report.expired + report.failed_checks}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} md={12}>
          <Card title="证书状态分布">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#52c41a' }}>正常</span>
                  <span>{report.valid_certs} 个</span>
                </div>
                <Progress
                  percent={report.total_domains > 0 ? (report.valid_certs / report.total_domains * 100) : 0}
                  strokeColor="#52c41a"
                  size="large"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#faad14' }}>即将过期</span>
                  <span>{report.expiring_soon} 个</span>
                </div>
                <Progress
                  percent={report.total_domains > 0 ? (report.expiring_soon / report.total_domains * 100) : 0}
                  strokeColor="#faad14"
                  size="large"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#ff4d4f' }}>已过期</span>
                  <span>{report.expired} 个</span>
                </div>
                <Progress
                  percent={report.total_domains > 0 ? (report.expired / report.total_domains * 100) : 0}
                  strokeColor="#ff4d4f"
                  size="large"
                />
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#8c8c8c' }}>检查失败</span>
                  <span>{report.failed_checks} 个</span>
                </div>
                <Progress
                  percent={report.total_domains > 0 ? (report.failed_checks / report.total_domains * 100) : 0}
                  strokeColor="#8c8c8c"
                  size="large"
                />
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="加密算法统计">
            {(() => {
              const algoStats = {}
              records.forEach(r => {
                const algo = r.public_key_algo || '未知'
                algoStats[algo] = (algoStats[algo] || 0) + 1
              })
              return Object.entries(algoStats).map(([algo, count]) => (
                <div key={algo} style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span>{algo}</span>
                    <span>{count} 个</span>
                  </div>
                  <Progress
                    percent={records.length > 0 ? (count / records.length * 100) : 0}
                    size="small"
                  />
                </div>
              ))
            })()}
          </Card>
        </Col>
      </Row>

      <Card title="证书详情列表">
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>
    </div>
  )
}

export default Report
