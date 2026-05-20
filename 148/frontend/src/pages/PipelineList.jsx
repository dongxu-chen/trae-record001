import { useState, useEffect } from 'react'
import { Table, Button, Space, Modal, Form, Input, message, Popconfirm, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, EyeOutlined } from '@ant-design/icons'
import { pipelineApi } from '../services/api'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'

export default function PipelineList() {
  const [pipelines, setPipelines] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingPipeline, setEditingPipeline] = useState(null)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const loadPipelines = async () => {
    setLoading(true)
    try {
      const data = await pipelineApi.list()
      setPipelines(data)
    } catch (error) {
      message.error('加载管道列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPipelines()
  }, [])

  const handleCreate = () => {
    setEditingPipeline(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record) => {
    setEditingPipeline(record)
    form.setFieldsValue(record)
    setModalVisible(true)
  }

  const handleDelete = async (id) => {
    try {
      await pipelineApi.delete(id)
      message.success('删除成功')
      loadPipelines()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingPipeline) {
        await pipelineApi.update(editingPipeline.id, values)
        message.success('更新成功')
      } else {
        const defaultConfig = {
          name: values.name,
          tasks: [],
          edges: []
        }
        await pipelineApi.create({ ...values, flow_config: defaultConfig })
        message.success('创建成功')
      }
      setModalVisible(false)
      loadPipelines()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleRun = async (record) => {
    try {
      message.info('开始执行管道...')
      const result = await pipelineApi.run(record.id)
      message.success(`执行成功! 执行ID: ${result.execution_id}`)
    } catch (error) {
      message.error('执行失败')
    }
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '管道名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/designer/${record.id}`)}
          >
            设计
          </Button>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleRun(record)}
          >
            运行
          </Button>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个管道吗?"
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
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h3>数据管道列表</h3>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建管道
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={pipelines}
        rowKey="id"
        loading={loading}
      />

      <Modal
        title={editingPipeline ? '编辑管道' : '新建管道'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="管道名称"
            rules={[{ required: true, message: '请输入管道名称' }]}
          >
            <Input placeholder="请输入管道名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入描述" rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
