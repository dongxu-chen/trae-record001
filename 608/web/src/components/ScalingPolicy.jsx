import React, { useState } from 'react'
import { api } from '../services/api'

export default function ScalingPolicy({ events, nodes, onRefresh }) {
  const [addAddr, setAddAddr] = useState('')
  const [removeId, setRemoveId] = useState('')
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  const masters = nodes.filter((n) => n.role === 'master')

  const handleAddNode = async () => {
    if (!addAddr.trim()) return
    setBusy(true)
    setMessage(null)
    try {
      await api.addNode(addAddr.trim())
      setMessage({ type: 'success', text: `Node ${addAddr} added, rebalancing started` })
      setAddAddr('')
      onRefresh()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const handleRemoveNode = async () => {
    if (!removeId.trim()) return
    setBusy(true)
    setMessage(null)
    try {
      await api.removeNode(removeId.trim())
      setMessage({ type: 'success', text: `Node ${removeId.substring(0, 8)} removal started` })
      setRemoveId('')
      onRefresh()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div style={styles.sectionGrid}>
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Add Node (Scale Up)</h3>
          <p style={styles.description}>
            Add a new Redis node to the cluster. The system will automatically join the node
            and redistribute slots for balanced load.
          </p>
          <div style={styles.inputRow}>
            <input
              type="text"
              placeholder="e.g., 10.0.0.10:6379"
              value={addAddr}
              onChange={(e) => setAddAddr(e.target.value)}
              style={styles.input}
            />
            <button onClick={handleAddNode} disabled={busy || !addAddr.trim()} style={styles.addButton}>
              ↑ Add & Rebalance
            </button>
          </div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Remove Node (Scale Down)</h3>
          <p style={styles.description}>
            Remove a master node from the cluster. All slots will be migrated to other
            master nodes before removal.
          </p>
          <div style={styles.inputRow}>
            <select
              value={removeId}
              onChange={(e) => setRemoveId(e.target.value)}
              style={styles.select}
            >
              <option value="">Select a master node...</option>
              {masters.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.addr} ({n.id.substring(0, 8)})
                </option>
              ))}
            </select>
            <button
              onClick={handleRemoveNode}
              disabled={busy || !removeId || masters.length <= 3}
              style={{
                ...styles.removeButton,
                opacity: masters.length <= 3 ? 0.5 : 1,
              }}
            >
              ↓ Evacuate & Remove
            </button>
          </div>
          {masters.length <= 3 && (
            <p style={styles.warning}>Cannot remove: minimum 3 master nodes required</p>
          )}
        </div>
      </div>

      {message && (
        <div style={{
          ...styles.message,
          background: message.type === 'success' ? '#10b98122' : '#ef444422',
          color: message.type === 'success' ? '#10b981' : '#ef4444',
          border: `1px solid ${message.type === 'success' ? '#10b98144' : '#ef444444'}`,
        }}>
          {message.text}
        </div>
      )}

      <div style={{ ...styles.section, marginTop: '24px' }}>
        <h3 style={styles.sectionTitle}>Auto-Scaling Policy</h3>
        <div style={styles.policyGrid}>
          <div style={styles.policyItem}>
            <span style={styles.policyLabel}>Scale Up Triggers</span>
            <ul style={styles.policyList}>
              <li>Average memory usage &gt; 80%</li>
              <li>Total QPS &gt; 50,000</li>
              <li>Average hit rate &lt; 70%</li>
            </ul>
          </div>
          <div style={styles.policyItem}>
            <span style={styles.policyLabel}>Scale Down Triggers</span>
            <ul style={styles.policyList}>
              <li>Average memory usage &lt; 30%</li>
              <li>Total QPS &lt; 5,000</li>
            </ul>
          </div>
          <div style={styles.policyItem}>
            <span style={styles.policyLabel}>Constraints</span>
            <ul style={styles.policyList}>
              <li>Minimum 3 master nodes</li>
              <li>Maximum 12 master nodes</li>
              <li>5-minute cooldown between actions</li>
            </ul>
          </div>
        </div>
      </div>

      <div style={{ ...styles.section, marginTop: '24px' }}>
        <h3 style={styles.sectionTitle}>Scaling Event Log</h3>
        <div style={styles.eventTable}>
          {events.length === 0 ? (
            <div style={styles.empty}>No scaling events recorded</div>
          ) : (
            events.slice().reverse().map((event, i) => (
              <div key={i} style={styles.eventRow}>
                <span style={styles.eventTime}>
                  {new Date(event.timestamp * 1000).toLocaleString()}
                </span>
                <span style={{
                  ...styles.eventAction,
                  color: event.action === 'scale_up' ? '#10b981' : '#ef4444',
                }}>
                  {event.action === 'scale_up' ? '↑ UP' : '↓ DOWN'}
                </span>
                <span style={styles.eventReason}>{event.reason}</span>
                <span style={{
                  ...styles.eventStatus,
                  color: event.status === 'completed' ? '#10b981' : '#f59e0b',
                }}>
                  {event.status}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

const styles = {
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
    margin: '0 0 12px 0',
    fontSize: '16px',
    fontWeight: 600,
    color: '#e2e8f0',
  },
  description: {
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: 1.5,
    margin: '0 0 16px 0',
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '14px',
    fontFamily: 'monospace',
    outline: 'none',
  },
  select: {
    flex: 1,
    padding: '10px 14px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '14px',
    outline: 'none',
  },
  addButton: {
    padding: '10px 20px',
    background: '#10b981',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    whiteSpace: 'nowrap',
  },
  removeButton: {
    padding: '10px 20px',
    background: '#ef4444',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    whiteSpace: 'nowrap',
  },
  warning: {
    fontSize: '12px',
    color: '#f59e0b',
    marginTop: '8px',
  },
  message: {
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '14px',
    marginTop: '16px',
  },
  policyGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
  },
  policyItem: {},
  policyLabel: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e2e8f0',
    display: 'block',
    marginBottom: '8px',
  },
  policyList: {
    margin: 0,
    paddingLeft: '16px',
    fontSize: '13px',
    color: '#94a3b8',
    lineHeight: 1.8,
  },
  eventTable: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
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
    gap: '16px',
    padding: '10px 14px',
    background: '#0f172a',
    borderRadius: '8px',
  },
  eventTime: {
    fontSize: '12px',
    color: '#64748b',
    fontFamily: 'monospace',
    minWidth: '140px',
  },
  eventAction: {
    fontSize: '12px',
    fontWeight: 700,
    minWidth: '60px',
  },
  eventReason: {
    fontSize: '13px',
    color: '#94a3b8',
    flex: 1,
  },
  eventStatus: {
    fontSize: '12px',
    fontWeight: 600,
  },
}
