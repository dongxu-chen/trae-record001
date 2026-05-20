const MAX_DRIFT_THRESHOLD = 0.05
const DRIFT_HISTORY_SIZE = 30
const CORRECTION_COOLDOWN = 1.0
const SAMPLE_WINDOW_SIZE = 10

class PTS {
  constructor(timestamp, source = 'unknown') {
    this.timestamp = timestamp
    this.source = source
    this.createdAt = performance.now() / 1000
  }

  get age() {
    return performance.now() / 1000 - this.createdAt
  }
}

class DriftDetector {
  constructor(threshold = MAX_DRIFT_THRESHOLD) {
    this.threshold = threshold
    this.history = []
    this.maxHistorySize = DRIFT_HISTORY_SIZE
    this.driftTrend = 0
    this.avgDrift = 0
    this.maxDrift = 0
    this.minDrift = 0
  }

  addSample(videoPTS, audioPTS) {
    const drift = audioPTS - videoPTS
    const sample = {
      drift,
      videoPTS,
      audioPTS,
      timestamp: performance.now() / 1000,
    }
    
    this.history.push(sample)
    
    if (this.history.length > this.maxHistorySize) {
      this.history.shift()
    }
    
    this._calculateStats()
    return sample
  }

  _calculateStats() {
    if (this.history.length === 0) return
    
    const drifts = this.history.map(s => s.drift)
    this.avgDrift = drifts.reduce((a, b) => a + b, 0) / drifts.length
    this.maxDrift = Math.max(...drifts)
    this.minDrift = Math.min(...drifts)
    
    if (this.history.length >= 2) {
      const recent = this.history.slice(-SAMPLE_WINDOW_SIZE)
      const older = this.history.slice(0, SAMPLE_WINDOW_SIZE)
      
      if (older.length > 0) {
        const recentAvg = recent.reduce((a, b) => a + b.drift, 0) / recent.length
        const olderAvg = older.reduce((a, b) => a + b.drift, 0) / older.length
        this.driftTrend = recentAvg - olderAvg
      }
    }
  }

  isDrifted() {
    return Math.abs(this.avgDrift) > this.threshold
  }

  getCorrectionAmount() {
    if (!this.isDrifted()) return 0
    
    const correction = -this.avgDrift * 0.8
    
    const maxCorrection = this.threshold * 2
    return Math.max(-maxCorrection, Math.min(maxCorrection, correction))
  }

  getDriftSeverity() {
    const absDrift = Math.abs(this.avgDrift)
    if (absDrift < this.threshold * 0.5) return 'low'
    if (absDrift < this.threshold) return 'medium'
    if (absDrift < this.threshold * 2) return 'high'
    return 'critical'
  }

  reset() {
    this.history = []
    this.driftTrend = 0
    this.avgDrift = 0
    this.maxDrift = 0
    this.minDrift = 0
  }

  getStats() {
    return {
      avgDrift: this.avgDrift,
      maxDrift: this.maxDrift,
      minDrift: this.minDrift,
      driftTrend: this.driftTrend,
      severity: this.getDriftSeverity(),
      isDrifted: this.isDrifted(),
      sampleCount: this.history.length,
      threshold: this.threshold,
    }
  }
}

class PTSAligner {
  constructor(options = {}) {
    this.videoPTS = new PTS(0, 'video')
    this.audioPTS = new PTS(0, 'audio')
    this.masterPTS = new PTS(0, 'master')
    
    this.driftDetector = new DriftDetector(options.driftThreshold || MAX_DRIFT_THRESHOLD)
    
    this.lastCorrectionTime = 0
    this.correctionCooldown = options.correctionCooldown || CORRECTION_COOLDOWN
    
    this.correctionHistory = []
    this.maxCorrectionHistory = 50
    
    this.syncMode = options.syncMode || 'video_master'
    this.autoCorrect = options.autoCorrect !== false
    this.correctionMethod = options.correctionMethod || 'seek'
    
    this.videoElement = null
    this.audioElement = null
    
    this.isMonitoring = false
    this.monitorInterval = null
    this.monitorIntervalMs = options.monitorInterval || 100
    
    this.onDriftDetected = options.onDriftDetected || null
    this.onCorrectionApplied = options.onCorrectionApplied || null
    this.onSyncLost = options.onSyncLost || null
    this.onSyncRestored = options.onSyncRestored || null
    
    this._wasDrifted = false
    this._syncLostCount = 0
    this._syncRestoredCount = 0
  }

  setVideoElement(element) {
    this.videoElement = element
  }

