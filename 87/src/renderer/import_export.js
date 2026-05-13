import { redisClient } from './RedisClient.js'

export async function exportData(connectionId, pattern = '*') {
  try {
    const data = await redisClient.export(connectionId, pattern)
    const exportObj = {
      version: '1.0',
      exportTime: new Date().toISOString(),
      pattern,
      keyCount: data.length,
      data
    }
    const json = JSON.stringify(exportObj, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = `redis-backup-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    return { success: true, count: data.length }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export function importDataFile() {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) {
        resolve({ success: false, error: 'No file selected' })
        return
      }

      try {
        const text = await file.text()
        const parsed = JSON.parse(text)
        resolve({ success: true, data: parsed.data || parsed })
      } catch (error) {
        resolve({ success: false, error: error.message })
      }
    }
    input.click()
  })
}

export async function importData(connectionId, data) {
  try {
    const count = await redisClient.import(connectionId, data)
    return { success: true, imported: count }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

export function formatDurationUs(us) {
  if (us < 1000) return `${us}µs`
  if (us < 1000000) return `${(us / 1000).toFixed(2)}ms`
  return `${(us / 1000000).toFixed(2)}s`
}

export function formatTimestamp(ts) {
  const d = new Date(ts * 1000)
  const pad = (n) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
