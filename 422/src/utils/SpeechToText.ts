export interface TranscriptSegment {
  id: string
  text: string
  startTime: number
  endTime: number
  confidence: number
  speaker?: string
}

export interface TranscriptResult {
  segments: TranscriptSegment[]
  language: string
  duration: number
  wordCount: number
}

export interface SpeechRecognitionConfig {
  language: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
}

const DEFAULT_CONFIG: SpeechRecognitionConfig = {
  language: 'zh-CN',
  continuous: true,
  interimResults: true,
  maxAlternatives: 3,
}

declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
  }
}

export class SpeechToText {
  private config: SpeechRecognitionConfig
  private recognition: any = null
  private segments: TranscriptSegment[] = []
  private currentSegment: Partial<TranscriptSegment> = {}
  private startTime = 0
  private isRecording = false
  private audioContext: AudioContext | null = null

  constructor(config?: Partial<SpeechRecognitionConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config }
  }

  isSupported(): boolean {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window
  }

  async transcribeFile(
    file: File,
    onProgress?: (progress: number, stage: string) => void
  ): Promise<TranscriptResult> {
    onProgress?.(0, '准备转录...')

    if (!this.isSupported()) {
      throw new Error('当前浏览器不支持语音识别功能，请使用Chrome或Edge浏览器')
    }

    onProgress?.(0.1, '分析音频...')

    const audioBuffer = await this.decodeAudio(file)
    const sampleRate = audioBuffer.sampleRate
    const duration = audioBuffer.duration

    onProgress?.(0.2, '分段处理...')

    const segments: TranscriptSegment[] = []
    const segmentDuration = 30
    const totalSegments = Math.ceil(duration / segmentDuration)

    for (let i = 0; i < totalSegments; i++) {
      const startTime = i * segmentDuration
      const endTime = Math.min(startTime + segmentDuration, duration)
      const segmentLength = Math.floor((endTime - startTime) * sampleRate)

      const segmentBuffer = new AudioBuffer({
        numberOfChannels: audioBuffer.numberOfChannels,
        length: segmentLength,
        sampleRate: sampleRate,
      })

      for (let ch = 0; ch < audioBuffer.numberOfChannels; ch++) {
        const channelData = audioBuffer.getChannelData(ch)
        const segmentData = segmentBuffer.getChannelData(ch)
        const startSample = Math.floor(startTime * sampleRate)
        for (let j = 0; j < segmentLength && startSample + j < channelData.length; j++) {
          segmentData[j] = channelData[startSample + j]
        }
      }

      onProgress?.(
        0.2 + (i / totalSegments) * 0.6,
        `转录分段 ${i + 1}/${totalSegments}...`
      )

      const wavBlob = this.bufferToWav(segmentBuffer)
      const text = await this.transcribeBlob(wavBlob, this.config.language)

      if (text) {
        segments.push({
          id: `seg_${i}_${Date.now()}`,
          text,
          startTime,
          endTime,
          confidence: 0.8,
        })
      }
    }

    onProgress?.(0.85, '合并结果...')

    const mergedSegments = this.mergeSegments(segments)

    onProgress?.(0.95, '生成字幕...')

    const result: TranscriptResult = {
      segments: mergedSegments,
      language: this.config.language,
      duration,
      wordCount: mergedSegments.reduce((sum, s) => sum + s.text.length, 0),
    }

    onProgress?.(1, '完成')

    return result
  }

  startRealTimeRecognition(
    onSegment: (segment: TranscriptSegment) => void,
    onError?: (error: string) => void
  ): boolean {
    if (!this.isSupported()) {
      onError?.('当前浏览器不支持语音识别')
      return false
    }

    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition
    this.recognition = new SpeechRecognitionClass()
    this.recognition.lang = this.config.language
    this.recognition.continuous = this.config.continuous
    this.recognition.interimResults = this.config.interimResults
    this.recognition.maxAlternatives = this.config.maxAlternatives

    this.segments = []
    this.startTime = Date.now()
    this.isRecording = true
    this.currentSegment = {
      startTime: 0,
    }

    this.recognition.onresult = (event: any) => {
      const result = event.results[event.results.length - 1]
      const transcript = result[0].transcript
      const confidence = result[0].confidence

      if (result.isFinal) {
        const endTime = (Date.now() - this.startTime) / 1000
        const segment: TranscriptSegment = {
          id: `seg_${Date.now()}`,
          text: transcript.trim(),
          startTime: this.currentSegment.startTime || 0,
          endTime,
          confidence,
        }
        this.segments.push(segment)
        onSegment(segment)

        this.currentSegment = {
          startTime: endTime,
        }
      }
    }

    this.recognition.onerror = (event: any) => {
      if (event.error !== 'no-speech') {
        onError?.(`识别错误: ${event.error}`)
      }
    }

    this.recognition.onend = () => {
      if (this.isRecording) {
        try {
          this.recognition?.start()
        } catch (e) {
          // ignore
        }
      }
    }

    try {
      this.recognition.start()
      return true
    } catch (e) {
      return false
    }
  }

  stopRealTimeRecognition(): TranscriptSegment[] {
    this.isRecording = false
    this.recognition?.stop()
    return [...this.segments]
  }

  generateSRT(segments: TranscriptSegment[]): string {
    let srt = ''

    segments.forEach((segment, index) => {
      srt += `${index + 1}\n`
      srt += `${this.formatSRTTime(segment.startTime)} --> ${this.formatSRTTime(segment.endTime)}\n`
      srt += `${segment.text}\n\n`
    })

    return srt
  }

  generateVTT(segments: TranscriptSegment[]): string {
    let vtt = 'WEBVTT\n\n'

    segments.forEach((segment) => {
      vtt += `${this.formatVTTTime(segment.startTime)} --> ${this.formatVTTTime(segment.endTime)}\n`
      vtt += `${segment.text}\n\n`
    })

    return vtt
  }

  exportSubtitleFile(
    segments: TranscriptSegment[],
    format: 'srt' | 'vtt' = 'srt'
  ): Blob {
    const content = format === 'srt'
      ? this.generateSRT(segments)
      : this.generateVTT(segments)

    const mimeTypes: Record<string, string> = {
      srt: 'application/x-subrip',
      vtt: 'text/vtt',
    }

    return new Blob([content], { type: mimeTypes[format] })
  }

  private async decodeAudio(file: File): Promise<AudioBuffer> {
    if (!this.audioContext) {
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.audioContext = new AudioContextClass()
    }
    const arrayBuffer = await file.arrayBuffer()
    return await this.audioContext.decodeAudioData(arrayBuffer.slice(0))
  }

  private bufferToWav(buffer: AudioBuffer): Blob {
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

    const writeString = (str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset++, str.charCodeAt(i))
      }
    }

    writeString('RIFF')
    view.setUint32(offset, 36 + dataLength, true)
    offset += 4
    writeString('WAVE')
    writeString('fmt ')
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
    writeString('data')
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

  private async transcribeBlob(blob: Blob, language: string): Promise<string> {
    return new Promise((resolve) => {
      if (!this.isSupported()) {
        resolve('')
        return
      }

      const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition
      const recognition = new SpeechRecognitionClass()
      recognition.lang = language
      recognition.continuous = false
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      let finalTranscript = ''

      recognition.onresult = (event: any) => {
        finalTranscript = event.results[0][0].transcript
      }

      recognition.onerror = () => {
        resolve(finalTranscript)
      }

      recognition.onend = () => {
        resolve(finalTranscript)
      }

      try {
        recognition.start()
        setTimeout(() => {
          recognition.stop()
        }, 10000)
      } catch (e) {
        resolve('')
      }
    })
  }

  private mergeSegments(segments: TranscriptSegment[]): TranscriptSegment[] {
    if (segments.length === 0) return segments

    const merged: TranscriptSegment[] = []
    let current = { ...segments[0] }

    for (let i = 1; i < segments.length; i++) {
      const next = segments[i]

      if (next.text.length === 0) continue

      if (next.startTime - current.endTime < 0.5 &&
          current.text.length + next.text.length < 100) {
        current.text += next.text
        current.endTime = next.endTime
        current.confidence = (current.confidence + next.confidence) / 2
      } else {
        merged.push(current)
        current = { ...next }
      }
    }

    merged.push(current)
    return merged
  }

  private formatSRTTime(seconds: number): string {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 1000)
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${ms.toString().padStart(3, '0')}`
  }

  private formatVTTTime(seconds: number): string {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    const ms = Math.floor((seconds % 1) * 1000)
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`
  }

  setLanguage(language: string) {
    this.config.language = language
  }

  getSegments(): TranscriptSegment[] {
    return this.segments
  }

  isRecordingActive(): boolean {
    return this.isRecording
  }
}

export const speechToText = new SpeechToText()