  setAudioElement(element) {
    this.audioElement = element
  }

  setSyncMode(mode) {
    this.syncMode = mode
    this.reset()
  }

  updateVideoPTS(timestamp) {
    this.videoPTS = new PTS(timestamp, 'video')
    this._checkAlignment()
  }

  updateAudioPTS(timestamp) {
    this.audioPTS = new PTS(timestamp, 'audio')
    this._checkAlignment()
  }

  updateMasterPTS(timestamp) {
    this.masterPTS = new PTS(timestamp, 'master')
  }

  _checkAlignment() {
    if (this.videoPTS.age > 1 || this.audioPTS.age > 1) {
      return
    }
    
    const sample = this.driftDetector.addSample(
      this.videoPTS.timestamp,
      this.audioPTS.timestamp
    )
    
    const isDrifted = this.driftDetector.isDrifted()
    
    if (isDrifted && !this._wasDrifted) {
      this._wasDrifted = true
      this._syncLostCount++
      
      if (this.onDriftDetected) {
        this.onDriftDetected(this.driftDetector.getStats(), sample)
      }
      
      if (this.onSyncLost) {
        this.onSyncLost(this.driftDetector.getStats())
      }
      
      if (this.autoCorrect) {
        this._tryCorrect()
      }
    } else if (!isDrifted && this._wasDrifted) {
      this._wasDrifted = false
      this._syncRestoredCount++
      
      if (this.onSyncRestored) {
        this.onSyncRestored(this.driftDetector.getStats())
      }
    }
  }

  _tryCorrect() {
    const now = performance.now() / 1000
    if (now - this.lastCorrectionTime < this.correctionCooldown) {
      return false
    }
    
    const correction = this.driftDetector.getCorrectionAmount()
    if (correction === 0) return false
    
    let success = false
    
    switch (this.correctionMethod) {
      case 'seek':
        success = this._correctBySeek(correction)
        break
      case 'rate':
        success = this._correctByRate(correction)
        break
      case 'skip':
        success = this._correctBySkip(correction)
        break
      default:
        success = this._correctBySeek(correction)
    }
    
    if (success) {
      this.lastCorrectionTime = now
      this._recordCorrection(correction)
      
      if (this.onCorrectionApplied) {
        this.onCorrectionApplied(correction, this.correctionMethod)
      }
    }
    
    return success
  }

  _correctBySeek(correction) {
    try {
      if (this.syncMode === 'video_master') {
        if (this.audioElement) {
          const targetTime = this.videoElement.currentTime + correction
          this.audioElement.currentTime = Math.max(0, targetTime)
          return true
        }
      } else if (this.syncMode === 'audio_master') {
        if (this.videoElement) {
          const targetTime = this.audioElement.currentTime + correction
          this.videoElement.currentTime = Math.max(0, targetTime)
          return true
        }
      } else {
        if (this.videoElement && this.audioElement) {
          const targetTime = (this.videoElement.currentTime + this.audioElement.currentTime) / 2
          this.videoElement.currentTime = targetTime
          this.audioElement.currentTime = targetTime
          return true
        }
      }
    } catch (e) {
      console.error('Seek correction failed:', e)
    }
    return false
  }

  _correctByRate(correction) {
    try {
      const baseRate = 1.0
      const rateAdjustment = Math.sign(correction) * 0.05
      const adjustedRate = Math.max(0.5, Math.min(2.0, baseRate + rateAdjustment))
      
      if (this.syncMode === 'video_master' && this.audioElement) {
        this.audioElement.playbackRate = adjustedRate
        setTimeout(() => {
          if (this.audioElement) {
            this.audioElement.playbackRate = baseRate
          }
        }, 500)
        return true
      } else if (this.syncMode === 'audio_master' && this.videoElement) {
        this.videoElement.playbackRate = adjustedRate
        setTimeout(() => {
          if (this.videoElement) {
            this.videoElement.playbackRate = baseRate
          }
        }, 500)
        return true
      }
    } catch (e) {
      console.error('Rate correction failed:', e)
    }
    return false
  }

  _correctBySkip(correction) {
    try {
      if (correction > 0) {
        if (this.audioElement) {
          this.audioElement.currentTime += correction
          return true
        }
      } else {
        if (this.videoElement) {
          this.videoElement.currentTime += Math.abs(correction)
          return true
        }
      }
    } catch (e) {
      console.error('Skip correction failed:', e)
    }
    return false
  }

