import { useState, useEffect, useRef } from 'react'
import Countdown from '../components/Countdown'
import useLocalStorage from '../hooks/useLocalStorage'
import { notify, canSendNotification } from '../utils/notify'
import { addSession, getCurrentUser } from '../utils/sync'

const TIMER_MODES = {
  WORK: { key: 'work', label: '专注时间', defaultTime: 25 * 60, color: '#ff6b6b' },
  SHORT_BREAK: { key: 'shortBreak', label: '短休息', defaultTime: 5 * 60, color: '#4ecdc4' },
  LONG_BREAK: { key: 'longBreak', label: '长休息', defaultTime: 15 * 60, color: '#45b7d1' }
}

function Timer() {
  const [settings, setSettings] = useLocalStorage('pomodoro_settings', {
    workDuration: 25,
    shortBreakDuration: 5,
    longBreakDuration: 15,
    longBreakInterval: 4,
    autoStartBreaks: true,
    autoStartPomodoros: false,
    notificationsEnabled: true,
    soundEnabled: true
  })

  const [stats, setStats] = useLocalStorage('pomodoro_stats', {
    totalPomodoros: 0,
    todayPomodoros: 0,
    lastSessionDate: null,
    totalFocusMinutes: 0
  })

  const [currentMode, setCurrentMode] = useState(TIMER_MODES.WORK)
  const [isRunning, setIsRunning] = useState(false)
  const [pomodoroCount, setPomodoroCount] = useState(0)
  const [sessionStartTime, setSessionStartTime] = useState(null)
  const [actualDuration, setActualDuration] = useState(0)
  const autoStartTimerRef = useRef(false)

  useEffect(() => {
    const today = new Date().toDateString()
    if (stats.lastSessionDate !== today) {
      setStats({
        ...stats,
        todayPomodoros: 0,
        lastSessionDate: today
      })
    }
  }, [])

  const getDuration = (mode) => {
    switch (mode.key) {
      case 'work':
        return settings.workDuration * 60
      case 'shortBreak':
        return settings.shortBreakDuration * 60
      case 'longBreak':
        return settings.longBreakDuration * 60
      default:
        return mode.defaultTime
    }
  }

  const recordSession = async (type, duration, completed = true) => {
    const session = {
      type,
      duration,
      completed,
      scheduledDuration: getDuration(currentMode === TIMER_MODES.WORK ? TIMER_MODES.WORK : currentMode),
      userId: getCurrentUser()?.uid || null
    }
    return await addSession(session)
  }

  const handleComplete = async () => {
    setIsRunning(false)
    
    const today = new Date().toDateString()
    const currentTime = new Date()
    
    if (currentMode.key === 'work') {
      const newCount = pomodoroCount + 1
      setPomodoroCount(newCount)
      
      const scheduledDuration = settings.workDuration
      const actualFocusMinutes = sessionStartTime 
        ? Math.max(1, Math.round((currentTime - sessionStartTime) / 60000))
        : scheduledDuration
      
      setStats(prevStats => ({
        ...prevStats,
        totalPomodoros: prevStats.totalPomodoros + 1,
        todayPomodoros: prevStats.lastSessionDate === today 
          ? prevStats.todayPomodoros + 1 
          : 1,
        lastSessionDate: today,
        totalFocusMinutes: (prevStats.totalFocusMinutes || 0) + actualFocusMinutes
      }))

      await recordSession('work', actualFocusMinutes, true)

      if (settings.notificationsEnabled && canSendNotification()) {
        notify('番茄完成！', { 
          body: `专注了 ${actualFocusMinutes} 分钟，休息一下吧`,
          requireInteraction: true
        })
      }

      if (newCount % settings.longBreakInterval === 0) {
        setCurrentMode(TIMER_MODES.LONG_BREAK)
        if (settings.autoStartBreaks) {
          autoStartTimerRef.current = true
        }
      } else {
        setCurrentMode(TIMER_MODES.SHORT_BREAK)
        if (settings.autoStartBreaks) {
          autoStartTimerRef.current = true
        }
      }
    } else {
      if (settings.notificationsEnabled && canSendNotification()) {
        notify('休息结束！', { 
          body: '准备开始下一个番茄',
          requireInteraction: true
        })
      }
      setCurrentMode(TIMER_MODES.WORK)
      if (settings.autoStartPomodoros) {
        autoStartTimerRef.current = true
      }
    }

    setSessionStartTime(null)
    setActualDuration(0)
  }

  useEffect(() => {
    if (autoStartTimerRef.current) {
      setIsRunning(true)
      setSessionStartTime(new Date())
      autoStartTimerRef.current = false
    }
  }, [currentMode])

  const handleStartPause = () => {
    if (!isRunning) {
      setSessionStartTime(new Date())
    }
    setIsRunning(!isRunning)
  }

  const handleReset = async () => {
    if (isRunning && sessionStartTime) {
      const now = new Date()
      const focusMinutes = Math.round((now - sessionStartTime) / 60000)
      if (focusMinutes >= 1 && currentMode.key === 'work') {
        await recordSession('work', focusMinutes, false)
      }
    }
    setIsRunning(false)
    setSessionStartTime(null)
    setActualDuration(0)
  }

  const handleModeChange = async (mode) => {
    if (isRunning && sessionStartTime && currentMode.key === 'work') {
      const now = new Date()
      const focusMinutes = Math.max(1, Math.round((now - sessionStartTime) / 60000))
      await recordSession('work', focusMinutes, false)
    }
    setIsRunning(false)
    setSessionStartTime(null)
    setCurrentMode(mode)
  }

  const handleSkip = async () => {
    if (isRunning && sessionStartTime && currentMode.key === 'work') {
      const now = new Date()
      const focusMinutes = Math.max(1, Math.round((now - sessionStartTime) / 60000))
      await recordSession('work', focusMinutes, false)
    }
    setIsRunning(false)
    setSessionStartTime(null)
    if (currentMode.key === 'work') {
      setCurrentMode(TIMER_MODES.SHORT_BREAK)
    } else {
      setCurrentMode(TIMER_MODES.WORK)
    }
  }

  const handleTick = (timeLeft) => {
    if (sessionStartTime && currentMode.key === 'work') {
      const now = new Date()
      const minutes = Math.round((now - sessionStartTime) / 60000)
      setActualDuration(minutes)
    }
  }

  return (
    <div className="timer-page" style={{ '--accent-color': currentMode.color }}>
      <div className="timer-container">
        <h1 className="timer-title">🍅 番茄时钟</h1>
        
        <div className="mode-tabs">
          {Object.values(TIMER_MODES).map((mode) => (
            <button
              key={mode.key}
              className={`mode-tab ${currentMode.key === mode.key ? 'active' : ''}`}
              onClick={() => handleModeChange(mode)}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <Countdown
          initialTime={getDuration(currentMode)}
          isRunning={isRunning}
          onComplete={handleComplete}
          onTick={handleTick}
        />

        {currentMode.key === 'work' && actualDuration > 0 && (
          <div className="session-info">
            当前专注时长: {actualDuration} 分钟
          </div>
        )}

        <div className="timer-controls">
          <button className="control-btn reset" onClick={handleReset}>
            重置
          </button>
          <button 
            className="control-btn primary" 
            onClick={handleStartPause}
          >
            {isRunning ? '暂停' : '开始'}
          </button>
          <button className="control-btn skip" onClick={handleSkip}>
            跳过
          </button>
        </div>

        <div className="stats-info">
          <div className="stat-item">
            <span className="stat-label">今日番茄</span>
            <span className="stat-value">{stats.todayPomodoros}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">总计番茄</span>
            <span className="stat-value">{stats.totalPomodoros}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">专注时长</span>
            <span className="stat-value">{stats.totalFocusMinutes || 0} 分钟</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Timer
