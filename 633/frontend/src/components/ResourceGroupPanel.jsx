import { useState, useEffect } from 'react'
import axios from 'axios'

function ResourceGroupPanel({ status }) {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newGroup, setNewGroup] = useState({
    name: '',
    weight: 100,
    max_concurrency: 10,
    max_queue_size: 1000,
    global_rate: 10,
    max_scan_rows: 100000000,
    max_memory: 1073741824
  })

  const fetchGroups = async () => {
    try {
      const res = await axios.get('/api/resource-groups')
      setGroups(res.data)
    } catch (err) {
      console.error('Failed to fetch resource groups:', err)
    }
  }

  useEffect(() => {
    fetchGroups()
    const interval = setInterval(fetchGroups, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleAddGroup = async () => {
    if (!newGroup.name) return
    setLoading(true)
    try {
      const groupData = {
        name: newGroup.name,
        weight: parseInt(newGroup.weight),
        max_concurrency: parseInt(newGroup.max_concurrency),
        max_queue_size: parseInt(newGroup.max_queue_size),
        limiter: {
          global_rate: parseFloat(newGroup.global_rate),
          global_burst: parseInt(newGroup.global_rate) * 2,
          user_rate: parseFloat(newGroup.global_rate) / 2,
          user_burst: parseInt(newGroup.global_rate),
          max_scan_rows: parseInt(newGroup.max_scan_rows),
          max_memory_bytes: parseInt(newGroup.max_memory),
          query_timeout: 60000000000,
          circuit_breaker: {
            failure_threshold: 0.5,
            success_threshold: 3,
            timeout: 30000000000
          }
        }
      }
      await axios.post('/api/resource-groups', groupData)
      setShowAddForm(false)
      setNewGroup({
        name: '',
        weight: 100,
        max_concurrency: 10,
        max_queue_size: 1000,
        global_rate: 10,
        max_scan_rows: 100000000,
        max_memory: 1073741824
      })
      fetchGroups()
    } catch (err) {
      console.error('Failed to add resource group:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteGroup = async (name) => {
    if (name === 'default') return
    if (!confirm(`确定要删除资源组 "${name}" 吗？`)) return
    try {
      await axios.delete(`/api/resource-groups/${name}`)
      fetchGroups()
    } catch (err) {
      console.error('Failed to delete resource group:', err)
    }
  }

  const getGroupColor = (name) => {
    const colors = {
      'default': 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)',
      'data_team': 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)',
      'reporting': 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
      'realtime': 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
    }
    return colors[name] || 'linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)'
  }

  const getGroupTextColor = (name) => {
    const colors = {
      'default': '#3730a3',
      'data_team': '#be185d',
      'reporting': '#b45309',
      'realtime': '#15803d',
    }
    return colors[name] || '#374151'
  }

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  return (
    <div>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <p style={{ color: '#666', fontSize: '14px' }}>
            不同业务组资源隔离，独立配额、独立限流、独立熔断
          </p>
        </div>
        <button 
          className="btn btn-primary"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          {showAddForm ? '取消' : '+ 新增资源组'}
        </button>
      </div>

      {showAddForm && (
        <div style={{
          background: '#f8fafc',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '24px',
          border: '1px solid #e1e5eb'
        }}>
          <h4 style={{ marginBottom: '16px', fontSize: '15px' }}>新增资源组</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label>资源组名称</label>
              <input
                type="text"
                value={newGroup.name}
                onChange={(e) => setNewGroup({...newGroup, name: e.target.value})}
                placeholder="如: data_team"
              />
            </div>
            <div className="form-group">
              <label>权重</label>
              <input
                type="number"
                value={newGroup.weight}
                onChange={(e) => setNewGroup({...newGroup, weight: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>最大并发数</label>
              <input
                type="number"
                value={newGroup.max_concurrency}
                onChange={(e) => setNewGroup({...newGroup, max_concurrency: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>全局限流 (QPS)</label>
              <input
                type="number"
                value={newGroup.global_rate}
                onChange={(e) => setNewGroup({...newGroup, global_rate: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>最大扫描行数</label>
              <input
                type="number"
                value={newGroup.max_scan_rows}
                onChange={(e) => setNewGroup({...newGroup, max_scan_rows: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>最大内存 (字节)</label>
              <input
                type="number"
                value={newGroup.max_memory}
                onChange={(e) => setNewGroup({...newGroup, max_memory: e.target.value})}
              />
            </div>
          </div>
          <button 
            className="btn btn-primary" 
            onClick={handleAddGroup}
            disabled={loading || !newGroup.name}
            style={{ marginTop: '12px' }}
          >
            {loading ? '添加中...' : '添加资源组'}
          </button>
        </div>
      )}

      <div style={{ display: 'grid', gap: '16px' }}>
        {groups.map((group) => (
          <div key={group.name} style={{
            background: getGroupColor(group.name),
            padding: '20px',
            borderRadius: '8px',
            border: '1px solid #e1e5eb'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h3 style={{ margin: 0, color: getGroupTextColor(group.name), fontSize: '18px' }}>
                  {group.name === 'default' ? '📦 默认组' : 
                   group.name === 'data_team' ? '🔬 数据分析组' :
                   group.name === 'reporting' ? '📊 报表组' :
                   group.name === 'realtime' ? '⚡ 实时组' : `👥 ${group.name}`}
                </h3>
                <p style={{ margin: '4px 0 0 0', color: '#666', fontSize: '13px' }}>
                  权重: {group.weight} | 最大并发: {group.max_concurrency}
                </p>
              </div>
              {group.name !== 'default' && (
                <button 
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDeleteGroup(group.name)}
                >
                  删除
                </button>
              )}
            </div>

            <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', marginBottom: '16px' }}>
              <div className="metric-card" style={{ background: 'rgba(255,255,255,0.7)' }}>
                <div className="value" style={{ color: getGroupTextColor(group.name) }}>{group.active_queries}</div>
                <div className="label">运行中查询</div>
              </div>
              <div className="metric-card" style={{ background: 'rgba(255,255,255,0.7)' }}>
                <div className="value" style={{ color: getGroupTextColor(group.name) }}>{group.queued_queries}</div>
                <div className="label">排队中</div>
              </div>
              <div className="metric-card" style={{ background: 'rgba(255,255,255,0.7)' }}>
                <div className="value" style={{ color: getGroupTextColor(group.name) }}>{group.total_queries}</div>
                <div className="label">总查询数</div>
              </div>
              <div className="metric-card" style={{ background: 'rgba(255,255,255,0.7)' }}>
                <div className="value" style={{ color: getGroupTextColor(group.name) }}>{group.rejected_queries}</div>
                <div className="label">被拒绝数</div>
              </div>
              <div className="metric-card" style={{ background: 'rgba(255,255,255,0.7)' }}>
                <div className="value" style={{ 
                  color: group.circuit_breaker?.state === 'open' ? '#dc2626' : 
                         group.circuit_breaker?.state === 'half_open' ? '#f59e0b' : '#16a34a' 
                }}>
                  {group.circuit_breaker?.state === 'open' ? '已熔断' : 
                   group.circuit_breaker?.state === 'half_open' ? '恢复中' : '正常'}
                </div>
                <div className="label">熔断器</div>
              </div>
            </div>

            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(3, 1fr)', 
              gap: '12px',
              fontSize: '12px',
              color: '#555'
            }}>
              <div>
                <strong>限流速率：</strong>{group.limiter_config?.global_rate}/秒
              </div>
              <div>
                <strong>最大扫描：</strong>{(group.limiter_config?.max_scan_rows / 1000000).toFixed(0)}M行
              </div>
              <div>
                <strong>最大内存：</strong>{formatBytes(group.limiter_config?.max_memory)}
              </div>
            </div>

            {group.circuit_breaker?.recovery_stage && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#92400e' }}>
                <strong>恢复阶段：</strong>{group.circuit_breaker.recovery_stage.name} 
                ({(group.circuit_breaker.recovery_stage.allow_rate * 100).toFixed(0)}% 流量)
                | 成功: {group.circuit_breaker.recovery_stage.current_successes}/{group.circuit_breaker.recovery_stage.success_required}
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: '24px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
        <h4 style={{ marginBottom: '12px', fontSize: '15px' }}>📌 资源组说明</h4>
        <ul style={{ fontSize: '13px', lineHeight: '2', color: '#555', paddingLeft: '20px' }}>
          <li><strong>隔离性：</strong>每个资源组有独立的限流、熔断、并发控制，互不影响</li>
          <li><strong>并发控制：</strong>超过最大并发数的查询会被直接拒绝</li>
          <li><strong>权重分配：</strong>用于多资源组调度时的资源分配比例</li>
          <li><strong>独立熔断：</strong>某个资源组熔断不会影响其他组的查询</li>
        </ul>
      </div>
    </div>
  )
}

export default ResourceGroupPanel
