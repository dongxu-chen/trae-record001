import type { RootCauseResult } from '../types'

interface Props {
  rootCauses: RootCauseResult[]
}

function getConfidenceStyle(confidence: number): React.CSSProperties {
  if (confidence >= 0.7) {
    return {
      padding: '2px 8px',
      borderRadius: '12px',
      fontSize: '10px',
      fontWeight: 700,
      background: '#ef444420',
      color: '#ef4444',
    }
  }
  if (confidence >= 0.4) {
    return {
      padding: '2px 8px',
      borderRadius: '12px',
      fontSize: '10px',
      fontWeight: 700,
      background: '#f59e0b20',
      color: '#f59e0b',
    }
  }
  return {
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '10px',
    fontWeight: 700,
    background: '#3b82f620',
    color: '#3b82f6',
  }
}

function getConfidenceBarStyle(confidence: number): React.CSSProperties {
  return {
    width: `${Math.min(confidence * 100, 100)}%`,
    height: '100%',
    borderRadius: '3px',
    background: confidence >= 0.7 ? '#ef4444' : confidence >= 0.4 ? '#f59e0b' : '#3b82f6',
    transition: 'width 0.3s',
  }
}

const cardStyle: React.CSSProperties = {
  background: '#0f1117',
  border: '1px solid #21262d',
  borderRadius: '8px',
  padding: '12px',
  marginBottom: '8px',
}

export default function RootCausePanel({ rootCauses }: Props) {
  if (rootCauses.length === 0) {
    return <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e' }}>暂无根因分析数据</div>
  }

  return (
    <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
      {rootCauses.slice(0, 10).map((rc, i) => (
        <div key={i} style={cardStyle}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '8px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '10px',
                fontWeight: 700,
                background: rc.anomaly.direction === 'up' ? '#ef444420' : '#3b82f620',
                color: rc.anomaly.direction === 'up' ? '#ef4444' : '#3b82f6',
              }}>
                {rc.anomaly.direction === 'up' ? '↑' : '↓'} {rc.anomaly.metric.replace(/_/g, ' ')}
              </span>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>
                {new Date(rc.anomaly.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {rc.top_cause && (
              <span style={getConfidenceStyle(rc.top_cause.confidence)}>
                置信度 {(rc.top_cause.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>

          {rc.top_cause && (
            <div style={{
              background: '#1a1e2e',
              borderRadius: '6px',
              padding: '8px 10px',
              marginBottom: '8px',
              borderLeft: '3px solid',
              borderLeftColor: rc.top_cause.confidence >= 0.7 ? '#ef4444' : '#f59e0b',
            }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#e1e4e8', marginBottom: '4px' }}>
                🎯 推荐根因: {rc.top_cause.metric.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: '11px', color: '#8b949e', lineHeight: '1.5' }}>
                {rc.top_cause.reason}
              </div>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginTop: '6px',
              }}>
                <span style={{ fontSize: '10px', color: '#8b949e' }}>置信度</span>
                <div style={{
                  width: '60px',
                  height: '5px',
                  borderRadius: '3px',
                  background: '#21262d',
                  overflow: 'hidden',
                }}>
                  <div style={getConfidenceBarStyle(rc.top_cause.confidence)} />
                </div>
                <span style={{ fontSize: '10px', color: '#8b949e' }}>
                  相关 {rc.top_cause.correlation.toFixed(2)}
                </span>
                {rc.top_cause.lead_time > 0 && (
                  <span style={{ fontSize: '10px', color: '#8b949e' }}>
                    领先 {(rc.top_cause.lead_time / 1e9).toFixed(0)}s
                  </span>
                )}
              </div>
            </div>
          )}

          {rc.root_causes.length > 1 && (
            <div style={{ marginTop: '4px' }}>
              <div style={{ fontSize: '10px', color: '#6e7681', marginBottom: '4px' }}>
                其他可能原因 ({rc.root_causes.length - 1})
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {rc.root_causes.slice(1, 5).map((cause, j) => (
                  <span key={j} style={{
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    background: '#21262d',
                    color: '#8b949e',
                  }}>
                    {cause.metric.replace(/_/g, ' ')} ({(cause.confidence * 100).toFixed(0)}%)
                  </span>
                ))}
              </div>
            </div>
          )}

          {rc.top_cause && rc.top_cause.evidence.length > 0 && (
            <div style={{ marginTop: '6px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
              {rc.top_cause.evidence.map((ev, j) => (
                <span key={j} style={{
                  padding: '1px 6px',
                  borderRadius: '3px',
                  fontSize: '9px',
                  background: '#161b22',
                  color: '#6e7681',
                  border: '1px solid #21262d',
                }}>
                  {ev.type === 'correlation' ? '🔗' : ev.type === 'temporal_lead' ? '⏱' : ev.type === 'lagged_correlation' ? '📐' : '📋'} {ev.description.substring(0, 30)}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