  _recordCorrection(amount) {
    this.correctionHistory.push({
      amount,
      method: this.correctionMethod,
      timestamp: performance.now() / 1000,
      driftAtCorrection: this.driftDetector.avgDrift,
    })
    
    if (this.correctionHistory.length > this.maxCorrectionHistory) {
      this.correctionHistory.shift()
    }
  }

  startMonitoring() {
    if (this.isMonitoring) return
    
    this.isMonitoring = true
    this.monitorInterval = setInterval(() => {
      this._monitorTick()
    }, this.monitorIntervalMs)
  }

  stopMonitoring() {
    this.isMonitoring = false
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval)
      this.monitorInterval = null
    }
  }

  _monitorTick() {
    if (this.videoElement) {
      this.updateVideoPTS(this.videoElement.currentTime)
    }
    if (this.audioElement) {
      this.updateAudioPTS(this.audioElement.currentTime)
    }
  }

  alignTracks(videoClips, audioClips) {
    const alignedClips = []
    
    for (const videoClip of videoClips) {
      const matchingAudio = audioClips.find(a => 
        Math.abs(a.startTime - videoClip.startTime) < 0.5
      )
      
      if (matchingAudio) {
        const offset = matchingAudio.startTime - videoClip.startTime
        
        if (Math.abs(offset) > 0.01) {
          alignedClips.push({
            videoClip,
            audioClip: matchingAudio,
            offset,
            needsAlignment: true,
          })
        } else {
          alignedClips.push({
            videoClip,
            audioClip: matchingAudio,
            offset: 0,
            needsAlignment: false,
          })
        }
      } else {
        alignedClips.push({
          videoClip,
          audioClip: null,
          offset: 0,
          needsAlignment: false,
        })
      }
    }
    
    return alignedClips
  }

  generateAlignmentFilter(alignedClips) {
    const filters = []
    
    for (let i = 0; i < alignedClips.length; i++) {
      const item = alignedClips[i]
      
      if (item.needsAlignment && item.audioClip) {
        const offset = item.offset
        
        if (offset > 0) {
          filters.push(
            `[${i}:a]adelay=${Math.floor(offset * 1000)}:all=1[a${i}]`
          )
        } else if (offset < 0) {
          filters.push(
            `[${i}:a]atrim=start=${Math.abs(offset)}[a${i}]`
          )
        }
      }
    }
    
    return filters
  }

  generateSyncReport() {
    const driftStats = this.driftDetector.getStats()
    
    const recentCorrections = this.correctionHistory.slice(-10)
    const totalCorrection = recentCorrections.reduce((sum, c) => sum + Math.abs(c.amount), 0)
    
    return {
      drift: driftStats,
      syncMode: this.syncMode,
      autoCorrect: this.autoCorrect,
      correctionMethod: this.correctionMethod,
      isMonitoring: this.isMonitoring,
      syncLostCount: this._syncLostCount,
      syncRestoredCount: this._syncRestoredCount,
      correctionCount: this.correctionHistory.length,
      recentCorrectionAmount: totalCorrection,
      videoPTS: this.videoPTS.timestamp,
      audioPTS: this.audioPTS.timestamp,
      currentOffset: this.audioPTS.timestamp - this.videoPTS.timestamp,
      videoPTSAge: this.videoPTS.age,
      audioPTSAge: this.audioPTS.age,
      timestamp: Date.now(),
    }
  }

  reset() {
    this.videoPTS = new PTS(0, 'video')
    this.audioPTS = new PTS(0, 'audio')
    this.masterPTS = new PTS(0, 'master')
    this.driftDetector.reset()
    this.correctionHistory = []
    this.lastCorrectionTime = 0
    this._wasDrifted = false
    this._syncLostCount = 0
    this._syncRestoredCount = 0
  }

  dispose() {
    this.stopMonitoring()
    this.reset()
    this.videoElement = null
    this.audioElement = null
    this.onDriftDetected = null
    this.onCorrectionApplied = null
    this.onSyncLost = null
    this.onSyncRestored = null
  }
}

class AudioVideoSynchronizer {
  constructor(videoElement, audioElement, options = {}) {
    this.aligner = new PTSAligner({
      ...options,
      driftThreshold: options.driftThreshold || 0.03,
      correctionCooldown: options.correctionCooldown || 0.5,
    })
    
    this.aligner.setVideoElement(videoElement)
    this.aligner.setAudioElement(audioElement)
    
    this._setupEventListeners()
    
    this.statsHistory = []
    this.maxStatsHistory = 100
    
    this.enabled = true
  }

