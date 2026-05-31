import { useState, useEffect } from 'react'
import axios from 'axios'

function DrillPanel() {
  const [drillStatus, setDrillStatus] = useState(null)
  const [drillReport, setDrillReport] = useState(null)
  const [defaultConfig, setDefaultConfig] = useState(null)
  const [showConfig, setShowConfig] = useState(false)
  const [config, setConfig] = useState({
    name: 'stress_test',
    duration_seconds: 60,
    concurrency: 50,
    queries_per_second: 100,
    resource_group: 'default',
    slow_query_ratio: 0.05,
    error_ratio: 0.02,
    priority_weights: {
      high: 20,
      medium: 60,
      low: 20
    }
  })

  const fetchDrillStatus = async () => {
    try {
      const res = await axios.get('/api/drill/status')
      setDrillStatus(res.data)
      if (res.data.running) {
        const reportRes = await axios.get('/api/drill/report')
        setDrillReport(reportRes.data)
      }
    } catch (err) {
      console.error('Failed to fetch drill status:', err)
    }
  }

  const fetchDefaultConfig = async () => {
    try {
      const res = await axios.get('/api/drill/config')
      setDefaultConfig(res.data)
    } catch (err) {
      console.error('Failed to fetch drill config:', err)
    }
  }

  useEffect(() => {
    fetchDrillStatus()
    fetchDefaultConfig()
    const interval = setInterval(fetchDrillStatus, 1000)
    return () => clearInterval(interval)
  }, [])

  const startDrill = async (useDefault = false) => {
    try {
      const payload = useDefault ? {} : config
      await axios.post('/api/drill/start', payload)
      fetchDrillStatus()
    } catch (err) {
      alert('启动失败: ' + (err.response?.data || err.message))
    }
  }

  const stopDrill = async () => {
    if (!confirm('确定要停止当前演练吗？')) return
    try {
      await axios.post('/api/drill/stop')
      fetchDrillStatus()
      const reportRes = await axios.get('/api/drill/report')
      setDrillReport(reportRes.data)
    } catch (err) {
      console.error('Failed to stop drill:', err)
    }
  }

  const getStatusColor = (value, max, type) => {
    const ratio = value / max
    if (type === 'success') {
      if (ratio > 0.9) return '#16a34a'
      if (ratio > 0.7) return '#f59e0b'
      return '#dc2626'
    }
    if (type === 'reject') {
      if (ratio < 0.1) return '#16a34a'
      if (ratio < 0.3) return '#f59e0b'
      return '#dc2626'
    }
    return '#666'
  }

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    if (num >= 1000000) return (num / 1000000).toFixed(2) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(2) + 'K'
    return num.toFixed(0)
  }

  return (
    <div>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <p style={{ color: '#666', fontSize: '14px' }}>
            模拟高并发场景，测试限流、熔断、排队等功能的实际效果
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!drillStatus?.running ? (
            <>
              <button 
                className="btn btn-primary"
                onClick={() => startDrill(true)}
              >
                🚀 快速开始 (默认配置)
              </button>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowConfig(!showConfig)}
              >
                ⚙️ 自定义配置
              </button>
            </>
          ) : (
            <button 
              className="btn btn-danger"
              onClick={stopDrill}
            >
              ⏹️ 停止演练
            </button>
          )}
        </div>
      </div>

      {showConfig && !drillStatus?.running && (
        <div style={{
          background: '#f8fafc',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '24px',
          border: '1px solid #e1e5eb'
        }}>
          <h4 style={{ marginBottom: '16px', fontSize: '15px' }}>演练配置</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label>演练名称</label>
              <input
                type="text"
                value={config.name}
                onChange={(e) => setConfig({...config, name: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>持续时间 (秒)</label>
              <input
                type="number"
                value={config.duration_seconds}
                onChange={(e) => setConfig({...config, duration_seconds: parseInt(e.target.value)})}
              />
            </div>
            <div className="form-group">
              <label>并发数</label>
              <input
                type="number"
                value={config.concurrency}
                onChange={(e) => setConfig({...config, concurrency: parseInt(e.target.value)})}
              />
            </div>
            <div className="form-group">
              <label>每秒查询数 (QPS)</label>
              <input
                type="number"
                value={config.queries_per_second}
                onChange={(e) => setConfig({...config, queries_per_second: parseInt(e.target.value)})}
              />
            </div>
            <div className="form-group">
              <label>目标资源组</label>
              <select
                value={config.resource_group}
                onChange={(e) => setConfig({...config, resource_group: e.target.value})}
              >
                <option value="default">default</option>
                <option value="data_team">data_team</option>
                <option value="reporting">reporting</option>
                <option value="realtime">realtime</option>
              </select>
            </div>
            <div className="form-group">
              <label>慢查询比例</label>
              <input
                type="number"
                step="0.01"
                value={config.slow_query_ratio}
                onChange={(e) => setConfig({...config, slow_query_ratio: parseFloat(e.target.value)})}
              />
            </div>
            <div className="form-group">
              <label>错误查询比例</label>
              <input
                type="number"
                step="0.01"
                value={config.error_ratio}
                onChange={(e) => setConfig({...config, error_ratio: parseFloat(e.target.value)})}
              />
            </div>
          </div>
          <button 
            className="btn btn-primary"
            onClick={() => startDrill(false)}
            style={{ marginTop: '12px' }}
          >
            🚀 开始演练
          </button>
        </div>
      )}

      {drillStatus?.running && (
        <div style={{
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '24px',
          border: '1px solid #fbbf24'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0, color: '#92400e', fontSize: '18px' }}>
              🔥 演练进行中: {drillStatus.name}
            </h3>
            <span className="status-badge status-warning">
              运行中
            </span>
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ color: '#92400e' }}>
                已运行: {drillStatus.metrics?.elapsed_seconds?.toFixed(1)}s / {drillStatus.metrics?.duration_seconds}s
              </span>
              <span style={{ color: '#92400e' }}>
                进度: {((drillStatus.metrics?.elapsed_seconds / drillStatus.metrics?.duration_seconds) * 100).toFixed(1)}%
              </span>
            </div>
            <div style={{
              background: '#fcd34d',
              borderRadius: '4px',
              height: '16px',
              overflow: 'hidden'
            }}>
              <div style={{
                background: 'linear-gradient(90deg, #f59e0b, #d97706)',
                height: '100%',
                width: `${Math.min(100, (drillStatus.metrics?.elapsed_seconds / drillStatus.metrics?.duration_seconds) * 100)}%`,
                transition: 'width 0.3s ease'
              }}></div>
            </div>
          </div>
        </div>
      )}

      {drillStatus?.metrics && (
        <>
          <h4 style={{ marginBottom: '16px', fontSize: '16px' }}>📊 实时指标</h4>
          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '24px' }}>
            <div className="metric-card" style={{ background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)' }}>
              <div className="value" style={{ color: '#15803d', fontSize: '28px' }}>
                {formatNumber(drillStatus.metrics.total_queries)}
              </div>
              <div className="label" style={{ color: '#166534' }}>总请求数</div>
            </div>
            <div className="metric-card" style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)' }}>
              <div className="value" style={{ 
                color: getStatusColor(drillStatus.metrics.success_queries, drillStatus.metrics.total_queries, 'success'),
                fontSize: '28px' 
              }}>
                {formatNumber(drillStatus.metrics.success_queries)}
              </div>
              <div className="label" style={{ color: '#1e40af' }}>成功数</div>
            </div>
            <div className="metric-card" style={{ background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)' }}>
              <div className="value" style={{ 
                color: getStatusColor(drillStatus.metrics.rejected_queries, drillStatus.metrics.total_queries, 'reject'),
                fontSize: '28px' 
              }}>
                {formatNumber(drillStatus.metrics.rejected_queries)}
              </div>
              <div className="label" style={{ color: '#92400e' }}>被限流数</div>
            </div>
            <div className="metric-card" style={{ background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)' }}>
              <div className="value" style={{ color: '#b91c1c', fontSize: '28px' }}>
                {formatNumber(drillStatus.metrics.failed_queries + drillStatus.metrics.timed_out_queries)}
              </div>
              <div className="label" style={{ color: '#991b1b' }}>失败/超时</div>
            </div>
          </div>

          <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: '24px' }}>
            <div className="metric-card">
              <div className="value" style={{ color: '#667eea', fontSize: '24px' }}>
                {drillStatus.metrics.throughput?.toFixed(1) || '-'}
              </div>
              <div className="label">吞吐量 (QPS)</div>
            </div>
            <div className="metric-card">
              <div className="value" style={{ color: '#8b5cf6', fontSize: '24px' }}>
                {drillStatus.metrics.avg_latency_ms?.toFixed(1) || '-'} ms
              </div>
              <div className="label">平均延迟</div>
            </div>
            <div className="metric-card">
              <div className="value" style={{ 
                color: getStatusColor(drillStatus.metrics.success_queries, drillStatus.metrics.total_queries, 'success'),
                fontSize: '24px' 
              }}>
                {drillStatus.metrics.total_queries > 0 
                  ? ((drillStatus.metrics.success_queries / drillStatus.metrics.total_queries) * 100).toFixed(1) 
                  : '-'}%
              </div>
              <div className="label">成功率</div>
            </div>
          </div>
        </>
      )}

      {drillReport && (
        <div style={{
          background: '#f0f9ff',
          border: '1px solid #bae6fd',
          padding: '24px',
          borderRadius: '8px',
          marginTop: '24px'
        }}>
          <h3 style={{ marginBottom: '20px', fontSize: '18px', color: '#0369a1' }}>📋 演练报告</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div>
              <h4 style={{ marginBottom: '12px', fontSize: '15px', color: '#0c4a6e' }}>配置信息</h4>
              <div style={{ fontSize: '13px', lineHeight: '2', color: '#555' }}>
                <div><strong>演练名称：</strong>{drillReport.Config?.name}</div>
                <div><strong>持续时间：</strong>{drillReport.Config?.Duration / 1000000000}秒</div>
                <div><strong>并发数：</strong>{drillReport.Config?.Concurrency}</div>
                <div><strong>目标QPS：</strong>{drillReport.Config?.QueriesPerSec}</div>
                <div><strong>资源组：</strong>{drillReport.Config?.ResourceGroup}</div>
              </div>
            </div>
            <div>
              <h4 style={{ marginBottom: '12px', fontSize: '15px', color: '#0c4a6e' }}>性能指标</h4>
              <div style={{ fontSize: '13px', lineHeight: '2', color: '#555' }}>
                <div><strong>实际吞吐量：</strong>{drillReport.Throughput?.toFixed(2)} QPS</div>
                <div><strong>成功率：</strong>{drillReport.SuccessRate?.toFixed(2)}%</div>
                <div><strong>拒绝率：</strong>{drillReport.RejectRate?.toFixed(2)}%</div>
                <div><strong>平均延迟：</strong>{drillReport.AvgLatency?.toFixed(2)} ms</div>
                <div><strong>P95延迟：</strong>{drillReport.P95Latency?.toFixed(2)} ms</div>
                <div><strong>P99延迟：</strong>{drillReport.P99Latency?.toFixed(2)} ms</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '20px' }}>
            <h4 style={{ marginBottom: '12px', fontSize: '15px', color: '#0c4a6e' }}>结果统计</h4>
            <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              <div className="metric-card">
                <div className="value">{drillReport.Metrics?.TotalQueries}</div>
                <div className="label">总请求</div>
              </div>
              <div className="metric-card" style={{ background: '#dcfce7' }}>
                <div className="value" style={{ color: '#15803d' }}>{drillReport.Metrics?.SuccessQueries}</div>
                <div className="label" style={{ color: '#166534' }}>成功</div>
              </div>
              <div className="metric-card" style={{ background: '#fef3c7' }}>
                <div className="value" style={{ color: '#b45309' }}>{drillReport.Metrics?.RejectedQueries}</div>
                <div className="label" style={{ color: '#92400e' }}>被限流</div>
              </div>
              <div className="metric-card" style={{ background: '#fee2e2' }}>
                <div className="value" style={{ color: '#b91c1c' }}>{drillReport.Metrics?.FailedQueries}</div>
                <div className="label" style={{ color: '#991b1b' }}>失败</div>
              </div>
              <div className="metric-card" style={{ background: '#fef2f2' }}>
                <div className="value" style={{ color: '#dc2626' }}>{drillReport.Metrics?.TimedOutQueries}</div>
                <div className="label" style={{ color: '#b91c1c' }}>超时</div>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '20px', padding: '16px', background: 'white', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '12px', fontSize: '15px', color: '#0c4a6e' }}>💡 评估结论</h4>
            <div style={{ fontSize: '13px', lineHeight: '2', color: '#555' }}>
              {drillReport.SuccessRate >= 95 ? (
                <p style={{ color: '#15803d' }}>✅ 系统表现优秀，成功率达到 {drillReport.SuccessRate?.toFixed(1)}%，限流策略有效。</p>
              ) : drillReport.SuccessRate >= 80 ? (
                <p style={{ color: '#b45309' }}>⚠️ 系统表现一般，成功率 {drillReport.SuccessRate?.toFixed(1)}%，建议优化限流参数。</p>
              ) : (
                <p style={{ color: '#dc2626' }}>❌ 系统表现较差，成功率仅 {drillReport.SuccessRate?.toFixed(1)}%，需要立即调整限流策略！</p>
              )}
              {drillReport.RejectRate > 20 && (
                <p style={{ color: '#dc2626' }}>⚠️ 限流严重，拒绝率达到 {drillReport.RejectRate?.toFixed(1)}%，建议增加资源配额。</p>
              )}
              {drillReport.P99Latency > 1000 && (
                <p style={{ color: '#b45309' }}>⚠️ P99延迟过高 ({drillReport.P99Latency?.toFixed(0)}ms)，查询处理效率需要优化。</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ marginTop: '24px', padding: '20px', background: '#f8f9fa', borderRadius: '8px' }}>
        <h4 style={{ marginBottom: '12px', fontSize: '15px' }}>🧪 演练说明</h4>
        <ul style={{ fontSize: '13px', lineHeight: '2', color: '#555', paddingLeft: '20px' }}>
          <li><strong>高并发模拟：</strong>按指定并发数和QPS持续发送查询请求</li>
          <li><strong>混合负载：</strong>按比例混合简单查询、复杂查询、慢查询和错误查询</li>
          <li><strong>优先级分布：</strong>按权重随机生成高/中/低优先级查询</li>
          <li><strong>实时监控：</strong>展示成功数、拒绝数、延迟分布等关键指标</li>
          <li><strong>演练报告：</strong>演练结束后生成详细报告，包含P95/P99延迟和评估建议</li>
        </ul>
      </div>
    </div>
  )
}

export default DrillPanel
