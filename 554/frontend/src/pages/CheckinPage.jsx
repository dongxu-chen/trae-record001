import React, { useState, useEffect } from 'react'
import axios from 'axios'
import dayjs from 'dayjs'
import Calendar from '../components/Calendar'
import RewardsList from '../components/RewardsList'
import TreasuresGrid from '../components/TreasuresGrid'
import RewardModal from '../components/RewardModal'
import ReminderSettings from '../components/ReminderSettings'
import SharePanel from '../components/SharePanel'
import AnalysisPanel from '../components/AnalysisPanel'

function CheckinPage({ user, onLogout, showToast, updateUser }) {
  const [activeTab, setActiveTab] = useState('checkin')
  const [periodType, setPeriodType] = useState('DAILY')
  const [currentDate, setCurrentDate] = useState(dayjs())
  const [calendarData, setCalendarData] = useState(null)
  const [modalData, setModalData] = useState(null)
  const [stats, setStats] = useState(null)
  const [reminderStatus, setReminderStatus] = useState(null)

  useEffect(() => {
    if (activeTab === 'checkin') {
      fetchCalendarData()
      fetchStats()
      fetchReminderStatus()
    }
  }, [periodType, currentDate, activeTab])

  const fetchCalendarData = async () => {
    try {
      const res = await axios.get('/api/checkin/calendar', {
        params: {
          userId: user.id,
          periodType,
          date: currentDate.format('YYYY-MM-DD')
        }
      })
      if (res.data.code === 200) {
        setCalendarData(res.data.data)
      }
    } catch (err) {
      console.error('获取日历数据失败', err)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/checkin/stats', {
        params: { userId: user.id }
      })
      if (res.data.code === 200) {
        setStats(res.data.data)
      }
    } catch (err) {
      console.error('获取统计数据失败', err)
    }
  }

  const fetchReminderStatus = async () => {
    try {
      const res = await axios.get(`/api/reminder/status/${user.id}`)
      if (res.data.code === 200) {
        setReminderStatus(res.data.data)
      }
    } catch (err) {
      console.error('获取提醒状态失败', err)
    }
  }

  const handleCheckin = async () => {
    try {
      const res = await axios.post('/api/checkin', {
        userId: user.id,
        periodType
      })
      if (res.data.code === 200) {
        const data = res.data.data
        setModalData({
          type: 'checkin',
          icon: '🎉',
          title: '签到成功！',
          desc: `连续签到 ${data.continuousDays} 天`,
          reward: data.reward
        })
        updateUser({ points: data.points })
        fetchCalendarData()
        fetchStats()
        fetchReminderStatus()
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '签到失败', 'error')
    }
  }

  const handleRecheck = async (date) => {
    try {
      const res = await axios.post('/api/checkin/recheck', {
        userId: user.id,
        periodType,
        checkinDate: date
      })
      if (res.data.code === 200) {
        showToast('补签成功', 'success')
        updateUser({ recheckCards: res.data.data.remainingCards })
        fetchCalendarData()
        fetchStats()
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '补签失败', 'error')
    }
  }

  const handleClaimTreasure = async (treasureId) => {
    try {
      const res = await axios.post(`/api/checkin/treasure/${treasureId}?userId=${user.id}`)
      if (res.data.code === 200) {
        const data = res.data.data
        setModalData({
          type: 'treasure',
          icon: '🎁',
          title: '领取成功！',
          desc: `获得 ${data.name}`,
          reward: { name: data.name, value: data.value, type: data.type }
        })
        fetchCalendarData()
        fetchStats()
      } else {
        showToast(res.data.message, 'error')
      }
    } catch (err) {
      showToast(err.response?.data?.message || '领取失败', 'error')
    }
  }

  const periodLabels = {
    DAILY: '日签到',
    WEEKLY: '周签到',
    MONTHLY: '月签到'
  }

  const tabs = [
    { key: 'checkin', label: '签到', icon: '📅' },
    { key: 'reminder', label: '提醒', icon: '🔔' },
    { key: 'share', label: '分享', icon: '📤' },
    { key: 'analysis', label: '分析', icon: '📊' }
  ]

  const renderCheckinContent = () => (
    <>
      {reminderStatus?.continuousBrokenRisk && !reminderStatus.todayChecked && (
        <div style={{
          background: 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)',
          padding: '15px',
          borderRadius: '12px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <div style={{ fontWeight: 'bold', color: '#c62828', marginBottom: '4px' }}>
              ⚠️ 连续签到即将中断！
            </div>
            <div style={{ fontSize: '13px', color: '#8b0000' }}>
              您已连续签到 {reminderStatus.continuousDays} 天，今日若不签到将重置连续天数！
            </div>
          </div>
          <button
            onClick={handleCheckin}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '8px',
              background: '#c62828',
              color: 'white',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            立即签到
          </button>
        </div>
      )}

      {reminderStatus?.nearTreasure && !reminderStatus.todayChecked && (
        <div style={{
          background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
          padding: '15px',
          borderRadius: '12px',
          marginBottom: '20px'
        }}>
          <div style={{ fontWeight: 'bold', color: '#00695c', marginBottom: '4px' }}>
            💎 宝箱即将达成！
          </div>
          <div style={{ fontSize: '13px', color: '#004d40' }}>
            还差 {reminderStatus.nextTreasureDays} 天即可解锁新宝箱，加油！
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-title">
          <span>📆</span>
          <span>{periodLabels[periodType]}</span>
        </div>
        
        <div className="period-tabs">
          {Object.entries(periodLabels).map(([key, label]) => (
            <button
              key={key}
              className={`period-tab ${periodType === key ? 'active' : ''}`}
              onClick={() => setPeriodType(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <button
          className={`checkin-btn ${calendarData?.todayChecked ? 'checked' : ''}`}
          onClick={handleCheckin}
          disabled={calendarData?.todayChecked}
        >
          {calendarData?.todayChecked ? '✓ 今日已签到' : '立即签到'}
        </button>

        {calendarData && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-card-value">{calendarData.continuousDays}</div>
              <div className="stat-card-label">连续签到</div>
            </div>
            <div className="stat-card">
              <div className="stat-card-value">{calendarData.totalDays}</div>
              <div className="stat-card-label">累计签到</div>
            </div>
          </div>
        )}

        {calendarData && (
          <Calendar
            periodType={periodType}
            currentDate={currentDate}
            calendarData={calendarData}
            onDateChange={setCurrentDate}
            onRecheck={handleRecheck}
            showToast={showToast}
          />
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div className="card">
          <div className="card-title">
            <span>🎯</span>
            <span>签到奖励</span>
          </div>
          {calendarData && <RewardsList rewards={calendarData.rewards} />}
        </div>

        <div className="card">
          <div className="card-title">
            <span>💎</span>
            <span>累计宝箱</span>
          </div>
          {calendarData && (
            <TreasuresGrid 
              treasures={calendarData.treasures}
              onClaim={handleClaimTreasure}
            />
          )}
        </div>
      </div>
    </>
  )

  return (
    <>
      <div className="header">
        <h1>📅 用户签到奖励系统</h1>
        <div className="user-info">
          <div className="user-stats">
            <div className="stat-item">
              <div className="stat-value">{user.points}</div>
              <div className="stat-label">积分</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{user.recheckCards}</div>
              <div className="stat-label">补签卡</div>
            </div>
          </div>
          <span>欢迎，{user.nickname}</span>
          <button onClick={onLogout} style={{
            padding: '8px 16px',
            border: 'none',
            borderRadius: '8px',
            background: '#f0f0f0',
            cursor: 'pointer'
          }}>退出</button>
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: '10px',
        marginBottom: '20px',
        background: 'rgba(255,255,255,0.95)',
        padding: '10px',
        borderRadius: '12px'
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              borderRadius: '10px',
              background: activeTab === tab.key 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                : 'transparent',
              color: activeTab === tab.key ? 'white' : '#666',
              fontSize: '15px',
              fontWeight: activeTab === tab.key ? 'bold' : 'normal',
              cursor: 'pointer',
              transition: 'all 0.3s'
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      <div className="checkin-container">
        {activeTab === 'checkin' && renderCheckinContent()}
        {activeTab === 'reminder' && (
          <div style={{ gridColumn: '1 / -1' }}>
            <ReminderSettings user={user} showToast={showToast} />
          </div>
        )}
        {activeTab === 'share' && (
          <div style={{ gridColumn: '1 / -1' }}>
            <SharePanel user={user} showToast={showToast} updateUser={updateUser} />
          </div>
        )}
        {activeTab === 'analysis' && (
          <div style={{ gridColumn: '1 / -1' }}>
            <AnalysisPanel user={user} showToast={showToast} />
          </div>
        )}
      </div>

      {modalData && (
        <RewardModal 
          data={modalData}
          onClose={() => setModalData(null)}
        />
      )}
    </>
  )
}

export default CheckinPage
