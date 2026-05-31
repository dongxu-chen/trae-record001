import React, { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Table,
  Statistic,
  Row,
  Col,
  Tag,
  Button,
  Space,
  Tabs,
  List,
  Descriptions,
  message,
  Spin,
  Alert,
  Progress,
} from 'antd'
import {
  ArrowLeftOutlined,
  TableOutlined,
  DatabaseOutlined,
  PartitionOutlined,
  RiseOutlined,
  ThunderboltOutlined,
  KeyOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { tablesApi, partitionApi } from '../services/api'
import type { TableInfo, GrowthPrediction, PartitionDef } from '../types'

const { Title, Paragraph, Text } = Typography

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
  if (confidence >= 70) return 'confidence-high'
  if (confidence >= 40) return 'confidence-medium'
  return 'confidence-low'
}

const TableDetailPage: React.FC = () => {
  const { tableName } = useParams<{ tableName: string }>()
  const navigate = useNavigate()
  const [tableInfo, setTableInfo] = useState<TableInfo | null>(null)
  const [prediction, setPrediction] = useState<GrowthPrediction | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (tableName) {
      loadTableInfo()
      loadPrediction()
    }
  }, [tableName])

  const loadTableInfo = async () => {
    try {
      setLoading(true)
      const response = await tablesApi.getInfo(tableName!)
      setTableInfo(response.data)
    } catch (error) {
      message.error('加载表信息失败')
    } finally {
      setLoading(false)
    }
  }

  const loadPrediction = async () => {
    try {
      const response = await tablesApi.getPrediction(tableName!)
      setPrediction(response.data)
    } catch (error) {
      console.error('Load prediction error:', error)
    }
  }

  if (!tableInfo) {
    return (
      <div className="page-container">
        <Spin spinning={loading} tip="加载中...">
          <div style={{ height: 400 }} />
        </Spin>
      </div>
    )
  }

  const columnColumns = [
    {
      title: '字段名',
      dataIndex: 'columnName',
      key: 'columnName',
      render: (text: string, record: any) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.columnKey === 'PRI' && <Tag color="red" icon={<KeyOutlined />}>PK</Tag>}
          {record.columnKey === 'UNI' && <Tag color="blue">UNIQUE</Tag>}
          {record.columnKey === 'MUL' && <Tag color="green">INDEX</Tag>}
        </Space>
      ),
    },
    {
      title: '数据类型',
      dataIndex: 'columnType',
      key: 'columnType',
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'isNullable',
      key: 'isNullable',
      render: (text: boolean) => (text ? '是' : '否'),
    },
    {
      title: '默认值',
      dataIndex: 'columnDefault',
      key: 'columnDefault',
      render: (text: string) => text || '-',
    },
    {
      title: '额外属性',
      dataIndex: 'extra',
      key: 'extra',
      render: (text: string) => text || '-',
    },
    {
      title: '注释',
      dataIndex: 'comment',
      key: 'comment',
      render: (text: string) => text || '-',
    },
  ]

  const indexColumns = [
    {
      title: '索引名',
      dataIndex: 'indexName',
      key: 'indexName',
      render: (text: string, record: any) => (
        <Space>
          <span style={{ fontWeight: 500 }}>{text}</span>
          {!record.nonUnique && <Tag color="blue">UNIQUE</Tag>}
        </Space>
      ),
    },
    {
      title: '字段',
      dataIndex: 'columnName',
      key: 'columnName',
    },
    {
      title: '顺序',
      dataIndex: 'seqInIndex',
      key: 'seqInIndex',
    },
    {
      title: '类型',
      dataIndex: 'indexType',
      key: 'indexType',
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: '注释',
      dataIndex: 'comment',
      key: 'comment',
      render: (text: string) => text || '-',
    },
  ]

  const partitionColumns = [
    {
      title: '分区名',
      dataIndex: 'partitionName',
      key: 'partitionName',
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '序号',
      dataIndex: 'partitionOrdinal',
      key: 'partitionOrdinal',
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
      render: (text: number) => formatNumber(text),
      sorter: (a: PartitionDef, b: PartitionDef) => a.tableRows - b.tableRows,
    },
    {
      title: '数据大小',
      dataIndex: 'dataLength',
      key: 'dataLength',
      render: (text: number) => formatSize(text),
      sorter: (a: PartitionDef, b: PartitionDef) => a.dataLength - b.dataLength,
    },
    {
      title: '索引大小',
      dataIndex: 'indexLength',
      key: 'indexLength',
      render: (text: number) => formatSize(text),
    },
    {
      title: '注释',
      dataIndex: 'comment',
      key: 'comment',
      render: (text: string) => text || '-',
    },
  ]

  const growthChartData = tableInfo.stats?.dataPoints?.map((dp) => ({
    date: dayjs(dp.date).format('MM-DD'),
    rows: dp.value,
  })) || []

  const predictionChartData = prediction
    ? [
        { name: '当前', rows: prediction.currentRows },
        { name: '30天', rows: prediction.predicted30Days },
        { name: '90天', rows: prediction.predicted90Days },
        { name: '365天', rows: prediction.predicted365Days },
      ]
    : []

  const partitionDistribution = tableInfo.partitionInfo?.partitions?.map((p) => ({
    name: p.partitionName,
    rows: p.tableRows,
    size: p.dataLength / (1024 * 1024),
  })) || []

  return (
    <div className="page-container">
      <div className="page-header">
        <Space style={{ marginBottom: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tables')}>
            返回列表
          </Button>
        </Space>
        <Title level={1} style={{ margin: 0 }}>
          <TableOutlined style={{ marginRight: 12 }} />
          {tableInfo.tableName}
          {tableInfo.partitionInfo && (
            <Tag color="blue" icon={<PartitionOutlined />} style={{ marginLeft: 12 }}>
              {tableInfo.partitionInfo.partitionMethod} 分区
            </Tag>
          )}
        </Title>
        <Paragraph className="description">
          {tableInfo.comment || '暂无注释'}
        </Paragraph>
      </div>

      {prediction?.shouldPartition && !tableInfo.partitionInfo && (
        <Alert
          type="warning"
          showIcon
          message="建议创建分区"
          description={prediction.recommendedAction}
          style={{ marginBottom: 24 }}
          action={
            <Button type="primary" size="small" onClick={() => navigate(`/recommendations?table=${tableName}`)}>
              查看分区推荐
            </Button>
          }
        />
      )}

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="总行数"
              value={tableInfo.tableRows}
              formatter={(value) => formatNumber(value as number)}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="数据大小"
              value={tableInfo.dataSize}
              formatter={(value) => formatSize(value as number)}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="索引大小"
              value={tableInfo.indexSize}
              formatter={(value) => formatSize(value as number)}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="总大小"
              value={tableInfo.totalSize}
              formatter={(value) => formatSize(value as number)}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="平均行大小"
              value={tableInfo.stats?.avgRowSizeKB || 0}
              suffix="KB"
              precision={2}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card className="stat-card">
            <Statistic
              title="日增长"
              value={tableInfo.stats?.growthPerDay || 0}
              formatter={(value) => `+${formatNumber(value as number)}`}
              className={
                (tableInfo.stats?.growthPerDay || 0) > 1000
                  ? 'growth-high'
                  : (tableInfo.stats?.growthPerDay || 0) > 100
                  ? 'growth-positive'
                  : ''
              }
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'overview',
              label: '概览',
              children: (
                <Spin spinning={loading}>
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Descriptions title="基本信息" bordered column={3}>
                      <Descriptions.Item label="引擎">{tableInfo.engine}</Descriptions.Item>
                      <Descriptions.Item label="字符集">{tableInfo.tableCollation}</Descriptions.Item>
                      <Descriptions.Item label="行数">{formatNumber(tableInfo.tableRows)}</Descriptions.Item>
                      <Descriptions.Item label="数据大小">{formatSize(tableInfo.dataSize)}</Descriptions.Item>
                      <Descriptions.Item label="索引大小">{formatSize(tableInfo.indexSize)}</Descriptions.Item>
                      <Descriptions.Item label="总大小">{formatSize(tableInfo.totalSize)}</Descriptions.Item>
                      <Descriptions.Item label="创建时间">
                        {tableInfo.createTime ? dayjs(tableInfo.createTime).format('YYYY-MM-DD HH:mm:ss') : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="更新时间">
                        {tableInfo.updateTime ? dayjs(tableInfo.updateTime).format('YYYY-MM-DD HH:mm:ss') : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="主键">
                        {tableInfo.primaryKeys.join(', ') || '-'}
                      </Descriptions.Item>
                    </Descriptions>

                    {tableInfo.stats && (
                      <div>
                        <Title level={4}><RiseOutlined /> 数据增长趋势</Title>
                        {growthChartData.length > 0 ? (
                          <div className="chart-container" style={{ height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={growthChartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="rows" stroke="#1890ff" name="行数" />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        ) : (
                          <Alert type="info" message="暂无增长数据" />
                        )}
                      </div>
                    )}

                    {prediction && (
                      <div>
                        <Title level={4}><ThunderboltOutlined /> 增长预测</Title>
                        <Row gutter={16}>
                          <Col span={8}>
                            <Card>
                              <Statistic
                                title="30天后预测"
                                value={prediction.predicted30Days}
                                formatter={(v) => formatNumber(v as number)}
                              />
                              <Progress
                                percent={Math.min(100, (prediction.predicted30Days / 1000000) * 100)}
                                status={prediction.shouldPartition ? 'exception' : 'active'}
                              />
                            </Card>
                          </Col>
                          <Col span={8}>
                            <Card>
                              <Statistic
                                title="90天后预测"
                                value={prediction.predicted90Days}
                                formatter={(v) => formatNumber(v as number)}
                              />
                              <Progress
                                percent={Math.min(100, (prediction.predicted90Days / 1000000) * 100)}
                                status={prediction.shouldPartition ? 'exception' : 'active'}
                              />
                            </Card>
                          </Col>
                          <Col span={8}>
                            <Card>
                              <Statistic
                                title="365天后预测"
                                value={prediction.predicted365Days}
                                formatter={(v) => formatNumber(v as number)}
                              />
                              <Progress
                                percent={Math.min(100, (prediction.predicted365Days / 1000000) * 100)}
                                status={prediction.shouldPartition ? 'exception' : 'active'}
                              />
                            </Card>
                          </Col>
                        </Row>
                        <div className="chart-container" style={{ height: 300, marginTop: 16 }}>
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={predictionChartData}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="name" />
                              <YAxis />
                              <Tooltip />
                              <Legend />
                              <Bar dataKey="rows" fill="#1890ff" name="预测行数" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                        <Alert
                          type={prediction.shouldPartition ? 'warning' : 'info'}
                          message={prediction.shouldPartition ? '建议分区' : '状态正常'}
                          description={prediction.recommendedAction}
                          style={{ marginTop: 16 }}
                        />
                      </div>
                    )}
                  </Space>
                </Spin>
              ),
            },
            {
              key: 'columns',
              label: '字段',
              children: (
                <Table
                  columns={columnColumns}
                  dataSource={tableInfo.columns}
                  rowKey="columnName"
                  pagination={false}
                />
              ),
            },
            {
              key: 'indexes',
              label: '索引',
              children: (
                <Table
                  columns={indexColumns}
                  dataSource={tableInfo.indexes}
                  rowKey={(record) => `${record.indexName}-${record.seqInIndex}`}
                  pagination={false}
                />
              ),
            },
            {
              key: 'partitions',
              label: '分区信息',
              children: tableInfo.partitionInfo ? (
                <Spin spinning={loading}>
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <Alert
                      type="info"
                      message={`分区方式: ${tableInfo.partitionInfo.partitionMethod}`}
                      description={`分区表达式: ${tableInfo.partitionInfo.partitionExpr}`}
                    />
                    {partitionDistribution.length > 0 && (
                      <div className="chart-container" style={{ height: 300 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={partitionDistribution}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis yAxisId="left" />
                            <YAxis yAxisId="right" orientation="right" />
                            <Tooltip />
                            <Legend />
                            <Bar yAxisId="left" dataKey="rows" fill="#1890ff" name="行数" />
                            <Bar yAxisId="right" dataKey="size" fill="#52c41a" name="大小(MB)" />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                    <Table
                      columns={partitionColumns}
                      dataSource={tableInfo.partitionInfo.partitions}
                      rowKey="partitionName"
                      pagination={{ pageSize: 20 }}
                    />
                  </Space>
                </Spin>
              ) : (
                <Alert
                  type="info"
                  message="表未分区"
                  description={
                    <Space>
                      <span>该表尚未创建分区。</span>
                      <Button
                        type="primary"
                        size="small"
                        onClick={() => navigate(`/recommendations?table=${tableName}`)}
                      >
                        生成分区方案
                      </Button>
                    </Space>
                  }
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default TableDetailPage
