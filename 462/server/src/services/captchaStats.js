const fs = require('fs')
const path = require('path')

class CaptchaStatsService {
  constructor() {
    this.stats = {
      slide: this._createTypeStats(),
      rotate: this._createTypeStats(),
      click: this._createTypeStats(),
      voice: this._createTypeStats(),
    }
    this.hourlyStats = new Map()
    this.dailyStats = new Map()
    this.ipRiskMap = new Map()
    this.saveFilePath = path.join(__dirname, '../../data/captcha_stats.json')
    this._loadStats()
    this._setupAutoSave()
  }

  _createTypeStats() {
    return {
      total: 0,
      success: 0,
      failed: 0,
      firstTimeSuccess: 0,
      avgAttempts: 0,
      totalAttempts: 0,
      avgDuration: 0,
      totalDuration: 0,
      avgBehaviorRisk: 0,
      totalBehaviorRisk: 0,
      highRiskCount: 0,
      mediumRiskCount: 0,
      lowRiskCount: 0,
      difficultyBreakdown: {
        easy: { total: 0, success: 0, failed: 0 },
        medium: { total: 0, success: 0, failed: 0 },
        hard: { total: 0, success: 0, failed: 0 },
      },
    }
  }

  recordGeneration(type, difficulty = 'medium') {
    this._ensureType(type)
    this.stats[type].total++
    this.stats[type].difficultyBreakdown[difficulty].total++
    this._recordHourlyStat(type, 'generate')
  }

  recordVerification(type, success, attempts = 1, duration = 0, behaviorRisk = null, difficulty = 'medium') {
    this._ensureType(type)
    const stat = this.stats[type]

    if (success) {
      stat.success++
      if (attempts === 1) stat.firstTimeSuccess++
      stat.difficultyBreakdown[difficulty].success++
    } else {
      stat.failed++
      stat.difficultyBreakdown[difficulty].failed++
    }

    stat.totalAttempts += attempts
    stat.avgAttempts = stat.totalAttempts / (stat.success + stat.failed)

    if (duration > 0) {
      stat.totalDuration += duration
      stat.avgDuration = stat.totalDuration / (stat.success + stat.failed)
    }

    if (behaviorRisk !== null) {
      stat.totalBehaviorRisk += behaviorRisk
      stat.avgBehaviorRisk = stat.totalBehaviorRisk / (stat.success + stat.failed)

      if (behaviorRisk >= 70) stat.highRiskCount++
      else if (behaviorRisk >= 40) stat.mediumRiskCount++
      else stat.lowRiskCount++
    }

    this._recordHourlyStat(type, success ? 'success' : 'failed')
  }

  recordIpRisk(ip, riskScore) {
    const existing = this.ipRiskMap.get(ip) || { count: 0, totalRisk: 0, lastSeen: 0 }
    existing.count++
    existing.totalRisk += riskScore
    existing.lastSeen = Date.now()
    existing.avgRisk = existing.totalRisk / existing.count
    this.ipRiskMap.set(ip, existing)
  }

  getIpRisk(ip) {
    const record = this.ipRiskMap.get(ip)
    if (!record) return { risk: 0, count: 0, avgRisk: 0 }
    return record
  }

  getStats(type = null) {
    if (type) {
      return this._enrichStats(this.stats[type], type)
    }

    const result = {}
    for (const t of Object.keys(this.stats)) {
      result[t] = this._enrichStats(this.stats[t], t)
    }

    result.overall = this._getOverallStats()
    result.hourly = this._getRecentHourlyStats()
    result.highRiskIps = this._getHighRiskIps()

    return result
  }

  _enrichStats(stat, type) {
    const total = stat.success + stat.failed

    return {
      ...stat,
      successRate: total > 0 ? (stat.success / total * 100).toFixed(2) + '%' : '0%',
      failureRate: total > 0 ? (stat.failed / total * 100).toFixed(2) + '%' : '0%',
      firstTimeSuccessRate: stat.success > 0
        ? (stat.firstTimeSuccess / stat.success * 100).toFixed(2) + '%'
        : '0%',
      avgDuration: Math.round(stat.avgDuration) + 'ms',
      crackRisk: this._calculateCrackRisk(stat),
      difficultyPassRates: this._getDifficultyPassRates(stat.difficultyBreakdown),
    }
  }

  _calculateCrackRisk(stat) {
    const total = stat.success + stat.failed
    if (total < 50) return 'insufficient_data'

    const successRate = stat.success / total
    const firstTimeRate = stat.success > 0 ? stat.firstTimeSuccess / stat.success : 0
    const highRiskRatio = total > 0 ? stat.highRiskCount / total : 0

    let risk = 0
    if (successRate > 0.85) risk += 30
    if (firstTimeRate > 0.8) risk += 30
    if (highRiskRatio > 0.3) risk += 40

    if (risk >= 70) return 'high'
    if (risk >= 40) return 'medium'
    return 'low'
  }

