class LayerResourceManager {
  constructor() {
    this.layerCache = new Map()
    this.hiddenLayers = new Set()
    this.lruOrder = []
    this.maxCacheSize = 50
    this.memoryThreshold = 100 * 1024 * 1024
    this.totalCachedSize = 0
    this.gcTimer = null
    this.startAutoGC()
  }

  registerLayer(layerId, fabricObject) {
    if (this.layerCache.has(layerId)) {
      this.updateLRU(layerId)
      return
    }

    const cacheEntry = {
      id: layerId,
      object: fabricObject,
      visible: true,
      originalElement: null,
      cachedData: null,
      cacheSize: 0,
      lastUsed: Date.now(),
      refCount: 1
    }

    this.layerCache.set(layerId, cacheEntry)
    this.lruOrder.push(layerId)
    this.updateLRU(layerId)

    this.checkMemoryPressure()
  }

  unregisterLayer(layerId) {
    const entry = this.layerCache.get(layerId)
    if (!entry) return

    entry.refCount--
    if (entry.refCount <= 0) {
      this.releaseLayerResources(layerId)
      this.layerCache.delete(layerId)
      this.lruOrder = this.lruOrder.filter(id => id !== layerId)
      this.totalCachedSize -= entry.cacheSize
    }
  }

  hideLayer(layerId) {
    const entry = this.layerCache.get(layerId)
    if (!entry || !entry.visible) return

    entry.visible = false
    this.hiddenLayers.add(layerId)

    if (entry.object && entry.object.type === 'image') {
      this.cacheAndReleaseImage(entry)
    }

    if (entry.object) {
      entry.object.visible = false
    }

    this.scheduleGC()
  }

  showLayer(layerId) {
    const entry = this.layerCache.get(layerId)
    if (!entry) return

    entry.visible = true
    this.hiddenLayers.delete(layerId)

    if (entry.object && entry.object.type === 'image' && entry.cachedData) {
      this.restoreImageFromCache(entry)
    }

    if (entry.object) {
      entry.object.visible = true
    }

    this.updateLRU(layerId)
  }

  cacheAndReleaseImage(entry) {
    if (!entry.object || !entry.object.getElement()) return

    const imgElement = entry.object.getElement()
    if (!(imgElement instanceof HTMLImageElement)) return

    const canvas = document.createElement('canvas')
    canvas.width = imgElement.naturalWidth || imgElement.width
    canvas.height = imgElement.naturalHeight || imgElement.height

    const ctx = canvas.getContext('2d')
    ctx.drawImage(imgElement, 0, 0)

    entry.cachedData = canvas.toDataURL('image/png')
    entry.cacheSize = entry.cachedData.length
    entry.originalElement = imgElement.src
    this.totalCachedSize += entry.cacheSize

    entry.object._element = null
  }

  restoreImageFromCache(entry) {
    if (!entry.cachedData || !entry.object) return

    const img = new Image()
    img.onload = () => {
      if (entry.object) {
        entry.object.setElement(img)
        entry.cachedData = null
        this.totalCachedSize -= entry.cacheSize
        entry.cacheSize = 0
      }
    }
    img.src = entry.cachedData
  }

  updateLRU(layerId) {
    const index = this.lruOrder.indexOf(layerId)
    if (index > -1) {
      this.lruOrder.splice(index, 1)
    }
    this.lruOrder.unshift(layerId)

    const entry = this.layerCache.get(layerId)
    if (entry) {
      entry.lastUsed = Date.now()
    }
  }

  checkMemoryPressure() {
    if (this.totalCachedSize > this.memoryThreshold) {
      this.evictLRU()
    }
  }

  evictLRU() {
    while (this.totalCachedSize > this.memoryThreshold * 0.7 && this.lruOrder.length > 0) {
      const layerId = this.lruOrder.pop()
      const entry = this.layerCache.get(layerId)

      if (entry && entry.visible) {
        continue
      }

      if (entry) {
        this.releaseLayerResources(layerId)
      }
    }
  }

  releaseLayerResources(layerId) {
    const entry = this.layerCache.get(layerId)
    if (!entry) return

    if (entry.cachedData) {
      this.totalCachedSize -= entry.cacheSize
      entry.cachedData = null
      entry.cacheSize = 0
    }

    if (entry.object && entry.object.type === 'image') {
      const element = entry.object.getElement()
      if (element && element.src && element.src.startsWith('blob:')) {
        URL.revokeObjectURL(element.src)
      }
    }
  }

  scheduleGC() {
    if (this.gcTimer) {
      clearTimeout(this.gcTimer)
    }
    this.gcTimer = setTimeout(() => {
      this.garbageCollect()
    }, 5000)
  }

  garbageCollect() {
    const now = Date.now()
    const idleThreshold = 30000

    for (const layerId of this.hiddenLayers) {
      const entry = this.layerCache.get(layerId)
      if (entry && now - entry.lastUsed > idleThreshold) {
        this.releaseLayerResources(layerId)
      }
    }
  }

  startAutoGC() {
    setInterval(() => {
      this.garbageCollect()
    }, 60000)
  }

  isLayerVisible(layerId) {
    const entry = this.layerCache.get(layerId)
    return entry ? entry.visible : true
  }

  getLayerEntry(layerId) {
    return this.layerCache.get(layerId)
  }

  getMemoryStats() {
    return {
      totalLayers: this.layerCache.size,
      hiddenLayers: this.hiddenLayers.size,
      cachedMemory: this.formatSize(this.totalCachedSize),
      memoryLimit: this.formatSize(this.memoryThreshold)
    }
  }

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  dispose() {
    if (this.gcTimer) {
      clearTimeout(this.gcTimer)
    }

    for (const layerId of this.layerCache.keys()) {
      this.releaseLayerResources(layerId)
    }

    this.layerCache.clear()
    this.hiddenLayers.clear()
    this.lruOrder = []
    this.totalCachedSize = 0
  }
}

export const layerResourceManager = new LayerResourceManager()
export default LayerResourceManager
