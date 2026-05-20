import React from 'react'
import { Button, Space, Modal, Input, message } from 'antd'
import {
  PlayCircleOutlined,
  DownloadOutlined,
  UploadOutlined,
  ClearOutlined
} from '@ant-design/icons'

const Toolbar = ({
  nodes,
  edges,
  onPreview,
  onExport,
  onImport,
  onClear
}) => {
  const [importModalVisible, setImportModalVisible] = React.useState(false)
  const [importJson, setImportJson] = React.useState('')

  const handleExport = () => {
    const config = { nodes, edges }
    const jsonStr = JSON.stringify(config, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'form-flow-config.json'
    a.click()
    URL.revokeObjectURL(url)
    message.success('导出成功！')
  }

  const handleImport = () => {
    try {
      const config = JSON.parse(importJson)
      if (config.nodes && config.edges) {
        onImport(config.nodes, config.edges)
        setImportModalVisible(false)
        setImportJson('')
        message.success('导入成功！')
      } else {
        message.error('配置格式不正确')
      }
    } catch (e) {
      message.error('JSON解析失败')
    }
  }

  return (
    <>
      <div className="toolbar">
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={onPreview}
          >
            预览表单
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            导出JSON
          </Button>
          <Button
            icon={<UploadOutlined />}
            onClick={() => setImportModalVisible(true)}
          >
            导入JSON
          </Button>
          <Button
            danger
            icon={<ClearOutlined />}
            onClick={onClear}
          >
            清空画布
          </Button>
        </Space>
      </div>

      <Modal
        title="导入配置"
        open={importModalVisible}
        onOk={handleImport}
        onCancel={() => setImportModalVisible(false)}
        okText="导入"
        cancelText="取消"
      >
        <Input.TextArea
          rows={15}
          placeholder="请粘贴JSON配置"
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          style={{ fontFamily: 'monospace' }}
        />
      </Modal>
    </>
  )
}

export default Toolbar
