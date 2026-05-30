const crypto = require('crypto')

const CHAR_POOL = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
const CHAR_MAP = {
  '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
  '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
  'A': 'AY', 'B': 'BEE', 'C': 'SEE', 'D': 'DEE', 'E': 'EE',
  'F': 'EF', 'G': 'GEE', 'H': 'AITCH', 'J': 'JAY', 'K': 'KAY',
  'L': 'ELL', 'M': 'EM', 'N': 'EN', 'P': 'PEE', 'Q': 'CUE',
  'R': 'ARE', 'S': 'ESS', 'T': 'TEE', 'U': 'YOU', 'V': 'VEE',
  'W': 'DOUBLE YOU', 'X': 'EX', 'Y': 'WHY', 'Z': 'ZED',
}

const PHONEME_MAP = {
  'A': { f1: 800, f2: 1200, dur: 0.25 },
  'B': { f1: 300, f2: 1500, dur: 0.15 },
  'C': { f1: 2500, f2: 4500, dur: 0.2 },
  'D': { f1: 300, f2: 1600, dur: 0.15 },
  'E': { f1: 500, f2: 2500, dur: 0.25 },
  'F': { f1: 4000, f2: 6000, dur: 0.18 },
  'G': { f1: 300, f2: 1800, dur: 0.15 },
  'H': { f1: 600, f2: 1400, dur: 0.1 },
  'I': { f1: 400, f2: 2700, dur: 0.2 },
  'J': { f1: 2500, f2: 5000, dur: 0.2 },
  'K': { f1: 2500, f2: 4500, dur: 0.15 },
  'L': { f1: 400, f2: 1200, dur: 0.2 },
  'M': { f1: 300, f2: 1200, dur: 0.2 },
  'N': { f1: 300, f2: 1600, dur: 0.18 },
  'O': { f1: 500, f2: 900, dur: 0.25 },
  'P': { f1: 300, f2: 1500, dur: 0.15 },
  'Q': { f1: 2500, f2: 4500, dur: 0.2 },
  'R': { f1: 400, f2: 1400, dur: 0.18 },
  'S': { f1: 4000, f2: 6500, dur: 0.2 },
  'T': { f1: 2500, f2: 5000, dur: 0.12 },
  'U': { f1: 350, f2: 800, dur: 0.25 },
  'V': { f1: 300, f2: 1500, dur: 0.18 },
  'W': { f1: 400, f2: 800, dur: 0.2 },
  'X': { f1: 2500, f2: 5000, dur: 0.2 },
  'Y': { f1: 400, f2: 2000, dur: 0.2 },
  'Z': { f1: 3500, f2: 6000, dur: 0.2 },
  '0': { f1: 500, f2: 900, dur: 0.3 },
  '1': { f1: 400, f2: 2000, dur: 0.25 },
  '2': { f1: 500, f2: 1500, dur: 0.25 },
  '3': { f1: 500, f2: 2500, dur: 0.25 },
  '4': { f1: 400, f2: 1800, dur: 0.25 },
  '5': { f1: 500, f2: 1200, dur: 0.25 },
  '6': { f1: 400, f2: 1400, dur: 0.25 },
  '7': { f1: 500, f2: 2000, dur: 0.25 },
  '8': { f1: 500, f2: 1100, dur: 0.3 },
  '9': { f1: 400, f2: 2500, dur: 0.25 },
}

class VoiceCaptchaService {
  constructor() {
    this.sampleRate = 22050
    this.charDuration = 0.35
    this.charGap = 0.2
    this.prefixGap = 0.3

    this.difficultySettings = {
      easy: {
        codeLength: 4,
        useNumbersOnly: true,
        charGap: 0.3,
      },
      medium: {
        codeLength: 5,
        useNumbersOnly: false,
        charGap: 0.2,
      },
      hard: {
        codeLength: 7,
        useNumbersOnly: false,
        charGap: 0.15,
      },
    }
  }

  generate(difficulty = 'medium') {
    const settings = this.difficultySettings[difficulty] || this.difficultySettings.medium
    const pool = settings.useNumbersOnly ? '0123456789' : CHAR_POOL

    let code = ''
    for (let i = 0; i < settings.codeLength; i++) {
      code += pool[crypto.randomInt(0, pool.length)]
    }

    const chars = code.split('').map((char, index) => ({
      char,
      x: 20 + index * 28,
      y: 45,
      rotateAngle: crypto.randomInt(-25, 26) / 100,
      color: '#ffffff',
      font: 'bold 32px Arial',
    }))

    const spokenText = code.split('').map(c => CHAR_MAP[c] || c).join(', ')

    return {
      code,
      chars,
      width: 200,
      height: 80,
      gradientColors: ['#f093fb', '#f5576c'],
      spokenText,
      codeLength: settings.codeLength,
      difficulty,
      charGap: settings.charGap,
    }
  }

