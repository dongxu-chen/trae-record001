const express = require('express')
const router = express.Router()

const captchaStore = require('../services/captchaStore')
const slideCaptchaService = require('../services/slideCaptcha')
const rotateCaptchaService = require('../services/rotateCaptcha')
const clickCaptchaService = require('../services/clickCaptcha')
const voiceCaptchaService = require('../services/voiceCaptcha')
const behaviorAnalysisService = require('../services/behaviorAnalysis')
const captchaStatsService = require('../services/captchaStats')
const { captchaRateLimit, verifyRateLimit } = require('../middleware/rateLimiter')

const getClientIp = (req) => {
  return req.ip || req.connection.remoteAddress ||
         req.headers['x-forwarded-for'] || 'unknown'
}

router.get('/slide', captchaRateLimit, async (req, res) => {
  try {
    const ip = getClientIp(req)
    const recommendedDifficulty = captchaStatsService.getRecommendedDifficulty('slide', ip)
    const difficulty = req.query.difficulty || recommendedDifficulty

    const data = await slideCaptchaService.generate(difficulty)
    const captchaId = captchaStore.generateId()

    captchaStore.save(captchaId, {
      correctX: data._correctX,
      correctY: data._correctY,
      tolerance: data.tolerance,
      difficulty: data.difficulty,
      createdAt: Date.now(),
    }, 'slide')

    captchaStatsService.recordGeneration('slide', difficulty)

    res.json({
      success: true,
      captchaId,
      originalImage: data.originalImage,
      puzzleImage: data.puzzleImage,
      puzzleY: data.puzzleY,
      puzzleSize: data.puzzleSize,
      width: data.width,
      height: data.height,
      difficulty: data.difficulty,
    })
  } catch (error) {
    console.error('Slide captcha generation error:', error)
    res.status(500).json({
      success: false,
      message: '验证码生成失败',
    })
  }
})

router.post('/slide/verify', verifyRateLimit, (req, res) => {
  const { captchaId, x, y, trajectory, attempts = 1, duration } = req.body
  const ip = getClientIp(req)

  if (captchaStore.isLocked(captchaId, ip)) {
    return res.json({
      success: false,
      message: '错误次数过多，请60秒后再试',
      locked: true,
    })
  }

  const captcha = captchaStore.get(captchaId)
  if (!captcha) {
    return res.json({
      success: false,
      message: '验证码已过期，请重新获取',
      expired: true,
    })
  }

  if (captcha.verified) {
    return res.json({
      success: false,
      message: '验证码已使用，请重新获取',
    })
  }

  const isValid = slideCaptchaService.verify(
    x, y,
    captcha.correctX, captcha.correctY,
    captcha.tolerance
  )

  const behaviorAnalysis = trajectory && trajectory.length > 0
    ? behaviorAnalysisService.analyzeTrajectory(trajectory)
    : null

  if (behaviorAnalysis) {
    captchaStatsService.recordIpRisk(ip, behaviorAnalysis.riskScore)
  }

  const difficulty = captcha.difficulty || 'medium'
  const actualDuration = duration || (Date.now() - (captcha.createdAt || Date.now()))

  if (isValid) {
    captchaStore.markVerified(captchaId)
    captchaStatsService.recordVerification(
      'slide', true, attempts, actualDuration,
      behaviorAnalysis?.riskScore, difficulty
    )

    res.json({
      success: true,
      message: '验证成功',
      behaviorScore: behaviorAnalysis?.riskScore,
      riskLevel: behaviorAnalysis?.riskLevel,
    })
  } else {
    const errorInfo = captchaStore.recordError(captchaId, ip)
    captchaStatsService.recordVerification(
      'slide', false, attempts, actualDuration,
      behaviorAnalysis?.riskScore, difficulty
    )

    res.json({
      success: false,
      message: errorInfo.locked
        ? '错误次数过多，请60秒后再试'
        : `验证失败，还剩 ${errorInfo.remaining} 次机会`,
      remaining: errorInfo.remaining,
      locked: errorInfo.locked,
      behaviorScore: behaviorAnalysis?.riskScore,
      riskLevel: behaviorAnalysis?.riskLevel,
      upgradeDifficulty: behaviorAnalysis?.riskLevel === 'high',
    })
  }
})

