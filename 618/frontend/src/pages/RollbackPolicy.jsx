import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  message,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Tag,
  Popconfirm,
  InputNumber,
  Alert,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { rollbackPolicyApi, namespaceApi } from '../services/api'

const { Option } = Select

function RollbackPolicy() {
  const [loading, setLoading] = useState(false)
  const [policies, setPolicies] = useState([])
  const [namespaces, setNamespaces] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [nsData, policyData] = await Promise.all([
        namespaceApi.getNamespaces(),
        rollbackPolicyApi.getPolicies(),
      ])
      setNamespaces(nsData || [])
      setPolicies(policyData || [])
    } catch (error) {
      message.error('加载数据失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingPolicy(null)
    form.resetFields()
    form.setFieldsValue({
      auto_rollback_on_compliance_fail: true,
      auto_rollback_on_sensitive_data: true,
      auto_rollback_on_critical_change: false,
      max_change_lines: 0,
      is_enabled: true,
    })
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingPolicy(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingPolicy) {
        values.id = editingPolicy.id
        await rollbackPolicyApi.updatePolicy({ ...editingPolicy, ...values })
      } else {
        await rollbackPolicyApi.createPolicy(values)
      }
      message.success('保存成功')
      setModalVisible(false)
      loadData()
    } catch (error) {
      message.error('保存失败: ' + error.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await rollbackPolicyApi.deletePolicy(id)
      message.success('删除成功')
      loadData()
    } catch (error) {
      message.error('删除失败: ' + error.message)
    }
  }

  const columns = [
    { title: '策略名称', dataIndex: 'name', key: 'name', width: 180 },
    { title: '命名空间', dataIndex: 'namespace_id', key: 'namespace_id', width: 120 },
    { title: '分组', dataIndex: 'group', key: 'group', width: 120, render: (g) => g || '*' },
    { title: 'DataID', dataIndex: 'data_id', key: 'data_id', width: 150, render: (d) => d || '*' },
    {
      title: '合规失败回滚',
      dataIndex: 'auto_rollback_on_compliance_fail',
      key: 'auto_rollback_on_compliance_fail',
      width: 120,
      render: (v) => v ? <Tag color="red">启用</Tag> : <Tag>禁用</Tag>,
    },
    {
      title: '敏感数据回滚',
      dataIndex: 'auto_rollback_on_sensitive_data',
      key: 'auto_rollback_on_sensitive_data',
      width: 120,
      render: (v) => v ? <Tag color="red">启用</Tag> : <Tag>禁用</Tag>,
    },
    {
      title: '删除操作回滚',
      dataIndex: 'auto_rollback_on_critical_change',
      key: 'auto_rollback_on_critical_change',
      width: 120,
      render: (v) => v ? <Tag color="orange">启用</Tag> : <Tag>禁用</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 80,
      render: (v) => v ? <Tag color="success">启用</Tag> : <Tag>禁用</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
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
      <Card title="自动回滚策略">
        <Alert
          message="说明"
          description="自动回滚策略可针对特定配置设置回滚条件。当配置变更触发回滚条件时（如合规检查失败、检测到敏感数据等），系统将自动执行回滚操作。"
          type="info"
          showIcon
          icon={<ThunderboltOutlined />}
          style={{ marginBottom: 16 }}
        />

        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增策略
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={policies}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 1100 }}
        />
      </Card>

      <Modal
        title={editingPolicy ? '编辑策略' : '新增策略'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={650}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="策略名称" rules={[{ required: true, message: '请输入策略名称' }]}>
            <Input placeholder="例如：生产环境核心配置策略" />
          </Form.Item>

          <Form.Item name="namespace_id" label="命名空间" rules={[{ required: true }]}>
            <Select placeholder="选择命名空间">
              {namespaces.map((ns) => (
                <Option key={ns.id} value={ns.id}>{ns.name || ns.id}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="group" label="分组（留空表示所有）">
            <Input placeholder="例如：DEFAULT_GROUP" />
          </Form.Item>

          <Form.Item name="data_id" label="DataID（留空表示所有）">
            <Input placeholder="例如：application.yml" />
          </Form.Item>

          <Form.Item name="auto_rollback_on_compliance_fail" label="合规检查失败时自动回滚" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="auto_rollback_on_sensitive_data" label="检测到敏感数据时自动回滚" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="auto_rollback_on_critical_change" label="配置被删除时自动回滚" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="max_change_lines" label="最大允许变更行数（0表示不限制）">
            <InputNumber min={0} max={10000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="is_enabled" label="启用策略" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RollbackPolicy
