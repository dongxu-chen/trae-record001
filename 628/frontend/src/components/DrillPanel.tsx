import { useState } from 'react'
import type { InjectionResult, DrillSummary } from '../types'

interface Props {
  results: InjectionResult[]
  summary: DrillSummary | null
  onRunDrill: () => void
  loading: boolean
}

function getTypeLabel(t: string): string {
  switch (t) {
    case 'spike': return '⚡ 突增'
    case 'drop': return '📉 突降'
    case 'gradual': return '📈 渐增'
    case 'oscillation': return '〰️ 振荡'
    default: return t
  }
}

function getSensitivityColor(s: number): string {
  if (s >= 0.8) return '#10b981'
  if (s >= 0.5) return '#f59e0b'
  return '#ef4444'
}

function getGradeStyle(grade: string): React.CSSProperties {
  const colors: Record<string, string> = {
    '优秀': '#10b981',
    '良好': '#3b82f6',
    '一般': '#f59e0b',
    '需改进': '#ef4444',
  }
  const c = colors[grade] || '#8b949e'
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    border: `3px solid ${c}`,
    color: c,
    fontSize: '14px',
    fontWeight: 800,
  }
}

export default function DrillPanel({ results, summary, onRunDrill, loading }: Props) {
  const [expandedResult, setExpandedResult] = useState<number | null>(null)

  return (
    <div>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '12px',
      }}>
        <button
          onClick={onRunDrill}
          disabled={loading}
          style={{
            padding: '6px 14px',
            borderRadius: '8px',
            border: '1px solid #30363d',
            background: loading ? '#21262d' : '#f9731620',
            color: loading ? '#8b949e' : '#f97316',
            fontSize: '12px',
            fontWeight: 600,
            cursor: loading ? 'default' : 'pointer',
          }}
        >
          {loading ? '⏳ 演练中...' : '🧪 运行演练'}
        </button>
        {summary && (
          <span style={{ fontSize: '11px', color: '#8b949e' }}>
            {summary.summary}
          </span>
        )}
      </div>

      {summary && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr 1fr 1fr 1fr',
          gap: '12px',
          alignItems: 'center',
          background: '#0f1117',
          border: '1px solid #21262d',
          borderRadius: '8px',
          padding: '12px',
          marginBottom: '12px',
        }}>
          <div style={getGradeStyle(summary.grade)}>
            {summary.grade.charAt(0)}
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: getSensitivityColor(summary.avg_sensitivity) }}>
              {(summary.avg_sensitivity * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '10px', color: '#6e7681' }}>平均灵敏度</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#3b82f6' }}>
              {(summary.detection_rate * 100).toFixed(0)}%
            </div>
            <div style={{ fontSize: '10px', color: '#6e7681' }}>检出率</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b' }}>
              {summary.avg_detection_delay}
            </div>
            <div style={{ fontSize: '10px', color: '#6e7681' }}>平均延迟步</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 700, color: summary.avg_false_positive_rate <= 0.05 ? '#10b981' : '#ef4444' }}>
              {(summary.avg_false_positive_rate * 100).toFixed(1)}%
            </div>
            <div style={{ fontSize: '10px', color: '#6e7681' }}>误报率</div>
          </div>
        </div>
      )}

      {summary?.by_type && (
        <div style={{ marginBottom: '12px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '6px', color: '#6e7681', borderBottom: '1px solid #21262d' }}>注入类型</th>
                <th style={{ textAlign: 'center', padding: '6px', color: '#6e7681', borderBottom: '1px solid #21262d' }}>测试数</th>
                <th style={{ textAlign: 'center', padding: '6px', color: '#6e7681', borderBottom: '1px solid #21262d' }}>灵敏度</th>
                <th style={{ textAlign: 'center', padding: '6px', color: '#6e7681', borderBottom: '1px solid #21262d' }}>检出率</th>
                <th style={{ textAlign: 'center', padding: '6px', color: '#6e7681', borderBottom: '1px solid #21262d' }}>误报率</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.by_type).map(([type, data]) => (
                <tr key={type}>
                  <td style={{ padding: '6px', color: '#e1e4e8' }}>{getTypeLabel(type)}</td>
                  <td style={{ padding: '6px', textAlign: 'center', color: '#8b949e' }}>{data.count}</td>
                  <td style={{
                    padding: '6px',
                    textAlign: 'center',
                    color: getSensitivityColor(data.avg_sensitivity),
                    fontWeight: 600,
                  }}>
                    {(data.avg_sensitivity * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center', color: '#3b82f6' }}>
                    {(data.detection_rate * 100).toFixed(0)}%
                  </td>
                  <td style={{ padding: '6px', textAlign: 'center', color: '#f59e0b' }}>
                    {(data.avg_false_positive * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {results.map((r, i) => (
          <div key={i} style={{
            background: '#0f1117',
            border: '1px solid #21262d',
            borderRadius: '6px',
            padding: '10px',
            marginBottom: '6px',
            cursor: 'pointer',
          }} onClick={() => setExpandedResult(expandedResult === i ? null : i)}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px' }}>{getTypeLabel(r.injection_type)}</span>
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#e1e4e8' }}>
                  {r.injected_metric.replace(/_/g, ' ')}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: getSensitivityColor(r.sensitivity),
                }}>
                  灵敏度 {(r.sensitivity * 100).toFixed(0)}%
                </span>
                <span style={{
                  fontSize: '11px',
                  color: r.detected_count > 0 ? '#10b981' : '#ef4444',
                }}>
                  {r.detected_count}/{r.injected_count} 检出
                </span>
                <span style={{ fontSize: '10px', color: '#6e7681' }}>
                  {expandedResult === i ? '▼' : '▶'}
                </span>
              </div>
            </div>

            {expandedResult === i && r.detection_details && (
              <div style={{ marginTop: '8px', borderTop: '1px solid #21262d', paddingTop: '8px' }}>
                <div style={{
                  display: 'flex',
                  gap: '2px',
                  alignItems: 'flex-end',
                  height: '40px',
                }}>
                  {r.detection_details.map((d, j) => (
                    <div
                      key={j}
                      style={{
                        flex: 1,
                        height: `${Math.min(Math.abs(d.actual - d.expected) / (Math.max(...r.detection_details.map(dd => Math.abs(dd.actual - dd.expected))) || 1) * 100, 100)}%`,
                        minHeight: '2px',
                        background: d.detected ? '#10b981' : '#ef444480',
                        borderRadius: '1px',
                      }}
                      title={`索引${d.index}: 实际${d.actual.toFixed(1)}, 预期${d.expected.toFixed(1)}, ${d.detected ? '已检出' : '未检出'}`}
                    />
                  ))}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '9px', color: '#6e7681' }}>
                  <span>延迟: {r.detection_delay}步</span>
                  <span>误报率: {(r.false_positive_rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {results.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e', fontSize: '13px' }}>
          点击"运行演练"注入异常并验证检测灵敏度
        </div>
      )}
    </div>
  )
}
