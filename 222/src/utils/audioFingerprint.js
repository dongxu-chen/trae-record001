export class AudioFingerprinter {
  constructor() {
    this.fingerprints = new Map()
    this.sampleRate = 44100
    this.fftSize = 2048
    this.bands = 33
  }

  async generateFingerprint(audioBuffer) {
    const offlineCtx = new OfflineAudioContext(1, audioBuffer.length, audioBuffer.sampleRate)
    const source = offlineCtx.createBufferSource()
    source.buffer = audioBuffer
    
    const analyser = offlineCtx.createAnalyser()
    analyser.fftSize = this.fftSize
    
    source.connect(analyser)
    analyser.connect(offlineCtx.destination)
    
    source.start(0)
    await offlineCtx.startRendering()
    
    const frequencyData = new Float32Array(analyser.frequencyBinCount)
    analyser.getFloatFrequencyData(frequencyData)
    
    return this.extractFingerprint(frequencyData, analyser.frequencyBinCount, audioBuffer.sampleRate)
  }

  extractFingerprint(frequencyData, binCount, sampleRate) {
    const fingerprint = []
    const bandEdges = this.getLogBands(sampleRate, binCount)
    
    for (let i = 0; i < bandEdges.length - 1; i++) {
      let maxEnergy = -Infinity
      let maxBin = bandEdges[i]
      
      for (let j = bandEdges[i]; j < bandEdges[i + 1]; j++) {
        if (frequencyData[j] > maxEnergy) {
          maxEnergy = frequencyData[j]
          maxBin = j
        }
      }
      
      fingerprint.push(maxBin)
    }
    
    return fingerprint
  }

  getLogBands(sampleRate, binCount) {
    const nyquist = sampleRate / 2
    const minFreq = 20
    const maxFreq = nyquist
    const bands = []
    
    for (let i = 0; i <= this.bands; i++) {
      const freq = minFreq * Math.pow(maxFreq / minFreq, i / this.bands)
      const bin = Math.floor((freq / nyquist) * binCount)
      bands.push(Math.min(bin, binCount - 1))
    }
    
    return bands
  }

  async generateFingerprintFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
          const audioBuffer = await audioCtx.decodeAudioData(e.target.result)
          const fingerprint = await this.generateFingerprint(audioBuffer)
          audioCtx.close()
          resolve(fingerprint)
        } catch (err) {
          reject(err)
        }
      }
      reader.onerror = reject
      reader.readAsArrayBuffer(file)
    })
  }

  addToLibrary(songId, fingerprint, metadata) {
    this.fingerprints.set(songId, { fingerprint, metadata })
  }

  removeFromLibrary(songId) {
    this.fingerprints.delete(songId)
  }

  compareFingerprints(fp1, fp2) {
    if (fp1.length !== fp2.length) return 0
    
    let matches = 0
    const threshold = 5
    
    for (let i = 0; i < fp1.length; i++) {
      if (Math.abs(fp1[i] - fp2[i]) <= threshold) {
        matches++
      }
    }
    
    return matches / fp1.length
  }

  async identify(recordedFingerprint, threshold = 0.6) {
    let bestMatch = null
    let bestScore = 0
    
    for (const [songId, data] of this.fingerprints.entries()) {
      const score = this.compareFingerprints(recordedFingerprint, data.fingerprint)
      if (score > bestScore && score >= threshold) {
        bestScore = score
        bestMatch = { songId, score, metadata: data.metadata }
      }
    }
    
    return bestMatch
  }
}

export class AudioRecorder {
  constructor() {
    this.mediaRecorder = null
    this.audioChunks = []
    this.stream = null
  }

  async start() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.mediaRecorder = new MediaRecorder(this.stream)
      this.audioChunks = []
      
      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          this.audioChunks.push(e.data)
        }
      }
      
      this.mediaRecorder.start()
      return true
    } catch (err) {
      console.error('录音失败:', err)
      return false
    }
  }

  async stop() {
    return new Promise((resolve) => {
      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' })
        
        this.stream.getTracks().forEach(track => track.stop())
        this.stream = null
        this.mediaRecorder = null
        
        resolve(audioBlob)
      }
      
      this.mediaRecorder.stop()
    })
  }

  async record(duration = 5000) {
    await this.start()
    await new Promise(resolve => setTimeout(resolve, duration))
    return this.stop()
  }
}

export async function blobToAudioBuffer(blob) {
  const arrayBuffer = await blob.arrayBuffer()
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer)
  audioCtx.close()
  return audioBuffer
}
