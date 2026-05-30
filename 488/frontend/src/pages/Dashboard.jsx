import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getCurrentDeadlocks, getStatistics, getDetectorStatus, startDetector, stopDetector } from '../api/client'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [currentDeadlocks, setCurrentDeadlocks] = useState([])
  const [detectorRunning, setDetectorRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statsRes, deadlocksRes, statusRes] = await Promise.all([
        getStatistics(),
        getCurrentDeadlocks(),
        getDetectorStatus()
      ])
      setStats(statsRes.data.data)
      setCurrentDeadlocks(deadlocksRes.data.data || [])
      setDetectorRunning(statusRes.data.running)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleDetector = async () => {
    try {
      if (detectorRunning) {
        await stopDetector()
      } else {
        await startDetector()
      }
      setDetectorRunning(!detectorRunning)
    } catch (err) {
      console.error('Failed to toggle detector:', err)
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

  const chartData = stats?.DeadlocksByHour?.map(item => ({
    name: item.Time.split(' ')[1] || item.Time,
    死锁数: item.Count
  })) || []

  if (loading) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>仪表板</h2>
        <p>实时监控数据库死锁状态（每3秒自动刷新）</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">总死锁数</div>
          <div className="value">{stats?.TotalDeadlocks || 0}</div>
        </div>
        <div className="stat-card success">
          <div className="label">已解决</div>
          <div className="value">{stats?.ResolvedDeadlocks || 0}</div>
        </div>
        <div className="stat-card warning">
          <div className="label">当前死锁</div>
          <div className="value">{currentDeadlocks.length}</div>
        </div>
        <div className="stat-card error">
          <div className="label">自动KILL</div>
          <div className="value">{stats?.AutoKilledCount || 0}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>检测器状态</h3>
          <button 
            className={`btn ${detectorRunning ? 'btn-danger' : 'btn-success'}`}
            onClick={toggleDetector}
          >
            {detectorRunning ? '停止检测' : '开始检测'}
          </button>
        </div>
        <div className="form-row">
          <div>
            <p>检测器当前状态: <span style={{ color: detectorRunning ? 'green' : 'red', fontWeight: 'bold' }}>
              {detectorRunning ? '运行中' : '已停止'}
            </span></p>
          </div>
          <div>
            <p>平均检测延迟: <span style={{ color: '#1890ff', fontWeight: 'bold' }}>
              {stats?.AvgDetectionLatency || '-'}
            </span></p>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>死锁趋势</h3>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="死锁数" stroke="#1890ff" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>当前死锁 ({currentDeadlocks.length})</h3>
        </div>
        {currentDeadlocks.length === 0 ? (
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
              </tr>
            </thead>
            <tbody>
              {currentDeadlocks.map(deadlock => (
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default Dashboard
