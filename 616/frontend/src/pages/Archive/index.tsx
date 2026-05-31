import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Row,
  Col,
  Tabs,
  InputNumber,
  Descriptions,
  List,
  Tooltip,
} from 'antd'
import {
  InboxOutlined,
  SearchOutlined,
  ReloadOutlined,
  RollbackOutlined,
  FileTextOutlined,
  CalendarOutlined,
  OrderedListOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import {
  getArchiveIndexList,
  searchArchiveMessages,
  restoreArchiveMessage,
} from '@/services/api'
import type { ArchiveIndex, DeadLetterMessage, MqTypeEnum, DeadReasonTypeEnum } from '@/types'

const { Option } = Select
const { TabPane } = Tabs

const Archive: React.FC = () => {
  const [indexLoading, setIndexLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [indexList, setIndexList] = useState<ArchiveIndex[]>([])
  const [messageList, setMessageList] = useState<DeadLetterMessage[]>([])
  const [total, setTotal] = useState(0)
  const [pageNum, setPageNum] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [selectedIndex, setSelectedIndex] = useState<string>('')
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [selectedItems, setSelectedItems] = useState<DeadLetterMessage[]>([])
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [currentDetail, setCurrentDetail] = useState<DeadLetterMessage | null>(null)
  const [searchForm] = Form.useForm()

  const fetchIndexList = async () => {
    setIndexLoading(true)
    try {
      const result = await getArchiveIndexList()
      setIndexList(result)
      if (result.length > 0 && !selectedIndex) {
        setSelectedIndex(result[0].indexName)
      }
    } catch (error) {
      console.error('Failed to fetch archive index list:', error)
    } finally {
      setIndexLoading(false)
    }
  }

  const fetchMessageList = async () => {
    if (!selectedIndex) return
    setSearchLoading(true)
    try {
      const values = searchForm.getFieldsValue()
      const result = await searchArchiveMessages({
        indexName: selectedIndex,
        keyword: values.keyword,
        pageNum,
        pageSize,
      })
      setMessageList(result.list)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to search archive messages:', error)
    } finally {
      setSearchLoading(false)
    }
  }

  useEffect(() => {
    fetchIndexList()
  }, [])

  useEffect(() => {
    if (selectedIndex) {
      fetchMessageList()
    }
  }, [selectedIndex, pageNum, pageSize])

  const handleSearch = () => {
    setPageNum(1)
    fetchMessageList()
  }

  const handleReset = () => {
    searchForm.resetFields()
    setPageNum(1)
    fetchMessageList()
  }

  const handleViewDetail = (record: DeadLetterMessage) => {
    setCurrentDetail(record)
    setDetailModalOpen(true)
  }

  const handleRestore = (record: DeadLetterMessage) => {
    Modal.confirm({
      title: '恢复确认',
      icon: <RollbackOutlined style={{ color: '#faad14' }} />,
      content: `确定要恢复消息「${record.messageId}」吗？恢复后消息将移至死信列表中。`,
      okText: '确认恢复',
      cancelText: '取消',
      onOk: async () => {
        try {
          await restoreArchiveMessage([record.id], selectedIndex)
          message.success('恢复成功')
          fetchMessageList()
        } catch (error) {
          console.error('Restore failed:', error)
        }
      },
    })
  }

  const handleBatchRestore = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要恢复的消息')
      return
    }
    Modal.confirm({
      title: '批量恢复确认',
      content: `确定要恢复选中的 ${selectedRowKeys.length} 条消息吗？`,
      okText: '确认恢复',
      cancelText: '取消',
      onOk: async () => {
        try {
          await restoreArchiveMessage(selectedRowKeys as string[], selectedIndex)
          message.success(`成功恢复 ${selectedRowKeys.length} 条消息`)
          setSelectedRowKeys([])
          setSelectedItems([])
          fetchMessageList()
        } catch (error) {
          console.error('Batch restore failed:', error)
        }
      },
    })
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

  const indexColumns = [
    {
      title: '索引名称',
      dataIndex: 'indexName',
      key: 'indexName',
      width: 200,
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: 13 }}>{text}</span>
      ),
    },
    {
      title: '日期范围',
      key: 'dateRange',
      width: 250,
      render: (_: unknown, record: ArchiveIndex) => (
        <Space direction="vertical" size={0}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <CalendarOutlined style={{ color: '#1890ff' }} />
            开始：{record.startDate}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <CalendarOutlined style={{ color: '#52c41a' }} />
            结束：{record.endDate}
          </span>
        </Space>
      ),
    },
    {
      title: '消息总数',
      dataIndex: 'totalCount',
      key: 'totalCount',
      width: 120,
      render: (count: number) => (
        <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
          <DatabaseOutlined style={{ marginRight: 4 }} />
          {count.toLocaleString()}
        </Tag>
      ),
    },
    {
      title: '归档时间',
      dataIndex: 'archiveTime',
      key: 'archiveTime',
      width: 170,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: ArchiveIndex) => (
        <Button
          type={selectedIndex === record.indexName ? 'primary' : 'default'}
          size="small"
          onClick={() => {
            setSelectedIndex(record.indexName)
            setPageNum(1)
          }}
        >
          {selectedIndex === record.indexName ? '已选中' : '查看'}
        </Button>
      ),
    },
  ]

  const messageColumns = [
    {
      title: '消息ID',
      dataIndex: 'messageId',
      key: 'messageId',
      ellipsis: true,
      width: 180,
      render: (text: string) => (
        <Tooltip title={text}>
          <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{text}</span>
        </Tooltip>
      ),
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
      title: '死信原因',
      dataIndex: 'deadReason',
      key: 'deadReason',
      ellipsis: true,
      width: 200,
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
            icon={<FileTextOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<RollbackOutlined />}
            onClick={() => handleRestore(record)}
          >
            恢复
          </Button>
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
    <Card
      title={
        <Space>
          <InboxOutlined style={{ color: '#1890ff' }} />
          归档管理
        </Space>
      }
    >
      <Tabs defaultActiveKey="1">
        <TabPane
          tab={
            <Space>
              <OrderedListOutlined />
              归档索引列表
            </Space>
          }
          key="1"
        >
          <Card type="inner" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <Button icon={<ReloadOutlined />} onClick={fetchIndexList}>
                刷新
              </Button>
              <span style={{ marginLeft: 12, color: '#666' }}>
                共 <span style={{ color: '#1890ff', fontWeight: 'bold' }}>{indexList.length}</span> 个归档索引
              </span>
            </div>
            <Table
              columns={indexColumns}
              dataSource={indexList}
              rowKey="id"
              loading={indexLoading}
              pagination={false}
              scroll={{ x: 800 }}
            />
          </Card>
        </TabPane>

        <TabPane
          tab={
            <Space>
              <SearchOutlined />
              归档消息查询
            </Space>
          }
          key="2"
        >
          <Card type="inner">
            <Form form={searchForm} layout="vertical" onFinish={handleSearch}>
              <Row gutter={16}>
                <Col xs={24} sm={12} md={8}>
                  <Form.Item label="归档索引">
                    <Select
                      value={selectedIndex}
                      onChange={(value) => {
                        setSelectedIndex(value)
                        setPageNum(1)
                      }}
                      placeholder="请选择归档索引"
                      loading={indexLoading}
                    >
                      {indexList.map((item) => (
                        <Option key={item.indexName} value={item.indexName}>
                          {item.indexName} ({item.totalCount}条)
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={12}>
                  <Form.Item name="keyword" label="关键词">
                    <Input placeholder="请输入消息ID或Topic" allowClear prefix={<SearchOutlined />} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12} md={4}>
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

            <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
              <Button
                type="primary"
                icon={<RollbackOutlined />}
                onClick={handleBatchRestore}
                disabled={selectedRowKeys.length === 0}
              >
                批量恢复
              </Button>
              <span style={{ alignSelf: 'center', marginLeft: 'auto', color: '#666' }}>
                已选择 <span style={{ color: '#1890ff', fontWeight: 'bold' }}>{selectedRowKeys.length}</span> 项
              </span>
            </div>

            <Table
              rowSelection={rowSelection}
              columns={messageColumns}
              dataSource={messageList}
              rowKey="id"
              loading={searchLoading}
              scroll={{ x: 1000 }}
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
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title="归档消息详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setDetailModalOpen(false)}>关闭</Button>
            <Button
              type="primary"
              icon={<RollbackOutlined />}
              onClick={() => {
                if (currentDetail) {
                  handleRestore(currentDetail)
                  setDetailModalOpen(false)
                }
              }}
            >
              恢复消息
            </Button>
          </Space>
        }
        width={800}
      >
        {currentDetail && (
          <div>
            <Descriptions column={2} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="消息ID">{currentDetail.messageId}</Descriptions.Item>
              <Descriptions.Item label="MQ类型">{getMqTypeName(currentDetail.mqType)}</Descriptions.Item>
              <Descriptions.Item label="Topic">{currentDetail.topic}</Descriptions.Item>
              <Descriptions.Item label="原因类型">
                <Tag color={getReasonTypeColor(currentDetail.deadReasonType)}>
                  {getReasonTypeName(currentDetail.deadReasonType)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{currentDetail.createTime}</Descriptions.Item>
              <Descriptions.Item label="重试次数">{currentDetail.retryCount}</Descriptions.Item>
              <Descriptions.Item label="死信原因" span={2}>
                <span style={{ color: '#cf1322' }}>{currentDetail.deadReason}</span>
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginBottom: 12, fontWeight: 500 }}>消息内容：</div>
            <pre
              style={{
                maxHeight: 200,
                overflow: 'auto',
                background: '#f6f8fa',
                padding: 12,
                borderRadius: 4,
                fontSize: 12,
                fontFamily: 'Consolas, Monaco, monospace',
              }}
            >
              <code>{formatJson(currentDetail.content)}</code>
            </pre>

            <div style={{ marginTop: 16, marginBottom: 12, fontWeight: 500 }}>异常堆栈：</div>
            <pre
              style={{
                maxHeight: 200,
                overflow: 'auto',
                background: '#fff1f0',
                padding: 12,
                borderRadius: 4,
                fontSize: 11,
                fontFamily: 'Consolas, Monaco, monospace',
                color: '#cf1322',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              <code>{currentDetail.stackTrace}</code>
            </pre>
          </div>
        )}
      </Modal>
    </Card>
  )
}

export default Archive
