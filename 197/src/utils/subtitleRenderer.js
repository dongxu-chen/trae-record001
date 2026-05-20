class LRUCache {
  constructor(maxSize = 100) {
    this.maxSize = maxSize
    this.cache = new Map()
    this.hits = 0
    this.misses = 0
  }

  get(key) {
    if (!this.cache.has(key)) {
      this.misses++
      return null
    }
    
    const value = this.cache.get(key)
    this.cache.delete(key)
    this.cache.set(key, value)
    this.hits++
    return value
  }

  set(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key)
    }
    
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      const oldValue = this.cache.get(firstKey)
      if (oldValue && oldValue.canvas) {
        this.releaseCanvas(oldValue.canvas)
      }
      this.cache.delete(firstKey)
    }
    
    this.cache.set(key, value)
  }

  has(key) {
    return this.cache.has(key)
  }

  clear() {
    for (const value of this.cache.values()) {
      if (value && value.canvas) {
        this.releaseCanvas(value.canvas)
      }
    }
    this.cache.clear()
  }

  getStats() {
    const total = this.hits + this.misses
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      hits: this.hits,
      misses: this.misses,
      hitRate: total > 0 ? (this.hits / total * 100).toFixed(1) + '%' : '0%',
    }
  }

  releaseCanvas(canvas) {
    try {
      const gl = canvas.getContext('webgl') || canvas.getContext('webgl2')
      if (gl) {
        gl.getExtension('WEBGL_lose_context')?.loseContext()
      }
      canvas.width = 0
      canvas.height = 0
    } catch (e) {}
  }
}

class CanvasPool {
  constructor(poolSize = 20) {
    this.pool = []
    this.poolSize = poolSize
    this._initializePool()
  }

  _initializePool() {
    for (let i = 0; i < this.poolSize; i++) {
      this.pool.push(this._createCanvas())
    }
  }

  _createCanvas() {
    const canvas = document.createElement('canvas')
    canvas._inUse = false
    canvas._lastUsed = 0
    return canvas
  }

  acquire(width, height) {
    let canvas = this.pool.find(c => !c._inUse)
    
    if (!canvas) {
      if (this.pool.length < this.poolSize * 2) {
        canvas = this._createCanvas()
        this.pool.push(canvas)
      } else {
        const oldest = this.pool
          .filter(c => !c._inUse)
          .sort((a, b) => a._lastUsed - b._lastUsed)[0]
        
        if (oldest) {
          canvas = oldest
        } else {
          canvas = this._createCanvas()
        }
      }
    }
    
    canvas._inUse = true
    canvas._lastUsed = Date.now()
    
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
    }
    
    return canvas
  }

  release(canvas) {
    if (canvas && this.pool.includes(canvas)) {
      canvas._inUse = false
      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height)
      }
    }
  }

  clear() {
    for (const canvas of this.pool) {
      if (!canvas._inUse) {
        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2')
        if (gl) {
          gl.getExtension('WEBGL_lose_context')?.loseContext()
        }
        canvas.width = 0
        canvas.height = 0
      }
    }
    this.pool = this.pool.filter(c => c._inUse)
  }

  getStats() {
    const inUse = this.pool.filter(c => c._inUse).length
    return {
      total: this.pool.length,
      inUse,
      available: this.pool.length - inUse,
    }
  }
}

export class SubtitleRenderer {
  constructor(options = {}) {
    this.width = options.width || 1920
    this.height = options.height || 1080
    this.dpr = options.dpr || window.devicePixelRatio || 1
    
    this.frameCache = new LRUCache(options.cacheSize || 200)
    this.canvasPool = new CanvasPool(options.poolSize || 30)
    
    this.offscreenCanvas = document.createElement('canvas')
    this.offscreenCanvas.width = this.width * this.dpr
    this.offscreenCanvas.height = this.height * this.dpr
    
    this.ctx = this.offscreenCanvas.getContext('2d', { 
      alpha: true,
      willReadFrequently: false,
    })
    
    this.ctx.scale(this.dpr, this.dpr)
    
    this.currentSubtitleId = null
    this.currentStyleHash = null
    this.renderStats = {
      totalRenders: 0,
      cachedRenders: 0,
      incrementalRenders: 0,
    }
    
    this.animationFrameId = null
    this.pendingFrames = new Map()
    this.preloadWindow = 2.0
  }

  _hashSubtitle(subtitle) {
    const style = subtitle.style || {}
    return [
      subtitle.id,
      subtitle.text,
      style.fontSize,
      style.color,
      style.backgroundColor,
      style.position,
      style.fontFamily || 'Arial',
      style.fontWeight || 'normal',
    ].join('|')
  }

