export interface WaveformLevel {
  level: number
  samplesPerPixel: number
  min: Float32Array
  max: Float32Array
  length: number
}

export interface PyramidCache {
  id: string
  levels: WaveformLevel[]
  duration: number
  sampleRate: number
  originalData: Float32Array | null
  baseLevelPixels: number
}

const PYRAMID_LEVELS = [
  { level: 0, pixelsPerSecond: 200 },
  { level: 1, pixelsPerSecond: 100 },
  { level: 2, pixelsPerSecond: 50 },
  { level: 3, pixelsPerSecond: 25 },
  { level: 4, pixelsPerSecond: 10 },
  { level: 5, pixelsPerSecond: 5 },
  { level: 6, pixelsPerSecond: 2 },
  { level: 7, pixelsPerSecond: 1 },
]

export class WaveformPyramid {
  private cache: Map<string, PyramidCache> = new Map()
  private audioContext: AudioContext | null = null

  setAudioContext(ctx: AudioContext) {
    this.audioContext = ctx
  }

  private async decodeAudio(file: File): Promise<AudioBuffer> {
    if (!this.audioContext) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.audioContext = new AudioContextClass()
    }
    const arrayBuffer = await file.arrayBuffer()
    return await this.audioContext.decodeAudioData(arrayBuffer.slice(0))
  }

  private getMonoChannelData(buffer: AudioBuffer): Float32Array {
    if (buffer.numberOfChannels === 1) {
      return buffer.getChannelData(0)
    }
    const left = buffer.getChannelData(0)
    const right = buffer.getChannelData(1)
    const mono = new Float32Array(left.length)
    for (let i = 0; i < left.length; i++) {
      mono[i] = (left[i] + right[i]) * 0.5
    }
    return mono
  }

  private buildLevel(
    sourceData: Float32Array,
    sourceSampleRate: number,
    targetSamplesPerPixel: number,
    level: number
  ): WaveformLevel {
    const samplesPerPixel = targetSamplesPerPixel
    const totalPixels = Math.ceil(sourceData.length / samplesPerPixel)

    const min = new Float32Array(totalPixels)
    const max = new Float32Array(totalPixels)

    for (let i = 0; i < totalPixels; i++) {
      const startIdx = i * samplesPerPixel
      const endIdx = Math.min(startIdx + samplesPerPixel, sourceData.length)

      let pixelMin = Infinity
      let pixelMax = -Infinity

      for (let j = startIdx; j < endIdx; j++) {
        const val = sourceData[j]
        if (val < pixelMin) pixelMin = val
        if (val > pixelMax) pixelMax = val
      }

      min[i] = isFinite(pixelMin) ? pixelMin : 0
      max[i] = isFinite(pixelMax) ? pixelMax : 0
    }

    return {
      level,
      samplesPerPixel,
      min,
      max,
      length: totalPixels,
    }
  }

  async buildPyramid(file: File, fileId: string): Promise<PyramidCache> {
    const audioBuffer = await this.decodeAudio(file)
    const monoData = this.getMonoChannelData(audioBuffer)
    const sampleRate = audioBuffer.sampleRate
    const duration = audioBuffer.duration

    const basePixelsPerSecond = PYRAMID_LEVELS[0].pixelsPerSecond
    const baseSamplesPerPixel = Math.floor(sampleRate / basePixelsPerSecond)

    const levels: WaveformLevel[] = []

    for (const levelConfig of PYRAMID_LEVELS) {
      const targetSamplesPerPixel = Math.floor(sampleRate / levelConfig.pixelsPerSecond)
      const level = this.buildLevel(monoData, sampleRate, targetSamplesPerPixel, levelConfig.level)
      levels.push(level)
    }

    const cache: PyramidCache = {
      id: fileId,
      levels,
      duration,
      sampleRate,
      originalData: monoData,
      baseLevelPixels: levels[0].length,
    }

    this.cache.set(fileId, cache)
    return cache
  }

  getCache(fileId: string): PyramidCache | undefined {
    return this.cache.get(fileId)
  }

  getOptimalLevel(fileId: string, pixelsPerSecond: number): WaveformLevel | null {
    const cache = this.cache.get(fileId)
    if (!cache) return null

    let optimalLevel = cache.levels[cache.levels.length - 1]
    let minDiff = Infinity

    for (const level of cache.levels) {
      const levelPixelsPerSecond = cache.sampleRate / level.samplesPerPixel
      const diff = Math.abs(levelPixelsPerSecond - pixelsPerSecond)
      if (diff < minDiff) {
        minDiff = diff
        optimalLevel = level
      }
    }

    return optimalLevel
  }

  getWaveformDataForRange(
    fileId: string,
    startTime: number,
    endTime: number,
    pixelsPerSecond: number
  ): { min: Float32Array; max: Float32Array; length: number } | null {
    const cache = this.cache.get(fileId)
    if (!cache) return null

    const level = this.getOptimalLevel(fileId, pixelsPerSecond)
    if (!level) return null

    const levelPixelsPerSecond = cache.sampleRate / level.samplesPerPixel
    const startPixel = Math.floor(startTime * levelPixelsPerSecond)
    const endPixel = Math.ceil(endTime * levelPixelsPerSecond)

    const safeStart = Math.max(0, startPixel)
    const safeEnd = Math.min(level.length, endPixel)
    const length = safeEnd - safeStart

    if (length <= 0) {
      return { min: new Float32Array(), max: new Float32Array(), length: 0 }
    }

    return {
      min: level.min.subarray(safeStart, safeEnd),
      max: level.max.subarray(safeStart, safeEnd),
      length,
    }
  }

  renderToCanvas(
    fileId: string,
    canvas: HTMLCanvasElement,
    startTime: number,
    endTime: number,
    color: string,
    backgroundColor?: string
  ): boolean {
    const cache = this.cache.get(fileId)
    if (!cache) return false

    const width = canvas.width
    const height = canvas.height
    const ctx = canvas.getContext('2d')
    if (!ctx) return false

    const pixelsPerSecond = width / (endTime - startTime)
    const level = this.getOptimalLevel(fileId, pixelsPerSecond)
    if (!level) return false

    if (backgroundColor) {
      ctx.fillStyle = backgroundColor
      ctx.fillRect(0, 0, width, height)
    } else {
      ctx.clearRect(0, 0, width, height)
    }

    const levelPixelsPerSecond = cache.sampleRate / level.samplesPerPixel
    const startPixel = Math.floor(startTime * levelPixelsPerSecond)
    const endPixel = Math.ceil(endTime * levelPixelsPerSecond)
    const rangeLength = endPixel - startPixel

    ctx.fillStyle = color
    const centerY = height / 2
    const amplitude = height / 2 - 2

    for (let x = 0; x < width; x++) {
      const t = x / width
      const levelPixel = Math.floor(startPixel + t * rangeLength)

      if (levelPixel >= 0 && levelPixel < level.length) {
        const minVal = level.min[levelPixel]
        const maxVal = level.max[levelPixel]

        const yMin = centerY - maxVal * amplitude
        const yMax = centerY - minVal * amplitude
        const barHeight = Math.max(1, yMax - yMin)

        ctx.fillRect(x, yMin, 1, barHeight)
      }
    }

    return true
  }

  dispose(fileId?: string) {
    if (fileId) {
      this.cache.delete(fileId)
    } else {
      this.cache.clear()
    }
  }
}

export const waveformPyramid = new WaveformPyramid()
