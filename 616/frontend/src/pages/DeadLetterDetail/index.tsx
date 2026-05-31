import { useState, useEffect } from 'react'
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Row,
  Col,
  message,
  Modal,
  Spin,
  Typography,
  Divider,
  Breadcrumb,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  InboxOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  BugOutlined,
  HistoryOutlined,
  RefreshOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getDeadLetterDetail,
  analyzeDeadLetter,
  archiveDeadLetter,
  ignoreDeadLetter,
} from '@/services/api'
import AnalysisResult from '@/components/AnalysisResult'
import ReplayModal from '@/components/ReplayModal'
import type { DeadLetterMessage, DeadLetterAnalysisResult, MqTypeEnum, DeadReasonTypeEnum, ProcessStatusEnum } from '@/types'

const { Text, Paragraph } = Typography

const DeadLetterDetail: React.FC = () => {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [detail, setDetail] = useState<DeadLetterMessage | null>(null)
  const [analysisResult, setAnalysisResult] = useState<DeadLetterAnalysisResult | null>(null)
  const [replayModalOpen, setReplayModalOpen] = useState(false)

  const fetchDetail = async () => {
    if (!id) return
    setLoading(true)
    try {
      const result = await getDeadLetterDetail(id)
      setDetail(result)
      if (result.analysisResult) {
        setAnalysisResult(result.analysisResult)
      }
    } catch (error) {
      console.error('Failed to fetch dead letter detail:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDetail()
  }, [id])

  const handleAnalyze = async () => {
    if (!id) return
    setAnalyzing(true)
    try {
      const result = await analyzeDeadLetter(id)
      setAnalysisResult(result)
      message.success('分析完成')
    } catch (error) {
      console.error('Failed to analyze:', error)
      message.error('分析失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleArchive = () => {
    if (!id) return
    Modal.confirm({
      title: '归档确认',
      content: '确定要归档该消息吗？',
      okText: '确认归档',
      cancelText: '取消',
      onOk: async () => {
        try {
          await archiveDeadLetter([id])
          message.success('归档成功')
          fetchDetail()
        } catch (error) {
          console.error('Archive failed:', error)
        }
      },
    })
  }

  const handleIgnore = () => {
    if (!id) return
    Modal.confirm({
      title: '忽略确认',
      content: '确定要忽略该消息吗？忽略后将不再处理。',
      okText: '确认忽略',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await ignoreDeadLetter([id])
          message.success('已忽略')
          fetchDetail()
        } catch (error) {
          console.error('Ignore failed:', error)
        }
      },
    })
  }

  const handleReplaySuccess = () => {
    fetchDetail()
  }

  const formatJson = (jsonStr: string) => {
    try {
      const parsed = JSON.parse(jsonStr)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return jsonStr
    }
  }

  const getReasonTypeColor = (type: DeadReasonTypeEnum) => {
    const colorMap: Record<string, string> = {
      BIZ_EXCEPTION: 'red',
      TIMEOUT: 'orange',
      REJECTED: 'gold',
      FORMAT_ERROR: 'purple',
      NULL_POINTER: 'magenta',
      DATABASE_ERROR: 'volcano',
      OTHER: 'default',
    }
    return colorMap[type] || 'default'
  }

  const getReasonTypeName = (type: DeadReasonTypeEnum) => {
    const nameMap: Record<string, string> = {
      BIZ_EXCEPTION: '业务异常',
      TIMEOUT: '超时异常',
      REJECTED: '被拒绝',
      FORMAT_ERROR: '格式错误',
      NULL_POINTER: '空指针',
      DATABASE_ERROR: '数据库错误',
      OTHER: '其他',
    }
    return nameMap[type] || type
  }

  const getMqTypeName = (type: MqTypeEnum) => {
    const nameMap: Record<string, string> = {
      RABBITMQ: 'RabbitMQ',
      ROCKETMQ: 'RocketMQ',
      KAFKA: 'Kafka',
    }
    return nameMap[type] || type
  }

  const getStatusColor = (status: ProcessStatusEnum) => {
    const colorMap: Record<string, string> = {
      PENDING: 'processing',
      REPLAYED: 'success',
      ARCHIVED: 'default',
      IGNORED: 'warning',
    }
    return colorMap[status] || 'default'
  }

  const getStatusName = (status: ProcessStatusEnum) => {
    const nameMap: Record<string, string> = {
      PENDING: '待处理',
      REPLAYED: '已重放',
      ARCHIVED: '已归档',
      IGNORED: '已忽略',
    }
    return nameMap[status] || status
  }

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16 }}>
        <Breadcrumb>
          <Breadcrumb.Item onClick={() => navigate('/dead-letter')} style={{ cursor: 'pointer' }}>
            死信列表
          </Breadcrumb.Item>
          <Breadcrumb.Item>详情</Breadcrumb.Item>
        </Breadcrumb>
      </div>

      <Card
        title={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dead-letter')}>
              返回
            </Button>
            <span>死信详情</span>
          </Space>
        }
        extra={
          detail && detail.processStatus === 'PENDING' && (
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => detail && setReplayModalOpen(true)}
              >
                重放
              </Button>
              <Button icon={<InboxOutlined />} onClick={handleArchive}>
                归档
              </Button>
              <Button danger icon={<CloseCircleOutlined />} onClick={handleIgnore}>
                忽略
              </Button>
            </Space>
          )
        }
      >
        {detail && (
          <>
            <Card
              type="inner"
              title={
                <Space>
                  <FileTextOutlined />
                  基本信息
                </Space>
              }
              style={{ marginBottom: 16 }}
            >
              <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" bordered>
                <Descriptions.Item label="消息ID">
                  <Text code copyable>{detail.messageId}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="MQ类型">
                  <Tag>{getMqTypeName(detail.mqType)}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Topic">
                  <Text strong>{detail.topic}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="原因类型">
                  <Tag color={getReasonTypeColor(detail.deadReasonType)}>
                    {getReasonTypeName(detail.deadReasonType)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={getStatusColor(detail.processStatus)}>
                    {getStatusName(detail.processStatus)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="重试次数">
                  <Text type={detail.retryCount > 3 ? 'danger' : 'secondary'}>
                    {detail.retryCount}
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <HistoryOutlined />
                    {detail.createTime}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="更新时间">
                  {detail.updateTime}
                </Descriptions.Item>
                <Descriptions.Item label="死信原因" span={3}>
                  <Text type="danger">{detail.deadReason}</Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card
                  type="inner"
                  title={
                    <Space>
                      <FileTextOutlined />
                      消息内容
                    </Space>
                  }
                  extra={
                    <Button size="small" onClick={() => navigator.clipboard.writeText(detail.content)}>
                      复制
                    </Button>
                  }
                >
                  <pre
                    style={{
                      maxHeight: 400,
                      overflow: 'auto',
                      background: '#f6f8fa',
                      padding: 16,
                      borderRadius: 4,
                      fontSize: 13,
                      fontFamily: 'Consolas, Monaco, monospace',
                    }}
                  >
                    <code>{formatJson(detail.content)}</code>
                  </pre>
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card
                  type="inner"
                  title={
                    <Space>
                      <BugOutlined />
                      异常堆栈
                    </Space>
                  }
                  extra={
                    <Button size="small" onClick={() => navigator.clipboard.writeText(detail.stackTrace)}>
                      复制
                    </Button>
                  }
                >
                  <pre
                    style={{
                      maxHeight: 400,
                      overflow: 'auto',
                      background: '#fff1f0',
                      padding: 16,
                      borderRadius: 4,
                      fontSize: 12,
                      fontFamily: 'Consolas, Monaco, monospace',
                      color: '#cf1322',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                    }}
                  >
                    <code>{detail.stackTrace}</code>
                  </pre>
                </Card>
              </Col>
            </Row>

            <Divider />

            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<RefreshOutlined />}
                onClick={handleAnalyze}
                loading={analyzing}
              >
                {analysisResult ? '重新分析' : '开始分析'}
              </Button>
              <Text type="secondary" style={{ marginLeft: 12 }}>
                分析死信原因，获取处理建议和修复步骤
              </Text>
            </div>

            <AnalysisResult result={analysisResult!} loading={analyzing} />
          </>
        )}
      </Card>

      <ReplayModal
        open={replayModalOpen}
        onCancel={() => setReplayModalOpen(false)}
        onSuccess={handleReplaySuccess}
        selectedItems={detail ? [detail] : []}
        mode="single"
      />
    </Spin>
  )
}

export default DeadLetterDetail
