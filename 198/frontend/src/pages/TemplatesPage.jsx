import { useState, useEffect } from 'react'
import {
  Card,
  Tag,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Button,
  Modal,
  Descriptions,
  List,
  Tabs,
  Input,
  Select,
  Form,
  message,
  Divider,
  Tooltip,
  Alert,
} from 'antd'
import {
  AppstoreOutlined,
  ThunderboltOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  ApiOutlined,
  SecurityScanOutlined,
  ServerOutlined,
  FileTextOutlined,
  CheckOutlined,
  CopyOutlined,
  ImportOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { templateApi, groupApi, promqlApi } from '../api/client'

const { Title, Text, Paragraph } = Typography
const { Search } = Input
const { Option } = Select
const { TabPane } = Tabs

const categoryIcons = {
  infra: <ServerOutlined />,
  app: <ApiOutlined />,
  database: <DatabaseOutlined />,
  k8s: <CloudServerOutlined />,
  network: <SafetyOutlined />,
  security: <SecurityScanOutlined />,
}

const complexityColors = {
  low: 'green',
  medium: 'gold',
  high: 'orange',
  critical: 'red',
}

const severityColors = {
  warning: 'gold',
  critical: 'red',
  info: 'blue',
}

export default function TemplatesPage() {
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState(null)
  const [detailModal, setDetailModal] = useState(false)
  const [applyModal, setApplyModal] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchText, setSearchText] = useState('')
  const [groups, setGroups] = useState([])
  const [form] = Form.useForm()
  const [validationResult, setValidationResult] = useState(null)
  const [validating, setValidating] = useState(false)

  const fetchTemplates = async () => {
    setLoading(true)
    try {
      const res = await templateApi.list()
      setTemplates(res.data)
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchGroups = async () => {
    try {
      const res = await groupApi.list()
      setGroups(res.data)
    } catch (err) {
      console.error('Failed to fetch groups:', err)
    }
  }

  const validateExpr = async (expr) => {
    setValidating(true)
    try {
      const res = await promqlApi.validate(expr)
      setValidationResult(res.data)
    } catch (err) {
      setValidationResult({ valid: false, error: err.message })
    } finally {
      setValidating(false)
    }
  }

  useEffect(() => {
    fetchTemplates()
    fetchGroups()
  }, [])

  useEffect(() => {
    if (selectedTemplate) {
      validateExpr(selectedTemplate.expr)
    }
  }, [selectedTemplate])

  const handleApply = async (values) => {
    try {
      const res = await templateApi.apply(selectedTemplate.id, values)
      message.success(`成功创建规则: ${res.data.rule.name}`)
      setApplyModal(false)
      form.resetFields()
    } catch (err) {
      message.error('创建规则失败: ' + err.message)
    }
  }

  const handleApplyCategory = async (categoryId) => {
    Modal.confirm({
      title: '批量应用模板',
      content: `确定要应用该分类下的所有模板吗？将创建 ${templates.categories.find((c) => c.id === categoryId)?.count} 条规则。`,
      onOk: async () => {
        try {
          const values = form.getFieldsValue()
          const res = await templateApi.applyCategory(categoryId, values)
          message.success(`成功创建 ${res.data.created_count} 条规则`)
        } catch (err) {
          message.error('批量创建失败: ' + err.message)
        }
      },
    })
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  }

  const filteredTemplates = () => {
    if (!templates?.categories) return []

    const search = searchText.toLowerCase()
    return templates.categories
      .filter((cat) => selectedCategory === 'all' || cat.id === selectedCategory)
      .map((cat) => ({
        ...cat,
        templates: cat.templates.filter(
          (t) =>
            t.name.toLowerCase().includes(search) ||
            t.description.toLowerCase().includes(search) ||
            t.tags?.some((tag) => tag.toLowerCase().includes(search))
        ),
      }))
      .filter((cat) => cat.templates.length > 0)
  }

  const renderTemplateCard = (template, categoryId) => (
    <Card
      key={template.id}
      size="small"
      style={{ marginBottom: 16 }}
      hoverable
      actions={[
        <Tooltip title="查看详情">
          <Button
            type="text"
            icon={<FileTextOutlined />}
            onClick={() => {
              setSelectedTemplate(template)
              setDetailModal(true)
            }}
          />
        </Tooltip>,
        <Tooltip title="使用此模板">
          <Button
            type="text"
            icon={<ImportOutlined />}
            onClick={() => {
              setSelectedTemplate(template)
              setApplyModal(true)
            }}
          />
        </Tooltip>,
      ]}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Text strong style={{ fontSize: 15 }}>
            {template.name}
          </Text>
          <Space>
            <Tag color={severityColors[template.severity]}>{template.severity}</Tag>
            <Tag color={complexityColors[template.estimated_complexity]}>
              {template.estimated_complexity}
            </Tag>
          </Space>
        </Space>

        <Text type="secondary" style={{ fontSize: 13 }}>
          {template.description}
        </Text>

        <div
          style={{
            backgroundColor: '#f6f8fa',
            padding: 8,
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={template.expr}
        >
          {template.expr}
        </div>

        <Space wrap>
          {template.tags?.map((tag) => (
            <Tag key={tag} color="blue">
              #{tag}
            </Tag>
          ))}
          <Tag color="default">{template.for}</Tag>
        </Space>
      </Space>
    </Card>
  )

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <AppstoreOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                <div>
                  <Title level={3} style={{ margin: 0 }}>
                    规则模板市场
                  </Title>
                  <Text type="secondary">
                    内置常见监控规则模板，一键应用快速搭建监控体系
                  </Text>
                </div>
              </Space>
              <Search
                placeholder="搜索模板名称、描述或标签..."
                allowClear
                style={{ width: 300 }}
                onSearch={setSearchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
            </Space>

            {templates && (
              <Row gutter={16}>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="模板分类"
                      value={templates.total_categories}
                      prefix={<AppstoreOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="模板总数"
                      value={templates.total_templates}
                      prefix={<ThunderboltOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="基础设施"
                      value={templates.categories?.find((c) => c.id === 'infra')?.count || 0}
                      prefix={<ServerOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="应用服务"
                      value={templates.categories?.find((c) => c.id === 'app')?.count || 0}
                      prefix={<ApiOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="Kubernetes"
                      value={templates.categories?.find((c) => c.id === 'k8s')?.count || 0}
                      prefix={<CloudServerOutlined />}
                    />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card>
                    <Statistic
                      title="数据库"
                      value={templates.categories?.find((c) => c.id === 'database')?.count || 0}
                      prefix={<DatabaseOutlined />}
                    />
                  </Card>
                </Col>
              </Row>
            )}

            <Space wrap>
              <Select
                value={selectedCategory}
                onChange={setSelectedCategory}
                style={{ width: 150 }}
              >
                <Option value="all">全部分类</Option>
                {templates?.categories?.map((cat) => (
                  <Option key={cat.id} value={cat.id}>
                    {categoryIcons[cat.id]} {cat.name} ({cat.count})
                  </Option>
                ))}
              </Select>

              <Text type="secondary">共 {templates?.total_templates} 个模板</Text>
            </Space>
          </Space>
        </Card>

        <Tabs
          activeKey={selectedCategory === 'all' ? 'all' : selectedCategory}
          onChange={(key) => setSelectedCategory(key)}
          type="card"
        >
          <TabPane
            tab={
              <Space>
                <AppstoreOutlined />
                全部
              </Space>
            }
            key="all"
          >
            {filteredTemplates().map((category) => (
              <Card
                key={category.id}
                title={
                  <Space>
                    {categoryIcons[category.id]}
                    {category.name}
                    <Tag>{category.templates.length} 个模板</Tag>
                  </Space>
                }
                extra={
                  <Button
                    type="primary"
                    size="small"
                    onClick={() => handleApplyCategory(category.id)}
                  >
                    批量应用
                  </Button>
                }
                style={{ marginBottom: 16 }}
              >
                <Row gutter={16}>
                  {category.templates.map((template) => (
                    <Col span={8} key={template.id}>
                      {renderTemplateCard(template, category.id)}
                    </Col>
                  ))}
                </Row>
              </Card>
            ))}
          </TabPane>

          {templates?.categories?.map((category) => (
            <TabPane
              key={category.id}
              tab={
                <Space>
                  {categoryIcons[category.id]}
                  {category.name}
                  <Tag>{category.count}</Tag>
                </Space>
              }
            >
              <Card
                title={
                  <Space>
                    {categoryIcons[category.id]}
                    {category.name}
                    <Tag>{category.templates.length} 个模板</Tag>
                  </Space>
                }
                extra={
                  <Space>
                    <Text type="secondary">{category.description}</Text>
                    <Button
                      type="primary"
                      onClick={() => handleApplyCategory(category.id)}
                    >
                      批量应用全部
                    </Button>
                  </Space>
                }
              >
                <Row gutter={16}>
                  {category.templates
                    .filter((t) => {
                      if (!searchText) return true
                      const search = searchText.toLowerCase()
                      return (
                        t.name.toLowerCase().includes(search) ||
                        t.description.toLowerCase().includes(search) ||
                        t.tags?.some((tag) => tag.toLowerCase().includes(search))
                      )
                    })
                    .map((template) => (
                      <Col span={8} key={template.id}>
                        {renderTemplateCard(template, category.id)}
                      </Col>
                    ))}
                </Row>
              </Card>
            </TabPane>
          ))}
        </Tabs>
      </Space>

      <Modal
        title={
          <Space>
            <FileTextOutlined />
            {selectedTemplate?.name}
          </Space>
        }
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        width={900}
        footer={[
          <Button
            key="copy"
            icon={<CopyOutlined />}
            onClick={() => copyToClipboard(selectedTemplate?.expr)}
          >
            复制表达式
          </Button>,
          <Button
            key="apply"
            type="primary"
            icon={<ImportOutlined />}
            onClick={() => {
              setDetailModal(false)
              setApplyModal(true)
            }}
          >
            使用此模板
          </Button>,
          <Button key="close" onClick={() => setDetailModal(false)}>
            关闭
          </Button>,
        ]}
      >
        {selectedTemplate && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={severityColors[selectedTemplate.severity]}>
                级别: {selectedTemplate.severity}
              </Tag>
              <Tag color={complexityColors[selectedTemplate.estimated_complexity]}>
                复杂度: {selectedTemplate.estimated_complexity}
              </Tag>
              <Tag color="blue">持续时间: {selectedTemplate.for}</Tag>
              {selectedTemplate.tags?.map((tag) => (
                <Tag key={tag} color="purple">
                  #{tag}
                </Tag>
              ))}
            </Space>

            <Alert
              message="模板说明"
              description={selectedTemplate.description}
              type="info"
              showIcon
            />

            <Card
              title={
                <Space>
                  <InfoCircleOutlined />
                  PromQL 表达式
                  <Space>
                    {validating && <span style={{ color: '#faad14' }}>验证中...</span>}
                    {validationResult && !validating && (
                      <Tag color={validationResult.valid ? 'green' : 'red'}>
                        {validationResult.valid ? <CheckOutlined /> : <InfoCircleOutlined />}
                        {validationResult.valid ? '语法正确' : '语法错误'}
                      </Tag>
                    )}
                  </Space>
                </Space>
              }
              extra={
                <Button
                  type="text"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard(selectedTemplate.expr)}
                >
                  复制
                </Button>
              }
            >
              <Paragraph
                style={{
                  fontFamily: 'monospace',
                  backgroundColor: '#f6f8fa',
                  padding: 16,
                  borderRadius: 4,
                  margin: 0,
                  wordBreak: 'break-all',
                }}
              >
                {selectedTemplate.expr}
              </Paragraph>
            </Card>

            <Descriptions title="规则配置" bordered column={2}>
              <Descriptions.Item label="规则名称">
                {selectedTemplate.name}
              </Descriptions.Item>
              <Descriptions.Item label="告警级别">
                <Tag color={severityColors[selectedTemplate.severity]}>
                  {selectedTemplate.severity}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="持续时间">
                {selectedTemplate.for}
              </Descriptions.Item>
              <Descriptions.Item label="复杂度">
                <Tag color={complexityColors[selectedTemplate.estimated_complexity]}>
                  {selectedTemplate.estimated_complexity}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="摘要模板" span={2}>
                {selectedTemplate.summary}
              </Descriptions.Item>
              <Descriptions.Item label="描述模板" span={2}>
                {selectedTemplate.description_template}
              </Descriptions.Item>
            </Descriptions>

            {selectedTemplate.labels && Object.keys(selectedTemplate.labels).length > 0 && (
              <Card title="默认标签" size="small">
                <List
                  dataSource={Object.entries(selectedTemplate.labels)}
                  renderItem={([key, value]) => (
                    <List.Item>
                      <Space>
                        <Tag color="blue">{key}</Tag>
                        <Text code>{value}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {selectedTemplate.annotations && Object.keys(selectedTemplate.annotations).length > 0 && (
              <Card title="默认注解" size="small">
                <List
                  dataSource={Object.entries(selectedTemplate.annotations)}
                  renderItem={([key, value]) => (
                    <List.Item>
                      <Space>
                        <Tag color="purple">{key}</Tag>
                        <Text>{value}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {selectedTemplate.use_cases?.length > 0 && (
              <Card title="适用场景" size="small">
                <List
                  dataSource={selectedTemplate.use_cases}
                  renderItem={(item) => (
                    <List.Item>
                      <CheckOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              </Card>
            )}

            <Text type="secondary">贡献者: {selectedTemplate.contributor}</Text>
          </Space>
        )}
      </Modal>

      <Modal
        title={
          <Space>
            <ImportOutlined />
            应用模板: {selectedTemplate?.name}
          </Space>
        }
        open={applyModal}
        onCancel={() => {
          setApplyModal(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleApply}>
          <Form.Item
            name="group_id"
            label="目标分组"
            rules={[{ required: true, message: '请选择分组' }]}
          >
            <Select placeholder="选择规则分组">
              {groups.map((group) => (
                <Option key={group.id} value={group.id}>
                  {group.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="prefix" label="名称前缀">
            <Input placeholder="可选：为规则名称添加前缀，如 [生产环境]" />
          </Form.Item>

          <Divider />

          <Alert
            message="模板信息"
            description={
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text>
                  <strong>表达式:</strong>
                </Text>
                <Text
                  code
                  style={{
                    backgroundColor: '#f6f8fa',
                    padding: 8,
                    borderRadius: 4,
                    width: '100%',
                    wordBreak: 'break-all',
                  }}
                >
                  {selectedTemplate?.expr}
                </Text>
                <Text>
                  <strong>持续时间:</strong> {selectedTemplate?.for}
                </Text>
                <Text>
                  <strong>级别:</strong>{' '}
                  <Tag color={severityColors[selectedTemplate?.severity]}>
                    {selectedTemplate?.severity}
                  </Tag>
                </Text>
              </Space>
            }
            type="info"
            showIcon
          />
        </Form>
      </Modal>
    </div>
  )
}
