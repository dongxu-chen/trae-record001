import { useState, useEffect } from 'react'
import axios from 'axios'

function QueryForm({ onSubmit, loading }) {
  const [userId, setUserId] = useState('user_001')
  const [query, setQuery] = useState('SELECT 1')
  const [priority, setPriority] = useState('medium')
  const [resourceGroup, setResourceGroup] = useState('default')
  const [complexity, setComplexity] = useState(null)

  const analyzeQuery = async () => {
    if (!query.trim()) {
      setComplexity(null)
      return
    }
    try {
      const res = await axios.post('/api/analyze', { query })
      setComplexity(res.data)
    } catch (err) {
      console.error('Failed to analyze query:', err)
      setComplexity(null)
    }
  }

  useEffect(() => {
    const timer = setTimeout(analyzeQuery, 800)
    return () => clearTimeout(timer)
  }, [query])

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ user_id: userId, query, priority, resource_group: resourceGroup })
  }

  const getRiskClass = (level) => {
    const classes = {
      'CRITICAL': 'risk-critical',
      'HIGH': 'risk-high',
      'MEDIUM': 'risk-medium',
      'LOW': 'risk-low'
    }
    return classes[level] || 'risk-low'
  }

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  const formatCost = (cost) => {
    if (!cost) return '0'
    if (cost >= 1000000) return (cost / 1000000).toFixed(2) + 'M'
    if (cost >= 1000) return (cost / 1000).toFixed(2) + 'K'
    return cost.toFixed(2)
  }

  const sampleQueries = [
    'SELECT 1',
    'SELECT count(*) FROM system.tables',
    'SELECT * FROM system.query_log LIMIT 100',
    'SELECT user_id, count(*) as cnt FROM events GROUP BY user_id ORDER BY cnt DESC LIMIT 10',
    'SELECT a.*, b.name FROM table_a a JOIN table_b b ON a.id = b.id WHERE a.date > today() - 7'
  ]

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
        <div className="form-group">
          <label>用户 ID</label>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="输入用户ID"
          />
        </div>
        <div className="form-group">
          <label>资源组</label>
          <select value={resourceGroup} onChange={(e) => setResourceGroup(e.target.value)}>
            <option value="default">📦 default - 默认组</option>
            <option value="data_team">🔬 data_team - 数据分析组</option>
            <option value="reporting">📊 reporting - 报表组</option>
            <option value="realtime">⚡ realtime - 实时组</option>
          </select>
        </div>
        <div className="form-group">
          <label>查询优先级</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="high">高优先级 (High) - 自动插队</option>
            <option value="medium">中优先级 (Medium)</option>
            <option value="low">低优先级 (Low)</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label>SQL 查询</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入 SQL 查询语句..."
          rows={6}
        />
      </div>

      <div style={{ marginBottom: '16px' }}>
        <span style={{ fontSize: '13px', color: '#666', marginRight: '8px' }}>示例查询：</span>
        {sampleQueries.map((q, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setQuery(q)}
            style={{
              padding: '4px 12px',
              margin: '0 4px 4px 0',
              fontSize: '12px',
              background: '#f0f2f5',
              border: '1px solid #e1e5eb',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            示例 {i + 1}
          </button>
        ))}
      </div>

      {complexity && (
        <div style={{
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '16px',
          border: '1px solid #e1e5eb'
        }}>
          <h4 style={{ marginBottom: '16px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📊</span> 查询复杂度分析 (基于执行计划 Cost)
          </h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '12px', marginBottom: '16px' }}>
            <div style={{ textAlign: 'center', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>风险等级</div>
              <span className={`complexity-badge ${getRiskClass(complexity.RiskLevel)}`}>
                {complexity.RiskLevel}
              </span>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Cost 估值</div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: '#667eea' }}>{formatCost(complexity.EstimatedCost)}</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>复杂度分数</div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: '#667eea' }}>{complexity.ComplexityScore?.toFixed(1)}</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>预估扫描行</div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: '#f59e0b' }}>{complexity.EstimatedRows?.toLocaleString()}</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', background: 'white', borderRadius: '6px', border: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>预估内存</div>
              <div style={{ fontSize: '20px', fontWeight: '700', color: '#8b5cf6' }}>{formatBytes(complexity.EstimatedMemory)}</div>
            </div>
          </div>

          {complexity.CostBreakdown && Object.keys(complexity.CostBreakdown).length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#555', marginBottom: '8px' }}>Cost 构成分析:</div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {Object.entries(complexity.CostBreakdown).map(([key, value]) => (
                  <div key={key} style={{
                    padding: '6px 12px',
                    background: '#eff6ff',
                    borderRadius: '20px',
                    fontSize: '12px',
                    color: '#1d4ed8'
                  }}>
                    {key}: {value.toFixed(1)}%
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#666', flexWrap: 'wrap', paddingTop: '12px', borderTop: '1px solid #e1e5eb' }}>
            {complexity.HasJoin && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>🔗 JOIN操作</span>}
            {complexity.HasGroupBy && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>📊 GROUP BY</span>}
            {complexity.HasOrderBy && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>↕️ ORDER BY</span>}
            {complexity.HasAggregation && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>📈 聚合函数</span>}
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>📋 {complexity.TableCount} 张表</span>
          </div>

          {complexity.PlanStages && complexity.PlanStages.length > 0 && (
            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#555', marginBottom: '8px' }}>执行计划阶段:</div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {complexity.PlanStages.map((stage, i) => (
                  <div key={i} style={{
                    padding: '6px 10px',
                    background: '#f0fdf4',
                    border: '1px solid #86efac',
                    borderRadius: '6px',
                    fontSize: '11px',
                    color: '#166534'
                  }}>
                    {stage.Name}
                    {stage.Rows > 0 && <span style={{ marginLeft: '4px', color: '#15803d' }}>({stage.Rows.toLocaleString()}行)</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {complexity.Prediction && (
            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e1e5eb' }}>
              <div style={{ fontSize: '13px', fontWeight: '500', color: '#555', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🔮</span> 资源消耗预测 (提交前预估)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '10px' }}>
                <div style={{ textAlign: 'center', padding: '10px', background: '#fef3c7', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#92400e', marginBottom: '4px' }}>CPU时间</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#b45309' }}>
                    {complexity.Prediction.EstimatedCPUTimeMs < 1 
                      ? complexity.Prediction.EstimatedCPUTimeMs.toFixed(2) + 'ms'
                      : complexity.Prediction.EstimatedCPUTimeMs < 1000
                        ? complexity.Prediction.EstimatedCPUTimeMs.toFixed(0) + 'ms'
                        : (complexity.Prediction.EstimatedCPUTimeMs / 1000).toFixed(1) + 's'}
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '10px', background: '#dbeafe', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#1e40af', marginBottom: '4px' }}>IO读取</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#1d4ed8' }}>
                    {complexity.Prediction.EstimatedIOMB < 1 
                      ? complexity.Prediction.EstimatedIOMB.toFixed(2) + 'MB'
                      : complexity.Prediction.EstimatedIOMB < 1024
                        ? complexity.Prediction.EstimatedIOMB.toFixed(1) + 'MB'
                        : (complexity.Prediction.EstimatedIOMB / 1024).toFixed(1) + 'GB'}
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '10px', background: '#dcfce7', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#166534', marginBottom: '4px' }}>网络传输</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#15803d' }}>
                    {complexity.Prediction.EstimatedNetworkMB < 1 
                      ? (complexity.Prediction.EstimatedNetworkMB * 1024).toFixed(0) + 'KB'
                      : complexity.Prediction.EstimatedNetworkMB < 1024
                        ? complexity.Prediction.EstimatedNetworkMB.toFixed(1) + 'MB'
                        : (complexity.Prediction.EstimatedNetworkMB / 1024).toFixed(1) + 'GB'}
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '10px', background: '#fce7f3', borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', color: '#9d174d', marginBottom: '4px' }}>预估耗时</div>
                  <div style={{ fontSize: '16px', fontWeight: '700', color: '#be185d' }}>
                    {complexity.Prediction.EstimatedDurationMs < 1000
                      ? complexity.Prediction.EstimatedDurationMs.toFixed(0) + 'ms'
                      : (complexity.Prediction.EstimatedDurationMs / 1000).toFixed(1) + 's'}
                  </div>
                </div>
                <div style={{ textAlign: 'center', padding: '10px', 
                  background: complexity.Prediction.ResourcePressure === 'EXTREME' ? '#fee2e2' :
                             complexity.Prediction.ResourcePressure === 'HIGH' ? '#fef3c7' :
                             complexity.Prediction.ResourcePressure === 'MEDIUM' ? '#dbeafe' : '#dcfce7',
                  borderRadius: '6px' }}>
                  <div style={{ fontSize: '11px', 
                    color: complexity.Prediction.ResourcePressure === 'EXTREME' ? '#991b1b' :
                           complexity.Prediction.ResourcePressure === 'HIGH' ? '#92400e' :
                           complexity.Prediction.ResourcePressure === 'MEDIUM' ? '#1e40af' : '#166534',
                    marginBottom: '4px' }}>资源压力</div>
                  <div style={{ fontSize: '16px', fontWeight: '700',
                    color: complexity.Prediction.ResourcePressure === 'EXTREME' ? '#b91c1c' :
                           complexity.Prediction.ResourcePressure === 'HIGH' ? '#b45309' :
                           complexity.Prediction.ResourcePressure === 'MEDIUM' ? '#1d4ed8' : '#15803d' }}>
                    {complexity.Prediction.ResourcePressure === 'EXTREME' ? '🔴 极高' :
                     complexity.Prediction.ResourcePressure === 'HIGH' ? '🟠 高' :
                     complexity.Prediction.ResourcePressure === 'MEDIUM' ? '🔵 中' : '🟢 低'}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#666' }}>
                <strong>并发影响：</strong>
                <div style={{ 
                  display: 'inline-block', 
                  marginLeft: '8px',
                  width: '150px',
                  height: '8px',
                  background: '#e5e7eb',
                  borderRadius: '4px',
                  overflow: 'hidden',
                  verticalAlign: 'middle'
                }}>
                  <div style={{
                    width: `${complexity.Prediction.ConcurrencyImpact * 100}%`,
                    height: '100%',
                    background: complexity.Prediction.ConcurrencyImpact > 0.7 ? '#ef4444' :
                               complexity.Prediction.ConcurrencyImpact > 0.4 ? '#f59e0b' : '#10b981',
                    borderRadius: '4px'
                  }}></div>
                </div>
                <span style={{ marginLeft: '8px', fontSize: '11px' }}>
                  {(complexity.Prediction.ConcurrencyImpact * 100).toFixed(0)}% 
                  {complexity.Prediction.ConcurrencyImpact > 0.7 ? ' - 高影响，建议避开高峰' :
                   complexity.Prediction.ConcurrencyImpact > 0.4 ? ' - 中等影响' : ' - 低影响'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      <button type="submit" className="btn btn-primary" disabled={loading}>
        {loading ? <span className="loading"></span> : '🚀'}
        {loading ? ' 执行中...' : ' 执行查询'}
      </button>
    </form>
  )
}

export default QueryForm
