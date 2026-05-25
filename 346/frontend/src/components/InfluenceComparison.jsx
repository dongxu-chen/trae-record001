import { useState, useEffect, useMemo } from 'react'
import { Spin, Empty, Typography, Space, Row, Col, Tag, Alert, Table, Tooltip } from 'antd'
import { BarChartOutlined, ThunderboltOutlined, TeamOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'
import { getInfluenceMethodLabel, getNodeLabel } from '../utils/graphUtils'

const { Text } = Typography

const METHOD_COLORS = {
  degree: '#1890ff',
  betweenness: '#52c41a',
  closeness: '#faad14',
  eigenvector: '#722ed1',
  pagerank: '#eb2f96',
}

const InfluenceComparison = ({ nodes = [] }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [comparisonData, setComparisonData] = useState(null)

  const nodeMap = useMemo(() => {
    const map = {}
    nodes.forEach((node) => {
      map[node.id] = node
    })
    return map
  }, [nodes])

  useEffect(() => {
    loadComparisonData()
  }, [])

  const loadComparisonData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await graphApi.getInfluenceComparison()
      setComparisonData(data)
    } catch (err) {
      setError('加载影响力对比数据失败')
      console.error('Influence comparison error:', err)
    } finally {
      setLoading(false)
    }
  }

  const methods = useMemo(() => {
    if (!comparisonData?.top_nodes) return []
    return Object.keys(comparisonData.top_nodes)
  }, [comparisonData])

  const renderTop5Comparison = () => {
    if (!comparisonData?.top_nodes) return null

    const top5Data = []
    for (let rank = 0; rank < 5; rank++) {
      const row = { rank: rank + 1 }
      methods.forEach((method) => {
        const node = comparisonData.top_nodes[method]?.[rank]
        row[method] = node || null
      })
      top5Data.push(row)
    }

    const columns = [
      {
        title: '排名',
        dataIndex: 'rank',
        key: 'rank',
        width: 60,
        render: (rank) => (
          <span className={`influence-rank ${rank <= 3 ? `top-${rank}` : ''}`}>
            {rank}
          </span>
        ),
      },
      ...methods.map((method) => ({
        title: (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <span
              style={{
                display: 'inline-block',
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: METHOD_COLORS[method],
              }}
            />
            <Text strong style={{ fontSize: 12 }}>
              {getInfluenceMethodLabel(method)}
            </Text>
          </Space>
        ),
        dataIndex: method,
        key: method,
        render: (nodeData) => {
          if (!nodeData) return <Text type="secondary">-</Text>
          const node = nodeMap[nodeData.node_id]
          return (
            <Tooltip title={`ID: ${nodeData.node_id}, 分数: ${nodeData.score?.toFixed(4)}`}>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Text strong style={{ fontSize: 12 }}>
                  {node ? getNodeLabel(node) : nodeData.node_id}
                </Text>
                <Text type="secondary" style={{ fontSize: 10 }}>
                  {nodeData.score?.toFixed(4)}
                </Text>
              </Space>
            </Tooltip>
          )
        },
      })),
    ]

    return (
      <div className="top5-comparison">
        <Text strong style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
          <BarChartOutlined style={{ marginRight: 4 }} />
          Top 5 节点对比
        </Text>
        <Table
          size="small"
          dataSource={top5Data}
          columns={columns}
          pagination={false}
          bordered
          rowKey="rank"
        />
      </div>
    )
  }

  const renderCorrelationMatrix = () => {
    if (!comparisonData?.correlation_matrix) return null

    const matrix = comparisonData.correlation_matrix
    const methodList = Object.keys(matrix)

    if (methodList.length < 2) return null

    const cellSize = 50
    const padding = 60

    const getCorrelationColor = (value) => {
      const absValue = Math.abs(value)
      if (absValue >= 0.8) return value > 0 ? '#1890ff' : '#ff4d4f'
      if (absValue >= 0.5) return value > 0 ? '#91d5ff' : '#ffa39e'
      if (absValue >= 0.3) return value > 0 ? '#d6e4ff' : '#ffccc7'
      return '#f0f0f0'
    }

    return (
      <div className="correlation-matrix">
        <Text strong style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
          <ThunderboltOutlined style={{ marginRight: 4 }} />
          算法相关性矩阵
        </Text>
        <div className="matrix-container">
          <svg
            width={padding + methodList.length * cellSize}
            height={padding + methodList.length * cellSize}
            className="matrix-svg"
          >
            {methodList.map((method, i) => (
              <g key={`x-label-${i}`}>
                <text
                  x={padding + i * cellSize + cellSize / 2}
                  y={padding - 10}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#666"
                >
                  {getInfluenceMethodLabel(method).slice(0, 4)}
                </text>
              </g>
            ))}

            {methodList.map((method, i) => (
              <g key={`y-label-${i}`}>
                <text
                  x={padding - 10}
                  y={padding + i * cellSize + cellSize / 2 + 4}
                  textAnchor="end"
                  fontSize="10"
                  fill="#666"
                >
                  {getInfluenceMethodLabel(method).slice(0, 4)}
                </text>
              </g>
            ))}

            {methodList.map((method1, i) =>
              methodList.map((method2, j) => {
                const value = matrix[method1]?.[method2] ?? 0
                const color = getCorrelationColor(value)

                return (
                  <g key={`cell-${i}-${j}`}>
                    <rect
                      x={padding + j * cellSize}
                      y={padding + i * cellSize}
                      width={cellSize - 2}
                      height={cellSize - 2}
                      fill={color}
                      stroke="#fff"
                      strokeWidth="1"
                      className="matrix-cell"
                    />
                    <text
                      x={padding + j * cellSize + cellSize / 2}
                      y={padding + i * cellSize + cellSize / 2 + 4}
                      textAnchor="middle"
                      fontSize="11"
                      fill={Math.abs(value) >= 0.5 ? '#fff' : '#333'}
                      fontWeight="bold"
                    >
                      {value.toFixed(2)}
                    </text>
                  </g>
                )
              })
            )}
          </svg>
        </div>
        <div className="matrix-legend">
          <Space size="middle">
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, background: '#1890ff' }} />
            <Text type="secondary" style={{ fontSize: 11 }}>强正相关</Text>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, background: '#f0f0f0' }} />
            <Text type="secondary" style={{ fontSize: 11 }}>无相关</Text>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, background: '#ff4d4f' }} />
            <Text type="secondary" style={{ fontSize: 11 }}>强负相关</Text>
          </Space>
          </Space>
        </div>
      </div>
    )
  }

  const renderOverlapAnalysis = () => {
    if (!comparisonData?.overlap_analysis) return null

    const overlap = comparisonData.overlap_analysis

    return (
      <div className="overlap-analysis">
        <Text strong style={{ fontSize: 13, marginBottom: 12, display: 'block' }}>
          <TeamOutlined style={{ marginRight: 4 }} />
          Top 10 节点重叠分析
        </Text>

        <Row gutter={[8, 8]}>
          <Col span={12}>
            <div className="overlap-stat">
              <Text type="secondary" style={{ fontSize: 12 }}>平均重叠数</Text>
              <Text strong style={{ fontSize: 20, color: '#1890ff' }}>
                {overlap.average_overlap?.toFixed(1) || 0}
              </Text>
            </div>
          </Col>
          <Col span={12}>
            <div className="overlap-stat">
              <Text type="secondary" style={{ fontSize: 12 }}>共同节点数</Text>
              <Text strong style={{ fontSize: 20, color: '#52c41a' }}>
                {overlap.common_nodes?.length || 0}
              </Text>
            </div>
          </Col>
        </Row>

        {overlap.pairwise_overlaps && (
          <div className="pairwise-overlaps" style={{ marginTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              算法间重叠数:
            </Text>
            <Space wrap size="small">
              {Object.entries(overlap.pairwise_overlaps).map(([key, value]) => {
                const [m1, m2] = key.split('_')
                const percentage = (value / 10) * 100
                return (
                  <Tooltip key={key} title={`${getInfluenceMethodLabel(m1)} vs ${getInfluenceMethodLabel(m2)}`}>
                    <Tag
                      color={percentage >= 70 ? 'green' : percentage >= 40 ? 'blue' : 'default'}
                      style={{ margin: 2 }}
                    >
                      {getInfluenceMethodLabel(m1).slice(0, 2)}-{getInfluenceMethodLabel(m2).slice(0, 2)}:
                      <Text strong style={{ marginLeft: 4 }}>{value}/10</Text>
                    </Tag>
                  </Tooltip>
                )
              })}
            </Space>
          </div>
        )}

        {overlap.common_nodes && overlap.common_nodes.length > 0 && (
          <div className="common-nodes" style={{ marginTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 12, marginBottom: 8, display: 'block' }}>
              所有算法共同的 Top 10 节点:
            </Text>
            <Space wrap size="small">
              {overlap.common_nodes.slice(0, 10).map((nodeId) => {
                const node = nodeMap[nodeId]
                return (
                  <Tag key={nodeId} color="blue">
                    {node ? getNodeLabel(node) : nodeId}
                  </Tag>
                )
              })}
            </Space>
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="loading-container">
      <Spin size="small" tip="加载中..." />
      </div>
    )
  }

  if (error) {
    return <Alert type="error" message={error} showIcon />
  }

  if (!comparisonData) {
    return <Empty description="暂无对比数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div className="influence-comparison">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {renderTop5Comparison()}
        {renderCorrelationMatrix()}
        {renderOverlapAnalysis()}
      </Space>
    </div>
  )
}

export default InfluenceComparison
