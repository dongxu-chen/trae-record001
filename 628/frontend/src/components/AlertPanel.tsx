import type { Alert } from '../types'

interface Props {
  alerts: Alert[]
  onAcknowledge: (id: string) => void
}

const severityConfig: Record<string, { bg: string; color: string; label: string; icon: string }> = {
  critical: { bg: '#ef444420', color: '#ef4444', label: '严重', icon: '🔴' },
  warning: { bg: '#f59e0b20', color: '#f59e0b', label: '警告', icon: '🟡' },
  info: { bg: '#3b82f620', color: '#3b82f6', label: '信息', icon: '🔵' },
}

function getAlertStyle(severity: string): React.CSSProperties {
  return {
    background: severityConfig[severity]?.bg || '#21262d',
    border: '1px solid',
    borderColor: severityConfig[severity]?.color || '#30363d',
    borderRadius: '8px',
    padding: '12px',
  }
}

function getSeverityBadgeStyle(severity: string): React.CSSProperties {
  return {
    padding: '2px 8px',
    borderRadius: '12px',
    fontSize: '10px',
    fontWeight: 700,
    background: severityConfig[severity]?.bg,
    color: severityConfig[severity]?.color,
  }
}

function getAckBtnStyle(acknowledged: boolean): React.CSSProperties {
  return {
    padding: '4px 10px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
    cursor: acknowledged ? 'default' : 'pointer',
    border: 'none',
    background: acknowledged ? '#10b98120' : '#30363d',
    color: acknowledged ? '#10b981' : '#8b949e',
  }
}

function getAnomalyChipStyle(direction: string): React.CSSProperties {
  return {
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: 600,
    background: direction === 'up' ? '#ef444415' : '#3b82f615',
    color: direction === 'up' ? '#ef4444' : '#3b82f6',
  }
}

export default function AlertPanel({ alerts, onAcknowledge }: Props) {
  if (alerts.length === 0) {
    return <div style={{ textAlign: 'center', padding: '24px', color: '#8b949e' }}>✅ 暂无告警</div>
  }

  const sorted = [...alerts].sort((a, b) => {
    const order = { critical: 3, warning: 2, info: 1 }
    return (order[b.severity as keyof typeof order] || 0) - (order[a.severity as keyof typeof order] || 0)
  })

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      maxHeight: '400px',
      overflowY: 'auto',
    }}>
      {sorted.map(alert => {
        const sev = severityConfig[alert.severity] || severityConfig.info
        return (
          <div
            key={alert.id}
            style={{
              ...getAlertStyle(alert.severity),
              ...(alert.suppressed ? { opacity: 0.5 } : {}),
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px',
                fontWeight: 600,
              }}>
                <span>{sev.icon}</span>
                {alert.title}
                {alert.suppressed && (
                  <span style={{ fontSize: '10px', color: '#8b949e' }}>🔇 已降噪</span>
                )}
              </div>
              <button
                style={getAckBtnStyle(alert.acknowledged)}
                onClick={() => !alert.acknowledged && onAcknowledge(alert.id)}
              >
                {alert.acknowledged ? '✓ 已确认' : '确认'}
              </button>
            </div>
            <div style={{
              display: 'flex',
              gap: '12px',
              fontSize: '11px',
              color: '#8b949e',
              marginBottom: '8px',
            }}>
              <span>⏱ {new Date(alert.created_at).toLocaleTimeString()}</span>
              <span>📊 {alert.anomalies.length} 个异常</span>
              <span style={getSeverityBadgeStyle(alert.severity)}>{sev.label}</span>
            </div>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '4px',
            }}>
              {alert.anomalies.slice(0, 8).map(a => (
                <span key={a.id} style={getAnomalyChipStyle(a.direction)}>
                  {a.direction === 'up' ? '↑' : '↓'} {a.metric.replace(/_/g, ' ').substring(0, 20)}
                </span>
              ))}
              {alert.anomalies.length > 8 && (
                <span style={{ fontSize: '10px', color: '#8b949e' }}>
                  +{alert.anomalies.length - 8} 更多
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
