import { useMemo } from 'react'
import type { CorrelationResult } from '../types'

interface Props {
  correlations: CorrelationResult[]
}

const NODE_RADIUS = 24

interface GraphNode {
  id: string
  x: number
  y: number
  connections: number
}

interface GraphEdge {
  from: string
  to: string
  weight: number
  significant: boolean
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    width: '100%',
    height: '300px',
  },
  svg: {
    width: '100%',
    height: '100%',
  },
  tooltip: {
    position: 'absolute',
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '8px',
    padding: '8px 12px',
    fontSize: '12px',
    color: '#e1e4e8',
    pointerEvents: 'none',
    zIndex: 10,
  },
  legend: {
    display: 'flex',
    gap: '16px',
    marginTop: '8px',
    fontSize: '11px',
    color: '#8b949e',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  empty: {
    textAlign: 'center',
    padding: '24px',
    color: '#8b949e',
  },
}

function layoutNodes(metrics: string[], width: number, height: number): GraphNode[] {
  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(width, height) * 0.35

  return metrics.map((id, i) => {
    const angle = (2 * Math.PI * i) / metrics.length - Math.PI / 2
    return {
      id,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      connections: 0,
    }
  })
}

export default function CorrelationGraph({ correlations }: Props) {

  const graphData = useMemo(() => {
    if (correlations.length === 0) return { nodes: [], edges: [] }

    const metricSet = new Set<string>()
    for (const c of correlations) {
      metricSet.add(c.metric_a)
      metricSet.add(c.metric_b)
    }
    const metrics = Array.from(metricSet)

    const nodes = layoutNodes(metrics, 500, 280)

    const nodeMap = new Map(nodes.map(n => [n.id, n]))

    const edges: GraphEdge[] = correlations.map(c => ({
      from: c.metric_a,
      to: c.metric_b,
      weight: Math.abs(c.coefficient),
      significant: c.significant,
    }))

    for (const e of edges) {
      const a = nodeMap.get(e.from)
      const b = nodeMap.get(e.to)
      if (a) a.connections++
      if (b) b.connections++
    }

    return { nodes, edges }
  }, [correlations])

  if (correlations.length === 0) {
    return <div style={styles.empty}>暂无关联数据</div>
  }

  const maxWeight = Math.max(...graphData.edges.map(e => e.weight), 0.01)

  return (
    <div>
      <div style={styles.container}>
        <svg style={styles.svg} viewBox="0 0 500 280">
          <defs>
            <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="100%" stopColor="#a78bfa" />
            </linearGradient>
          </defs>

          {graphData.edges.map((edge, i) => {
            const from = graphData.nodes.find(n => n.id === edge.from)
            const to = graphData.nodes.find(n => n.id === edge.to)
            if (!from || !to) return null

            const normalizedWeight = edge.weight / maxWeight
            const strokeWidth = 1 + normalizedWeight * 4

            return (
              <line
                key={i}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={edge.significant ? '#3b82f6' : '#30363d'}
                strokeWidth={strokeWidth}
                strokeDasharray={edge.significant ? 'none' : '4 4'}
                opacity={edge.significant ? 0.7 : 0.3}
              />
            )
          })}

          {graphData.nodes.map((node) => {
            const isConnected = node.connections > 0
            const color = isConnected ? '#f97316' : '#8b949e'
            const r = NODE_RADIUS + node.connections * 2

            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={r}
                  fill={`${color}20`}
                  stroke={color}
                  strokeWidth={1.5}
                />
                <text
                  x={node.x}
                  y={node.y}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={color}
                  fontSize={8}
                  fontWeight={600}
                >
                  {node.id.replace(/_/g, ' ').length > 14
                    ? node.id.replace(/_/g, ' ').substring(0, 12) + '...'
                    : node.id.replace(/_/g, ' ')}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div style={styles.legend}>
        <div style={styles.legendItem}>
          <svg width="20" height="8">
            <line x1="0" y1="4" x2="20" y2="4" stroke="#3b82f6" strokeWidth="2" />
          </svg>
          <span>显著关联</span>
        </div>
        <div style={styles.legendItem}>
          <svg width="20" height="8">
            <line x1="0" y1="4" x2="20" y2="4" stroke="#30363d" strokeWidth="2" strokeDasharray="4 4" />
          </svg>
          <span>弱关联</span>
        </div>
        <div style={styles.legendItem}>
          <span style={{ color: '#f97316', fontSize: '14px' }}>●</span>
          <span>关联指标</span>
        </div>
      </div>

      <div style={{ marginTop: '12px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '6px', color: '#8b949e', borderBottom: '1px solid #30363d' }}>指标A</th>
              <th style={{ textAlign: 'left', padding: '6px', color: '#8b949e', borderBottom: '1px solid #30363d' }}>指标B</th>
              <th style={{ textAlign: 'left', padding: '6px', color: '#8b949e', borderBottom: '1px solid #30363d' }}>相关系数</th>
              <th style={{ textAlign: 'left', padding: '6px', color: '#8b949e', borderBottom: '1px solid #30363d' }}>显著性</th>
            </tr>
          </thead>
          <tbody>
            {correlations.slice(0, 10).map((c, i) => (
              <tr key={i}>
                <td style={{ padding: '6px', color: '#e1e4e8' }}>{c.metric_a.replace(/_/g, ' ')}</td>
                <td style={{ padding: '6px', color: '#e1e4e8' }}>{c.metric_b.replace(/_/g, ' ')}</td>
                <td style={{ padding: '6px', color: c.coefficient > 0 ? '#10b981' : '#ef4444' }}>
                  {c.coefficient.toFixed(3)}
                </td>
                <td style={{ padding: '6px' }}>
                  <span style={{
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: 600,
                    background: c.significant ? '#10b98120' : '#21262d',
                    color: c.significant ? '#10b981' : '#8b949e',
                  }}>
                    {c.significant ? '显著' : '不显著'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
