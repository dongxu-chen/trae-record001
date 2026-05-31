import React, { useState, useEffect } from 'react'
import {
  Card,
  Descriptions,
  Button,
  Space,
  message,
  Row,
  Col,
  Tag,
  Popconfirm,
  Tabs,
} from 'antd'
import {
  ArrowLeftOutlined,
  RollbackOutlined,
  DiffOutlined,
  ApiOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { auditApi } from '../services/api'

function AuditLogDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [log, setLog] = useState(null)
  const [diff, setDiff] = useState(null)
  const [structDiff, setStructDiff] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('struct')

  useEffect(() => {
    loadData()
  }, [id])

  const loadData = async () => {
    setLoading(true)
    try {
      const [logData, diffData] = await Promise.all([
        auditApi.getLog(id),
        auditApi.getDiff(id),
      ])
      setLog(logData)
      setDiff(diffData)

      if (logData.content_type === 'json' || logData.content_type === 'yaml' || logData.content_type === 'yml') {
        try {
          const structDiffData = await auditApi.getStructDiff(id)
          setStructDiff(structDiffData)
        } catch (e) {
          console.log('Structured diff not available')
        }
      }
    } catch (error) {
      message.error('加载详情失败')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleRollback = async () => {
    try {
      await auditApi.rollback(id, 'admin')
      message.success('回滚成功')
      navigate('/')
    } catch (error) {
      message.error('回滚失败: ' + error.message)
    }
  }

  const renderDiff = () => {
    if (!diff || !diff.lines) return null

    return diff.lines.map((line, index) => {
      let className = 'diff-unchanged'
      let prefix = '  '

      if (line.type === 'added') {
        className = 'diff-added'
        prefix = '+ '
      } else if (line.type === 'removed') {
        className = 'diff-removed'
        prefix = '- '
      }

      return (
        <div key={index} className={className}>
          <span style={{ opacity: 0.5, marginRight: '8px' }}>
            {line.line_no || ''}
          </span>
          {prefix}
          {line.content || ' '}
        </div>
      )
    })
  }

  const renderStructDiff = () => {
    if (!structDiff || !structDiff.changes) return <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>无结构化差异</div>

    return structDiff.changes.map((change, index) => {
      let className = ''
      let prefix = ''
      let content = ''

      switch (change.type) {
        case 'added':
          className = 'diff-added'
          prefix = '+ '
          content = `${change.path} = ${JSON.stringify(change.new_value)}`
          break
        case 'removed':
          className = 'diff-removed'
          prefix = '- '
          content = `${change.path} = ${JSON.stringify(change.old_value)}`
          break
        case 'modified':
          className = 'diff-modified'
          prefix = '~ '
          content = `${change.path}: ${JSON.stringify(change.old_value)} → ${JSON.stringify(change.new_value)}`
          break
        default:
          return null
      }

      return (
        <div key={index} className={className} style={{ padding: '2px 8px', margin: '1px 0' }}>
          <span style={{ fontWeight: 'bold' }}>{prefix}</span>
          {content}
        </div>
      )
    })
  }

  const getActionColor = (action) => {
    switch (action) {
      case 'CREATE':
        return 'success'
      case 'UPDATE':
        return 'processing'
      case 'DELETE':
        return 'error'
      case 'ROLLBACK':
        return 'warning'
      default:
        return 'default'
    }
  }

  if (loading) {
    return <Card loading={true} />
  }

  if (!log) {
    return <Card>未找到记录</Card>
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回列表
        </Button>
        {log.action !== 'DELETE' && (
          <Popconfirm
            title="确认回滚"
            description="确定要将配置回滚到此版本吗？"
            onConfirm={handleRollback}
            okText="确定"
            cancelText="取消"
          >
            <Button type="primary" danger icon={<RollbackOutlined />}>
              回滚到此版本
            </Button>
          </Popconfirm>
        )}
      </Space>

      <Card title="基本信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="命名空间">
            {log.namespace_id}
          </Descriptions.Item>
          <Descriptions.Item label="分组">{log.group}</Descriptions.Item>
          <Descriptions.Item label="DataID">{log.data_id}</Descriptions.Item>
          <Descriptions.Item label="操作类型">
            <Tag color={getActionColor(log.action)}>{log.action}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="操作人">{log.operator}</Descriptions.Item>
          <Descriptions.Item label="操作IP">{log.operator_ip || '-'}</Descriptions.Item>
          <Descriptions.Item label="合规检查">
            {log.compliance_pass === null || log.compliance_pass === undefined ? (
              <Tag color="default">未检查</Tag>
            ) : log.compliance_pass ? (
              <Tag color="success">通过</Tag>
            ) : (
              <Tag color="error">不通过</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="变更时间">
            {dayjs(log.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {log.compliance_msg && (
            <Descriptions.Item label="合规说明" span={2}>
              {log.compliance_msg}
            </Descriptions.Item>
          )}
          {log.desc && (
            <Descriptions.Item label="备注" span={2}>
              {log.desc}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card
        title={
          <Space>
            <DiffOutlined />
            变更对比
          </Space>
        }
      >
        {structDiff && structDiff.changes && structDiff.changes.length > 0 ? (
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'struct',
                label: (
                  <span>
                    <ApiOutlined /> 结构化对比
                    <Tag color="green" style={{ marginLeft: 8 }}>
                      +{structDiff.added_count} -{structDiff.removed_count} ~{structDiff.modified_count}
                    </Tag>
                  </span>
                ),
                children: (
                  <div className="diff-container" style={{ maxHeight: '500px', overflow: 'auto' }}>
                    {renderStructDiff()}
                  </div>
                ),
              },
              {
                key: 'line',
                label: (
                  <span>
                    <DiffOutlined /> 行级对比
                    {diff && (
                      <Tag color="blue" style={{ marginLeft: 8 }}>
                        +{diff.added_count} -{diff.removed_count}
                      </Tag>
                    )}
                  </span>
                ),
                children: (
                  <div className="diff-container" style={{ maxHeight: '500px', overflow: 'auto' }}>
                    {renderDiff()}
                  </div>
                ),
              },
            ]}
          />
        ) : (
          <div className="diff-container" style={{ maxHeight: '500px', overflow: 'auto' }}>
            {renderDiff()}
          </div>
        )}
      </Card>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="变更前内容" size="small">
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                maxHeight: '300px',
                overflow: 'auto',
                fontSize: '12px',
              }}
            >
              {log.old_content || '(空)'}
            </pre>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="变更后内容" size="small">
            <pre
              style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                maxHeight: '300px',
                overflow: 'auto',
                fontSize: '12px',
              }}
            >
              {log.new_content || '(空)'}
            </pre>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default AuditLogDetail
