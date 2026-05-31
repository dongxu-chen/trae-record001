import React from 'react'

function StatCard({ label, value, unit, color, icon }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.cardIcon}>{icon}</span>
        <span style={styles.cardLabel}>{label}</span>
      </div>
      <div style={{ ...styles.cardValue, color: color || '#f8fafc' }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
        {unit && <span style={styles.cardUnit}>{unit}</span>}
      </div>
    </div>
  )
}

export default function Dashboard({ clusterInfo, nodes, metrics, events }) {
  const masters = nodes.filter((n) => n.role === 'master')
  const replicas = nodes.filter((n) => n.role === 'replica')

  return (
    <div>
      <div style={styles.statsGrid}>
        <StatCard
          icon="🟢"
          label="Cluster State"
          value={clusterInfo?.cluster_state || 'N/A'}
          color={clusterInfo?.cluster_state === 'ok' ? '#10b981' : '#ef4444'}
        />
        <StatCard
          icon="📦"
          label="Master Nodes"
          value={masters.length}
          color="#3b82f6"
        />
        <StatCard
          icon="🔄"
          label="Replica Nodes"
          value={replicas.length}
          color="#8b5cf6"
        />
        <StatCard
          icon="💾"
          label="Avg Memory"
          value={metrics ? metrics.avg_memory_pct.toFixed(1) : 'N/A'}
          unit="%"
          color={metrics && metrics.avg_memory_pct > 80 ? '#ef4444' : '#10b981'}
        />
        <StatCard
          icon="⚡"
          label="Total QPS"
          value={metrics ? Math.round(metrics.total_qps) : 'N/A'}
          color="#f59e0b"
        />
        <StatCard
          icon="🎯"
          label="Avg Hit Rate"
          value={metrics ? metrics.avg_hit_rate.toFixed(1) : 'N/A'}
          unit="%"
          color={metrics && metrics.avg_hit_rate < 70 ? '#ef4444' : '#10b981'}
        />
        <StatCard
          icon="🔑"
          label="Total Keys"
          value={metrics ? metrics.total_keys : 'N/A'}
          color="#06b6d4"
        />
        <StatCard
          icon="📊"
          label="Slots Assigned"
          value={masters.reduce((acc, n) => {
            return acc + n.slots.reduce((s, sr) => s + sr.end - sr.start + 1, 0)
          }, 0)}
          unit="/ 16384"
          color="#ec4899"
        />
      </div>

      <div style={styles.sectionGrid}>
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Node Health</h3>
          <div style={styles.nodeList}>
            {nodes.map((node) => (
              <div key={node.id} style={styles.nodeRow}>
                <span
                  style={{
                    ...styles.nodeDot,
                    background: node.connected
                      ? node.role === 'master' ? '#3b82f6' : '#8b5cf6'
                      : '#ef4444',
                  }}
                />
                <span style={styles.nodeAddr}>{node.addr}</span>
                <span style={styles.nodeRole}>{node.role}</span>
                <span style={{
                  ...styles.nodeMem,
                  color: node.memory?.used_percent > 80 ? '#ef4444' : '#94a3b8',
                }}>
                  {node.memory?.used_percent?.toFixed(1) || '—'}% mem
                </span>
              </div>
            ))}
          </div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Recent Scaling Events</h3>
          <div style={styles.eventList}>
            {events.length === 0 ? (
              <div style={styles.empty}>No scaling events yet</div>
            ) : (
              events.slice(-10).reverse().map((event, i) => (
                <div key={i} style={styles.eventRow}>
                  <span style={{
                    ...styles.eventBadge,
                    background: event.action === 'scale_up' ? '#10b98133' : '#ef444433',
                    color: event.action === 'scale_up' ? '#10b981' : '#ef4444',
                  }}>
                    {event.action === 'scale_up' ? '↑ Scale Up' : '↓ Scale Down'}
                  </span>
                  <span style={styles.eventReason}>{event.reason}</span>
                  <span style={styles.eventStatus}>{event.status}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const styles = {
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  card: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '20px',
    border: '1px solid #334155',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  cardIcon: {
    fontSize: '16px',
  },
  cardLabel: {
    fontSize: '13px',
    color: '#94a3b8',
    fontWeight: 500,
  },
  cardValue: {
    fontSize: '28px',
    fontWeight: 700,
    lineHeight: 1.2,
  },
  cardUnit: {
    fontSize: '14px',
    fontWeight: 400,
    marginLeft: '4px',
    opacity: 0.7,
  },
  sectionGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  section: {
    background: '#1e293b',
    borderRadius: '12px',
    padding: '20px',
    border: '1px solid #334155',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '15px',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  nodeList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  nodeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    background: '#0f172a',
    borderRadius: '8px',
  },
  nodeDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  nodeAddr: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#e2e8f0',
    fontFamily: 'monospace',
  },
  nodeRole: {
    fontSize: '11px',
    color: '#64748b',
    textTransform: 'uppercase',
    fontWeight: 600,
  },
  nodeMem: {
    fontSize: '12px',
    marginLeft: 'auto',
  },
  eventList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  empty: {
    color: '#64748b',
    fontSize: '13px',
    textAlign: 'center',
    padding: '20px',
  },
  eventRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    background: '#0f172a',
    borderRadius: '8px',
  },
  eventBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  eventReason: {
    fontSize: '12px',
    color: '#94a3b8',
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  eventStatus: {
    fontSize: '11px',
    color: '#64748b',
  },
}