  _getDifficultyPassRates(breakdown) {
    const result = {}
    for (const diff of ['easy', 'medium', 'hard']) {
      const b = breakdown[diff]
      const total = b.success + b.failed
      result[diff] = {
        attempts: b.total,
        passRate: total > 0 ? (b.success / total * 100).toFixed(2) + '%' : 'N/A',
      }
    }
    return result
  }

  _getOverallStats() {
    const allTypes = Object.values(this.stats)
    const total = allTypes.reduce((sum, s) => sum + s.success + s.failed, 0)
    const totalSuccess = allTypes.reduce((sum, s) => sum + s.success, 0)
    const totalFailed = allTypes.reduce((sum, s) => sum + s.failed, 0)

    return {
      totalVerifications: total,
      totalSuccess,
      totalFailed,
      overallSuccessRate: total > 0 ? (totalSuccess / total * 100).toFixed(2) + '%' : '0%',
      types: Object.keys(this.stats),
    }
  }

  _recordHourlyStat(type, action) {
    const now = Date.now()
    const hourKey = Math.floor(now / 3600000)
    const hourData = this.hourlyStats.get(hourKey) || this._createHourlyStats()

    if (!hourData.types[type]) {
      hourData.types[type] = { generate: 0, success: 0, failed: 0 }
    }
    hourData.types[type][action]++
    hourData.total[action]++

    this.hourlyStats.set(hourKey, hourData)
    this._cleanOldHourlyStats()
  }

  _createHourlyStats() {
    return {
      timestamp: Date.now(),
      total: { generate: 0, success: 0, failed: 0 },
      types: {},
    }
  }

  _cleanOldHourlyStats() {
    const cutoff = Math.floor(Date.now() / 3600000) - 48
    for (const key of this.hourlyStats.keys()) {
      if (key < cutoff) {
        this.hourlyStats.delete(key)
      }
    }
  }

  _getRecentHourlyStats() {
    const hours = Array.from(this.hourlyStats.entries())
      .sort((a, b) => b[0] - a[0])
      .slice(0, 24)
      .map(([key, data]) => ({
        hour: new Date(key * 3600000).toLocaleString('zh-CN', { hour: '2-digit', month: '2-digit', day: '2-digit' }),
        ...data,
      }))
    return hours
  }

  _getHighRiskIps() {
    return Array.from(this.ipRiskMap.entries())
      .filter(([_, data]) => data.avgRisk >= 50 && data.count >= 3)
      .sort((a, b) => b[1].avgRisk - a[1].avgRisk)
      .slice(0, 10)
      .map(([ip, data]) => ({
        ip,
        riskScore: Math.round(data.avgRisk),
        attempts: data.count,
        lastSeen: new Date(data.lastSeen).toLocaleString('zh-CN'),
      }))
  }

  _ensureType(type) {
    if (!this.stats[type]) {
      this.stats[type] = this._createTypeStats()
    }
  }

  _setupAutoSave() {
    setInterval(() => this._saveStats(), 60000)
  }

  _saveStats() {
    try {
      const dir = path.dirname(this.saveFilePath)
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true })
      }

      const data = {
        stats: this.stats,
        hourlyStats: Object.fromEntries(this.hourlyStats),
        ipRiskMap: Object.fromEntries(this.ipRiskMap),
        savedAt: Date.now(),
      }

      fs.writeFileSync(this.saveFilePath, JSON.stringify(data, null, 2))
    } catch (e) {
      console.warn('Failed to save captcha stats:', e.message)
    }
  }

  _loadStats() {
    try {
      if (fs.existsSync(this.saveFilePath)) {
        const data = JSON.parse(fs.readFileSync(this.saveFilePath, 'utf8'))
        if (data.stats) {
          Object.assign(this.stats, data.stats)
        }
        if (data.hourlyStats) {
          this.hourlyStats = new Map(Object.entries(data.hourlyStats))
        }
        if (data.ipRiskMap) {
          this.ipRiskMap = new Map(Object.entries(data.ipRiskMap))
        }
      }
    } catch (e) {
      console.warn('Failed to load captcha stats:', e.message)
    }
  }

  getRecommendedDifficulty(type, ip) {
    const ipRisk = this.getIpRisk(ip)
    let baseRisk = ipRisk.avgRisk || 0

    const stat = this.stats[type]
    if (stat) {
      const total = stat.success + stat.failed
      if (total > 100) {
        const successRate = stat.success / total
        if (successRate > 0.9) baseRisk += 20
        else if (successRate < 0.5) baseRisk -= 10
      }
    }

    if (baseRisk >= 60) return 'hard'
    if (baseRisk >= 30) return 'medium'
    return 'easy'
  }
}

module.exports = new CaptchaStatsService()
