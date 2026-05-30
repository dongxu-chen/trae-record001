import { useEffect, useState } from 'react'
import { Card, Form, Input, Select, InputNumber, Switch, Button, Space, Tabs, message, Row, Col } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { ruleApi } from '../services/api'

const { TextArea } = Input
const { TabPane } = Tabs

const GROOVY_TEMPLATE = `// Groovy 风控规则脚本
// 可用变量: event(RiskEvent), context(Map)
// 返回值: Boolean | Map[hit:Boolean, riskScore:Number, riskTags:List]

def userId = event.userId
def ip = event.ip

// 示例: IP黑名单检测
def blackIps = ['192.168.1.100', '10.0.0.1']
if (blackIps.contains(ip)) {
    return [hit: true, riskScore: 200, riskTags: ['IP黑名单']]
}

return [hit: false, riskScore: 0, riskTags: []]
`

const DROOLS_TEMPLATE = `package rules

import com.riskengine.model.RiskEvent
import com.riskengine.model.RiskDecision

global RiskDecision decision

rule "高风险IP检测"
    when
        $event : RiskEvent(ip == "192.168.1.100")
    then
        decision.getHitRules().add("高风险IP检测");
        decision.setRiskScore(decision.getRiskScore() + 200);
        decision.getRiskTags().add("IP黑名单");
end
`

export default function RuleEditor() {
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams()
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [activeTab, setActiveTab] = useState('groovy')
  const isEdit = !!id

  useEffect(() => {
    if (isEdit) {
      loadRule()
    } else {
      form.setFieldsValue({
        ruleType: 'GROOVY',
        priority: 100,
        enabled: true,
        groovyScript: GROOVY_TEMPLATE,
      })
    }
  }, [id])

  const loadRule = async () => {
    try {
      setLoading(true)
      const rule = await ruleApi.getByCode(id)
      if (rule) {
        form.setFieldsValue(rule)
        if (rule.groovyScript) setActiveTab('groovy')
        else if (rule.droolsDrl) setActiveTab('drools')
      }
    } catch (e) {
      message.error('加载规则失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (values) => {
    try {
      setLoading(true)
      if (isEdit) {
        await ruleApi.update(values.id, values)
        message.success('规则更新成功')
      } else {
        await ruleApi.create(values)
        message.success('规则创建成功')
      }
      navigate('/rules')
    } catch (e) {
      message.error(isEdit ? '更新失败' : '创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleValidate = async () => {
    try {
      setValidating(true)
      const values = form.getFieldsValue()
      if (activeTab === 'groovy' && values.groovyScript) {
        const result = await ruleApi.validateGroovy(values.groovyScript)
        if (result.valid) {
          message.success('Groovy 脚本语法验证通过')
        } else {
          message.error('Groovy 脚本语法错误')
        }
      } else if (activeTab === 'drools' && values.droolsDrl) {
        const result = await ruleApi.validateDrl(values.droolsDrl)
        if (result.valid) {
          message.success('Drools DRL 语法验证通过')
        } else {
          message.error('Drools DRL 语法错误')
        }
      } else {
        message.warning('请先填写脚本内容')
      }
    } catch (e) {
      message.error('验证失败')
    } finally {
      setValidating(false)
    }
  }

  return (
    <Card title={isEdit ? '编辑规则' : '新建规则'}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ ruleType: 'GROOVY', priority: 100, enabled: true }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="ruleCode" label="规则编码" rules={[{ required: true, message: '请输入规则编码' }]}>
              <Input placeholder="例如: IP_BLACKLIST_CHECK" disabled={isEdit} style={{ fontFamily: 'monospace' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="ruleName" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
              <Input placeholder="例如: IP黑名单检测" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item name="ruleType" label="规则类型" rules={[{ required: true }]}>
              <Select options={[
                { value: 'GROOVY', label: 'Groovy 脚本' },
                { value: 'DROOLS', label: 'Drools DRL' },
                { value: 'HYBRID', label: '混合模式' },
              ]} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item name="sceneCode" label="场景编码">
              <Input placeholder="例如: LOGIN, TRANSFER" />
            </Form.Item>
          </Col>
          <Col span={4}>
            <Form.Item name="priority" label="优先级">
              <InputNumber min={1} max={1000} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={4}>
            <Form.Item name="enabled" label="启用" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="description" label="规则描述">
          <TextArea rows={2} placeholder="描述规则的业务逻辑和触发条件" />
        </Form.Item>

        <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
          {
            key: 'groovy',
            label: 'Groovy 脚本',
            children: (
              <Form.Item name="groovyScript">
                <TextArea
                  rows={18}
                  placeholder="输入 Groovy 脚本..."
                  style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 13, lineHeight: 1.6 }}
                />
              </Form.Item>
            ),
          },
          {
            key: 'drools',
            label: 'Drools DRL',
            children: (
              <Form.Item name="droolsDrl">
                <TextArea
                  rows={18}
                  placeholder="输入 Drools DRL 规则..."
                  style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 13, lineHeight: 1.6 }}
                />
              </Form.Item>
            ),
          },
        ]} />

        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              {isEdit ? '更新规则' : '创建规则'}
            </Button>
            <Button onClick={handleValidate} loading={validating}>
              验证语法
            </Button>
            <Button onClick={() => navigate('/rules')}>取消</Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  )
}
