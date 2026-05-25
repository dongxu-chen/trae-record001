import { useMemo, useState } from 'react'
import { List, Select, Empty, Tag, Space, Typography, Progress, Radio } from 'antd'
import {
  getInfluenceMethodLabel,
  formatInfluenceScore,
  getNodeLabel,
} from '../utils/graphUtils'

const { Text } = Typography
const { Option } = Select

const InfluencePanel = ({ influences = [], nodes = [], onMethodChange }) => {
  const [method, setMethod] = useState('degree')
  const [sortOrder, setSortOrder] = useState('desc')

  const nodeMap = useMemo(() => {
    const map = {}
    nodes.forEach((node) => {
      map[node.id] = node
    })
    return map
  }, [nodes])

  const topInfluences = useMemo(() => {
    let sorted = [...influences]
    if (sortOrder === 'asc') {
      sorted.reverse()
    }
    return sorted.slice(0, 20)
  }, [influences, sortOrder])

  const maxScore = useMemo(() => {
    if (influences.length === 0) return 1
    return Math.max(...influences.map((i) => i.score))
  }, [influences])

  const handleMethodChange = (newMethod) => {
    setMethod(newMethod)
    onMethodChange?.(newMethod)
  }

  const getRankClass = (rank) => {
    if (rank === 1) return 'top-1'
    if (rank === 2) return 'top-2'
    if (rank === 3) return 'top-3'
    return ''
  }

  const methodOptions = [
    { value: 'degree', label: '度数中心性' },
    { value: 'betweenness', label: '介数中心性' },
    { value: 'closeness', label: '接近中心性' },
    { value: 'eigenvector', label: '特征向量中心性' },
    { value: 'pagerank', label: 'PageRank' },
  ]

  if (influences.length === 0) {
    return <Empty description="暂无影响力数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div className="influence-list">
      <Space direction="vertical" size="small" style={{ width: '100%', marginBottom: 12 }}>
        <div>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
            分析方法
          </Text>
          <Select
            value={method}
            onChange={handleMethodChange}
            style={{ width: '100%' }}
            size="small"
          >
            {methodOptions.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
        </div>

        <div>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
            排序方式
          </Text>
          <Radio.Group
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            size="small"
            style={{ width: '100%' }}
          >
            <Radio.Button value="desc" style={{ width: '50%', textAlign: 'center' }}>
              降序
            </Radio.Button>
            <Radio.Button value="asc" style={{ width: '50%', textAlign: 'center' }}>
              升序
            </Radio.Button>
          </Radio.Group>
        </div>
      </Space>

      <div style={{ marginBottom: 12, fontSize: 12, color: '#666' }}>
        当前方法: <Tag color="blue">{getInfluenceMethodLabel(method)}</Tag>
        显示前 {Math.min(20, influences.length)} 个节点
      </div>

      <List
        size="small"
        dataSource={topInfluences}
        renderItem={(item, index) => {
          const node = nodeMap[item.node_id]
          const displayRank = sortOrder === 'desc' ? item.rank : influences.length - item.rank + 1
          const percentage = maxScore > 0 ? (item.score / maxScore) * 100 : 0

          return (
            <List.Item style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Space>
                  <span className={`influence-rank ${getRankClass(displayRank)}`}>
                    {displayRank}
                  </span>
                  <div>
                    <Text strong>{node ? getNodeLabel(node) : item.node_id}</Text>
                    <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                      ID: {item.node_id}
                    </Text>
                  </div>
                </Space>
                <Text type="primary" style={{ fontFamily: 'monospace' }}>
                  {formatInfluenceScore(item.score, method)}
                </Text>
              </Space>
              <Progress
                percent={percentage}
                size="small"
                showInfo={false}
                style={{ marginTop: 4 }}
                strokeColor={
                  displayRank === 1
                    ? '#faad14'
                    : displayRank === 2
                    ? '#8c8c8c'
                    : displayRank === 3
                    ? '#d48806'
                    : '#1890ff'
                }
              />
            </List.Item>
          )
        }}
      />
    </div>
  )
}

export default InfluencePanel
