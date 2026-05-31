import React, { useState } from 'react'
import { Card, Form, Input, Button, Alert, Space, Typography, message } from 'antd'
import { DatabaseOutlined, TestOutlined, LoginOutlined } from '@ant-design/icons'
import { connectionApi } from '../services/api'
import type { DBConfig } from '../types'

const { Title, Paragraph } = Typography

interface ConnectionPageProps {
  onConnect: (config: DBConfig) => Promise<void>
  connected: boolean
}

const ConnectionPage: React.FC<ConnectionPageProps> = ({ onConnect, connected }) => {
  const [form] = Form.useForm()
  const [testing, setTesting] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields()
      setTesting(true)
      setTestResult(null)

      await connectionApi.test(values)

      setTestResult({
        success: true,
        message: '连接测试成功！',
      })
      message.success('连接测试成功')
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.message || error.message || '连接测试失败',
      })
      message.error('连接测试失败')
    } finally {
      setTesting(false)
    }
  }

  const handleConnect = async () => {
    try {
      const values = await form.validateFields()
      setConnecting(true)

      await onConnect(values)

      message.success('连接成功！')
    } catch (error: any) {
      message.error(error.response?.data?.message || error.message || '连接失败')
    } finally {
      setConnecting(false)
    }
  }

  const initialValues: DBConfig = {
    host: 'localhost',
    port: '3306',
    user: 'root',
    password: '',
    database: '',
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={1} style={{ margin: 0 }}>
          <DatabaseOutlined style={{ marginRight: 12 }} />
          数据库连接配置
        </Title>
        <Paragraph className="description">
          配置 MySQL 数据库连接信息，支持分区策略推荐、分区管理和查询优化
        </Paragraph>
      </div>

      <Card
        style={{ maxWidth: 600, margin: '0 auto' }}
        title="连接信息"
      >
        {connected && (
          <Alert
            type="success"
            message="已连接到数据库"
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}

        {testResult && (
          <Alert
            type={testResult.success ? 'success' : 'error'}
            message={testResult.message}
            showIcon
            style={{ marginBottom: 24 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          onFinish={handleConnect}
        >
          <Form.Item
            name="host"
            label="主机地址"
            rules={[{ required: true, message: '请输入主机地址' }]}
          >
            <Input placeholder="localhost" />
          </Form.Item>

          <Form.Item
            name="port"
            label="端口"
            rules={[{ required: true, message: '请输入端口' }]}
          >
            <Input placeholder="3306" />
          </Form.Item>

          <Form.Item
            name="user"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="root" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item
            name="database"
            label="数据库名"
            rules={[{ required: true, message: '请输入数据库名' }]}
          >
            <Input placeholder="mydatabase" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="default"
                icon={<TestOutlined />}
                onClick={handleTestConnection}
                loading={testing}
              >
                测试连接
              </Button>
              <Button
                type="primary"
                htmlType="submit"
                icon={<LoginOutlined />}
                loading={connecting}
              >
                连接数据库
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card
        style={{ maxWidth: 600, margin: '24px auto 0' }}
        title="功能特性"
        size="small"
      >
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          <li>智能分析表数据量和增长趋势</li>
          <li>自动推荐 RANGE / LIST / HASH 分区策略</li>
          <li>生成分区 SQL 执行脚本</li>
          <li>分区管理（添加、删除、合并、拆分）</li>
          <li>查询改写优化，自动利用分区剪枝</li>
        </ul>
      </Card>
    </div>
  )
}

export default ConnectionPage
