const Jimp = require('jimp')
const crypto = require('crypto')

class SlideCaptchaService {
  constructor() {
    this.width = 400
    this.height = 200
    this.defaultPuzzleSize = 50
    this.defaultTolerance = 5

    this.difficultySettings = {
      easy: {
        puzzleSize: 60,
        tolerance: 8,
        hasBumps: false,
        noiseLevel: 'low',
      },
      medium: {
        puzzleSize: 50,
        tolerance: 5,
        hasBumps: true,
        noiseLevel: 'medium',
      },
      hard: {
        puzzleSize: 40,
        tolerance: 3,
        hasBumps: true,
        noiseLevel: 'high',
      },
    }
  }

  async generate(difficulty = 'medium') {
    const settings = this.difficultySettings[difficulty] || this.difficultySettings.medium
    const puzzleSize = settings.puzzleSize
    const tolerance = settings.tolerance

    const x = crypto.randomInt(puzzleSize + 20, this.width - puzzleSize - 20)
    const y = crypto.randomInt(puzzleSize + 20, this.height - puzzleSize - 20)

    const bgImage = await this._createBackgroundImage(settings.noiseLevel)

    const puzzlePiece = await this._extractPuzzlePiece(bgImage, x, y, puzzleSize, settings.hasBumps)

    await this._cutHoleFromBackground(bgImage, x, y, puzzleSize, settings.hasBumps)

    const originalImage = await bgImage.getBase64Async(Jimp.MIME_PNG)
    const puzzleImage = await puzzlePiece.getBase64Async(Jimp.MIME_PNG)

    return {
      originalImage,
      puzzleImage,
      _correctX: x,
      _correctY: y,
      puzzleY: y,
      puzzleSize,
      width: this.width,
      height: this.height,
      tolerance,
      difficulty,
    }
  }

