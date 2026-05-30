const { v4: uuidv4 } = require('uuid')

class CaptchaStore {
  constructor() {
    this.store = new Map()
    this.errorCount = new Map()
    this.maxErrors = 5
    this.lockTime = 60000
    this.expireTime = 300000
  }

  generateId() {
    return uuidv4()
  }

  save(captchaId, data, type) {
    this.store.set(captchaId, {
      ...data,
      type,
      createdAt: Date.now(),
      verified: false,
    })
  }

  get(captchaId) {
    const data = this.store.get(captchaId)
    if (!data) return null

    if (Date.now() - data.createdAt > this.expireTime) {
      this.store.delete(captchaId)
      return null
    }

    return data
  }

  delete(captchaId) {
    this.store.delete(captchaId)
  }

  markVerified(captchaId) {
    const data = this.store.get(captchaId)
    if (data) {
      data.verified = true
    }
  }

  recordError(captchaId, ip) {
    const key = `${ip}:${captchaId}`
    const count = (this.errorCount.get(key) || 0) + 1
    this.errorCount.set(key, count)

    if (count >= this.maxErrors) {
      setTimeout(() => {
        this.errorCount.delete(key)
      }, this.lockTime)
      return { locked: true, remaining: 0, lockTime: this.lockTime }
    }

    return { locked: false, remaining: this.maxErrors - count }
  }

  isLocked(captchaId, ip) {
    const key = `${ip}:${captchaId}`
    const count = this.errorCount.get(key) || 0
    return count >= this.maxErrors
  }

  cleanup() {
    const now = Date.now()
    for (const [id, data] of this.store.entries()) {
      if (now - data.createdAt > this.expireTime) {
        this.store.delete(id)
      }
    }
  }
}

const captchaStore = new CaptchaStore()

setInterval(() => {
  captchaStore.cleanup()
}, 60000)

module.exports = captchaStore
