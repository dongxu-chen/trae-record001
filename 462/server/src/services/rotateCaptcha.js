const crypto = require('crypto')

class RotateCaptchaService {
  constructor() {
    this.size = 300

    this.difficultySettings = {
      easy: { tolerance: 15, size: 300 },
      medium: { tolerance: 8, size: 300 },
      hard: { tolerance: 4, size: 280 },
    }
  }

  generate(difficulty = 'medium') {
    const settings = this.difficultySettings[difficulty] || this.difficultySettings.medium
    const targetAngle = crypto.randomInt(45, 315)
    const randomSeed = crypto.randomInt(0, 100000)

    return {
      seed: randomSeed,
      targetAngle,
      tolerance: settings.tolerance,
      size: settings.size,
      difficulty,
      imageUrl: `https://picsum.photos/seed/${randomSeed}/${settings.size}/${settings.size}`,
    }
  }

  verify(answerAngle, correctAngle, tolerance) {
    let diff = Math.abs(answerAngle - correctAngle)
    if (diff > 180) {
      diff = 360 - diff
    }
    return diff <= tolerance
  }
}

module.exports = new RotateCaptchaService()
