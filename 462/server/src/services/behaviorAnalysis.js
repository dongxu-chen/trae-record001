class BehaviorAnalysisService {
  constructor() {
    this.thresholds = {
      minPoints: 5,
      maxSpeed: 80,
      minSpeed: 5,
      maxAcceleration: 50,
      minLinearity: 0.3,
      minEntropy: 0.5,
      suspiciousStraightness: 0.98,
      minDuration: 300,
    }
  }

  analyzeTrajectory(trajectory) {
    if (!trajectory || trajectory.length < this.thresholds.minPoints) {
      return {
        riskScore: 100,
        riskLevel: 'high',
        reason: 'insufficient_points',
        details: { pointCount: trajectory?.length || 0 },
      }
    }

    const metrics = this._calculateMetrics(trajectory)
    const riskScore = this._calculateRiskScore(metrics)
    const riskLevel = this._getRiskLevel(riskScore)

    return {
      riskScore,
      riskLevel,
      details: metrics,
      reasons: this._getRiskReasons(metrics, riskScore),
    }
  }

  _calculateMetrics(trajectory) {
    const n = trajectory.length
    const durations = []
    const distances = []
    const speeds = []
    const accelerations = []
    const directions = []
    const pathLength = 0

    for (let i = 1; i < n; i++) {
      const prev = trajectory[i - 1]
      const curr = trajectory[i]

      const dt = curr.t - prev.t
      const dx = curr.x - prev.x
      const dy = curr.y - prev.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      const speed = dt > 0 ? dist / dt * 1000 : 0
      const direction = Math.atan2(dy, dx)

      durations.push(dt)
      distances.push(dist)
      speeds.push(speed)
      directions.push(direction)
    }

    for (let i = 1; i < speeds.length; i++) {
      const dt = durations[i]
      const dv = speeds[i] - speeds[i - 1]
      const accel = dt > 0 ? dv / dt * 1000 : 0
      accelerations.push(accel)
    }

    const totalDuration = trajectory[n - 1].t - trajectory[0].t
    const totalDistance = distances.reduce((a, b) => a + b, 0)
    const start = trajectory[0]
    const end = trajectory[n - 1]
    const directDistance = Math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)
    const linearity = totalDistance > 0 ? directDistance / totalDistance : 1

    const avgSpeed = speeds.reduce((a, b) => a + b, 0) / speeds.length
    const maxSpeed = Math.max(...speeds)
    const minSpeed = Math.min(...speeds)
    const speedStd = this._stdDev(speeds, avgSpeed)

    const avgAcceleration = accelerations.length > 0
      ? accelerations.reduce((a, b) => a + b, 0) / accelerations.length
      : 0
    const maxAcceleration = accelerations.length > 0 ? Math.max(...accelerations.map(Math.abs)) : 0

    const directionEntropy = this._calculateDirectionEntropy(directions)
    const directionChanges = this._countDirectionChanges(directions)

    const jerkiness = this._calculateJerkiness(trajectory)

    return {
      pointCount: n,
      totalDuration,
      totalDistance,
      directDistance,
      linearity,
      avgSpeed,
      maxSpeed,
      minSpeed,
      speedStd,
      avgAcceleration,
      maxAcceleration,
      directionEntropy,
      directionChanges,
      jerkiness,
    }
  }

  _stdDev(values, mean) {
    if (values.length === 0) return 0
    const squaredDiffs = values.map(v => (v - mean) ** 2)
    return Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / values.length)
  }

  _calculateDirectionEntropy(directions) {
    if (directions.length === 0) return 0

    const bins = 16
    const binSize = (Math.PI * 2) / bins
    const counts = new Array(bins).fill(0)

    for (const dir of directions) {
      const normalized = ((dir + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2)
      const bin = Math.floor(normalized / binSize) % bins
      counts[bin]++
    }

    const total = directions.length
    let entropy = 0
    for (const count of counts) {
      if (count > 0) {
        const p = count / total
        entropy -= p * Math.log2(p)
      }
    }

    return entropy / Math.log2(bins)
  }

  _countDirectionChanges(directions) {
    if (directions.length < 2) return 0

    let changes = 0
    const threshold = Math.PI / 6

    for (let i = 1; i < directions.length; i++) {
      let diff = Math.abs(directions[i] - directions[i - 1])
      if (diff > Math.PI) diff = Math.PI * 2 - diff
      if (diff > threshold) changes++
    }

    return changes
  }

  _calculateJerkiness(trajectory) {
    if (trajectory.length < 4) return 0

    const velocities = []
    for (let i = 1; i < trajectory.length; i++) {
      const dx = trajectory[i].x - trajectory[i - 1].x
      const dy = trajectory[i].y - trajectory[i - 1].y
      const dt = trajectory[i].t - trajectory[i - 1].t
      if (dt > 0) {
        velocities.push({
          vx: dx / dt,
          vy: dy / dt,
        })
      }
    }

    const accelerations = []
    for (let i = 1; i < velocities.length; i++) {
      accelerations.push({
        ax: velocities[i].vx - velocities[i - 1].vx,
        ay: velocities[i].vy - velocities[i - 1].vy,
      })
    }

    let totalJerk = 0
    for (let i = 1; i < accelerations.length; i++) {
      const jx = accelerations[i].ax - accelerations[i - 1].ax
      const jy = accelerations[i].ay - accelerations[i - 1].ay
      totalJerk += Math.sqrt(jx * jx + jy * jy)
    }

    return accelerations.length > 1 ? totalJerk / (accelerations.length - 1) : 0
  }

  _calculateRiskScore(metrics) {
    let score = 0

    if (metrics.pointCount < 10) score += 25
    else if (metrics.pointCount < 20) score += 10

    if (metrics.totalDuration < this.thresholds.minDuration) {
      score += Math.min(30, (this.thresholds.minDuration - metrics.totalDuration) / 10)
    }

    if (metrics.maxSpeed > this.thresholds.maxSpeed) {
      score += Math.min(30, (metrics.maxSpeed - this.thresholds.maxSpeed) / 2)
    } else if (metrics.avgSpeed < this.thresholds.minSpeed) {
      score += 10
    }

    if (metrics.maxAcceleration > this.thresholds.maxAcceleration) {
      score += Math.min(25, (metrics.maxAcceleration - this.thresholds.maxAcceleration) / 2)
    }

    if (metrics.linearity > this.thresholds.suspiciousStraightness) {
      score += 20
    } else if (metrics.linearity < this.thresholds.minLinearity) {
      score += 5
    }

    if (metrics.directionEntropy < this.thresholds.minEntropy) {
      score += Math.min(20, (this.thresholds.minEntropy - metrics.directionEntropy) * 30)
    }

    if (metrics.jerkiness > 5) {
      score += Math.min(20, (metrics.jerkiness - 5) * 2)
    }

    if (metrics.directionChanges < 2) {
      score += 10
    }

    return Math.min(100, score)
  }

  _getRiskLevel(score) {
    if (score >= 70) return 'high'
    if (score >= 40) return 'medium'
    return 'low'
  }

  _getRiskReasons(metrics, score) {
    const reasons = []

    if (metrics.pointCount < 10) reasons.push('too_few_points')
    if (metrics.totalDuration < this.thresholds.minDuration) reasons.push('too_fast_completion')
    if (metrics.maxSpeed > this.thresholds.maxSpeed) reasons.push('abnormal_high_speed')
    if (metrics.maxAcceleration > this.thresholds.maxAcceleration) reasons.push('abnormal_acceleration')
    if (metrics.linearity > this.thresholds.suspiciousStraightness) reasons.push('suspicious_straight_line')
    if (metrics.directionEntropy < this.thresholds.minEntropy) reasons.push('low_direction_variety')

    return reasons
  }

  analyzeClickPattern(clicks) {
    if (!clicks || clicks.length === 0) {
      return { riskScore: 50, riskLevel: 'medium' }
    }

    const intervals = []
    for (let i = 1; i < clicks.length; i++) {
      intervals.push(clicks[i].t - clicks[i - 1].t)
    }

    if (intervals.length === 0) {
      return { riskScore: 30, riskLevel: 'low' }
    }

    const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length
    const stdInterval = this._stdDev(intervals, avgInterval)
    const cv = avgInterval > 0 ? stdInterval / avgInterval : 0

    let riskScore = 0

    if (avgInterval < 100) riskScore += 25
    if (cv < 0.2) riskScore += 25
    if (clicks.length < 3) riskScore += 10

    return {
      riskScore: Math.min(100, riskScore),
      riskLevel: this._getRiskLevel(riskScore),
      avgInterval,
      cv,
    }
  }
}

module.exports = new BehaviorAnalysisService()
