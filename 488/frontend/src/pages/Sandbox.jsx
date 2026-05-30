import React, { useState, useEffect } from 'react'
import { 
  getSandboxScenarios, getSimulationResults, runSimulation, 
  getSimulationResult, getSimulationStatus, createSandboxScenario,
  deleteSandboxScenario, getSandboxScenario
} from '../api/client'
import { FlaskConical, Play, Clock, CheckCircle, XCircle, Plus, Trash2, Eye, Settings } from 'lucide-react'

function Sandbox() {
  const [scenarios, setScenarios] = useState([])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('scenarios')
  const [selectedScenario, setSelectedScenario] = useState(null)
  const [selectedResult, setSelectedResult] = useState(null)
  const [showRunModal, setShowRunModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showResultModal, setShowResultModal] = useState(false)
  const [killStrategy, setKillStrategy] = useState('priority')
  const [runningSimulations, setRunningSimulations] = useState({})
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'ROW_LOCK',
    db_type: 'MySQL',
    setup_sql: '',
    deadlock_sql: '',
    expected_result: '',
    difficulty: 'MEDIUM',
    tags: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      checkRunningSimulations()
    }, 1000)
    return () => clearInterval(interval)
  }, [runningSimulations])

  const loadData = async () => {
    try {
      const [scenRes, resRes] = await Promise.all([
        getSandboxScenarios(),
        getSimulationResults(50)
      ])
      setScenarios(scenRes.data.data || [])
      setResults(resRes.data.data || [])
    } catch (err) {
      console.error('Failed to load sandbox data:', err)
    } finally {
      setLoading(false)
    }
  }

  const checkRunningSimulations = async () => {
    const simIds = Object.keys(runningSimulations)
    if (simIds.length === 0) return

    for (const simId of simIds) {
      try {
        const res = await getSimulationStatus(simId)
        if (res.data.status !== 'RUNNING') {
          const result = await getSimulationResult(simId)
          setResults(prev => {
            const idx = prev.findIndex(r => r.id === simId)
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = result.data.data
              return updated
            }
            return [result.data.data, ...prev]
          })
          setRunningSimulations(prev => {
            const updated = { ...prev }
            delete updated[simId]
            return updated
          })
        }
      } catch (err) {
        console.error('Error checking simulation status:', err)
      }
    }
  }

  const handleRunSimulation = async () => {
    if (!selectedScenario) return
    
    try {
      const res = await runSimulation(selectedScenario.id, killStrategy)
      const newResult = res.data.data
      setResults(prev => [newResult, ...prev])
      setRunningSimulations(prev => ({ ...prev, [newResult.id]: true }))
      setShowRunModal(false)
      setActiveTab('results')
    } catch (err) {
      alert('启动模拟失败: ' + err.message)
    }
  }

  const handleCreateScenario = async (e) => {
    e.preventDefault()
    try {
      const scenarioData = {
        ...formData,
        setup_sql: formData.setup_sql.split('\n').filter(s => s.trim()),
        deadlock_sql: formData.deadlock_sql.split('\n').filter(s => s.trim()),
        tags: formData.tags ? formData.tags.split(',').map(s => s.trim()).filter(Boolean) : []
      }
      await createSandboxScenario(scenarioData)
      await loadData()
      setShowCreateModal(false)
      setFormData({
        name: '', description: '', type: 'ROW_LOCK',
        db_type: 'MySQL', setup_sql: '', deadlock_sql: '',
        expected_result: '', difficulty: 'MEDIUM', tags: ''
      })
    } catch (err) {
      alert('创建场景失败: ' + err.message)
    }
  }

  const handleDeleteScenario = async (id) => {
    if (!confirm('确定删除此场景？')) return
    try {
      await deleteSandboxScenario(id)
      await loadData()
    } catch (err) {
      alert('删除失败: ' + err.message)
    }
  }

  const getDifficultyColor = (difficulty) => {
    const colors = { 'EASY': '#28a745', 'MEDIUM': '#ffc107', 'HARD': '#dc3545' }
    return colors[difficulty] || '#6c757d'
  }

  const getStatusColor = (status) => {
    const colors = { 
      'COMPLETED': '#28a745', 'RUNNING': '#0d6efd', 
      'FAILED': '#dc3545', 'TIMEOUT': '#fd7e14' 
    }
    return colors[status] || '#6c757d'
  }

  const getTypeColor = (type) => {
    const colors = {
      'ROW_LOCK': '#0d6efd', 'GAP_LOCK': '#6610f2',
      'SELECT_FOR_UPDATE': '#17a2b8', 'DDL_MIX': '#dc3545',
      'MULTI_WAY': '#fd7e14'
    }
    return colors[type] || '#6c757d'
  }

  if (loading) {
    return <div className="loading">加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>死锁演练沙箱</h2>
        <p>模拟死锁场景，测试解除策略效果</p>
      </div>

      <div className="tabs" style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        <button 
          className={`tab-btn ${activeTab === 'scenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('scenarios')}
          style={{
            padding: '10px 20px',
            border: 'none',
            background: activeTab === 'scenarios' ? '#0d6efd' : '#e9ecef',
            color: activeTab === 'scenarios' ? 'white' : '#495057',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          演练场景
        </button>
        <button 
          className={`tab-btn ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
          style={{
            padding: '10px 20px',
            border: 'none',
            background: activeTab === 'results' ? '#0d6efd' : '#e9ecef',
            color: activeTab === 'results' ? 'white' : '#495057',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 'bold'
          }}
        >
          模拟结果
        </button>
      </div>

      {activeTab === 'scenarios' && (
        <div>
          <div className="card">
            <div className="card-header">
              <h3>可用场景</h3>
              <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                <Plus size={16} style={{ marginRight: '6px', verticalAlign: 'text-bottom' }} />
                新建场景
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '16px', padding: '20px' }}>
              {scenarios.map(scenario => (
                <div key={scenario.id} className="card" style={{ margin: 0, border: `2px solid ${getTypeColor(scenario.type)}30` }}>
                  <div className="card-header" style={{ borderBottom: `3px solid ${getTypeColor(scenario.type)}` }}>
                    <h4 style={{ margin: 0 }}>{scenario.name}</h4>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <span style={{ 
                        background: getDifficultyColor(scenario.difficulty) + '20',
                        color: getDifficultyColor(scenario.difficulty),
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {scenario.difficulty}
                      </span>
                      <span style={{ 
                        background: getTypeColor(scenario.type) + '20',
                        color: getTypeColor(scenario.type),
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {scenario.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                  <div style={{ padding: '16px' }}>
                    <p style={{ color: '#6c757d', fontSize: '14px', marginBottom: '12px' }}>
                      {scenario.description}
                    </p>
                    <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '12px' }}>
                      <div>预期结果: {scenario.expected_result}</div>
                    </div>
                    {scenario.tags && scenario.tags.length > 0 && (
                      <div style={{ marginBottom: '12px' }}>
                        {scenario.tags.map((tag, i) => (
                          <span key={i} style={{ 
                            display: 'inline-block',
                            padding: '2px 8px',
                            background: '#e9ecef',
                            borderRadius: '12px',
                            fontSize: '11px',
                            marginRight: '6px',
                            marginBottom: '4px'
                          }}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        className="btn btn-primary"
                        onClick={() => { setSelectedScenario(scenario); setShowRunModal(true) }}
                      >
                        <Play size={14} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                        运行
                      </button>
                      <button 
                        className="btn"
                        onClick={() => { setSelectedScenario(scenario); setShowResultModal(true); setSelectedResult(null) }}
                      >
                        <Eye size={14} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                        查看SQL
                      </button>
                      <button 
                        className="btn btn-danger"
                        onClick={() => handleDeleteScenario(scenario.id)}
                      >
                        <Trash2 size={14} style={{ marginRight: '4px', verticalAlign: 'text-bottom' }} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'results' && (
        <div className="card">
          <div className="card-header">
            <h3>模拟结果</h3>
          </div>
          {results.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: '#6c757d' }}>
              <FlaskConical size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
              <p>暂无模拟结果，请先运行演练场景</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>场景</th>
                  <th>KILL策略</th>
                  <th>状态</th>
                  <th>死锁检测</th>
                  <th>被KILL事务</th>
                  <th>解决时间</th>
                  <th>开始时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {results.map(result => (
                  <tr key={result.id}>
                    <td>
                      <span style={{ fontWeight: 'bold' }}>{result.scenario_name}</span>
                    </td>
                    <td>
                      <span style={{ 
                        background: '#e3f2fd',
                        color: '#1976d2',
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '12px'
                      }}>
                        {result.kill_strategy}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${
                        result.status === 'COMPLETED' ? 'resolved' : 
                        result.status === 'RUNNING' ? 'pending' : 'blocked'
                      }`}>
                        {result.status}
                      </span>
                    </td>
                    <td>
                      {result.deadlock_detected ? (
                        <CheckCircle size={18} color="#28a745" />
                      ) : (
                        <XCircle size={18} color="#dc3545" />
                      )}
                    </td>
                    <td>
                      {result.victim_killed ? (
                        <span style={{ color: '#dc3545', fontFamily: 'monospace' }}>
                          #{result.victim_killed}
                        </span>
                      ) : '-'}
                    </td>
                    <td>
                      {result.resolution_time_ms ? `${result.resolution_time_ms}ms` : '-'}
                    </td>
                    <td>{new Date(result.started_at).toLocaleString()}</td>
                    <td>
                      <button 
                        className="btn"
                        onClick={() => { setSelectedResult(result); setShowResultModal(true); setSelectedScenario(null) }}
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
      )}

      {showRunModal && selectedScenario && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: '500px' }}>
            <div className="card-header">
              <h3>运行模拟</h3>
              <button className="btn" onClick={() => setShowRunModal(false)}>关闭</button>
            </div>
            <div style={{ padding: '20px' }}>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>场景</div>
                <div>{selectedScenario.name}</div>
              </div>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  {selectedScenario.description}
                </div>
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                  <Settings size={16} style={{ marginRight: '6px', verticalAlign: 'text-bottom' }} />
                  KILL策略
                </label>
                <select 
                  className="form-control"
                  value={killStrategy}
                  onChange={(e) => setKillStrategy(e.target.value)}
                >
                  <option value="priority">优先级优先</option>
                  <option value="lowest_cost">最低开销优先</option>
                  <option value="youngest">最新事务优先</option>
                  <option value="oldest">最早事务优先</option>
                  <option value="least_work">最少工作优先</option>
                </select>
              </div>
              <div style={{ textAlign: 'right' }}>
                <button className="btn" onClick={() => setShowRunModal(false)} style={{ marginRight: '12px' }}>
                  取消
                </button>
                <button className="btn btn-primary" onClick={handleRunSimulation}>
                  <Play size={16} style={{ marginRight: '6px', verticalAlign: 'text-bottom' }} />
                  开始模拟
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showCreateModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: '600px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="card-header">
              <h3>新建演练场景</h3>
              <button className="btn" onClick={() => setShowCreateModal(false)}>关闭</button>
            </div>
            <form onSubmit={handleCreateScenario} style={{ padding: '20px' }}>
              <div className="form-group">
                <label>场景名称</label>
                <input 
                  type="text" 
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>描述</label>
                <textarea 
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows="2"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>死锁类型</label>
                  <select 
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  >
                    <option value="ROW_LOCK">行锁死锁</option>
                    <option value="GAP_LOCK">Gap Lock死锁</option>
                    <option value="SELECT_FOR_UPDATE">SELECT FOR UPDATE</option>
                    <option value="DDL_MIX">DDL与DML混合</option>
                    <option value="MULTI_WAY">多路死锁</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>难度</label>
                  <select 
                    value={formData.difficulty}
                    onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                  >
                    <option value="EASY">简单</option>
                    <option value="MEDIUM">中等</option>
                    <option value="HARD">困难</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>初始化SQL（每行一条）</label>
                <textarea 
                  value={formData.setup_sql}
                  onChange={(e) => setFormData({ ...formData, setup_sql: e.target.value })}
                  rows="4"
                  placeholder="CREATE TABLE ...&#10;INSERT INTO ..."
                />
              </div>
              <div className="form-group">
                <label>死锁SQL（每行一条，包含多个事务）</label>
                <textarea 
                  value={formData.deadlock_sql}
                  onChange={(e) => setFormData({ ...formData, deadlock_sql: e.target.value })}
                  rows="8"
                  placeholder="-- 事务1&#10;START TRANSACTION&#10;UPDATE ...&#10;-- 事务2&#10;START TRANSACTION&#10;UPDATE ..."
                />
              </div>
              <div className="form-group">
                <label>预期结果</label>
                <input 
                  type="text"
                  value={formData.expected_result}
                  onChange={(e) => setFormData({ ...formData, expected_result: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>标签（逗号分隔）</label>
                <input 
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="row-lock, ordering, classic"
                />
              </div>
              <div style={{ marginTop: '20px', textAlign: 'right' }}>
                <button type="button" className="btn" onClick={() => setShowCreateModal(false)} style={{ marginRight: '12px' }}>
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showResultModal && (selectedResult || selectedScenario) && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="card" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="card-header">
              <h3>{selectedResult ? '模拟结果详情' : '场景SQL详情'}</h3>
              <button className="btn" onClick={() => setShowResultModal(false)}>关闭</button>
            </div>
            <div style={{ padding: '20px' }}>
              {selectedScenario && (
                <div>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>初始化SQL</div>
                    <pre style={{ 
                      padding: '12px', background: '#f8f9fa', borderRadius: '6px',
                      fontSize: '12px', overflow: 'auto'
                    }}>
                      {selectedScenario.setup_sql && selectedScenario.setup_sql.join('\n')}
                    </pre>
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>死锁SQL</div>
                    <pre style={{ 
                      padding: '12px', background: '#f8f9fa', borderRadius: '6px',
                      fontSize: '12px', overflow: 'auto'
                    }}>
                      {selectedScenario.deadlock_sql && selectedScenario.deadlock_sql.join('\n')}
                    </pre>
                  </div>
                </div>
              )}
              
              {selectedResult && (
                <div>
                  <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '12px', color: '#6c757d' }}>场景</div>
                      <div style={{ fontWeight: 'bold' }}>{selectedResult.scenario_name}</div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '12px', color: '#6c757d' }}>状态</div>
                      <div style={{ color: getStatusColor(selectedResult.status), fontWeight: 'bold' }}>
                        {selectedResult.status}
                      </div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '12px', color: '#6c757d' }}>解决时间</div>
                      <div style={{ fontWeight: 'bold' }}>
                        {selectedResult.resolution_time_ms ? `${selectedResult.resolution_time_ms}ms` : '-'}
                      </div>
                    </div>
                  </div>
                  
                  {selectedResult.rule_applied && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontSize: '12px', color: '#6c757d' }}>应用规则</div>
                      <div style={{ 
                        padding: '8px 12px', background: '#fff3cd', borderRadius: '6px'
                      }}>
                        {selectedResult.rule_applied}
                      </div>
                    </div>
                  )}
                  
                  {selectedResult.transactions && selectedResult.transactions.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>事务详情</div>
                      {selectedResult.transactions.map((tx, i) => (
                        <div key={i} style={{ 
                          padding: '12px', 
                          background: tx.id === selectedResult.victim_killed ? '#f8d7da' : '#f8f9fa',
                          borderRadius: '6px',
                          marginBottom: '8px',
                          border: tx.id === selectedResult.victim_killed ? '1px solid #dc3545' : 'none'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <span style={{ fontFamily: 'monospace' }}>事务 #{tx.id}</span>
                            {tx.id === selectedResult.victim_killed && (
                              <span style={{ color: '#dc3545', fontWeight: 'bold', fontSize: '12px' }}>
                                被KILL
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                            <span style={{ color: '#6c757d' }}>类型:</span> {tx.transaction_type} | 
                            <span style={{ color: '#6c757d', marginLeft: '8px' }}>优先级:</span> {tx.kill_priority} |
                            <span style={{ color: '#6c757d', marginLeft: '8px' }}>开销:</span> {tx.cost_score}
                          </div>
                          <pre style={{ 
                            margin: 0, fontSize: '11px', background: '#fff', 
                            padding: '8px', borderRadius: '4px', overflow: 'auto'
                          }}>
                            {tx.info}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {selectedResult.error_message && (
                    <div style={{ 
                      padding: '12px', background: '#f8d7da', color: '#721c24',
                      borderRadius: '6px'
                    }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>错误</div>
                      {selectedResult.error_message}
                    </div>
                  )}
                </div>
              )}
              
              <div style={{ marginTop: '20px', textAlign: 'right' }}>
                <button className="btn" onClick={() => setShowResultModal(false)}>
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

export default Sandbox
