import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, Slider, Button, Space, Statistic, Row, Col, InputNumber, Select, List, Tag, Typography, Timeline, Tooltip, Spin, Empty, Progress, Divider, Switch, message } from 'antd'
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined, StepForwardOutlined, StepBackwardOutlined, VirusOutlined, HeartOutlined, UserOutlined, FireOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'

const { Title, Text, Paragraph } = Typography
const { Option } = Select

const DiffusionSimulation = ({ onNodeClick, onStepChange, nodeList = [] }) => {
  const [startNodes, setStartNodes] = useState([])
  const [infectionRate, setInfectionRate] = useState(0.3)
  const [recoveryRate, setRecoveryRate] = useState(0.1)
  const [maxSteps, setMaxSteps] = useState(50)
  const [autoSelectStart, setAutoSelectStart] = useState(true)

  const [simulationData, setSimulationData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playSpeed, setPlaySpeed] = useState(500)
  const [nodePositions, setNodePositions] = useState({})

  const intervalRef = useRef(null)
  const svgRef = useRef(null)

  const allNodeIds = simulationData?.affected_nodes || nodeList

  const runSimulation = useCallback(async () => {
    setLoading(true)
    setIsPlaying(false)
    setCurrentStep(0)

    try {
      const params = {
        start_nodes: autoSelectStart ? undefined : startNodes,
        infection_rate: infectionRate,
        recovery_rate: recoveryRate,
        max_steps: maxSteps,
      }

      const response = await graphApi.simulateDiffusion(params)
      const data = response.data

      setSimulationData(data)
      message.success('模拟完成')

      const positions = calculateNodePositions(data)
      setNodePositions(positions)

      onStepChange?.(data.steps[0])
    } catch (error) {
      console.error('Simulation error:', error)
      message.error('模拟失败，请检查参数')
    } finally {
      setLoading(false)
    }
  }, [startNodes, infectionRate, recoveryRate, maxSteps, autoSelectStart, onStepChange])

  const calculateNodePositions = (data) => {
    const positions = {}
    const nodes = data.affected_nodes || []
    const width = 600
    const height = 400
    const centerX = width / 2
    const centerY = height / 2

    if (nodes.length <= 1) {
      nodes.forEach((nodeId) => {
        positions[nodeId] = { x: centerX, y: centerY }
      })
      return positions
    }

    const layers = {}
    const visited = new Set()
    const queue = [...(data.parameters?.start_nodes || [])]

    queue.forEach((nodeId) => {
      layers[nodeId] = 0
      visited.add(nodeId)
    })

    while (queue.length > 0) {
      const current = queue.shift()
      const currentLayer = layers[current]

      const children = data.infection_tree?.[current] || []
      children.forEach((child) => {
        if (!visited.has(child)) {
          visited.add(child)
          layers[child] = currentLayer + 1
          queue.push(child)
        }
      })
    }

    nodes.forEach((nodeId) => {
      if (layers[nodeId] === undefined) {
        layers[nodeId] = 0
      }
    })

    const maxLayer = Math.max(...Object.values(layers), 1)
    const nodesByLayer = {}

    Object.entries(layers).forEach(([nodeId, layer]) => {
      if (!nodesByLayer[layer]) {
        nodesByLayer[layer] = []
      }
      nodesByLayer[layer].push(nodeId)
    })

    Object.entries(nodesByLayer).forEach(([layer, layerNodes]) => {
      const layerNum = parseInt(layer)
      const x = centerX + ((layerNum - maxLayer / 2) * (width - 80)) / Math.max(maxLayer, 1)
      const count = layerNodes.length

      layerNodes.forEach((nodeId, index) => {
        const y = height / 2 + ((index - (count - 1) / 2) * (height - 80)) / Math.max(count, 1)
        positions[nodeId] = { x, y }
      })
    })

    return positions
  }

  useEffect(() => {
    if (isPlaying && simulationData) {
      intervalRef.current = setInterval(() => {
        setCurrentStep((prev) => {
          const next = prev + 1
          if (next >= simulationData.steps.length) {
            setIsPlaying(false)
            return prev
          }
          onStepChange?.(simulationData.steps[next])
          return next
        })
      }, playSpeed)
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, simulationData, playSpeed, onStepChange])

  const handlePlay = () => {
    if (currentStep >= (simulationData?.steps.length || 0) - 1) {
      setCurrentStep(0)
      onStepChange?.(simulationData?.steps[0])
    }
    setIsPlaying(true)
  }

  const handlePause = () => {
    setIsPlaying(false)
  }

  const handleReset = () => {
    setIsPlaying(false)
    setCurrentStep(0)
    onStepChange?.(simulationData?.steps[0])
  }

  const handleStepForward = () => {
    if (simulationData && currentStep < simulationData.steps.length - 1) {
      const next = currentStep + 1
      setCurrentStep(next)
      onStepChange?.(simulationData.steps[next])
    }
  }

  const handleStepBackward = () => {
    if (currentStep > 0) {
      const prev = currentStep - 1
      setCurrentStep(prev)
      onStepChange?.(simulationData?.steps[prev])
    }
  }

  const getNodeStatus = (nodeId, stepData) => {
    if (!stepData) return 'susceptible'
    if (stepData.recovered?.includes(nodeId)) return 'recovered'
    if (stepData.infected?.includes(nodeId)) return 'infected'
    return 'susceptible'
  }

  const getNodeColor = (status) => {
    switch (status) {
      case 'infected':
        return '#ff4d4f'
      case 'recovered':
        return '#52c41a'
      default:
        return '#d9d9d9'
    }
  }

  const renderSpreadVisualization = () => {
    if (!simulationData) return null

    const stepData = simulationData.steps[currentStep]
    const width = 600
    const height = 400

    const edges = []
    Object.entries(simulationData.infection_tree || {}).forEach(([source, targets]) => {
      targets.forEach((target) => {
        edges.push({ source, target })
      })
    })

    return (
      <svg ref={svgRef} width={width} height={height} className="diffusion-svg">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
          </marker>
        </defs>

        {edges.map((edge, idx) => {
          const sourcePos = nodePositions[edge.source]
          const targetPos = nodePositions[edge.target]
          if (!sourcePos || !targetPos) return null

          const sourceStatus = getNodeStatus(edge.source, stepData)
          const targetStatus = getNodeStatus(edge.target, stepData)
          const isActive = sourceStatus === 'infected' || targetStatus === 'infected'

          return (
            <line
              key={idx}
              x1={sourcePos.x}
              y1={sourcePos.y}
              x2={targetPos.x}
              y2={targetPos.y}
              stroke={isActive ? '#ff4d4f' : '#e0e0e0'}
              strokeWidth={isActive ? 2 : 1}
              strokeOpacity={isActive ? 0.8 : 0.4}
              markerEnd="url(#arrowhead)"
            />
          )
        })}

        {Object.entries(nodePositions).map(([nodeId, pos]) => {
          const status = getNodeStatus(nodeId, stepData)
          const isNewInfection = stepData.new_infections?.includes(nodeId)
          const isStartNode = simulationData.parameters?.start_nodes?.includes(nodeId)

          return (
            <g
              key={nodeId}
              className="diffusion-node"
              onClick={() => onNodeClick?.(nodeId)}
              style={{ cursor: 'pointer' }}
            >
              {isNewInfection && (
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={20}
                  fill="none"
                  stroke="#ff4d4f"
                  strokeWidth={2}
                  opacity={0.6}
                  className="pulse-animation"
                />
              )}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isStartNode ? 14 : 10}
                fill={getNodeColor(status)}
                stroke={isStartNode ? '#faad14' : '#fff'}
                strokeWidth={isStartNode ? 3 : 2}
                className="diffusion-node-circle"
              />
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fontSize={10}
                fill={status === 'susceptible' ? '#666' : '#fff'}
                fontWeight="bold"
                pointerEvents="none"
              >
                {nodeId}
              </text>
            </g>
          )
        })}
      </svg>
    )
  }

  const renderTimeSeriesChart = () => {
    if (!simulationData) return null

    const width = 500
    const height = 200
    const padding = { top: 20, right: 20, bottom: 30, left: 40 }
    const chartWidth = width - padding.left - padding.right
    const chartHeight = height - padding.top - padding.bottom

    const steps = simulationData.steps
    const maxInfected = Math.max(...steps.map((s) => s.infection_count), 1)
    const maxRecovered = Math.max(...steps.map((s) => s.recovery_count), 1)
    const maxValue = Math.max(maxInfected, maxRecovered, 1)

    const xScale = (index) => padding.left + (index / Math.max(steps.length - 1, 1)) * chartWidth
    const yScale = (value) => padding.top + chartHeight - (value / maxValue) * chartHeight

    const infectedPath = steps.map((s, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(s.infection_count)}`).join(' ')
    const recoveredPath = steps.map((s, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(s.recovery_count)}`).join(' ')

    const gridLines = []
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartHeight / 4) * i
      const value = Math.round((maxValue / 4) * (4 - i))
      gridLines.push(
        <g key={`grid-${i}`}>
          <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#f0f0f0" strokeWidth={1} />
          <text x={padding.left - 5} y={y + 4} textAnchor="end" fontSize={10} fill="#999">
            {value}
          </text>
        </g>
      )
    }

    const xAxisLabels = []
    const labelStep = Math.ceil(steps.length / 10)
    steps.forEach((s, i) => {
      if (i % labelStep === 0 || i === steps.length - 1) {
        xAxisLabels.push(
          <text key={`x-${i}`} x={xScale(i)} y={height - padding.bottom + 15} textAnchor="middle" fontSize={10} fill="#999">
            {s.step}
          </text>
        )
      }
    })

    const currentX = xScale(currentStep)

    return (
      <svg width={width} height={height} className="time-series-chart">
        {gridLines}
        {xAxisLabels}

        <text x={width / 2} y={height - 5} textAnchor="middle" fontSize={11} fill="#666">
          步数
        </text>
        <text x={12} y={height / 2} textAnchor="middle" fontSize={11} fill="#666" transform={`rotate(-90, 12, ${height / 2})`}>
          数量
        </text>

        <path d={infectedPath} fill="none" stroke="#ff4d4f" strokeWidth={2} className="line-chart-path" />
        <path d={recoveredPath} fill="none" stroke="#52c41a" strokeWidth={2} className="line-chart-path" />

        <line x1={currentX} y1={padding.top} x2={currentX} y2={height - padding.bottom} stroke="#1890ff" strokeWidth={1} strokeDasharray="4,4" />

        {steps.map((s, i) => (
          <g key={`points-${i}`}>
            <circle
              cx={xScale(i)}
              cy={yScale(s.infection_count)}
              r={i === currentStep ? 5 : 2}
              fill="#ff4d4f"
              className="line-chart-point"
            />
            <circle
              cx={xScale(i)}
              cy={yScale(s.recovery_count)}
              r={i === currentStep ? 5 : 2}
              fill="#52c41a"
              className="line-chart-point"
            />
          </g>
        ))}

        <g transform={`translate(${width - padding.right - 120}, ${padding.top})`}>
          <rect x={0} y={0} width={120} height={40} fill="#fff" stroke="#f0f0f0" rx={4} />
          <circle cx={10} cy={15} r={4} fill="#ff4d4f" />
          <text x={20} y={18} fontSize={10} fill="#666">感染数</text>
          <circle cx={10} cy={30} r={4} fill="#52c41a" />
          <text x={20} y={33} fontSize={10} fill="#666">恢复数</text>
        </g>
      </svg>
    )
  }

  const renderInfectionTree = () => {
    if (!simulationData?.infection_tree) return null

    const tree = simulationData.infection_tree
    const startNodes = simulationData.parameters?.start_nodes || []

    const renderTreeNode = (nodeId, level = 0) => {
      const children = tree[nodeId] || []
      const stepData = simulationData.steps[currentStep]
      const status = getNodeStatus(nodeId, stepData)

      return (
        <div key={nodeId} className="tree-node" style={{ marginLeft: level * 20 }}>
          <div
            className="tree-node-content"
            onClick={() => onNodeClick?.(nodeId)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '4px 8px',
              borderRadius: 4,
              cursor: 'pointer',
              background: status === 'infected' ? '#fff1f0' : status === 'recovered' ? '#f6ffed' : '#fafafa',
              borderLeft: `3px solid ${getNodeColor(status)}`,
              marginBottom: 4,
            }}
          >
            <UserOutlined style={{ color: getNodeColor(status) }} />
            <Text strong={status === 'infected'} style={{ color: status === 'susceptible' ? '#999' : '#333' }}>
              节点 {nodeId}
            </Text>
            {status === 'infected' && <Tag color="red" size="small">感染中</Tag>}
            {status === 'recovered' && <Tag color="green" size="small">已恢复</Tag>}
          </div>
          {children.length > 0 && (
            <div className="tree-children">
              {children.map((child) => renderTreeNode(child, level + 1))}
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="infection-tree">
        {startNodes.map((nodeId) => renderTreeNode(nodeId, 0))}
      </div>
    )
  }

  const renderSpreadPaths = () => {
    if (!simulationData?.spread_paths?.length) return null

    const paths = [...simulationData.spread_paths].sort((a, b) => b.length - a.length).slice(0, 10)

    return (
      <List
        size="small"
        dataSource={paths}
        renderItem={(pathInfo, index) => (
          <List.Item key={index} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space>
                <Tag color={index === 0 ? 'gold' : 'blue'}>路径 {index + 1}</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  长度: {pathInfo.length}
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {pathInfo.start_node} → {pathInfo.end_node}
                </Text>
              </Space>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                {pathInfo.path.map((nodeId, nodeIndex) => (
                  <span key={nodeId} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Tag
                      color={getNodeColor(getNodeStatus(nodeId, simulationData.steps[currentStep]))}
                      style={{ margin: 0, cursor: 'pointer' }}
                      onClick={() => onNodeClick?.(nodeId)}
                    >
                      {nodeId}
                    </Tag>
                    {nodeIndex < pathInfo.path.length - 1 && <Text type="secondary">→</Text>}
                  </span>
                ))}
              </div>
            </Space>
          </List.Item>
        )}
      />
    )
  }

  const currentStepData = simulationData?.steps[currentStep]
  const progress = simulationData ? ((currentStep + 1) / simulationData.steps.length) * 100 : 0

  return (
    <div className="diffusion-simulation">
      <Card title="传播模拟参数配置" className="param-card">
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Text strong>自动选择起始节点 (PageRank)</Text>
                <Switch checked={autoSelectStart} onChange={setAutoSelectStart} />
              </Space>
              {!autoSelectStart && (
                <Select
                  mode="multiple"
                  placeholder="选择起始节点"
                  value={startNodes}
                  onChange={setStartNodes}
                  style={{ width: '100%' }}
                  disabled={loading}
                >
                  {allNodeIds.map((nodeId) => (
                    <Option key={nodeId} value={nodeId}>
                      节点 {nodeId}
                    </Option>
                  ))}
                </Select>
              )}
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text strong>最大步数</Text>
              <InputNumber
                min={1}
                max={500}
                value={maxSteps}
                onChange={setMaxSteps}
                style={{ width: '100%' }}
                disabled={loading}
              />
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text strong>感染率: {infectionRate.toFixed(2)}</Text>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={infectionRate}
                onChange={setInfectionRate}
                disabled={loading}
              />
            </Space>
          </Col>
          <Col span={12}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text strong>恢复率: {recoveryRate.toFixed(2)}</Text>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={recoveryRate}
                onChange={setRecoveryRate}
                disabled={loading}
              />
            </Space>
          </Col>
        </Row>
        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <Button type="primary" size="large" icon={<FireOutlined />} onClick={runSimulation} loading={loading}>
            运行模拟
          </Button>
        </div>
      </Card>

      {loading && (
        <div className="loading-container">
          <Spin size="large" tip="正在模拟传播过程..." />
        </div>
      )}

      {!loading && !simulationData && (
        <Card>
          <Empty description="请配置参数并运行模拟" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        </Card>
      )}

      {simulationData && !loading && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card className="statistic-card">
                <Statistic
                  title={<Space><VirusOutlined style={{ color: '#ff4d4f' }} />总感染数</Space>}
                  value={simulationData.total_infected}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="statistic-card">
                <Statistic
                  title={<Space><HeartOutlined style={{ color: '#52c41a' }} />总恢复数</Space>}
                  value={simulationData.total_recovered}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="statistic-card">
                <Statistic
                  title={<Space><FireOutlined style={{ color: '#faad14' }} />峰值感染</Space>}
                  value={simulationData.peak_infected}
                  valueStyle={{ color: '#faad14' }}
                  suffix={`/ 第 ${simulationData.peak_step} 步`}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="statistic-card">
                <Statistic
                  title={<Space><UserOutlined style={{ color: '#1890ff' }} />持续时间</Space>}
                  value={simulationData.duration}
                  suffix="步"
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
          </Row>

          <Card
            title="传播过程动画"
            extra={
              <Space>
                <Text type="secondary">播放速度:</Text>
                <Slider
                  min={100}
                  max={2000}
                  step={100}
                  value={2100 - playSpeed}
                  onChange={(v) => setPlaySpeed(2100 - v)}
                  style={{ width: 100 }}
                />
                <Button icon={<StepBackwardOutlined />} onClick={handleStepBackward} disabled={currentStep === 0 || isPlaying} />
                {isPlaying ? (
                  <Button type="primary" icon={<PauseCircleOutlined />} onClick={handlePause}>暂停</Button>
                ) : (
                  <Button type="primary" icon={<PlayCircleOutlined />} onClick={handlePlay}>播放</Button>
                )}
                <Button icon={<StepForwardOutlined />} onClick={handleStepForward} disabled={currentStep >= simulationData.steps.length - 1 || isPlaying} />
                <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
              </Space>
            }
          >
            <div style={{ marginBottom: 16 }}>
              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Text strong>步数: {currentStep} / {simulationData.steps.length - 1}</Text>
                <Space>
                  <Tag color="red">感染: {currentStepData?.infection_count || 0}</Tag>
                  <Tag color="green">恢复: {currentStepData?.recovery_count || 0}</Tag>
                  <Tag color="default">新增: {currentStepData?.new_infections?.length || 0}</Tag>
                </Space>
              </Space>
              <Progress percent={progress} showInfo={false} style={{ marginTop: 8 }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', background: '#fafafa', borderRadius: 8, padding: 16 }}>
              {renderSpreadVisualization()}
            </div>

            <div style={{ marginTop: 16, display: 'flex', justifyContent: 'center', gap: 16 }}>
              <Space>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#d9d9d9' }}></span>
                <Text type="secondary">易感</Text>
              </Space>
              <Space>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#ff4d4f' }}></span>
                <Text type="secondary">感染</Text>
              </Space>
              <Space>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: '#52c41a' }}></span>
                <Text type="secondary">恢复</Text>
              </Space>
              <Space>
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', border: '3px solid #faad14', background: '#fff' }}></span>
                <Text type="secondary">起始节点</Text>
              </Space>
            </div>
          </Card>

          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Card title="传播趋势">
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  {renderTimeSeriesChart()}
                </div>
              </Card>

              <Card title="最长传播路径">
                {simulationData.spread_paths?.length ? (
                  renderSpreadPaths()
                ) : (
                  <Empty description="暂无传播路径" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                )}
              </Card>
            </Col>
            <Col span={12}>
              <Card title="当前步骤详情">
                {currentStepData && (
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        新感染节点 ({currentStepData.new_infections?.length || 0})
                      </Text>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {currentStepData.new_infections?.length ? (
                          currentStepData.new_infections.map((nodeId) => (
                            <Tag key={nodeId} color="red" style={{ cursor: 'pointer' }} onClick={() => onNodeClick?.(nodeId)}>
                              {nodeId}
                            </Tag>
                          ))
                        ) : (
                          <Text type="secondary">无</Text>
                        )}
                      </div>
                    </div>

                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        感染中节点 ({currentStepData.infected?.length || 0})
                      </Text>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxHeight: 100, overflowY: 'auto' }}>
                        {currentStepData.infected?.length ? (
                          currentStepData.infected.map((nodeId) => (
                            <Tag key={nodeId} color="orange" style={{ cursor: 'pointer' }} onClick={() => onNodeClick?.(nodeId)}>
                              {nodeId}
                            </Tag>
                          ))
                        ) : (
                          <Text type="secondary">无</Text>
                        )}
                      </div>
                    </div>

                    <div>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>
                        已恢复节点 ({currentStepData.recovered?.length || 0})
                      </Text>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxHeight: 100, overflowY: 'auto' }}>
                        {currentStepData.recovered?.length ? (
                          currentStepData.recovered.map((nodeId) => (
                            <Tag key={nodeId} color="green" style={{ cursor: 'pointer' }} onClick={() => onNodeClick?.(nodeId)}>
                              {nodeId}
                            </Tag>
                          ))
                        ) : (
                          <Text type="secondary">无</Text>
                        )}
                      </div>
                    </div>
                  </Space>
                )}
              </Card>

              <Card title="感染树">
                <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                  {renderInfectionTree()}
                </div>
              </Card>
            </Col>
          </Row>
        </>
      )}

      <style>{`
        .diffusion-svg {
          background: #fff;
          border-radius: 8px;
        }
        
        .diffusion-node-circle {
          transition: all 0.3s ease;
        }
        
        .diffusion-node:hover .diffusion-node-circle {
          filter: brightness(1.1);
          transform: scale(1.1);
        }
        
        .pulse-animation {
          animation: pulse 1.5s ease-out infinite;
        }
        
        @keyframes pulse {
          0% {
            r: 10;
            opacity: 0.8;
          }
          100% {
            r: 25;
            opacity: 0;
          }
        }
        
        .time-series-chart {
          background: #fff;
          border-radius: 4px;
        }
        
        .tree-node-content:hover {
          background: #e6f7ff !important;
        }
        
        .param-card .ant-card-body {
          padding-bottom: 8px;
        }
      `}</style>
    </div>
  )
}

export default DiffusionSimulation