router.get('/rotate', captchaRateLimit, async (req, res) => {
  try {
    const ip = getClientIp(req)
    const recommendedDifficulty = captchaStatsService.getRecommendedDifficulty('rotate', ip)
    const difficulty = req.query.difficulty || recommendedDifficulty

    const data = rotateCaptchaService.generate(difficulty)
    const captchaId = captchaStore.generateId()

    captchaStore.save(captchaId, {
      correctAngle: data.targetAngle,
      tolerance: data.tolerance,
      difficulty: data.difficulty,
      createdAt: Date.now(),
    }, 'rotate')

    captchaStatsService.recordGeneration('rotate', difficulty)

    res.json({
      success: true,
      captchaId,
      imageUrl: data.imageUrl,
      size: data.size,
      difficulty: data.difficulty,
    })
  } catch (error) {
    console.error('Rotate captcha generation error:', error)
    res.status(500).json({
      success: false,
      message: '验证码生成失败',
    })
  }
})

router.post('/rotate/verify', verifyRateLimit, (req, res) => {
  const { captchaId, angle, trajectory, attempts = 1, duration, clickPattern } = req.body
  const ip = getClientIp(req)

  if (captchaStore.isLocked(captchaId, ip)) {
    return res.json({
      success: false,
      message: '错误次数过多，请60秒后再试',
      locked: true,
    })
  }

  const captcha = captchaStore.get(captchaId)
  if (!captcha) {
    return res.json({
      success: false,
      message: '验证码已过期，请重新获取',
      expired: true,
    })
  }

  if (captcha.verified) {
    return res.json({
      success: false,
      message: '验证码已使用，请重新获取',
    })
  }

  const isValid = rotateCaptchaService.verify(
    angle,
    captcha.correctAngle,
    captcha.tolerance
  )

  let behaviorRisk = null
  if (trajectory && trajectory.length > 0) {
    const analysis = behaviorAnalysisService.analyzeTrajectory(trajectory)
    behaviorRisk = analysis.riskScore
    captchaStatsService.recordIpRisk(ip, behaviorRisk)
  } else if (clickPattern && clickPattern.length > 0) {
    const analysis = behaviorAnalysisService.analyzeClickPattern(clickPattern)
    behaviorRisk = analysis.riskScore
    captchaStatsService.recordIpRisk(ip, behaviorRisk)
  }

  const difficulty = captcha.difficulty || 'medium'
  const actualDuration = duration || (Date.now() - (captcha.createdAt || Date.now()))

  if (isValid) {
    captchaStore.markVerified(captchaId)
    captchaStatsService.recordVerification(
      'rotate', true, attempts, actualDuration,
      behaviorRisk, difficulty
    )
    res.json({
      success: true,
      message: '验证成功',
      behaviorScore: behaviorRisk,
    })
  } else {
    const errorInfo = captchaStore.recordError(captchaId, ip)
    captchaStatsService.recordVerification(
      'rotate', false, attempts, actualDuration,
      behaviorRisk, difficulty
    )
    res.json({
      success: false,
      message: errorInfo.locked
        ? '错误次数过多，请60秒后再试'
        : `验证失败，还剩 ${errorInfo.remaining} 次机会`,
      remaining: errorInfo.remaining,
      locked: errorInfo.locked,
      upgradeDifficulty: behaviorRisk && behaviorRisk >= 70,
    })
  }
})

