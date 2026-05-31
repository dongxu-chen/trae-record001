import React, { useState, useEffect } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'

function AnalysisPanel({ user, showToast }) {
  const [activeTab, setActiveTab] = useState('user')
  const [userAnalysis, setUserAnalysis] = useState(null)
  const [churnAnalysis, setChurnAnalysis] = useState(null)
  const [trendData, setTrendData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (activeTab === 'user') {
      fetchUserAnalysis()
    } else if (activeTab === 'churn') {
      fetchChurnAnalysis()
    } else if (activeTab === 'trend') {
      fetchTrendAnalysis()
    }
  }, [activeTab, user.id])

  const fetchUserAnalysis = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`/api/analysis/user/${user.id}`, {
        params: { periodType: 'DAILY' }
      })
      if (res.data.code === 200) {
        setUserAnalysis(res.data.data)
      }
    } catch (err) {
      console.error('获取用户分析失败', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchChurnAnalysis = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/analysis/churn/DAILY', {
        params: { days: 30 }
      })
      if (res.data.code === 200) {
        setChurnAnalysis(res.data.data)
      }
    } catch (err) {
      console.error('获取流失分析失败', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchTrendAnalysis = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/analysis/trend/DAILY', {
        params: { days: 7 }
      })
      if (res.data.code === 200) {
        setTrendData(res.data.data)
      }
    } catch (err) {
      console.error('获取趋势分析失败', err)
    } finally {
      setLoading(false)
    }
  }

  const renderUserAnalysis = () => {
    if (!userAnalysis) return null

    const weekdays = ['一', '二', '三', '四', '五', '六', '日']
    const maxWeekdayCount = Math.max(...Object.values(userAnalysis.weekdayDistribution || {}), 1)

    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px', marginBottom: '20px' }}>
          <div style={{ padding: '15px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', borderRadius: '10px', color: 'white' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{userAnalysis.checkinRate}%</div>
            <div style={{ fontSize: '13px', opacity: 0.9 }}>近30天签到率</div>
          </div>
          <div style={{ padding: '15px', background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', borderRadius: '10px', color: 'white' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{userAnalysis.maxContinuousDays}</div>
            <div style={{ fontSize: '13px', opacity: 0.9 }}>最长连续签到</div>
          </div>
          <div style={{ padding: '15px', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', borderRadius: '10px', color: 'white' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{userAnalysis.totalCheckins}</div>
            <div style={{ fontSize: '13px', opacity: 0.9 }}>近30天签到次数</div>
          </div>
          <div style={{ padding: '15px', background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', borderRadius: '10px', color: 'white' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold' }}>{userAnalysis.avgCheckinsPerWeek}</div>
            <div style={{ fontSize: '13px', opacity: 0.9 }}>平均每周签到</div>
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '12px' }}>
            📊 星期签到分布
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '120px', padding: '10px', background: '#f8f9fa', borderRadius: '10px' }}>
            {weekdays.map((day, index) => {
              const count = userAnalysis.weekdayDistribution?.[index + 1] || 0
              const height = (count / maxWeekdayCount) * 100
              return (
                <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <div style={{ fontSize: '11px', color: '#666' }}>{count}</div>
                  <div style={{
                    width: '100%',
                    height: `${Math.max(height, 5)}%`,
                    background: 'linear-gradient(180deg, #667eea 0%, #764ba2 100%)',
                    borderRadius: '4px 4px 0 0',
                    transition: 'height 0.5s'
                  }}></div>
                  <div style={{ fontSize: '12px', color: '#666' }}>{day}</div>
                </div>
              )
            })}
          </div>
        </div>

        {userAnalysis.streakAnalysis && (
          <div style={{ padding: '15px', background: '#fff8e1', borderRadius: '10px' }}>
            <div style={{ fontWeight: 'bold', color: '#ff8f00', marginBottom: '10px' }}>
              📈 签到连续性分析
            </div>
            <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.8' }}>
              <div>当前连续签到：<span style={{ color: '#667eea', fontWeight: 'bold' }}>{userAnalysis.streakAnalysis.currentStreak}</span> 天</div>
              {userAnalysis.streakAnalysis.brokenStreaks?.length > 0 && (
                <div>
                  历史断签记录：{userAnalysis.streakAnalysis.brokenStreaks.slice(0, 5).map((d, i) => (
                    <span key={i} style={{ marginLeft: '5px', color: '#f5576c' }}>{d}天</span>
                  ))}
                </div>
              )}
              {userAnalysis.streakAnalysis.avgBrokenStreakLength > 0 && (
                <div>平均断签前连续：<span style={{ color: '#ff8f00', fontWeight: 'bold' }}>{userAnalysis.streakAnalysis.avgBrokenStreakLength}</span> 天</div>
              )}
            </div>
          </div>
        )}
      </div>
    )
  }

  const renderChurnAnalysis = () => {
    if (!churnAnalysis) return null

    const riskColors = {
      HIGH: '#f44336',
      MEDIUM: '#ff9800',
      LOW: '#4caf50'
    }

    return (
      <div>
        <div style={{ padding: '15px', background: '#ffebee', borderRadius: '10px', marginBottom: '20px' }}>
          <div style={{ fontWeight: 'bold', color: '#c62828', marginBottom: '8px' }}>
            ⚠️ 最高流失风险点
          </div>
          <div style={{ fontSize: '14px', color: '#666' }}>
            用户最容易在第 <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#f44336', margin: '0 4px' }}>
              {churnAnalysis.churnDay}
            </span> 天断签
            <div style={{ fontSize: '12px', marginTop: '4px' }}>
              流失率：{churnAnalysis.churnRate}% | 影响人数：{churnAnalysis.churnCount}人
            </div>
          </div>
        </div>

        {churnAnalysis.riskPoints && churnAnalysis.riskPoints.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '12px' }}>
              📊 前2周流失风险分布
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {churnAnalysis.riskPoints.slice(0, 14).map((point, index) => (
                <div key={index} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px',
                  background: '#fafafa',
                  borderRadius: '8px'
                }}>
                  <div style={{
                    width: '50px',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    background: riskColors[point.riskLevel] + '20',
                    color: riskColors[point.riskLevel],
                    fontSize: '11px',
                    textAlign: 'center',
                    fontWeight: 'bold'
                  }}>
                    {point.riskLevel === 'HIGH' ? '高风险' : point.riskLevel === 'MEDIUM' ? '中风险' : '低风险'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', color: '#333' }}>第 {point.day} 天</div>
                    <div style={{
                      height: '6px',
                      background: '#e0e0e0',
                      borderRadius: '3px',
                      overflow: 'hidden',
                      marginTop: '4px'
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${Math.min((point.churnCount / (churnAnalysis.churnCount || 1)) * 100, 100)}%`,
                        background: riskColors[point.riskLevel],
                        transition: 'width 0.5s'
                      }}></div>
                    </div>
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', width: '50px', textAlign: 'right' }}>
                    {point.churnCount}人
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ padding: '15px', background: '#e8f5e9', borderRadius: '10px' }}>
          <div style={{ fontWeight: 'bold', color: '#2e7d32', marginBottom: '8px' }}>
            💡 运营建议
          </div>
          <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.8' }}>
            <div>• 在第 {churnAnalysis.churnDay} 天前增加提醒推送</div>
            <div>• 对连续签到 {churnAnalysis.churnDay - 1} 天的用户发放额外奖励</div>
            <div>• 设计里程碑奖励，降低高风险点的流失率</div>
          </div>
        </div>
      </div>
    )
  }

  const renderTrendAnalysis = () => {
    if (!trendData || !trendData.trendData) return null

    const maxRate = Math.max(...trendData.trendData.map(d => d.checkinRate || 0), 1)

    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '20px' }}>
          <div style={{ padding: '12px', background: '#f0f9ff', borderRadius: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#0369a1' }}>{trendData.avgCheckinRate}%</div>
            <div style={{ fontSize: '11px', color: '#666' }}>平均签到率</div>
          </div>
          <div style={{ padding: '12px', background: '#f0fdf4', borderRadius: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#15803d' }}>{trendData.totalCheckins}</div>
            <div style={{ fontSize: '11px', color: '#666' }}>总签到人次</div>
          </div>
          <div style={{ padding: '12px', background: '#fef2f2', borderRadius: '10px', textAlign: 'center' }}>
            <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#dc2626' }}>{trendData.avgChurnRate}%</div>
            <div style={{ fontSize: '11px', color: '#666' }}>平均流失率</div>
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '12px' }}>
            📈 近7天签到率趋势
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '150px', padding: '10px', background: '#f8f9fa', borderRadius: '10px' }}>
            {trendData.trendData.map((data, index) => (
              <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <div style={{ fontSize: '10px', color: '#667eea', fontWeight: 'bold' }}>{data.checkinRate}%</div>
                <div style={{
                  width: '100%',
                  height: `${Math.max((data.checkinRate / maxRate) * 100, 5)}%`,
                  background: data.checkinRate >= 50 
                    ? 'linear-gradient(180deg, #43e97b 0%, #38f9d7 100%)'
                    : 'linear-gradient(180deg, #667eea 0%, #764ba2 100%)',
                  borderRadius: '4px 4px 0 0',
                  transition: 'height 0.5s',
                  position: 'relative'
                }}>
                  <div style={{
                    position: 'absolute',
                    bottom: '-20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    fontSize: '10px',
                    color: '#999',
                    whiteSpace: 'nowrap'
                  }}>
                    {data.checkedInUsers}人
                  </div>
                </div>
                <div style={{ fontSize: '10px', color: '#666', marginTop: '16px' }}>
                  {dayjs(data.date).format('MM/DD')}
                </div>
              </div>
            ))}
          </div>
        </div>

        {trendData.trendData.length > 0 && (
          <div style={{ padding: '15px', background: '#f5f5f5', borderRadius: '10px', fontSize: '12px' }}>
            <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '8px' }}>
              📋 详细数据
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e0e0e0' }}>
                    <th style={{ padding: '6px', textAlign: 'left', color: '#666' }}>日期</th>
                    <th style={{ padding: '6px', textAlign: 'center', color: '#666' }}>签到率</th>
                    <th style={{ padding: '6px', textAlign: 'center', color: '#666' }}>签到人数</th>
                    <th style={{ padding: '6px', textAlign: 'center', color: '#666' }}>新增用户</th>
                    <th style={{ padding: '6px', textAlign: 'center', color: '#666' }}>流失用户</th>
                  </tr>
                </thead>
                <tbody>
                  {trendData.trendData.map((data, index) => (
                    <tr key={index} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '6px', color: '#333' }}>{dayjs(data.date).format('MM月DD日')}</td>
                      <td style={{ padding: '6px', textAlign: 'center', color: '#667eea' }}>{data.checkinRate}%</td>
                      <td style={{ padding: '6px', textAlign: 'center', color: '#333' }}>{data.checkedInUsers || '-'}</td>
                      <td style={{ padding: '6px', textAlign: 'center', color: '#4caf50' }}>{data.newUsers || 0}</td>
                      <td style={{ padding: '6px', textAlign: 'center', color: '#f44336' }}>{data.lostUsers || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-title">
        <span>📊</span>
        <span>签到数据分析</span>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        {[
          { key: 'user', label: '我的分析', icon: '👤' },
          { key: 'churn', label: '流失分析', icon: '⚠️' },
          { key: 'trend', label: '趋势分析', icon: '📈' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: '10px',
              border: 'none',
              borderRadius: '8px',
              background: activeTab === tab.key 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : '#f0f0f0',
              color: activeTab === tab.key ? 'white' : '#666',
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
          <div style={{ fontSize: '40px', marginBottom: '10px' }}>📊</div>
          加载中...
        </div>
      ) : (
        <>
          {activeTab === 'user' && renderUserAnalysis()}
          {activeTab === 'churn' && renderChurnAnalysis()}
          {activeTab === 'trend' && renderTrendAnalysis()}
        </>
      )}
    </div>
  )
}

export default AnalysisPanel
