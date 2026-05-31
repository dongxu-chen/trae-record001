import React, { useState, useEffect, useCallback } from 'react'
import { api } from './services/api'
import Dashboard from './components/Dashboard'
import ClusterView from './components/ClusterView'
import Monitoring from './components/Monitoring'
import ScalingPolicy from './components/ScalingPolicy'
import MigrationStatus from './components/MigrationStatus'
import FailoverStatus from './components/FailoverStatus'
import CostAnalysis from './components/CostAnalysis'
import Simulation from './components/Simulation'

const TABS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'cluster', label: 'Cluster Nodes' },
  { key: 'monitoring', label: 'Monitoring' },
  { key: 'scaling', label: 'Scaling Policy' },
  { key: 'migration', label: 'Migration' },
  { key: 'failover', label: 'Failover' },
  { key: 'cost', label: 'Cost' },
  { key: 'simulation', label: 'Simulation' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [clusterInfo, setClusterInfo] = useState(null)
  const [nodes, setNodes] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [history, setHistory] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [info, nodeList, current, hist, evt] = await Promise.allSettled([
        api.getClusterInfo(),
        api.getClusterNodes(),
        api.getMonitorCurrent(),
        api.getMonitorHistory(),
        api.getScalerEvents(),
      ])
      if (info.status === 'fulfilled') setClusterInfo(info.value)
      if (nodeList.status === 'fulfilled') setNodes(nodeList.value || [])
      if (current.status === 'fulfilled') setMetrics(current.value)
      if (hist.status === 'fulfilled') setHistory(hist.value || [])
      if (evt.status === 'fulfilled') setEvents(evt.value || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [refresh])

  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard clusterInfo={clusterInfo} nodes={nodes} metrics={metrics} events={events} />
      case 'cluster':
        return <ClusterView nodes={nodes} clusterInfo={clusterInfo} onRefresh={refresh} />
      case 'monitoring':
        return <Monitoring metrics={metrics} history={history} />
      case 'scaling':
        return <ScalingPolicy events={events} nodes={nodes} onRefresh={refresh} />
      case 'migration':
        return <MigrationStatus nodes={nodes} onRefresh={refresh} />
      case 'failover':
        return <FailoverStatus nodes={nodes} onRefresh={refresh} />
      case 'cost':
        return <CostAnalysis nodes={nodes} onRefresh={refresh} />
      case 'simulation':
        return <Simulation nodes={nodes} onRefresh={refresh} />
      default:
        return null
    }
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>⟁ Redis Cluster Auto-Scaler</h1>
          {clusterInfo && (
            <span style={{
              ...styles.statusBadge,
              background: clusterInfo.cluster_state === 'ok' ? '#10b981' : '#ef4444',
            }}>
              {clusterInfo.cluster_state === 'ok' ? 'Cluster OK' : 'Cluster Issue'}
            </span>
          )}
        </div>
        <button onClick={refresh} style={styles.refreshBtn} disabled={loading}>
          ↻ Refresh
        </button>
      </header>

      {error && <div style={styles.error}>{error}</div>}

      <nav style={styles.nav}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.key ? styles.activeTab : {}),
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {renderTab()}
      </main>
    </div>
  )
}

const styles = {
  container: {
    minHeight: '100vh',
    background: '#0f172a',
    color: '#e2e8f0',
    fontFamily: "'Inter', -apple-system, sans-serif",
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 24px',
    background: '#1e293b',
    borderBottom: '1px solid #334155',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  title: {
    margin: 0,
    fontSize: '20px',
    fontWeight: 700,
    color: '#f8fafc',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: '9999px',
    fontSize: '12px',
    fontWeight: 600,
    color: '#fff',
  },
  refreshBtn: {
    padding: '8px 16px',
    background: '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  nav: {
    display: 'flex',
    gap: '4px',
    padding: '8px 24px',
    background: '#1e293b',
    borderBottom: '1px solid #334155',
  },
  tab: {
    padding: '8px 16px',
    background: 'transparent',
    color: '#94a3b8',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 500,
  },
  activeTab: {
    background: '#3b82f6',
    color: '#fff',
  },
  main: {
    padding: '24px',
  },
  error: {
    padding: '12px 24px',
    background: '#7f1d1d',
    color: '#fca5a5',
    fontSize: '14px',
  },
}
