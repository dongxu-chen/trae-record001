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
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { namespaceApi } from '../services/api'

const { Option } = Select

function NamespaceConfig() {
  const [loading, setLoading] = useState(false)
  const [configs, setConfigs] = useState([])
  const [namespaces, setNamespaces] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [editingConfig, setEditingConfig] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [nsData, configData] = await Promise.all([
        namespaceApi.getNamespaces(),
        namespaceApi.getConfigs(),
      ])
      setNamespaces(nsData || [])
      setConfigs(configData || [])
    } catch (error) {
      message.error('加载数据失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingConfig(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingConfig(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      await namespaceApi.saveConfig({
        ...editingConfig,
        ...values,
      })
      message.success('保存成功')
      setModalVisible(false)
      loadData()
    } catch (error) {
      message.error('保存失败: ' + error.message)
    }
  }

  const getNamespaceName = (id) => {
    const ns = namespaces.find((n) => n.id === id)
    return ns?.name || id
  }

  const columns = [
    {
      title: '命名空间ID',
      dataIndex: 'namespace_id',
      key: 'namespace_id',
      width: 200,
    },
    {
      title: '命名空间名称',
      dataIndex: 'namespace_name',
      key: 'namespace_name',
      width: 200,
      render: (_, record) => getNamespaceName(record.namespace_id),
    },
    {
      title: '启用审计',
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
      title: '通知邮箱',
      dataIndex: 'notify_emails',
      key: 'notify_emails',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Card title="命名空间配置">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增配置
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingConfig ? '编辑配置' : '新增配置'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="namespace_id"
            label="命名空间"
            rules={[{ required: true, message: '请选择命名空间' }]}
          >
            <Select placeholder="选择命名空间">
              {namespaces.map((ns) => (
                <Option key={ns.id} value={ns.id}>
                  {ns.name || ns.id}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="namespace_name" label="命名空间名称">
            <Input placeholder="输入命名空间名称" />
          </Form.Item>

          <Form.Item
            name="is_enabled"
            label="启用审计"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="notify_emails"
            label="通知邮箱"
            help="多个邮箱用逗号分隔"
          >
            <Input.TextArea
              placeholder="输入通知邮箱，多个用逗号分隔"
              rows={3}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default NamespaceConfig
