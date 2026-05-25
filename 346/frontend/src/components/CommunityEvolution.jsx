import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import {
  Card,
  Button,
  Space,
  Statistic,
  Row,
  Col,
  Slider,
  Select,
  List,
  Tag,
  Typography,
  Timeline,
  Tooltip,
  Spin,
  Empty,
  Progress,
  Divider,
  Switch,
  Badge,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  StepForwardOutlined,
  StepBackwardOutlined,
  TeamOutlined,
  MergeCellsOutlined,
  SplitCellsOutlined,
  PlusCircleOutlined,
  DeleteOutlined,
  ArrowsAltOutlined,
  ShrinkOutlined,
} from '@ant-design/icons'
import { graphApi } from '../services/api'
import * as d3 from 'd3'

const { Text, Title } = Typography
const { Option } = Select

const EVENT_CONFIG = {
  initial: { color: '#1890ff', icon: TeamOutlined, label: '初始' },
  new: { color: '#52c41a', icon: PlusCircleOutlined, label: '新建' },
  merge: { color: '#722ed1', icon: MergeCellsOutlined, label: '合并' },
  split: { color: '#fa8c16', icon: SplitCellsOutlined, label: '分裂' },
  expanded: { color: '#13c2c2', icon: ArrowsAltOutlined, label: '扩张' },
  contracted: { color: '#eb2f96', icon: ShrinkOutlined, label: '收缩' },
  dissolved: { color: '#f5222d', icon: DeleteOutlined, label: '解散' },
}

const COMMUNITY_COLORS = d3.schemeCategory10.concat(
  d3.schemeSet2,
  d3.schemeSet3,
  d3.schemePastel1,
  d3.schemeAccent
)

const lerp = (a, b, t) => a + (b - a) * t

const getCommunityColor = (communityId) => {
  return COMMUNITY_COLORS[communityId % COMMUNITY_COLORS.length]
}

const calculateConvexHull = (points) => {
  if (points.length < 3) return null

  const sorted = [...points].sort((a, b) => a.x - b.x || a.y - b.y)

  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

  const lower = []
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
      lower.pop()
    }
    lower.push(p)
  }

  const upper = []
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i]
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
      upper.pop()
    }
    upper.push(p)
  }

  lower.pop()
  upper.pop()

  return lower.concat(upper)
}

const convexHullToPath = (hull, padding = 30) => {
  if (!hull || hull.length < 3) return ''

  const points = hull.map((p) => `${p.x},${p.y}`)

  const paddedPoints = hull.map((p, i) => {
    const prev = hull[(i - 1 + hull.length) % hull.length]
    const next = hull[(i + 1) % hull.length]

    const dxA = p.x - prev.x
    const dyA = p.y - prev.y
    const lenA = Math.sqrt(dxA * dxA + dyA * dyA) || 1
    const nxA = -dyA / lenA
    const nyA = dxA / lenA

    const dxB = next.x - p.x
    const dyB = next.y - p.y
    const lenB = Math.sqrt(dxB * dxB + dyB * dyB) || 1
    const nxB = -dyB / lenB
    const nyB = dxB / lenB

    const nx = (nxA + nxB) / 2
    const ny = (nyA + nyB) / 2
    const len = Math.sqrt(nx * nx + ny * ny) || 1

    return {
      x: p.x + (nx / len) * padding,
      y: p.y + (ny / len) * padding,
    }
  })

  return `M ${paddedPoints.map((p) => `${p.x},${p.y}`).join(' L ')} Z`
}

