import React, { useState, useEffect } from 'react'
import {
  Table,
  Button,
  Drawer,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Tag,
  Modal,
  message,
  Popconfirm,
  Collapse,
  Descriptions,
  Empty,
  Badge,
  Typography,
  Row,
  Col,
  Alert,
  Checkbox,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EyeOutlined,
  DiffOutlined,
  RollbackOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import Editor from '@monaco-editor/react'

import { ruleApi, groupApi, promqlApi } from '../api/client'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select
const { Panel } = Collapse

function RulesPage() {
  const [rules, setRules] = useState([])
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [editingRule, setEditingRule] = useState(null)
  const [form] = Form.useForm()
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [versionsVisible, setVersionsVisible] = useState(false)
  const [versions, setVersions] = useState([])
  const [currentRule, setCurrentRule] = useState(null)
  const [validating, setValidating] = useState(false)
  const [exprValid, setExprValid] = useState(null)
  const [exprMessage, setExprMessage] = useState('')
  const [viewingRule, setViewingRule] = useState(null)
  const [compareVisible, setCompareVisible] = useState(false)
  const [compareResult, setCompareResult] = useState(null)
  const [comparingVersion, setComparingVersion] = useState(null)
  const [restoreConfirmVisible, setRestoreConfirmVisible] = useState(false)
  const [restoringVersion, setRestoringVersion] = useState(null)
  const [restoreConfirm, setRestoreConfirm] = useState(false)
  const [restoreChangeLog, setRestoreChangeLog] = useState('')
  const [restoreLoading, setRestoreLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [selectedGroup])

  const loadData = async () => {
    setLoading(true)
    try {
      const [rulesRes, groupsRes] = await Promise.all([
        ruleApi.list(selectedGroup),
        groupApi.list(),
      ])
      setRules(rulesRes.data)
      setGroups(groupsRes.data)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }

  const validateExpr = async (expr) => {
    if (!expr) return
    setValidating(true)
    try {
      const res = await promqlApi.validate(expr)
      setExprValid(res.data.valid)
      setExprMessage(res.data.message)
    } catch (error) {
      setExprValid(false)
      setExprMessage(error.response?.data?.error || '校验失败')
    } finally {
      setValidating(false)
    }
  }

  const handleCreate = () => {
    setEditingRule(null)
    form.resetFields()
    setExprValid(null)
    setExprMessage('')
    setDrawerVisible(true)
  }

  const handleEdit = (record) => {
    setEditingRule(record)
    form.setFieldsValue({
      ...record,
      labels: record.labels ? JSON.stringify(JSON.parse(record.labels), null, 2) : '',
      annotations: record.annotations ? JSON.stringify(JSON.parse(record.annotations), null, 2) : '',
    })
    setExprValid(null)
    setExprMessage('')
    setDrawerVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await ruleApi.delete(id)
      message.success('删除成功')
      loadData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values) => {
    try {
      if (editingRule) {
        await ruleApi.update(editingRule.id, values)
        message.success('更新成功')
      } else {
        await ruleApi.create(values)
        message.success('创建成功')
      }
      setDrawerVisible(false)
      loadData()
    } catch (error) {
      message.error(error.response?.data?.error || '操作失败')
    }
  }

  const handleViewVersions = async (record) => {
    setCurrentRule(record)
    try {
      const res = await ruleApi.listVersions(record.id)
      setVersions(res.data)
      setVersionsVisible(true)
    } catch (error) {
      message.error('加载版本历史失败')
    }
  }

  const handleCompare = async (versionId, version) => {
    setComparingVersion(version)
    setCompareVisible(true)
    try {
      const res = await ruleApi.compareVersions(currentRule.id, versionId)
      setCompareResult(res.data)
    } catch (error) {
      message.error('版本对比失败')
    }
  }

  const handleShowRestoreConfirm = (versionId, version) => {
    setRestoringVersion(version)
    setRestoreConfirm(false)
    setRestoreChangeLog('')
    setRestoreConfirmVisible(true)
  }

  const handleRestore = async () => {
    if (!restoreConfirm) {
      message.warning('请确认恢复操作')
      return
    }

    setRestoreLoading(true)
    try {
      const res = await ruleApi.restoreVersionWithConfirm(
        currentRule.id,
        restoringVersion.id,
        {
          confirm: true,
          change_log: restoreChangeLog,
        }
      )
      message.success(res.data.message || '版本恢复成功')
      setRestoreConfirmVisible(false)
      setVersionsVisible(false)
      loadData()
    } catch (error) {
      message.error(error.response?.data?.error || '恢复失败')
    } finally {
      setRestoreLoading(false)
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text, record) => (
        <Space>
          <span>{text}</span>
          {record.enabled ? (
            <Badge status="success" text="启用" />
          ) : (
            <Badge status="default" text="禁用" />
          )}
        </Space>
      ),
    },
    {
      title: '分组',
      dataIndex: ['group', 'name'],
      key: 'group',
      width: 120,
      render: (text) => <Tag color="blue">{text || '-'}</Tag>,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (text) => {
        const colors = {
          critical: 'red',
          warning: 'orange',
          info: 'blue',
        }
        return text ? <Tag color={colors[text]}>{text}</Tag> : '-'
      },
    },
    {
      title: 'PromQL 表达式',
      dataIndex: 'expr',
      key: 'expr',
      ellipsis: true,
      render: (text) => (
        <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>
          {text}
        </code>
      ),
    },
    {
      title: '持续时间',
      dataIndex: 'for',
      key: 'for',
      width: 100,
    },
    {
      title: '操作',
      key: 'actions',
      width: 240,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => setViewingRule(record)}
          >
            查看
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            icon={<HistoryOutlined />}
            onClick={() => handleViewVersions(record)}
          >
            版本
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div className="page-header">
        <Title level={3} className="page-title">告警规则管理</Title>
        <Space>
          <Select
            placeholder="选择分组筛选"
            style={{ width: 200 }}
            allowClear
            value={selectedGroup}
            onChange={setSelectedGroup}
          >
            {groups.map((g) => (
              <Option key={g.id} value={g.id}>
                {g.name}
              </Option>
            ))}
          </Select>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建规则
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={rules}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Drawer
        title={editingRule ? '编辑告警规则' : '新建告警规则'}
        width={720}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ enabled: true, severity: 'warning' }}
        >
          <Form.Item name="group_id" label="分组" rules={[{ required: true }]}>
            <Select placeholder="选择分组">
              {groups.map((g) => (
                <Option key={g.id} value={g.id}>
                  {g.name}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
            <Input placeholder="例如: HighCPUUsage" />
          </Form.Item>

          <Form.Item
            name="expr"
            label="PromQL 表达式"
            rules={[{ required: true }]}
            extra={
              <Space>
                {validating && <span>校验中...</span>}
                {!validating && exprValid === true && (
                  <span style={{ color: '#52c41a' }}>
                    <CheckCircleOutlined /> {exprMessage}
                  </span>
                )}
                {!validating && exprValid === false && (
                  <span style={{ color: '#ff4d4f' }}>
                    <CloseCircleOutlined /> {exprMessage}
                  </span>
                )}
              </Space>
            }
          >
            <div className="monaco-editor-container">
              <Editor
                height="150px"
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
                value={form.getFieldValue('expr')}
              />
            </div>
          </Form.Item>

          <Space style={{ width: '100%', display: 'flex' }}>
            <Form.Item name="for" label="持续时间" style={{ flex: 1 }}>
              <Input placeholder="例如: 5m" />
            </Form.Item>

            <Form.Item name="severity" label="严重程度" style={{ flex: 1 }}>
              <Select>
                <Option value="critical">Critical (严重)</Option>
                <Option value="warning">Warning (警告)</Option>
                <Option value="info">Info (信息)</Option>
              </Select>
            </Form.Item>

            <Form.Item name="enabled" label="启用" valuePropName="checked" style={{ flex: 1 }}>
              <Switch />
            </Form.Item>
          </Space>

          <Form.Item name="summary" label="摘要">
            <Input placeholder="简短描述告警内容" />
          </Form.Item>

          <Form.Item name="description" label="详细描述">
            <TextArea rows={3} placeholder="详细的告警描述和处理建议" />
          </Form.Item>

          <Form.Item name="labels" label="标签 (JSON格式)">
            <div className="monaco-editor-container">
              <Editor
                height="100px"
                defaultLanguage="json"
                theme="vs-light"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
                onChange={(value) => form.setFieldsValue({ labels: value })}
                value={form.getFieldValue('labels')}
              />
            </div>
          </Form.Item>

          <Form.Item name="annotations" label="注解 (JSON格式)">
            <div className="monaco-editor-container">
              <Editor
                height="100px"
                defaultLanguage="json"
                theme="vs-light"
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                }}
                onChange={(value) => form.setFieldsValue({ annotations: value })}
                value={form.getFieldValue('annotations')}
              />
            </div>
          </Form.Item>

          <Form.Item name="change_log" label="变更说明">
            <Input placeholder="描述本次修改内容" />
          </Form.Item>

          <Form.Item style={{ marginTop: 24, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setDrawerVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingRule ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title={
          <Space>
            <HistoryOutlined />
            版本历史
            <Tag color="blue">{currentRule?.name}</Tag>
          </Space>
        }
        open={versionsVisible}
        onCancel={() => setVersionsVisible(false)}
        width={900}
        footer={null}
      >
        {versions.length === 0 ? (
          <Empty description="暂无版本历史" />
        ) : (
          <div>
            <Alert
              message="版本管理说明"
              description="点击「对比」可查看与当前版本的差异，点击「恢复」可将规则回滚到历史版本。恢复操作会自动创建新版本记录。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Collapse defaultActiveKey={[0]}>
              {versions.map((v, idx) => (
                <Panel
                  header={
                    <Space>
                      <Tag color={idx === 0 ? 'green' : 'blue'}>
                        v{v.version}
                        {idx === 0 && ' (当前)'}
                      </Tag>
                      <span>{new Date(v.created_at).toLocaleString()}</span>
                      {v.change_log && (
                        <Text type="secondary">- {v.change_log}</Text>
                      )}
                    </Space>
                  }
                  key={idx}
                  extra={
                    idx > 0 && (
                      <Space size="small" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="small"
                          icon={<DiffOutlined />}
                          onClick={() => handleCompare(v.id, v)}
                        >
                          对比
                        </Button>
                        <Button
                          size="small"
                          type="primary"
                          danger
                          icon={<RollbackOutlined />}
                          onClick={() => handleShowRestoreConfirm(v.id, v)}
                        >
                          恢复此版本
                        </Button>
                      </Space>
                    )
                  }
                >
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="名称">{v.name}</Descriptions.Item>
                    <Descriptions.Item label="严重程度">
                      {v.severity ? <Tag>{v.severity}</Tag> : '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="表达式" span={2}>
                      <pre
                        style={{
                          background: '#f5f5f5',
                          padding: '8px 12px',
                          borderRadius: 4,
                          margin: 0,
                          fontSize: 12,
                        }}
                      >
                        {v.expr}
                      </pre>
                    </Descriptions.Item>
                    <Descriptions.Item label="持续时间">
                      {v.for || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="摘要">{v.summary || '-'}</Descriptions.Item>
                    <Descriptions.Item label="描述" span={2}>
                      {v.description || '-'}
                    </Descriptions.Item>
                    {v.labels && (
                      <Descriptions.Item label="标签" span={2}>
                        <pre
                          style={{
                            background: '#f5f5f5',
                            padding: '8px 12px',
                            borderRadius: 4,
                            margin: 0,
                            fontSize: 12,
                            maxHeight: 100,
                            overflow: 'auto',
                          }}
                        >
                          {v.labels}
                        </pre>
                      </Descriptions.Item>
                    )}
                    {v.annotations && (
                      <Descriptions.Item label="注解" span={2}>
                        <pre
                          style={{
                            background: '#f5f5f5',
                            padding: '8px 12px',
                            borderRadius: 4,
                            margin: 0,
                            fontSize: 12,
                            maxHeight: 100,
                            overflow: 'auto',
                          }}
                        >
                          {v.annotations}
                        </pre>
                      </Descriptions.Item>
                    )}
                  </Descriptions>
                </Panel>
              ))}
            </Collapse>
          </div>
        )}
      </Modal>

      <Modal
        title={
          <Space>
            <DiffOutlined />
            版本对比
          </Space>
        }
        open={compareVisible}
        onCancel={() => setCompareVisible(false)}
        width={1000}
        footer={[
          <Button key="close" onClick={() => setCompareVisible(false)}>
            关闭
          </Button>,
          comparingVersion && (
            <Button
              key="restore"
              type="primary"
              danger
              icon={<RollbackOutlined />}
              onClick={() => {
                setCompareVisible(false)
                handleShowRestoreConfirm(comparingVersion.id, comparingVersion)
              }}
            >
              恢复到此版本
            </Button>
          ),
        ]}
      >
        {compareResult ? (
          <div>
            <Alert
              message={
                <Space>
                  <span>
                    当前版本: <Tag color="green">v{compareResult.current_version}</Tag>
                  </span>
                  <span>
                    → 目标版本: <Tag color="orange">v{compareResult.target_version}</Tag>
                  </span>
                  <span>
                    变更数: <Tag color={compareResult.change_count > 0 ? 'red' : 'green'}>
                      {compareResult.change_count} 处
                    </Tag>
                  </span>
                </Space>
              }
              description="绿色表示未变化，红色表示有变更"
              type={compareResult.change_count > 0 ? 'warning' : 'success'}
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Row gutter={16}>
              <Col span={12}>
                <Card
                  title={<Text strong>当前版本 (v{compareResult.current_version})</Text>}
                  size="small"
                  type="inner"
                >
                  {compareResult.differences.map((diff, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '8px 12px',
                        marginBottom: 4,
                        borderRadius: 4,
                        background: diff.Changed ? '#fff1f0' : '#f6ffed',
                        border: `1px solid ${diff.Changed ? '#ffccc7' : '#b7eb8f'}`,
                      }}
                    >
                      <Text strong>{diff.field}:</Text>
                      <div
                        style={{
                          fontFamily: 'monospace',
                          wordBreak: 'break-all',
                          marginTop: 4,
                          color: diff.Changed ? '#ff4d4f' : '#52c41a',
                        }}
                      >
                        {diff.old_value || '(空)'}
                      </div>
                    </div>
                  ))}
                </Card>
              </Col>
              <Col span={12}>
                <Card
                  title={<Text strong>目标版本 (v{compareResult.target_version})</Text>}
                  size="small"
                  type="inner"
                >
                  {compareResult.differences.map((diff, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '8px 12px',
                        marginBottom: 4,
                        borderRadius: 4,
                        background: diff.Changed ? '#fff1f0' : '#f6ffed',
                        border: `1px solid ${diff.Changed ? '#ffccc7' : '#b7eb8f'}`,
                      }}
                    >
                      <Text strong>{diff.field}:</Text>
                      <div
                        style={{
                          fontFamily: 'monospace',
                          wordBreak: 'break-all',
                          marginTop: 4,
                          color: diff.Changed ? '#ff4d4f' : '#52c41a',
                        }}
                      >
                        {diff.new_value || '(空)'}
                      </div>
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>
          </div>
        ) : (
          <Empty description="加载对比数据中..." />
        )}
      </Modal>

      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
            确认恢复版本
          </Space>
        }
        open={restoreConfirmVisible}
        onCancel={() => setRestoreConfirmVisible(false)}
        width={600}
        footer={[
          <Button key="cancel" onClick={() => setRestoreConfirmVisible(false)}>
            取消
          </Button>,
          <Button
            key="confirm"
            type="primary"
            danger
            loading={restoreLoading}
            disabled={!restoreConfirm}
            onClick={handleRestore}
            icon={<RollbackOutlined />}
          >
            确认恢复
          </Button>,
        ]}
      >
        {restoringVersion && (
          <div>
            <Alert
              message="此操作将恢复规则到以下历史版本"
              description={
                <div>
                  <div>
                    <Text strong>版本: </Text>
                    <Tag color="orange">v{restoringVersion.version}</Tag>
                  </div>
                  <div>
                    <Text strong>创建时间: </Text>
                    {new Date(restoringVersion.created_at).toLocaleString()}
                  </div>
                  <div>
                    <Text strong>规则名称: </Text>
                    {restoringVersion.name}
                  </div>
                  <div>
                    <Text strong>表达式: </Text>
                    <code>{restoringVersion.expr}</code>
                  </div>
                </div>
              }
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="影响">
                <Text type="warning">
                  恢复操作会将当前规则的所有字段替换为历史版本，并创建新版本记录当前状态。
                </Text>
              </Descriptions.Item>
            </Descriptions>

            <Form.Item label="变更说明">
              <TextArea
                value={restoreChangeLog}
                onChange={(e) => setRestoreChangeLog(e.target.value)}
                placeholder="请输入本次恢复的原因或说明（可选）"
                rows={3}
              />
            </Form.Item>

            <Checkbox
              checked={restoreConfirm}
              onChange={(e) => setRestoreConfirm(e.target.checked)}
            >
              我确认要将规则恢复到 v{restoringVersion.version} 版本
            </Checkbox>
          </div>
        )}
      </Modal>

      <Modal
        title="规则详情"
        open={!!viewingRule}
        onCancel={() => setViewingRule(null)}
        width={800}
        footer={null}
      >
        {viewingRule && (
          <Descriptions column={1}>
            <Descriptions.Item label="名称">{viewingRule.name}</Descriptions.Item>
            <Descriptions.Item label="分组">{viewingRule.group?.name || '-'}</Descriptions.Item>
            <Descriptions.Item label="严重程度">
              {viewingRule.severity && <Tag>{viewingRule.severity}</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="表达式">
              <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, overflow: 'auto' }}>
                {viewingRule.expr}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="持续时间">{viewingRule.for || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              {viewingRule.enabled ? <Badge status="success" text="已启用" /> : <Badge status="default" text="已禁用" />}
            </Descriptions.Item>
            <Descriptions.Item label="摘要">{viewingRule.summary || '-'}</Descriptions.Item>
            <Descriptions.Item label="描述">{viewingRule.description || '-'}</Descriptions.Item>
            {viewingRule.labels && (
              <Descriptions.Item label="标签">
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(JSON.parse(viewingRule.labels), null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            {viewingRule.annotations && (
              <Descriptions.Item label="注解">
                <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                  {JSON.stringify(JSON.parse(viewingRule.annotations), null, 2)}
                </pre>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="创建时间">
              {new Date(viewingRule.created_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {new Date(viewingRule.updated_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default RulesPage
