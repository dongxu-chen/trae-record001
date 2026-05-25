export class AudioCutter {
  constructor() {
    this.audioContext = null
  }

  initContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
  }

  async loadAudioBuffer(url) {
    this.initContext()
    const response = await fetch(url)
    const arrayBuffer = await response.arrayBuffer()
    return await this.audioContext.decodeAudioData(arrayBuffer)
  }

  async cutAudio(audioBuffer, startTime, endTime) {
    this.initContext()
    
    const sampleRate = audioBuffer.sampleRate
    const startSample = Math.floor(startTime * sampleRate)
    const endSample = Math.floor(endTime * sampleRate)
    const length = endSample - startSample

    const offlineContext = new OfflineAudioContext(
      audioBuffer.numberOfChannels,
      length,
      sampleRate
    )

    const source = offlineContext.createBufferSource()
    source.buffer = audioBuffer
    source.connect(offlineContext.destination)
    source.start(0, startTime, endTime - startTime)

    return await offlineContext.startRendering()
  }

  audioBufferToWav(audioBuffer) {
    const numChannels = audioBuffer.numberOfChannels
    const sampleRate = audioBuffer.sampleRate
    const format = 1
    const bitDepth = 16

    const bytesPerSample = bitDepth / 8
    const blockAlign = numChannels * bytesPerSample

    const dataLength = audioBuffer.length * blockAlign
    const buffer = new ArrayBuffer(44 + dataLength)
    const view = new DataView(buffer)

    this.writeString(view, 0, 'RIFF')
    view.setUint32(4, 36 + dataLength, true)
    this.writeString(view, 8, 'WAVE')
    this.writeString(view, 12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, format, true)
    view.setUint16(22, numChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * blockAlign, true)
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, bitDepth, true)
    this.writeString(view, 36, 'data')
    view.setUint32(40, dataLength, true)

    const channels = []
    for (let i = 0; i < numChannels; i++) {
      channels.push(audioBuffer.getChannelData(i))
    }

    let offset = 44
    for (let i = 0; i < audioBuffer.length; i++) {
      for (let ch = 0; ch < numChannels; ch++) {
        const sample = Math.max(-1, Math.min(1, channels[ch][i]))
        const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        view.setInt16(offset, intSample, true)
        offset += 2
      }
    }

    return new Blob([buffer], { type: 'audio/wav' })
  }

  writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async exportClip(audioUrl, startTime, endTime, filename = 'clip.wav') {
    try {
      const audioBuffer = await this.loadAudioBuffer(audioUrl)
      const clippedBuffer = await this.cutAudio(audioBuffer, startTime, endTime)
      const wavBlob = this.audioBufferToWav(clippedBuffer)
      this.downloadBlob(wavBlob, filename)
      return true
    } catch (error) {
      console.error('Export failed:', error)
      return false
    }
  }
}

export default AudioCutter
