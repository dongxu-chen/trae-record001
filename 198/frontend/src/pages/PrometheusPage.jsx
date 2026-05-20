import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Input,
  Space,
  message,
  Typography,
  Row,
  Col,
  Table,
  Tag,
  Empty,
  Tabs,
  Badge,
  Alert,
} from 'antd'
import {
  DatabaseOutlined,
  ReloadOutlined,
  SearchOutlined,
  AlertOutlined,
  SafetyOutlined,
} from '@ant-design/icons'

import { prometheusApi } from '../api/client'

const { Title, Text } = Typography
const { TabPane } = Tabs

function PrometheusPage() {
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('up')
  const [queryResult, setQueryResult] = useState(null)
  const [rules, setRules] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [activeTab, setActiveTab] = useState('query')

  const executeQuery = async () => {
    if (!query.trim()) {
      message.warning('请输入查询语句')
      return
    }
    setLoading(true)
    try {
      const res = await prometheusApi.query(query)
      setQueryResult(res.data)
      message.success('查询成功')
    } catch (error) {
      message.error(error.response?.data?.error || '查询失败')
    } finally {
      setLoading(false)
    }
  }

  const loadRules = async () => {
    setLoading(true)
    try {
      const res = await prometheusApi.getRules()
      setRules(res.data)
    } catch (error) {
      message.error(error.response?.data?.error || '加载规则失败')
    } finally {
      setLoading(false)
    }
  }

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const res = await prometheusApi.getAlerts()
      setAlerts(res.data)
    } catch (error) {
      message.error(error.response?.data?.error || '加载告警失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'rules' && !rules) {
      loadRules()
    } else if (activeTab === 'alerts' && !alerts) {
      loadAlerts()
    }
  }, [activeTab])

  const getStatusColor = (state) => {
    switch (state) {
      case 'firing':
        return 'red'
      case 'pending':
        return 'orange'
      case 'inactive':
        return 'green'
      default:
        return 'default'
    }
  }

  const ruleColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (text) => (
        <Tag color={text === 'alerting' ? 'red' : 'blue'}>{text}</Tag>
      ),
    },
    {
      title: '表达式',
      dataIndex: 'query',
      key: 'query',
      render: (text) => (
        <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
          {text}
        </code>
      ),
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      width: 120,
      render: (text) => (
        <Badge status={text === 'firing' ? 'error' : text === 'pending' ? 'warning' : 'success'} text={text} />
      ),
    },
  ]

  const alertColumns = [
    {
      title: '告警名称',
      dataIndex: ['labels', 'alertname'],
      key: 'alertname',
      width: 200,
      render: (text) => <span style={{ fontWeight: 'bold' }}>{text}</span>,
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      width: 100,
      render: (text) => (
        <Tag color={getStatusColor(text)}>{text}</Tag>
      ),
    },
    {
      title: '标签',
      dataIndex: 'labels',
      key: 'labels',
      render: (labels) => (
        <Space wrap>
          {Object.entries(labels)
            .filter(([k]) => k !== 'alertname')
            .map(([k, v]) => (
              <Tag key={k}>{k}={v}</Tag>
            ))}
        </Space>
      ),
    },
    {
      title: '活动时间',
      dataIndex: 'activeAt',
      key: 'activeAt',
      width: 200,
      render: (time) => new Date(time).toLocaleString(),
    },
  ]

  const renderVectorResult = (result) => {
    const columns = [
      {
        title: '指标',
        key: 'metric',
        render: (record) => (
          <Space direction="vertical" size={0}>
            <Text code>{record.metric.__name__ || '-'}</Text>
            <Space wrap size={[4, 0]}>
              {Object.entries(record.metric)
                .filter(([k]) => k !== '__name__')
                .map(([k, v]) => (
                  <Tag key={k} size="small">
                    {k}={v}
                  </Tag>
                ))}
            </Space>
          </Space>
        ),
      },
      {
        title: '时间戳',
        key: 'timestamp',
        width: 200,
        render: (record) => new Date(record.value[0] * 1000).toLocaleString(),
      },
      {
        title: '值',
        key: 'value',
        width: 120,
        render: (record) => (
          <Text strong style={{ fontFamily: 'monospace' }}>
            {record.value[1]}
          </Text>
        ),
      },
    ]

    return (
      <Table
        columns={columns}
        dataSource={result}
        rowKey={(record, idx) => idx}
        pagination={false}
      />
    )
  }

  return (
    <div>
      <div className="page-header">
        <Title level={3} className="page-title">
          <DatabaseOutlined /> Prometheus 集成
        </Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              if (activeTab === 'rules') loadRules()
              else if (activeTab === 'alerts') loadAlerts()
              else executeQuery()
            }}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane
            tab={
              <Space>
                <SearchOutlined /> PromQL 查询
              </Space>
            }
            key="query"
          >
            <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="输入 PromQL 查询语句，例如: up, rate(http_requests_total[5m])"
                onPressEnter={executeQuery}
              />
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={executeQuery}
                loading={loading}
              >
                查询
              </Button>
            </Space.Compact>

            <Space wrap style={{ marginBottom: 16 }}>
              <Text type="secondary">快捷查询:</Text>
              {['up', 'cpu_usage', 'memory_usage', 'rate(http_requests_total[5m])', 'sum by (job) (up)'].map(
                (q) => (
                  <Button key={q} size="small" onClick={() => setQuery(q)}>
                    {q}
                  </Button>
                )
              )}
            </Space>

            {queryResult ? (
              queryResult.status === 'success' ? (
                <div>
                  <Alert
                    message="查询成功"
                    description={
                      <div>
                        <div>返回类型: <Tag color="blue">{queryResult.data.resultType}</Tag></div>
                        <div>结果数量: <Tag color="green">{queryResult.data.result?.length || 0}</Tag></div>
                      </div>
                    }
                    type="success"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  {queryResult.data.resultType === 'vector' &&
                    renderVectorResult(queryResult.data.result)}
                  {queryResult.data.resultType !== 'vector' && (
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        overflow: 'auto',
                        maxHeight: '400px',
                      }}
                    >
                      {JSON.stringify(queryResult.data, null, 2)}
                    </pre>
                  )}
                </div>
              ) : (
                <Alert
                  message="查询失败"
                  description={queryResult.error || '未知错误'}
                  type="error"
                  showIcon
                />
              )
            ) : (
              <Empty description="执行 PromQL 查询以查看结果" />
            )}
          </TabPane>

          <TabPane
            tab={
              <Space>
                <SafetyOutlined /> 规则列表
              </Space>
            }
            key="rules"
          >
            {rules ? (
              rules.status === 'success' ? (
                <div>
                  {rules.data.groups?.map((group, idx) => (
                    <Card
                      key={idx}
                      title={
                        <Space>
                          <Text strong>{group.name}</Text>
                          <Tag>间隔: {group.interval}</Tag>
                        </Space>
                      }
                      style={{ marginBottom: 16 }}
                      size="small"
                    >
                      <Table
                        columns={ruleColumns}
                        dataSource={group.rules}
                        rowKey={(record, i) => i}
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  ))}
                </div>
              ) : (
                <Alert
                  message="加载失败"
                  description={rules.error || '未知错误'}
                  type="error"
                  showIcon
                />
              )
            ) : (
              <Empty description="加载中..." />
            )}
          </TabPane>

          <TabPane
            tab={
              <Space>
                <AlertOutlined /> 当前告警
              </Space>
            }
            key="alerts"
          >
            {alerts ? (
              alerts.status === 'success' ? (
                alerts.data.alerts?.length > 0 ? (
                  <Table
                    columns={alertColumns}
                    dataSource={alerts.data.alerts}
                    rowKey={(record, idx) => idx}
                    pagination={{ pageSize: 10 }}
                  />
                ) : (
                  <Empty description="当前没有触发的告警" />
                )
              ) : (
                <Alert
                  message="加载失败"
                  description={alerts.error || '未知错误'}
                  type="error"
                  showIcon
                />
              )
            ) : (
              <Empty description="加载中..." />
            )}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default PrometheusPage
