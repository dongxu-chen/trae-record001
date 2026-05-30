import { useState, useEffect } from 'react'
import { Card, Row, Col, Form, Input, Select, Button, Space, message, Divider, Tag, Spin, Alert } from 'antd'
import { PlayCircleOutlined, ClearOutlined } from '@ant-design/icons'
import { ruleApi } from '../services/api'

const { TextArea } = Input

const SAMPLE_EVENT = `{
  "eventId": "EVT_001",
  "eventType": "LOGIN",
  "userId": "user_12345",
  "ip": "192.168.1.100",
  "deviceId": "DEV_001",
  "timestamp": null,
  "payload": {
    "amount": 5000,
    "country": "CN",
    "loginCount": 3
  }
}`

export default function SimulateTest() {
  const [form] = Form.useForm()
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      const data = await ruleApi.getAll()
      setRules(data || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleSimulate = async () => {
    try {
      setLoading(true)
      setResult(null)
      const values = form.getFieldsValue()

      let event
      try {
        event = JSON.parse(values.eventJson)
      } catch (e) {
        message.error('事件 JSON 格式错误')
        return
      }

      const response = await ruleApi.simulate({
        ruleCode: values.ruleCode,
        event: event,
      })

      setResult(response)
      message.success('模拟测试完成')
    } catch (e) {
      message.error('模拟测试失败: ' + (e.response?.data?.message || e.message))
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    form.resetFields()
    setResult(null)
  }

  const getActionColor = (action) => {
    const map = { PASS: 'success', REVIEW: 'warning', REJECT: 'error', BLOCK: 'default' }
    return map[action] || 'default'
  }

  const getActionLabel = (action) => {
    const map = { PASS: '通过', REVIEW: '审核', REJECT: '拒绝', BLOCK: '阻断' }
    return map[action] || action
  }

  return (
    <Row gutter={16}>
      <Col xs={24} lg={14}>
        <Card title="模拟测试" extra={
          <Space>
            <Button icon={<ClearOutlined />} onClick={handleClear}>清空</Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={loading}
              onClick={handleSimulate}
            >
              执行测试
            </Button>
          </Space>
        }>
          <Form form={form} layout="vertical" initialValues={{ eventJson: SAMPLE_EVENT }}>
            <Form.Item name="ruleCode" label="选择规则" rules={[{ required: true, message: '请选择规则' }]}>
              <Select
                placeholder="选择要测试的规则"
                showSearch
                optionFilterProp="children"
                options={rules.map(r => ({
                  value: r.ruleCode,
                  label: `${r.ruleName} (${r.ruleCode})`,
                }))}
              />
            </Form.Item>

            <Form.Item name="eventJson" label="事件数据 (JSON)" rules={[{ required: true, message: '请输入事件数据' }]}>
              <TextArea
                rows={16}
                placeholder="输入风控事件 JSON 数据"
                style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 13, lineHeight: 1.6 }}
              />
            </Form.Item>
          </Form>
        </Card>
      </Col>

      <Col xs={24} lg={10}>
        <Card title="测试结果">
          {loading && (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin size="large" tip="执行中..." />
            </div>
          )}

          {!loading && !result && (
            <Alert
              type="info"
              message="选择规则并输入事件数据，点击执行测试查看结果"
              showIcon
            />
          )}

          {!loading && result && (
            <div>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 12, color: '#999' }}>决策动作</div>
                    <Tag
                      color={getActionColor(result.action)}
                      style={{ fontSize: 18, padding: '4px 16px', marginTop: 8 }}
                    >
                      {getActionLabel(result.action)}
                    </Tag>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 12, color: '#999' }}>风险分数</div>
                    <div style={{
                      fontSize: 28,
                      fontWeight: 'bold',
                      color: result.riskScore >= 200 ? '#ff4d4f' : result.riskScore >= 100 ? '#faad14' : '#52c41a',
                      marginTop: 4,
                    }}>
                      {result.riskScore}
                    </div>
                  </Card>
                </Col>
              </Row>

              <Divider orientation="left">命中规则</Divider>
              {result.hitRules && result.hitRules.length > 0 ? (
                <div>
                  {result.hitRules.map((rule, idx) => (
                    <Tag key={idx} color="blue" style={{ marginBottom: 4 }}>{rule}</Tag>
                  ))}
                </div>
              ) : (
                <span style={{ color: '#999' }}>未命中任何规则</span>
              )}

              <Divider orientation="left">风险标签</Divider>
              {result.riskTags && result.riskTags.length > 0 ? (
                <div>
                  {result.riskTags.map((tag, idx) => (
                    <Tag key={idx} color="red" style={{ marginBottom: 4 }}>{tag}</Tag>
                  ))}
                </div>
              ) : (
                <span style={{ color: '#999' }}>无风险标签</span>
              )}

              <Divider orientation="left">完整响应</Divider>
              <pre style={{
                background: '#1e1e1e',
                color: '#d4d4d4',
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                fontFamily: 'Consolas, Monaco, monospace',
                lineHeight: 1.6,
                maxHeight: 300,
                overflow: 'auto',
              }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      </Col>
    </Row>
  )
}
