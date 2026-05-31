import React, { useState, useEffect } from 'react'
import {
  Table,
  Button,
  Space,
  message,
  Card,
  Modal,
  Form,
  Input,
  Switch,
  Select,
  Tag,
  Popconfirm,
  Row,
  Col,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { complianceApi } from '../services/api'

const { Option } = Select

function ComplianceRules() {
  const [loading, setLoading] = useState(false)
  const [rules, setRules] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRule, setEditingRule] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    setLoading(true)
    try {
      const data = await complianceApi.getRules()
      setRules(data || [])
    } catch (error) {
      message.error('加载规则失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingRule(null)
    form.resetFields()
    form.setFieldsValue({
      is_enabled: true,
      rule_type: 'regex',
      severity: 'MEDIUM',
    })
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingRule(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await complianceApi.deleteRule(id)
      message.success('删除成功')
      loadRules()
    } catch (error) {
      message.error('删除失败: ' + error.message)
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      await complianceApi.saveRule({
        ...editingRule,
        ...values,
      })
      message.success('保存成功')
      setModalVisible(false)
      loadRules()
    } catch (error) {
      message.error('保存失败: ' + error.message)
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'HIGH':
        return 'error'
      case 'MEDIUM':
        return 'warning'
      case 'LOW':
        return 'processing'
      default:
        return 'default'
    }
  }

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '规则类型',
      dataIndex: 'rule_type',
      key: 'rule_type',
      width: 150,
      render: (type) => {
        const typeMap = {
          regex: '正则匹配',
          required_key: '必需键检查',
          forbidden_key: '禁止键检查',
          password_strength: '密码强度',
        }
        return typeMap[type] || type
      },
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 100,
      render: (enabled) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '已启用' : '已禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="确定要删除此规则吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
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
      <Card title="合规规则">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增规则
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadRules}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingRule ? '编辑规则' : '新增规则'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="规则名称"
                rules={[{ required: true, message: '请输入规则名称' }]}
              >
                <Input placeholder="输入规则名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rule_type"
                label="规则类型"
                rules={[{ required: true, message: '请选择规则类型' }]}
              >
                <Select>
                  <Option value="regex">正则匹配</Option>
                  <Option value="required_key">必需键检查</Option>
                  <Option value="forbidden_key">禁止键检查</Option>
                  <Option value="password_strength">密码强度</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="规则描述"
          >
            <Input.TextArea
              placeholder="输入规则描述"
              rows={2}
            />
          </Form.Item>

          <Form.Item
            name="pattern"
            label="规则模式"
            help="正则表达式或键路径（如：database.password）"
          >
            <Input.TextArea
              placeholder="输入规则模式"
              rows={3}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="severity"
                label="严重级别"
                rules={[{ required: true, message: '请选择严重级别' }]}
              >
                <Select>
                  <Option value="HIGH">高</Option>
                  <Option value="MEDIUM">中</Option>
                  <Option value="LOW">低</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_enabled"
                label="启用规则"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}

export default ComplianceRules