  _setupEventListeners() {
    const video = this.aligner.videoElement
    const audio = this.aligner.audioElement
    
    if (video) {
      video.addEventListener('timeupdate', this._onVideoTimeUpdate.bind(this))
      video.addEventListener('play', this._onPlay.bind(this))
      video.addEventListener('pause', this._onPause.bind(this))
      video.addEventListener('seeked', this._onSeek.bind(this))
    }
    
    if (audio) {
      audio.addEventListener('timeupdate', this._onAudioTimeUpdate.bind(this))
    }
    
    this.aligner.onDriftDetected = (stats, sample) => {
      console.warn(`[Sync] Drift detected: ${(stats.avgDrift * 1000).toFixed(1)}ms`, stats)
    }
    
    this.aligner.onCorrectionApplied = (correction, method) => {
      console.log(`[Sync] Applied ${method} correction: ${(correction * 1000).toFixed(1)}ms`)
    }
    
    this.aligner.onSyncLost = (stats) => {
      console.warn('[Sync] Sync lost', stats)
    }
    
    this.aligner.onSyncRestored = (stats) => {
      console.log('[Sync] Sync restored', stats)
    }
  }

  _onVideoTimeUpdate(e) {
    if (!this.enabled) return
    this.aligner.updateVideoPTS(e.target.currentTime)
    this._recordStats()
  }

  _onAudioTimeUpdate(e) {
    if (!this.enabled) return
    this.aligner.updateAudioPTS(e.target.currentTime)
  }

  _onPlay() {
    if (!this.enabled) return
    this.aligner.startMonitoring()
  }

  _onPause() {
    this.aligner.stopMonitoring()
  }

  _onSeek() {
    if (!this.enabled) return
    this.aligner.reset()
  }

  _recordStats() {
    const report = this.aligner.generateSyncReport()
    this.statsHistory.push(report)
    
    if (this.statsHistory.length > this.maxStatsHistory) {
      this.statsHistory.shift()
    }
  }

  setEnabled(enabled) {
    this.enabled = enabled
    if (!enabled) {
      this.aligner.stopMonitoring()
      this.aligner.reset()
    }
  }

  getSyncQuality() {
    const report = this.aligner.generateSyncReport()
    const severity = report.drift.severity
    
    let quality = 100
    switch (severity) {
      case 'low':
        quality = 95
        break
      case 'medium':
        quality = 75
        break
      case 'high':
        quality = 50
        break
      case 'critical':
        quality = 25
        break
    }
    
    return {
      quality,
      label: this._getQualityLabel(quality),
      report,
    }
  }

  _getQualityLabel(quality) {
    if (quality >= 90) return 'excellent'
    if (quality >= 75) return 'good'
    if (quality >= 50) return 'fair'
    if (quality >= 25) return 'poor'
    return 'bad'
  }

  getAlignmentRecommendations() {
    const report = this.aligner.generateSyncReport()
    const recommendations = []
    
    if (report.drift.severity === 'high' || report.drift.severity === 'critical') {
      recommendations.push({
        type: 'critical',
        message: '音视频同步偏差较大，建议重新对齐',
        action: () => this.forceAlign(),
      })
    }
    
    if (report.syncLostCount > 5) {
      recommendations.push({
        type: 'warning',
        message: `检测到 ${report.syncLostCount} 次同步丢失，建议检查源文件`,
        action: null,
      })
    }
    
    if (report.drift.driftTrend > 0.01) {
      recommendations.push({
        type: 'info',
        message: '音频有逐渐滞后的趋势，可能需要调整采样率',
        action: null,
      })
    }
    
    return recommendations
  }

  forceAlign() {
    const video = this.aligner.videoElement
    const audio = this.aligner.audioElement
    
    if (video && audio) {
      const targetTime = video.currentTime
      audio.currentTime = targetTime
      this.aligner.reset()
      console.log('[Sync] Forced alignment to', targetTime)
    }
  }

  dispose() {
    const video = this.aligner.videoElement
    const audio = this.aligner.audioElement
    
    if (video) {
      video.removeEventListener('timeupdate', this._onVideoTimeUpdate.bind(this))
      video.removeEventListener('play', this._onPlay.bind(this))
      video.removeEventListener('pause', this._onPause.bind(this))
      video.removeEventListener('seeked', this._onSeek.bind(this))
    }
    
    if (audio) {
      audio.removeEventListener('timeupdate', this._onAudioTimeUpdate.bind(this))
    }
    
    this.aligner.dispose()
    this.statsHistory = []
  }
}

export {
  PTS,
  DriftDetector,
  PTSAligner,
  AudioVideoSynchronizer,
}

export default AudioVideoSynchronizer
