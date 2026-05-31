import React from 'react'

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export default function ClusterView({ nodes, clusterInfo, onRefresh }) {
  const masters = nodes.filter((n) => n.role === 'master')
  const replicas = nodes.filter((n) => n.role === 'replica')

  return (
    <div>
      <div style={styles.infoBar}>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>Cluster State</span>
          <span style={{
            ...styles.infoValue,
            color: clusterInfo?.cluster_state === 'ok' ? '#10b981' : '#ef4444',
          }}>
            {clusterInfo?.cluster_state || 'Unknown'}
          </span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>Slots Covered</span>
          <span style={styles.infoValue}>{clusterInfo?.cluster_slots_ok || '—'}</span>
        </div>
        <div style={styles.infoItem}>
          <span style={styles.infoLabel}>Known Nodes</span>
          <span style={styles.infoValue}>{clusterInfo?.cluster_known_nodes || nodes.length}</span>
        </div>
      </div>

      <h3 style={styles.sectionTitle}>Master Nodes</h3>
      <div style={styles.nodesGrid}>
        {masters.map((node) => (
          <div key={node.id} style={styles.nodeCard}>
            <div style={styles.nodeCardHeader}>
              <span style={{
                ...styles.statusDot,
                background: node.connected ? '#10b981' : '#ef4444',
              }} />
              <span style={styles.nodeAddr}>{node.addr}</span>
              <span style={styles.nodeId}>{node.id.substring(0, 8)}</span>
            </div>
            <div style={styles.nodeCardBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Memory</span>
                <span style={styles.metricValue}>
                  {formatBytes(node.memory?.used_bytes)}
                  <span style={styles.metricSub}>
                    ({node.memory?.used_percent?.toFixed(1) || '—'}%)
                  </span>
                </span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Peak</span>
                <span style={styles.metricValue}>{formatBytes(node.memory?.peak_bytes)}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Fragment Ratio</span>
                <span style={styles.metricValue}>{node.memory?.fragment_ratio?.toFixed(2) || '—'}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Slots</span>
                <span style={styles.metricValue}>
                  {node.slots.reduce((acc, sr) => acc + sr.end - sr.start + 1, 0)}
                </span>
              </div>
              <div style={styles.slotRanges}>
                {node.slots.map((sr, i) => (
                  <span key={i} style={styles.slotTag}>
                    {sr.start === sr.end ? sr.start : `${sr.start}-${sr.end}`}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <h3 style={{ ...styles.sectionTitle, marginTop: '32px' }}>Replica Nodes</h3>
      <div style={styles.nodesGrid}>
        {replicas.map((node) => (
          <div key={node.id} style={styles.nodeCard}>
            <div style={styles.nodeCardHeader}>
              <span style={{
                ...styles.statusDot,
                background: node.connected ? '#10b981' : '#ef4444',
              }} />
              <span style={styles.nodeAddr}>{node.addr}</span>
              <span style={styles.nodeId}>{node.id.substring(0, 8)}</span>
            </div>
            <div style={styles.nodeCardBody}>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Master</span>
                <span style={styles.metricValue}>{node.master_id?.substring(0, 8) || '—'}</span>
              </div>
              <div style={styles.metricRow}>
                <span style={styles.metricLabel}>Memory</span>
                <span style={styles.metricValue}>{formatBytes(node.memory?.used_bytes)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles = {
  infoBar: {
    display: 'flex',
    gap: '24px',
    padding: '16px 20px',
    background: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    marginBottom: '24px',
  },
  infoItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  infoLabel: {
    fontSize: '12px',
    color: '#64748b',
    fontWeight: 500,
  },
  infoValue: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#f8fafc',
  },
  sectionTitle: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  nodesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '16px',
  },
  nodeCard: {
    background: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    overflow: 'hidden',
  },
  nodeCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    background: '#0f172a',
    borderBottom: '1px solid #334155',
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  nodeAddr: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e2e8f0',
    fontFamily: 'monospace',
  },
  nodeId: {
    fontSize: '11px',
    color: '#64748b',
    fontFamily: 'monospace',
    marginLeft: 'auto',
  },
  nodeCardBody: {
    padding: '12px 16px',
  },
  metricRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '4px 0',
  },
  metricLabel: {
    fontSize: '13px',
    color: '#94a3b8',
  },
  metricValue: {
    fontSize: '13px',
    color: '#e2e8f0',
    fontWeight: 500,
    fontFamily: 'monospace',
  },
  metricSub: {
    fontSize: '11px',
    color: '#64748b',
    marginLeft: '4px',
  },
  slotRanges: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginTop: '8px',
  },
  slotTag: {
    padding: '2px 8px',
    background: '#3b82f622',
    color: '#3b82f6',
    borderRadius: '4px',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
}
