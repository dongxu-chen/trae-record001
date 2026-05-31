import React, { useState, useEffect } from 'react'
import {
  Table,
  Card,
  Typography,
  Tag,
  Button,
  Space,
  Input,
  Statistic,
  Row,
  Col,
  message,
  Spin,
} from 'antd'
import {
  TableOutlined,
  SearchOutlined,
  EyeOutlined,
  PartitionOutlined,
  RiseOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { tablesApi, partitionApi } from '../services/api'
import type { TableInfo, PartitionRecommendation } from '../types'

const { Title, Paragraph } = Typography

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(2)}K`
  return num.toString()
}

const TablesPage: React.FC = () => {
  const navigate = useNavigate()
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [recommendations, setRecommendations] = useState<Record<string, PartitionRecommendation>>({})

  useEffect(() => {
    loadTables()
  }, [])

  const loadTables = async () => {
    try {
      setLoading(true)
      const response = await tablesApi.getList()
      setTables(response.data || [])
    } catch (error) {
      message.error('加载表列表失败')
      console.error('Load tables error:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadRecommendations = async () => {
    try {
      setLoading(true)
      const response = await partitionApi.getAllRecommendations()
      const recMap: Record<string, PartitionRecommendation> = {}
      ;(response.data || []).forEach((item: any) => {
        recMap[item.tableName] = item.recommendation
      })
      setRecommendations(recMap)
    } catch (error) {
      message.error('加载推荐失败')
    } finally {
      setLoading(false)
    }
  }

  const filteredTables = tables.filter((table) =>
    table.tableName.toLowerCase().includes(searchText.toLowerCase())
  )

  const totalRows = tables.reduce((sum, t) => sum + t.tableRows, 0)
  const totalSize = tables.reduce((sum, t) => sum + t.totalSize, 0)
  const partitionedTables = tables.filter(
    (t) => t.partitionInfo && t.partitionInfo.partitions.length > 0
  ).length

  const columns = [
    {
      title: '表名',
      dataIndex: 'tableName',
      key: 'tableName',
      render: (text: string, record: TableInfo) => (
        <Space>
          <TableOutlined />
          <span style={{ fontWeight: 500 }}>{text}</span>
          {record.partitionInfo && (
            <Tag color="blue" icon={<PartitionOutlined />}>
              {record.partitionInfo.partitionMethod}
            </Tag>
          )}
          {recommendations[text]?.confidence && recommendations[text].confidence > 70 && !record.partitionInfo && (
            <Tag color="orange" icon={<RiseOutlined />}>
              建议分区
            </Tag>
          )}
        </Space>
      ),
      sorter: (a: TableInfo, b: TableInfo) => a.tableName.localeCompare(b.tableName),
    },
    {
      title: '行数',
      dataIndex: 'tableRows',
      key: 'tableRows',
      render: (text: number) => formatNumber(text),
      sorter: (a: TableInfo, b: TableInfo) => a.tableRows - b.tableRows,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '数据大小',
      dataIndex: 'dataSize',
      key: 'dataSize',
      render: (text: number) => formatSize(text),
      sorter: (a: TableInfo, b: TableInfo) => a.dataSize - b.dataSize,
    },
    {
      title: '索引大小',
      dataIndex: 'indexSize',
      key: 'indexSize',
      render: (text: number) => formatSize(text),
      sorter: (a: TableInfo, b: TableInfo) => a.indexSize - b.indexSize,
    },
    {
      title: '总大小',
      dataIndex: 'totalSize',
      key: 'totalSize',
      render: (text: number) => formatSize(text),
      sorter: (a: TableInfo, b: TableInfo) => a.totalSize - b.totalSize,
    },
    {
      title: '引擎',
      dataIndex: 'engine',
      key: 'engine',
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: '更新时间',
      dataIndex: 'updateTime',
      key: 'updateTime',
      render: (text: string) =>
        text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: TableInfo) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tables/${record.tableName}`)}
          >
            详情
          </Button>
          <Button
            type="link"
            icon={<ArrowRightOutlined />}
            onClick={() => navigate(`/recommendations?table=${record.tableName}`)}
          >
            分区推荐
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={1} style={{ margin: 0 }}>
          <TableOutlined style={{ marginRight: 12 }} />
          数据表列表
        </Title>
        <Paragraph className="description">
          查看数据库中的所有表，分析数据量和增长趋势
        </Paragraph>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据表总数"
              value={tables.length}
              prefix={<TableOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总记录数"
              value={totalRows}
              formatter={(value) => formatNumber(value as number)}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总数据大小"
              value={totalSize}
              formatter={(value) => formatSize(value as number)}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已分区表"
              value={partitionedTables}
              suffix={`/ ${tables.length}`}
              prefix={<PartitionOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Input
            placeholder="搜索表名..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 300 }}
            allowClear
          />
          <Space>
            <Button onClick={loadTables}>刷新</Button>
            <Button type="primary" onClick={loadRecommendations}>
              <PartitionOutlined />
              加载分区建议
            </Button>
          </Space>
        </Space>

        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={filteredTables}
            rowKey="tableName"
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 张表`,
            }}
          />
        </Spin>
      </Card>
    </div>
  )
}

export default TablesPage