router.get('/click', captchaRateLimit, (req, res) => {
  try {
    const ip = getClientIp(req)
    const recommendedDifficulty = captchaStatsService.getRecommendedDifficulty('click', ip)
    const difficulty = req.query.difficulty || recommendedDifficulty

    const data = clickCaptchaService.generate(difficulty)
    const captchaId = captchaStore.generateId()

    captchaStore.save(captchaId, {
      correctPoints: data.correctPoints,
      tolerance: data.tolerance,
      difficulty: data.difficulty,
      createdAt: Date.now(),
    }, 'click')

    captchaStatsService.recordGeneration('click', difficulty)

    res.json({
      success: true,
      captchaId,
      chars: data.chars,
      tipText: data.tipText,
      clickCount: data.clickCount,
      width: data.width,
      height: data.height,
      gradientColors: data.gradientColors,
      difficulty: data.difficulty,
    })
  } catch (error) {
    console.error('Click captcha generation error:', error)
    res.status(500).json({
      success: false,
      message: '验证码生成失败',
    })
  }
})

router.post('/click/verify', verifyRateLimit, (req, res) => {
  const { captchaId, points, clickPattern, attempts = 1, duration } = req.body
  const ip = getClientIp(req)

  if (captchaStore.isLocked(captchaId, ip)) {
    return res.json({
      success: false,
      message: '错误次数过多，请60秒后再试',
      locked: true,
    })
  }

  const captcha = captchaStore.get(captchaId)
  if (!captcha) {
    return res.json({
      success: false,
      message: '验证码已过期，请重新获取',
      expired: true,
    })
  }

  if (captcha.verified) {
    return res.json({
      success: false,
      message: '验证码已使用，请重新获取',
    })
  }

  const isValid = clickCaptchaService.verify(
    points,
    captcha.correctPoints,
    captcha.tolerance
  )

  let behaviorRisk = null
  if (clickPattern && clickPattern.length > 0) {
    const analysis = behaviorAnalysisService.analyzeClickPattern(clickPattern)
    behaviorRisk = analysis.riskScore
    captchaStatsService.recordIpRisk(ip, behaviorRisk)
  }

  const difficulty = captcha.difficulty || 'medium'
  const actualDuration = duration || (Date.now() - (captcha.createdAt || Date.now()))

  if (isValid) {
    captchaStore.markVerified(captchaId)
    captchaStatsService.recordVerification(
      'click', true, attempts, actualDuration,
      behaviorRisk, difficulty
    )
    res.json({
      success: true,
      message: '验证成功',
      behaviorScore: behaviorRisk,
    })
  } else {
    const errorInfo = captchaStore.recordError(captchaId, ip)
    captchaStatsService.recordVerification(
      'click', false, attempts, actualDuration,
      behaviorRisk, difficulty
    )
    res.json({
      success: false,
      message: errorInfo.locked
        ? '错误次数过多，请60秒后再试'
        : `验证失败，还剩 ${errorInfo.remaining} 次机会`,
      remaining: errorInfo.remaining,
      locked: errorInfo.locked,
      upgradeDifficulty: behaviorRisk && behaviorRisk >= 70,
    })
  }
})

router.get('/voice/:captchaId', captchaRateLimit, async (req, res) => {
  const { captchaId } = req.params
  const captcha = captchaStore.get(captchaId)

  if (!captcha) {
    const voiceData = voiceCaptchaService.generate()
    const newCaptchaId = captchaStore.generateId()

    captchaStore.save(newCaptchaId, {
      code: voiceData.code,
      chars: voiceData.chars,
      spokenText: voiceData.spokenText,
      width: voiceData.width,
      height: voiceData.height,
      gradientColors: voiceData.gradientColors,
      codeLength: voiceData.codeLength,
    }, 'voice')

    try {
      const wavBuffer = await voiceCaptchaService.generateVoice(voiceData.code)
      res.set({
        'Content-Type': 'audio/wav',
        'X-Captcha-Id': newCaptchaId,
      })
      return res.send(wavBuffer)
    } catch (error) {
      return res.status(500).json({
        success: false,
        message: '语音生成失败',
      })
    }
  }

  if (captcha.type === 'voice' && captcha.code) {
    try {
      const wavBuffer = await voiceCaptchaService.generateVoice(captcha.code)
      res.set({
        'Content-Type': 'audio/wav',
        'X-Captcha-Id': captchaId,
      })
      return res.send(wavBuffer)
    } catch (error) {
      return res.status(500).json({
        success: false,
        message: '语音生成失败',
      })
    }
  }

  res.status(404).json({
    success: false,
    message: '验证码不存在',
  })
})

