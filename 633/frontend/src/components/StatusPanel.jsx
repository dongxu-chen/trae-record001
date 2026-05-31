function StatusPanel({ status }) {
  if (!status) {
    return <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>加载中...</div>
  }

  const getCircuitBreakerStatus = (state) => {
    const baseStatus = state.split(':')[0]
    const statusMap = {
      'closed': { text: '正常运行', class: 'status-success' },
      'open': { text: '已熔断', class: 'status-error' },
      'half_open': { text: '恢复中', class: 'status-warning' }
    }
    const result = statusMap[baseStatus] || { text: state, class: 'status-info' }
    
    if (state.includes(':')) {
      const stageMap = {
        'probe': '探测阶段',
        'low_traffic': '低流量',
        'medium_traffic': '中流量',
        'high_traffic': '高流量'
      }
      const stage = state.split(':')[1]
      result.text = `${result.text} (${stageMap[stage] || stage})`
    }
    return result
  }

  const cbStatus = getCircuitBreakerStatus(status.CircuitBreaker)
  const cbDetail = status.CircuitBreakerDetail || {}
  const recoveryStage = cbDetail.recovery_stage

  const getRecoveryProgress = () => {
    if (cbDetail.state === 'closed') return 100
    if (cbDetail.state === 'open') return 0
    if (recoveryStage) {
      const stageIndex = recoveryStage.stage || 0
      const totalStages = 4
      const stageProgress = recoveryStage.current_successes / Math.max(recoveryStage.success_required, 1)
      return Math.min(100, ((stageIndex + Math.min(stageProgress, 1)) / totalStages) * 100)
    }
    return 0
  }

  const queueOrder = status.QueueOrder || []

  const getPriorityLabel = (p) => {
    if (p === 3) return { text: '高', color: '#fee2e2', textColor: '#991b1b' }
    if (p === 2) return { text: '中', color: '#fef3c7', textColor: '#92400e' }
    return { text: '低', color: '#dbeafe', textColor: '#1d4ed8' }
  }

  return (
    <div>
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="value">{status.QueryCount || 0}</div>
          <div className="label">总查询数</div>
        </div>
        <div className="metric-card">
          <div className="value">
            <span className={`status-badge ${cbStatus.class}`}>{cbStatus.text}</span>
          </div>
          <div className="label">熔断器状态</div>
        </div>
        <div className="metric-card">
          <div className="value">{status.QueueMetrics?.total || 0}</div>
          <div className="label">队列中查询</div>
        </div>
      </div>

      {recoveryStage && (
        <div style={{
          background: '#fff7ed',
          border: '1px solid #fed7aa',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '24px'
        }}>
          <h3 style={{ marginBottom: '16px', fontSize: '16px' }}>🔄 熔断恢复进度</h3>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '14px', color: '#92400e' }}>
                当前阶段: {recoveryStage.name === 'probe' ? '🔍 探测阶段' : 
                           recoveryStage.name === 'low_traffic' ? '📊 低流量阶段' :
                           recoveryStage.name === 'medium_traffic' ? '📈 中流量阶段' : '🚀 高流量阶段'}
              </span>
              <span style={{ fontSize: '14px', color: '#92400e' }}>
                允许通过率: {(recoveryStage.allow_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{
              background: '#fed7aa',
              borderRadius: '4px',
              height: '20px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                background: 'linear-gradient(90deg, #f59e0b, #d97706)',
                height: '100%',
                width: `${getRecoveryProgress()}%`,
                transition: 'width 0.3s ease'
              }}></div>
              <span style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                fontSize: '12px',
                fontWeight: '600',
                color: '#78350f'
              }}>
                {getRecoveryProgress().toFixed(1)}%
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: '#78350f' }}>
              <span>成功数: {recoveryStage.current_successes} / {recoveryStage.success_required}</span>
              <span>已持续: {Math.floor(recoveryStage.elapsed_time / 1000000000)}秒</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['probe', 'low_traffic', 'medium_traffic', 'high_traffic'].map((stage, i) => (
              <div key={stage} style={{
                flex: 1,
                padding: '8px',
                background: i <= (recoveryStage.stage || 0) ? '#f59e0b' : '#fef3c7',
                color: i <= (recoveryStage.stage || 0) ? 'white' : '#92400e',
                borderRadius: '4px',
                textAlign: 'center',
                fontSize: '11px',
                fontWeight: '500'
              }}>
                {stage === 'probe' ? '探测' : stage === 'low_traffic' ? '低流量' : stage === 'medium_traffic' ? '中流量' : '高流量'}
                {i < (recoveryStage.stage || 0) && ' ✓'}
              </div>
            ))}
          </div>
        </div>
      )}

      <h3 style={{ marginBottom: '16px', fontSize: '16px' }}>📦 优先级队列状态</h3>
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="metric-card" style={{ background: 'linear-gradient(135deg, #ffe4e6 0%, #fecdd3 100%)' }}>
          <div className="value" style={{ color: '#be123c' }}>{status.QueueMetrics?.high || 0}</div>
          <div className="label" style={{ color: '#9f1239' }}>高优先级</div>
        </div>
        <div className="metric-card" style={{ background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)' }}>
          <div className="value" style={{ color: '#b45309' }}>{status.QueueMetrics?.medium || 0}</div>
          <div className="label" style={{ color: '#92400e' }}>中优先级</div>
        </div>
        <div className="metric-card" style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)' }}>
          <div className="value" style={{ color: '#1d4ed8' }}>{status.QueueMetrics?.low || 0}</div>
          <div className="label" style={{ color: '#1e40af' }}>低优先级</div>
        </div>
        <div className="metric-card" style={{ background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)' }}>
          <div className="value" style={{ color: '#15803d' }}>{status.QueueMetrics?.max_size || 0}</div>
          <div className="label" style={{ color: '#166534' }}>队列容量</div>
        </div>
        <div className="metric-card" style={{ background: 'linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%)' }}>
          <div className="value" style={{ color: '#7c3aed' }}>{status.QueueMetrics?.preempt_count || 0}</div>
          <div className="label" style={{ color: '#6b21a8' }}>插队次数</div>
        </div>
      </div>

      {queueOrder.length > 0 && (
        <div style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '16px', fontSize: '16px' }}>📋 队列顺序</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>位置</th>
                  <th>请求ID</th>
                  <th>用户ID</th>
                  <th>优先级</th>
                  <th>插入位置</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {queueOrder.slice(0, 20).map((item) => {
                  const prio = getPriorityLabel(item.priority)
                  return (
                    <tr key={item.id}>
                      <td style={{ fontWeight: '600' }}>#{item.position + 1}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: '11px' }}>{item.id?.slice(0, 8)}...</td>
                      <td>{item.user_id}</td>
                      <td>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          background: prio.color,
                          color: prio.textColor
                        }}>{prio.text}</span>
                      </td>
                      <td>#{item.insert_pos + 1}</td>
                      <td>
                        {item.preempted ? (
                          <span className="status-badge status-warning">已插队</span>
                        ) : (
                          <span className="status-badge status-info">正常排队</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {queueOrder.length > 20 && (
            <div style={{ textAlign: 'center', marginTop: '8px', color: '#666', fontSize: '12px' }}>
              仅显示前20条，共 {queueOrder.length} 条
            </div>
          )}
        </div>
      )}

      <div style={{ marginTop: '24px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
        <h3 style={{ marginBottom: '16px', fontSize: '16px' }}>⚙️ 限流规则说明</h3>
        <ul style={{ fontSize: '14px', lineHeight: '2', color: '#555', paddingLeft: '20px' }}>
          <li><strong>全局限流：</strong>每秒 10 个查询，最大突发 20 个</li>
          <li><strong>用户级限流：</strong>每个用户每秒 5 个查询，最大突发 10 个</li>
          <li><strong>扫描行数限制：</strong>最大 1 亿行</li>
          <li><strong>内存限制：</strong>最大 1 GB</li>
          <li><strong>查询超时：</strong>60 秒</li>
          <li><strong>优先级插队：</strong>高优查询自动插到中低优查询前面</li>
          <li><strong>渐进式恢复：</strong>10% → 30% → 60% → 90% 逐步放开流量</li>
        </ul>
      </div>
    </div>
  )
}

export default StatusPanel
