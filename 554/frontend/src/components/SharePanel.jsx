import React, { useState, useEffect } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'

function SharePanel({ user, showToast, updateUser }) {
  const [shareStats, setShareStats] = useState(null)
  const [shareHistory, setShareHistory] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [shareData, setShareData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchData()
  }, [user.id])

  const fetchData = async () => {
    try {
      const [statsRes, historyRes, platformsRes] = await Promise.all([
        axios.get(`/api/share/stats/${user.id}`),
        axios.get(`/api/share/history/${user.id}`),
        axios.get('/api/share/platforms')
      ])

      if (statsRes.data.code === 200) {
        setShareStats(statsRes.data.data)
      }
      if (historyRes.data.code === 200) {
        setShareHistory(historyRes.data.data)
      }
      if (platformsRes.data.code === 200) {
        setPlatforms(platformsRes.data.data)
      }
    } catch (err) {
      console.error('获取分享数据失败', err)
    }
  }

  const handleCreateShare = async (platform) => {
    setLoading(true)
    try {
      const res = await axios.post('/api/share/create', {
        userId: user.id,
        periodType: 'DAILY',
        platform: platform.platform
      })

      if (res.data.code === 200) {
        setShareData(res.data.data)
        showToast('分享内容已生成！', 'success')
        
        if (navigator.share) {
          try {
            await navigator.share({
              title: '我的签到成就',
              text: res.data.data.shareContent,
              url: window.location.href
            })
          } catch (e) {
            console.log('分享取消')
          }
        }
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '生成分享失败', 'error')
    } finally {
      setLoading(false)
    }
  }

  const handleClaimReward = async (shareId) => {
    try {
      const res = await axios.post(`/api/share/claim/${shareId}`)
      if (res.data.code === 200) {
        const data = res.data.data
        showToast(`领取成功！获得 ${data.totalReward} 积分${data.bonusReward > 0 ? '（含周奖励' + data.bonusReward + '）' : ''}`, 'success')
        updateUser({ points: data.newPoints })
        fetchData()
        setShareData(null)
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '领取失败', 'error')
    }
  }

  return (
    <div className="card">
      <div className="card-title">
        <span>📤</span>
        <span>社交分享</span>
      </div>

      {shareStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '20px' }}>
          <div style={{ textAlign: 'center', padding: '12px', background: '#f0f9ff', borderRadius: '10px' }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#0369a1' }}>
              {shareStats.totalShares}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>总分享</div>
          </div>
          <div style={{ textAlign: 'center', padding: '12px', background: '#f0fdf4', borderRadius: '10px' }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#15803d' }}>
              {shareStats.claimedRewards}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>已领奖</div>
          </div>
          <div style={{ textAlign: 'center', padding: '12px', background: '#fefce8', borderRadius: '10px' }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ca8a04' }}>
              {shareStats.totalViews}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>总浏览</div>
          </div>
          <div style={{ textAlign: 'center', padding: '12px', background: '#fdf2f8', borderRadius: '10px' }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#be185d' }}>
              {shareStats.totalLikes}
            </div>
            <div style={{ fontSize: '12px', color: '#666' }}>总点赞</div>
          </div>
        </div>
      )}

      <div style={{ background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)', padding: '15px', borderRadius: '10px', marginBottom: '20px' }}>
        <div style={{ fontWeight: 'bold', color: '#667eea', marginBottom: '8px' }}>
          🎁 分享奖励规则
        </div>
        <div style={{ fontSize: '13px', color: '#666', lineHeight: '1.8' }}>
          <div>• 每日分享可获得 <span style={{ color: '#667eea', fontWeight: 'bold' }}>20积分</span></div>
          <div>• 每周累计分享7天额外获得 <span style={{ color: '#f5576c', fontWeight: 'bold' }}>100积分</span></div>
          <div style={{ marginTop: '8px', color: '#888' }}>
            本周进度：{shareStats?.weekClaimedCount || 0} / 7
            {shareStats?.canGetWeeklyBonus && (
              <span style={{ color: '#4caf50', marginLeft: '10px' }}>✓ 可领取周奖励</span>
            )}
          </div>
        </div>
      </div>

      {!shareStats?.todayShared ? (
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '12px' }}>
            选择分享平台
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {platforms.map((platform, index) => (
              <button
                key={index}
                onClick={() => handleCreateShare(platform)}
                disabled={loading}
                style={{
                  flex: 1,
                  minWidth: '80px',
                  padding: '12px 8px',
                  border: '2px solid #e0e0e0',
                  borderRadius: '10px',
                  background: 'white',
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                  fontSize: '13px'
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = '#667eea'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = '#e0e0e0'}
              >
                <div style={{ fontSize: '24px', marginBottom: '4px' }}>{platform.icon}</div>
                <div>{platform.name}</div>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: '20px' }}>
          {!shareStats.todayRewardClaimed && shareData && (
            <div style={{ background: '#e8f5e9', padding: '15px', borderRadius: '10px', marginBottom: '15px' }}>
              <div style={{ fontWeight: 'bold', color: '#2e7d32', marginBottom: '10px' }}>
                ✨ 今日分享内容已生成
              </div>
              <div style={{ 
                background: 'white', 
                padding: '12px', 
                borderRadius: '8px',
                marginBottom: '12px',
                fontSize: '13px',
                color: '#333',
                lineHeight: '1.6',
                whiteSpace: 'pre-line'
              }}>
                {shareData.shareContent}
              </div>
              <button
                onClick={() => handleClaimReward(shareData.shareId)}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: 'none',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                领取 {shareData.rewardPoints} 积分奖励
              </button>
            </div>
          )}
          
          {shareStats.todayRewardClaimed && (
            <div style={{ textAlign: 'center', padding: '20px', background: '#f5f5f5', borderRadius: '10px' }}>
              <div style={{ fontSize: '40px', marginBottom: '10px' }}>✅</div>
              <div style={{ color: '#666' }}>今日已分享并领取奖励</div>
            </div>
          )}
          
          {!shareStats.todayRewardClaimed && !shareData && (
            <div style={{ textAlign: 'center', padding: '20px', background: '#fff3e0', borderRadius: '10px' }}>
              <div style={{ fontSize: '40px', marginBottom: '10px' }}>📝</div>
              <div style={{ color: '#e65100', marginBottom: '10px' }}>今日已分享但未领奖</div>
              <button
                onClick={async () => {
                  const res = await axios.get(`/api/share/history/${user.id}`)
                  if (res.data.code === 200 && res.data.data.length > 0) {
                    const today = dayjs().format('YYYY-MM-DD')
                    const todayShare = res.data.data.find(s => 
                      dayjs(s.shareDate).format('YYYY-MM-DD') === today
                    )
                    if (todayShare) {
                      handleClaimReward(todayShare.id)
                    }
                  }
                }}
                style={{
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '8px',
                  background: '#ff9800',
                  color: 'white',
                  fontWeight: 'bold',
                  cursor: 'pointer'
                }}
              >
                领取今日奖励
              </button>
            </div>
          )}
        </div>
      )}

      {shareHistory.length > 0 && (
        <div>
          <div style={{ fontWeight: 'bold', color: '#333', marginBottom: '12px' }}>
            分享记录
          </div>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {shareHistory.slice(0, 10).map((item, index) => (
              <div key={index} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px',
                marginBottom: '8px',
                background: '#fafafa',
                borderRadius: '8px',
                fontSize: '13px'
              }}>
                <div>
                  <div style={{ color: '#333' }}>
                    {dayjs(item.shareDate).format('MM月DD日')}
                    {item.platform && <span style={{ color: '#999', marginLeft: '8px' }}>· {item.platform}</span>}
                  </div>
                  <div style={{ fontSize: '11px', color: '#999', marginTop: '2px' }}>
                    👁️ {item.viewCount} · ❤️ {item.likeCount}
                  </div>
                </div>
                <div style={{ color: item.rewardClaimed ? '#4caf50' : '#ff9800', fontSize: '12px' }}>
                  {item.rewardClaimed ? `+${item.rewardValue}分` : '待领取'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SharePanel