  _hashStyle(style) {
    return JSON.stringify(style)
  }

  _getCacheKey(subtitle, time) {
    const hash = this._hashSubtitle(subtitle)
    const timeKey = Math.floor(time * 1000)
    return `${hash}_${timeKey}`
  }

  async preloadSubtitles(subtitles, currentTime) {
    if (!subtitles || subtitles.length === 0) return
    
    const upcoming = subtitles.filter(s => 
      s.startTime >= currentTime - 0.5 && 
      s.startTime <= currentTime + this.preloadWindow
    )
    
    for (const sub of upcoming) {
      const cacheKey = this._getCacheKey(sub, sub.startTime)
      if (!this.frameCache.has(cacheKey)) {
        this.pendingFrames.set(cacheKey, sub)
      }
    }
    
    this._processPendingFrames()
  }

  _processPendingFrames() {
    if (this.pendingFrames.size === 0) return
    if (this.animationFrameId) return
    
    const processBatch = () => {
      const entries = Array.from(this.pendingFrames.entries()).slice(0, 3)
      
      for (const [cacheKey, subtitle] of entries) {
        if (!this.frameCache.has(cacheKey)) {
          const bitmap = this._renderToBitmap(subtitle)
          this.frameCache.set(cacheKey, {
            bitmap,
            timestamp: Date.now(),
            subtitleId: subtitle.id,
          })
        }
        this.pendingFrames.delete(cacheKey)
      }
      
      if (this.pendingFrames.size > 0) {
        this.animationFrameId = requestAnimationFrame(processBatch)
      } else {
        this.animationFrameId = null
      }
    }
    
    this.animationFrameId = requestAnimationFrame(processBatch)
  }

  _renderToBitmap(subtitle) {
    const canvas = this.canvasPool.acquire(this.width, this.height)
    const ctx = canvas.getContext('2d', { alpha: true })
    
    ctx.clearRect(0, 0, this.width, this.height)
    
    this._drawSubtitle(ctx, subtitle, this.width, this.height)
    
    const bitmap = canvas.transferToImageBitmap 
      ? canvas.transferToImageBitmap()
      : this._canvasToImageBitmap(canvas)
    
    this.canvasPool.release(canvas)
    
    return bitmap
  }

