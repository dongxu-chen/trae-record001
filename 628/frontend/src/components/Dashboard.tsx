import type { Anomaly, Alert, ClusterResult, CorrelationResult, TimeSeries, RootCauseResult, Prediction, InjectionResult, DrillSummary } from '../types'
import MetricChart from './MetricChart'
import AnomalyTable from './AnomalyTable'
import AlertPanel from './AlertPanel'
import CorrelationGraph from './CorrelationGraph'
import RootCausePanel from './RootCausePanel'
import PredictionPanel from './PredictionPanel'
import DrillPanel from './DrillPanel'

interface Props {
  anomalies: Anomaly[]
  clusters: ClusterResult[]
  correlations: CorrelationResult[]
  alerts: Alert[]
  series: TimeSeries[]
  selectedMetrics: string[]
  rootCauses: RootCauseResult[]
  predictions: Prediction[]
  drillResults: InjectionResult[]
  drillSummary: DrillSummary | null
  onMetricToggle: (name: string) => void
  onAcknowledge: (id: string) => void
  onRunDrill: () => void
  drillLoading: boolean
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  fullRow: {
    gridColumn: '1 / -1',
  },
  section: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  sectionHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid #30363d',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    fontWeight: 600,
    color: '#e1e4e8',
  },
  sectionBody: {
    padding: '16px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '20px',
    height: '20px',
    padding: '0 6px',
    borderRadius: '10px',
    fontSize: '11px',
    fontWeight: 700,
  },
}

export default function Dashboard({
  anomalies,
  clusters,
  correlations,
  alerts,
  series,
  selectedMetrics,
  rootCauses,
  predictions,
  drillResults,
  drillSummary,
  onMetricToggle,
  onAcknowledge,
  onRunDrill,
  drillLoading,
}: Props) {
  const filteredSeries = series.filter(s => selectedMetrics.includes(s.name))
  const anomalyTimestamps: Record<string, Anomaly[]> = {}
  for (const a of anomalies) {
    if (!anomalyTimestamps[a.metric]) anomalyTimestamps[a.metric] = []
    anomalyTimestamps[a.metric].push(a)
  }

  return (
    <div style={styles.container}>
      <div style={styles.fullRow}>
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <span>📊</span> 指标时序图
            <span style={{
              ...styles.badge,
              background: '#f9731620',
              color: '#f97316',
            }}>
              {selectedMetrics.length} 项
            </span>
          </div>
          <div style={styles.sectionBody}>
            <MetricChart
              series={filteredSeries}
              anomalies={anomalies}
              selectedMetrics={selectedMetrics}
              allMetrics={series.map(s => s.name)}
              onMetricToggle={onMetricToggle}
            />
          </div>
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>🔔</span> 告警面板
          <span style={{
            ...styles.badge,
            background: alerts.length > 0 ? '#ef444420' : '#30363d30',
            color: alerts.length > 0 ? '#ef4444' : '#8b949e',
          }}>
            {alerts.length}
          </span>
        </div>
        <div style={styles.sectionBody}>
          <AlertPanel alerts={alerts} onAcknowledge={onAcknowledge} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>🔗</span> 指标关联
          <span style={{
            ...styles.badge,
            background: '#3b82f620',
            color: '#3b82f6',
          }}>
            {correlations.filter(c => c.significant).length}
          </span>
        </div>
        <div style={styles.sectionBody}>
          <CorrelationGraph correlations={correlations} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>🎯</span> 根因推荐
          <span style={{
            ...styles.badge,
            background: rootCauses.length > 0 ? '#ef444420' : '#30363d30',
            color: rootCauses.length > 0 ? '#ef4444' : '#8b949e',
          }}>
            {rootCauses.length}
          </span>
        </div>
        <div style={styles.sectionBody}>
          <RootCausePanel rootCauses={rootCauses} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>🔮</span> 异常预测
          <span style={{
            ...styles.badge,
            background: predictions.length > 0 ? '#f59e0b20' : '#30363d30',
            color: predictions.length > 0 ? '#f59e0b' : '#8b949e',
          }}>
            {predictions.length}
          </span>
        </div>
        <div style={styles.sectionBody}>
          <PredictionPanel predictions={predictions} />
        </div>
      </div>

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>🧪</span> 异常演练
          <span style={{
            ...styles.badge,
            background: drillResults.length > 0 ? '#10b98120' : '#30363d30',
            color: drillResults.length > 0 ? '#10b981' : '#8b949e',
          }}>
            {drillResults.length}
          </span>
        </div>
        <div style={styles.sectionBody}>
          <DrillPanel
            results={drillResults}
            summary={drillSummary}
            onRunDrill={onRunDrill}
            loading={drillLoading}
          />
        </div>
      </div>

      <div style={styles.fullRow}>
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <span>🔍</span> 异常详情
            <span style={{
              ...styles.badge,
              background: '#a78bfa20',
              color: '#a78bfa',
            }}>
              {anomalies.length}
            </span>
          </div>
          <div style={styles.sectionBody}>
            <AnomalyTable anomalies={anomalies} clusters={clusters} />
          </div>
        </div>
      </div>
    </div>
  )
}
