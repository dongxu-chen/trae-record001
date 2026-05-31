import { useEffect, useState } from 'react'
import { Card, Table, Select, Spin, Tag } from 'antd'
import { getTopPaths, type PathStat } from '../services/api'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const { Option } = Select

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const PathStats = () => {
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('total_size')
  const [paths, setPaths] = useState<PathStat[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getTopPaths(sortBy, 20)
      setPaths(data || [])
    } catch (error) {
      console.error('Failed to load path stats:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [sortBy])

  const columns = [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      ellipsis: true,
      width: 250,
      render: (text: string) => <code style={{ background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>{text}</code>,
    },
    {
      title: '节点数',
      dataIndex: 'node_count',
      key: 'node_count',
      sorter: (a: PathStat, b: PathStat) => a.node_count - b.node_count,
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '总数据量',
      dataIndex: 'total_data_size',
      key: 'total_data_size',
      sorter: (a: PathStat, b: PathStat) => a.total_data_size - b.total_data_size,
      render: (size: number) => formatBytes(size),
    },
    {
      title: '平均数据量',
      dataIndex: 'avg_data_size',
      key: 'avg_data_size',
      sorter: (a: PathStat, b: PathStat) => a.avg_data_size - b.avg_data_size,
      render: (size: number) => formatBytes(size),
    },
    {
      title: '最大深度',
      dataIndex: 'max_depth',
      key: 'max_depth',
      sorter: (a: PathStat, b: PathStat) => a.max_depth - b.max_depth,
    },
    {
      title: '临时节点数',
      dataIndex: 'ephemeral_count',
      key: 'ephemeral_count',
      sorter: (a: PathStat, b: PathStat) => a.ephemeral_count - b.ephemeral_count,
      render: (count: number) => count > 0 ? <Tag color="orange">{count}</Tag> : '-',
    },
  ]

  const chartData = paths.slice(0, 10).map(p => ({
    path: p.path.length > 20 ? p.path.substring(0, 20) + '...' : p.path,
    node_count: p.node_count,
    total_size: p.total_data_size,
  }))

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>路径统计</h2>

      <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
        <span>排序方式：</span>
        <Select value={sortBy} onChange={setSortBy} style={{ width: 150 }}>
          <Option value="total_size">按数据量</Option>
          <Option value="node_count">按节点数</Option>
          <Option value="max_depth">按深度</Option>
        </Select>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="path" type="category" width={150} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey={sortBy === 'total_size' ? 'total_size' : 'node_count'} fill="#1890ff" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="路径详情">
        <Table
          columns={columns}
          dataSource={paths}
          rowKey="path"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  )
}

export default PathStats
