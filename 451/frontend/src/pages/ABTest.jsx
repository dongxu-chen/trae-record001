import { useState, useEffect } from 'react'
import { Card, Table, Button, Tag, Space, Modal, Form, Input, InputNumber, Select, Statistic, Row, Col, message, Popconfirm, Progress } from 'antd'
import { PlayCircleOutlined, PauseCircleOutlined, DeleteOutlined, BarChartOutlined, PlusOutlined } from '@ant-design/icons'
import { abtestApi, ruleApi } from '../services/api'

const STATUS_MAP = {
  CREATED: { color: 'default', label: '已创建' },
  RUNNING: { color: 'processing', label: '运行中' },
  STOPPED: { color: 'error', label: '已停止' },
}

const SPLIT_STRATEGY_MAP = {
  USER_ID_HASH: '用户ID哈希',
  IP_HASH: 'IP哈希',
  RANDOM: '随机分流',
}

export default function ABTest() {
  const [experiments, setExperiments] = useState([])
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [createVisible, setCreateVisible] = useState(false)
  const [statsVisible, setStatsVisible] = useState(false)
  const [currentStats, setCurrentStats] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [expData, ruleData] = await Promise.all([
        abtestApi.getAll(),
        ruleApi.getAll(),
      ])
      setExperiments(expData || [])
      setRules(ruleData || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (values) => {
    try {
      await abtestApi.create(values)
      message.success('A/B测试实验已创建')
      setCreateVisible(false)
      form.resetFields()
      loadData()
    } catch (e) {
      message.error('创建失败')
    }
  }

  const handleStart = async (id) => {
    try {
      await abtestApi.start(id)
      message.success('实验已启动')
      loadData()
    } catch (e) {
      message.error('启动失败')
    }
  }

  const handleStop = async (id) => {
    try {
      await abtestApi.stop(id)
      message.success('实验已停止')
      loadData()
    } catch (e) {
      message.error('停止失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await abtestApi.delete(id)
      message.success('实验已删除')
      loadData()
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleViewStats = async (id) => {
    try {
      const data = await abtestApi.getStats(id)
      setCurrentStats(data)
      setStatsVisible(true)
    } catch (e) {
      message.error('获取统计失败')
    }
  }

  const columns = [
    {
      title: '实验编码',
      dataIndex: 'experimentCode',
      key: 'experimentCode',
      width: 150,
      render: (text) => <code style={{ color: '#1677ff' }}>{text}</code>,
    },
    {
      title: '实验名称',
      dataIndex: 'experimentName',
      key: 'experimentName',
      width: 180,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s) => <Tag color={STATUS_MAP[s]?.color}>{STATUS_MAP[s]?.label}</Tag>,
    },
    {
      title: '流量比例',
      dataIndex: 'trafficPercentage',
      key: 'trafficPercentage',
      width: 100,
      render: (pct) => (
        <Progress percent={pct} size="small" style={{ width: 80 }} format={(p) => `${p}%`} />
      ),
    },
    {
      title: '分流策略',
      dataIndex: 'splitStrategy',
      key: 'splitStrategy',
      width: 120,
      render: (s) => SPLIT_STRATEGY_MAP[s] || s,
    },
    {
      title: '基线规则数',
      dataIndex: 'baselineRuleCodes',
      key: 'baselineRuleCodes',
      width: 100,
      render: (codes) => codes?.length || 0,
    },
    {
      title: '实验规则数',
      dataIndex: 'experimentRuleCodes',
      key: 'experimentRuleCodes',
      width: 100,
      render: (codes) => codes?.length || 0,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_, record) => (
        <Space size="small">
          {record.status !== 'RUNNING' && (
            <Button type="link" size="small" icon={<PlayCircleOutlined />} onClick={() => handleStart(record.id)}>
              启动
            </Button>
          )}
          {record.status === 'RUNNING' && (
            <Button type="link" size="small" icon={<PauseCircleOutlined />} onClick={() => handleStop(record.id)}>
              停止
            </Button>
          )}
          <Button type="link" size="small" icon={<BarChartOutlined />} onClick={() => handleViewStats(record.id)}>
            统计
          </Button>
          <Popconfirm title="确定删除此实验？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="A/B 测试管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
            新建实验
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={experiments}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
        />
      </Card>

      <Modal
        title="新建 A/B 测试实验"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="experimentCode" label="实验编码" rules={[{ required: true }]}>
            <Input placeholder="例如: EXP_IP_CHECK_V2" style={{ fontFamily: 'monospace' }} />
          </Form.Item>
          <Form.Item name="experimentName" label="实验名称" rules={[{ required: true }]}>
            <Input placeholder="例如: IP检测规则V2灰度测试" />
          </Form.Item>
          <Form.Item name="description" label="实验描述">
            <Input.TextArea rows={2} placeholder="描述实验目的和预期" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="trafficPercentage" label="实验组流量比例 (%)" initialValue={10}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="splitStrategy" label="分流策略" initialValue="USER_ID_HASH">
                <Select options={Object.entries(SPLIT_STRATEGY_MAP).map(([k, v]) => ({ value: k, label: v }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="baselineRuleCodes" label="基线规则集（对照组）" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="选择对照组使用的规则"
              options={rules.map(r => ({ value: r.ruleCode, label: `${r.ruleName} (${r.ruleCode})` }))}
            />
          </Form.Item>
          <Form.Item name="experimentRuleCodes" label="实验规则集（实验组）" rules={[{ required: true }]}>
            <Select mode="multiple" placeholder="选择实验组使用的新规则"
              options={rules.map(r => ({ value: r.ruleCode, label: `${r.ruleName} (${r.ruleCode})` }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="A/B 测试统计"
        open={statsVisible}
        onCancel={() => setStatsVisible(false)}
        footer={null}
        width={700}
      >
        {currentStats && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Card title="📊 基线组（对照组）" size="small" style={{ borderColor: '#1677ff' }}>
                  <Statistic title="总事件" value={currentStats.baseline?.total || 0} />
                  <Statistic title="命中次数" value={currentStats.baseline?.hit || 0} valueStyle={{ color: '#1677ff' }} style={{ marginTop: 8 }} />
                  <Statistic title="命中率" value={Number(currentStats.baseline?.hitRate || 0).toFixed(2)} suffix="%" valueStyle={{ color: '#1677ff' }} style={{ marginTop: 8 }} />
                  <Row gutter={8} style={{ marginTop: 8 }}>
                    <Col span={6}><Statistic title="通过" value={currentStats.baseline?.pass || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="审核" value={currentStats.baseline?.review || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="拒绝" value={currentStats.baseline?.reject || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="阻断" value={currentStats.baseline?.block || 0} valueStyle={{ fontSize: 14 }} /></Col>
                  </Row>
                </Card>
              </Col>
              <Col span={12}>
                <Card title="🧪 实验组（新规则）" size="small" style={{ borderColor: '#52c41a' }}>
                  <Statistic title="总事件" value={currentStats.experimentGroup?.total || 0} />
                  <Statistic title="命中次数" value={currentStats.experimentGroup?.hit || 0} valueStyle={{ color: '#52c41a' }} style={{ marginTop: 8 }} />
                  <Statistic title="命中率" value={Number(currentStats.experimentGroup?.hitRate || 0).toFixed(2)} suffix="%" valueStyle={{ color: '#52c41a' }} style={{ marginTop: 8 }} />
                  <Row gutter={8} style={{ marginTop: 8 }}>
                    <Col span={6}><Statistic title="通过" value={currentStats.experimentGroup?.pass || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="审核" value={currentStats.experimentGroup?.review || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="拒绝" value={currentStats.experimentGroup?.reject || 0} valueStyle={{ fontSize: 14 }} /></Col>
                    <Col span={6}><Statistic title="阻断" value={currentStats.experimentGroup?.block || 0} valueStyle={{ fontSize: 14 }} /></Col>
                  </Row>
                </Card>
              </Col>
            </Row>

            {currentStats.hitRateDiff != null && (
              <Card size="small" style={{ marginTop: 16, borderColor: '#722ed1' }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title="命中率差异"
                      value={Number(currentStats.hitRateDiff).toFixed(2)}
                      suffix="%"
                      valueStyle={{ color: currentStats.hitRateDiff > 0 ? '#52c41a' : currentStats.hitRateDiff < 0 ? '#ff4d4f' : '#999' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic title="结论" value={currentStats.conclusion || '数据不足'} valueStyle={{ fontSize: 14 }} />
                  </Col>
                </Row>
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