  async generateVoice(code) {
    const totalDuration = this.prefixGap + code.length * (this.charDuration + this.charGap) + 0.3
    const numSamples = Math.floor(this.sampleRate * totalDuration)
    const buffer = Buffer.alloc(44 + numSamples * 2)

    this._writeWavHeader(buffer, numSamples)

    for (let i = 0; i < numSamples; i++) {
      const t = i / this.sampleRate
      const sample = this._generateSample(t, code)
      const clampedSample = Math.max(-1, Math.min(1, sample))
      buffer.writeInt16LE(Math.floor(clampedSample * 32767), 44 + i * 2)
    }

    return buffer
  }

  _generateSample(t, code) {
    let sample = 0
    const charStart = this.prefixGap

    for (let i = 0; i < code.length; i++) {
      const c = code[i]
      const startT = charStart + i * (this.charDuration + this.charGap)
      const endT = startT + this.charDuration

      if (t >= startT && t < endT) {
        const localT = (t - startT) / this.charDuration
        const envelope = this._adsrEnvelope(localT)
        sample += this._synthesizeChar(c, t, startT) * envelope
      }

      const gapStart = endT
      const gapEnd = startT + this.charDuration + this.charGap
      if (t >= gapStart && t < gapEnd) {
        const gapLocal = (t - gapStart) / (gapEnd - gapStart)
        const gapEnv = Math.max(0, 1 - gapLocal * 4)
        sample += this._generateNoise() * 0.005 * gapEnv
      }
    }

    return sample
  }

  _synthesizeChar(char, globalT, charStartT) {
    const phoneme = PHONEME_MAP[char]
    if (!phoneme) return this._generateNoise() * 0.1

    const localT = globalT - charStartT
    const vibrato = Math.sin(2 * Math.PI * 5 * localT) * 3

    let sample = 0

    sample += Math.sin(2 * Math.PI * (phoneme.f1 + vibrato) * globalT) * 0.35
    sample += Math.sin(2 * Math.PI * (phoneme.f1 * 2 + vibrato) * globalT) * 0.15
    sample += Math.sin(2 * Math.PI * (phoneme.f1 * 3 + vibrato) * globalT) * 0.08

    sample += Math.sin(2 * Math.PI * (phoneme.f2 + vibrato) * globalT) * 0.2
    sample += Math.sin(2 * Math.PI * (phoneme.f2 * 2 + vibrato) * globalT) * 0.08

    const formantMod = Math.sin(2 * Math.PI * (phoneme.f2 - phoneme.f1) * globalT) * 0.1
    sample += formantMod

    const noiseAmt = char in { 'S': 1, 'F': 1, 'X': 1, 'Z': 1, 'C': 1, 'T': 1 } ? 0.12 : 0.02
    sample += this._generateNoise() * noiseAmt

    return sample
  }

  _adsrEnvelope(t) {
    const attack = 0.08
    const decay = 0.1
    const sustain = 0.75
    const release = 0.15

    if (t < attack) {
      return t / attack
    } else if (t < attack + decay) {
      const decayT = (t - attack) / decay
      return 1 - (1 - sustain) * decayT
    } else if (t < 1 - release) {
      return sustain
    } else {
      const releaseT = (t - (1 - release)) / release
      return sustain * (1 - releaseT)
    }
  }

  _generateNoise() {
    return (Math.random() * 2 - 1)
  }

  _writeWavHeader(buffer, numSamples) {
    buffer.write('RIFF', 0)
    buffer.writeUInt32LE(36 + numSamples * 2, 4)
    buffer.write('WAVE', 8)
    buffer.write('fmt ', 12)
    buffer.writeUInt32LE(16, 16)
    buffer.writeUInt16LE(1, 20)
    buffer.writeUInt16LE(1, 22)
    buffer.writeUInt32LE(this.sampleRate, 24)
    buffer.writeUInt32LE(this.sampleRate * 2, 28)
    buffer.writeUInt16LE(2, 32)
    buffer.writeUInt16LE(16, 34)
    buffer.write('data', 36)
    buffer.writeUInt32LE(numSamples * 2, 40)
  }

  verify(answerCode, correctCode) {
    return answerCode.toUpperCase() === correctCode.toUpperCase()
  }
}

module.exports = new VoiceCaptchaService()
