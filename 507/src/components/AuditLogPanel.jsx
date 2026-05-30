import { useState, useMemo } from 'react'
import AuditLog from '../utils/auditLog'

function AuditLogPanel({ onRevert }) {
  const [filter, setFilter] = useState('all')
  const [expandedId, setExpandedId] = useState(null)

  const auditLog = useMemo(() => new AuditLog(), [])

  const entries = useMemo(() => {
    const filters = {}
    if (filter !== 'all') {
      if (filter === 'reverted') filters.reverted = true
      else if (filter === 'active') filters.reverted = false
      else filters.type = filter
    }
    return auditLog.getEntries({ ...filters, limit: 50 })
  }, [filter, auditLog])

  const stats = useMemo(() => auditLog.getStatistics(), [auditLog])

  const formatTime = (isoStr) => {
    try {
      const d = new Date(isoStr)
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const hours = String(d.getHours()).padStart(2, '0')
      const minutes = String(d.getMinutes()).padStart(2, '0')
      const seconds = String(d.getSeconds()).padStart(2, '0')
      return `${month}-${day} ${hours}:${minutes}:${seconds}`
    } catch {
      return isoStr
    }
  }

  const getTypeLabel = (type) => {
    const labels = {
      fill: '单列填充',
      batch_fill: '批量填充',
      revert: '撤销'
    }
    return labels[type] || type
  }

  const getTypeColor = (type) => {
    switch (type) {
      case 'fill': return '#2563eb'
      case 'batch_fill': return '#7c3aed'
      case 'revert': return '#dc2626'
      default: return '#6b7280'
    }
  }

  return (
    <div>
      {stats.totalOperations > 0 && (
        <div style={{
          padding: '10px 12px',
          background: 'linear-gradient(135deg, #fefce8 0%, #fef3c7 100%)',
          borderRadius: '8px',
          marginBottom: '12px',
          fontSize: '12px'
        }}>
          <div style={{ fontWeight: 600, marginBottom: '6px', color: '#92400e' }}>
            📊 审计概览
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', color: '#78350f' }}>
            <div>总操作: {stats.totalOperations}</div>
            <div>总填充: {stats.totalCellsFilled}格</div>
            <div>今日操作: {stats.todayOperations}</div>
            <div>今日填充: {stats.todayCellsFilled}格</div>
            <div>撤销次数: {stats.totalReverts}</div>
            <div>最常用: {stats.mostUsedRule}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '4px', marginBottom: '12px', flexWrap: 'wrap' }}>
        {[
          { key: 'all', label: '全部' },
          { key: 'fill', label: '单列' },
          { key: 'batch_fill', label: '批量' },
          { key: 'active', label: '有效' },
          { key: 'reverted', label: '已撤销' }
        ].map(f => (
          <button
            key={f.key}
            className={`btn ${filter === f.key ? 'btn-primary' : 'btn-default'}`}
            style={{ padding: '3px 8px', fontSize: '11px' }}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {entries.length === 0 ? (
        <div className="empty-state">
          <div style={{ fontSize: '28px', marginBottom: '8px' }}>📝</div>
          <div>暂无审计记录</div>
          <div style={{ fontSize: '12px', marginTop: '4px' }}>
            执行填充操作后将自动记录
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '400px', overflowY: 'auto' }}>
          {entries.map(entry => (
            <div
              key={entry.id}
              style={{
                border: `1px solid ${expandedId === entry.id ? '#667eea' : '#e5e7eb'}`,
                borderRadius: '6px',
                overflow: 'hidden',
                opacity: entry.reverted ? 0.6 : 1
              }}
            >
              <div
                style={{
                  padding: '8px 10px',
                  cursor: 'pointer',
                  background: expandedId === entry.id ? '#faf5ff' : 'white',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
                onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{
                    fontSize: '10px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    background: getTypeColor(entry.type) + '20',
                    color: getTypeColor(entry.type),
                    fontWeight: 500
                  }}>
                    {getTypeLabel(entry.type)}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 500, color: '#374151' }}>
                    {entry.columnName || '-'}
                  </span>
                  {entry.reverted && (
                    <span style={{ fontSize: '10px', color: '#dc2626', fontWeight: 500 }}>
                      已撤销
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '11px', color: '#9ca3af' }}>
                  {formatTime(entry.timestamp)}
                </span>
              </div>

              {expandedId === entry.id && (
                <div style={{
                  padding: '10px',
                  borderTop: '1px solid #e5e7eb',
                  background: '#faf5ff',
                  fontSize: '12px'
                }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px', color: '#4b5563' }}>
                    <div>规则: <strong>{entry.ruleName || '-'}</strong></div>
                    <div>填充数: <strong>{entry.fillCount}</strong></div>
                    <div>跳过数: {entry.skipCount}</div>
                    <div>影响行: {entry.totalAffected}</div>
                    <div>耗时: {entry.duration}ms</div>
                    <div>覆盖率: {entry.totalRows > 0 ? Math.round((entry.totalAffected / entry.totalRows) * 100) : 0}%</div>
                  </div>

                  {entry.beforeSample?.length > 0 && entry.afterSample?.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ fontWeight: 500, color: '#374151', marginBottom: '4px' }}>数据变化</div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ color: '#9ca3af', fontSize: '11px' }}>填充前</div>
                          <div style={{ fontFamily: 'monospace', color: '#6b7280' }}>
                            {entry.beforeSample.slice(0, 3).join(', ')}
                          </div>
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ color: '#9ca3af', fontSize: '11px' }}>填充后</div>
                          <div style={{ fontFamily: 'monospace', color: '#059669' }}>
                            {entry.afterSample.slice(0, 3).join(', ')}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {entry.affectedRows?.length > 0 && (
                    <div style={{ marginTop: '8px' }}>
                      <div style={{ fontWeight: 500, color: '#374151', marginBottom: '4px' }}>影响范围</div>
                      <div style={{ color: '#6b7280', fontSize: '11px' }}>
                        行: {entry.affectedRows.slice(0, 10).map(r => r + 1).join(', ')}
                        {entry.affectedRows.length > 10 ? ` ...共${entry.affectedRows.length}行` : ''}
                      </div>
                    </div>
                  )}

                  {!entry.reverted && entry.type !== 'revert' && onRevert && (
                    <button
                      className="btn btn-default"
                      style={{
                        marginTop: '8px',
                        padding: '4px 12px',
                        fontSize: '12px',
                        color: '#dc2626',
                        borderColor: '#fca5a5'
                      }}
                      onClick={(e) => {
                        e.stopPropagation()
                        onRevert(entry)
                      }}
                    >
                      撤销此操作
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AuditLogPanel
