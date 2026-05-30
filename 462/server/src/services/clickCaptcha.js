const CHAR_POOL = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

class ClickCaptchaService {
  constructor() {
    this.width = 350
    this.height = 200
    this.defaultCharCount = 5
    this.defaultClickCount = 3
    this.defaultTolerance = 25

    this.difficultySettings = {
      easy: {
        charCount: 4,
        clickCount: 2,
        tolerance: 35,
        rotateRange: 30,
      },
      medium: {
        charCount: 5,
        clickCount: 3,
        tolerance: 25,
        rotateRange: 60,
      },
      hard: {
        charCount: 7,
        clickCount: 4,
        tolerance: 18,
        rotateRange: 90,
      },
    }
  }

  generate(difficulty = 'medium') {
    const settings = this.difficultySettings[difficulty] || this.difficultySettings.medium
    const charCount = settings.charCount
    const clickCount = settings.clickCount
    const tolerance = settings.tolerance
    const rotateRange = settings.rotateRange
    const chars = []
    const positions = []
    const fontSize = 36
    const fonts = ['Arial', 'Georgia', 'Verdana', 'Times New Roman', 'Courier New']

    for (let i = 0; i < charCount; i++) {
      let x, y, overlap
      let attempts = 0
      do {
        overlap = false
        x = Math.floor(Math.random() * (this.width - fontSize * 2)) + fontSize
        y = Math.floor(Math.random() * (this.height - fontSize * 2)) + fontSize

        for (const pos of positions) {
          const dist = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2)
          if (dist < fontSize * 1.2) {
            overlap = true
            break
          }
        }
        attempts++
      } while (overlap && attempts < 50)

      const char = CHAR_POOL[Math.floor(Math.random() * CHAR_POOL.length)]
      const rotateAngle = (Math.random() - 0.5) * rotateRange
      const color = `hsl(${Math.random() * 360}, 70%, 60%)`
      const font = fonts[Math.floor(Math.random() * fonts.length)]

      chars.push({ char, x, y, rotateAngle, color, font })
      positions.push({ x, y })
    }

    const clickIndices = []
    while (clickIndices.length < clickCount) {
      const idx = Math.floor(Math.random() * charCount)
      if (!clickIndices.includes(idx)) {
        clickIndices.push(idx)
      }
    }

    const clickChars = clickIndices.map((idx) => chars[idx].char)
    const correctPoints = clickIndices.map((idx) => ({
      x: chars[idx].x,
      y: chars[idx].y,
      char: chars[idx].char,
    }))

    const tipText = `请依次点击: ${clickChars.join(' , ')}`

    return {
      chars,
      tipText,
      correctPoints,
      tolerance,
      width: this.width,
      height: this.height,
      clickCount,
      difficulty,
      gradientColors: ['#667eea', '#764ba2'],
    }
  }

  verify(answerPoints, correctPoints, tolerance) {
    if (answerPoints.length !== correctPoints.length) {
      return false
    }

    for (let i = 0; i < answerPoints.length; i++) {
      const dx = Math.abs(answerPoints[i].x - correctPoints[i].x)
      const dy = Math.abs(answerPoints[i].y - correctPoints[i].y)
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist > tolerance) {
        return false
      }
    }

    return true
  }
}

module.exports = new ClickCaptchaService()
