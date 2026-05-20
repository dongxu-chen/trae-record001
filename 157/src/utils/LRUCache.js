export class LRUCache {
  constructor(maxSize = 20) {
    this.maxSize = maxSize
    this.cache = new Map()
    this.accessOrder = []
  }

  get(key) {
    if (!this.cache.has(key)) {
      return null
    }
    
    const index = this.accessOrder.indexOf(key)
    if (index > -1) {
      this.accessOrder.splice(index, 1)
    }
    this.accessOrder.push(key)
    
    return this.cache.get(key)
  }

  set(key, value) {
    if (this.cache.has(key)) {
      const index = this.accessOrder.indexOf(key)
      if (index > -1) {
        this.accessOrder.splice(index, 1)
      }
    } else {
      if (this.cache.size >= this.maxSize) {
        const oldestKey = this.accessOrder.shift()
        const oldValue = this.cache.get(oldestKey)
        if (oldValue && typeof oldValue.destroy === 'function') {
          oldValue.destroy()
          console.log(`LRU缓存: 释放页面 ${oldestKey + 1} 纹理`)
        }
        this.cache.delete(oldestKey)
      }
    }
    
    this.cache.set(key, value)
    this.accessOrder.push(key)
    console.log(`LRU缓存: 缓存页面 ${key + 1}, 当前大小: ${this.cache.size}/${this.maxSize}`)
  }

  has(key) {
    return this.cache.has(key)
  }

  delete(key) {
    const value = this.cache.get(key)
    if (value && typeof value.destroy === 'function') {
      value.destroy()
    }
    this.cache.delete(key)
    const index = this.accessOrder.indexOf(key)
    if (index > -1) {
      this.accessOrder.splice(index, 1)
    }
  }

  clear() {
    for (const [key, value] of this.cache.entries()) {
      if (value && typeof value.destroy === 'function') {
        value.destroy()
      }
    }
    this.cache.clear()
    this.accessOrder = []
  }

  size() {
    return this.cache.size
  }

  keys() {
    return this.cache.keys()
  }
}

export default LRUCache