router.get('/voice', captchaRateLimit, async (req, res) => {
  try {
    const ip = getClientIp(req)
    const recommendedDifficulty = captchaStatsService.getRecommendedDifficulty('voice', ip)
    const difficulty = req.query.difficulty || recommendedDifficulty

    const voiceData = voiceCaptchaService.generate(difficulty)
    const captchaId = captchaStore.generateId()

    captchaStore.save(captchaId, {
      code: voiceData.code,
      chars: voiceData.chars,
      spokenText: voiceData.spokenText,
      width: voiceData.width,
      height: voiceData.height,
      gradientColors: voiceData.gradientColors,
      codeLength: voiceData.codeLength,
      difficulty: voiceData.difficulty,
      createdAt: Date.now(),
    }, 'voice')

    captchaStatsService.recordGeneration('voice', difficulty)

    res.json({
      success: true,
      captchaId,
      chars: voiceData.chars,
      width: voiceData.width,
      height: voiceData.height,
      gradientColors: voiceData.gradientColors,
      codeLength: voiceData.codeLength,
      difficulty: voiceData.difficulty,
    })
  } catch (error) {
    console.error('Voice captcha generation error:', error)
    res.status(500).json({
      success: false,
      message: '验证码生成失败',
    })
  }
})

router.post('/voice/verify', verifyRateLimit, (req, res) => {
  const { captchaId, code, attempts = 1, duration } = req.body
  const ip = getClientIp(req)

  if (captchaStore.isLocked(captchaId, ip)) {
    return res.json({
      success: false,
      message: '错误次数过多，请60秒后再试',
      locked: true,
    })
  }

  const captcha = captchaStore.get(captchaId)
  if (!captcha) {
    return res.json({
      success: false,
      message: '验证码已过期，请重新获取',
      expired: true,
    })
  }

  if (captcha.verified) {
    return res.json({
      success: false,
      message: '验证码已使用，请重新获取',
    })
  }

  const isValid = voiceCaptchaService.verify(code, captcha.code)

  const difficulty = captcha.difficulty || 'medium'
  const actualDuration = duration || (Date.now() - (captcha.createdAt || Date.now()))

  if (isValid) {
    captchaStore.markVerified(captchaId)
    captchaStatsService.recordVerification(
      'voice', true, attempts, actualDuration, null, difficulty
    )
    res.json({
      success: true,
      message: '验证成功',
    })
  } else {
    const errorInfo = captchaStore.recordError(captchaId, ip)
    captchaStatsService.recordVerification(
      'voice', false, attempts, actualDuration, null, difficulty
    )
    res.json({
      success: false,
      message: errorInfo.locked
        ? '错误次数过多，请60秒后再试'
        : `验证失败，还剩 ${errorInfo.remaining} 次机会`,
      remaining: errorInfo.remaining,
      locked: errorInfo.locked,
    })
  }
})

router.get('/stats', (req, res) => {
  try {
    const { type } = req.query
    const stats = captchaStatsService.getStats(type)
    res.json({
      success: true,
      data: stats,
    })
  } catch (error) {
    console.error('Stats error:', error)
    res.status(500).json({
      success: false,
      message: '获取统计数据失败',
    })
  }
})

router.get('/behavior-analysis', (req, res) => {
  try {
    const { type } = req.query
    const stats = captchaStatsService.getStats(type)
    res.json({
      success: true,
      data: {
        riskDistribution: {
          high: stats[type]?.highRiskCount || 0,
          medium: stats[type]?.mediumRiskCount || 0,
          low: stats[type]?.lowRiskCount || 0,
        },
        highRiskIps: stats.highRiskIps || [],
      },
    })
  } catch (error) {
    console.error('Behavior analysis error:', error)
    res.status(500).json({
      success: false,
      message: '获取行为分析数据失败',
    })
  }
})

module.exports = router
