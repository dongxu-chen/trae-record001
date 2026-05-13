class RedisClient {
  constructor() {
    this.connections = new Map()
    this.api = window.electronAPI?.redis
  }

  async connect(config) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.connect(config)
    if (result.success) {
      this.connections.set(result.connectionId, {
        id: result.connectionId,
        name: config.name || `${config.host}:${config.port}`,
        host: config.host,
        port: config.port
      })
      return result.connectionId
    } else {
      throw new Error(result.error)
    }
  }

  async disconnect(connectionId) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.disconnect(connectionId)
    if (result.success) {
      this.connections.delete(connectionId)
      return true
    } else {
      throw new Error(result.error)
    }
  }

  async keys(connectionId, pattern = '*') {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.keys(connectionId, pattern)
    if (result.success) {
      return result.keys
    } else {
      throw new Error(result.error)
    }
  }

  async scanBatch(connectionId, cursor = 0, pattern = '*', count = 500) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.scanBatch(connectionId, cursor, pattern, count)
    if (result.success) {
      return { cursor: result.cursor, keys: result.keys }
    } else {
      throw new Error(result.error)
    }
  }

  async type(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.type(connectionId, key)
    if (result.success) {
      return result.type
    } else {
      throw new Error(result.error)
    }
  }

  async get(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.get(connectionId, key)
    if (result.success) {
      return result.value
    } else {
      throw new Error(result.error)
    }
  }

  async hgetall(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.hgetall(connectionId, key)
    if (result.success) {
      return result.value
    } else {
      throw new Error(result.error)
    }
  }

  async lrange(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.lrange(connectionId, key)
    if (result.success) {
      return result.value
    } else {
      throw new Error(result.error)
    }
  }

  async smembers(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.smembers(connectionId, key)
    if (result.success) {
      return result.value
    } else {
      throw new Error(result.error)
    }
  }

  async zrange(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.zrange(connectionId, key)
    if (result.success) {
      return result.value
    } else {
      throw new Error(result.error)
    }
  }

  async del(connectionId, key) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.del(connectionId, key)
    if (result.success) {
      return true
    } else {
      throw new Error(result.error)
    }
  }

  async execute(connectionId, command, args = []) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.execute(connectionId, command, args)
    if (result.success) {
      return result.result
    } else {
      throw new Error(result.error)
    }
  }

  async slowlog(connectionId, limit = 128) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.slowlog(connectionId, limit)
    if (result.success) {
      return result.logs
    } else {
      throw new Error(result.error)
    }
  }

  async slowlogLen(connectionId) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.slowlogLen(connectionId)
    if (result.success) {
      return result.length
    } else {
      throw new Error(result.error)
    }
  }

  async slowlogReset(connectionId) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.slowlogReset(connectionId)
    if (result.success) {
      return true
    } else {
      throw new Error(result.error)
    }
  }

  async export(connectionId, pattern = '*') {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.export(connectionId, pattern)
    if (result.success) {
      return result.data
    } else {
      throw new Error(result.error)
    }
  }

  async import(connectionId, data) {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.import(connectionId, data)
    if (result.success) {
      return result.imported
    } else {
      throw new Error(result.error)
    }
  }

  async configGet(connectionId, parameter = '*') {
    if (!this.api) {
      throw new Error('Electron API not available')
    }

    const result = await this.api.configGet(connectionId, parameter)
    if (result.success) {
      return result.config
    } else {
      throw new Error(result.error)
    }
  }

  getConnections() {
    return Array.from(this.connections.values())
  }
}

export const redisClient = new RedisClient()
