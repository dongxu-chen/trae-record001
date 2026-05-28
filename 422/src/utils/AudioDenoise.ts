export interface NoiseProfile {
  noiseFloor: Float32Array
  sampleRate: number
  frameSize: number
  analyzed: boolean
}

export interface DenoiseConfig {
  noiseThreshold: number
  spectralGating: number
  temporalSmoothing: number
  preserveTransients: boolean
  fftSize: number
  useRNNoise: boolean
}

const DEFAULT_CONFIG: DenoiseConfig = {
  noiseThreshold: -40,
  spectralGating: 0.7,
  temporalSmoothing: 0.1,
  preserveTransients: true,
  fftSize: 2048,
  useRNNoise: false,
}

export class AudioDenoise {
  private config: DenoiseConfig
  private noiseProfile: NoiseProfile | null = null
  private audioContext: AudioContext | null = null

  constructor(config?: Partial<DenoiseConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  setConfig(config: Partial<DenoiseConfig>) {
    this.config = { ...this.config, ...config }
  }

  async analyzeNoise(
    file: File,
    durationMs: number = 500,
    offsetMs: number = 0
  ): Promise<NoiseProfile> {
    const audioBuffer = await this.decodeAudio(file)
    const monoData = this.getMonoData(audioBuffer)

    const startSample = Math.floor((offsetMs / 1000) * audioBuffer.sampleRate)
    const endSample = Math.min(
      startSample + Math.floor((durationMs / 1000) * audioBuffer.sampleRate),
      monoData.length
    )

    const fftSize = this.config.fftSize
    const hopSize = fftSize / 4
    const frameCount = Math.floor((endSample - startSample - fftSize) / hopSize)

    const noiseFloor = new Float32Array(fftSize / 2)
    const window = this.createHannWindow(fftSize)

    for (let i = 0; i < frameCount; i++) {
      const frameStart = startSample + i * hopSize
      const frame = monoData.slice(frameStart, frameStart + fftSize)

      for (let j = 0; j < fftSize; j++) {
        frame[j] *= window[j]
      }

      const magnitudes = this.computeMagnitudes(frame)
      for (let bin = 0; bin < noiseFloor.length; bin++) {
        noiseFloor[bin] += magnitudes[bin]
      }
    }

    for (let bin = 0; bin < noiseFloor.length; bin++) {
      noiseFloor[bin] /= frameCount
    }

    this.noiseProfile = {
      noiseFloor,
      sampleRate: audioBuffer.sampleRate,
      frameSize: fftSize,
      analyzed: true,
    }

    return this.noiseProfile
  }

  async denoiseFile(
    file: File,
    progressCallback?: (progress: number, stage: string) => void
  ): Promise<Blob> {
    progressCallback?.(0, '分析音频...')

    if (!this.noiseProfile) {
      progressCallback?.(0.1, '分析噪声...')
      await this.analyzeNoise(file, 500, 0)
    }

    progressCallback?.(0.2, '解码音频...')
    const audioBuffer = await this.decodeAudio(file)
    const sampleRate = audioBuffer.sampleRate
    const numChannels = audioBuffer.numberOfChannels

    progressCallback?.(0.3, '降噪处理...')
    const processedChannels: Float32Array[] = []

    for (let ch = 0; ch < numChannels; ch++) {
      const channelData = audioBuffer.getChannelData(ch)
      const processed = this.spectralSubtraction(
        channelData,
        this.noiseProfile!.noiseFloor,
        sampleRate
      )
      processedChannels.push(processed)

      progressCallback?.(
        0.3 + (ch + 1) / numChannels * 0.5,
        `处理声道 ${ch + 1}/${numChannels}...`
      )
    }

    progressCallback?.(0.8, '编码输出...')

    const length = processedChannels[0].length
    const offlineCtx = new OfflineAudioContext(numChannels, length, sampleRate)

    for (let ch = 0; ch < numChannels; ch++) {
      const buffer = offlineCtx.createBuffer(1, length, sampleRate)
      buffer.copyToChannel(new Float32Array(processedChannels[ch]), 0, 0)
      const source = offlineCtx.createBufferSource()
      source.buffer = buffer
      source.connect(offlineCtx.destination)
      source.start()
    }

    const renderedBuffer = await offlineCtx.startRendering()

    progressCallback?.(0.9, '导出文件...')

    const wavBlob = this.encodeWAV(renderedBuffer)
    progressCallback?.(1, '完成')

    return wavBlob
  }

  private spectralSubtraction(
    input: Float32Array,
    noiseFloor: Float32Array,
    sampleRate: number
  ): Float32Array {
    const fftSize = this.config.fftSize
    const hopSize = fftSize / 4
    const window = this.createHannWindow(fftSize)
    const output = new Float32Array(input.length)

    const thresholdLinear = Math.pow(10, this.config.noiseThreshold / 20)
    const gatingFactor = this.config.spectralGating

    let prevFrame: Float32Array | null = null
    const smoothState = new Float32Array(fftSize / 2)

    for (let pos = 0; pos <= input.length - fftSize; pos += hopSize) {
      const frame = new Float32Array(fftSize)
      for (let i = 0; i < fftSize; i++) {
        frame[i] = input[pos + i] * window[i]
      }

      const real = new Float32Array(frame)
      const imag = new Float32Array(fftSize)

      this.fft(real, imag)

      const magnitudes = new Float32Array(fftSize / 2)
      const phases = new Float32Array(fftSize / 2)

      for (let i = 0; i < fftSize / 2; i++) {
        magnitudes[i] = Math.sqrt(real[i] * real[i] + imag[i] * imag[i])
        phases[i] = Math.atan2(imag[i], real[i])
      }

      const cleanedMagnitudes = new Float32Array(fftSize / 2)

      for (let bin = 0; bin < fftSize / 2; bin++) {
        const noiseMag = noiseFloor[bin] * thresholdLinear * 2
        const snr = magnitudes[bin] / (noiseMag + 0.0001)

        let gain = 1.0
        if (snr < gatingFactor) {
          gain = Math.max(0.01, snr / gatingFactor)
        }

        if (this.config.preserveTransients && prevFrame) {
          const delta = magnitudes[bin] - prevFrame[bin]
          if (delta > 0.5 * magnitudes[bin]) {
            gain = Math.min(1.0, gain + 0.3)
          }
        }

        smoothState[bin] =
          (1 - this.config.temporalSmoothing) * gain +
          this.config.temporalSmoothing * smoothState[bin]

        cleanedMagnitudes[bin] = magnitudes[bin] * smoothState[bin]
      }

      prevFrame = magnitudes

      for (let i = 0; i < fftSize / 2; i++) {
        real[i] = cleanedMagnitudes[i] * Math.cos(phases[i])
        imag[i] = cleanedMagnitudes[i] * Math.sin(phases[i])
        real[fftSize - 1 - i] = real[i]
        imag[fftSize - 1 - i] = -imag[i]
      }

      this.ifft(real, imag)

      for (let i = 0; i < fftSize && pos + i < output.length; i++) {
        output[pos + i] += real[i] * window[i] / (fftSize / hopSize)
      }
    }

    return output
  }

  async applyRealTimeDenoise(
    sourceNode: AudioNode,
    audioContext: AudioContext
  ): Promise<AudioNode> {
    this.audioContext = audioContext

    const analyser = audioContext.createAnalyser()
    analyser.fftSize = this.config.fftSize

    const gainNode = audioContext.createGain()

    if (this.noiseProfile) {
      const biquadFilter = audioContext.createBiquadFilter()
      biquadFilter.type = 'highpass'
      biquadFilter.frequency.value = 80

      const lowpass = audioContext.createBiquadFilter()
      lowpass.type = 'lowpass'
      lowpass.frequency.value = 16000

      sourceNode.connect(biquadFilter)
      biquadFilter.connect(lowpass)
      lowpass.connect(gainNode)
    } else {
      sourceNode.connect(gainNode)
    }

    return gainNode
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

  private createHannWindow(size: number): Float32Array {
    const window = new Float32Array(size)
    for (let i = 0; i < size; i++) {
      window[i] = 0.5 * (1 - Math.cos((2 * Math.PI * i) / (size - 1)))
    }
    return window
  }

  private computeMagnitudes(frame: Float32Array): Float32Array {
    const fftSize = frame.length
    const magnitudes = new Float32Array(fftSize / 2)
    const real = new Float32Array(frame)
    const imag = new Float32Array(fftSize)

    this.fft(real, imag)

    for (let i = 0; i < fftSize / 2; i++) {
      magnitudes[i] = Math.sqrt(real[i] * real[i] + imag[i] * imag[i])
    }

    return magnitudes
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

  private ifft(real: Float32Array, imag: Float32Array) {
    const n = real.length

    for (let i = 0; i < n; i++) {
      imag[i] = -imag[i]
    }

    this.fft(real, imag)

    for (let i = 0; i < n; i++) {
      real[i] /= n
      imag[i] = -imag[i] / n
    }
  }

  private encodeWAV(buffer: AudioBuffer): Blob {
    const numChannels = buffer.numberOfChannels
    const sampleRate = buffer.sampleRate
    const format = 1
    const bitDepth = 16

    const bytesPerSample = bitDepth / 8
    const blockAlign = numChannels * bytesPerSample

    const dataLength = buffer.length * blockAlign
    const bufferLength = 44 + dataLength

    const arrayBuffer = new ArrayBuffer(bufferLength)
    const view = new DataView(arrayBuffer)

    let offset = 0

    this.writeString(view, offset, 'RIFF')
    offset += 4
    view.setUint32(offset, 36 + dataLength, true)
    offset += 4
    this.writeString(view, offset, 'WAVE')
    offset += 4

    this.writeString(view, offset, 'fmt ')
    offset += 4
    view.setUint32(offset, 16, true)
    offset += 4
    view.setUint16(offset, format, true)
    offset += 2
    view.setUint16(offset, numChannels, true)
    offset += 2
    view.setUint32(offset, sampleRate, true)
    offset += 4
    view.setUint32(offset, sampleRate * blockAlign, true)
    offset += 4
    view.setUint16(offset, blockAlign, true)
    offset += 2
    view.setUint16(offset, bitDepth, true)
    offset += 2

    this.writeString(view, offset, 'data')
    offset += 4
    view.setUint32(offset, dataLength, true)
    offset += 4

    const channels: Float32Array[] = []
    for (let ch = 0; ch < numChannels; ch++) {
      channels.push(buffer.getChannelData(ch))
    }

    for (let i = 0; i < buffer.length; i++) {
      for (let ch = 0; ch < numChannels; ch++) {
        const sample = Math.max(-1, Math.min(1, channels[ch][i]))
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
        offset += 2
      }
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' })
  }

  private writeString(view: DataView, offset: number, str: string) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i))
    }
  }

  getNoiseProfile(): NoiseProfile | null {
    return this.noiseProfile
  }

  resetNoiseProfile() {
    this.noiseProfile = null
  }
}

export const audioDenoise = new AudioDenoise()
