import { useState, useCallback } from 'react'
import { Card, Row, Col, Button, Space, Tag, message, Modal, Select, Drawer, Radio, Badge, Alert } from 'antd'
import {
  DeleteOutlined,
  PlusOutlined,
  SaveOutlined,
  LinkOutlined,
  ForkOutlined,
  MergeOutlined,
} from '@ant-design/icons'

const NODE_TYPES = {
  CONDITION: { color: '#1677ff', label: '条件', icon: '🔍' },
  AND: { color: '#13c2c2', label: 'AND(与)', icon: '∧' },
  OR: { color: '#eb2f96', label: 'OR(或)', icon: '∨' },
  ACTION: { color: '#52c41a', label: '动作', icon: '⚡' },
  AGGREGATE: { color: '#faad14', label: '聚合', icon: '📊' },
  THRESHOLD: { color: '#ff4d4f', label: '阈值', icon: '🎯' },
  PARALLEL_START: { color: '#722ed1', label: '并行开始', icon: '🔀' },
  PARALLEL_END: { color: '#9254de', label: '并行结束', icon: '🔁' },
  OUTPUT: { color: '#f5222d', label: '输出', icon: '📤' },
}

const EDGE_TYPES = {
  ALL: { label: '无条件', color: '#1677ff' },
  PASS: { label: '满足', color: '#52c41a' },
  FAIL: { label: '不满足', color: '#ff4d4f' },
}

const TEMPLATES = {
  CONDITION: {
    id: '',
    type: 'CONDITION',
    name: '条件节点',
    config: { field: '', operator: 'EQ', value: '' },
    x: 100,
    y: 100,
  },
  AND: {
    id: '',
    type: 'AND',
    name: 'AND(与)',
    config: { minMatch: 2 },
    x: 200,
    y: 100,
  },
  OR: {
    id: '',
    type: 'OR',
    name: 'OR(或)',
    config: { minMatch: 1 },
    x: 200,
    y: 100,
  },
  ACTION: {
    id: '',
    type: 'ACTION',
    name: '动作节点',
    config: { actionType: 'ADD_SCORE', params: {} },
    x: 300,
    y: 100,
  },
  AGGREGATE: {
    id: '',
    type: 'AGGREGATE',
    name: '聚合节点',
    config: { field: '', function: 'COUNT', window: '5m' },
    x: 500,
    y: 100,
  },
  THRESHOLD: {
    id: '',
    type: 'THRESHOLD',
    name: '阈值节点',
    config: { field: '', threshold: 100, operator: 'GT' },
    x: 300,
    y: 300,
  },
  PARALLEL_START: {
    id: '',
    type: 'PARALLEL_START',
    name: '并行开始',
    config: { branches: [] },
    x: 100,
    y: 100,
  },
  PARALLEL_END: {
    id: '',
    type: 'PARALLEL_END',
    name: '并行结束',
    config: { mergeStrategy: 'ANY' },
    x: 500,
    y: 100,
  },
  OUTPUT: {
    id: '',
    type: 'OUTPUT',
    name: '输出节点',
    config: { action: 'REJECT', riskScore: 200, riskTags: [] },
    x: 500,
    y: 300,
  },
}

const OP_MAP = { EQ: '==', NE: '!=', GT: '>', LT: '<', GE: '>=', LE: '<=' }