  _canvasToImageBitmap(canvas) {
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        createImageBitmap(blob).then(resolve)
      }, 'image/png')
    })
  }

  _drawSubtitle(ctx, subtitle, width, height) {
    const style = subtitle.style || {}
    const text = subtitle.text
    
    const fontSize = style.fontSize || 48
    const fontFamily = style.fontFamily || 'Arial, sans-serif'
    const fontWeight = style.fontWeight || 'bold'
    const color = style.color || '#ffffff'
    const backgroundColor = style.backgroundColor || 'rgba(0, 0, 0, 0.5)'
    const position = style.position || 'bottom'
    
    ctx.save()
    
    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`
    ctx.textBaseline = 'middle'
    ctx.textAlign = 'center'
    
    const lines = text.split('\n')
    const lineHeight = fontSize * 1.2
    const totalHeight = lines.length * lineHeight
    const paddingX = fontSize * 0.4
    const paddingY = fontSize * 0.2
    
    let maxWidth = 0
    const lineWidths = []
    for (const line of lines) {
      const w = ctx.measureText(line).width
      lineWidths.push(w)
      maxWidth = Math.max(maxWidth, w)
    }
    
    const boxWidth = maxWidth + paddingX * 2
    const boxHeight = totalHeight + paddingY * 2
    
    let x = width / 2
    let y
    
    switch (position) {
      case 'top':
        y = height * 0.15
        break
      case 'middle':
        y = height / 2
        break
      case 'bottom':
      default:
        y = height - height * 0.12
        break
    }
    
    const boxX = x - boxWidth / 2
    const boxY = y - boxHeight / 2
    
    if (backgroundColor && backgroundColor !== 'transparent') {
      ctx.fillStyle = backgroundColor
      this._drawRoundedRect(ctx, boxX, boxY, boxWidth, boxHeight, 8)
      ctx.fill()
    }
    
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 4
    ctx.shadowOffsetX = 2
    ctx.shadowOffsetY = 2
    
    ctx.fillStyle = color
    
    let currentY = y - (lines.length - 1) * lineHeight / 2
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i], x, currentY)
      currentY += lineHeight
    }
    
    ctx.restore()
  }

  _drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + width - radius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
    ctx.lineTo(x + width, y + height - radius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    ctx.lineTo(x + radius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
  }

  render(subtitle, currentTime) {
    if (!subtitle) {
      this.currentSubtitleId = null
      return null
    }
    
    const cacheKey = this._getCacheKey(subtitle, currentTime)
    const cached = this.frameCache.get(cacheKey)
    
    if (cached) {
      this.renderStats.cachedRenders++
      return {
        bitmap: cached.bitmap,
        fromCache: true,
      }
    }
    
    const styleHash = this._hashStyle(subtitle.style)
    const isIncremental = (
      this.currentSubtitleId === subtitle.id && 
      this.currentStyleHash === styleHash
    )
    
    if (isIncremental) {
      this.renderStats.incrementalRenders++
    }
    
    this.renderStats.totalRenders++
    
    const bitmap = this._renderToBitmap(subtitle)
    
    this.frameCache.set(cacheKey, {
      bitmap,
      timestamp: Date.now(),
      subtitleId: subtitle.id,
    })
    
    this.currentSubtitleId = subtitle.id
    this.currentStyleHash = styleHash
    
    return {
      bitmap,
      fromCache: false,
      incremental: isIncremental,
    }
  }

  renderToCanvas(targetCanvas, subtitle, currentTime) {
    const result = this.render(subtitle, currentTime)
    
    if (!result) {
      const ctx = targetCanvas.getContext('2d')
      ctx.clearRect(0, 0, targetCanvas.width, targetCanvas.height)
      return false
    }
    
    const ctx = targetCanvas.getContext('2d')
    
    if (targetCanvas.width !== this.width || targetCanvas.height !== this.height) {
      targetCanvas.width = this.width
      targetCanvas.height = this.height
    }
    
    ctx.clearRect(0, 0, targetCanvas.width, targetCanvas.height)
    
    if (result.bitmap instanceof ImageBitmap) {
      ctx.drawImage(result.bitmap, 0, 0)
    } else if (result.bitmap instanceof HTMLCanvasElement) {
      ctx.drawImage(result.bitmap, 0, 0)
    } else if (result.bitmap instanceof Promise) {
      result.bitmap.then(bitmap => {
        ctx.drawImage(bitmap, 0, 0)
      })
    }
    
    return result
  }

  renderToDOM(subtitle, currentTime) {
    const result = this.render(subtitle, currentTime)
    if (!result) return null
    
    const canvas = document.createElement('canvas')
    canvas.width = this.width
    canvas.height = this.height
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    canvas.style.objectFit = 'contain'
    
    const ctx = canvas.getContext('2d')
    
    if (result.bitmap instanceof ImageBitmap) {
      ctx.drawImage(result.bitmap, 0, 0)
    } else if (result.bitmap instanceof Promise) {
      result.bitmap.then(bitmap => {
        ctx.drawImage(bitmap, 0, 0)
      })
    }
    
    return {
      element: canvas,
      ...result,
    }
  }

  invalidateSubtitle(subtitleId) {
    const keysToDelete = []
    for (const [key, value] of this.frameCache.cache.entries()) {
      if (value.subtitleId === subtitleId) {
        keysToDelete.push(key)
      }
    }
    for (const key of keysToDelete) {
      const value = this.frameCache.cache.get(key)
      if (value && value.bitmap && value.bitmap.close) {
        value.bitmap.close()
      }
      this.frameCache.cache.delete(key)
    }
  }

  invalidateAll() {
    this.frameCache.clear()
    this.currentSubtitleId = null
    this.currentStyleHash = null
  }

  resize(width, height) {
    this.width = width
    this.height = height
    this.offscreenCanvas.width = width * this.dpr
    this.offscreenCanvas.height = height * this.dpr
    this.ctx.setTransform(1, 0, 0, 1, 0, 0)
    this.ctx.scale(this.dpr, this.dpr)
    this.invalidateAll()
  }

  getStats() {
    return {
      render: this.renderStats,
      cache: this.frameCache.getStats(),
      pool: this.canvasPool.getStats(),
      dpr: this.dpr,
      resolution: `${this.width}x${this.height}`,
    }
  }

  dispose() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId)
    }
    
    this.frameCache.clear()
    this.canvasPool.clear()
    this.pendingFrames.clear()
    
    const gl = this.offscreenCanvas.getContext('webgl') || 
               this.offscreenCanvas.getContext('webgl2')
    if (gl) {
      gl.getExtension('WEBGL_lose_context')?.loseContext()
    }
    
    this.offscreenCanvas.width = 0
    this.offscreenCanvas.height = 0
  }
}

export default SubtitleRenderer