const CommunityEvolution = ({ onNodeClick, onEventClick, onCommunityClick }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [timeWindows, setTimeWindows] = useState(10)
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [showCommunityBackground, setShowCommunityBackground] = useState(true)
  const [showNodeLabels, setShowNodeLabels] = useState(true)
  const [interpolatedFrame, setInterpolatedFrame] = useState(0)
  const [flashingEvents, setFlashingEvents] = useState([])

  const animationRef = useRef(null)
  const lastTimeRef = useRef(0)
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 700, height: 500 })

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    }
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
    return () => window.removeEventListener('resize', updateDimensions)
  }, [])

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await graphApi.getCommunityEvolution(timeWindows)
      setData(result.data || result)
      setCurrentFrame(0)
      setInterpolatedFrame(0)
      setIsPlaying(false)
    } catch (err) {
      setError('加载社群演化数据失败')
      console.error('Community evolution error:', err)
    } finally {
      setLoading(false)
    }
  }, [timeWindows])

  useEffect(() => {
    loadData()
  }, [loadData])

  const frames = useMemo(() => {
    if (!data) return []
    return data.animation_data?.frames || data.frames || []
  }, [data])

  const totalFrames = useMemo(() => {
    if (!data) return 0
    return data.animation_data?.total_frames || frames.length
  }, [data, frames.length])

  const events = useMemo(() => {
    if (!data) return []
    return data.events || []
  }, [data])

  const getInterpolatedNodes = useCallback(() => {
    if (frames.length === 0) return []

    const frameIdx = Math.floor(interpolatedFrame)
    const nextFrameIdx = Math.min(frameIdx + 1, frames.length - 1)
    const t = interpolatedFrame - frameIdx

    const currentFrameData = frames[frameIdx]
    const nextFrameData = frames[nextFrameIdx]

    if (!currentFrameData?.nodes) return []

    const currentNodes = currentFrameData.nodes
    const nextNodes = nextFrameData?.nodes || currentNodes

    const currentNodeMap = {}
    currentNodes.forEach((n) => {
      currentNodeMap[n.id] = n
    })

    const nextNodeMap = {}
    nextNodes.forEach((n) => {
      nextNodeMap[n.id] = n
    })

    const allNodeIds = new Set([...Object.keys(currentNodeMap), ...Object.keys(nextNodeMap)])

    return Array.from(allNodeIds).map((id) => {
      const curr = currentNodeMap[id]
      const next = nextNodeMap[id] || curr

      if (!curr) {
        return {
          ...next,
          x: next.x,
          y: next.y,
          opacity: t,
        }
      }

      if (!nextNodeMap[id]) {
        return {
          ...curr,
          x: curr.x,
          y: curr.y,
          opacity: 1 - t,
        }
      }

      return {
        ...curr,
        x: lerp(curr.x, next.x, t),
        y: lerp(curr.y, next.y, t),
        opacity: 1,
      }
    })
  }, [interpolatedFrame, frames])

  const getCurrentCommunities = useCallback(() => {
    if (frames.length === 0) return []
    const frameIdx = Math.floor(interpolatedFrame)
    return frames[frameIdx]?.communities || []
  }, [interpolatedFrame, frames])

  const getCurrentEvents = useCallback(() => {
    if (frames.length === 0) return []
    const frameIdx = Math.floor(interpolatedFrame)
    return frames[frameIdx]?.events || []
  }, [interpolatedFrame, frames])

  useEffect(() => {
    if (!isPlaying || frames.length < 2) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
      return
    }

    const animate = (timestamp) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp
      const delta = timestamp - lastTimeRef.current
      lastTimeRef.current = timestamp

      const frameIncrement = (delta / 1000) * speed * 2

      setInterpolatedFrame((prev) => {
        const next = prev + frameIncrement
        if (next >= totalFrames - 1) {
          setIsPlaying(false)
          return totalFrames - 1
        }
        return next
      })

      setCurrentFrame(Math.floor(interpolatedFrame))
      animationRef.current = requestAnimationFrame(animate)
    }

    animationRef.current = requestAnimationFrame(animate)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [isPlaying, speed, totalFrames, interpolatedFrame, frames.length])

  useEffect(() => {
    const currentEvents = getCurrentEvents()
    if (currentEvents.length > 0 && isPlaying) {
      setFlashingEvents(currentEvents.map((e) => e.community_id))
      const timer = setTimeout(() => setFlashingEvents([]), 500)
      return () => clearTimeout(timer)
    }
  }, [currentFrame, getCurrentEvents, isPlaying])

  const handlePlay = () => {
    if (interpolatedFrame >= totalFrames - 1) {
      setInterpolatedFrame(0)
      setCurrentFrame(0)
    }
    lastTimeRef.current = 0
    setIsPlaying(true)
  }

  const handlePause = () => {
    setIsPlaying(false)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setInterpolatedFrame(0)
    setCurrentFrame(0)
  }

  const handleStepForward = () => {
    setIsPlaying(false)
    setInterpolatedFrame((prev) => Math.min(prev + 1, totalFrames - 1))
    setCurrentFrame((prev) => Math.min(prev + 1, totalFrames - 1))
  }

  const handleStepBackward = () => {
    setIsPlaying(false)
    setInterpolatedFrame((prev) => Math.max(prev - 1, 0))
    setCurrentFrame((prev) => Math.max(prev - 1, 0))
  }

  const handleSliderChange = (value) => {
    setIsPlaying(false)
    setInterpolatedFrame(value)
    setCurrentFrame(Math.floor(value))
  }

  const handleEventClick = (event) => {
    setIsPlaying(false)
    setInterpolatedFrame(event.window_index)
    setCurrentFrame(event.window_index)
    if (onEventClick) {
      onEventClick(event)
    }
  }

  const handleNodeClick = (nodeId) => {
    if (onNodeClick) {
      onNodeClick(nodeId)
    }
  }

  const handleCommunityClick = (communityId) => {
    if (onCommunityClick) {
      onCommunityClick(communityId, currentFrame)
    }
  }

  const renderCommunityBackgrounds = (communities, nodes) => {
    if (!showCommunityBackground) return null

    const nodeMap = {}
    nodes.forEach((n) => {
      nodeMap[n.id] = n
    })

    return communities.map((community) => {
      const communityNodes = community.nodes
        .map((id) => nodeMap[id])
        .filter(Boolean)

      if (communityNodes.length === 0) return null

      const color = getCommunityColor(community.id)
      const isFlashing = flashingEvents.includes(community.id)

      if (communityNodes.length === 1) {
        const node = communityNodes[0]
        return (
          <circle
            key={`bg-${community.id}`}
            cx={node.x}
            cy={node.y}
            r={35}
            fill={color}
            fillOpacity={isFlashing ? 0.4 : 0.15}
            stroke={color}
            strokeWidth={isFlashing ? 3 : 1}
            style={{
              cursor: 'pointer',
              transition: 'all 0.3s ease',
            }}
            onClick={() => handleCommunityClick(community.id)}
          />
        )
      }

      const hull = calculateConvexHull(communityNodes)
      const path = convexHullToPath(hull)

      if (!path) return null

      return (
        <path
          key={`bg-${community.id}`}
          d={path}
          fill={color}
          fillOpacity={isFlashing ? 0.4 : 0.15}
          stroke={color}
          strokeWidth={isFlashing ? 3 : 1}
          style={{
            cursor: 'pointer',
            transition: 'all 0.3s ease',
          }}
          onClick={() => handleCommunityClick(community.id)}
        />
      )
    })
  }

  const renderNodes = (nodes) => {
    return nodes.map((node) => {
      const color = getCommunityColor(node.community)
      const isFlashing = flashingEvents.includes(node.community)

      return (
        <g
          key={node.id}
          transform={`translate(${node.x}, ${node.y})`}
          style={{
            cursor: 'pointer',
            opacity: node.opacity !== undefined ? node.opacity : 1,
            transition: 'opacity 0.3s ease',
          }}
          onClick={() => handleNodeClick(node.id)}
        >
          <circle
            r={8}
            fill={color}
            stroke={isFlashing ? '#fff' : '#fff'}
            strokeWidth={isFlashing ? 3 : 2}
            style={{
              filter: isFlashing ? 'drop-shadow(0 0 8px rgba(255,255,255,0.8))' : 'none',
              transition: 'all 0.3s ease',
            }}
          />
          {showNodeLabels && (
            <text
              y={18}
              textAnchor="middle"
              fontSize="10"
              fill="#666"
              style={{ pointerEvents: 'none' }}
            >
              {node.id}
            </text>
          )}
        </g>
      )
    })
  }

  const renderEventMarkers = (events) => {
    return events.map((event, idx) => {
      const config = EVENT_CONFIG[event.event_type]
      if (!config) return null

      const IconComponent = config.icon
      return (
        <g
          key={`event-${idx}`}
          transform={`translate(${20 + idx * 40}, 30)`}
          onClick={() => handleEventClick(event)}
          style={{ cursor: 'pointer' }}
        >
          <circle r={14} fill={config.color} fillOpacity={0.2} stroke={config.color} strokeWidth={2} />
          <text
            y={4}
            textAnchor="middle"
            fontSize="14"
            fill={config.color}
            style={{ pointerEvents: 'none' }}
          >
            <IconComponent />
          </text>
          <text
            y={30}
            textAnchor="middle"
            fontSize="9"
            fill="#666"
            style={{ pointerEvents: 'none' }}
          >
            {config.label}
          </text>
        </g>
      )
    })
  }

  const renderCommunityCountChart = () => {
    if (frames.length === 0) return null

    const width = 280
    const height = 100
    const padding = 25

    const communityCounts = frames.map((f) => f.communities?.length || 0)
    const maxCount = Math.max(...communityCounts, 1)

    const xStep = frames.length > 1 ? (width - padding * 2) / (frames.length - 1) : 0

    const points = communityCounts.map((count, i) => {
      const x = padding + i * xStep
      const y = padding + (height - padding * 2) * (1 - count / maxCount)
      return `${x},${y}`
    })

    const areaPath = `M ${padding},${height - padding} L ${points.join(' L ')} L ${width - padding},${height - padding} Z`
    const linePath = `M ${points.join(' L ')}`

    return (
      <svg width={width} height={height}>
        {[0, 0.5, 1].map((ratio, i) => (
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

        <path d={areaPath} fill="#722ed1" fillOpacity="0.15" />
        <path d={linePath} fill="none" stroke="#722ed1" strokeWidth="2" />

        {communityCounts.map((count, i) => {
          const x = padding + i * xStep
          const y = padding + (height - padding * 2) * (1 - count / maxCount)
          const isCurrent = Math.floor(interpolatedFrame) === i
          return (
            <g key={i}>
              <circle
                cx={x}
                cy={y}
                r={isCurrent ? 6 : 4}
                fill={isCurrent ? '#722ed1' : '#fff'}
                stroke="#722ed1"
                strokeWidth={2}
                style={{ cursor: 'pointer' }}
                onClick={() => handleSliderChange(i)}
              />
              {i % Math.ceil(frames.length / 5) === 0 && (
                <text x={x} y={height - 8} textAnchor="middle" fontSize="9" fill="#999">
                  T{i}
                </text>
              )}
            </g>
          )
        })}

        <text x={8} y={padding - 5} fontSize="10" fill="#999">
          {maxCount}
        </text>
        <text x={8} y={height - padding + 5} fontSize="10" fill="#999">
          0
        </text>
      </svg>
    )
  }

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="large" tip="加载中..." />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <Empty description={error} />
      </Card>
    )
  }

  if (!data || frames.length === 0) {
    return (
      <Card>
        <Empty description="暂无社群演化数据" />
      </Card>
    )
  }

  const interpolatedNodes = getInterpolatedNodes()
  const currentCommunities = getCurrentCommunities()
  const currentEvents = getCurrentEvents()

  return (
    <div className="community-evolution">
      <Row gutter={[16, 16]}>
        <Col span={17}>
          <Card
            title="社群演化动画"
            extra={
              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  时间窗口:
                </Text>
                <Select
                  value={timeWindows}
                  onChange={setTimeWindows}
                  size="small"
                  style={{ width: 100 }}
                >
                  {[5, 10, 15, 20].map((n) => (
                    <Option key={n} value={n}>
                      {n} 个
                    </Option>
                  ))}
                </Select>
                <Tooltip title="刷新数据">
                  <Button size="small" icon={<ReloadOutlined />} onClick={loadData} />
                </Tooltip>
              </Space>
            }
          >
            <div className="animation-controls" style={{ marginBottom: 16 }}>
              <Space size="small" style={{ marginBottom: 8 }}>
                <Tooltip title="上一帧">
                  <Button
                    size="small"
                    icon={<StepBackwardOutlined />}
                    onClick={handleStepBackward}
                    disabled={currentFrame === 0}
                  />
                </Tooltip>
                {isPlaying ? (
                  <Tooltip title="暂停">
                    <Button
                      size="small"
                      type="primary"
                      icon={<PauseCircleOutlined />}
                      onClick={handlePause}
                    />
                  </Tooltip>
                ) : (
                  <Tooltip title="播放">
                    <Button
                      size="small"
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={handlePlay}
                    />
                  </Tooltip>
                )}
                <Tooltip title="重置">
                  <Button size="small" icon={<ReloadOutlined />} onClick={handleReset} />
                </Tooltip>
                <Tooltip title="下一帧">
                  <Button
                    size="small"
                    icon={<StepForwardOutlined />}
                    onClick={handleStepForward}
                    disabled={currentFrame >= totalFrames - 1}
                  />
                </Tooltip>
                <Divider type="vertical" />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  速度:
                </Text>
                <Slider
                  min={0.5}
                  max={5}
                  step={0.5}
                  value={speed}
                  onChange={setSpeed}
                  style={{ width: 100 }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {speed}x
                </Text>
              </Space>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                  时间窗口 {currentFrame + 1} / {totalFrames}
                </Text>
                <Slider
                  min={0}
                  max={totalFrames - 1}
                  step={0.01}
                  value={interpolatedFrame}
                  onChange={handleSliderChange}
                  style={{ flex: 1 }}
                />
                <Progress
                  type="circle"
                  percent={Math.round(((currentFrame + 1) / totalFrames) * 100)}
                  size={40}
                />
              </div>

              <Space size="small" style={{ marginTop: 8 }}>
                <Switch
                  size="small"
                  checked={showCommunityBackground}
                  onChange={setShowCommunityBackground}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  显示社区背景
                </Text>
                <Switch
                  size="small"
                  checked={showNodeLabels}
                  onChange={setShowNodeLabels}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  显示节点标签
                </Text>
              </Space>
            </div>

            <div
              className="animation-container"
              ref={containerRef}
              style={{
                position: 'relative',
                height: dimensions.height,
                border: '1px solid #f0f0f0',
                borderRadius: 4,
                background: '#fafafa',
              }}
            >
              <svg
                ref={svgRef}
                width={dimensions.width}
                height={dimensions.height}
                style={{ display: 'block' }}
              >
                <defs>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {renderCommunityBackgrounds(currentCommunities, interpolatedNodes)}
                {renderNodes(interpolatedNodes)}
                {renderEventMarkers(currentEvents)}
              </svg>

              <div
                className="community-legend"
                style={{
                  position: 'absolute',
                  bottom: 10,
                  right: 10,
                  background: 'rgba(255,255,255,0.95)',
                  padding: 8,
                  borderRadius: 4,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  maxHeight: 120,
                  overflowY: 'auto',
                }}
              >
                <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                  社区图例
                </Text>
                {currentCommunities.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      marginBottom: 2,
                      cursor: 'pointer',
                    }}
                    onClick={() => handleCommunityClick(c.id)}
                  >
                    <div
                      style={{
                        width: 12,
                        height: 12,
                        borderRadius: 2,
                        background: getCommunityColor(c.id),
                      }}
                    />
                    <Text style={{ fontSize: 11 }}>
                      社区 {c.id} ({c.nodes?.length || 0}个节点)
                    </Text>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>

        <Col span={7}>
          <Card title="统计信息" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Statistic
                  title="合并总数"
                  value={data.total_merges || 0}
                  valueStyle={{ color: EVENT_CONFIG.merge.color, fontSize: 18 }}
                  prefix={<MergeCellsOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="分裂总数"
                  value={data.total_splits || 0}
                  valueStyle={{ color: EVENT_CONFIG.split.color, fontSize: 18 }}
                  prefix={<SplitCellsOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="新增社区"
                  value={data.total_new_communities || 0}
                  valueStyle={{ color: EVENT_CONFIG.new.color, fontSize: 18 }}
                  prefix={<PlusCircleOutlined />}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="解散社区"
                  value={data.total_dissolved_communities || 0}
                  valueStyle={{ color: EVENT_CONFIG.dissolved.color, fontSize: 18 }}
                  prefix={<DeleteOutlined />}
                />
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
              社区数量随时间变化
            </Text>
            {renderCommunityCountChart()}
          </Card>

          <Card
            title={
              <Space>
                <span>事件时间线</span>
                <Badge count={events.length} size="small" />
              </Space>
            }
            size="small"
            style={{ marginBottom: 16 }}
            bodyStyle={{ maxHeight: 300, overflowY: 'auto' }}
          >
            {events.length === 0 ? (
              <Empty description="暂无事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Timeline
                size="small"
                items={events.slice(0, 20).map((event, idx) => {
                  const config = EVENT_CONFIG[event.event_type]
                  const IconComponent = config?.icon || TeamOutlined
                  const color = config?.color || '#999'
                  const isCurrent = event.window_index === currentFrame

                  return {
                    color: color,
                    dot: <IconComponent style={{ fontSize: 14 }} />,
                    children: (
                      <div
                        style={{
                          cursor: 'pointer',
                          padding: 4,
                          borderRadius: 4,
                          background: isCurrent ? `${color}15` : 'transparent',
                          transition: 'background 0.3s ease',
                        }}
                        onClick={() => handleEventClick(event)}
                      >
                        <Space size="small">
                          <Tag color={color} style={{ margin: 0 }}>
                            T{event.window_index}
                          </Tag>
                          <Text strong style={{ fontSize: 12 }}>
                            {config?.label || event.event_type}
                          </Text>
                        </Space>
                        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 2 }}>
                          {event.description || `社区 ${event.community_id}`}
                        </Text>
                      </div>
                    ),
                  }
                })}
              />
            )}
          </Card>

          <Card title="事件类型说明" size="small">
            <List
              size="small"
              dataSource={Object.entries(EVENT_CONFIG)}
              renderItem={([type, config]) => {
                const IconComponent = config.icon
                return (
                  <List.Item>
                    <Space>
                      <Tag color={config.color}>
                        <IconComponent />
                      </Tag>
                      <Text style={{ fontSize: 12 }}>{config.label}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {type}
                      </Text>
                    </Space>
                  </List.Item>
                )
              }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default CommunityEvolution
