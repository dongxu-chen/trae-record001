export class HeatmapCache {
  constructor(maxSize = 10) {
    this.cache = new Map()
    this.maxSize = maxSize
    this.accessOrder = []
  }

  _getKey(zoom, center, radius, blur) {
    const centerKey = `${center.lat.toFixed(4)}_${center.lng.toFixed(4)}`
    return `${zoom}_${centerKey}_${radius}_${blur.toFixed(2)}`
  }

  has(zoom, center, radius, blur) {
    const key = this._getKey(zoom, center, radius, blur)
    return this.cache.has(key)
  }

  get(zoom, center, radius, blur) {
    const key = this._getKey(zoom, center, radius, blur)
    const item = this.cache.get(key)
    
    if (item) {
      this._updateAccessOrder(key)
      return item.data
    }
    return null
  }

  set(zoom, center, radius, blur, imageData) {
    const key = this._getKey(zoom, center, radius, blur)
    
    if (this.cache.size >= this.maxSize) {
      const oldestKey = this.accessOrder.shift()
      this.cache.delete(oldestKey)
    }
    
    this.cache.set(key, {
      data: imageData,
      timestamp: Date.now()
    })
    this.accessOrder.push(key)
  }

  _updateAccessOrder(key) {
    const index = this.accessOrder.indexOf(key)
    if (index > -1) {
      this.accessOrder.splice(index, 1)
      this.accessOrder.push(key)
    }
  }

  clear() {
    this.cache.clear()
    this.accessOrder = []
  }

  clearByZoom(zoom) {
    const keysToDelete = []
    for (const key of this.cache.keys()) {
      if (key.startsWith(`${zoom}_`)) {
        keysToDelete.push(key)
      }
    }
    keysToDelete.forEach(key => {
      this.cache.delete(key)
      const index = this.accessOrder.indexOf(key)
      if (index > -1) {
        this.accessOrder.splice(index, 1)
      }
    })
  }

  get size() {
    return this.cache.size
  }
}

export class ZoomLevelCache {
  constructor() {
    this.zoomCache = new Map()
  }

  has(zoom) {
    return this.zoomCache.has(zoom)
  }

  get(zoom) {
    return this.zoomCache.get(zoom)
  }

  set(zoom, data) {
    this.zoomCache.set(zoom, {
      data: data,
      timestamp: Date.now()
    })
  }

  clear() {
    this.zoomCache.clear()
  }

  clearExcept(zoomLevels) {
    for (const key of this.zoomCache.keys()) {
      if (!zoomLevels.includes(key)) {
        this.zoomCache.delete(key)
      }
    }
  }

  get size() {
    return this.zoomCache.size
  }
}
