import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Upload,
  Select,
  Space,
  message,
  Typography,
  Row,
  Col,
  Tabs,
  Alert,
  Descriptions,
  Divider,
} from 'antd'
import {
  ImportOutlined,
  ExportOutlined,
  UploadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'

import { ioApi, groupApi, ruleApi } from '../api/client'

const { Title, Text } = Typography
const { TabPane } = Tabs
const { Option } = Select
const { Dragger } = Upload

function ImportExportPage() {
  const [groups, setGroups] = useState([])
  const [rules, setRules] = useState([])
  const [importGroupId, setImportGroupId] = useState(null)
  const [exportGroupId, setExportGroupId] = useState(null)
  const [exportFormat, setExportFormat] = useState('yaml')
  const [importFormat, setImportFormat] = useState('yaml')
  const [importResult, setImportResult] = useState(null)
  const [fileContent, setFileContent] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [groupsRes, rulesRes] = await Promise.all([
        groupApi.list(),
        ruleApi.list(),
      ])
      setGroups(groupsRes.data)
      setRules(rulesRes.data)
    } catch (error) {
      message.error('加载数据失败')
    }
  }

  const handleImport = async (file) => {
    const reader = new FileReader()
    reader.onload = async (e) => {
      const content = e.target.result
      setFileContent(content)
      setImportResult(null)

      try {
        const res = await ioApi.import(content, importGroupId, importFormat)
        setImportResult(res.data)
        message.success(`成功导入 ${res.data.count} 条规则`)
        loadData()
      } catch (error) {
        message.error(error.response?.data?.error || '导入失败')
      }
    }

    if (importFormat === 'yaml') {
      reader.readAsText(file)
    } else {
      reader.readAsText(file)
    }

    return false
  }

  const handleExport = async () => {
    try {
      const res = await ioApi.export(exportGroupId, exportFormat)
      let content, filename, mimeType

      if (exportFormat === 'yaml') {
        content = res.data
        filename = `alert_rules_${Date.now()}.yaml`
        mimeType = 'application/x-yaml'
      } else {
        content = JSON.stringify(res.data, null, 2)
        filename = `alert_rules_${Date.now()}.json`
        mimeType = 'application/json'
      }

      const blob = new Blob([content], { type: mimeType })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      message.success('导出成功')
    } catch (error) {
      message.error('导出失败')
    }
  }

  const beforeUpload = (file) => {
    const supportedFormats = importFormat === 'yaml' ? ['.yaml', '.yml'] : ['.json']
    const fileName = file.name.toLowerCase()
    const isSupported = supportedFormats.some((ext) => fileName.endsWith(ext))
    if (!isSupported) {
      message.error(`只支持 ${supportedFormats.join(', ')} 格式文件!`)
    }
    return isSupported
  }

  return (
    <div>
      <div className="page-header">
        <Title level={3} className="page-title">
          <ImportOutlined /> 批量导入导出
        </Title>
      </div>

      <Card>
        <Tabs defaultActiveKey="export">
          <TabPane
            tab={
              <Space>
                <ExportOutlined /> 导出规则
              </Space>
            }
            key="export"
          >
            <Row gutter={24}>
              <Col span={12}>
                <Card title="导出配置" size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        选择分组
                      </Text>
                      <Select
                        placeholder="导出所有分组"
                        style={{ width: '100%' }}
                        allowClear
                        value={exportGroupId}
                        onChange={setExportGroupId}
                      >
                        {groups.map((g) => (
                          <Option key={g.id} value={g.id}>
                            {g.name} ({g.rules?.length || 0} 条规则)
                          </Option>
                        ))}
                      </Select>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        不选择则导出所有分组
                      </Text>
                    </div>

                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        导出格式
                      </Text>
                      <Select
                        value={exportFormat}
                        onChange={setExportFormat}
                        style={{ width: '100%' }}
                      >
                        <Option value="yaml">YAML (Prometheus 原生格式)</Option>
                        <Option value="json">JSON 格式</Option>
                      </Select>
                    </div>

                    <Button
                      type="primary"
                      size="large"
                      icon={<ExportOutlined />}
                      onClick={handleExport}
                      style={{ width: '100%' }}
                    >
                      导出规则
                    </Button>
                  </Space>
                </Card>
              </Col>

              <Col span={12}>
                <Card title="导出预览" size="small">
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="规则总数">
                      {rules.length} 条
                    </Descriptions.Item>
                    <Descriptions.Item label="分组总数">
                      {groups.length} 个
                    </Descriptions.Item>
                    <Descriptions.Item label="启用规则">
                      {rules.filter((r) => r.enabled).length} 条
                    </Descriptions.Item>
                    <Descriptions.Item label="禁用规则">
                      {rules.filter((r) => !r.enabled).length} 条
                    </Descriptions.Item>
                  </Descriptions>

                  <Divider />

                  <Alert
                    message="Prometheus YAML 格式示例"
                    description={
                      <pre
                        style={{
                          background: '#f5f5f5',
                          padding: 12,
                          borderRadius: 4,
                          fontSize: 12,
                          margin: 0,
                        }}
                      >
                        {`groups:
  - name: example
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage detected
          description: CPU usage is above 80% for 5 minutes`}
                      </pre>
                    }
                    type="info"
                    showIcon
                  />
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane
            tab={
              <Space>
                <ImportOutlined /> 导入规则
              </Space>
            }
            key="import"
          >
            <Row gutter={24}>
              <Col span={12}>
                <Card title="导入配置" size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        导入格式
                      </Text>
                      <Select
                        value={importFormat}
                        onChange={setImportFormat}
                        style={{ width: '100%' }}
                      >
                        <Option value="yaml">YAML (Prometheus 原生格式)</Option>
                        <Option value="json">JSON 格式</Option>
                      </Select>
                    </div>

                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        目标分组 (可选)
                      </Text>
                      <Select
                        placeholder="按文件中的分组名称自动创建/匹配"
                        style={{ width: '100%' }}
                        allowClear
                        value={importGroupId}
                        onChange={setImportGroupId}
                      >
                        {groups.map((g) => (
                          <Option key={g.id} value={g.id}>
                            {g.name}
                          </Option>
                        ))}
                      </Select>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        不选择则根据文件中的分组名称自动创建或匹配现有分组
                      </Text>
                    </div>

                    <Dragger
                      name="file"
                      multiple={false}
                      accept={importFormat === 'yaml' ? '.yaml,.yml' : '.json'}
                      beforeUpload={beforeUpload}
                      customRequest={({ file }) => handleImport(file)}
                      showUploadList={false}
                    >
                      <p className="ant-upload-drag-icon">
                        <UploadOutlined />
                      </p>
                      <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                      <p className="ant-upload-hint">
                        支持 {importFormat === 'yaml' ? '.yaml, .yml' : '.json'} 格式的规则文件
                      </p>
                    </Dragger>
                  </Space>
                </Card>
              </Col>

              <Col span={12}>
                <Card title="导入结果" size="small">
                  {importResult ? (
                    <div>
                      <Alert
                        message="导入成功"
                        description={importResult.message}
                        type="success"
                        showIcon
                        icon={<CheckCircleOutlined />}
                        style={{ marginBottom: 16 }}
                      />
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="导入数量">
                          {importResult.count} 条规则
                        </Descriptions.Item>
                      </Descriptions>
                    </div>
                  ) : fileContent ? (
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        文件内容预览
                      </Text>
                      <pre
                        style={{
                          background: '#f5f5f5',
                          padding: 12,
                          borderRadius: 4,
                          maxHeight: '400px',
                          overflow: 'auto',
                          fontSize: 12,
                        }}
                      >
                        {fileContent}
                      </pre>
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '48px 0', color: '#999' }}>
                      <FileTextOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                      <p>选择文件后将在此显示预览和导入结果</p>
                    </div>
                  )}
                </Card>
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  )
}

export default ImportExportPage
