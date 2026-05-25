export class AudioReactor {
  constructor() {
    this.audioContext = null
    this.analyser = null
    this.dataArray = null
    this.source = null
    this.audioElement = null
    
    this.enabled = false
    this.initialized = false
    
    this.fftSize = 2048
    this.smoothingTimeConstant = 0.8
    
    this.bass = 0
    this.mid = 0
    this.treble = 0
    this.volume = 0
    
    this.sensitivity = 1.5
    this.bassMultiplier = 2.0
    this.midMultiplier = 1.0
    this.trebleMultiplier = 0.8
    
    this.reactiveParams = {
      emissionRate: { enabled: true, intensity: 1, freqBand: 'bass' },
      speed: { enabled: true, intensity: 0.5, freqBand: 'mid' },
      size: { enabled: true, intensity: 0.3, freqBand: 'treble' },
      color: { enabled: false, intensity: 1, freqBand: 'mid' }
    }
    
    this.onUpdate = null
  }
  
  async init() {
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = this.fftSize
      this.analyser.smoothingTimeConstant = this.smoothingTimeConstant
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount)
      this.initialized = true
      return true
    } catch (error) {
      console.error('Failed to initialize audio context:', error)
      return false
    }
  }
  
  async connectToMicrophone() {
    if (!this.initialized && !(await this.init())) {
      return false
    }
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.source = this.audioContext.createMediaStreamSource(stream)
      this.source.connect(this.analyser)
      this.enabled = true
      return true
    } catch (error) {
      console.error('Failed to connect to microphone:', error)
      return false
    }
  }
  
  async connectToAudioElement(audioElement) {
    if (!this.initialized && !(await this.init())) {
      return false
    }
    
    try {
      this.audioElement = audioElement
      this.source = this.audioContext.createMediaElementSource(audioElement)
      this.source.connect(this.analyser)
      this.analyser.connect(this.audioContext.destination)
      this.enabled = true
      return true
    } catch (error) {
      console.error('Failed to connect to audio element:', error)
      return false
    }
  }
  
  loadAudioFile(file) {
    return new Promise((resolve, reject) => {
      const audio = new Audio()
      audio.src = URL.createObjectURL(file)
      audio.crossOrigin = 'anonymous'
      audio.loop = true
      
      audio.addEventListener('loadedmetadata', async () => {
        await this.connectToAudioElement(audio)
        resolve(audio)
      })
      
      audio.addEventListener('error', (error) => {
        reject(error)
      })
    })
  }
  
  update() {
    if (!this.enabled || !this.analyser) return
    
    this.analyser.getByteFrequencyData(this.dataArray)
    
    const binCount = this.dataArray.length
    const bassEnd = Math.floor(binCount * 0.1)
    const midEnd = Math.floor(binCount * 0.5)
    
    let bassSum = 0
    let midSum = 0
    let trebleSum = 0
    let totalSum = 0
    
    for (let i = 0; i < bassEnd; i++) {
      bassSum += this.dataArray[i]
    }
    
    for (let i = bassEnd; i < midEnd; i++) {
      midSum += this.dataArray[i]
    }
    
    for (let i = midEnd; i < binCount; i++) {
      trebleSum += this.dataArray[i]
    }
    
    this.bass = (bassSum / bassEnd / 255) * this.sensitivity * this.bassMultiplier
    this.mid = (midSum / (midEnd - bassEnd) / 255) * this.sensitivity * this.midMultiplier
    this.treble = (trebleSum / (binCount - midEnd) / 255) * this.sensitivity * this.trebleMultiplier
    this.volume = (this.bass + this.mid + this.treble) / 3
    
    if (this.onUpdate) {
      this.onUpdate({
        bass: this.bass,
        mid: this.mid,
        treble: this.treble,
        volume: this.volume
      })
    }
  }
  
  getFreqBand(band) {
    switch (band) {
      case 'bass': return this.bass
      case 'mid': return this.mid
      case 'treble': return this.treble
      case 'volume': return this.volume
      default: return this.volume
    }
  }
  
  applyToParticleConfig(baseConfig) {
    if (!this.enabled) return baseConfig
    
    const config = { ...baseConfig }
    
    for (const [paramName, settings] of Object.entries(this.reactiveParams)) {
      if (!settings.enabled) continue
      
      const freqValue = this.getFreqBand(settings.freqBand)
      const intensity = settings.intensity
      
      switch (paramName) {
        case 'emissionRate':
          if (typeof config.emissionRate === 'number') {
            config.emissionRate = Math.floor(config.emissionRate * (1 + freqValue * intensity))
          }
          break
          
        case 'speed':
          if (config.speed && typeof config.speed.min === 'number') {
            config.speed = {
              min: config.speed.min * (1 + freqValue * intensity * 0.5),
              max: config.speed.max * (1 + freqValue * intensity)
            }
          }
          break
          
        case 'size':
          if (config.size && typeof config.size.min === 'number') {
            config.size = {
              min: config.size.min * (1 + freqValue * intensity * 0.5),
              max: config.size.max * (1 + freqValue * intensity)
            }
          }
          break
          
        case 'color':
          if (config.color && config.color.start) {
            const baseColor = this.hexToRgb(config.color.start)
            const shift = freqValue * intensity
            
            const newColor = {
              r: Math.min(255, Math.floor(baseColor.r * (1 + shift))),
              g: Math.min(255, Math.floor(baseColor.g * (1 + shift * 0.5))),
              b: Math.min(255, Math.floor(baseColor.b * (1 + shift * 0.3)))
            }
            
            config.color = {
              start: this.rgbToHex(newColor.r, newColor.g, newColor.b),
              end: config.color.end
            }
          }
          break
      }
    }
    
    return config
  }
  
  hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 255, g: 255, b: 255 }
  }
  
  rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(x => {
      const hex = Math.max(0, Math.min(255, x)).toString(16)
      return hex.length === 1 ? '0' + hex : hex
    }).join('')
  }
  
  setSensitivity(value) {
    this.sensitivity = value
  }
  
  setReactiveParam(paramName, settings) {
    if (this.reactiveParams[paramName]) {
      Object.assign(this.reactiveParams[paramName], settings)
    }
  }
  
  play() {
    if (this.audioElement) {
      this.audioElement.play()
    }
  }
  
  pause() {
    if (this.audioElement) {
      this.audioElement.pause()
    }
  }
  
  stop() {
    this.enabled = false
    
    if (this.audioElement) {
      this.audioElement.pause()
      this.audioElement.currentTime = 0
    }
    
    if (this.source) {
      this.source.disconnect()
      this.source = null
    }
    
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
      this.initialized = false
    }
    
    this.bass = 0
    this.mid = 0
    this.treble = 0
    this.volume = 0
  }
  
  dispose() {
    this.stop()
    this.onUpdate = null
  }
}
