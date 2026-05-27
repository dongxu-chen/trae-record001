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
  Select,
  Statistic,
  message,
  Modal,
  Form,
  Upload,
  Drawer,
  Descriptions,
  Tabs,
  Popconfirm,
} from 'antd'
import {
  ReloadOutlined,
  CloudDownloadOutlined,
  UploadOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  HistoryOutlined,
  SafetyOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  QuestionCircleOutlined,
  ExportOutlined,
  ImportOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const { TextArea } = Input
const { TabPane } = Tabs

const RuleLibrary = () => {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(false)
  const [ruleType, setRuleType] = useState('')
  const [version, setVersion] = useState('')
  const [addModal, setAddModal] = useState(false)
  const [editModal, setEditModal] = useState(false)
  const [currentRule, setCurrentRule] = useState(null)
  const [logs, setLogs] = useState([])
  const [logsTotal, setLogsTotal] = useState(0)
  const [logsPage, setLogsPage] = useState(1)
  const [detailDrawer, setDetailDrawer] = useState(false)

  const [addForm] = Form.useForm()
  const [editForm] = Form.useForm()

  useEffect(() => {
    fetchRules()
    fetchVersion()
  }, [ruleType])

  useEffect(() => {
    fetchLogs()
  }, [logsPage])

  const fetchRules = async () => {
    setLoading(true)
    try {
      const res = await api.getRules({ type: ruleType })
      setRules(res.data)
    } catch (error) {
      message.error('获取规则失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchVersion = async () => {
    try {
      const res = await api.getRuleVersion()
      setVersion(res.data.version)
    } catch (error) {
      console.error('获取版本失败:', error)
    }
  }

  const fetchLogs = async () => {
    try {
      const res = await api.getRuleUpdateLogs({
        page: logsPage,
        page_size: 10,
      })
      setLogs(res.data.logs)
      setLogsTotal(res.data.total)
    } catch (error) {
      console.error('获取更新日志失败:', error)
    }
  }

  const handleUpdateRules = async () => {
    try {
      message.loading({ content: '正在更新规则库...', key: 'update' })
      const res = await api.updateRules()
      message.success({
        content: `更新成功: 新增${res.data.added_rules}条, 更新${res.data.updated_rules}条`,
        key: 'update',
      })
      fetchRules()
      fetchVersion()
      fetchLogs()
    } catch (error) {
      message.error({ content: error.message || '更新失败', key: 'update' })
    }
  }

  const handleAdd = async () => {
    try {
      const values = await addForm.validateFields()
      await api.addRule(values)
      message.success('添加成功')
      setAddModal(false)
      addForm.resetFields()
      fetchRules()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '添加失败')
    }
  }

  const handleEdit = async () => {
    try {
      const values = await editForm.validateFields()
      await api.updateRule(currentRule.id, values)
      message.success('更新成功')
      setEditModal(false)
      fetchRules()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '更新失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteRule(id)
      message.success('删除成功')
      fetchRules()
    } catch (error) {
      message.error(error.message || '删除失败')
    }
  }

  const handleImportRules = async (info) => {
    try {
      const formData = new FormData()
      formData.append('file', info.file)
      const res = await api.importRules(formData)
      message.success(`导入成功: ${res.data.count}条规则`)
      fetchRules()
      fetchVersion()
    } catch (error) {
      message.error('导入失败: ' + error.message)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      secure: 'green',
      acceptable: 'blue',
      weak: 'orange',
      insecure: 'red',
      unknown: 'default',
    }
    return colors[status] || 'default'
  }

  const getStatusText = (status) => {
    const texts = {
      secure: '安全',
      acceptable: '可接受',
      weak: '较弱',
      insecure: '不安全',
      unknown: '未知',
    }
    return texts[status] || status
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'secure':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case 'acceptable':
        return <QuestionCircleOutlined style={{ color: '#1890ff' }} />
      case 'weak':
        return <WarningOutlined style={{ color: '#faad14' }} />
      case 'insecure':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      default:
        return <QuestionCircleOutlined />
    }
  }

  const getRuleTypeColor = (type) => {
    const colors = {
      signature: 'purple',
      public_key: 'cyan',
    }
    return colors[type] || 'default'
  }

  const getRuleTypeText = (type) => {
    const texts = {
      signature: '签名算法',
      public_key: '公钥算法',
    }
    return texts[type] || type
  }

  const columns = [
    {
      title: '算法',
      dataIndex: 'algorithm',
      key: 'algorithm',
      render: (text, record) => (
        <a onClick={() => {
          setCurrentRule(record)
          setDetailDrawer(true)
        }}>
          {text}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 100,
      render: (text) => <Tag color={getRuleTypeColor(text)}>{getRuleTypeText(text)}</Tag>,
    },
    {
      title: '安全状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Space>
          {getStatusIcon(status)}
          <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
        </Space>
      ),
    },
    {
      title: '最小密钥位',
      dataIndex: 'min_bits',
      key: 'min_bits',
      width: 100,
      render: (val) => (val > 0 ? `${val}位` : '-'),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      render: (text) => {
        const colors = {
          default: 'blue',
          remote: 'green',
          custom: 'orange',
          imported: 'purple',
          local: 'cyan',
        }
        return <Tag color={colors[text] || 'default'}>{text}</Tag>
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 120,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          {record.source === 'custom' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => {
                  setCurrentRule(record)
                  editForm.setFieldsValue(record)
                  setEditModal(true)
                }}
              />
              <Popconfirm
                title="确定删除该规则？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  const logColumns = [
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: '总规则数',
      dataIndex: 'total_rules',
      key: 'total_rules',
    },
    {
      title: '新增',
      dataIndex: 'added_rules',
      key: 'added_rules',
      render: (val) => val > 0 ? <Tag color="green">+{val}</Tag> : '0',
    },
    {
      title: '更新',
      dataIndex: 'updated_rules',
      key: 'updated_rules',
      render: (val) => val > 0 ? <Tag color="blue">{val}</Tag> : '0',
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (text) => (
        <Tag color={text === 'success' ? 'green' : 'red'}>
          {text === 'success' ? '成功' : text}
        </Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
  ]

  const secureCount = rules.filter(r => r.status === 'secure').length
  const weakCount = rules.filter(r => r.status === 'weak').length
  const insecureCount = rules.filter(r => r.status === 'insecure').length

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="规则总数"
              value={rules.length}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="安全算法"
              value={secureCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="不安全/弱算法"
              value={weakCount + insecureCount}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Tag color="blue">当前版本: {version}</Tag>
            <Select
              placeholder="类型筛选"
              value={ruleType || undefined}
              onChange={setRuleType}
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value="signature">签名算法</Select.Option>
              <Select.Option value="public_key">公钥算法</Select.Option>
            </Select>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Space>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setAddModal(true)}
            >
              自定义规则
            </Button>
            <Upload
              accept=".json"
              showUploadList={false}
              customRequest={handleImportRules}
            >
              <Button icon={<ImportOutlined />}>导入规则</Button>
            </Upload>
            <Button
              icon={<ExportOutlined />}
              onClick={() => api.exportRules()}
            >
              导出规则
            </Button>
            <Button
              type="primary"
              icon={<CloudDownloadOutlined />}
              onClick={handleUpdateRules}
            >
              更新规则库
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchRules}
            >
              刷新
            </Button>
          </Space>
        </Col>
      </Row>

      <Tabs defaultActiveKey="1">
        <TabPane tab="规则列表" key="1">
          <Table
            columns={columns}
            dataSource={rules}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
          />
        </TabPane>
        <TabPane tab={<span><HistoryOutlined /> 更新日志</span>} key="2">
          <Table
            columns={logColumns}
            dataSource={logs}
            rowKey="id"
            pagination={{
              current: logsPage,
              pageSize: 10,
              total: logsTotal,
              showSizeChanger: true,
              onChange: (p) => setLogsPage(p),
            }}
          />
        </TabPane>
      </Tabs>

      <Modal
        title="添加自定义规则"
        open={addModal}
        onOk={handleAdd}
        onCancel={() => {
          setAddModal(false)
          addForm.resetFields()
        }}
      >
        <Form form={addForm} layout="vertical">
          <Form.Item
            name="algorithm"
            label="算法名称"
            rules={[{ required: true, message: '请输入算法名称' }]}
          >
            <Input placeholder="例如: RSA" />
          </Form.Item>
          <Form.Item
            name="rule_type"
            label="规则类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select>
              <Select.Option value="signature">签名算法</Select.Option>
              <Select.Option value="public_key">公钥算法</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="status"
            label="安全状态"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Select.Option value="secure">安全</Select.Option>
              <Select.Option value="acceptable">可接受</Select.Option>
              <Select.Option value="weak">较弱</Select.Option>
              <Select.Option value="insecure">不安全</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="min_bits" label="最小密钥位数">
            <Input type="number" placeholder="例如: 2048" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="规则描述" />
          </Form.Item>
          <Form.Item name="reference" label="参考链接">
            <Input placeholder="标准文档链接" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑规则"
        open={editModal}
        onOk={handleEdit}
        onCancel={() => setEditModal(false)}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="algorithm" label="算法名称">
            <Input disabled />
          </Form.Item>
          <Form.Item name="status" label="安全状态">
            <Select>
              <Select.Option value="secure">安全</Select.Option>
              <Select.Option value="acceptable">可接受</Select.Option>
              <Select.Option value="weak">较弱</Select.Option>
              <Select.Option value="insecure">不安全</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="min_bits" label="最小密钥位数">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item name="reference" label="参考链接">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title="规则详情"
        width={500}
        open={detailDrawer}
        onClose={() => setDetailDrawer(false)}
      >
        {currentRule && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="算法">{currentRule.algorithm}</Descriptions.Item>
            <Descriptions.Item label="类型">{getRuleTypeText(currentRule.rule_type)}</Descriptions.Item>
            <Descriptions.Item label="安全状态">
              <Tag color={getStatusColor(currentRule.status)}>
                {getStatusText(currentRule.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="最小密钥位数">
              {currentRule.min_bits > 0 ? `${currentRule.min_bits}位` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="描述">{currentRule.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="参考链接">
              {currentRule.reference ? (
                <a href={currentRule.reference} target="_blank" rel="noreferrer">
                  {currentRule.reference}
                </a>
              ) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="来源">{currentRule.source}</Descriptions.Item>
            <Descriptions.Item label="版本">{currentRule.version}</Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {dayjs(currentRule.updated_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}

export default RuleLibrary
