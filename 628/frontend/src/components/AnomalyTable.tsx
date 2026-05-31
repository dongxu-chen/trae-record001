import { useState } from 'react'
import type { Anomaly, ClusterResult } from '../types'

interface Props {
  anomalies: Anomaly[]
  clusters: ClusterResult[]
}

function getDirectionBadgeStyle(dir: string): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 600,
    background: dir === 'up' ? '#ef444420' : '#3b82f620',
    color: dir === 'up' ? '#ef4444' : '#3b82f6',
  }
}

function getScoreBarStyle(): React.CSSProperties {
  return {
    width: '60px',
    height: '6px',
    borderRadius: '3px',
    background: '#21262d',
    overflow: 'hidden',
    display: 'inline-block',
    verticalAlign: 'middle',
    marginLeft: '8px',
  }
}

function getScoreFillStyle(score: number): React.CSSProperties {
  return {
    width: `${Math.min(score * 20, 100)}%`,
    height: '100%',
    borderRadius: '3px',
    background: score > 3 ? '#ef4444' : score > 2 ? '#f59e0b' : '#10b981',
  }
}

function getFilterBtnStyle(active: boolean): React.CSSProperties {
  return {
    padding: '4px 12px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
    cursor: 'pointer',
    border: '1px solid',
    borderColor: active ? '#f97316' : '#30363d',
    background: active ? '#f9731620' : 'transparent',
    color: active ? '#f97316' : '#8b949e',
  }
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '10px 12px',
  borderBottom: '1px solid #30363d',
  color: '#8b949e',
  fontWeight: 600,
  fontSize: '11px',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
}

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  borderBottom: '1px solid #21262d',
  color: '#e1e4e8',
}

export default function AnomalyTable({ anomalies, clusters }: Props) {
  const [directionFilter, setDirectionFilter] = useState<string>('all')

  const filtered = directionFilter === 'all'
    ? anomalies
    : anomalies.filter(a => a.direction === directionFilter)

  const sorted = [...filtered].sort((a, b) => b.score - a.score)

  if (anomalies.length === 0) {
    return <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e' }}>暂无异常数据</div>
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <button style={getFilterBtnStyle(directionFilter === 'all')} onClick={() => setDirectionFilter('all')}>
          全部 ({anomalies.length})
        </button>
        <button style={getFilterBtnStyle(directionFilter === 'up')} onClick={() => setDirectionFilter('up')}>
          ↑ 突增 ({anomalies.filter(a => a.direction === 'up').length})
        </button>
        <button style={getFilterBtnStyle(directionFilter === 'down')} onClick={() => setDirectionFilter('down')}>
          ↓ 突降 ({anomalies.filter(a => a.direction === 'down').length})
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr>
              <th style={thStyle}>指标</th>
              <th style={thStyle}>时间</th>
              <th style={thStyle}>方向</th>
              <th style={thStyle}>实际值</th>
              <th style={thStyle}>预期值</th>
              <th style={thStyle}>偏差</th>
              <th style={thStyle}>评分</th>
              <th style={thStyle}>聚类</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(a => (
              <tr key={a.id}>
                <td style={tdStyle}>
                  <span style={{ fontWeight: 600, color: '#f97316' }}>
                    {a.metric.replace(/_/g, ' ')}
                  </span>
                </td>
                <td style={tdStyle}>
                  {new Date(a.timestamp).toLocaleTimeString()}
                </td>
                <td style={tdStyle}>
                  <span style={getDirectionBadgeStyle(a.direction)}>
                    {a.direction === 'up' ? '↑ 突增' : a.direction === 'down' ? '↓ 突降' : '↕ 异常'}
                  </span>
                </td>
                <td style={tdStyle}>{a.value.toFixed(2)}</td>
                <td style={{ ...tdStyle, color: '#8b949e' }}>{a.expected.toFixed(2)}</td>
                <td style={tdStyle}>{a.deviation.toFixed(2)}</td>
                <td style={tdStyle}>
                  {a.score.toFixed(2)}
                  <span style={getScoreBarStyle()}>
                    <span style={getScoreFillStyle(a.score)} />
                  </span>
                </td>
                <td style={tdStyle}>
                  {a.cluster_id >= 0 ? (
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: 600,
                      background: '#a78bfa20',
                      color: '#a78bfa',
                    }}>
                      C{a.cluster_id}
                    </span>
                  ) : (
                    <span style={{ color: '#8b949e' }}>-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
