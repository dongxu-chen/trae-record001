const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const Redis = require('ioredis')

let redisClients = new Map()
let mainWindow = null

function cleanupAll() {
  redisClients.forEach(client => {
    try {
      client.disconnect()
    } catch (e) {}
  })
  redisClients.clear()
}

function createWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.focus()
    return
  }

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
    cleanupAll()
  })

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  cleanupAll()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

ipcMain.handle('redis:connect', async (event, config) => {
  try {
    const id = `conn_${Date.now()}`
    const client = new Redis({
      host: config.host,
      port: config.port,
      password: config.password,
      db: config.db || 0,
      family: 4,
      connectTimeout: 5000,
      lazyConnect: true
    })

    await client.connect()
    redisClients.set(id, client)

    client.on('error', (err) => {
      console.error('Redis error:', err)
    })

    return { success: true, connectionId: id, name: config.name }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:disconnect', async (event, connectionId) => {
  const client = redisClients.get(connectionId)
  if (client) {
    client.disconnect()
    redisClients.delete(connectionId)
    return { success: true }
  }
  return { success: false, error: 'Connection not found' }
})

ipcMain.handle('redis:keys', async (event, { connectionId, pattern }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const matchPattern = pattern || '*'
    const keys = new Set()
    let cursor = 0

    do {
      const result = await client.scan(cursor, 'MATCH', matchPattern, 'COUNT', 500)
      cursor = parseInt(result[0], 10)
      const batchKeys = result[1]
      for (const k of batchKeys) {
        keys.add(k)
      }
    } while (cursor !== 0)

    return { success: true, keys: Array.from(keys) }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:scanBatch', async (event, { connectionId, cursor, pattern, count }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const result = await client.scan(
      cursor || 0,
      'MATCH',
      pattern || '*',
      'COUNT',
      count || 500
    )
    return {
      success: true,
      cursor: parseInt(result[0], 10),
      keys: result[1]
    }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:type', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const type = await client.type(key)
    return { success: true, type }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:get', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const value = await client.get(key)
    return { success: true, value }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:hgetall', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const value = await client.hgetall(key)
    return { success: true, value }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:lrange', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const value = await client.lrange(key, 0, -1)
    return { success: true, value }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:smembers', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const value = await client.smembers(key)
    return { success: true, value }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:zrange', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const value = await client.zrange(key, 0, -1, 'WITHSCORES')
    return { success: true, value }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:del', async (event, { connectionId, key }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    await client.del(key)
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:execute', async (event, { connectionId, command, args }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const cmd = command.toLowerCase()
    const result = await client.call(cmd, ...(args || []))
    return { success: true, result }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:slowlog', async (event, { connectionId, limit }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const logs = await client.call('slowlog', 'get', limit || 128)
    const parsed = logs.map((log) => ({
      id: log[0],
      timestamp: log[1],
      durationUs: log[2],
      command: log[3].join(' '),
      client: log[4] || '',
      clientName: log[5] || ''
    }))
    return { success: true, logs: parsed }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:slowlogLen', async (event, { connectionId }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const len = await client.call('slowlog', 'len')
    return { success: true, length: len }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:slowlogReset', async (event, { connectionId }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    await client.call('slowlog', 'reset')
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:export', async (event, { connectionId, pattern }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const matchPattern = pattern || '*'
    const keys = new Set()
    let cursor = 0

    do {
      const result = await client.scan(cursor, 'MATCH', matchPattern, 'COUNT', 500)
      cursor = parseInt(result[0], 10)
      for (const k of result[1]) keys.add(k)
    } while (cursor !== 0)

    const data = []
    for (const key of Array.from(keys)) {
      const type = await client.type(key)
      let value = null

      if (type === 'string') {
        value = await client.get(key)
      } else if (type === 'hash') {
        value = await client.hgetall(key)
      } else if (type === 'list') {
        value = await client.lrange(key, 0, -1)
      } else if (type === 'set') {
        value = await client.smembers(key)
      } else if (type === 'zset') {
        value = await client.zrange(key, 0, -1, 'WITHSCORES')
      }

      data.push({ key, type, value })
    }

    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:import', async (event, { connectionId, data }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    let imported = 0
    for (const item of data) {
      const { key, type, value } = item
      try {
        if (type === 'string') {
          await client.set(key, value)
        } else if (type === 'hash') {
          if (Object.keys(value).length > 0) {
            await client.hmset(key, value)
          }
        } else if (type === 'list') {
          if (value.length > 0) {
            await client.del(key)
            await client.rpush(key, ...value)
          }
        } else if (type === 'set') {
          if (value.length > 0) {
            await client.sadd(key, ...value)
          }
        } else if (type === 'zset') {
          if (value.length > 0) {
            await client.del(key)
            for (let i = 0; i < value.length; i += 2) {
              await client.zadd(key, value[i + 1], value[i])
            }
          }
        }
        imported++
      } catch (e) {
        console.warn(`Failed to import key ${key}:`, e.message)
      }
    }
    return { success: true, imported }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('redis:configGet', async (event, { connectionId, parameter }) => {
  const client = redisClients.get(connectionId)
  if (!client) {
    return { success: false, error: 'Connection not found' }
  }
  try {
    const result = await client.call('config', 'get', parameter || '*')
    const config = {}
    for (let i = 0; i < result.length; i += 2) {
      config[result[i]] = result[i + 1]
    }
    return { success: true, config }
  } catch (error) {
    return { success: false, error: error.message }
  }
})
