import React, { useState, useEffect } from 'react'
import { getDeadlockHistory } from '../api/client'

function History() {
  const [history, setHistory] = useState([])
  const [selectedDeadlock, setSelectedDeadlock] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      const res = await getDeadlockHistory()
      setHistory(res.data.data || [])
    } catch (err) {
      console.error('Failed to load history:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>死锁历史</h2>
        <p>查看历史死锁记录和分析</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>历史记录 ({history.length})</h3>
        </div>
        {history.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
            暂无历史记录
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>死锁ID</th>
                <th>检测时间</th>
                <th>解决时间</th>
                <th>事务数</th>
                <th>解决方式</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {history.map(deadlock => (
                <tr key={deadlock.id}>
                  <td>{deadlock.id}</td>
                  <td>{new Date(deadlock.detected_at).toLocaleString()}</td>
                  <td>
                    {deadlock.resolved_at ? new Date(deadlock.resolved_at).toLocaleString() : '-'}
                  </td>
                  <td>{deadlock.transactions?.length || 0}</td>
                  <td>
                    <span className={`status-badge ${deadlock.resolution_type || 'pending'}`}>
                      {deadlock.resolution_type === 'auto' ? '自动' : 
                       deadlock.resolution_type === 'manual' ? '手动' : 
                       deadlock.resolution_type === 'resolved' ? '已解决' : '待处理'}
                    </span>
                  </td>
                  <td>
                    <button 
                      className="btn btn-primary"
                      onClick={() => setSelectedDeadlock(deadlock)}
                    >
                      详情
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
                <p><strong>检测时间:</strong> {new Date(selectedDeadlock.detected_at).toLocaleString()}</p>
                <p><strong>解决时间:</strong> {selectedDeadlock.resolved_at ? new Date(selectedDeadlock.resolved_at).toLocaleString() : '-'}</p>
              </div>
              <div>
                <p><strong>事务数:</strong> {selectedDeadlock.transactions?.length || 0}</p>
                <p><strong>解决方式:</strong> {selectedDeadlock.resolution_type || '-'}</p>
              </div>
            </div>
            <p style={{ marginTop: '12px' }}>
              <strong>等待图:</strong> {selectedDeadlock.wait_for_graph || '-'}
            </p>
          </div>

          {selectedDeadlock.impact_assessment && (
            <div className="deadlock-detail" style={{ marginTop: '16px' }}>
              <h4 style={{ marginBottom: '12px' }}>影响评估</h4>
              <div className="form-row">
                <div>
                  <p><strong>影响行数:</strong> {selectedDeadlock.impact_assessment.affected_rows}</p>
                  <p><strong>回滚时间:</strong> {selectedDeadlock.impact_assessment.rollback_time}</p>
                </div>
                <div>
                  <p><strong>业务影响:</strong> {selectedDeadlock.impact_assessment.business_impact}</p>
                  <p><strong>建议:</strong> {selectedDeadlock.impact_assessment.recommendation}</p>
                </div>
              </div>
            </div>
          )}

          <h4 style={{ marginTop: '20px', marginBottom: '12px' }}>涉及事务</h4>
          {selectedDeadlock.transactions?.map((trx, index) => (
            <div 
              key={index} 
              className={`transaction-item ${selectedDeadlock.victim_selected === trx.id ? 'victim' : ''}`}
            >
              <div className="transaction-header">
                <div>
                  <strong>事务 {index + 1}</strong> 
                  {selectedDeadlock.victim_selected === trx.id && (
                    <span className="status-badge manual" style={{ marginLeft: '12px' }}>
                      被KILL
                    </span>
                  )}
                </div>
                <span>ID: {trx.id || trx.trx_id}</span>
              </div>
              <div className="form-row">
                <div>
                  <p><strong>用户:</strong> {trx.user || '-'}</p>
                  <p><strong>数据库:</strong> {trx.db || '-'}</p>
                </div>
                <div>
                  <p><strong>状态:</strong> {trx.state || '-'}</p>
                  <p><strong>开始时间:</strong> {trx.start_time ? new Date(trx.start_time).toLocaleString() : '-'}</p>
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
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default History
