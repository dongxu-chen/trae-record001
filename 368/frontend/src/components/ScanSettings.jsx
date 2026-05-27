import React, { useState, useEffect } from 'react'
import {
  Row,
  Col,
  Card,
  Descriptions,
  Button,
  Form,
  InputNumber,
  Switch,
  message,
  Divider,
  Space,
  Alert,
} from 'antd'
import {
  SaveOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { api } from '../services/api.js'

const ScanSettings = () => {
  const [form] = Form.useForm()
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    try {
      const res = await api.getScanConfig()
      setConfig(res.data)
      form.setFieldsValue(res.data)
    } catch (error) {
      message.error('获取配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      message.info('配置修改需要重启服务后生效')
    } catch (error) {
      message.error('保存失败')
    }
  }

  return (
    <div>
      <Alert
        message="扫描设置说明"
        description={
          <div>
            <p>• <strong>并发控制</strong>: 控制同时扫描的域名数量，避免对服务器造成压力</p>
            <p>• <strong>随机延时</strong>: 在扫描之间添加随机延迟，防止被目标服务器封禁</p>
            <p>• <strong>重试机制</strong>: 连接失败时的重试次数和间隔</p>
            <p>• <strong>配置文件</strong>: 修改配置需要编辑 backend/config.yaml 文件并重启服务</p>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="当前配置" loading={loading}>
            {config && (
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="最大并发数">
                  {config.max_concurrent}
                </Descriptions.Item>
                <Descriptions.Item label="最小延迟">
                  {config.min_delay_ms} ms
                </Descriptions.Item>
                <Descriptions.Item label="最大延迟">
                  {config.max_delay_ms} ms
                </Descriptions.Item>
                <Descriptions.Item label="连接超时">
                  {config.timeout_seconds} 秒
                </Descriptions.Item>
                <Descriptions.Item label="重试次数">
                  {config.retry_count} 次
                </Descriptions.Item>
                <Descriptions.Item label="随机延迟">
                  {config.randomize_delay ? '启用' : '禁用'}
                </Descriptions.Item>
                <Descriptions.Item label="抖动百分比">
                  {config.jitter_percent}%
                </Descriptions.Item>
              </Descriptions>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="配置说明">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSave}
            >
              <Form.Item
                name="max_concurrent"
                label={
                  <Space>
                    最大并发数
                    <InfoCircleOutlined />
                  </Space>
                }
                tooltip="同时扫描的域名数量，建议根据服务器性能调整"
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} disabled />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="min_delay_ms"
                    label="最小延迟 (ms)"
                    tooltip="扫描之间的最小延迟"
                  >
                    <InputNumber min={0} max={10000} style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="max_delay_ms"
                    label="最大延迟 (ms)"
                    tooltip="扫描之间的最大延迟"
                  >
                    <InputNumber min={0} max={60000} style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="timeout_seconds"
                    label="连接超时 (秒)"
                    tooltip="SSL连接超时时间"
                  >
                    <InputNumber min={5} max={120} style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="retry_count"
                    label="重试次数"
                    tooltip="连接失败后的重试次数"
                  >
                    <InputNumber min={0} max={10} style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="randomize_delay"
                    label="启用随机延迟"
                    valuePropName="checked"
                  >
                    <Switch disabled />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="jitter_percent"
                    label="抖动百分比 (%)"
                    tooltip="在延迟基础上增加的随机抖动范围"
                  >
                    <InputNumber min={0} max={100} style={{ width: '100%' }} disabled />
                  </Form.Item>
                </Col>
              </Row>

              <Divider />

              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={fetchConfig}
                >
                  刷新
                </Button>
              </Space>

              <Alert
                message="配置文件位置"
                description="backend/config.yaml - 修改后重启服务生效"
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Form>
          </Card>
        </Col>
      </Row>

      <Card title="配置示例" style={{ marginTop: 16 }}>
        <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
{`scan:
  max_concurrent: 5        # 最大并发5个域名
  min_delay_ms: 100        # 最小延迟100ms
  max_delay_ms: 1000       # 最大延迟1s
  timeout_seconds: 15      # 连接超时15秒
  retry_count: 2           # 失败重试2次
  retry_delay_ms: 500      # 重试间隔500ms
  randomize_delay: true    # 启用随机延迟
  jitter_percent: 20       # 20%随机抖动`}
        </pre>
      </Card>
    </div>
  )
}

export default ScanSettings
