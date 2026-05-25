import { useState, useEffect, useMemo } from 'react'
import { Spin, Empty, Select, Typography, Space, Row, Col, Statistic, Tag, Alert, List } from 'antd'
import { ClockCircleOutlined, TeamOutlined, LinkOutlined, ThunderboltOutlined, ClusterOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'
import { getNodeLabel } from '../utils/graphUtils'

const { Text } = Typography
const { Option } = Select

const TemporalAnalysis = ({ nodes = [] }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [windowCount, setWindowCount] = useState(6)
  const [temporalData, setTemporalData] = useState(null)

  const nodeMap = useMemo(() => {
    const map = {}
    nodes.forEach((node) => {
      map[node.id] = node
    })
    return map
  }, [nodes])

  useEffect(() => {
    loadTemporalData()
  }, [windowCount])

  const loadTemporalData = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await graphApi.getTemporalAnalysis({ windows: windowCount })
      setTemporalData(data)
    } catch (err) {
      setError('加载时间演化数据失败')
      console.error('Temporal analysis error:', err)
    } finally {
      setLoading(false)
    }
  }

  const chartData = useMemo(() => {
    if (!temporalData?.time_windows) return []
    return temporalData.time_windows.map((window, index) => ({
      index,
      label: window.label || `T${index + 1}`,
      nodeCount: window.metrics?.node_count || 0,
      edgeCount: window.metrics?.edge_count || 0,
      density: window.metrics?.density || 0,
      communityCount: window.metrics?.community_count || 0,
    }))
  }, [temporalData])

  const maxValues = useMemo(() => {
    if (chartData.length === 0) return { nodeCount: 1, edgeCount: 1, density: 1, communityCount: 1 }
    return {
      nodeCount: Math.max(...chartData.map((d) => d.nodeCount), 1),
      edgeCount: Math.max(...chartData.map((d) => d.edgeCount), 1),
      density: Math.max(...chartData.map((d) => d.density), 0.0001),
      communityCount: Math.max(...chartData.map((d) => d.communityCount), 1),
    }
  }, [chartData])

  const generateLinePath = (data, key, maxValue, width, height, padding) => {
    if (data.length < 2) return ''
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2
    const xStep = data.length > 1 ? chartWidth / (data.length - 1) : 0

    const points = data.map((d, i) => {
      const x = padding + i * xStep
      const value = d[key]
      const normalizedValue = Math.min(value / maxValue, 1)
      const y = padding + chartHeight - normalizedValue * chartHeight
      return `${x},${y}`
    })

    return `M ${points.join(' L ')}`
  }

  const generateAreaPath = (data, key, maxValue, width, height, padding) => {
    if (data.length < 2) return ''
    const chartWidth = width - padding * 2
    const chartHeight = height - padding * 2
    const xStep = data.length > 1 ? chartWidth / (data.length - 1) : 0
    const bottomY = padding + chartHeight

    const points = data.map((d, i) => {
      const x = padding + i * xStep
      const value = d[key]
      const normalizedValue = Math.min(value / maxValue, 1)
      const y = padding + chartHeight - normalizedValue * chartHeight
      return `${x},${y}`
    })

    const firstX = padding
    const lastX = padding + (data.length - 1) * xStep

    return `M ${firstX},${bottomY} L ${points.join(' L ')} L ${lastX},${bottomY} Z`
  }

  const renderLineChart = (data, key, color, title, maxValue) => {
    const width = 300
    const height = 120
    const padding = 20

    if (data.length === 0) return null

    return (
      <div className="line-chart-container">
        <div className="line-chart-title">
          <Text strong>{title}</Text>
        </div>
        <svg width={width} height={height} className="line-chart-svg">
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
            <line
              key={i}
              x1={padding}
              y1={padding + (height - padding * 2) * (1 - ratio)}
              x2={width - padding}
              y2={padding + (height - padding * 2) * (1 - ratio)}
              stroke="#f0f0f0"
              strokeWidth="1"
            />
          ))}

          <path
            d={generateAreaPath(data, key, maxValue, width, height, padding)}
            fill={color}
            fillOpacity="0.15"
          />

          <path
            d={generateLinePath(data, key, maxValue, width, height, padding)}
            fill="none"
            stroke={color}
            strokeWidth="2"
            className="line-chart-path"
          />

          {data.map((d, i) => {
            const chartWidth = width - padding * 2
            const chartHeight = height - padding * 2
            const xStep = data.length > 1 ? chartWidth / (data.length - 1) : 0
            const x = padding + i * xStep
            const normalizedValue = Math.min(d[key] / maxValue, 1)
            const y = padding + chartHeight - normalizedValue * chartHeight

            return (
              <g key={i}>
                <circle cx={x} cy={y} r="4" fill={color} className="line-chart-point" />
                <text x={x} y={height - 5} textAnchor="middle" fontSize="10" fill="#999">
                  {d.label}
                </text>
                <text x={padding - 5} y={y + 3} textAnchor="end" fontSize="9" fill="#999">
                  {typeof d[key] === 'number' && d[key] < 1 ? d[key].toFixed(3) : d[key]}
                </text>
              </g>
            )
          })}
        </svg>
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

  if (!temporalData || chartData.length === 0) {
    return <Empty description="暂无时间演化数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div className="temporal-analysis">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            时间窗口数量
          </Text>
          <Select
            value={windowCount}
            onChange={setWindowCount}
            size="small"
            style={{ width: 100 }}
          >
            {[3, 4, 5, 6, 8, 10, 12].map((n) => (
              <Option key={n} value={n}>
                {n} 个窗口
              </Option>
            ))}
          </Select>
        </div>

        <Row gutter={[8, 8]}>
          <Col span={12}>
            <Statistic
              title="时间跨度"
              value={temporalData.time_span || 'N/A'}
              prefix={<ClockCircleOutlined />}
              className="statistic-card"
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="社区数量变化"
              value={temporalData.community_changes?.count || 0}
              prefix={<ClusterOutlined />}
              className="statistic-card"
            />
          </Col>
        </Row>

        <div className="charts-grid">
          {renderLineChart(chartData, 'nodeCount', '#1890ff', '节点数', maxValues.nodeCount)}
          {renderLineChart(chartData, 'edgeCount', '#52c41a', '边数', maxValues.edgeCount)}
          {renderLineChart(chartData, 'density', '#faad14', '图密度', maxValues.density)}
          {renderLineChart(chartData, 'communityCount', '#722ed1', '社区数', maxValues.communityCount)}
        </div>

        {temporalData.community_changes?.transitions && temporalData.community_changes.transitions.length > 0 && (
          <div className="community-transitions">
            <Text strong style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
              社区变化追踪
            </Text>
            <List
              size="small"
              dataSource={temporalData.community_changes.transitions.slice(0, 5)}
              renderItem={(transition, idx) => (
                <List.Item style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Space>
                        <Tag color="blue">{transition.from_window}</Tag>
                        <span>→</span>
                        <Tag color="green">{transition.to_window}</Tag>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {transition.change_type}
                      </Text>
                    </div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      涉及节点: {transition.nodes?.slice(0, 3).map((id) => (
                        <Tag key={id} color="default" style={{ margin: '0 2px' }}>
                          {nodeMap[id] ? getNodeLabel(nodeMap[id]) : id}
                        </Tag>
                      ))}
                      {transition.nodes?.length > 3 && ` 等${transition.nodes.length}个`}
                    </Text>
                  </Space>
                </List.Item>
              )}
            />
          </div>
        )}
      </Space>
    </div>
  )
}

export default TemporalAnalysis
