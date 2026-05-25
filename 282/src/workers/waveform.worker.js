class WaveformProcessor {
  constructor() {
    this.audioContext = null
    this.offlineContext = null
  }

  async computeWaveform(audioData, samples = 1000) {
    try {
      if (!this.offlineContext) {
        this.offlineContext = new OfflineAudioContext(1, audioData.length, audioData.sampleRate)
      }

      const channelData = audioData.getChannelData(0)
      const blockSize = Math.floor(channelData.length / samples)
      const waveformData = new Float32Array(samples)

      for (let i = 0; i < samples; i++) {
        const start = i * blockSize
        const end = start + blockSize
        let max = 0
        let min = 0

        for (let j = start; j < end; j++) {
          const val = channelData[j]
          if (val > max) max = val
          if (val < min) min = val
        }

        waveformData[i] = max - min
      }

      const normalized = this.normalizeWaveform(waveformData)

      self.postMessage({
        type: 'waveform',
        data: Array.from(normalized),
        samples
      })
    } catch (error) {
      self.postMessage({
        type: 'error',
        error: error.message
      })
    }
  }

  normalizeWaveform(data) {
    const max = Math.max(...data)
    if (max === 0) return data
    return data.map(v => v / max)
  }

  async decodeAudioFile(arrayBuffer) {
    try {
      const tempContext = new OfflineAudioContext(1, 1000, 44100)
      const audioBuffer = await tempContext.decodeAudioData(arrayBuffer.slice(0))

      self.postMessage({
        type: 'decoded',
        duration: audioBuffer.duration
      })

      await this.computeWaveform(audioBuffer, 2000)
    } catch (error) {
      self.postMessage({
        type: 'error',
        error: error.message
      })
    }
  }

  cleanup() {
    this.offlineContext = null
    this.audioContext = null
  }
}

const processor = new WaveformProcessor()

self.onmessage = async (e) => {
  const { type, data } = e.data

  switch (type) {
    case 'decode':
      await processor.decodeAudioFile(data)
      break
    case 'compute':
      await processor.computeWaveform(data.audioData, data.samples)
      break
    case 'cleanup':
      processor.cleanup()
      break
  }
}
