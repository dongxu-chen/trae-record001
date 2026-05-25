import { useState, useRef } from 'react'
import { Upload, Button, Space, message, Modal, Radio, Input } from 'antd'
import { UploadOutlined, FileTextOutlined, ClearOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'

const { TextArea } = Input

const DataUpload = ({ onSuccess }) => {
  const [dragOver, setDragOver] = useState(false)
  const [jsonModalVisible, setJsonModalVisible] = useState(false)
  const [jsonInput, setJsonInput] = useState('')
  const [importType, setImportType] = useState('file')
  const fileInputRef = useRef(null)

  const handleFileUpload = async (file) => {
    try {
      const text = await file.text()
      const data = JSON.parse(text)

      if (!data.nodes || !data.edges) {
        message.error('JSON文件格式不正确，需要包含nodes和edges字段')
        return false
      }

      await graphApi.importData(data)
      onSuccess?.()
      return false
    } catch (error) {
      console.error('导入失败:', error)
      message.error('文件解析失败，请检查JSON格式')
      return false
    }
  }

  const handleJsonImport = async () => {
    try {
      const data = JSON.parse(jsonInput)

      if (!data.nodes || !data.edges) {
        message.error('JSON格式不正确，需要包含nodes和edges字段')
        return
      }

      await graphApi.importData(data)
      setJsonModalVisible(false)
      setJsonInput('')
      onSuccess?.()
    } catch (error) {
      console.error('导入失败:', error)
      message.error('JSON解析失败，请检查格式')
    }
  }

  const handleClear = async () => {
    Modal.confirm({
      title: '确认清空数据库',
      content: '此操作将删除所有图数据，确定要继续吗？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await graphApi.clearDatabase()
          message.success('数据库已清空')
          onSuccess?.()
        } catch (error) {
          message.error('清空失败')
        }
      },
    })
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileUpload(files[0])
    }
  }

  const sampleJson = `{
  "nodes": [
    {"id": "1", "label": "User", "name": "张三"},
    {"id": "2", "label": "User", "name": "李四"}
  ],
  "edges": [
    {"source": "1", "target": "2", "type": "FRIEND", "weight": 1}
  ]
}`

  return (
    <div>
      <Radio.Group
        value={importType}
        onChange={(e) => setImportType(e.target.value)}
        style={{ marginBottom: 12, width: '100%' }}
        block
      >
        <Radio.Button value="file" style={{ width: '50%' }}>
          文件上传
        </Radio.Button>
        <Radio.Button value="json" style={{ width: '50%' }}>
          JSON输入
        </Radio.Button>
      </Radio.Group>

      {importType === 'file' ? (
        <div
          className={`upload-area ${dragOver ? 'drag-over' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files?.[0]) {
                handleFileUpload(e.target.files[0])
              }
            }}
          />
          <UploadOutlined style={{ fontSize: '32px', color: '#1890ff', marginBottom: 8 }} />
          <p style={{ margin: '8px 0', color: '#666' }}>
            拖拽JSON文件到此处，或点击选择文件
          </p>
          <p style={{ fontSize: '12px', color: '#999' }}>支持 .json 格式</p>
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button type="primary" block onClick={() => setJsonModalVisible(true)}>
            <FileTextOutlined /> 输入JSON数据
          </Button>
        </Space>
      )}

      <Space style={{ marginTop: 12, width: '100%' }} direction="vertical">
        <Button danger block onClick={handleClear}>
          <ClearOutlined /> 清空数据库
        </Button>
      </Space>

      <Modal
        title="输入JSON数据"
        open={jsonModalVisible}
        onOk={handleJsonImport}
        onCancel={() => setJsonModalVisible(false)}
        width={600}
        okText="导入"
        cancelText="取消"
      >
        <p style={{ color: '#999', marginBottom: 8, fontSize: 12 }}>
          格式示例:
          <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, fontSize: 11 }}>
            {sampleJson}
          </pre>
        </p>
        <TextArea
          value={jsonInput}
          onChange={(e) => setJsonInput(e.target.value)}
          placeholder="请输入JSON格式的图数据..."
          rows={12}
          style={{ fontFamily: 'monospace', fontSize: 12 }}
        />
      </Modal>
    </div>
  )
}

export default DataUpload
