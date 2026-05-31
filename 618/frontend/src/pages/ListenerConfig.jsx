import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  message,
  Alert,
  List,
  Tag,
  Divider,
} from 'antd'
import {
  PlayCircleOutlined,
  StopOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { namespaceApi, listenerApi } from '../services/api'

const { Option } = Select

function ListenerConfig() {
  const [form] = Form.useForm()
  const [namespaces, setNamespaces] = useState([])
  const [activeListeners, setActiveListeners] = useState([])
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  useEffect(() => {
    loadNamespaces()
  }, [])

  const loadNamespaces = async () => {
    try {
      const data = await namespaceApi.getNamespaces()
      setNamespaces(data || [])
    } catch (error) {
      console.error('Failed to load namespaces:', error)
    }
  }

  const handleStart = async () => {
    try {
      const values = await form.validateFields()
      setStarting(true)
      await listenerApi.start(values)
      message.success('监听器启动成功')
      
      const listenerKey = `${values.namespace_id}:${values.group}:${values.data_id}`
      if (!activeListeners.includes(listenerKey)) {
        setActiveListeners([...activeListeners, listenerKey])
      }
    } catch (error) {
      message.error('启动失败: ' + error.message)
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async (listenerKey) => {
    try {
      const [namespace_id, group, data_id] = listenerKey.split(':')
      setStopping(true)
      await listenerApi.stop({ namespace_id, group, data_id })
      message.success('监听器已停止')
      setActiveListeners(activeListeners.filter((l) => l !== listenerKey))
    } catch (error) {
      message.error('停止失败: ' + error.message)
    } finally {
      setStopping(false)
    }
  }

  return (
    <div>
      <Card title="配置监听管理">
        <Alert
          message="提示"
          description="配置监听器可以自动监听 Nacos 配置的变化，并记录到审计日志中。启动监听器后，当配置发生变化时会自动创建审计记录。"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />

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

          <Form.Item
            name="group"
            label="分组"
            rules={[{ required: true, message: '请输入分组' }]}
          >
            <Input placeholder="例如：DEFAULT_GROUP" />
          </Form.Item>

          <Form.Item
            name="data_id"
            label="DataID"
            rules={[{ required: true, message: '请输入 DataID' }]}
          >
            <Input placeholder="配置的 DataID" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStart}
              loading={starting}
            >
              启动监听器
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <div>
          <h4 style={{ marginBottom: 16 }}>
            <BellOutlined style={{ marginRight: 8 }} />
            活动监听器 ({activeListeners.length})
          </h4>
          
          {activeListeners.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              暂无活动的监听器
            </div>
          ) : (
            <List
              dataSource={activeListeners}
              renderItem={(item) => {
                const [namespace, group, dataId] = item.split(':')
                return (
                  <List.Item
                    actions={[
                      <Button
                        key="stop"
                        type="link"
                        danger
                        icon={<StopOutlined />}
                        onClick={() => handleStop(item)}
                        loading={stopping}
                      >
                        停止
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color="success">运行中</Tag>
                          <span>{dataId}</span>
                        </Space>
                      }
                      description={`命名空间: ${namespace} | 分组: ${group}`}
                    />
                  </List.Item>
                )
              }}
            />
          )}
        </div>
      </Card>

      <Card title="使用说明" style={{ marginTop: 16 }}>
        <ol style={{ marginLeft: 20, lineHeight: 2 }}>
          <li>
            <strong>启动监听器</strong>：输入要监听的命名空间、分组和 DataID，点击启动。
          </li>
          <li>
            <strong>自动记录</strong>：当配置发生变化时，系统会自动记录变更历史。
          </li>
          <li>
            <strong>邮件通知</strong>：如果配置了通知邮箱，变更时会发送邮件提醒。
          </li>
          <li>
            <strong>合规检查</strong>：新的配置内容会自动进行合规规则检查。
          </li>
          <li>
            <strong>回滚功能</strong>：在变更历史页面可以查看详情并执行回滚操作。
          </li>
        </ol>
      </Card>
    </div>
  )
}

export default ListenerConfig
