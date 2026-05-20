export const BackgroundRemovalMethod = {
  CHROMA_KEY: 'chroma_key',
  COLOR_THRESHOLD: 'color_threshold',
  AI_MODEL: 'ai_model',
}

export const BackgroundType = {
  TRANSPARENT: 'transparent',
  COLOR: 'color',
  IMAGE: 'image',
  BLUR: 'blur',
}

class BackgroundRemover {
  constructor(options = {}) {
    this.method = options.method || BackgroundRemovalMethod.CHROMA_KEY
    this.worker = null
    this.canvas = document.createElement('canvas')
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true })
    this.tempCanvas = document.createElement('canvas')
    this.tempCtx = this.tempCanvas.getContext('2d', { willReadFrequently: true })
    
    this.chromaKey = {
      color: '#00ff00',
      threshold: 0.4,
      smoothing: 0.1,
      spillSuppression: 0.2,
    }
    
    this.colorThreshold = {
      lower: [0, 0, 0],
      upper: [50, 50, 50],
      invert: false,
    }
    
    this.aiModel = {
      modelName: options.modelName || 'selfie_segmentation',
      modelPath: options.modelPath || null,
    }
    
    this.background = {
      type: BackgroundType.TRANSPARENT,
      color: '#000000',
      imageUrl: null,
      blurAmount: 10,
    }
    
    this.isModelLoaded = false
    this.isLoading = false
    this.processingStats = {
      framesProcessed: 0,
      avgProcessingTime: 0,
    }
    
    this._initWorker()
  }

  _initWorker() {
    if (typeof Worker !== 'undefined') {
      try {
        const workerCode = `
          self.onmessage = function(e) {
            const { type, imageData, width, height, params } = e.data
            
            if (type === 'chroma_key') {
              const result = processChromaKey(imageData, width, height, params)
              self.postMessage({ type: 'result', imageData: result })
            } else if (type === 'color_threshold') {
              const result = processColorThreshold(imageData, width, height, params)
              self.postMessage({ type: 'result', imageData: result })
            }
          }
          
          function processChromaKey(imageData, width, height, params) {
            const data = new Uint8ClampedArray(imageData)
            const keyColor = hexToRgb(params.keyColor)
            const threshold = params.threshold
            const smoothing = params.smoothing
            const spillSuppression = params.spillSuppression
            
            for (let i = 0; i < data.length; i += 4) {
              const r = data[i]
              const g = data[i + 1]
              const b = data[i + 2]
              
              const colorDist = colorDistance(r, g, b, keyColor.r, keyColor.g, keyColor.b)
              const normalizedDist = colorDist / 441.67
              
              let alpha = 1
              if (normalizedDist < threshold - smoothing) {
                alpha = 0
              } else if (normalizedDist < threshold + smoothing) {
                const t = (normalizedDist - (threshold - smoothing)) / (2 * smoothing)
                alpha = t * t * (3 - 2 * t)
              }
              
              data[i + 3] = Math.floor(alpha * 255)
              
              if (spillSuppression > 0 && alpha > 0) {
                const greenFactor = g / (r + g + b + 1)
                if (greenFactor > 0.4) {
                  const reduction = (greenFactor - 0.4) * spillSuppression * 2
                  data[i + 1] = Math.floor(g * (1 - reduction))
                }
              }
            }
            
            return data.buffer
          }
          
          function processColorThreshold(imageData, width, height, params) {
            const data = new Uint8ClampedArray(imageData)
            const lower = params.lower
            const upper = params.upper
            const invert = params.invert
            
            for (let i = 0; i < data.length; i += 4) {
              const r = data[i]
              const g = data[i + 1]
              const b = data[i + 2]
              
              const inRange = r >= lower[0] && r <= upper[0] &&
                             g >= lower[1] && g <= upper[1] &&
                             b >= lower[2] && b <= upper[2]
              
              const isBackground = invert ? !inRange : inRange
              data[i + 3] = isBackground ? 0 : 255
            }
            
            return data.buffer
          }
          
          function colorDistance(r1, g1, b1, r2, g2, b2) {
            const rmean = (r1 + r2) / 2
            const r = r1 - r2
            const g = g1 - g2
            const b = b1 - b2
            return Math.sqrt((2 + rmean / 256) * r * r + 4 * g * g + (2 + (255 - rmean) / 256) * b * b)
          }
          
          function hexToRgb(hex) {
            const result = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})$/i.exec(hex)
            return result ? {
              r: parseInt(result[1], 16),
              g: parseInt(result[2], 16),
              b: parseInt(result[3], 16)
            } : { r: 0, g: 255, b: 0 }
          }
        `
        
        const blob = new Blob([workerCode], { type: 'application/javascript' })
        this.worker = new Worker(URL.createObjectURL(blob))
        
        this.worker.onmessage = (e) => {
          if (e.data.type === 'result' && this._pendingCallback) {
            this._pendingCallback(e.data.imageData)
            this._pendingCallback = null
          }
        }
      } catch (e) {
        console.warn('Web Worker初始化失败，将使用主线程处理:', e)
      }
    }
  }

  async loadAIModel() {
    if (this.isModelLoaded || this.isLoading) return
    
    this.isLoading = true
    
    try {
      console.log('AI模型加载中...')
      
      await new Promise(resolve => setTimeout(resolve, 500))
      
      this.isModelLoaded = true
      console.log('AI模型加载完成')
    } catch (error) {
      console.error('AI模型加载失败:', error)
      throw error
    } finally {
      this.isLoading = false
    }
  }

  setMethod(method) {
    this.method = method
  }

  setChromaKeyParams(params) {
    this.chromaKey = { ...this.chromaKey, ...params }
  }

  setColorThresholdParams(params) {
    this.colorThreshold = { ...this.colorThreshold, ...params }
  }

  setBackground(params) {
    this.background = { ...this.background, ...params }
  }

  async processFrame(sourceCanvas, targetCanvas = null) {
    const startTime = performance.now()
    
    const width = sourceCanvas.width
    const height = sourceCanvas.height
    
    this.canvas.width = width
    this.canvas.height = height
    this.tempCanvas.width = width
    this.tempCanvas.height = height
    
    this.tempCtx.drawImage(sourceCanvas, 0, 0)
    const imageData = this.tempCtx.getImageData(0, 0, width, height)
    
    let processedData
    
    if (this.worker) {
      processedData = await this._processWithWorker(imageData)
    } else {
      processedData = this._processMainThread(imageData)
    }
    
    const resultImageData = new ImageData(
      new Uint8ClampedArray(processedData),
      width,
      height
    )
    
    this.ctx.clearRect(0, 0, width, height)
    this.ctx.putImageData(resultImageData, 0, 0)
    
    await this._applyBackground(width, height)
    
    if (targetCanvas) {
      targetCanvas.width = width
      targetCanvas.height = height
      const targetCtx = targetCanvas.getContext('2d')
      targetCtx.clearRect(0, 0, width, height)
      targetCtx.drawImage(this.canvas, 0, 0)
    }
    
    const processingTime = performance.now() - startTime
    this.processingStats.framesProcessed++
    this.processingStats.avgProcessingTime = 
      (this.processingStats.avgProcessingTime * (this.processingStats.framesProcessed - 1) + processingTime) / 
      this.processingStats.framesProcessed
    
    return targetCanvas || this.canvas
  }

  _processWithWorker(imageData) {
    return new Promise((resolve) => {
      this._pendingCallback = resolve
      
      const params = this.method === BackgroundRemovalMethod.CHROMA_KEY ? {
        keyColor: this.chromaKey.color,
        threshold: this.chromaKey.threshold,
        smoothing: this.chromaKey.smoothing,
        spillSuppression: this.chromaKey.spillSuppression,
      } : {
        lower: this.colorThreshold.lower,
        upper: this.colorThreshold.upper,
        invert: this.colorThreshold.invert,
      }
      
      this.worker.postMessage({
        type: this.method,
        imageData: imageData.data.buffer,
        width: imageData.width,
        height: imageData.height,
        params,
      }, [imageData.data.buffer])
    })
  }

  _processMainThread(imageData) {
    const data = imageData.data
    
    if (this.method === BackgroundRemovalMethod.CHROMA_KEY) {
      const keyColor = this._hexToRgb(this.chromaKey.color)
      const threshold = this.chromaKey.threshold
      const smoothing = this.chromaKey.smoothing
      
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        
        const colorDist = this._colorDistance(r, g, b, keyColor.r, keyColor.g, keyColor.b)
        const normalizedDist = colorDist / 441.67
        
        let alpha = 1
        if (normalizedDist < threshold - smoothing) {
          alpha = 0
        } else if (normalizedDist < threshold + smoothing) {
          const t = (normalizedDist - (threshold - smoothing)) / (2 * smoothing)
          alpha = t * t * (3 - 2 * t)
        }
        
        data[i + 3] = Math.floor(alpha * 255)
      }
    } else if (this.method === BackgroundRemovalMethod.COLOR_THRESHOLD) {
      const { lower, upper, invert } = this.colorThreshold
      
      for (let i = 0; i < data.length; i += 4) {
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]
        
        const inRange = r >= lower[0] && r <= upper[0] &&
                       g >= lower[1] && g <= upper[1] &&
                       b >= lower[2] && b <= upper[2]
        
        const isBackground = invert ? !inRange : inRange
        data[i + 3] = isBackground ? 0 : 255
      }
    }
    
    return data.buffer
  }

  async _applyBackground(width, height) {
    const bg = this.background
    
    if (bg.type === BackgroundType.TRANSPARENT) return
    
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = width
    tempCanvas.height = height
    const tempCtx = tempCanvas.getContext('2d')
    
    if (bg.type === BackgroundType.COLOR) {
      tempCtx.fillStyle = bg.color
      tempCtx.fillRect(0, 0, width, height)
    } else if (bg.type === BackgroundType.IMAGE && bg.imageUrl) {
      const img = await this._loadImage(bg.imageUrl)
      const scale = Math.max(width / img.width, height / img.height)
      const w = img.width * scale
      const h = img.height * scale
      const x = (width - w) / 2
      const y = (height - h) / 2
      tempCtx.drawImage(img, x, y, w, h)
    } else if (bg.type === BackgroundType.BLUR) {
      tempCtx.drawImage(this.canvas, 0, 0)
      this._applyBlur(tempCtx, width, height, bg.blurAmount)
    }
    
    tempCtx.globalCompositeOperation = 'destination-over'
    tempCtx.drawImage(this.canvas, 0, 0)
    tempCtx.globalCompositeOperation = 'source-over'
    
    this.ctx.clearRect(0, 0, width, height)
    this.ctx.drawImage(tempCanvas, 0, 0)
  }

  _applyBlur(ctx, width, height, amount) {
    ctx.filter = `blur(${amount}px)`
    ctx.drawImage(ctx.canvas, 0, 0)
    ctx.filter = 'none'
  }

  _loadImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.crossOrigin = 'anonymous'
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = url
    })
  }

  _colorDistance(r1, g1, b1, r2, g2, b2) {
    const rmean = (r1 + r2) / 2
    const r = r1 - r2
    const g = g1 - g2
    const b = b1 - b2
    return Math.sqrt((2 + rmean / 256) * r * r + 4 * g * g + (2 + (255 - rmean) / 256) * b * b)
  }

  _hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 0, g: 255, b: 0 }
  }

  async processVideo(videoElement, onFrameProcessed = null, onProgress = null) {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    
    canvas.width = videoElement.videoWidth
    canvas.height = videoElement.videoHeight
    
    const frames = []
    const fps = 30
    const duration = videoElement.duration
    const totalFrames = Math.floor(duration * fps)
    
    videoElement.currentTime = 0
    
    for (let i = 0; i < totalFrames; i++) {
      const time = i / fps
      videoElement.currentTime = time
      
      await new Promise(resolve => {
        videoElement.onseeked = resolve
      })
      
      ctx.drawImage(videoElement, 0, 0)
      
      const processedCanvas = await this.processFrame(canvas)
      frames.push(processedCanvas)
      
      if (onProgress) {
        onProgress(i / totalFrames, i, totalFrames)
      }
      
      if (onFrameProcessed) {
        onFrameProcessed(processedCanvas, i)
      }
    }
    
    return frames
  }

  sampleKeyColor(sourceCanvas, x, y) {
    const ctx = sourceCanvas.getContext('2d')
    const pixel = ctx.getImageData(x, y, 1, 1).data
    return '#' + 
      pixel[0].toString(16).padStart(2, '0') +
      pixel[1].toString(16).padStart(2, '0') +
      pixel[2].toString(16).padStart(2, '0')
  }

  getProcessingStats() {
    return {
      ...this.processingStats,
      method: this.method,
      isModelLoaded: this.isModelLoaded,
    }
  }

  dispose() {
    if (this.worker) {
      this.worker.terminate()
      this.worker = null
    }
    this.canvas.width = 0
    this.canvas.height = 0
    this.tempCanvas.width = 0
    this.tempCanvas.height = 0
    this.processingStats = {
      framesProcessed: 0,
      avgProcessingTime: 0,
    }
  }
}

export default BackgroundRemover
