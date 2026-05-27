import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Select,
  Card,
  Form,
  Input,
  Modal,
  message,
} from 'antd'
import {
  ReloadOutlined,
  SendOutlined,
  AlertOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'
import dayjs from 'dayjs'

const AlertLogs = () => {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [level, setLevel] = useState('')
  const [testModal, setTestModal] = useState(false)
  const [testForm] = Form.useForm()

  useEffect(() => {
    fetchLogs()
  }, [page, pageSize, level])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await api.getAlertLogs({
        page,
        page_size: pageSize,
      })
      setLogs(res.data.logs)
      setTotal(res.data.total)
    } catch (error) {
      console.error('获取告警记录失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSendTest = async () => {
    try {
      const values = await testForm.validateFields()
      await api.sendTestAlert(values)
      message.success('测试告警已发送')
      setTestModal(false)
      testForm.resetFields()
    } catch (error) {
      if (error.errorFields) return
      message.error(error.message || '发送失败')
    }
  }

  const getLevelColor = (level) => {
    const colors = {
      critical: 'red',
      warning: 'orange',
      error: 'red',
      info: 'blue',
    }
    return colors[level] || 'default'
  }

  const getLevelText = (level) => {
    const texts = {
      critical: '严重',
      warning: '警告',
      error: '错误',
      info: '信息',
    }
    return texts[level] || level
  }

  const columns = [
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      width: 200,
    },
    {
      title: '告警级别',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level) => (
        <Tag color={getLevelColor(level)}>{getLevelText(level)}</Tag>
      ),
    },
    {
      title: '告警方式',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 150,
      render: (type) => (
        <Space size={4}>
          {type.split(', ').map((t, i) => (
            <Tag key={i} color="blue">{t}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'sent',
      key: 'sent',
      width: 80,
      render: (sent) => (
        <Tag color={sent ? 'green' : 'red'}>
          {sent ? '已发送' : '失败'}
        </Tag>
      ),
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Select
              placeholder="级别筛选"
              value={level || undefined}
              onChange={setLevel}
              style={{ width: 150 }}
              allowClear
            >
              <Select.Option value="critical">严重</Select.Option>
              <Select.Option value="warning">警告</Select.Option>
              <Select.Option value="error">错误</Select.Option>
              <Select.Option value="info">信息</Select.Option>
            </Select>
          </Space>
        </Col>
        <Col flex="auto" style={{ textAlign: 'right' }}>
          <Space>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={() => setTestModal(true)}
            >
              发送测试告警
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchLogs}
            >
              刷新
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
      />

      <Modal
        title="发送测试告警"
        open={testModal}
        onOk={handleSendTest}
        onCancel={() => {
          setTestModal(false)
          testForm.resetFields()
        }}
      >
        <Form form={testForm} layout="vertical">
          <Form.Item
            name="domain"
            label="域名"
            rules={[{ required: true, message: '请输入域名' }]}
          >
            <Input placeholder="输入要测试的域名" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AlertLogs