export default function RuleVisualEditor() {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [dragging, setDragging] = useState(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [logicMode, setLogicMode] = useState('OR')

  const addNode = (type) => {
    const template = { ...TEMPLATES[type] }
    template.id = `node_${Date.now()}`
    template.x = 100 + Math.random() * 400
    template.y = 100 + Math.random() * 300
    template.name = NODE_TYPES[type].label + ` ${nodes.filter(n => n.type === type).length + 1}`
    setNodes([...nodes, template])
    message.success(`已添加 ${NODE_TYPES[type].label} 节点`)
  }

  const removeNode = (nodeId) => {
    setNodes(nodes.filter(n => n.id !== nodeId))
    setEdges(edges.filter(e => e.source !== nodeId && e.target !== nodeId))
    if (selectedNode?.id === nodeId) {
      setSelectedNode(null)
      setDrawerVisible(false)
    }
  }

  const addEdge = (sourceId, targetId, edgeType = 'ALL') => {
    if (sourceId === targetId) return
    const exists = edges.find(e => e.source === sourceId && e.target === targetId)
    if (exists) {
      message.warning('连接已存在')
      return
    }
    setEdges([...edges, {
      id: `edge_${Date.now()}`,
      source: sourceId,
      target: targetId,
      edgeType: edgeType,
    }])
    message.success(`已添加连接 (${EDGE_TYPES[edgeType].label})`)
  }

  const handleNodeMouseDown = (e, node) => {
    e.preventDefault()
    setSelectedNode(node)
    setDragging(node.id)
    setDragOffset({ x: e.clientX - node.x, y: e.clientY - node.y })
  }

  const handleMouseMove = useCallback((e) => {
    if (!dragging) return
    setNodes(prev => prev.map(n =>
      n.id === dragging ? { ...n, x: e.clientX - dragOffset.x, y: e.clientY - dragOffset.y } : n
    ))
  }, [dragging, dragOffset])

  const handleMouseUp = useCallback(() => {
    setDragging(null)
  }, [])

  const handleNodeClick = (node) => {
    setSelectedNode(node)
    setDrawerVisible(true)
  }

  const buildConditionExpression = (node) => {
    const { field, operator, value } = node.config
    if (!field || !value) return null
    const op = OP_MAP[operator] || '=='
    return typeof value === 'string'
      ? `event.${field} ${op} "${value}"`
      : `event.${field} ${op} ${value}`
  }

  const buildThresholdExpression = (node) => {
    const { field, threshold, operator } = node.config
    if (!field) return null
    const op = OP_MAP[operator] || '>'
    return `event.${field} ${op} ${threshold}`
  }

  const traverseBranch = (node, visited = new Set()) => {
    if (visited.has(node.id)) return { condition: 'true', score: 0, tags: [] }
    visited.add(node.id)

    const outEdges = edges.filter(e => e.source === node.id)

    if (node.type === 'CONDITION') {
      const expr = buildConditionExpression(node)
      if (!expr) return { condition: 'true', score: 0, tags: [] }

      const passEdges = outEdges.filter(e => e.edgeType === 'PASS' || e.edgeType === 'ALL')
      const results = passEdges.map(edge => {
        const target = nodes.find(n => n.id === edge.target)
        return target ? traverseBranch(target, new Set(visited)) : null
      }).filter(Boolean)

      if (results.length === 0) {
        return { condition: expr, score: 0, tags: [] }
      }

      const combined = combineResults(results, 'AND')
      return {
        condition: `(${expr} && ${combined.condition})`,
        score: combined.score,
        tags: combined.tags,
      }
    }

    if (node.type === 'AND' || node.type === 'OR') {
      const children = outEdges
        .map(edge => nodes.find(n => n.id === edge.target))
        .filter(Boolean)
      const childResults = children.map(child => traverseBranch(child, new Set(visited)))
      return combineResults(childResults, node.type)
    }

    if (node.type === 'OUTPUT') {
      return {
        condition: 'true',
        score: node.config.riskScore || 0,
        tags: node.config.riskTags || [],
      }
    }

    if (node.type === 'PARALLEL_START') {
      const branches = outEdges
        .map(edge => nodes.find(n => n.id === edge.target))
        .filter(Boolean)
      const branchResults = branches.map(branch => traverseBranch(branch, new Set(visited)))
      return combineResults(branchResults, 'OR')
    }

    if (node.type === 'PARALLEL_END') {
      const passEdges = outEdges.filter(e => e.edgeType === 'PASS' || e.edgeType === 'ALL')
      const results = passEdges.map(edge => {
        const target = nodes.find(n => n.id === edge.target)
        return target ? traverseBranch(target, new Set(visited)) : null
      }).filter(Boolean)
      return combineResults(results, 'AND')
    }

    if (node.type === 'THRESHOLD') {
      const expr = buildThresholdExpression(node)
      const passEdges = outEdges.filter(e => e.edgeType === 'PASS' || e.edgeType === 'ALL')
      const results = passEdges.map(edge => {
        const target = nodes.find(n => n.id === edge.target)
        return target ? traverseBranch(target, new Set(visited)) : null
      }).filter(Boolean)
      return combineResults(results.length > 0 ? results : [{ condition: expr || 'true', score: 50, tags: ['阈值触发'] }], 'AND')
    }

    const passEdges = outEdges.filter(e => e.edgeType === 'PASS' || e.edgeType === 'ALL')
    const results = passEdges.map(edge => {
      const target = nodes.find(n => n.id === edge.target)
      return target ? traverseBranch(target, new Set(visited)) : null
    }).filter(Boolean)
    return combineResults(results, 'AND')
  }

  const combineResults = (results, logic) => {
    if (results.length === 0) return { condition: 'true', score: 0, tags: [] }
    if (results.length === 1) return results[0]

    const conditions = results.map(r => r.condition)
    const condition = logic === 'AND'
      ? `(${conditions.join(' && ')})`
      : `(${conditions.join(' || ')})`

    const totalScore = results.reduce((sum, r) => sum + r.score, 0)
    const allTags = [...new Set(results.flatMap(r => r.tags))]

    return { condition, score: totalScore, tags: allTags }
  }

  const generateGroovy = () => {
    const startNodes = nodes.filter(n => {
      const incoming = edges.filter(e => e.target === n.id)
      return incoming.length === 0
    })

    if (startNodes.length === 0) {
      return `// 请先添加节点并建立连接\nreturn [hit: false, riskScore: 0, riskTags: []]`
    }

    let script = `// 可视化编排生成的 Groovy 规则\ndef event = context.event\n\n`

    const results = startNodes.map(node => traverseBranch(node, new Set()))
    const combined = combineResults(results, logicMode)

    script += `// 组合逻辑: ${logicMode} (${startNodes.length} 条规则链)\n`
    script += `if (${combined.condition}) {\n`
    script += `    return [hit: true, riskScore: ${combined.score}, riskTags: ${JSON.stringify(combined.tags)}]\n`
    script += `}\n\n`
    script += `return [hit: false, riskScore: 0, riskTags: []]`

    return script
  }

  const handleSave = () => {
    const script = generateGroovy()
    Modal.info({
      title: `生成的 Groovy 脚本 (组合逻辑: ${logicMode})`,
      width: 750,
      content: (
        <pre style={{
          background: '#1e1e1e',
          color: '#d4d4d4',
          padding: 16,
          borderRadius: 8,
          fontSize: 13,
          maxHeight: 500,
          overflow: 'auto',
          fontFamily: 'Consolas, Monaco, monospace',
          lineHeight: 1.6,
        }}>
          {script}
        </pre>
      ),
    })
  }

  const handleConnect = () => {
    if (!selectedNode) {
      message.warning('请先选择源节点')
      return
    }

    const otherNodes = nodes.filter(n => n.id !== selectedNode.id)
    if (otherNodes.length === 0) {
      message.warning('没有可连接的目标节点')
      return
    }

    let selectedTarget = null
    let selectedEdgeType = 'ALL'

    Modal.confirm({
      title: '连接节点',
      width: 450,
      content: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>目标节点</div>
            <Select
              id="connect-target"
              style={{ width: '100%' }}
              placeholder="选择目标节点"
              onChange={(val) => { selectedTarget = val }}
              options={otherNodes.map(n => ({ value: n.id, label: `${n.name} (${NODE_TYPES[n.type].label})` }))}
            />
          </div>
          <div>
            <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>连接类型</div>
            <Radio.Group
              id="connect-edge-type"
              defaultValue="ALL"
              onChange={(e) => { selectedEdgeType = e.target.value }}
              options={Object.entries(EDGE_TYPES).map(([key, val]) => ({
                value: key,
                label: <Tag color={val.color}>{val.label}</Tag>,
              }))}
            />
          </div>
        </div>
      ),
      onOk: () => {
        if (!selectedTarget) {
          message.warning('请选择目标节点')
          return Promise.reject()
        }
        addEdge(selectedNode.id, selectedTarget, selectedEdgeType)
      },
    })
  }

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      <Card
        title={
          <Space>
            <span>规则可视化编排</span>
            <Radio.Group value={logicMode} onChange={(e) => setLogicMode(e.target.value)} size="small">
              <Radio.Button value="AND">AND(与)组合</Radio.Button>
              <Radio.Button value="OR">OR(或)组合</Radio.Button>
            </Radio.Group>
            <Tag color="blue">{nodes.length} 个节点</Tag>
            <Tag color="green">{edges.length} 条连接</Tag>
          </Space>
        }
        extra={
          <Space wrap>
            {Object.entries(NODE_TYPES).map(([type, config]) => (
              <Button key={type} size="small" onClick={() => addNode(type)}>
                {config.icon} {config.label}
              </Button>
            ))}
            <Button icon={<LinkOutlined />} size="small" onClick={handleConnect}>
              连接
            </Button>
            <Button type="primary" icon={<SaveOutlined />} size="small" onClick={handleSave}>
              生成脚本
            </Button>
          </Space>
        }
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: 650,
            background: '#fafafa',
            border: '2px dashed #d9d9d9',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          <div style={{
            position: 'absolute',
            top: 10,
            right: 10,
            padding: '8px 12px',
            background: 'rgba(255,255,255,0.95)',
            borderRadius: 6,
            fontSize: 12,
            zIndex: 100,
            display: 'flex',
            gap: 12,
          }}>
            {Object.entries(EDGE_TYPES).map(([key, val]) => (
              <span key={key}>
                <span style={{ color: val.color, fontWeight: 'bold' }}>──</span> {val.label}
              </span>
            ))}
          </div>

          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
            }}
          >
            {edges.map(edge => {
              const source = nodes.find(n => n.id === edge.source)
              const target = nodes.find(n => n.id === edge.target)
              if (!source || !target) return null

              const color = EDGE_TYPES[edge.edgeType]?.color || '#1677ff'
              const midX = (source.x + target.x) / 2 + 75
              const midY = (source.y + target.y) / 2 + 25

              return (
                <g key={edge.id}>
                  <line
                    x1={source.x + 150}
                    y1={source.y + 25}
                    x2={target.x}
                    y2={target.y + 25}
                    stroke={color}
                    strokeWidth={2}
                    strokeDasharray={edge.edgeType === 'FAIL' ? '5,5' : 'none'}
                  />
                  <text
                    x={midX}
                    y={midY - 5}
                    fill={color}
                    fontSize={11}
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {EDGE_TYPES[edge.edgeType]?.label || ''}
                  </text>
                </g>
              )
            })}
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#1677ff" />
              </marker>
            </defs>
          </svg>

          {nodes.map(node => {
            const typeConfig = NODE_TYPES[node.type]
            const isLogicNode = node.type === 'AND' || node.type === 'OR'
            const isParallelNode = node.type === 'PARALLEL_START' || node.type === 'PARALLEL_END'

            return (
              <div
                key={node.id}
                onMouseDown={(e) => handleNodeMouseDown(e, node)}
                onClick={() => handleNodeClick(node)}
                style={{
                  position: 'absolute',
                  left: node.x,
                  top: node.y,
                  width: isLogicNode || isParallelNode ? 180 : 160,
                  padding: '10px 12px',
                  background: '#fff',
                  border: `2px solid ${selectedNode?.id === node.id ? '#1677ff' : typeConfig.color}`,
                  borderRadius: isLogicNode ? 20 : isParallelNode ? 8 : 8,
                  cursor: 'move',
                  boxShadow: selectedNode?.id === node.id
                    ? '0 4px 16px rgba(22,119,255,0.3)'
                    : '0 2px 8px rgba(0,0,0,0.1)',
                  userSelect: 'none',
                  zIndex: selectedNode?.id === node.id ? 10 : 1,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13 }}>
                    <Tag color={typeConfig.color} style={{ marginRight: 6, fontSize: 11 }}>
                      {typeConfig.icon}
                    </Tag>
                    {node.name}
                  </span>
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    style={{ padding: 0, minWidth: 24 }}
                    onClick={(e) => { e.stopPropagation(); removeNode(node.id) }}
                  />
                </div>
              </div>
            )
          })}

          {nodes.length === 0 && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: '#bbb',
              fontSize: 15,
              textAlign: 'center',
            }}>
              <p>点击上方按钮添加节点</p>
              <p style={{ marginTop: 8 }}>
                <Tag color="cyan">∧ AND</Tag>
                <Tag color="magenta">∨ OR</Tag>
                用于条件组合
                <br />
                <Tag color="purple">🔀 并行</Tag>
                支持多分支并行判断
              </p>
              <p style={{ marginTop: 8, fontSize: 12 }}>连接可选：无条件 / 满足时 / 不满足时</p>
            </div>
          )}
        </div>
      </Card>

      <Drawer
        title={selectedNode ? `节点配置 - ${selectedNode.name}` : '节点配置'}
        open={drawerVisible}
        onClose={() => { setDrawerVisible(false); setSelectedNode(null) }}
        width={420}
      >
        {selectedNode && (
          <div>
            <Row gutter={8} style={{ marginBottom: 12 }}>
              <Col span={12}>
                <p><strong>类型:</strong> <Tag color={NODE_TYPES[selectedNode.type].color}>{NODE_TYPES[selectedNode.type].icon} {NODE_TYPES[selectedNode.type].label}</Tag></p>
              </Col>
              <Col span={12}>
                <p><strong>ID:</strong> <code style={{ fontSize: 11 }}>{selectedNode.id}</code></p>
              </Col>
            </Row>
            <p style={{ marginBottom: 12 }}><strong>名称:</strong> {selectedNode.name}</p>
            <p><strong>配置:</strong></p>
            <pre style={{
              background: '#f5f5f5',
              padding: 14,
              borderRadius: 8,
              fontSize: 12,
              fontFamily: 'Consolas, Monaco, monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}>
              {JSON.stringify(selectedNode.config, null, 2)}
            </pre>

            {selectedNode.type === 'CONDITION' && (
              <Alert
                style={{ marginTop: 12 }}
                type="info"
                showIcon
                message={`条件: ${buildConditionExpression(selectedNode) || '未配置'}`}
              />
            )}

            {selectedNode.type === 'THRESHOLD' && (
              <Alert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                message={`阈值: ${buildThresholdExpression(selectedNode) || '未配置'}`}
              />
            )}

            <p style={{ color: '#999', fontSize: 12, marginTop: 16 }}>
              💡 提示：选择节点后点击"连接"按钮，可选择目标节点和连接类型
              <br />
              🔄 AND 节点：所有子条件满足才触发
              <br />
              🔀 OR 节点：任一子条件满足即触发
              <br />
              ⚡ 并行开始/结束：多分支并行判断，独立执行
            </p>
          </div>
        )}
      </Drawer>
    </div>
  )
}
