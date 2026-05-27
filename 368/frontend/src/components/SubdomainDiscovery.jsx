import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Statistic,
  message,
  Popconfirm,
  Tooltip,
  Modal,
} from 'antd'
import {
  ReloadOutlined,
  PlayCircleOutlined,
  RocketOutlined,
  DeleteOutlined,
  GlobalOutlined,
  ShareAltOutlined,
  SafetyOutlined,
  DnsOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const SubdomainDiscovery = () => {
  const [subdomains, setSubdomains] = useState([])
  const [dnsRecords, setDnsRecords] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [parentDomain, setParentDomain] = useState('')
  const [activeTab, setActiveTab] = useState('subdomains')
  const [stats, setStats] = useState(null)
  const [scanModal, setScanModal] = useState(false)
  const [scanDomain, setScanDomain] = useState('')

  useEffect(() => {
    fetchData()
    fetchStats()
  }, [page, pageSize, parentDomain, activeTab])

  const fetchData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'subdomains') {
        const res = await api.getSubdomains({
          page,
          page_size: pageSize,
          parent_domain: parentDomain,
        })
        setSubdomains(res.data.records)
        setTotal(res.data.total)
      } else {
        const res = await api.getDNSRecords({
          page,
          page_size: pageSize,
          domain: parentDomain,
        })
        setDnsRecords(res.data.records)
        setTotal(res.data.total)
      }
    } catch (error) {
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await api.getDNSStats()
      setStats(res.data)
    } catch (error) {
      console.error('获取统计失败:', error)
    }
  }

  const handleScan = async () => {
    try {
      message.loading({ content: '正在启动DNS扫描...', key: 'scan' })
      await api.scanDNS({ domain: scanDomain })
      message.success({ content: 'DNS扫描已启动', key: 'scan' })
      setScanModal(false)
      setScanDomain('')
      setTimeout(() => {
        fetchData()
        fetchStats()
      }, 2000)
    } catch (error) {
      message.error({ content: error.message || '启动失败', key: 'scan' })
    }
  }

  const handlePromote = async (id) => {
    try {
      message.loading({ content: '正在提升为监控域名...', key: 'promote' })
      await api.promoteSubdomain(id)
      message.success({ content: '提升成功，已开始监控', key: 'promote' })
      fetchData()
      fetchStats()
    } catch (error) {
      message.error({ content: error.message || '提升失败', key: 'promote' })
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteSubdomainRecord(id)
      message.success('删除成功')
      fetchData()
      fetchStats()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const getRecordTypeColor = (type) => {
    const colors = {
      A: 'blue',
      MX: 'green',
      CNAME: 'orange',
      TXT: 'purple',
      NS: 'cyan',
    }
    return colors[type] || 'default'
  }

  const subdomainColumns = [
    {
      title: '子域名',
      dataIndex: 'subdomain',
      key: 'subdomain',
      render: (text) => <a>{text}</a>,
    },
    {
      title: '父域名',
      dataIndex: 'parent_domain',
      key: 'parent_domain',
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '记录类型',
      dataIndex: 'record_type',
      key: 'record_type',
      render: (text) => <Tag color={getRecordTypeColor(text)}>{text}</Tag>,
    },
    {
      title: '记录值',
      dataIndex: 'record_value',
      key: 'record_value',
      ellipsis: true,
    },
    {
      title: '自动添加',
      dataIndex: 'auto_added',
      key: 'auto_added',
      render: (val) => (val ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '已监控',
      dataIndex: 'monitored',
      key: 'monitored',
      render: (val) => (val ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    {
      title: '发现时间',
      dataIndex: 'discovered_at',
      key: 'discovered_at',
      width: 160,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <Space size="small">
          {!record.monitored && (
            <Tooltip title="提升为监控域名">
              <Button
                type="link"
                size="small"
                icon={<RocketOutlined />}
                onClick={() => handlePromote(record.id)}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确定删除该记录？"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const dnsColumns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
    },
    {
      title: '记录类型',
      dataIndex: 'record_type',
      key: 'record_type',
      render: (text) => <Tag color={getRecordTypeColor(text)}>{text}</Tag>,
    },
    {
      title: '记录值',
      dataIndex: 'value',
      key: 'value',
      ellipsis: true,
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (val) => (val > 0 ? val : '-'),
    },
    {
      title: 'TTL',
      dataIndex: 'ttl',
      key: 'ttl',
      render: (val) => (val > 0 ? `${val}s` : '-'),
    },
    {
      title: 'DNS服务器',
      dataIndex: 'server',
      key: 'server',
    },
    {
      title: '扫描时间',
      dataIndex: 'scanned_at',
      key: 'scanned_at',
      width: 160,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="子域名总数"
              value={stats?.total_subdomains || 0}
              prefix={<ShareAltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="DNS记录总数"
              value={stats?.total_records || 0}
              prefix={<DnsOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="已监控"
              value={stats?.monitored || 0}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="自动添加"
              value={stats?.auto_added || 0}
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Input
              placeholder="搜索域名"
              value={parentDomain}
              onChange={(e) => setParentDomain(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Button.Group>
              <Button
                type={activeTab === 'subdomains' ? 'primary' : 'default'}
                onClick={() => {
                  setActiveTab('subdomains')
                  setPage(1)
                }}
              >
                子域名
              </Button>
              <Button
                type={activeTab === 'records' ? 'primary' : 'default'}
                onClick={() => {
                  setActiveTab('records')
                  setPage(1)
                }}
              >
                DNS记录
              </Button>
            </Button.Group>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => setScanModal(true)}
            >
              扫描DNS
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                fetchData()
                fetchStats()
              }}
            >
              刷新
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={activeTab === 'subdomains' ? subdomainColumns : dnsColumns}
        dataSource={activeTab === 'subdomains' ? subdomains : dnsRecords}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />

      <Modal
        title="DNS扫描"
        open={scanModal}
        onOk={handleScan}
        onCancel={() => setScanModal(false)}
        okText="开始扫描"
      >
        <p style={{ marginBottom: 16 }}>
          输入要扫描的域名，留空则扫描所有已添加的域名
        </p>
        <Input
          placeholder="例如: example.com"
          value={scanDomain}
          onChange={(e) => setScanDomain(e.target.value)}
        />
      </Modal>
    </div>
  )
}

export default SubdomainDiscovery
