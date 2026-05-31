import { useState, useEffect, useCallback } from 'react'
import type { Anomaly, Alert, ClusterResult, CorrelationResult, TimeSeries, RootCauseResult, Prediction, InjectionResult, DrillSummary } from './types'
import { demoDetect, demoGetSeries, getAlerts, acknowledgeAlert, demoDrill } from './api/client'
import Dashboard from './components/Dashboard'

const styles: Record<string, React.CSSProperties> = {
  app: {
    minHeight: '100vh',
    background: '#0f1117',
    color: '#e1e4e8',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  },
  header: {
    background: '#161b22',
    borderBottom: '1px solid #30363d',
    padding: '16px 24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logo: {
    width: 32,
    height: 32,
    borderRadius: '8px',
    background: 'linear-gradient(135deg, #f97316, #ef4444)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
    fontWeight: 700,
    color: '#fff',
  },
  title: {
    fontSize: '20px',
    fontWeight: 700,
    background: 'linear-gradient(135deg, #f97316, #ef4444)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    fontSize: '12px',
    color: '#8b949e',
    marginLeft: '8px',
  },
  btnGroup: {
    display: 'flex',
    gap: '8px',
  },
  btn: {
    padding: '8px 16px',
    borderRadius: '8px',
    border: '1px solid #30363d',
    background: '#21262d',
    color: '#e1e4e8',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  btnPrimary: {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: 'linear-gradient(135deg, #f97316, #ef4444)',
    color: '#fff',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  stats: {
    display: 'flex',
    gap: '16px',
    padding: '16px 24px',
  },
  statCard: {
    flex: 1,
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '12px',
    padding: '16px',
  },
  statLabel: {
    fontSize: '12px',
    color: '#8b949e',
    marginBottom: '4px',
  },
  statValue: {
    fontSize: '28px',
    fontWeight: 700,
  },
  content: {
    padding: '0 24px 24px',
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px',
    color: '#8b949e',
    fontSize: '16px',
  },
  spinner: {
    width: 20,
    height: 20,
    border: '2px solid #30363d',
    borderTopColor: '#f97316',
    borderRadius: '50%',
    animation: 'spin 0.6s linear infinite',
    marginRight: '12px',
  },
}

export default function App() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [clusters, setClusters] = useState<ClusterResult[]>([])
  const [correlations, setCorrelations] = useState<CorrelationResult[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [series, setSeries] = useState<TimeSeries[]>([])
  const [rootCauses, setRootCauses] = useState<RootCauseResult[]>([])
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [drillResults, setDrillResults] = useState<InjectionResult[]>([])
  const [drillSummary, setDrillSummary] = useState<DrillSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [drillLoading, setDrillLoading] = useState(false)
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])

  const runDemo = useCallback(async () => {
    setLoading(true)
    try {
      const [detectRes, seriesRes, alertsRes] = await Promise.all([
        demoDetect(),
        demoGetSeries(),
        getAlerts(),
      ])
      setAnomalies(detectRes.anomalies || [])
      setClusters(detectRes.clusters || [])
      setCorrelations(detectRes.correlations || [])
      setAlerts(alertsRes.alerts || [])
      setSeries(seriesRes.series || [])
      setRootCauses(detectRes.root_causes || [])
      setPredictions(detectRes.predictions || [])
      if (seriesRes.series?.length > 0) {
        setSelectedMetrics(seriesRes.series.slice(0, 3).map(s => s.name))
      }
    } catch (e) {
      console.error('Demo detection failed:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRunDrill = useCallback(async () => {
    setDrillLoading(true)
    try {
      const res = await demoDrill()
      setDrillResults(res.results || [])
      setDrillSummary(res.summary || null)
    } catch (e) {
      console.error('Drill failed:', e)
    } finally {
      setDrillLoading(false)
    }
  }, [])

  const handleAcknowledge = useCallback(async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId)
      const alertsRes = await getAlerts()
      setAlerts(alertsRes.alerts || [])
    } catch (e) {
      console.error('Acknowledge failed:', e)
    }
  }, [])

  useEffect(() => {
    runDemo()
  }, [runDemo])

  const criticalCount = alerts.filter(a => a.severity === 'critical').length
  const warningCount = alerts.filter(a => a.severity === 'warning').length
  const highConfPredCount = predictions.filter(p => p.confidence >= 0.8).length

  return (
    <div style={styles.app}>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f1117; }
        ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
      `}</style>

      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}>⚡</div>
          <div>
            <span style={styles.title}>Prometheus Anomaly Detector</span>
            <span style={styles.subtitle}>时序异常检测 · 根因推荐 · 异常预测 · 告警降噪</span>
          </div>
        </div>
        <div style={styles.btnGroup}>
          <button style={styles.btn} onClick={runDemo} disabled={loading}>
            🔄 刷新数据
          </button>
          <button style={styles.btnPrimary} onClick={runDemo} disabled={loading}>
            ▶ 运行检测
          </button>
        </div>
      </header>

      <div style={styles.stats}>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>检测异常</div>
          <div style={{ ...styles.statValue, color: '#f97316' }}>{anomalies.length}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>异常聚类</div>
          <div style={{ ...styles.statValue, color: '#a78bfa' }}>{clusters.length}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>严重告警</div>
          <div style={{ ...styles.statValue, color: '#ef4444' }}>{criticalCount}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>根因推荐</div>
          <div style={{ ...styles.statValue, color: '#ec4899' }}>{rootCauses.length}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>预测预警</div>
          <div style={{ ...styles.statValue, color: '#f59e0b' }}>{highConfPredCount}</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statLabel}>指标关联</div>
          <div style={{ ...styles.statValue, color: '#3b82f6' }}>{correlations.filter(c => c.significant).length}</div>
        </div>
      </div>

      {loading && (
        <div style={styles.loading}>
          <div style={styles.spinner} />
          正在运行异常检测...
        </div>
      )}

      <div style={styles.content}>
        <Dashboard
          anomalies={anomalies}
          clusters={clusters}
          correlations={correlations}
          alerts={alerts}
          series={series}
          selectedMetrics={selectedMetrics}
          rootCauses={rootCauses}
          predictions={predictions}
          drillResults={drillResults}
          drillSummary={drillSummary}
          onMetricToggle={(name: string) => {
            setSelectedMetrics(prev =>
              prev.includes(name) ? prev.filter(m => m !== name) : [...prev, name]
            )
          }}
          onAcknowledge={handleAcknowledge}
          onRunDrill={handleRunDrill}
          drillLoading={drillLoading}
        />
      </div>
    </div>
  )
}
