import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Form,
  Input,
  Select,
  Space,
  message,
  Typography,
  Row,
  Col,
  Table,
  Tag,
  Divider,
  Alert,
  Tabs,
  Modal,
  Switch,
  InputNumber,
  Descriptions,
  Timeline,
  Badge,
  Collapse,
} from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  DeleteOutlined,
  CodeOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  HistoryOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import Editor from '@monaco-editor/react'

import { promqlApi, ruleApi } from '../api/client'

const { Title, Text } = Typography
const { Option } = Select
const { TabPane } = Tabs
const { Panel } = Collapse

function SimulatePage() {
  const [form] = Form.useForm()
  const [rules, setRules] = useState([])
  const [simulating, setSimulating] = useState(false)
  const [validateResult, setValidateResult] = useState(null)
  const [simulateResult, setSimulateResult] = useState(null)
  const [inputMode, setInputMode] = useState('simple') // simple or timeseries
  const [forDuration, setForDuration] = useState('5m')
  const [enableDurationCheck, setEnableDurationCheck] = useState(true)

  const [metrics, setMetrics] = useState([
    { name: 'cpu_usage', labels: { instance: 'server-01', job: 'node' }, value: 85.5 },
    { name: 'cpu_usage', labels: { instance: 'server-02', job: 'node' }, value: 62.3 },
    { name: 'memory_usage', labels: { instance: 'server-01', job: 'node' }, value: 45.0 },
  ])

  const [timeSeries, setTimeSeries] = useState([])
  const [generateModalVisible, setGenerateModalVisible] = useState(false)
  const [generateForm] = Form.useForm()

  useEffect(() => {
    loadRules()
    generateSampleTimeSeries()
  }, [])

  const loadRules = async () => {
    try {
      const res = await ruleApi.list()
      setRules(res.data)
    } catch (error) {
      message.error('加载规则失败')
    }
  }

  const generateSampleTimeSeries = async () => {
    try {
      const res = await promqlApi.generateTestData({
        name: 'cpu_usage',
        labels: { instance: 'server-01', job: 'node' },
        duration: '10m',
        interval: '30s',
        pattern: 'spike',
        start_value: 40,
        end_value: 95,
      })
      setTimeSeries([res.data.time_series])
    } catch (error) {
      console.log('Generate sample data failed:', error)
    }
  }

  const validateExpr = async (expr) => {
    if (!expr) {
      setValidateResult(null)
      return
    }
    try {
      const res = await promqlApi.validate(expr)
      setValidateResult(res.data)
    } catch (error) {
      setValidateResult({
        valid: false,
        error: error.response?.data?.error || '校验失败',
        message: 'PromQL syntax is invalid',
      })
    }
  }

  const handleRuleSelect = (ruleId) => {
    const rule = rules.find((r) => r.id === ruleId)
    if (rule) {
      form.setFieldsValue({
        expr: rule.expr,
      })
      setForDuration(rule.for || '5m')
      validateExpr(rule.expr)
    }
  }

  const addMetric = () => {
    setMetrics([...metrics, { name: '', labels: {}, value: 0 }])
  }

  const removeMetric = (index) => {
    const newMetrics = [...metrics]
    newMetrics.splice(index, 1)
    setMetrics(newMetrics)
  }

  const updateMetric = (index, field, value) => {
    const newMetrics = [...metrics]
    if (field === 'labels') {
      try {
        newMetrics[index][field] = JSON.parse(value)
      } catch {
        newMetrics[index][field] = {}
      }
    } else if (field === 'value') {
      newMetrics[index][field] = parseFloat(value) || 0
    } else {
      newMetrics[index][field] = value
    }
    setMetrics(newMetrics)
  }

  const addTimeSeries = () => {
    setTimeSeries([...timeSeries, { name: '', labels: {}, points: [] }])
  }

  const removeTimeSeries = (index) => {
    const newTS = [...timeSeries]
    newTS.splice(index, 1)
    setTimeSeries(newTS)
  }

  const updateTimeSeries = (index, field, value) => {
    const newTS = [...timeSeries]
    if (field === 'labels') {
      try {
        newTS[index][field] = JSON.parse(value)
      } catch {
        newTS[index][field] = {}
      }
    } else if (field === 'points') {
      try {
        newTS[index][field] = JSON.parse(value)
      } catch {
        newTS[index][field] = []
      }
    } else {
      newTS[index][field] = value
    }
    setTimeSeries(newTS)
  }

  const handleGenerateTestData = async () => {
    const values = await generateForm.validateFields()
    try {
      const res = await promqlApi.generateTestData(values)
      setTimeSeries([...timeSeries, res.data.time_series])
      message.success(`成功生成 ${res.data.point_count} 个数据点`)
      setGenerateModalVisible(false)
      generateForm.resetFields()
    } catch (error) {
      message.error(error.response?.data?.error || '生成测试数据失败')
    }
  }

  const handleSimulate = async () => {
    const values = await form.validateFields()
    if (!validateResult?.valid) {
      message.error('请先输入有效的 PromQL 表达式')
      return
    }

    setSimulating(true)
    setSimulateResult(null)

    try {
      const duration = enableDurationCheck ? forDuration : ''
      const metricsData = inputMode === 'simple' ? metrics : []
      const timeSeriesData = inputMode === 'timeseries' ? timeSeries : []

      const res = await promqlApi.simulate(values.expr, duration, metricsData, timeSeriesData)
      setSimulateResult(res.data)
      message.success('模拟完成')
    } catch (error) {
      message.error(error.response?.data?.error || '模拟失败')
    } finally {
      setSimulating(false)
    }
  }

  const metricColumns = [
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
      render: (text, record, index) => (
        <Input
          value={text}
          onChange={(e) => updateMetric(index, 'name', e.target.value)}
          placeholder="例如: cpu_usage"
        />
      ),
    },
    {
      title: '标签 (JSON)',
      dataIndex: 'labels',
      key: 'labels',
      render: (text, record, index) => (
        <Input.TextArea
          value={JSON.stringify(text, null, 2)}
          onChange={(e) => updateMetric(index, 'labels', e.target.value)}
          placeholder='{"instance": "server-01"}'
          rows={2}
        />
      ),
    },
    {
      title: '数值',
      dataIndex: 'value',
      key: 'value',
      width: 120,
      render: (text, record, index) => (
        <InputNumber
          value={text}
          onChange={(value) => updateMetric(index, 'value', value)}
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record, index) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeMetric(index)}
        />
      ),
    },
  ]

  const timeSeriesColumns = [
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text, record, index) => (
        <Input
          value={text}
          onChange={(e) => updateTimeSeries(index, 'name', e.target.value)}
          placeholder="cpu_usage"
        />
      ),
    },
    {
      title: '标签 (JSON)',
      dataIndex: 'labels',
      key: 'labels',
      render: (text, record, index) => (
        <Input.TextArea
          value={JSON.stringify(text, null, 2)}
          onChange={(e) => updateTimeSeries(index, 'labels', e.target.value)}
          placeholder='{"instance": "server-01"}'
          rows={1}
        />
      ),
    },
    {
      title: '数据点数量',
      key: 'points',
      width: 120,
      render: (text, record) => <Tag color="blue">{record.points?.length || 0} 点</Tag>,
    },
    {
      title: '时间范围',
      key: 'timerange',
      width: 250,
      render: (text, record) => {
        if (!record.points || record.points.length === 0) return '-'
        const start = new Date(record.points[0].timestamp).toLocaleString()
        const end = new Date(record.points[record.points.length - 1].timestamp).toLocaleString()
        return `${start} → ${end}`
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record, index) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeTimeSeries(index)}
        />
      ),
    },
  ]

  const getEventTypeIcon = (type) => {
    switch (type) {
      case 'start_firing':
        return <ThunderboltOutlined style={{ color: '#ff4d4f' }} />
      case 'stop_firing':
        return <CloseCircleOutlined style={{ color: '#faad14' }} />
      case 'duration_met':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      default:
        return <ClockCircleOutlined />
    }
  }

  return (
    <div>
      <div className="page-header">
        <Title level={3} className="page-title">
          <PlayCircleOutlined /> 告警规则模拟测试
        </Title>
        <Space>
          <Tag color="blue">支持持续时间验证</Tag>
          <Tag color="green">支持时间序列模拟</Tag>
          <Tag color="purple">自动生成测试数据</Tag>
        </Space>
      </div>

      <Row gutter={24}>
        <Col span={14}>
          <Card title="PromQL 表达式" className="rule-card">
            <Form form={form} layout="vertical">
              <Form.Item label="从已有规则加载">
                <Select
                  placeholder="选择一个规则快速加载"
                  allowClear
                  onChange={handleRuleSelect}
                  showSearch
                  optionFilterProp="children"
                >
                  {rules.map((r) => (
                    <Option key={r.id} value={r.id}>
                      {r.name} {r.for && `(${r.for})`}
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                name="expr"
                label="PromQL 表达式"
                rules={[{ required: true, message: '请输入 PromQL 表达式' }]}
                extra={
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {validateResult?.valid === true && (
                      <div>
                        <Space>
                          <span style={{ color: '#52c41a' }}>
                            <CheckCircleOutlined /> {validateResult.message}
                          </span>
                          {validateResult.expr_type && (
                            <Tag color="blue">类型: {validateResult.expr_type}</Tag>
                          )}
                        </Space>
                        {validateResult.ast_info && (
                          <Space style={{ marginTop: 8 }} wrap>
                            {validateResult.ast_info.metrics && (
                              <Tag color="green">
                                指标: {validateResult.ast_info.metrics.join(', ')}
                              </Tag>
                            )}
                            {validateResult.ast_info.functions && (
                              <Tag color="orange">
                                函数: {validateResult.ast_info.functions.join(', ')}
                              </Tag>
                            )}
                            {validateResult.ast_info.aggregations && (
                              <Tag color="purple">
                                聚合: {validateResult.ast_info.aggregations.join(', ')}
                              </Tag>
                            )}
                            {validateResult.ast_info.binary_operators && (
                              <Tag color="cyan">
                                操作符: {validateResult.ast_info.binary_operators.join(', ')}
                              </Tag>
                            )}
                          </Space>
                        )}
                      </div>
                    )}
                    {validateResult?.valid === false && (
                      <span style={{ color: '#ff4d4f' }}>
                        <CloseCircleOutlined /> {validateResult.error || validateResult.message}
                      </span>
                    )}
                  </Space>
                }
              >
                <div className="monaco-editor-container">
                  <Editor
                    height="180px"
                    defaultLanguage="promql"
                    theme="vs-light"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      lineNumbers: 'on',
                    }}
                    onChange={(value) => {
                      form.setFieldsValue({ expr: value })
                      validateExpr(value)
                    }}
                    placeholder="例如: cpu_usage > 80"
                  />
                </div>
              </Form.Item>

              <Space style={{ width: '100%', display: 'flex', alignItems: 'center' }}>
                <Switch
                  checked={enableDurationCheck}
                  onChange={setEnableDurationCheck}
                />
                <Text>验证持续时间 (For)</Text>
                {enableDurationCheck && (
                  <Input
                    value={forDuration}
                    onChange={(e) => setForDuration(e.target.value)}
                    placeholder="例如: 5m, 1h"
                    style={{ width: 120 }}
                    prefix={<ClockCircleOutlined />}
                  />
                )}
              </Space>

              <Alert
                message="表达式示例"
                description={
                  <div>
                    <div><code>cpu_usage{job="node"} > 80</code> - CPU使用率超过80%</div>
                    <div><code>rate(http_requests_total[5m]) > 100</code> - 5分钟内HTTP请求速率超过100/s</div>
                    <div><code>sum by (instance) (memory_usage) > 90</code> - 按实例分组的内存使用率超过90%</div>
                  </div>
                }
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Form>
          </Card>

          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>模拟数据输入</span>
              </Space>
            }
            className="rule-card"
          >
            <Tabs
              activeKey={inputMode}
              onChange={setInputMode}
              tabBarExtraContent={
                inputMode === 'timeseries' && (
                  <Space>
                    <Button
                      size="small"
                      icon={<SettingOutlined />}
                      onClick={() => setGenerateModalVisible(true)}
                    >
                      生成测试数据
                    </Button>
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={addTimeSeries}
                    >
                      添加时序
                    </Button>
                  </Space>
                )
              }
            >
              <TabPane
                tab={
                  <Space>
                    <CodeOutlined />
                    简单模式 (瞬时值)
                  </Space>
                }
                key="simple"
              >
                <Table
                  columns={metricColumns}
                  dataSource={metrics}
                  rowKey={(record, index) => index}
                  pagination={false}
                  size="small"
                />
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={addMetric}
                  style={{ marginTop: 16 }}
                >
                  添加指标
                </Button>
              </TabPane>

              <TabPane
                tab={
                  <Space>
                    <HistoryOutlined />
                    时间序列模式
                  </Space>
                }
                key="timeseries"
              >
                <Alert
                  message="时间序列模式说明"
                  description="在此模式下，您可以输入多个时间点的数据，系统会模拟Prometheus的评估过程，验证告警条件是否持续了足够的时间。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                <Table
                  columns={timeSeriesColumns}
                  dataSource={timeSeries}
                  rowKey={(record, index) => index}
                  pagination={false}
                  size="small"
                  expandable={{
                    expandedRowRender: (record) => (
                      <Collapse defaultActiveKey={['1']}>
                        <Panel header="原始数据点" key="1">
                          <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                            {JSON.stringify(record.points, null, 2)}
                          </pre>
                        </Panel>
                      </Collapse>
                    ),
                  }}
                />
                {timeSeries.length > 0 && (
                  <Divider />
                )}
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="时间序列数量">
                    {timeSeries.length}
                  </Descriptions.Item>
                  <Descriptions.Item label="总数据点数">
                    {timeSeries.reduce((sum, ts) => sum + (ts.points?.length || 0), 0)}
                  </Descriptions.Item>
                  <Descriptions.Item label="持续时间要求">
                    <Tag color={enableDurationCheck ? 'blue' : 'default'}>
                      {enableDurationCheck ? forDuration : '不验证'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="评估模式">
                    <Tag color="green">按时间顺序评估</Tag>
                  </Descriptions.Item>
                </Descriptions>
              </TabPane>
            </Tabs>
          </Card>

          <Button
            type="primary"
            size="large"
            icon={<PlayCircleOutlined />}
            onClick={handleSimulate}
            loading={simulating}
            disabled={!validateResult?.valid}
            style={{ marginTop: 16, width: '100%' }}
          >
            运行模拟测试
          </Button>
        </Col>

        <Col span={10}>
          <Card title="模拟结果" className="rule-card">
            {simulateResult ? (
              <div>
                <div
                  className={`simulate-result ${
                    simulateResult.duration_verified ? 'firing' : simulateResult.firing ? 'warning' : 'success'
                  }`}
                  style={{
                    background: simulateResult.duration_verified
                      ? '#fff1f0'
                      : simulateResult.firing
                      ? '#fffbe6'
                      : '#f6ffed',
                    border: `1px solid ${
                      simulateResult.duration_verified
                        ? '#ffccc7'
                        : simulateResult.firing
                        ? '#ffe58f'
                        : '#b7eb8f'
                    }`,
                    padding: 16,
                    borderRadius: 8,
                    marginBottom: 16,
                  }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      {simulateResult.duration_verified ? (
                        <ThunderboltOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
                      ) : simulateResult.firing ? (
                        <ClockCircleOutlined style={{ color: '#faad14', fontSize: 24 }} />
                      ) : (
                        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
                      )}
                      <Text strong style={{ fontSize: 16 }}>
                        {simulateResult.message}
                      </Text>
                    </Space>

                    {simulateResult.required_duration && (
                      <Space wrap>
                        <Tag color="blue">
                          要求持续时间: {simulateResult.required_duration}
                        </Tag>
                        {simulateResult.actual_duration && (
                          <Tag
                            color={simulateResult.duration_verified ? 'red' : 'orange'}
                          >
                            实际持续时间: {simulateResult.actual_duration}
                          </Tag>
                        )}
                        <Tag color={simulateResult.duration_verified ? 'green' : 'default'}>
                          持续时间验证: {simulateResult.duration_verified ? '通过' : '未通过'}
                        </Tag>
                      </Space>
                    )}
                  </Space>
                </div>

                {simulateResult.matched_time_series && simulateResult.matched_time_series.length > 0 && (
                  <div>
                    <Title level={5}>
                      <Space>
                        <BarChartOutlined />
                        匹配的时间序列
                      </Space>
                    </Title>
                    {simulateResult.matched_time_series.map((ts, idx) => (
                      <Card
                        key={idx}
                        size="small"
                        style={{ marginBottom: 8 }}
                        title={
                          <Space>
                            <Text code>{ts.name}</Text>
                            <Badge
                              status={ts.firing ? 'error' : 'default'}
                              text={ts.firing ? '正在触发' : '未触发'}
                            />
                          </Space>
                        }
                        extra={
                          <Space>
                            {ts.firing_for && (
                              <Tag color="orange">持续: {ts.firing_for}</Tag>
                            )}
                            <Tag color="blue">{ts.point_count} 个数据点</Tag>
                          </Space>
                        }
                      >
                        <Space wrap style={{ marginBottom: 8 }}>
                          {Object.entries(ts.labels || {}).map(([k, v]) => (
                            <Tag key={k}>{k}={v}</Tag>
                          ))}
                        </Space>
                        <Descriptions column={2} size="small">
                          <Descriptions.Item label="当前值">
                            <Text strong style={{ color: ts.firing ? '#ff4d4f' : 'inherit' }}>
                              {ts.current_value?.toFixed(2)}
                            </Text>
                          </Descriptions.Item>
                          <Descriptions.Item label="触发开始时间">
                            {ts.firing_start
                              ? new Date(ts.firing_start).toLocaleString()
                              : '-'}
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                    ))}
                  </div>
                )}

                {simulateResult.matched_labels && simulateResult.matched_labels.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <Title level={5}>
                      <Space>
                        <ThunderboltOutlined />
                        触发的指标
                      </Space>
                    </Title>
                    {simulateResult.matched_labels.map((labels, idx) => (
                      <div key={idx} style={{ marginBottom: 8 }}>
                        <Text code>{labels['__name__']}</Text>
                        <div style={{ marginTop: 4 }}>
                          {Object.entries(labels)
                            .filter(([k]) => k !== '__name__')
                            .map(([k, v]) => (
                              <Tag key={k} color="blue">
                                {k}={v}
                              </Tag>
                            ))}
                          {simulateResult.values && (
                            <Tag color="red">值: {simulateResult.values[idx]}</Tag>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {simulateResult.timeline && simulateResult.timeline.length > 0 && (
                  <div style={{ marginTop: 16 }}>
                    <Title level={5}>
                      <Space>
                        <HistoryOutlined />
                        事件时间线
                      </Space>
                    </Title>
                    <Timeline
                      items={simulateResult.timeline.map((event) => ({
                        color:
                          event.event_type === 'duration_met'
                            ? 'green'
                            : event.event_type === 'start_firing'
                            ? 'red'
                            : 'gray',
                        dot: getEventTypeIcon(event.event_type),
                        children: (
                          <div>
                            <div style={{ fontSize: 12, color: '#888' }}>
                              {new Date(event.timestamp).toLocaleString()}
                            </div>
                            <div>{event.message}</div>
                          </div>
                        ),
                      }))}
                    />
                  </div>
                )}

                <Divider />

                <div>
                  <Title level={5}>原始结果</Title>
                  <pre
                    style={{
                      background: '#f5f5f5',
                      padding: 12,
                      borderRadius: 4,
                      overflow: 'auto',
                      maxHeight: 300,
                      fontSize: 12,
                    }}
                  >
                    {JSON.stringify(simulateResult, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '48px 0', color: '#999' }}>
                <PlayCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>输入 PromQL 表达式和模拟指标数据后点击"运行模拟测试"</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        title="生成测试数据"
        open={generateModalVisible}
        onCancel={() => setGenerateModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setGenerateModalVisible(false)}>
            取消
          </Button>,
          <Button key="submit" type="primary" onClick={handleGenerateTestData}>
            生成
          </Button>,
        ]}
      >
        <Form form={generateForm} layout="vertical">
          <Form.Item
            name="name"
            label="指标名称"
            rules={[{ required: true }]}
          >
            <Input placeholder="例如: cpu_usage" />
          </Form.Item>

          <Form.Item name="labels" label="标签 (JSON)">
            <Input.TextArea
              rows={2}
              placeholder='{"instance": "server-01", "job": "node"}'
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="duration"
                label="时间范围"
                rules={[{ required: true }]}
              >
                <Select placeholder="选择时间范围">
                  <Option value="1m">1 分钟</Option>
                  <Option value="5m">5 分钟</Option>
                  <Option value="10m">10 分钟</Option>
                  <Option value="30m">30 分钟</Option>
                  <Option value="1h">1 小时</Option>
                  <Option value="3h">3 小时</Option>
                  <Option value="6h">6 小时</Option>
                  <Option value="1d">1 天</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="interval"
                label="采样间隔"
                rules={[{ required: true }]}
              >
                <Select placeholder="选择采样间隔">
                  <Option value="5s">5 秒</Option>
                  <Option value="10s">10 秒</Option>
                  <Option value="15s">15 秒</Option>
                  <Option value="30s">30 秒</Option>
                  <Option value="1m">1 分钟</Option>
                  <Option value="5m">5 分钟</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="pattern"
            label="数据模式"
            rules={[{ required: true }]}
          >
            <Select placeholder="选择数据生成模式">
              <Option value="increasing">持续上升</Option>
              <Option value="decreasing">持续下降</Option>
              <Option value="spike">突然飙升</Option>
              <Option value="wave">正弦波动</Option>
              <Option value="random">随机波动</Option>
              <Option value="constant">恒定值</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_value"
                label="起始值"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: '100%' }} placeholder="例如: 40" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="end_value"
                label="结束/峰值"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: '100%' }} placeholder="例如: 90" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

export default SimulatePage
