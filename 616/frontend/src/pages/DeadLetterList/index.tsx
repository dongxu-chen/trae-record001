import { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Table,
  Tag,
  Space,
  message,
  Modal,
  Row,
  Col,
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  InboxOutlined,
  CloseCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  getDeadLetterList,
  archiveDeadLetter,
  ignoreDeadLetter,
} from '@/services/api'
import ReplayModal from '@/components/ReplayModal'
import type { DeadLetterMessage, DeadReasonTypeEnum, MqTypeEnum, ProcessStatusEnum } from '@/types'

const { RangePicker } = DatePicker
const { Option } = Select

const DeadLetterList: React.FC = () => {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [dataList, setDataList] = useState<DeadLetterMessage[]>([])
  const [total, setTotal] = useState(0)
  const [pageNum, setPageNum] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [selectedItems, setSelectedItems] = useState<DeadLetterMessage[]>([])
  const [replayModalOpen, setReplayModalOpen] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const values = form.getFieldsValue()
      const params = {
        keyword: values.keyword,
        mqType: values.mqType,
        reasonType: values.reasonType,
        status: values.status,
        startTime: values.timeRange ? dayjs(values.timeRange[0]).format('YYYY-MM-DD HH:mm:ss') : undefined,
        endTime: values.timeRange ? dayjs(values.timeRange[1]).format('YYYY-MM-DD HH:mm:ss') : undefined,
        pageNum,
        pageSize,
      }
      const result = await getDeadLetterList(params)
      setDataList(result.list)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to fetch dead letter list:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [pageNum, pageSize])

  const handleSearch = () => {
    setPageNum(1)
    fetchData()
  }

  const handleReset = () => {
    form.resetFields()
    setPageNum(1)
    fetchData()
  }

  const handleBatchReplay = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要重放的消息')
      return
    }
    setReplayModalOpen(true)
  }

  const handleBatchArchive = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要归档的消息')
      return
    }
    Modal.confirm({
      title: '批量归档确认',
      content: `确定要归档选中的 ${selectedRowKeys.length} 条消息吗？`,
      okText: '确认归档',
      cancelText: '取消',
      onOk: async () => {
        try {
          await archiveDeadLetter(selectedRowKeys as string[])
          message.success(`成功归档 ${selectedRowKeys.length} 条消息`)
          setSelectedRowKeys([])
          setSelectedItems([])
          fetchData()
        } catch (error) {
          console.error('Archive failed:', error)
        }
      },
    })
  }

  const handleBatchIgnore = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要忽略的消息')
      return
    }
    Modal.confirm({
      title: '批量忽略确认',
      content: `确定要忽略选中的 ${selectedRowKeys.length} 条消息吗？`,
      okText: '确认忽略',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await ignoreDeadLetter(selectedRowKeys as string[])
          message.success(`成功忽略 ${selectedRowKeys.length} 条消息`)
          setSelectedRowKeys([])
          setSelectedItems([])
          fetchData()
        } catch (error) {
          console.error('Ignore failed:', error)
        }
      },
    })
  }

  const handleReplaySuccess = () => {
    setSelectedRowKeys([])
    setSelectedItems([])
    fetchData()
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

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (_: unknown, __: DeadLetterMessage, index: number) => (pageNum - 1) * pageSize + index + 1,
    },
    {
      title: '消息ID',
      dataIndex: 'messageId',
      key: 'messageId',
      ellipsis: true,
      width: 180,
      render: (text: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>,
    },
    {
      title: 'MQ类型',
      dataIndex: 'mqType',
      key: 'mqType',
      width: 100,
      render: (text: MqTypeEnum) => <Tag>{getMqTypeName(text)}</Tag>,
    },
    {
      title: 'Topic',
      dataIndex: 'topic',
      key: 'topic',
      ellipsis: true,
      width: 150,
    },
    {
      title: '原因类型',
      dataIndex: 'deadReasonType',
      key: 'deadReasonType',
      width: 100,
      render: (type: DeadReasonTypeEnum) => (
        <Tag color={getReasonTypeColor(type)}>{getReasonTypeName(type)}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'processStatus',
      key: 'processStatus',
      width: 90,
      render: (status: ProcessStatusEnum) => (
        <Tag color={getStatusColor(status)}>{getStatusName(status)}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 170,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: DeadLetterMessage) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/dead-letter/${record.id}`)}
          >
            详情
          </Button>
          {record.processStatus === 'PENDING' && (
            <>
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => {
                  setSelectedItems([record])
                  setReplayModalOpen(true)
                }}
              >
                重放
              </Button>
              <Button
                type="link"
                size="small"
                icon={<InboxOutlined />}
                onClick={() => {
                  Modal.confirm({
                    title: '归档确认',
                    content: `确定要归档该消息吗？`,
                    okText: '确认归档',
                    cancelText: '取消',
                    onOk: async () => {
                      try {
                        await archiveDeadLetter([record.id])
                        message.success('归档成功')
                        fetchData()
                      } catch (error) {
                        console.error('Archive failed:', error)
                      }
                    },
                  })
                }}
              >
                归档
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[], selectedRows: DeadLetterMessage[]) => {
      setSelectedRowKeys(newSelectedRowKeys)
      setSelectedItems(selectedRows)
    },
  }

  return (
    <Card>
      <Form form={form} layout="vertical" onFinish={handleSearch}>
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="keyword" label="关键词">
              <Input placeholder="请输入消息ID或Topic" allowClear prefix={<SearchOutlined />} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="mqType" label="MQ类型">
              <Select placeholder="请选择MQ类型" allowClear>
                <Option value="RABBITMQ">RabbitMQ</Option>
                <Option value="ROCKETMQ">RocketMQ</Option>
                <Option value="KAFKA">Kafka</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="reasonType" label="原因类型">
              <Select placeholder="请选择原因类型" allowClear>
                <Option value="BIZ_EXCEPTION">业务异常</Option>
                <Option value="TIMEOUT">超时异常</Option>
                <Option value="REJECTED">被拒绝</Option>
                <Option value="FORMAT_ERROR">格式错误</Option>
                <Option value="NULL_POINTER">空指针</Option>
                <Option value="DATABASE_ERROR">数据库错误</Option>
                <Option value="OTHER">其他</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="status" label="状态">
              <Select placeholder="请选择状态" allowClear>
                <Option value="PENDING">待处理</Option>
                <Option value="REPLAYED">已重放</Option>
                <Option value="ARCHIVED">已归档</Option>
                <Option value="IGNORED">已忽略</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={16} lg={12}>
            <Form.Item name="timeRange" label="时间范围">
              <RangePicker
                showTime
                style={{ width: '100%' }}
                placeholder={['开始时间', '结束时间']}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8} lg={12}>
            <Form.Item label="&nbsp;">
              <Space>
                <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
                  搜索
                </Button>
                <Button onClick={handleReset} icon={<ReloadOutlined />}>
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Col>
        </Row>
      </Form>

      <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleBatchReplay}
          disabled={selectedRowKeys.length === 0}
        >
          批量重放
        </Button>
        <Button
          icon={<InboxOutlined />}
          onClick={handleBatchArchive}
          disabled={selectedRowKeys.length === 0}
        >
          批量归档
        </Button>
        <Button
          danger
          icon={<CloseCircleOutlined />}
          onClick={handleBatchIgnore}
          disabled={selectedRowKeys.length === 0}
        >
          批量忽略
        </Button>
        <span style={{ alignSelf: 'center', marginLeft: 'auto', color: '#666' }}>
          已选择 <span style={{ color: '#1890ff', fontWeight: 'bold' }}>{selectedRowKeys.length}</span> 项
        </span>
      </div>

      <Table
        rowSelection={rowSelection}
        columns={columns}
        dataSource={dataList}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1100 }}
        pagination={{
          current: pageNum,
          pageSize,
          total,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (totalNum) => `共 ${totalNum} 条记录`,
          onChange: (page, size) => {
            setPageNum(page)
            setPageSize(size)
          },
        }}
      />

      <ReplayModal
        open={replayModalOpen}
        onCancel={() => setReplayModalOpen(false)}
        onSuccess={handleReplaySuccess}
        selectedItems={selectedItems}
        mode={selectedItems.length > 1 ? 'batch' : 'single'}
      />
    </Card>
  )
}

export default DeadLetterList
