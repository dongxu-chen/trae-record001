import React, { useState, useEffect } from 'react'
import { getAuditLogs, getAuditStatistics, getAuditLogDetail, getAuditTraceByDeadlock } from '../api/client'
import { FileText, CheckCircle, XCircle, User, Clock, Database, Filter, Eye, AlertTriangle } from 'lucide-react'

function Audit() {
  const [logs, setLogs] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedLog, setSelectedLog] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [filters, setFilters] = useState({
    action: '',
    operator: '',
    success: '',
    source: '',
    transaction_type: ''
  })
  const [showFilters, setShowFilters] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [filters])

  const loadData = async () => {
    try {
      const [logsRes, statsRes] = await Promise.all([
        getAuditLogs({ ...filters, limit: 100 }),
        getAuditStatistics()
      ])
      setLogs(logsRes.data.data || [])
      setStatistics(statsRes.data.data || null)
    } catch (err) {
      console.error('Failed to load audit data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetail = async (id) => {
    try {
      const res = await getAuditLogDetail(id)
      setSelectedLog(res.data.data)
      setShowModal(true)
    } catch (err) {
      alert('获取详情失败: ' + err.message)
    }
  }

  const getActionColor = (action) => {
    const colors = {
      'KILL_TRANSACTION': '#dc3545',
      'MANUAL_KILL': '#fd7e14',
      'SYSTEM_START': '#198754',
      'SYSTEM_STOP': '#6c757d'
    }
    return colors[action] || '#6c757d'
  }

  const getSourceColor = (source) => {
    const colors = {
      'SYSTEM': '#198754',
      'MANUAL': '#fd7e14',
      'SANDBOX': '#6610f2'
    }
    return colors[source] || '#6c757d'
  }

  const getTransactionTypeColor = (type) => {
    const colors = {
      'READ': '#198754',
      'WRITE': '#fd7e14',
      'DDL': '#dc3545'
    }
    return colors[type] || '#6c757d'
  }

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({
      action: '',
      operator: '',
      success: '',
      source: '',
      transaction_type: ''
    })
  }

  if (loading) {
    return <div className="loading">加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>操作审计日志</h2>
        <p>记录所有死锁解除操作和业务影响追踪</p>
      </div>

      {statistics && (
        <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(13, 110, 253, 0.1)' }}>
              <FileText size={24} color="#0d6efd" />
            </div>
            <div>
              <div className="stat-value">{statistics.total_logs}</div>
              <div className="stat-label">总操作数</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(25, 135, 84, 0.1)' }}>
              <CheckCircle size={24} color="#198754" />
            </div>
            <div>
              <div className="stat-value">{statistics.success_count}</div>
              <div className="stat-label">成功</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(220, 53, 69, 0.1)' }}>
              <XCircle size={24} color="#dc3545" />
            </div>
            <div>
              <div className="stat-value">{statistics.failed_count}</div>
              <div className="stat-label">失败</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(13, 202, 240, 0.1)' }}>
              <AlertTriangle size={24} color="#0dcaf0" />
            </div>
            <div>
              <div className="stat-value">{statistics.success_rate ? statistics.success_rate.toFixed(1) : '0'}%</div>
              <div className="stat-label">成功率</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(102, 16, 242, 0.1)' }}>
              <Database size={24} color="#6610f2" />
            </div>
            <div>
              <div className="stat-value">{statistics.auto_kills || 0}</div>
              <div className="stat-label">自动KILL</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(253, 126, 20, 0.1)' }}>
              <User size={24} color="#fd7e14" />
            </div>
            <div>
              <div className="stat-value">{statistics.manual_kills || 0}</div>
              <div className="stat-label">手动KILL</div>
            </div>
          </div>
        </div>
      )}

      {statistics && statistics.by_source && statistics.by_source.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3>操作来源分布</h3>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', padding: '20px' }}>
            {statistics.by_source.map((s, i) => (
              <div key={i} style={{ 
                flex: '1', minWidth: '150px', 
                padding: '16px', borderRadius: '8px',
                border: `2px solid ${getSourceColor(s.key)}`,
                background: `${getSourceColor(s.key)}10`
              }}>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  {s.key === 'SYSTEM' ? '系统自动' : s.key === 'MANUAL' ? '手动操作' : s.key}
                </div>
                <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{s.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>操作日志</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn" onClick={() => setShowFilters(!showFilters)}>
              <Filter size={16} style={{ marginRight: '6px', verticalAlign: 'text-bottom' }} />
              筛选
            </button>
            {(Object.values(filters).some(v => v !== '')) && (
              <button className="btn" onClick={clearFilters}>
                清除筛选
              </button>
            )}
          </div>
        </div>

        {showFilters && (
          <div style={{ padding: '16px', background: '#f8f9fa', borderBottom: '1px solid #dee2e6' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <div className="form-group">
                <label>操作类型</label>
                <select 
                  className="form-control"
                  value={filters.action}
                  onChange={(e) => handleFilterChange('action', e.target.value)}
                >
                  <option value="">全部</option>
                  <option value="KILL_TRANSACTION">KILL事务</option>
                  <option value="MANUAL_KILL">手动KILL</option>
                  <option value="SYSTEM_START">系统启动</option>
                  <option value="SYSTEM_STOP">系统停止</option>
                </select>
              </div>
              <div className="form-group">
                <label>来源</label>
                <select 
                  className="form-control"
                  value={filters.source}
                  onChange={(e) => handleFilterChange('source', e.target.value)}
                >
                  <option value="">全部</option>
                  <option value="SYSTEM">系统自动</option>
                  <option value="MANUAL">手动操作</option>
                  <option value="SANDBOX">沙箱演练</option>
                </select>
              </div>
              <div className="form-group">
                <label>事务类型</label>
                <select 
                  className="form-control"
                  value={filters.transaction_type}
                  onChange={(e) => handleFilterChange('transaction_type', e.target.value)}
                >
                  <option value="">全部</option>
                  <option value="READ">读事务</option>
                  <option value="WRITE">写事务</option>
                  <option value="DDL">DDL操作</option>
                </select>
              </div>
              <div className="form-group">
                <label>状态</label>
                <select 
                  className="form-control"
                  value={filters.success}
                  onChange={(e) => handleFilterChange('success', e.target.value)}
                >
                  <option value="">全部</option>
                  <option value="true">成功</option>
                  <option value="false">失败</option>
                </select>
              </div>
              <div className="form-group">
                <label>操作者</label>
                <input 
                  type="text"
                  className="form-control"
                  value={filters.operator}
                  onChange={(e) => handleFilterChange('operator', e.target.value)}
                  placeholder="输入操作者..."
                />
              </div>
            </div>
          </div>
        )}

        {logs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#6c757d' }}>
            <FileText size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>暂无审计日志</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>操作</th>
                <th>来源</th>
                <th>死锁ID</th>
                <th>事务ID</th>
                <th>事务类型</th>
                <th>操作者</th>
                <th>开销分数</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} style={{ cursor: 'pointer' }} onClick={() => handleViewDetail(log.id)}>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>
                    <span style={{ 
                      color: getActionColor(log.action),
                      fontWeight: 'bold'
                    }}>
                      {log.action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>
                    <span style={{ 
                      background: getSourceColor(log.source) + '20',
                      color: getSourceColor(log.source),
                      padding: '4px 8px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {log.source}
                    </span>
                  </td>
                  <td>
                    {log.deadlock_id ? (
                      <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {log.deadlock_id.substring(0, 12)}...
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    {log.transaction_id ? (
                      <span style={{ fontFamily: 'monospace' }}>#{log.transaction_id}</span>
                    ) : '-'}
                  </td>
                  <td>
                    {log.transaction_type ? (
                      <span style={{ 
                        color: getTransactionTypeColor(log.transaction_type),
                        fontWeight: 'bold'
                      }}>
                        {log.transaction_type}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    <span style={{ color: '#495057' }}>
                      <User size={14} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                      {log.operator || '-'}
                    </span>
                  </td>
                  <td>
                    {log.cost_score > 0 ? log.cost_score : '-'}
                  </td>
                  <td>
                    {log.success ? (
                      <CheckCircle size={18} color="#28a745" />
                    ) : (
                      <XCircle size={18} color="#dc3545" />
                    )}
                  </td>
                  <td>
                    <button 
                      className="btn"
                      onClick={(e) => { e.stopPropagation(); handleViewDetail(log.id) }}
                    >
                      <Eye size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && selectedLog && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="card-header">
              <h3>操作详情</h3>
              <button className="btn" onClick={() => setShowModal(false)}>关闭</button>
            </div>
            <div style={{ padding: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>操作类型</div>
                  <div style={{ fontWeight: 'bold', color: getActionColor(selectedLog.action) }}>
                    {selectedLog.action.replace(/_/g, ' ')}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>操作时间</div>
                  <div>{new Date(selectedLog.timestamp).toLocaleString()}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>来源</div>
                  <div>
                    <span style={{ 
                      background: getSourceColor(selectedLog.source) + '20',
                      color: getSourceColor(selectedLog.source),
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      {selectedLog.source}
                    </span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>状态</div>
                  <div>
                    {selectedLog.success ? (
                      <span style={{ color: '#28a745', fontWeight: 'bold' }}>
                        <CheckCircle size={16} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                        成功
                      </span>
                    ) : (
                      <span style={{ color: '#dc3545', fontWeight: 'bold' }}>
                        <XCircle size={16} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                        失败
                      </span>
                    )}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>操作者</div>
                  <div>{selectedLog.operator || '-'}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>KILL策略</div>
                  <div>{selectedLog.strategy || '-'}</div>
                </div>
              </div>

              {selectedLog.deadlock_id && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>死锁ID</div>
                  <div style={{ fontFamily: 'monospace', background: '#f8f9fa', padding: '8px 12px', borderRadius: '6px' }}>
                    {selectedLog.deadlock_id}
                  </div>
                </div>
              )}

              {selectedLog.transaction_id > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px' }}>事务信息</div>
                  <div style={{ 
                    padding: '16px', background: '#f8f9fa', borderRadius: '6px',
                    border: '1px solid #dee2e6'
                  }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>事务ID</div>
                        <div style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>#{selectedLog.transaction_id}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>事务类型</div>
                        <div style={{ fontWeight: 'bold', color: getTransactionTypeColor(selectedLog.transaction_type) }}>
                          {selectedLog.transaction_type || '-'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>用户</div>
                        <div>{selectedLog.user || '-'}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>开销分数</div>
                        <div style={{ fontWeight: 'bold' }}>{selectedLog.cost_score || 0}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>KILL优先级</div>
                        <div style={{ fontWeight: 'bold' }}>{selectedLog.kill_priority || 0}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d' }}>预估回滚时间</div>
                        <div style={{ fontWeight: 'bold' }}>{selectedLog.rollback_time || '-'}</div>
                      </div>
                    </div>
                    {selectedLog.transaction_info && (
                      <div>
                        <div style={{ fontSize: '11px', color: '#6c757d', marginBottom: '4px' }}>SQL语句</div>
                        <pre style={{ 
                          margin: 0, padding: '12px', background: '#fff', 
                          borderRadius: '4px', fontSize: '12px', overflow: 'auto'
                        }}>
                          {selectedLog.transaction_info}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {selectedLog.business_impact && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>业务影响评估</div>
                  <div style={{ 
                    padding: '12px', background: '#fff3cd', 
                    borderLeft: '4px solid #ffc107',
                    borderRadius: '0 6px 6px 0'
                  }}>
                    {selectedLog.business_impact}
                  </div>
                </div>
              )}

              {selectedLog.rule_applied && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>应用规则</div>
                  <div style={{ padding: '8px 12px', background: '#e3f2fd', borderRadius: '6px' }}>
                    {selectedLog.rule_applied}
                  </div>
                </div>
              )}

              {selectedLog.queries_affected && selectedLog.queries_affected.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px' }}>
                    受影响的查询 ({selectedLog.queries_affected.length})
                  </div>
                  {selectedLog.queries_affected.map((query, i) => (
                    <div key={i} style={{ 
                      marginBottom: '8px', padding: '8px 12px', 
                      background: '#f8f9fa', borderRadius: '6px',
                      fontSize: '12px', fontFamily: 'monospace'
                    }}>
                      {query}
                    </div>
                  ))}
                </div>
              )}

              {selectedLog.error_message && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>错误信息</div>
                  <div style={{ 
                    padding: '12px', background: '#f8d7da', 
                    color: '#721c24', borderRadius: '6px'
                  }}>
                    {selectedLog.error_message}
                  </div>
                </div>
              )}

              {selectedLog.client_ip && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>客户端IP</div>
                    <div style={{ fontFamily: 'monospace' }}>{selectedLog.client_ip}</div>
                  </div>
                  {selectedLog.user_agent && (
                    <div>
                      <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>User Agent</div>
                      <div style={{ fontSize: '12px', wordBreak: 'break-all' }}>{selectedLog.user_agent}</div>
                    </div>
                  )}
                </div>
              )}

              <div style={{ marginTop: '24px', textAlign: 'right' }}>
                <button className="btn" onClick={() => setShowModal(false)}>
                  关闭
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Audit
