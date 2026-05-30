import React, { useState, useEffect } from 'react'
import { getCurrentDeadlocks, resolveDeadlock } from '../api/client'

function Deadlocks() {
  const [deadlocks, setDeadlocks] = useState([])
  const [selectedDeadlock, setSelectedDeadlock] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDeadlocks()
    const interval = setInterval(loadDeadlocks, 2000)
    return () => clearInterval(interval)
  }, [])

  const loadDeadlocks = async () => {
    try {
      const res = await getCurrentDeadlocks()
      setDeadlocks(res.data.data || [])
    } catch (err) {
      console.error('Failed to load deadlocks:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleResolve = async (deadlockId, transactionId) => {
    if (!confirm('确定要KILL此事务吗？这将回滚该事务的所有操作。')) {
      return
    }

    try {
      await resolveDeadlock(deadlockId, transactionId)
      alert('死锁已解除')
      loadDeadlocks()
      setSelectedDeadlock(null)
    } catch (err) {
      alert('解除死锁失败: ' + err.message)
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return '#ff4d4f'
      case 'HIGH': return '#fa8c16'
      case 'MEDIUM': return '#faad14'
      case 'LOW': return '#52c41a'
      default: return '#666'
    }
  }

  const getTransactionTypeColor = (type) => {
    switch (type) {
      case 'READ': return '#52c41a'
      case 'WRITE': return '#1890ff'
      case 'DDL': return '#ff4d4f'
      default: return '#666'
    }
  }

  const getPriorityColor = (priority) => {
    if (priority >= 150) return '#52c41a'
    if (priority >= 100) return '#1890ff'
    if (priority >= 50) return '#faad14'
    return '#ff4d4f'
  }

  if (loading) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>当前死锁</h2>
        <p>查看和处理当前检测到的死锁（每2秒自动刷新）</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>死锁列表 ({deadlocks.length})</h3>
        </div>
        {deadlocks.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            🎉 暂无死锁检测到，数据库运行正常
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>死锁ID</th>
                <th>检测时间</th>
                <th>严重等级</th>
                <th>事务数</th>
                <th>检测延迟</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {deadlocks.map(deadlock => (
                <tr key={deadlock.id}>
                  <td>{deadlock.id}</td>
                  <td>{new Date(deadlock.detected_at).toLocaleString()}</td>
                  <td>
                    <span style={{ 
                      color: getSeverityColor(deadlock.severity),
                      fontWeight: 'bold'
                    }}>
                      {deadlock.severity || 'UNKNOWN'}
                    </span>
                  </td>
                  <td>{deadlock.transactions?.length || 0}</td>
                  <td>{deadlock.detection_latency_ms}ms</td>
                  <td>
                    <span className={`status-badge ${deadlock.resolution_type || 'pending'}`}>
                      {deadlock.resolution_type || '待处理'}
                    </span>
                  </td>
                  <td>
                    <button 
                      className="btn btn-primary"
                      onClick={() => setSelectedDeadlock(deadlock)}
                    >
                      查看详情
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selectedDeadlock && (
        <div className="card">
          <div className="card-header">
            <h3>死锁详情 - {selectedDeadlock.id}</h3>
            <button 
              className="btn"
              onClick={() => setSelectedDeadlock(null)}
            >
              关闭
            </button>
          </div>

          <div className="deadlock-detail">
            <div className="form-row">
              <div>
                <p><strong>严重等级:</strong> 
                  <span style={{ 
                    color: getSeverityColor(selectedDeadlock.severity),
                    fontWeight: 'bold',
                    marginLeft: '8px'
                  }}>
                    {selectedDeadlock.severity || 'UNKNOWN'}
                  </span>
                </p>
                <p><strong>检测时间:</strong> {new Date(selectedDeadlock.detected_at).toLocaleString()}</p>
              </div>
              <div>
                <p><strong>检测延迟:</strong> {selectedDeadlock.detection_latency_ms}ms</p>
                <p><strong>检测来源:</strong> {selectedDeadlock.source || 'polling'}</p>
              </div>
            </div>
          </div>

          {selectedDeadlock.impact_assessment && (
            <div className="deadlock-detail" style={{ marginTop: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>影响评估</h4>
              <div className="form-row">
                <div>
                  <p><strong>事务类型:</strong> 
                    <span style={{ 
                      color: getTransactionTypeColor(selectedDeadlock.impact_assessment.transaction_type),
                      fontWeight: 'bold',
                      marginLeft: '8px'
                    }}>
                      {selectedDeadlock.impact_assessment.transaction_type || 'UNKNOWN'}
                    </span>
                  </p>
                  <p><strong>影响行数:</strong> {selectedDeadlock.impact_assessment.affected_rows}</p>
                  <p><strong>开销分数:</strong> {selectedDeadlock.impact_assessment.cost_score}</p>
                  <p><strong>回滚时间:</strong> {selectedDeadlock.impact_assessment.rollback_time}</p>
                </div>
                <div>
                  <p><strong>业务影响:</strong> 
                    <span style={{ 
                      color: selectedDeadlock.impact_assessment.business_impact === 'CRITICAL' ? 'red' :
                             selectedDeadlock.impact_assessment.business_impact === 'HIGH' ? 'orange' :
                             selectedDeadlock.impact_assessment.business_impact === 'MEDIUM' ? '#faad14' : 'green',
                      fontWeight: 'bold'
                    }}>
                      {selectedDeadlock.impact_assessment.business_impact}
                    </span>
                  </p>
                  <p><strong>建议:</strong> {selectedDeadlock.impact_assessment.recommendation}</p>
                </div>
              </div>
            </div>
          )}

          <h4 style={{ marginTop: '20px', marginBottom: '12px' }}>涉及事务 (按KILL优先级排序)</h4>
          {selectedDeadlock.transactions?.sort((a, b) => (b.kill_priority || 0) - (a.kill_priority || 0)).map((trx, index) => (
            <div 
              key={index} 
              className={`transaction-item ${selectedDeadlock.victim_selected === trx.id ? 'victim' : ''}`}
            >
              <div className="transaction-header">
                <div>
                  <strong>事务 {index + 1}</strong> 
                  {selectedDeadlock.victim_selected === trx.id && (
                    <span className="status-badge manual" style={{ marginLeft: '12px' }}>
                      建议KILL
                    </span>
                  )}
                  <span style={{ 
                    color: getTransactionTypeColor(trx.transaction_type),
                    marginLeft: '12px',
                    fontSize: '12px'
                  }}>
                    [{trx.transaction_type || 'UNKNOWN'}]
                  </span>
                </div>
                <div>
                  <span style={{ marginRight: '16px' }}>
                    KILL优先级: <span style={{ color: getPriorityColor(trx.kill_priority), fontWeight: 'bold' }}>{trx.kill_priority || 0}</span>
                  </span>
                  <span>开销分数: {trx.cost_score || 0}</span>
                </div>
              </div>
              <div className="form-row">
                <div>
                  <p><strong>用户:</strong> {trx.user || '-'}</p>
                  <p><strong>数据库:</strong> {trx.db || '-'}</p>
                  <p><strong>修改行数:</strong> {trx.rows_modified || 0}</p>
                  <p><strong>锁定行数:</strong> {trx.rows_locked || 0}</p>
                </div>
                <div>
                  <p><strong>状态:</strong> {trx.state || '-'}</p>
                  <p><strong>开始时间:</strong> {trx.start_time ? new Date(trx.start_time).toLocaleString() : '-'}</p>
                  <p><strong>锁内存:</strong> {(trx.lock_memory_bytes || 0) / 1024}KB</p>
                  <p><strong>等待锁:</strong> {trx.wait_lock_id || '-'}</p>
                </div>
              </div>
              {trx.info && (
                <div style={{ marginTop: '12px' }}>
                  <strong>SQL语句:</strong>
                  <pre style={{ 
                    background: '#f5f5f5', 
                    padding: '12px', 
                    borderRadius: '4px',
                    marginTop: '8px',
                    overflowX: 'auto'
                  }}>
                    {trx.info}
                  </pre>
                </div>
              )}
              {selectedDeadlock.victim_selected === trx.id && selectedDeadlock.resolution_type !== 'auto' && (
                <div style={{ marginTop: '12px', textAlign: 'right' }}>
                  <button 
                    className="btn btn-danger"
                    onClick={() => handleResolve(selectedDeadlock.id, trx.id)}
                  >
                    KILL 事务
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Deadlocks
