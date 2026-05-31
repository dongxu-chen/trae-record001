import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Checkbox,
  message,
  Row,
  Col,
  Radio,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BellOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import {
  getAlertRuleList,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  toggleAlertRule,
} from '@/services/api'
import type { AlertRule, AlertLevelEnum, DeadReasonTypeEnum } from '@/types'

const { Option } = Select
const { TextArea } = Input

const AlertRulePage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [modalLoading, setModalLoading] = useState(false)
  const [dataList, setDataList] = useState<AlertRule[]>([])
  const [total, setTotal] = useState(0)
  const [pageNum, setPageNum] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const result = await getAlertRuleList({ pageNum, pageSize })
      setDataList(result.list)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to fetch alert rules:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [pageNum, pageSize])

  const handleAdd = () => {
    setEditingRule(null)
    form.resetFields()
    form.setFieldsValue({
      level: 'WARNING',
      notifyType: [],
      enabled: true,
      minRetryCount: 3,
      timeRange: 60,
    })
    setModalOpen(true)
  }

  const handleEdit = (record: AlertRule) => {
    setEditingRule(record)
    form.setFieldsValue({
      ...record,
    })
    setModalOpen(true)
  }

  const handleDelete = (record: AlertRule) => {
    Modal.confirm({
      title: '删除确认',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除规则「${record.name}」吗？`,
      okText: '确认删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteAlertRule(record.id!)
          message.success('删除成功')
          fetchData()
        } catch (error) {
          console.error('Delete failed:', error)
        }
      },
    })
  }

  const handleToggle = async (record: AlertRule, enabled: boolean) => {
    try {
      await toggleAlertRule(record.id!, enabled)
      message.success(enabled ? '已启用' : '已禁用')
      fetchData()
    } catch (error) {
      console.error('Toggle failed:', error)
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setModalLoading(true)
      if (editingRule) {
        await updateAlertRule({ ...values, id: editingRule.id })
        message.success('更新成功')
      } else {
        await createAlertRule(values)
        message.success('创建成功')
      }
      setModalOpen(false)
      fetchData()
    } catch (error) {
      console.error('Submit failed:', error)
    } finally {
      setModalLoading(false)
    }
  }

  const getReasonTypeName = (type: DeadReasonTypeEnum) => {
    const nameMap: Record<string, string> = {
      BIZ_EXCEPTION: '业务异常',
      TIMEOUT: '超时异常',
      REJECTED: '被拒绝',
      FORMAT_ERROR: '格式错误',
      NULL_POINTER: '空指针',
      DATABASE_ERROR: '数据库错误',
      OTHER: '其他',
    }
    return nameMap[type] || type
  }

  const getLevelColor = (level: AlertLevelEnum) => {
    const colorMap: Record<string, string> = {
      INFO: 'blue',
      WARNING: 'orange',
      CRITICAL: 'red',
    }
    return colorMap[level] || 'default'
  }

  const getLevelName = (level: AlertLevelEnum) => {
    const nameMap: Record<string, string> = {
      INFO: '信息',
      WARNING: '警告',
      CRITICAL: '严重',
    }
    return nameMap[level] || level
  }

  const getNotifyTypeName = (type: string) => {
    const nameMap: Record<string, string> = {
      DINGTALK: '钉钉',
      WECHAT_WORK: '企业微信',
      EMAIL: '邮件',
      WEBHOOK: 'Webhook',
    }
    return nameMap[type] || type
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 200,
    },
    {
      title: '触发条件',
      key: 'trigger',
      width: 250,
      render: (_: unknown, record: AlertRule) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontSize: 12 }}>
            原因类型：<Tag size="small">{getReasonTypeName(record.reasonType)}</Tag>
          </span>
          <span style={{ fontSize: 12, color: '#666' }}>
            最小重试次数：{record.minRetryCount}
          </span>
          <span style={{ fontSize: 12, color: '#666' }}>
            时间范围：{record.timeRange}分钟
          </span>
          {record.keyword && (
            <span style={{ fontSize: 12, color: '#666' }}>
              关键词：{record.keyword}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: AlertLevelEnum) => (
        <Tag color={getLevelColor(level)}>{getLevelName(level)}</Tag>
      ),
    },
    {
      title: '通知方式',
      dataIndex: 'notifyType',
      key: 'notifyType',
      width: 180,
      render: (types: string[]) => (
        <Space wrap size={4}>
          {types.map((type) => (
            <Tag key={type} size="small">{getNotifyTypeName(type)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '通知目标',
      dataIndex: 'notifyTarget',
      key: 'notifyTarget',
      ellipsis: true,
      width: 180,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean, record: AlertRule) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record, checked)}
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 170,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right' as const,
      render: (_: unknown, record: AlertRule) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Card
      title={
        <Space>
          <BellOutlined style={{ color: '#1890ff' }} />
          告警规则管理
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          新增规则
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={dataList}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1300 }}
        pagination={{
          current: pageNum,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (totalNum) => `共 ${totalNum} 条记录`,
          onChange: (page, size) => {
            setPageNum(page)
            setPageSize(size)
          },
        }}
      />

      <Modal
        title={
          <Space>
            {editingRule ? <EditOutlined /> : <PlusOutlined />}
            {editingRule ? '编辑规则' : '新增规则'}
          </Space>
        }
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSubmit}
        confirmLoading={modalLoading}
        okText="保存"
        cancelText="取消"
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Divider orientation="left">基本信息</Divider>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="请输入规则名称" maxLength={50} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="enabled" label="启用状态" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="禁用" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="description" label="规则描述">
            <TextArea rows={2} placeholder="请输入规则描述" maxLength={200} />
          </Form.Item>

          <Divider orientation="left">触发条件</Divider>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="reasonType"
                label="原因类型"
                rules={[{ required: true, message: '请选择原因类型' }]}
              >
                <Select placeholder="请选择原因类型">
                  <Option value="BIZ_EXCEPTION">业务异常</Option>
                  <Option value="TIMEOUT">超时异常</Option>
                  <Option value="REJECTED">被拒绝</Option>
                  <Option value="FORMAT_ERROR">格式错误</Option>
                  <Option value="NULL_POINTER">空指针</Option>
                  <Option value="DATABASE_ERROR">数据库错误</Option>
                  <Option value="OTHER">其他</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="minRetryCount"
                label="最小重试次数"
                rules={[{ required: true, message: '请输入最小重试次数' }]}
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} placeholder="请输入最小重试次数" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="timeRange"
                label="时间范围（分钟）"
                rules={[{ required: true, message: '请输入时间范围' }]}
              >
                <InputNumber min={1} max={1440} style={{ width: '100%' }} placeholder="请输入时间范围" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="keyword" label="关键词">
                <Input placeholder="可输入关键词进行过滤" maxLength={100} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">告警级别</Divider>
          <Form.Item
            name="level"
            label="告警级别"
            rules={[{ required: true, message: '请选择告警级别' }]}
          >
            <Radio.Group>
              <Radio.Button value="INFO">
                <Tag color="blue">INFO 信息</Tag>
              </Radio.Button>
              <Radio.Button value="WARNING">
                <Tag color="orange">WARNING 警告</Tag>
              </Radio.Button>
              <Radio.Button value="CRITICAL">
                <Tag color="red">CRITICAL 严重</Tag>
              </Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Divider orientation="left">通知方式</Divider>
          <Form.Item
            name="notifyType"
            label="通知方式"
            rules={[{ required: true, message: '请选择通知方式' }]}
          >
            <Checkbox.Group>
              <Space wrap>
                <Checkbox value="DINGTALK">钉钉</Checkbox>
                <Checkbox value="WECHAT_WORK">企业微信</Checkbox>
                <Checkbox value="EMAIL">邮件</Checkbox>
                <Checkbox value="WEBHOOK">Webhook</Checkbox>
              </Space>
            </Checkbox.Group>
          </Form.Item>
          <Form.Item
            name="notifyTarget"
            label="通知目标"
            rules={[{ required: true, message: '请输入通知目标' }]}
          >
            <Input placeholder="请输入Webhook URL或邮箱地址，多个用逗号分隔" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

export default AlertRulePage
