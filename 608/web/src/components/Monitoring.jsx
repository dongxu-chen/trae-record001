import React, { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar,
} from 'recharts'

export default function Monitoring({ metrics, history }) {
  const memoryData = useMemo(() => {
    return (history || []).map((m) => ({
      time: new Date(m.timestamp * 1000).toLocaleTimeString(),
      memory: m.avg_memory_pct,
      hitRate: m.avg_hit_rate,
      qps: m.total_qps,
      keys: m.total_keys,
    }))
  }, [history])

  const nodeMetrics = useMemo(() => {
    if (!metrics || !metrics.nodes) return []
    return metrics.nodes.filter((n) => n.role === 'master')
  }, [metrics])

  return (
    <div>
      <h3 style={styles.sectionTitle}>Cluster Metrics Over Time</h3>
      <div style={styles.chartsGrid}>
        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Memory Usage (%)</h4>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={memoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Area type="monotone" dataKey="memory" stroke="#3b82f6" fill="#3b82f622" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Total QPS</h4>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={memoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Area type="monotone" dataKey="qps" stroke="#f59e0b" fill="#f59e0b22" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Hit Rate (%)</h4>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={memoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Line type="monotone" dataKey="hitRate" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div style={styles.chartCard}>
          <h4 style={styles.chartTitle}>Total Keys</h4>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={memoryData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Area type="monotone" dataKey="keys" stroke="#8b5cf6" fill="#8b5cf622" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <h3 style={{ ...styles.sectionTitle, marginTop: '32px' }}>Per-Node Metrics</h3>
      <div style={styles.nodesTable}>
        <div style={styles.tableHeader}>
          <span style={{ ...styles.tableCell, flex: 2 }}>Node</span>
          <span style={{ ...styles.tableCell, flex: 1 }}>Memory %</span>
          <span style={{ ...styles.tableCell, flex: 1 }}>QPS</span>
          <span style={{ ...styles.tableCell, flex: 1 }}>Hit Rate</span>
          <span style={{ ...styles.tableCell, flex: 1 }}>Keys</span>
          <span style={{ ...styles.tableCell, flex: 1 }}>Slots</span>
        </div>
        {nodeMetrics.map((node) => (
          <div key={node.node_id} style={styles.tableRow}>
            <span style={{ ...styles.tableCell, flex: 2, fontFamily: 'monospace' }}>
              {node.addr}
            </span>
            <span style={{
              ...styles.tableCell,
              flex: 1,
              color: node.memory_pct > 80 ? '#ef4444' : node.memory_pct > 60 ? '#f59e0b' : '#10b981',
              fontWeight: 600,
            }}>
              {node.memory_pct.toFixed(1)}%
            </span>
            <span style={{ ...styles.tableCell, flex: 1, fontFamily: 'monospace' }}>
              {Math.round(node.qps).toLocaleString()}
            </span>
            <span style={{
              ...styles.tableCell,
              flex: 1,
              color: node.hit_rate < 70 ? '#ef4444' : '#10b981',
              fontWeight: 600,
            }}>
              {node.hit_rate.toFixed(1)}%
            </span>
            <span style={{ ...styles.tableCell, flex: 1, fontFamily: 'monospace' }}>
              {node.keys.toLocaleString()}
            </span>
            <span style={{ ...styles.tableCell, flex: 1, fontFamily: 'monospace' }}>
              {node.slot_count}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  chartsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(440px, 1fr))',
    gap: '16px',
  },
  chartCard: {
    background: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    padding: '16px',
  },
  chartTitle: {
    margin: '0 0 12px 0',
    fontSize: '13px',
    fontWeight: 600,
    color: '#94a3b8',
  },
  nodesTable: {
    background: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    overflow: 'hidden',
  },
  tableHeader: {
    display: 'flex',
    padding: '12px 16px',
    background: '#0f172a',
    borderBottom: '1px solid #334155',
    fontSize: '12px',
    color: '#64748b',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  tableRow: {
    display: 'flex',
    padding: '10px 16px',
    borderBottom: '1px solid #1e293b',
    fontSize: '13px',
  },
  tableCell: {
    color: '#e2e8f0',
  },
}
