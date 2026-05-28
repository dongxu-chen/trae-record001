export interface AudioFingerprint {
  hash: string
  features: number[]
  duration: number
  sampleRate: number
}

export interface CopyrightInfo {
  title: string
  artist: string
  album?: string
  genre?: string
  year?: number
  isCopyrighted: boolean
  licenseType?: 'CC0' | 'CC-BY' | 'CC-BY-SA' | 'Royalty-Free' | 'Copyrighted' | 'Unknown'
  source?: string
  confidence: number
}

export interface RecognitionResult {
  fingerprint: AudioFingerprint
  matches: CopyrightInfo[]
  bestMatch: CopyrightInfo | null
  analyzed: boolean
}

export class AudioFingerprintService {
  private audioContext: AudioContext | null = null
  private readonly FFT_SIZE = 4096
  private readonly HOP_SIZE = 2048
  private readonly NUM_BANDS = 33
  private readonly BAND_FREQ_START = 300
  private readonly BAND_FREQ_END = 2000

  async generateFingerprint(
    file: File,
    onProgress?: (progress: number, stage: string) => void
  ): Promise<AudioFingerprint> {
    onProgress?.(0, '解码音频...')

    const audioBuffer = await this.decodeAudio(file)
    const sampleRate = audioBuffer.sampleRate
    const monoData = this.getMonoData(audioBuffer)

    onProgress?.(0.3, '提取特征...')

    const features = this.extractFeatures(monoData, sampleRate)
    const hash = this.computeHash(features)

    onProgress?.(1, '完成')

    return {
      hash,
      features,
      duration: audioBuffer.duration,
      sampleRate,
    }
  }

  async recognize(
    file: File,
    onProgress?: (progress: number, stage: string) => void
  ): Promise<RecognitionResult> {
    onProgress?.(0, '生成指纹...')

    const fingerprint = await this.generateFingerprint(file, (p, s) => {
      onProgress?.(p * 0.6, s)
    })

    onProgress?.(0.6, '匹配版权库...')

    const matches = await this.matchFingerprint(fingerprint)

    onProgress?.(0.9, '分析结果...')

    const bestMatch = matches.length > 0
      ? matches.reduce((best, current) =>
          current.confidence > best.confidence ? current : best
        )
      : null

    onProgress?.(1, '完成')

    return {
      fingerprint,
      matches,
      bestMatch,
      analyzed: true,
    }
  }

  computeSimilarity(hash1: string, hash2: string): number {
    if (hash1.length !== hash2.length) return 0

    let matches = 0
    for (let i = 0; i < hash1.length; i++) {
      if (hash1[i] === hash2[i]) {
        matches++
      }
    }

    return matches / hash1.length
  }

  private extractFeatures(data: Float32Array, sampleRate: number): number[] {
    const hopSize = this.HOP_SIZE
    const numFrames = Math.floor((data.length - this.FFT_SIZE) / hopSize)
    const bandCenters = this.getLogBandCenters()

    const frameFeatures: number[] = []

    for (let frame = 0; frame < numFrames; frame += 2) {
      const startSample = frame * hopSize
      const frameData = data.slice(startSample, startSample + this.FFT_SIZE)

      const windowed = this.applyHannWindow(frameData)
      const spectrum = this.computePowerSpectrum(windowed)

      const bandEnergies = this.computeBandEnergies(spectrum, sampleRate, bandCenters)
      const significantPeaks = this.findSignificantPeaks(bandEnergies)

      frameFeatures.push(...significantPeaks)
    }

    return frameFeatures
  }

  private computeHash(features: number[]): string {
    const quantized = features.map((f) => Math.round(f * 1000))
    const hashParts: string[] = []

    for (let i = 0; i < quantized.length; i += 4) {
      const chunk = quantized.slice(i, i + 4)
      const value = chunk.reduce((acc, val, idx) =>
        acc ^ (val << (idx * 4))
      , 0)
      hashParts.push((value >>> 0).toString(16).padStart(8, '0'))
    }

    return hashParts.join('')
  }

  private async matchFingerprint(
    fingerprint: AudioFingerprint
  ): Promise<CopyrightInfo[]> {
    const hash = fingerprint.hash
    const matches: CopyrightInfo[] = []

    const musicLibrary = this.getMusicLibrary()

    for (const [, info] of musicLibrary) {
      const similarity = this.computeSimilarity(hash, info.hash)

      if (similarity > 0.7) {
        matches.push({
          ...info.copyright,
          confidence: similarity,
        })
      }
    }

    if (matches.length === 0) {
      const genreGuess = this.guessGenre(fingerprint.features)
      matches.push({
        title: '未知音频',
        artist: '未识别',
        genre: genreGuess,
        isCopyrighted: true,
        licenseType: 'Unknown',
        confidence: 0,
      })
    }

    return matches.sort((a, b) => b.confidence - a.confidence)
  }

  private getMusicLibrary(): Map<string, { hash: string; copyright: CopyrightInfo }> {
    const library = new Map<string, { hash: string; copyright: CopyrightInfo }>()

    library.set('creative_commons_1', {
      hash: 'a'.repeat(64),
      copyright: {
        title: 'Creative Commons Sample 1',
        artist: 'CC Artist',
        genre: 'Electronic',
        isCopyrighted: false,
        licenseType: 'CC-BY',
        source: 'Free Music Archive',
        confidence: 0,
      },
    })

    library.set('royalty_free_1', {
      hash: 'b'.repeat(64),
      copyright: {
        title: 'Royalty Free Track',
        artist: 'Free Music Creator',
        genre: 'Ambient',
        isCopyrighted: false,
        licenseType: 'Royalty-Free',
        source: 'YouTube Audio Library',
        confidence: 0,
      },
    })

    return library
  }