  async _createBackgroundImage(noiseLevel = 'medium') {
    const image = new Jimp(this.width, this.height)

    const noiseMultiplier = { low: 0.5, medium: 1, high: 1.5 }[noiseLevel] || 1

    image.scan(0, 0, this.width, this.height, function (x, y, idx) {
      const r = 80 + Math.sin(x * 0.02) * 40 + Math.random() * 30 * noiseMultiplier | 0
      const g = 100 + Math.cos(y * 0.03) * 50 + Math.random() * 30 * noiseMultiplier | 0
      const b = 160 + Math.sin((x + y) * 0.01) * 60 + Math.random() * 20 * noiseMultiplier | 0
      this.bitmap.data[idx + 0] = r
      this.bitmap.data[idx + 1] = g
      this.bitmap.data[idx + 2] = b
      this.bitmap.data[idx + 3] = 255
    })

    const data = image.bitmap.data
    const circleCount = Math.round(5 * noiseMultiplier)
    for (let i = 0; i < circleCount; i++) {
      const cx = crypto.randomInt(30, this.width - 30)
      const cy = crypto.randomInt(30, this.height - 30)
      const radius = crypto.randomInt(15, 35)
      const hue = crypto.randomInt(0, 360)
      const color = this._hslToRgb(hue, 60, 70)

      for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
          if (dx * dx + dy * dy <= radius * radius) {
            const px = cx + dx
            const py = cy + dy
            if (px >= 0 && px < this.width && py >= 0 && py < this.height) {
              const idx = (py * this.width + px) * 4
              data[idx + 0] = data[idx + 0] * 0.7 + color.r * 0.3 | 0
              data[idx + 1] = data[idx + 1] * 0.7 + color.g * 0.3 | 0
              data[idx + 2] = data[idx + 2] * 0.7 + color.b * 0.3 | 0
            }
          }
        }
      }
    }

    const lineCount = Math.round(10 * noiseMultiplier)
    for (let i = 0; i < lineCount; i++) {
      const x1 = crypto.randomInt(0, this.width)
      const y1 = crypto.randomInt(0, this.height)
      const x2 = crypto.randomInt(0, this.width)
      const y2 = crypto.randomInt(0, this.height)
      const alpha = crypto.randomInt(30, 80)

      const steps = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1))
      for (let s = 0; s <= steps; s++) {
        const t = steps === 0 ? 0 : s / steps
        const px = Math.round(x1 + (x2 - x1) * t)
        const py = Math.round(y1 + (y2 - y1) * t)
        if (px >= 0 && px < this.width && py >= 0 && py < this.height) {
          const idx = (py * this.width + px) * 4
          data[idx + 0] = Math.min(255, data[idx + 0] + alpha)
          data[idx + 1] = Math.min(255, data[idx + 1] + alpha)
          data[idx + 2] = Math.min(255, data[idx + 2] + alpha)
        }
      }
    }

    return image
  }

  _isInsidePuzzle(px, py, size, r, hasBumps = true) {
    if (px < 0 || px >= size || py < 0 || py >= size) return false

    if (!hasBumps) {
      return true
    }

    const inTopBump = (px >= size * 0.35 - r && px <= size * 0.65 + r && py <= r * 2)
    if (inTopBump) {
      const cx = px < size * 0.5 ? size * 0.35 : size * 0.65
      const dist = Math.sqrt((px - cx) ** 2 + (py - r) ** 2)
      if (dist <= r) return true
    }

    const inRightBump = (px >= size - r * 2 && py >= size * 0.35 - r && py <= size * 0.65 + r)
    if (inRightBump) {
      const cy = py < size * 0.5 ? size * 0.35 : size * 0.65
      const dist = Math.sqrt((px - (size - r)) ** 2 + (py - cy) ** 2)
      if (dist <= r) return true
    }

    const inBody = (px >= 0 && px <= size && py >= 0 && py <= size)
    const inTopBumpsArea = py < r * 2
    const inRightBumpsArea = px > size - r * 2

    if (inBody && !inTopBumpsArea && !inRightBumpsArea) return true

    return false
  }

  async _cutHoleFromBackground(image, x, y, size, hasBumps) {
    const r = size * 0.2
    const data = image.bitmap.data
    const w = this.width

    for (let dy = -2; dy < size + 2; dy++) {
      for (let dx = -2; dx < size + 2; dx++) {
        const px = x + dx
        const py = y + dy
        if (px >= 0 && px < w && py >= 0 && py < this.height) {
          if (this._isInsidePuzzle(dx, dy, size, r, hasBumps)) {
            const isEdge = !this._isInsidePuzzle(dx - 1, dy, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx + 1, dy, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx, dy - 1, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx, dy + 1, size, r, hasBumps)

            const idx = (py * w + px) * 4
            if (isEdge) {
              data[idx + 0] = 255
              data[idx + 1] = 255
              data[idx + 2] = 255
              data[idx + 3] = 180
            } else {
              data[idx + 3] = 60
            }
          }
        }
      }
    }
  }

  async _extractPuzzlePiece(sourceImage, x, y, size, hasBumps) {
    const r = size * 0.2
    const padding = 20
    const piece = new Jimp(size + padding * 2, size + padding * 2, 0x00000000)
    const srcData = sourceImage.bitmap.data
    const dstData = piece.bitmap.data
    const srcW = this.width
    const dstW = size + padding * 2

    for (let dy = 0; dy < size; dy++) {
      for (let dx = 0; dx < size; dx++) {
        if (this._isInsidePuzzle(dx, dy, size, r, hasBumps)) {
          const srcX = x + dx
          const srcY = y + dy
          if (srcX >= 0 && srcX < srcW && srcY >= 0 && srcY < this.height) {
            const isEdge = !this._isInsidePuzzle(dx - 1, dy, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx + 1, dy, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx, dy - 1, size, r, hasBumps) ||
              !this._isInsidePuzzle(dx, dy + 1, size, r, hasBumps)

            const srcIdx = (srcY * srcW + srcX) * 4
            const dstIdx = ((dy + padding) * dstW + (dx + padding)) * 4

            if (isEdge) {
              dstData[dstIdx + 0] = 255
              dstData[dstIdx + 1] = 255
              dstData[dstIdx + 2] = 255
              dstData[dstIdx + 3] = 220
            } else {
              dstData[dstIdx + 0] = srcData[srcIdx + 0]
              dstData[dstIdx + 1] = srcData[srcIdx + 1]
              dstData[dstIdx + 2] = srcData[srcIdx + 2]
              dstData[dstIdx + 3] = 255
            }
          }
        }
      }
    }

    return piece
  }

  _hslToRgb(h, s, l) {
    h /= 360
    s /= 100
    l /= 100
    let r, g, b
    if (s === 0) {
      r = g = b = l
    } else {
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1
        if (t > 1) t -= 1
        if (t < 1 / 6) return p + (q - p) * 6 * t
        if (t < 1 / 2) return q
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6
        return p
      }
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s
      const p = 2 * l - q
      r = hue2rgb(p, q, h + 1 / 3)
      g = hue2rgb(p, q, h)
      b = hue2rgb(p, q, h - 1 / 3)
    }
    return { r: Math.round(r * 255), g: Math.round(g * 255), b: Math.round(b * 255) }
  }

  verify(answerX, answerY, correctX, correctY, tolerance) {
    const dx = Math.abs(answerX - correctX)
    const dy = Math.abs(answerY - correctY)
    return dx <= tolerance && dy <= tolerance
  }
}

module.exports = new SlideCaptchaService()
