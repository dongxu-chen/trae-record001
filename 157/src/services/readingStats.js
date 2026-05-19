class ReadingStatsService {
  constructor() {
    this.stats = {
      totalPages: 0,
      totalTime: 0,
      daysRead: new Set(),
      currentStreak: 0,
      longestStreak: 0,
      lastReadDate: null,
      startTime: null,
      pagesToday: 0,
      checkInHistory: []
    }
    this.checkInRewards = [
      { day: 1, reward: '新手徽章' },
      { day: 3, reward: '坚持3天' },
      { day: 7, reward: '一周达人' },
      { day: 14, reward: '两周大师' },
      { day: 30, reward: '月度冠军' }
    ]
  }

  init() {
    this.loadStats()
    this.startSession()
    console.log('阅读统计服务初始化完成')
    return this.stats
  }

  loadStats() {
    try {
      const data = localStorage.getItem('comic_reading_stats')
      if (data) {
        const saved = JSON.parse(data)
        this.stats = {
          ...this.stats,
          ...saved,
          daysRead: new Set(saved.daysRead || []),
          checkInHistory: saved.checkInHistory || []
        }
      }
      this.calculateStreak()
    } catch (e) {
      console.error('加载阅读统计失败:', e)
    }
  }

  saveStats() {
    try {
      const toSave = {
        ...this.stats,
        daysRead: Array.from(this.stats.daysRead)
      }
      localStorage.setItem('comic_reading_stats', JSON.stringify(toSave))
    } catch (e) {
      console.error('保存阅读统计失败:', e)
    }
  }

  startSession() {
    this.stats.startTime = Date.now()
  }

  endSession() {
    if (this.stats.startTime) {
      const elapsed = Date.now() - this.stats.startTime
      this.stats.totalTime += elapsed
      this.stats.startTime = null
      this.saveStats()
    }
  }

  recordPageRead(pageNum) {
    this.stats.totalPages++
    
    const today = this.getTodayString()
    if (!this.stats.daysRead.has(today)) {
      this.stats.daysRead.add(today)
      this.stats.pagesToday = 0
    }
    this.stats.pagesToday++
    
    this.stats.lastReadDate = today
    this.calculateStreak()
    this.saveStats()
  }

  getTodayString() {
    return new Date().toISOString().split('T')[0]
  }

  calculateStreak() {
    const today = this.getTodayString()
    const sortedDays = Array.from(this.stats.daysRead).sort().reverse()
    
    if (sortedDays.length === 0) {
      this.stats.currentStreak = 0
      return
    }

    let streak = 0
    let checkDate = new Date(today)
    
    for (const day of sortedDays) {
      const dayDate = new Date(day)
      const diffDays = Math.floor((checkDate - dayDate) / (1000 * 60 * 60 * 24))
      
      if (diffDays <= 1) {
        streak++
        checkDate = dayDate
      } else {
        break
      }
    }

    this.stats.currentStreak = streak
    this.stats.longestStreak = Math.max(this.stats.longestStreak, streak)
  }

  checkIn() {
    const today = this.getTodayString()
    
    if (this.hasCheckedInToday()) {
      return { success: false, message: '今日已签到' }
    }

    this.stats.checkInHistory.push({
      date: today,
      timestamp: Date.now()
    })
    
    this.stats.daysRead.add(today)
    this.calculateStreak()
    
    const reward = this.getCheckInReward(this.stats.currentStreak)
    this.saveStats()
    
    return {
      success: true,
      streak: this.stats.currentStreak,
      reward,
      message: reward ? `恭喜获得：${reward}` : '签到成功'
    }
  }

  hasCheckedInToday() {
    const today = this.getTodayString()
    return this.stats.checkInHistory.some(item => item.date === today)
  }

  getCheckInReward(streak) {
    const reward = this.checkInRewards.find(r => r.day === streak)
    return reward ? reward.reward : null
  }

  getNextReward() {
    const current = this.stats.currentStreak
    const nextReward = this.checkInRewards.find(r => r.day > current)
    if (nextReward) {
      return {
        daysLeft: nextReward.day - current,
        reward: nextReward.reward
      }
    }
    return null
  }

  getStats() {
    return {
      totalPages: this.stats.totalPages,
      totalTime: Math.round(this.stats.totalTime / 1000 / 60),
      daysRead: this.stats.daysRead.size,
      currentStreak: this.stats.currentStreak,
      longestStreak: this.stats.longestStreak,
      pagesToday: this.stats.pagesToday,
      checkedInToday: this.hasCheckedInToday()
    }
  }

  getWeeklyProgress() {
    const weekData = []
    const today = new Date()
    
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today)
      date.setDate(date.getDate() - i)
      const dateStr = date.toISOString().split('T')[0]
      
      weekData.push({
        date: dateStr,
        weekday: ['日', '一', '二', '三', '四', '五', '六'][date.getDay()],
        read: this.stats.daysRead.has(dateStr),
        checkedIn: this.stats.checkInHistory.some(c => c.date === dateStr)
      })
    }
    
    return weekData
  }

  resetStats() {
    this.stats = {
      totalPages: 0,
      totalTime: 0,
      daysRead: new Set(),
      currentStreak: 0,
      longestStreak: 0,
      lastReadDate: null,
      startTime: Date.now(),
      pagesToday: 0,
      checkInHistory: []
    }
    this.saveStats()
  }
}

export const readingStatsService = new ReadingStatsService()
export default readingStatsService
