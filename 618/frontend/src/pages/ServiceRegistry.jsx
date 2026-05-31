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
  Tag,
  Popconfirm,
  Alert,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { serviceApi, impactApi } from '../services/api'

const { Option } = Select

function ServiceRegistry() {
  const [loading, setLoading] = useState(false)
  const [services, setServices] = useState([])
  const [modalVisible, setModalVisible] = useState(false)
  const [impactVisible, setImpactVisible] = useState(false)
  const [impactData, setImpactData] = useState(null)
  const [impactLoading, setImpactLoading] = useState(false)
  const [editingService, setEditingService] = useState(null)
  const [impactForm] = Form.useForm()
  const [form] = Form.useForm()

  useEffect(() => {
    loadServices()
  }, [])

  const loadServices = async () => {
    setLoading(true)
    try {
      const data = await serviceApi.getServices()
      setServices(data || [])
    } catch (error) {
      message.error('加载服务列表失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingService(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingService(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingService) {
        values.id = editingService.id
        await serviceApi.updateService({ ...editingService, ...values })
      } else {
        await serviceApi.createService(values)
      }
      message.success('保存成功')
      setModalVisible(false)
      loadServices()
    } catch (error) {
      message.error('保存失败: ' + error.message)
    }
  }

  const handleDelete = async (id) => {
    try {
      await serviceApi.deleteService(id)
      message.success('删除成功')
      loadServices()
    } catch (error) {
      message.error('删除失败: ' + error.message)
    }
  }

  const handleAnalyzeImpact = async () => {
    try {
      const values = await impactForm.validateFields()
      setImpactLoading(true)
      setImpactVisible(true)
      const data = await impactApi.analyze(values)
      setImpactData(data)
    } catch (error) {
      message.error('分析失败: ' + error.message)
      setImpactVisible(false)
    } finally {
      setImpactLoading(false)
    }
  }

  const getEnvColor = (env) => {
    switch (env) {
      case 'production':
      case 'prod':
        return 'red'
      case 'staging':
      case 'pre':
        return 'orange'
      case 'test':
        return 'blue'
      case 'dev':
        return 'green'
      default:
        return 'default'
    }
  }

  const getRiskColor = (level) => {
    switch (level) {
      case 'CRITICAL': return 'red'
      case 'HIGH': return 'orange'
      case 'MEDIUM': return 'gold'
      case 'LOW': return 'green'
      default: return 'default'
    }
  }

  const columns = [
    { title: '服务名称', dataIndex: 'service_name', key: 'service_name', width: 180 },
    { title: '命名空间', dataIndex: 'namespace_id', key: 'namespace_id', width: 120 },
    { title: '分组', dataIndex: 'group', key: 'group', width: 120 },
    { title: 'DataID', dataIndex: 'data_id', key: 'data_id', width: 180, ellipsis: true },
    {
      title: '环境',
      dataIndex: 'environment',
      key: 'environment',
      width: 100,
      render: (env) => <Tag color={getEnvColor(env)}>{env || '-'}</Tag>,
    },
    { title: '负责人', dataIndex: 'owner', key: 'owner', width: 100 },
    { title: '描述', dataIndex: 'desc', key: 'desc', ellipsis: true },
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
      <Card title="服务注册与影响分析">
        <Space style={{ marginBottom: 16 }} wrap>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            注册服务
          </Button>
          <Button icon={<SearchOutlined />} onClick={() => setImpactVisible(true)}>
            影响分析
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadServices}>
            刷新
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={services}
          rowKey="id"
          loading={loading}
          pagination={false}
        />
      </Card>

      <Modal
        title={editingService ? '编辑服务' : '注册服务'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="service_name" label="服务名称" rules={[{ required: true, message: '请输入服务名称' }]}>
            <Input placeholder="例如：user-service" />
          </Form.Item>
          <Form.Item name="namespace_id" label="命名空间" rules={[{ required: true, message: '请输入命名空间' }]}>
            <Input placeholder="例如：dev" />
          </Form.Item>
          <Form.Item name="group" label="分组" rules={[{ required: true, message: '请输入分组' }]}>
            <Input placeholder="例如：DEFAULT_GROUP" />
          </Form.Item>
          <Form.Item name="data_id" label="DataID" rules={[{ required: true, message: '请输入DataID' }]}>
            <Input placeholder="例如：application.yml" />
          </Form.Item>
          <Form.Item name="environment" label="环境">
            <Select placeholder="选择环境">
              <Option value="dev">开发(dev)</Option>
              <Option value="test">测试(test)</Option>
              <Option value="staging">预发(staging)</Option>
              <Option value="production">生产(production)</Option>
            </Select>
          </Form.Item>
          <Form.Item name="owner" label="负责人">
            <Input placeholder="输入负责人" />
          </Form.Item>
          <Form.Item name="owner_email" label="负责人邮箱">
            <Input placeholder="输入负责人邮箱" />
          </Form.Item>
          <Form.Item name="desc" label="描述">
            <Input.TextArea placeholder="输入服务描述" rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="配置变更影响分析"
        open={impactVisible}
        onCancel={() => { setImpactVisible(false); setImpactData(null) }}
        footer={impactData ? null : undefined}
        width={700}
      >
        {!impactData ? (
          <Form form={impactForm} layout="vertical">
            <Alert
              message="输入要分析的配置信息，系统将计算受影响的服务范围和风险等级"
              type="info"
              style={{ marginBottom: 16 }}
            />
            <Form.Item name="namespace_id" label="命名空间" rules={[{ required: true }]}>
              <Input placeholder="输入命名空间ID" />
            </Form.Item>
            <Form.Item name="group" label="分组" rules={[{ required: true }]}>
              <Input placeholder="输入分组" />
            </Form.Item>
            <Form.Item name="data_id" label="DataID" rules={[{ required: true }]}>
              <Input placeholder="输入DataID" />
            </Form.Item>
            <Button type="primary" onClick={handleAnalyzeImpact} loading={impactLoading}>
              开始分析
            </Button>
          </Form>
        ) : (
          <div>
            <Alert
              message={`风险等级: ${impactData.risk_level}`}
              description={`配置 ${impactData.config_key} 变更将影响 ${impactData.total_services} 个服务`}
              type={impactData.risk_level === 'CRITICAL' || impactData.risk_level === 'HIGH' ? 'error' : impactData.risk_level === 'MEDIUM' ? 'warning' : 'success'}
              showIcon
              style={{ marginBottom: 16 }}
            />
            {impactData.warnings && impactData.warnings.length > 0 && (
              <Alert
                message="风险警告"
                description={
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {impactData.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                }
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                style={{ marginBottom: 16 }}
              />
            )}
            <h4>受影响的服务 ({impactData.total_services})</h4>
            <Table
              columns={[
                { title: '服务名称', dataIndex: 'service_name', key: 'service_name' },
                { title: '环境', dataIndex: 'environment', key: 'environment', render: (e) => <Tag color={getEnvColor(e)}>{e}</Tag> },
                { title: '负责人', dataIndex: 'owner', key: 'owner' },
                { title: '邮箱', dataIndex: 'owner_email', key: 'owner_email', ellipsis: true },
              ]}
              dataSource={impactData.affected_services}
              rowKey="service_name"
              pagination={false}
              size="small"
            />
          </div>
        )}
      </Modal>
    </div>
  )
}

export default ServiceRegistry
