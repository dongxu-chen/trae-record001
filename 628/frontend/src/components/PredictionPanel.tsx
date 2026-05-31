import type { Prediction } from '../types'

interface Props {
  predictions: Prediction[]
}

function getDirectionIcon(dir: string): string {
  if (dir === 'up') return '📈'
  if (dir === 'down') return '📉'
  return '📊'
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return '#ef4444'
  if (confidence >= 0.6) return '#f59e0b'
  return '#3b82f6'
}

function getPredictionCardStyle(confidence: number): React.CSSProperties {
  return {
    background: '#0f1117',
    border: '1px solid #21262d',
    borderLeft: `3px solid ${getConfidenceColor(confidence)}`,
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '8px',
  }
}

export default function PredictionPanel({ predictions }: Props) {
  if (predictions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e' }}>
        ✅ 当前无预测异常
      </div>
    )
  }

  const sorted = [...predictions].sort((a, b) => b.confidence - a.confidence)

  return (
    <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
      <div style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '12px',
        flexWrap: 'wrap',
      }}>
        <span style={{
          padding: '4px 10px',
          borderRadius: '6px',
          fontSize: '11px',
          fontWeight: 600,
          background: '#ef444420',
          color: '#ef4444',
        }}>
          高风险 {sorted.filter(p => p.confidence >= 0.8).length}
        </span>
        <span style={{
          padding: '4px 10px',
          borderRadius: '6px',
          fontSize: '11px',
          fontWeight: 600,
          background: '#f59e0b20',
          color: '#f59e0b',
        }}>
          中风险 {sorted.filter(p => p.confidence >= 0.6 && p.confidence < 0.8).length}
        </span>
        <span style={{
          padding: '4px 10px',
          borderRadius: '6px',
          fontSize: '11px',
          fontWeight: 600,
          background: '#3b82f620',
          color: '#3b82f6',
        }}>
          低风险 {sorted.filter(p => p.confidence < 0.6).length}
        </span>
      </div>

      {sorted.map((pred, i) => (
        <div key={i} style={getPredictionCardStyle(pred.confidence)}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '6px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>{getDirectionIcon(pred.direction)}</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#e1e4e8' }}>
                {pred.metric.replace(/_/g, ' ')}
              </span>
              <span style={{
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 600,
                background: pred.direction === 'up' ? '#ef444415' : '#3b82f615',
                color: pred.direction === 'up' ? '#ef4444' : '#3b82f6',
              }}>
                {pred.direction === 'up' ? '↑ 可能上升' : '↓ 可能下降'}
              </span>
            </div>
            <span style={{
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '10px',
              fontWeight: 700,
              background: `${getConfidenceColor(pred.confidence)}20`,
              color: getConfidenceColor(pred.confidence),
            }}>
              {(pred.confidence * 100).toFixed(0)}%
            </span>
          </div>

          <div style={{ fontSize: '11px', color: '#8b949e', lineHeight: '1.6', marginBottom: '8px' }}>
            {pred.reason}
          </div>

          <div style={{
            display: 'flex',
            gap: '16px',
            fontSize: '10px',
            color: '#6e7681',
          }}>
            <span>⏱ 预计时间: {new Date(pred.predicted_time).toLocaleTimeString()}</span>
            <span>📊 当前: {pred.current_value.toFixed(1)}</span>
            <span>⚠ 阈值: {pred.threshold.toFixed(1)}</span>
            <span>📐 斜率: {pred.trend_slope.toFixed(4)}</span>
          </div>

          <div style={{
            marginTop: '6px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{ fontSize: '10px', color: '#6e7681' }}>置信度</span>
            <div style={{
              flex: 1,
              height: '4px',
              borderRadius: '2px',
              background: '#21262d',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${Math.min(pred.confidence * 100, 100)}%`,
                height: '100%',
                borderRadius: '2px',
                background: getConfidenceColor(pred.confidence),
                transition: 'width 0.3s',
              }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