  private guessGenre(features: number[]): string {
    const avgEnergy = features.reduce((a, b) => a + b, 0) / features.length
    const variance = features.reduce((a, b) => a + Math.pow(b - avgEnergy, 2), 0) / features.length
    const stdDev = Math.sqrt(variance)

    if (avgEnergy > 0.7 && stdDev < 0.2) {
      return 'Electronic/Dance'
    } else if (avgEnergy < 0.3 && stdDev < 0.1) {
      return 'Ambient/Chill'
    } else if (stdDev > 0.3) {
      return 'Rock/Pop'
    } else if (avgEnergy > 0.5 && avgEnergy < 0.7) {
      return 'Hip-Hop/R&B'
    } else {
      return 'Unknown'
    }
  }

  private async decodeAudio(file: File): Promise<AudioBuffer> {
    if (!this.audioContext) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.audioContext = new AudioContextClass()
    }
    const arrayBuffer = await file.arrayBuffer()
    return await this.audioContext.decodeAudioData(arrayBuffer.slice(0))
  }

  private getMonoData(buffer: AudioBuffer): Float32Array {
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

  private applyHannWindow(data: Float32Array): Float32Array {
    const windowed = new Float32Array(data.length)
    for (let i = 0; i < data.length; i++) {
      windowed[i] = data[i] * 0.5 * (1 - Math.cos((2 * Math.PI * i) / (data.length - 1)))
    }
    return windowed
  }

  private computePowerSpectrum(data: Float32Array): Float32Array {
    const n = data.length
    const real = new Float32Array(data)
    const imag = new Float32Array(n)

    this.fft(real, imag)

    const spectrum = new Float32Array(n / 2)
    for (let i = 0; i < n / 2; i++) {
      spectrum[i] = (real[i] * real[i] + imag[i] * imag[i]) / n
    }

    return spectrum
  }

  private computeBandEnergies(
    spectrum: Float32Array,
    sampleRate: number,
    bandCenters: number[]
  ): Float32Array {
    const energies = new Float32Array(this.NUM_BANDS)
    const nyquist = sampleRate / 2

    for (let band = 0; band < this.NUM_BANDS; band++) {
      const centerFreq = bandCenters[band]
      const bandwidth = centerFreq * 0.1

      const startBin = Math.floor((centerFreq - bandwidth) / nyquist * spectrum.length)
      const endBin = Math.ceil((centerFreq + bandwidth) / nyquist * spectrum.length)

      let energy = 0
      for (let bin = Math.max(0, startBin); bin < Math.min(spectrum.length, endBin); bin++) {
        energy += spectrum[bin]
      }

      energies[band] = Math.log10(energy + 1)
    }

    return energies
  }

  private getLogBandCenters(): number[] {
    const centers: number[] = []
    const logMin = Math.log10(this.BAND_FREQ_START)
    const logMax = Math.log10(this.BAND_FREQ_END)

    for (let i = 0; i < this.NUM_BANDS; i++) {
      const logFreq = logMin + (logMax - logMin) * (i / (this.NUM_BANDS - 1))
      centers.push(Math.pow(10, logFreq))
    }

    return centers
  }

  private findSignificantPeaks(energies: Float32Array): number[] {
    const peaks: number[] = []
    const threshold = this.computeThreshold(energies)

    for (let i = 1; i < energies.length - 1; i++) {
      if (energies[i] > threshold &&
          energies[i] > energies[i - 1] &&
          energies[i] > energies[i + 1]) {
        peaks.push(i / this.NUM_BANDS)
        peaks.push(energies[i])
      }
    }

    return peaks
  }

  private computeThreshold(energies: Float32Array): number {
    const sorted = Array.from(energies).sort((a, b) => a - b)
    const median = sorted[Math.floor(sorted.length / 2)]
    return median * 1.5
  }

  private fft(real: Float32Array, imag: Float32Array) {
    const n = real.length
    if (n <= 1) return

    const evenReal = new Float32Array(n / 2)
    const evenImag = new Float32Array(n / 2)
    const oddReal = new Float32Array(n / 2)
    const oddImag = new Float32Array(n / 2)

    for (let i = 0; i < n / 2; i++) {
      evenReal[i] = real[2 * i]
      evenImag[i] = imag[2 * i]
      oddReal[i] = real[2 * i + 1]
      oddImag[i] = imag[2 * i + 1]
    }

    this.fft(evenReal, evenImag)
    this.fft(oddReal, oddImag)

    for (let k = 0; k < n / 2; k++) {
      const angle = (-2 * Math.PI * k) / n
      const cos = Math.cos(angle)
      const sin = Math.sin(angle)

      const tReal = oddReal[k] * cos - oddImag[k] * sin
      const tImag = oddReal[k] * sin + oddImag[k] * cos

      real[k] = evenReal[k] + tReal
      imag[k] = evenImag[k] + tImag
      real[k + n / 2] = evenReal[k] - tReal
      imag[k + n / 2] = evenImag[k] - tImag
    }
  }
}

export const audioFingerprintService = new AudioFingerprintService()
