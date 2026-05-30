import React, { useState, useEffect } from 'react'
import { getPreventionRecommendations, getPreventionStatistics, markRecommendationResolved } from '../api/client'
import { Lightbulb, AlertCircle, CheckCircle, Clock, TrendingUp, AlertTriangle } from 'lucide-react'

function Prevention() {
  const [recommendations, setRecommendations] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedRec, setSelectedRec] = useState(null)
  const [showModal, setShowModal] = useState(false)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [recRes, statsRes] = await Promise.all([
        getPreventionRecommendations(100),
        getPreventionStatistics()
      ])
      setRecommendations(recRes.data.data || [])
      setStatistics(statsRes.data.data || null)
    } catch (err) {
      console.error('Failed to load prevention data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkResolved = async (id) => {
    if (!confirm('确定标记此建议为已解决？')) return
    try {
      await markRecommendationResolved(id)
      loadData()
    } catch (err) {
      alert('标记失败: ' + err.message)
    }
  }

  const getPatternColor = (pattern) => {
    const colors = {
      'MISSING_INDEX': '#dc3545',
      'LONG_TRANSACTION': '#fd7e14',
      'TABLE_ORDER': '#6f42c1',
      'SELECT_FOR_UPDATE': '#17a2b8',
      'BATCH_OPERATION': '#e83e8c',
      'UNINDEXED_JOIN': '#ffc107'
    }
    return colors[pattern] || '#6c757d'
  }

  const getComplexityColor = (complexity) => {
    const colors = { 'LOW': '#28a745', 'MEDIUM': '#ffc107', 'HIGH': '#dc3545' }
    return colors[complexity] || '#6c757d'
  }

  const getSeverityColor = (severity) => {
    const colors = { 'LOW': '#28a745', 'MEDIUM': '#ffc107', 'HIGH': '#fd7e14', 'CRITICAL': '#dc3545' }
    return colors[severity] || '#6c757d'
  }

  if (loading) {
    return <div className="loading">加载中...</div>
  }

  const unresolvedRecs = recommendations.filter(r => !r.resolved)
  const resolvedRecs = recommendations.filter(r => r.resolved)

  return (
    <div>
      <div className="page-header">
        <h2>死锁预防建议</h2>
        <p>分析死锁SQL模式，提供优化建议</p>
      </div>

      {statistics && (
        <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(13, 110, 253, 0.1)' }}>
              <Lightbulb size={24} color="#0d6efd" />
            </div>
            <div>
              <div className="stat-value">{statistics.total_recommendations}</div>
              <div className="stat-label">总建议数</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(25, 135, 84, 0.1)' }}>
              <CheckCircle size={24} color="#198754" />
            </div>
            <div>
              <div className="stat-value">{statistics.resolved_count}</div>
              <div className="stat-label">已解决</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(220, 53, 69, 0.1)' }}>
              <AlertCircle size={24} color="#dc3545" />
            </div>
            <div>
              <div className="stat-value">{statistics.total_recommendations - statistics.resolved_count}</div>
              <div className="stat-label">待处理</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: 'rgba(13, 202, 240, 0.1)' }}>
              <Clock size={24} color="#0dcaf0" />
            </div>
            <div>
              <div className="stat-value">{statistics.avg_resolution_time || '-'}</div>
              <div className="stat-label">平均解决时间</div>
            </div>
          </div>
        </div>
      )}

      {statistics && statistics.pattern_distribution && statistics.pattern_distribution.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3>SQL模式分布</h3>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', padding: '20px' }}>
            {statistics.pattern_distribution.map((p, i) => (
              <div key={i} style={{ 
                flex: '1', minWidth: '200px', 
                padding: '16px', 
                borderRadius: '8px',
                border: `2px solid ${getSeverityColor(p.severity)}`,
                background: `${getSeverityColor(p.severity)}10`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <AlertTriangle size={16} color={getSeverityColor(p.severity)} />
                  <span style={{ fontWeight: 'bold' }}>{p.pattern.replace(/_/g, ' ')}</span>
                </div>
                <div style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '4px' }}>{p.count}</div>
                <div style={{ fontSize: '12px', color: '#6c757d' }}>{p.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>待处理建议 ({unresolvedRecs.length})</h3>
        </div>
        {unresolvedRecs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#6c757d' }}>
            <CheckCircle size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>暂无待处理的优化建议</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>优先级</th>
                <th>SQL模式</th>
                <th>相关表</th>
                <th>复杂度</th>
                <th>检测时间</th>
                <th>预期收益</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {unresolvedRecs.sort((a, b) => a.priority - b.priority).map(rec => (
                <tr key={rec.id} style={{ cursor: 'pointer' }} onClick={() => { setSelectedRec(rec); setShowModal(true) }}>
                  <td>
                    <span className="priority-badge" style={{ 
                      background: rec.priority === 1 ? '#dc3545' : rec.priority === 2 ? '#fd7e14' : '#ffc107',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      P{rec.priority}
                    </span>
                  </td>
                  <td>
                    <span style={{ 
                      color: getPatternColor(rec.sql_pattern),
                      fontWeight: 'bold'
                    }}>
                      {rec.sql_pattern.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>{rec.related_tables && rec.related_tables.join(', ')}</td>
                  <td>
                    <span style={{ color: getComplexityColor(rec.complexity), fontWeight: 'bold' }}>
                      {rec.complexity}
                    </span>
                  </td>
                  <td>{new Date(rec.detected_at).toLocaleString()}</td>
                  <td style={{ maxWidth: '200px', fontSize: '12px' }}>{rec.expected_benefit}</td>
                  <td>
                    <button className="btn btn-success" onClick={(e) => { e.stopPropagation(); handleMarkResolved(rec.id) }}>
                      标记解决
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {resolvedRecs.length > 0 && (
        <div className="card" style={{ marginTop: '24px' }}>
          <div className="card-header">
            <h3>已解决建议 ({resolvedRecs.length})</h3>
          </div>
          <table>
            <thead>
              <tr>
                <th>SQL模式</th>
                <th>相关表</th>
                <th>检测时间</th>
                <th>解决时间</th>
              </tr>
            </thead>
            <tbody>
              {resolvedRecs.slice(0, 10).map(rec => (
                <tr key={rec.id}>
                  <td style={{ color: getPatternColor(rec.sql_pattern) }}>{rec.sql_pattern.replace(/_/g, ' ')}</td>
                  <td>{rec.related_tables && rec.related_tables.join(', ')}</td>
                  <td>{new Date(rec.detected_at).toLocaleString()}</td>
                  <td>{rec.resolved_at ? new Date(rec.resolved_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && selectedRec && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="card-header">
              <h3>建议详情</h3>
              <button className="btn" onClick={() => setShowModal(false)}>关闭</button>
            </div>
            <div style={{ padding: '20px' }}>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>SQL模式</div>
                  <div style={{ fontWeight: 'bold', color: getPatternColor(selectedRec.sql_pattern) }}>
                    {selectedRec.sql_pattern.replace(/_/g, ' ')}
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>优先级</div>
                  <div>
                    <span className="priority-badge" style={{ 
                      background: selectedRec.priority === 1 ? '#dc3545' : selectedRec.priority === 2 ? '#fd7e14' : '#ffc107',
                      padding: '4px 12px', borderRadius: '12px', color: 'white', fontSize: '12px', fontWeight: 'bold'
                    }}>
                      P{selectedRec.priority}
                    </span>
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>修复复杂度</div>
                  <div style={{ fontWeight: 'bold', color: getComplexityColor(selectedRec.complexity) }}>
                    {selectedRec.complexity}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>模式描述</div>
                <div>{selectedRec.pattern_description}</div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>问题分析</div>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '6px' }}>
                  {selectedRec.problem_analysis}
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>相关SQL</div>
                <pre style={{ 
                  padding: '12px', background: '#f8f9fa', borderRadius: '6px',
                  overflow: 'auto', fontSize: '12px', margin: 0
                }}>
                  {selectedRec.sql_statement}
                </pre>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '8px' }}>优化建议</div>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {selectedRec.optimization_tips.map((tip, i) => (
                    <li key={i} style={{ marginBottom: '8px' }}>{tip}</li>
                  ))}
                </ul>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>预期收益</div>
                <div style={{ color: '#198754', fontWeight: 'bold' }}>
                  <TrendingUp size={16} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                  {selectedRec.expected_benefit}
                </div>
              </div>

              {selectedRec.related_tables && selectedRec.related_tables.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>相关表</div>
                  <div>
                    {selectedRec.related_tables.map((table, i) => (
                      <span key={i} style={{ 
                        display: 'inline-block',
                        padding: '4px 12px',
                        background: '#e3f2fd',
                        color: '#1976d2',
                        borderRadius: '12px',
                        fontSize: '12px',
                        marginRight: '8px',
                        marginBottom: '4px'
                      }}>
                        {table}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: '24px', textAlign: 'right' }}>
                <button className="btn" onClick={() => setShowModal(false)} style={{ marginRight: '12px' }}>
                  关闭
                </button>
                {!selectedRec.resolved && (
                  <button className="btn btn-success" onClick={() => {
                    handleMarkResolved(selectedRec.id)
                    setShowModal(false)
                  }}>
                    标记已解决
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Prevention
