import { useState, useEffect, useMemo } from 'react'
import { Card, Tabs, List, Tag, Typography, Space, Tooltip, Progress, Spin, Empty, Button, Select, Statistic, Row, Col, Alert } from 'antd'
import { StarOutlined, ThunderboltOutlined, GatewayOutlined, BarChartOutlined, ReloadOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'

const { Text, Title } = Typography
const { Option } = Select

const NODE_TYPE_CONFIG = {
  influence: {
    label: '影响力节点',
    icon: <StarOutlined />,
    color: '#faad14',
    description: '基于 PageRank 算法，衡量节点在网络中的整体影响力',
    dataKey: 'influence_nodes',
  },
  bridge: {
    label: '桥接节点',
    icon: <GatewayOutlined />,
    color: '#52c41a',
    description: '基于介数中心性，衡量节点作为网络桥梁连接不同社区的能力',
    dataKey: 'bridge_nodes',
  },
  hub: {
    label: '枢纽节点',
    icon: <ThunderboltOutlined />,
    color: '#1890ff',
    description: '基于度数中心性，衡量节点的连接数量和网络核心地位',
    dataKey: 'hub_nodes',
  },
}

const SCORE_METRICS = [
  { key: 'pagerank', label: 'PageRank', color: '#faad14' },
  { key: 'betweenness', label: '介数中心性', color: '#52c41a' },
  { key: 'degree', label: '度数', color: '#1890ff' },
  { key: 'eigenvector', label: '特征向量', color: '#722ed1' },
  { key: 'combined_score', label: '综合评分', color: '#eb2f96' },
]

const KeyNodesPanel = ({ onNodeClick, selectedNodeId }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [keyNodesData, setKeyNodesData] = useState(null)
  const [topN, setTopN] = useState(10)
  const [activeTab, setActiveTab] = useState('influence')

  useEffect(() => {
    loadKeyNodes()
  }, [topN])

  const loadKeyNodes = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await graphApi.getKeyNodes(topN)
      setKeyNodesData(data)
    } catch (err) {
      setError('加载关键节点数据失败')
      console.error('Key nodes error:', err)
    } finally {
      setLoading(false)
    }
  }

  const getRankClass = (rank) => {
    if (rank === 1) return 'top-1'
    if (rank === 2) return 'top-2'
    if (rank === 3) return 'top-3'
    return ''
  }

  const getNodeTypes = (nodeId) => {
    if (!keyNodesData?.data?.node_types) return []
    return Object.entries(keyNodesData.data.node_types)
      .filter(([_, nodeIds]) => nodeIds.includes(nodeId))
      .map(([type]) => type)
  }

  const renderNodeList = (type) => {
    const config = NODE_TYPE_CONFIG[type]
    const nodes = keyNodesData?.data?.[config.dataKey] || []

    if (nodes.length === 0) {
      return <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    }

    const maxScore = Math.max(...nodes.map((n) => n.score))

    return (
      <List
        size="small"
        dataSource={nodes}
        renderItem={(item) => {
          const percentage = maxScore > 0 ? (item.score / maxScore) * 100 : 0
          const isSelected = selectedNodeId === item.node_id
          const nodeTypes = getNodeTypes(item.node_id)

          return (
            <List.Item
              style={{
                padding: '10px 12px',
                borderBottom: '1px solid #f0f0f0',
                background: isSelected ? '#e6f7ff' : 'transparent',
                cursor: 'pointer',
                transition: 'background 0.2s',
              }}
              onClick={() => onNodeClick?.(item.node_id)}
              className={isSelected ? 'node-item-selected' : ''}
            >
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Space>
                    <span className={`influence-rank ${getRankClass(item.rank)}`}>
                      {item.rank}
                    </span>
                    <div>
                      <Space direction="vertical" size={0}>
                        <Text strong>节点 {item.node_id}</Text>
                        <Space size="small" wrap>
                          {nodeTypes.map((t) => (
                            <Tag
                              key={t}
                              color={NODE_TYPE_CONFIG[t].color}
                              style={{ fontSize: 10, padding: '0 4px', margin: 0 }}
                            >
                              {NODE_TYPE_CONFIG[t].label}
                            </Tag>
                          ))}
                        </Space>
                      </Space>
                    </div>
                  </Space>
                  <Tooltip title={`分数: ${item.score.toFixed(4)}`}>
                    <Text
                      type="primary"
                      style={{ fontFamily: 'monospace', fontWeight: 'bold' }}
                    >
                      {item.score.toFixed(4)}
                    </Text>
                  </Tooltip>
                </Space>
                <Progress
                  percent={percentage}
                  size="small"
                  showInfo={false}
                  style={{ marginTop: 4 }}
                  strokeColor={config.color}
                />
                {item.description && (
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {item.description}
                  </Text>
                )}
              </Space>
            </List.Item>
          )
        }}
      />
    )
  }

  const renderComparisonChart = () => {
    const allKeyNodes = keyNodesData?.data?.all_key_nodes || []

    if (allKeyNodes.length === 0) {
      return <Empty description="暂无对比数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    }

    const topNodes = allKeyNodes.slice(0, 5)
    const maxValues = useMemo(() => {
      const max = {}
      SCORE_METRICS.forEach((metric) => {
        max[metric.key] = Math.max(...allKeyNodes.map((n) => n[metric.key] || 0))
      })
      return max
    }, [allKeyNodes])

    return (
      <div className="score-comparison">
        <Text strong style={{ fontSize: 13, marginBottom: 16, display: 'block' }}>
          <BarChartOutlined style={{ marginRight: 4 }} />
          Top 5 节点多维度评分对比
        </Text>

        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {topNodes.map((node, nodeIndex) => (
            <div
              key={node.node_id}
              className="comparison-node"
              style={{
                padding: '12px',
                background: selectedNodeId === node.node_id ? '#e6f7ff' : '#fafafa',
                borderRadius: 8,
                cursor: 'pointer',
                border: selectedNodeId === node.node_id ? '1px solid #1890ff' : '1px solid #f0f0f0',
              }}
              onClick={() => onNodeClick?.(node.node_id)}
            >
              <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
                <Space>
                  <span className={`influence-rank ${getRankClass(node.rank)}`}>
                    #{node.rank}
                  </span>
                  <Text strong>节点 {node.node_id}</Text>
                  <Tag color="#eb2f96" style={{ margin: 0 }}>
                    综合: {node.combined_score?.toFixed(4)}
                  </Tag>
                </Space>
              </Space>

              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {SCORE_METRICS.map((metric) => {
                  const value = node[metric.key] || 0
                  const maxVal = maxValues[metric.key] || 1
                  const percentage = (value / maxVal) * 100

                  return (
                    <div key={metric.key} className="metric-bar">
                      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 2 }}>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {metric.label}
                        </Text>
                        <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>
                          {metric.key === 'degree' ? value : value.toFixed(4)}
                        </Text>
                      </Space>
                      <div
                        style={{
                          height: 8,
                          background: '#f0f0f0',
                          borderRadius: 4,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: `${percentage}%`,
                            background: metric.color,
                            borderRadius: 4,
                            transition: 'width 0.3s ease',
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </Space>
            </div>
          ))}
        </Space>

        <div className="chart-legend" style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
          <Text type="secondary" style={{ fontSize: 11, marginBottom: 8, display: 'block' }}>
            指标说明:
          </Text>
          <Space wrap size="small">
            {SCORE_METRICS.map((metric) => (
              <Space key={metric.key} size={4}>
                <span
                  style={{
                    display: 'inline-block',
                    width: 8,
                    height: 8,
                    borderRadius: 2,
                    background: metric.color,
                  }}
                />
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {metric.label}
                </Text>
              </Space>
            ))}
          </Space>
        </div>
      </div>
    )
  }

  const renderRadarChart = () => {
    const allKeyNodes = keyNodesData?.data?.all_key_nodes || []

    if (allKeyNodes.length === 0) return null

    const topNode = allKeyNodes[0]
    const metrics = SCORE_METRICS.filter((m) => m.key !== 'combined_score')
    const maxValues = {}
    metrics.forEach((metric) => {
      maxValues[metric.key] = Math.max(...allKeyNodes.map((n) => n[metric.key] || 0))
    })

    const centerX = 120
    const centerY = 120
    const radius = 80
    const angleStep = (2 * Math.PI) / metrics.length

    const getPoint = (index, value, maxVal) => {
      const normalizedValue = maxVal > 0 ? value / maxVal : 0
      const r = radius * normalizedValue
      const angle = index * angleStep - Math.PI / 2
      return {
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
      }
    }

    const polygonPoints = metrics
      .map((metric, i) => {
        const point = getPoint(i, topNode[metric.key] || 0, maxValues[metric.key])
        return `${point.x},${point.y}`
      })
      .join(' ')

    const gridLevels = [0.25, 0.5, 0.75, 1]

    return (
      <div className="radar-chart" style={{ marginTop: 16 }}>
        <Text strong style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
          <BarChartOutlined style={{ marginRight: 4 }} />
          Top 1 节点雷达图
        </Text>
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <svg width={240} height={240}>
            {gridLevels.map((level, i) => (
              <polygon
                key={i}
                points={metrics
                  .map((_, idx) => {
                    const point = getPoint(idx, level, 1)
                    return `${point.x},${point.y}`
                  })
                  .join(' ')}
                fill="none"
                stroke="#e0e0e0"
                strokeWidth="1"
              />
            ))}

            {metrics.map((_, i) => {
              const point = getPoint(i, 1, 1)
              return (
                <line
                  key={i}
                  x1={centerX}
                  y1={centerY}
                  x2={point.x}
                  y2={point.y}
                  stroke="#e0e0e0"
                  strokeWidth="1"
                />
              )
            })}

            <polygon
              points={polygonPoints}
              fill="rgba(24, 144, 255, 0.3)"
              stroke="#1890ff"
              strokeWidth="2"
            />

            {metrics.map((metric, i) => {
              const point = getPoint(i, topNode[metric.key] || 0, maxValues[metric.key])
              return (
                <circle
                  key={i}
                  cx={point.x}
                  cy={point.y}
                  r={4}
                  fill="#1890ff"
                />
              )
            })}

            {metrics.map((metric, i) => {
              const labelPoint = getPoint(i, 1.15, 1)
              return (
                <text
                  key={i}
                  x={labelPoint.x}
                  y={labelPoint.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="10"
                  fill="#666"
                >
                  {metric.label}
                </text>
              )
            })}
          </svg>
        </div>
      </div>
    )
  }

  const tabItems = useMemo(() => {
    return Object.entries(NODE_TYPE_CONFIG).map(([key, config]) => ({
      key,
      label: (
        <Space>
          <span style={{ color: config.color }}>{config.icon}</span>
          {config.label}
          <Tag color={config.color} style={{ marginLeft: 4 }}>
            {keyNodesData?.data?.[config.dataKey]?.length || 0}
          </Tag>
        </Space>
      ),
      children: (
        <div>
          <Alert
            type="info"
            showIcon
            message={config.description}
            style={{ marginBottom: 12, padding: '8px 12px' }}
          />
          {renderNodeList(key)}
        </div>
      ),
    }))
  }, [keyNodesData, selectedNodeId])

  if (loading) {
    return (
      <div className="loading-container" style={{ padding: '40px 0', textAlign: 'center' }}>
        <Spin size="small" tip="加载关键节点数据中..." />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: '20px' }}>
        <Alert
          type="error"
          message={error}
          showIcon
          action={
            <Button size="small" type="primary" onClick={loadKeyNodes}>
              重试
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="key-nodes-panel">
      <Card
        title={
          <Space>
            <StarOutlined style={{ color: '#faad14' }} />
            <Text strong>关键节点识别</Text>
            {keyNodesData?.from_cache && (
              <Tag color="default" style={{ fontSize: 10 }}>
                缓存
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Space size="small">
              <Text type="secondary" style={{ fontSize: 12 }}>
                Top N:
              </Text>
              <Select
                value={topN}
                onChange={setTopN}
                size="small"
                style={{ width: 80 }}
              >
                <Option value={5}>5</Option>
                <Option value={10}>10</Option>
                <Option value={20}>20</Option>
                <Option value={50}>50</Option>
              </Select>
            </Space>
            <Tooltip title="刷新数据">
              <Button
                type="text"
                icon={<ReloadOutlined />}
                size="small"
                onClick={loadKeyNodes}
              />
            </Tooltip>
          </Space>
        }
        size="small"
      >
        {keyNodesData?.compute_time_ms !== undefined && (
          <div
            style={{
              marginBottom: 12,
              padding: '8px 12px',
              background: '#f6ffed',
              borderRadius: 4,
              fontSize: 11,
            }}
          >
            <Space size="large">
              <Text type="secondary">
                计算耗时: <Text strong>{keyNodesData.compute_time_ms}ms</Text>
              </Text>
              <Text type="secondary">
                关键节点总数:{' '}
                <Text strong>{keyNodesData.data?.all_key_nodes?.length || 0}</Text>
              </Text>
            </Space>
          </div>
        )}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card
              size="small"
              title={
                <Text strong style={{ fontSize: 13 }}>
                  节点分类
                </Text>
              }
              style={{ height: '100%' }}
            >
              <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                items={tabItems}
                size="small"
              />
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Card size="small" title={<Text strong style={{ fontSize: 13 }}>综合评分对比</Text>}>
                {renderComparisonChart()}
              </Card>

              <Card size="small" title={<Text strong style={{ fontSize: 13 }}>多维分析</Text>}>
                {renderRadarChart()}
              </Card>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default KeyNodesPanel
