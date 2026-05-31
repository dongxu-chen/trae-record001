import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function MigrationStatus({ nodes, onRefresh }) {
  const [plan, setPlan] = useState(null)
  const [tasks, setTasks] = useState({})
  const [migrateFrom, setMigrateFrom] = useState('')
  const [migrateTo, setMigrateTo] = useState('')
  const [slotsInput, setSlotsInput] = useState('')
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  const masters = nodes.filter((n) => n.role === 'master')

  const loadPlan = async () => {
    try {
      const p = await api.getMigrationPlan()
      setPlan(p)
    } catch {}
  }

  const loadTasks = async () => {
    try {
      const t = await api.getMigrationTasks()
      setTasks(t)
    } catch {}
  }

  useEffect(() => {
    loadPlan()
    loadTasks()
    const interval = setInterval(loadTasks, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleExecuteRebalance = async () => {
    setBusy(true)
    setMessage(null)
    try {
      await api.executeMigration()
      setMessage({ type: 'success', text: 'Cluster rebalance started' })
      loadTasks()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const handleEvacuate = async (nodeId) => {
    setBusy(true)
    setMessage(null)
    try {
      await api.evacuateNode(nodeId)
      setMessage({ type: 'success', text: `Evacuation of ${nodeId.substring(0, 8)} started` })
      loadTasks()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const handleMigrateSlots = async () => {
    if (!migrateFrom || !migrateTo || !slotsInput.trim()) return
    const slots = slotsInput.split(',').map((s) => parseInt(s.trim(), 10)).filter((n) => !isNaN(n))
    if (slots.length === 0) return

    setBusy(true)
    setMessage(null)
    try {
      await api.migrateSlots(migrateFrom, migrateTo, slots)
      setMessage({ type: 'success', text: `Migration of ${slots.length} slots started` })
      setMigrateFrom('')
      setMigrateTo('')
      setSlotsInput('')
      loadTasks()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const handleCancel = async (taskId) => {
    try {
      await api.cancelMigration(taskId)
      setMessage({ type: 'success', text: 'Cancellation requested' })
      loadTasks()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    }
  }

  const handleBackup = async () => {
    setBusy(true)
    setMessage(null)
    try {
      await api.createBackup()
      setMessage({ type: 'success', text: 'Backup created successfully' })
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setBusy(false)
    }
  }

  const taskEntries = Object.entries(tasks || {})

  return (
    <div>
      <div style={styles.actionGrid}>
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Rebalance Cluster</h3>
          <p style={styles.description}>
            Generate and execute a rebalance plan to evenly distribute all 16,384 slots
            across master nodes.
          </p>
          <div style={styles.buttonRow}>
            <button onClick={loadPlan} style={styles.secondaryBtn}>Generate Plan</button>
            <button onClick={handleExecuteRebalance} disabled={busy} style={styles.primaryBtn}>
              Execute Rebalance
            </button>
            <button onClick={handleBackup} disabled={busy} style={styles.backupBtn}>
              ♦ Backup Before Migrate
            </button>
          </div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Migrate Specific Slots</h3>
          <p style={styles.description}>
            Manually migrate specific slot ranges from one master to another.
          </p>
          <div style={styles.formGrid}>
            <select value={migrateFrom} onChange={(e) => setMigrateFrom(e.target.value)} style={styles.select}>
              <option value="">Source node...</option>
              {masters.map((n) => (
                <option key={n.id} value={n.id}>{n.addr}</option>
              ))}
            </select>
            <select value={migrateTo} onChange={(e) => setMigrateTo(e.target.value)} style={styles.select}>
              <option value="">Target node...</option>
              {masters.map((n) => (
                <option key={n.id} value={n.id}>{n.addr}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Slots: 0,1,2,3"
              value={slotsInput}
              onChange={(e) => setSlotsInput(e.target.value)}
              style={styles.input}
            />
            <button onClick={handleMigrateSlots} disabled={busy || !migrateFrom || !migrateTo} style={styles.primaryBtn}>
              Migrate
            </button>
          </div>
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

      {plan && (
        <div style={{ ...styles.section, marginTop: '24px' }}>
          <h3 style={styles.sectionTitle}>
            Rebalance Plan — {plan.steps?.length || 0} slot migrations
            <span style={styles.planStatus}> {plan.status}</span>
          </h3>
          <div style={styles.planSummary}>
            {plan.steps?.slice(0, 20).map((step, i) => (
              <span key={i} style={{
                ...styles.slotChip,
                background: step.status === 'completed' ? '#10b98122' :
                  step.status === 'failed' ? '#ef444422' : '#3b82f622',
                color: step.status === 'completed' ? '#10b981' :
                  step.status === 'failed' ? '#ef4444' : '#3b82f6',
              }}>
                {step.slot}
              </span>
            ))}
            {plan.steps?.length > 20 && (
              <span style={styles.moreChip}>+{plan.steps.length - 20} more</span>
            )}
          </div>
        </div>
      )}

      <div style={{ ...styles.section, marginTop: '24px' }}>
        <h3 style={styles.sectionTitle}>Active Migration Tasks</h3>
        {taskEntries.length === 0 ? (
          <div style={styles.empty}>No active migrations</div>
        ) : (
          taskEntries.map(([taskId, task]) => (
            <div key={taskId} style={styles.taskCard}>
              <div style={styles.taskHeader}>
                <span style={styles.taskId}>{taskId}</span>
                <span style={{
                  ...styles.taskStatus,
                  color: task.status === 'completed' ? '#10b981' :
                    task.status === 'failed' ? '#ef4444' : '#f59e0b',
                }}>
                  {task.status}
                </span>
              </div>
              <div style={styles.progressBar}>
                <div style={{
                  ...styles.progressFill,
                  width: `${task.progress || 0}%`,
                  background: task.status === 'failed' ? '#ef4444' : '#3b82f6',
                }} />
              </div>
              <div style={styles.taskFooter}>
                <span style={styles.progressText}>{(task.progress || 0).toFixed(1)}%</span>
                <span style={styles.stepCount}>
                  {task.steps?.filter((s) => s.status === 'completed').length || 0} / {task.steps?.length || 0} slots
                </span>
                {task.status === 'running' && (
                  <button onClick={() => handleCancel(taskId)} style={styles.cancelBtn}>
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <div style={{ ...styles.section, marginTop: '24px' }}>
        <h3 style={styles.sectionTitle}>Quick Evacuate</h3>
        <p style={styles.description}>Move all slots from a master node to other masters.</p>
        <div style={styles.evacuateGrid}>
          {masters.map((node) => (
            <div key={node.id} style={styles.evacuateCard}>
              <span style={styles.evacuateAddr}>{node.addr}</span>
              <span style={styles.evacuateSlots}>
                {node.slots.reduce((acc, sr) => acc + sr.end - sr.start + 1, 0)} slots
              </span>
              <button
                onClick={() => handleEvacuate(node.id)}
                disabled={busy || masters.length <= 3}
                style={styles.evacuateBtn}
              >
                Evacuate
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const styles = {
  actionGrid: {
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
  buttonRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  primaryBtn: {
    padding: '10px 20px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  },
  secondaryBtn: {
    padding: '10px 20px',
    background: '#334155',
    color: '#e2e8f0',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  },
  backupBtn: {
    padding: '10px 20px',
    background: '#8b5cf6',
    color: '#fff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr auto',
    gap: '8px',
    alignItems: 'center',
  },
  select: {
    padding: '10px 14px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '14px',
    outline: 'none',
  },
  input: {
    padding: '10px 14px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '14px',
    fontFamily: 'monospace',
    outline: 'none',
  },
  message: {
    padding: '12px 16px',
    borderRadius: '8px',
    fontSize: '14px',
    marginTop: '16px',
  },
  planStatus: {
    fontSize: '13px',
    color: '#f59e0b',
    fontWeight: 500,
  },
  planSummary: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
  },
  slotChip: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontFamily: 'monospace',
  },
  moreChip: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    color: '#64748b',
  },
  empty: {
    color: '#64748b',
    fontSize: '13px',
    textAlign: 'center',
    padding: '20px',
  },
  taskCard: {
    padding: '16px',
    background: '#0f172a',
    borderRadius: '8px',
    marginBottom: '8px',
  },
  taskHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  taskId: {
    fontSize: '13px',
    fontFamily: 'monospace',
    color: '#94a3b8',
  },
  taskStatus: {
    fontSize: '13px',
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  progressBar: {
    height: '6px',
    background: '#334155',
    borderRadius: '3px',
    overflow: 'hidden',
    marginBottom: '8px',
  },
  progressFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  },
  taskFooter: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  progressText: {
    fontSize: '12px',
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  stepCount: {
    fontSize: '12px',
    color: '#64748b',
  },
  cancelBtn: {
    marginLeft: 'auto',
    padding: '4px 12px',
    background: '#ef444433',
    color: '#ef4444',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
  },
  evacuateGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '8px',
  },
  evacuateCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    background: '#0f172a',
    borderRadius: '8px',
  },
  evacuateAddr: {
    fontSize: '13px',
    fontFamily: 'monospace',
    color: '#e2e8f0',
    fontWeight: 600,
  },
  evacuateSlots: {
    fontSize: '12px',
    color: '#64748b',
  },
  evacuateBtn: {
    marginLeft: 'auto',
    padding: '6px 12px',
    background: '#ef444433',
    color: '#ef4444',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
  },
}
