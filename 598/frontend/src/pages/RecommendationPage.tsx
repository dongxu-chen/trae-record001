import React, { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Table,
  Select,
  Button,
  Space,
  Alert,
  Progress,
  Tag,
  Tabs,
  List,
  Statistic,
  Row,
  Col,
  Modal,
  Form,
  Input,
  message,
  Spin,
  Divider,
} from 'antd'
const { TabPane } = Tabs
import {
  PartitionOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
  PlusOutlined,
  MinusOutlined,
  SwapOutlined,
  ScissorOutlined,
} from '@ant-design/icons'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { tablesApi, partitionApi } from '../services/api'
import type {
  TableInfo,
  PartitionRecommendation,
  PartitionPlan,
  PartitionDef,
  PartitionOperationRequest,
} from '../types'

const { Title, Paragraph, Text } = Typography
const { Option } = Select

const formatSize = (bytes: number): string => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const formatNumber = (num: number): string => {
  if (!num) return '0'
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`
  return num.toString()
}

const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 70) return 'success'
  if (confidence >= 40) return 'warning'
  return 'error'
}

const RecommendationPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string>(searchParams.get('table') || '')
  const [recommendation, setRecommendation] = useState<PartitionRecommendation | null>(null)
  const [plan, setPlan] = useState<PartitionPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [selectedMethod, setSelectedMethod] = useState<string>('')
  const [selectedColumn, setSelectedColumn] = useState<string>('')
  const [tableInfo, setTableInfo] = useState<TableInfo | null>(null)
  const [showOperationModal, setShowOperationModal] = useState(false)
  const [operationType, setOperationType] = useState<string>('')
  const [selectedPartitions, setSelectedPartitions] = useState<string[]>([])
  const [newPartitionName, setNewPartitionName] = useState('')
  const [newPartitionDescription, setNewPartitionDescription] = useState('')
  const [useOnlineDDL, setUseOnlineDDL] = useState(false)
  const [toolAvailability, setToolAvailability] = useState<{ ptoscAvailable: boolean; ptocsAvailable: boolean } | null>(null)
  const [ptoscCommand, setPtoscCommand] = useState<string>('')
  const [dryRunCommand, setDryRunCommand] = useState<string>('')
  const [showPTOSCCommand, setShowPTOSCCommand] = useState(false)

  useEffect(() => {
    loadTables()
    checkToolAvailability()
  }, [])

  useEffect(() => {
    if (selectedTable) {
      loadRecommendation()
      loadTableInfo()
    }
  }, [selectedTable])

  const checkToolAvailability = async () => {
    try {
      const response = await partitionApi.getToolAvailability()
      setToolAvailability(response.data)
    } catch (error) {
      console.error('Check tool availability error:', error)
    }
  }

  const generatePTOSCCommand = async () => {
    if (!plan) return
    try {
      const response = await partitionApi.generatePTOSC({
        tableName: plan.tableName,
        partitionMethod: plan.partitionMethod,
        partitionExpr: plan.partitionExpr,
        partitions: plan.partitions,
      })
      setPtoscCommand(response.data.command)
      setDryRunCommand(response.data.dryRunCommand)
      setShowPTOSCCommand(true)
    } catch (error) {
      message.error('生成pt-online-schema-change命令失败')
    }
  }

  const loadTables = async () => {
    try {
      const response = await tablesApi.getList()
      setTables(response.data || [])
    } catch (error) {
      message.error('加载表列表失败')
    }
  }

  const loadRecommendation = async () => {
    try {
      setLoading(true)
      const response = await partitionApi.getRecommendation(selectedTable)
      setRecommendation(response.data)
      setSelectedMethod(response.data?.recommendedMethod || '')
      setSelectedColumn(response.data?.partitionColumn || '')
      setPlan(null)
    } catch (error) {
      message.error('加载推荐失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTableInfo = async () => {
    try {
      const response = await tablesApi.getInfo(selectedTable)
      setTableInfo(response.data)
    } catch (error) {
      console.error('Load table info error:', error)
    }
  }

  const generatePlan = async () => {
    if (!selectedMethod || !selectedColumn) {
      message.warning('请选择分区方式和分区字段')
      return
    }

    try {
      setGenerating(true)
      const response = await partitionApi.generatePlan(selectedTable, selectedMethod, selectedColumn)
      setPlan(response.data)
    } catch (error) {
      message.error('生成分区计划失败')
    } finally {
      setGenerating(false)
    }
  }

  const executePlan = async () => {
    if (!plan) return

    const executeAction = useOnlineDDL ? partitionApi.executeOnlineDDL : partitionApi.executePlan
    const modeText = useOnlineDDL ? '在线DDL（无锁）' : '直接ALTER'

    Modal.confirm({
      title: '确认执行分区',
      icon: <WarningOutlined />,
      content: (
        <div>
          <p>执行分区操作可能需要较长时间，特别是对于大表。</p>
          <p>执行模式: <strong>{modeText}</strong></p>
          <p>预计执行时间: {plan.estimatedTimeSec} 秒</p>
          {useOnlineDDL && (
            <Alert
              type="info"
              message="在线DDL模式"
              description="使用pt-online-schema-change执行无锁操作，避免表锁定"
              style={{ marginTop: 8 }}
            />
          )}
          <p style={{ marginTop: 8 }}><strong>请确保已备份数据！</strong></p>
        </div>
      ),
      okText: '确认执行',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await executeAction(plan, useOnlineDDL)
          if (response.data?.success) {
            message.success('分区执行成功')
            loadRecommendation()
          } else {
            message.error(response.data?.message || '执行失败')
          }
        } catch (error: any) {
          message.error(error.response?.data?.message || '执行失败')
        }
      },
    })
  }

  const handleOperation = async () => {
    const req: PartitionOperationRequest = {
      tableName: selectedTable,
      operation: operationType,
      partitionNames: selectedPartitions,
      newPartitions: operationType === 'ADD' || operationType === 'MERGE' || operationType === 'SPLIT'
        ? [{
            partitionName: newPartitionName,
            partitionDescription: newPartitionDescription,
            partitionMethod: tableInfo?.partitionInfo?.partitionMethod || '',
            partitionExpression: tableInfo?.partitionInfo?.partitionExpr || '',
            partitionOrdinal: 0,
            tableRows: 0,
            dataLength: 0,
            indexLength: 0,
            createTime: '',
            updateTime: '',
            comment: '',
          }]
        : [],
    }

    try {
      const response = await partitionApi.executeOperation(req)
      if (response.data?.success) {
        message.success(`${operationType}操作成功`)
        setShowOperationModal(false)
        loadTableInfo()
      } else {
        message.error(response.data?.message || '操作失败')
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '操作失败')
    }
  }

  const copySQL = (sql: string) => {
    navigator.clipboard.writeText(sql)
    message.success('已复制到剪贴板')
  }

  const downloadSQL = () => {
    if (!plan) return
    const content = plan.sqlStatements.join('\n\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedTable}_partition.sql`
    a.click()
    URL.revokeObjectURL(url)
  }

  const columns = tableInfo?.partitionInfo?.partitions?.map((p) => ({
    title: '选择',
    key: 'select',
    render: (_: any, record: PartitionDef) => (
      <input
        type="checkbox"
        checked={selectedPartitions.includes(record.partitionName)}
        onChange={(e) => {
          if (e.target.checked) {
            setSelectedPartitions([...selectedPartitions, record.partitionName])
          } else {
            setSelectedPartitions(selectedPartitions.filter((p) => p !== record.partitionName))
          }
        }}
      />
    ),
  })) || []

  const allPartitionColumns = [
    ...columns,
    {
      title: '分区名',
      dataIndex: 'partitionName',
      key: 'partitionName',
    },
    {
      title: '描述',
      dataIndex: 'partitionDescription',
      key: 'partitionDescription',
    },
    {
      title: '行数',
      dataIndex: 'tableRows',
      key: 'tableRows',
      render: (v: number) => formatNumber(v),
    },
    {
      title: '大小',
      dataIndex: 'dataLength',
      key: 'dataLength',
      render: (v: number) => formatSize(v),
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={1} style={{ margin: 0 }}>
          <PartitionOutlined style={{ marginRight: 12 }} />
          分区策略推荐
        </Title>
        <Paragraph className="description">
          根据表数据量和增长趋势，智能推荐最佳分区方案
        </Paragraph>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <Space size="large" align="center">
          <span>选择表：</span>
          <Select
            style={{ width: 300 }}
            value={selectedTable}
            onChange={setSelectedTable}
            showSearch
            placeholder="请选择表"
            filterOption={(input, option) =>
              (option?.children as string)?.toLowerCase().includes(input.toLowerCase())
            }
          >
            {tables.map((table) => (
              <Option key={table.tableName} value={table.tableName}>
                {table.tableName} ({formatNumber(table.tableRows)} 行, {formatSize(table.totalSize)})
              </Option>
            ))}
          </Select>
          <Button type="primary" onClick={loadRecommendation} loading={loading}>
            生成推荐
          </Button>
        </Space>
      </Card>

      {recommendation && (
        <Spin spinning={loading}>
          <Alert
            type={recommendation.confidence >= 70 ? 'success' : recommendation.confidence >= 40 ? 'warning' : 'info'}
            showIcon
            icon={<RocketOutlined />}
            message={
              <Space>
                推荐分区方式:
                <Tag color="blue" style={{ fontSize: 14 }}>
                  {recommendation.recommendedMethod}
                </Tag>
                <Tag color={getConfidenceColor(recommendation.confidence)}>
                  置信度: {recommendation.confidence}%
                </Tag>
              </Space>
            }
            description={
              <Space direction="vertical" style={{ width: '100%' }}>
                <p>{recommendation.reason}</p>
                <p>
                  分区字段: <strong>{recommendation.partitionColumn}</strong>
                </p>
                <p>
                  分区表达式: <code>{recommendation.partitionExpr}</code>
                </p>
                <p>
                  预计分区数: <strong>{recommendation.estimatedPartitions}</strong>
                </p>
                <p>
                  预计性能提升: <strong className="confidence-high">{recommendation.estimatedPerfGain}</strong>
                </p>
              </Space>
            }
          />

          {recommendation.alternativeMethods?.length > 0 && (
            <Card title="备选方案" size="small" style={{ marginTop: 16 }}>
              <List
                dataSource={recommendation.alternativeMethods}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <Tag color={getConfidenceColor(item.confidence)}>{item.method}</Tag>
                      <Text type="secondary">{item.reason}</Text>
                      <Text>(置信度: {item.confidence}%)</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          )}

          <Card title="自定义分区方案" style={{ marginTop: 24 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="分区方式" required>
                  <Select value={selectedMethod} onChange={setSelectedMethod}>
                    <Option value="RANGE">RANGE (日期范围分区)</Option>
                    <Option value="RANGE_ID">RANGE_ID (ID范围分区)</Option>
                    <Option value="LIST">LIST (列表分区)</Option>
                    <Option value="HASH">HASH (哈希分区)</Option>
                    <Option value="LINEAR_HASH">LINEAR_HASH (线性哈希分区)</Option>
                    <Option value="KEY">KEY (键值分区)</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="分区字段" required>
                  <Select value={selectedColumn} onChange={setSelectedColumn}>
                    {tableInfo?.columns?.map((col) => (
                      <Option key={col.columnName} value={col.columnName}>
                        {col.columnName} ({col.columnType})
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="&nbsp;">
                  <Button type="primary" onClick={generatePlan} loading={generating} block>
                    生成分区SQL
                  </Button>
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {plan && (
            <Tabs
              style={{ marginTop: 24 }}
              items={[
                {
                  key: 'sql',
                  label: 'SQL 脚本',
                  children: (
                    <Card
                      extra={
                        <Space>
                          <Button icon={<CopyOutlined />} onClick={() => copySQL(plan.sqlStatements.join('\n\n'))}>
                            复制全部
                          </Button>
                          <Button icon={<DownloadOutlined />} onClick={downloadSQL}>
                            下载
                          </Button>
                          <Button
                            icon={<ThunderboltOutlined />}
                            onClick={generatePTOSCCommand}
                            disabled={!toolAvailability?.ptoscAvailable}
                            title={toolAvailability?.ptoscAvailable ? '生成pt-online-schema-change命令' : 'pt-online-schema-change不可用'}
                          >
                            生成在线DDL命令
                          </Button>
                          <Button
                            type="primary"
                            danger
                            icon={<PlayCircleOutlined />}
                            onClick={executePlan}
                          >
                            执行分区
                          </Button>
                        </Space>
                      }
                    >
                      <Alert
                        type="warning"
                        message="执行前请务必备份数据！"
                        description={`预计执行时间: ${plan.estimatedTimeSec} 秒`}
                        style={{ marginBottom: 16 }}
                      />

                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={8}>
                          <Card size="small" title="执行模式">
                            <Space direction="vertical" style={{ width: '100%' }}>
                              <Space>
                                <input
                                  type="radio"
                                  checked={!useOnlineDDL}
                                  onChange={() => setUseOnlineDDL(false)}
                                />
                                <span>直接 ALTER TABLE</span>
                              </Space>
                              <Space>
                                <input
                                  type="radio"
                                  checked={useOnlineDDL}
                                  onChange={() => setUseOnlineDDL(true)}
                                  disabled={!toolAvailability?.ptoscAvailable}
                                />
                                <span>在线 DDL (无锁)</span>
                                {toolAvailability?.ptoscAvailable ? (
                                  <Tag color="success">可用</Tag>
                                ) : (
                                  <Tag color="default">需要安装 Percona Toolkit</Tag>
                                )}
                              </Space>
                            </Space>
                          </Card>
                        </Col>
                        <Col span={16}>
                          <Card size="small" title="工具状态">
                            <Space direction="vertical">
                              <Space>
                                <CheckCircleOutlined style={{ color: toolAvailability?.ptoscAvailable ? '#52c41a' : '#d9d9d9' }} />
                                <span>pt-online-schema-change: {toolAvailability?.ptoscAvailable ? '已安装' : '未安装'}</span>
                              </Space>
                              <Space>
                                <CheckCircleOutlined style={{ color: toolAvailability?.ptocsAvailable ? '#52c41a' : '#d9d9d9' }} />
                                <span>pt-table-checksum: {toolAvailability?.ptocsAvailable ? '已安装' : '未安装'}</span>
                              </Space>
                            </Space>
                          </Card>
                        </Col>
                      </Row>

                      {showPTOSCCommand && ptoscCommand && (
                        <Card
                          title="pt-online-schema-change 命令"
                          size="small"
                          style={{ marginBottom: 16 }}
                          extra={
                            <Space>
                              <Button size="small" onClick={() => copySQL(dryRunCommand)}>
                                复制 Dry-Run
                              </Button>
                              <Button size="small" onClick={() => copySQL(ptoscCommand)}>
                                复制执行命令
                              </Button>
                              <Button size="small" onClick={() => setShowPTOSCCommand(false)}>
                                隐藏
                              </Button>
                            </Space>
                          }
                        >
                          <Tabs size="small">
                            <TabPane tab="Dry-Run (预览)" key="dryrun">
                              <div className="code-block">
                                <pre>{dryRunCommand}</pre>
                              </div>
                            </TabPane>
                            <TabPane tab="Execute (执行)" key="execute">
                              <div className="code-block">
                                <pre>{ptoscCommand}</pre>
                              </div>
                            </TabPane>
                          </Tabs>
                        </Card>
                      )}

                      <div className="code-block">
                        <pre>
                          {plan.sqlStatements.map((sql, index) => (
                            <div key={index}>
                              {sql}
                              {index < plan.sqlStatements.length - 1 && '\n\n'}
                            </div>
                          ))}
                        </pre>
                      </div>
                    </Card>
                  ),
                },
                {
                  key: 'partitions',
                  label: '分区详情',
                  children: (
                    <Card>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={6}>
                          <Card size="small" className="stat-card">
                            <Statistic title="分区数量" value={plan.partitions.length} />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small" className="stat-card">
                            <Statistic title="预计时间" value={plan.estimatedTimeSec} suffix="秒" />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small" className="stat-card">
                            <Statistic title="分区方式" value={plan.partitionMethod} />
                          </Card>
                        </Col>
                        <Col span={6}>
                          <Card size="small" className="stat-card">
                            <Statistic title="分区字段" value={plan.partitionColumn} />
                          </Card>
                        </Col>
                      </Row>
                      <Table
                        dataSource={plan.partitions}
                        rowKey="partitionName"
                        pagination={false}
                        columns={[
                          {
                            title: '序号',
                            dataIndex: 'partitionOrdinal',
                            key: 'partitionOrdinal',
                            width: 80,
                          },
                          {
                            title: '分区名',
                            dataIndex: 'partitionName',
                            key: 'partitionName',
                          },
                          {
                            title: '描述',
                            dataIndex: 'partitionDescription',
                            key: 'partitionDescription',
                          },
                          {
                            title: '注释',
                            dataIndex: 'comment',
                            key: 'comment',
                          },
                        ]}
                      />
                    </Card>
                  ),
                },
              ]}
            />
          )}
        </Spin>
      )}

      {tableInfo?.partitionInfo && (
        <Card title="分区管理" style={{ marginTop: 24 }}>
          <Space style={{ marginBottom: 16 }}>
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                setOperationType('ADD')
                setShowOperationModal(true)
              }}
            >
              添加分区
            </Button>
            <Button
              icon={<MinusOutlined />}
              onClick={() => {
                setOperationType('DROP')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length === 0}
              danger
            >
              删除分区
            </Button>
            <Button
              icon={<SwapOutlined />}
              onClick={() => {
                setOperationType('MERGE')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length < 2}
            >
              合并分区
            </Button>
            <Button
              icon={<ScissorOutlined />}
              onClick={() => {
                setOperationType('SPLIT')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length !== 1}
            >
              拆分分区
            </Button>
            <Button
              onClick={() => {
                setOperationType('TRUNCATE')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length === 0}
              danger
            >
              清空分区
            </Button>
            <Button
              onClick={() => {
                setOperationType('OPTIMIZE')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length === 0}
            >
              优化分区
            </Button>
            <Button
              onClick={() => {
                setOperationType('REBUILD')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length === 0}
            >
              重建分区
            </Button>
            <Button
              onClick={() => {
                setOperationType('CHECK')
                setShowOperationModal(true)
              }}
              disabled={selectedPartitions.length === 0}
            >
              检查分区
            </Button>
          </Space>

          <Alert
            type="info"
            message={`分区方式: ${tableInfo.partitionInfo.partitionMethod}`}
            description={`分区表达式: ${tableInfo.partitionInfo.partitionExpr}`}
            style={{ marginBottom: 16 }}
          />

          <Table
            dataSource={tableInfo.partitionInfo.partitions}
            columns={allPartitionColumns}
            rowKey="partitionName"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      <Modal
        title={`${operationType} 分区`}
        open={showOperationModal}
        onOk={handleOperation}
        onCancel={() => setShowOperationModal(false)}
        okText="确认执行"
        cancelText="取消"
      >
        {(operationType === 'ADD' || operationType === 'MERGE' || operationType === 'SPLIT') && (
          <Form layout="vertical">
            <Form.Item label="新分区名" required>
              <Input
                value={newPartitionName}
                onChange={(e) => setNewPartitionName(e.target.value)}
                placeholder="例如: p2024_01"
              />
            </Form.Item>
            <Form.Item label="分区描述" required>
              <Input
                value={newPartitionDescription}
                onChange={(e) => setNewPartitionDescription(e.target.value)}
                placeholder="例如: TO_DAYS('2024-02-01')"
              />
            </Form.Item>
          </Form>
        )}
        {operationType === 'DROP' && (
          <Alert
            type="warning"
            message="确认删除"
            description={`将删除分区: ${selectedPartitions.join(', ')}，数据也会被删除！`}
          />
        )}
        {operationType === 'TRUNCATE' && (
          <Alert
            type="warning"
            message="确认清空"
            description={`将清空分区: ${selectedPartitions.join(', ')} 中的所有数据！`}
          />
        )}
      </Modal>
    </div>
  )
}

export default RecommendationPage
