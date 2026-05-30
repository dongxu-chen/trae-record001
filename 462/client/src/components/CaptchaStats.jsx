import React, { useState, useEffect, useCallback } from 'react'
import { captchaApi } from '../services/api'
import './CaptchaStats.css'

const CaptchaStats = () => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  const loadStats = useCallback(async () => {
    setLoading(true)
    try {
      const response = await captchaApi.getCaptchaStats()
      if (response.data.success) {
        setStats(response.data.data)
      }
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 10000)
    return () => clearInterval(interval)
  }, [loadStats])

  if (!stats) return null

  const difficultyColors = {
    slide: '🧩',
    rotate: '🔄',
    click: '👆',
    voice: '🔊',
  }

  const diffLabels = {
    slide: '拼图滑块',
    rotate: '旋转图片',
    click: '点选文字',
    voice: '语音验证',
  }

  return (
    <div className="captcha-stats-container">
      <div className="stats-header">
        <h2>📊 验证码统计</h2>
        <button
          className="refresh-btn"
          onClick={loadStats}
          disabled={loading}
        >
          🔄 刷新
        </button>
      </div>

      <div className="stats-tabs">
        {['overview', 'breakdown', 'risk', 'difficulty'].map((tab) => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'overview' ? '概览' :
             tab === 'breakdown' ? '类型分析' :
             tab === 'risk' ? '风险分析' : '难度分布'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="overview-section">
          <div className="stat-card">
            <h3>总体数据</h3>
            <div className="stat-grid">
              <div className="stat-item">
                <span className="stat-label">验证总数</span>
                <span className="stat-value">{stats.overall?.totalVerifications || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">成功次数</span>
                <span className="stat-value success">{stats.overall?.totalSuccess || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">失败次数</span>
                <span className="stat-value error">{stats.overall?.totalFailed || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">总成功率</span>
                <span className="stat-value">{stats.overall?.overallSuccessRate || '0%'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'breakdown' && (
        <div className="breakdown-section">
          {Object.keys(diffLabels).map((type) => {
            const typeStats = stats[type]
            if (!typeStats) return null

            return (
              <div key={type} className="type-stats">
                <h3>{difficultyColors[type]} {diffLabels[type]}</h3>
                <div className="type-stats-grid">
                  <div className="stat-item">
                    <span className="stat-label">成功率</span>
                    <span className="stat-value">{typeStats.successRate}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">失败率</span>
                    <span className="stat-value error">{typeStats.failureRate}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">平均尝试次数</span>
                    <span className="stat-value">{typeStats.avgAttempts?.toFixed(2) || 0}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">平均耗时</span>
                    <span className="stat-value">{typeStats.avgDuration}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">首次成功率</span>
                    <span className="stat-value success">{typeStats.firstTimeSuccessRate}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">破解风险</span>
                    <span className={`stat-value crack-risk-${typeStats.crackRisk}`}>
                      {typeStats.crackRisk === 'high' ? '高' :
                       typeStats.crackRisk === 'medium' ? '中' : '低'}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {activeTab === 'risk' && (
        <div className="risk-section">
          <div className="risk-stats">
            <h3>行为风险分析</h3>
            {Object.keys(diffLabels).map((type) => {
              const typeStats = stats[type]
              if (!typeStats) return null
              const low = typeStats.lowRiskCount || 0
              const medium = typeStats.mediumRiskCount || 0
              const high = typeStats.highRiskCount || 0
              const total = low + medium + high || 1

              return (
                <div key={type} className="risk-type">
                  <h4>{difficultyColors[type]} {diffLabels[type]}</h4>
                  <div className="risk-bar">
                    <div
                      className="risk-bar-low"
                      style={{ width: `${(low / total) * 100}%` }}
                    />
                    <div
                      className="risk-bar-medium"
                      style={{ width: `${(medium / total) * 100}%` }}
                    />
                    <div
                      className="risk-bar-high"
                      style={{ width: `${(high / total) * 100}%` }}
                    />
                  </div>
                  <div className="risk-labels">
                    <span className="risk-low">低风险: {low}</span>
                    <span className="risk-medium">中风险: {medium}</span>
                    <span className="risk-high">高风险: {high}</span>
                  </div>
                </div>
              )
            })}
          </div>

          {stats.highRiskIps && stats.highRiskIps.length > 0 && (
            <div className="high-risk-ips">
              <h3>⚠️ 高风险IP</h3>
              <table className="risk-table">
                <thead>
                  <tr>
                    <th>IP地址</th>
                    <th>风险评分</th>
                    <th>尝试次数</th>
                    <th>最后访问</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.highRiskIps.map((ip, idx) => (
                    <tr key={idx}>
                      <td>{ip.ip}</td>
                      <td className="risk-high">{ip.riskScore}</td>
                      <td>{ip.attempts}</td>
                      <td>{ip.lastSeen}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'difficulty' && (
        <div className="difficulty-section">
          <h3>难度通过率</h3>
          {Object.keys(diffLabels).map((type) => {
            const typeStats = stats[type]
            if (!typeStats?.difficultyPassRates) return null

            return (
              <div key={type} className="diff-type">
                <h4>{difficultyColors[type]} {diffLabels[type]}</h4>
                <div className="diff-grid">
                  {Object.entries(typeStats.difficultyPassRates || {}).map(([level, data]) => (
                    <div key={level} className="diff-item">
                      <span className="diff-label">
                        {level === 'easy' ? '简单' : level === 'medium' ? '中等' : '困难'}
                      </span>
                      <span className="diff-rate">{data.passRate}</span>
                      <span className="diff-count">{data.attempts} 次尝试</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default CaptchaStats
